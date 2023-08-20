from aiohttp import ClientSession
from datetime import date, datetime, time, timedelta
from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.models import StatisticMetaData, StatisticData
from homeassistant.components.recorder.statistics import async_add_external_statistics, get_last_statistics, statistics_during_period
from homeassistant.components.recorder.history import get_significant_states
from homeassistant.util.dt import get_time_zone, now, as_utc, as_local, DEFAULT_TIME_ZONE
from bisect import bisect_right
from itertools import islice

PRAGUE_TZ = get_time_zone('Europe/Prague')


def get_eur_rate(day: date):
    from_day_str = (day - timedelta(days=2)).strftime('%d.%m.%Y')
    day_str = day.strftime('%d.%m.%Y')
    url = f'https://www.cnb.cz/cs/financni-trhy/devizovy-trh/kurzy-devizoveho-trhu/kurzy-devizoveho-trhu/vybrane.txt?od={from_day_str}&do={day_str}&mena=EUR&format=txt'
    async with ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                line = resp.text().strip().split('\n')[-1].strip().split('|')
                #assert line[0] == day_str, f'Returned EUR rate date {line[0]} is not {day_str}'
                log.info(f'Read EUR rate of {line[1]} on {line[0]}')
                return float(line[1].replace(',', '.'))
            else:
                log.warning(f'Failed to get EUR rate for URL={url}, status={resp.status}')
                return None


def get_power(day: date):
    entity_id = 'sensor.meter_total_energy_export'
    dt = as_utc(datetime.combine(day, time.min, tzinfo=DEFAULT_TIME_ZONE))
    states = await get_instance(hass).async_add_executor_job(
        get_significant_states,
        hass,
        dt - timedelta(hours=3),
        dt + timedelta(days=1, hours=3),
        [entity_id],
        None, #filters
        True, #include_start_time_state
        True, #significant_changes_only
        False, #minimal_response
        True, #no_attributes
        False #compressed_state_format
    )
    points = {s.last_changed: float(s.state) for s in states[entity_id]}
    log.info(f'Read {len(points)} power points')
    return points


def get_prices(day: date):
    url = f'https://www.ote-cr.cz/cs/kratkodobe-trhy/elektrina/denni-trh/@@chart-data?report_date={day.isoformat()}'
    async with ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                log.warning(f'Reading electricicty prices for {url} failed: {resp.status}')
                return None
            else:
                data = resp.json()
                points = {(int(d['x']) - 1): float(d['y']) for d in data['data']['dataLine'][1]['point']}
                log.info(f'Read {len(points)} electricity prices')
                return points


@event_trigger('scrape_electricity_price')
def scrape_electricity_price():
    tomorrow = now().date() + timedelta(days=1)
    prices = get_prices(tomorrow)
    stats = [StatisticData(start=as_utc(datetime.combine(tomorrow, time(h, 0, 0), tzinfo=DEFAULT_TIME_ZONE)), mean=p, min=p, max=p) for h, p in prices.items()]
    meta = StatisticMetaData(statistic_id='ote:electricity_price', source='ote', name='Electricity price', has_sum=False, has_mean=True, unit_of_measurement='€/MWh')
    async_add_external_statistics(hass, meta, stats)
    log.info(f'Added {len(stats)} electricity prices for {tomorrow}')


def get_last_income_sum(yesterday: date):
    last_income_stats = await get_instance(hass).async_add_executor_job(
        get_last_statistics,
        hass,
        1,
        'ote:pv_income',
        False,
        {"sum"},
    )
    if len(last_income_stats) == 0:
        log.error('Starting income from zero? Better not saving!!!')
        raise Exception("No last income!")
    lis = last_income_stats['ote:pv_income'][0]
    last_income_date = datetime.fromtimestamp(lis['end'])
    assert last_income_date <= datetime.combine(yesterday, time.min), f"Last income sum is newer than what we are reading! last income date={last_income_date}, yesterday={yesterday}"
    income_sum = lis['sum']
    log.info(f'Read last income sum = {income_sum}')
    return income_sum
    

def get_prices_stats(yesterday: date):
    stats = await get_instance(hass).async_add_executor_job(
        statistics_during_period,
        hass,
        as_utc(datetime.combine(yesterday, time.min, tzinfo=DEFAULT_TIME_ZONE)),
        as_utc(datetime.combine(yesterday, time.min, tzinfo=DEFAULT_TIME_ZONE) + timedelta(days=1)),
        {'ote:electricity_price'},
        "hour",
        None,
        {"mean"},
    )
    prices = {i: s['mean'] for i, s in enumerate(stats['ote:electricity_price'])}
    log.info(f'Read {len(prices)} prices stats from {yesterday}')
    return prices


@event_trigger('scrape_electricity')
def scrape_electricity():
    yesterday = now().date() - timedelta(days=1)

    prices = get_prices_stats(yesterday)

    eur_rate = get_eur_rate(yesterday - timedelta(days=1))

    power = get_power(yesterday)
    i = 0
    power_dates = [as_local(d) for d in power.keys()]
    power_values = list(power.values())
    powers = {}
    for h in range(25):
        i = bisect_right(power_dates, datetime.combine(yesterday, time.min, tzinfo=DEFAULT_TIME_ZONE) + timedelta(hours=h), lo=i)
        if i == 0:
            continue
        if i >= len(power_dates):
            break
        powers[h] = power_values[i-1]
        log.debug((h, i, power_dates[i-1], power_values[i-1]))
    power_diffs = {h: (p2 - p1) for (h, p1), p2 in zip(powers.items(), islice(powers.values(), 1, None))}
    log.info(f'Reduced power to {len(power_diffs)} hours')

    income_stats = []
    income_sum = get_last_income_sum(yesterday)
    for h in range(24):
        start = as_utc(datetime.combine(yesterday, time(h, 0, 0), tzinfo=DEFAULT_TIME_ZONE))
        if h in prices and h in power_diffs:
            income = prices[h] * power_diffs[h] * eur_rate / 1000
            income_sum += income
            income_stats.append(StatisticData(start=start, state=income, sum=income_sum))

    income_meta = StatisticMetaData(statistic_id='ote:pv_income', source='ote', name='PV export income', has_sum=True, has_mean=False, unit_of_measurement='Kč')
    eur_rate_meta = StatisticMetaData(statistic_id='cnb:eur_rate', source='cnb', name='EUR/CZK rate', has_sum=False, has_mean=True, unit_of_measurement='Kč/€')
    async_add_external_statistics(hass, income_meta, income_stats)
    async_add_external_statistics(hass, eur_rate_meta, [StatisticData(start=as_utc(datetime.combine(yesterday - timedelta(days=1), time.min, tzinfo=DEFAULT_TIME_ZONE)), mean=eur_rate, min=eur_rate, max=eur_rate)])
    log.info(f'Added {len(income_stats)} income, and 1 eur rate stats for {yesterday}')

