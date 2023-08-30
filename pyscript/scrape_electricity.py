import requests
from datetime import date, datetime, time, timedelta
from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.models import StatisticMetaData, StatisticData
from homeassistant.components.recorder.statistics import async_add_external_statistics, get_last_statistics, statistics_during_period
from homeassistant.components.recorder.history import get_significant_states
from homeassistant.util.dt import now, as_utc, as_local, DEFAULT_TIME_ZONE
from bisect import bisect_right
from itertools import islice

CNB_EUR_PRICE_URL_PATTERN = 'https://www.cnb.cz/cs/financni-trhy/devizovy-trh/kurzy-devizoveho-trhu/kurzy-devizoveho-trhu/vybrane.txt?od={}&do={}&mena=EUR&format=txt'
OTE_SPOT_ELE_PRICE_URL_PATTERN = 'https://www.ote-cr.cz/cs/kratkodobe-trhy/elektrina/denni-trh/@@chart-data?report_date={}'
EXPORT_ENTITY_ID = 'sensor.meter_total_energy_export'
ELE_PRICE_STAT_ID = 'ote:electricity_price'
ELE_PRICE_SOURCE = 'ote'
PV_INCOME_STAT_ID = 'ote:pv_income'
PV_INCOME_SOURCE = 'ote'
EUR_RATE_STAT_ID = 'cnb:eur_rate'
EUR_RATE_SOURCE = 'cnb'
EXPORT_LIMIT_ENTITY_ID = 'number.grid_export_limit'
EXPORT_LIMIT_MAX = '6000.0'

DAY_DELTA = timedelta(days=1)


def get_eur_rate(day: date) -> float|None:
    from_day_str = (day - timedelta(days=2)).strftime('%d.%m.%Y')
    day_str = day.strftime('%d.%m.%Y')
    url = CNB_EUR_PRICE_URL_PATTERN.format(from_day_str, day_str)
    resp = http_get(url)
    if resp.status_code == 200:
        line = resp.text.strip().split('\n')[-1].strip().split('|')
        log.info(f'Read EUR rate from CNB of {line[1]} on {line[0]}')
        return float(line[1].replace(',', '.'))
    else:
        log.warning(f'Failed to get EUR rate for URL={url}, status={resp.status_code}')
        return None


def get_power(day: date, hours_overlap: int = 6):
    dt = day_with_hour_utc(day, hour=0)
    states = await get_instance(hass).async_add_executor_job(
        get_significant_states,
        hass,
        dt - timedelta(hours=hours_overlap),
        dt + timedelta(days=1, hours=hours_overlap),
        [EXPORT_ENTITY_ID],
        None,   # filters
        True,   # include_start_time_state
        True,   # significant_changes_only
        False,  # minimal_response
        True,   # no_attributes
        False,  # compressed_state_format
    )
    points = {s.last_changed: float(s.state) for s in states[EXPORT_ENTITY_ID]}
    log.info(f'Read {len(points)} power points from sensor')
    return points


def get_prices(day: date):
    url = OTE_SPOT_ELE_PRICE_URL_PATTERN.format(day.isoformat())
    resp = http_get(url)
    if resp.status_code != 200:
        log.warning(f'Reading electricity prices for {url} failed: {resp.status_code}')
        return None
    else:
        data = resp.json()
        points = {(int(d['x']) - 1): float(d['y']) for d in data['data']['dataLine'][1]['point']}
        log.info(f'Read {len(points)} electricity prices from OTE')
        return points


@event_trigger('scrape_electricity_price')
def scrape_electricity_price():
    tomorrow = now().date() + DAY_DELTA
    prices = get_prices(tomorrow)
    stats = [StatisticData(start=day_with_hour_utc(tomorrow, h), mean=p, min=p, max=p) for h, p in prices.items()]
    meta = StatisticMetaData(statistic_id=ELE_PRICE_STAT_ID, source=ELE_PRICE_SOURCE, name='Electricity price', has_sum=False, has_mean=True, unit_of_measurement='€/MWh')
    async_add_external_statistics(hass, meta, stats)
    log.info(f'Added {len(stats)} electricity prices for {tomorrow}')


def get_last_income_sum(yesterday: date):
    last_income_stats = await get_instance(hass).async_add_executor_job(
        get_last_statistics,
        hass,
        1,
        PV_INCOME_STAT_ID,
        False,
        {"sum"},
    )
    if len(last_income_stats) == 0:
        log.error('Starting income from zero? Better not saving!!!')
        raise Exception("No last income!")
    lis = last_income_stats[PV_INCOME_STAT_ID][0]
    last_income_date = datetime.fromtimestamp(lis['end'])
    assert last_income_date <= datetime.combine(yesterday, time.min), f"Last income sum is newer than what we are reading! last income date={last_income_date}, yesterday={yesterday}"
    income_sum = lis['sum']
    log.info(f'Read last income sum = {income_sum}')
    return income_sum


def get_prices_stats(start: datetime, end: datetime):
    stats = await get_instance(hass).async_add_executor_job(
        statistics_during_period,
        hass,
        start,
        end,
        {ELE_PRICE_STAT_ID},
        "hour",
        None,
        {"mean"},
    )
    if ELE_PRICE_STAT_ID not in stats:
        raise Exception(f'No electricity price stat found from {start.isoformat()} - {end.isoformat()}')
    prices = {i: s['mean'] for i, s in enumerate(stats[ELE_PRICE_STAT_ID])}
    log.info(f'Read {len(prices)} prices stats from {start.isoformat()} - {end.isoformat()}')
    return prices


@event_trigger('scrape_electricity')
def scrape_electricity():
    yesterday = now().date() - DAY_DELTA

    yesterday_dt = day_with_hour_utc(yesterday, hour=0)
    prices = get_prices_stats(yesterday_dt, yesterday_dt + DAY_DELTA)

    day_bef_yesterday = yesterday - DAY_DELTA
    eur_rate = get_eur_rate(day_bef_yesterday)
    store_eur_rate(eur_rate, day_bef_yesterday)

    power = get_power(yesterday)
    i = 0
    power_dates = [as_local(d) for d in power.keys()]
    power_values = list(power.values())
    powers = {}
    for h in range(25):
        i = bisect_right(power_dates, day_with_hour_utc(yesterday, hour=0) + timedelta(hours=h), lo=i)
        if i == 0:
            continue
        if i >= len(power_dates):
            break
        powers[h] = power_values[i-1]
        log.debug((h, i, power_dates[i-1], power_values[i-1]))
    if len(powers) < 2:
        log.warning(f'There is only {len(powers)} hourly powers, not enough to compute diffs!')
        return
    power_diffs = {h: (p2 - p1) for (h, p1), p2 in zip(powers.items(), islice(powers.values(), 1, None))}
    log.info(f'Reduced power to {len(power_diffs)} hours')

    income_stats = []
    income_sum = get_last_income_sum(yesterday)
    for h in range(24):
        if h in prices and h in power_diffs:
            income = prices[h] * power_diffs[h] * eur_rate / 1000
            income_sum += income
            income_stats.append(StatisticData(start=day_with_hour_utc(yesterday, h), state=income, sum=income_sum))

    income_meta = StatisticMetaData(statistic_id=PV_INCOME_STAT_ID, source=PV_INCOME_SOURCE, name='PV export income', has_sum=True, has_mean=False, unit_of_measurement='Kč')
    async_add_external_statistics(hass, income_meta, income_stats)
    log.info(f'Added {len(income_stats)} income stats for {yesterday}')


@event_trigger('adjust_electricity_export')
def adjust_electricity_export():
    start = now().replace(minute=0, second=0, microsecond=0)
    price = get_prices_stats(start, start + timedelta(hours=1))
    if price[0] < 0:
        log.info(f'Current electricity price is {price[0]}, disabling export')
        hass.states.async_set(EXPORT_LIMIT_ENTITY_ID, '0.0')
    else:
        hass.states.async_set(EXPORT_LIMIT_ENTITY_ID, EXPORT_LIMIT_MAX)


def store_eur_rate(eur_rate: float, day: date):
    eur_rate_meta = StatisticMetaData(statistic_id=EUR_RATE_STAT_ID, source=EUR_RATE_SOURCE, name='EUR/CZK rate', has_sum=False, has_mean=True, unit_of_measurement='Kč/€')
    async_add_external_statistics(hass, eur_rate_meta, [StatisticData(start=day_with_hour_utc(day, hour=0), mean=eur_rate, min=eur_rate, max=eur_rate)])
    log.info(f'Added eur rate {eur_rate} stat for {day}')


def day_with_hour_utc(day: date, hour: int) -> datetime:
    return as_utc(datetime.combine(day, time(hour, 0, 0), tzinfo=DEFAULT_TIME_ZONE))


def http_get(url: str) -> requests.Response:
    resp = await hass.async_add_executor_job(requests.get, url)
    return resp
