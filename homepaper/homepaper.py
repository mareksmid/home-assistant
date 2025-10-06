#!/usr/bin/python3

#waveshare_epd/epdconfig.py
#waveshare_epd/epd3in52.py
#cp e-Paper/RaspberryPi_JetsonNano/python/pic/100x100.bmp .
#waveshare_epd/epd3in52.py

import os
from waveshare_epd import epd3in52
import time
from PIL import Image, ImageFont, ImageDraw
import requests
import asyncio

STATES_URL = 'https://hass.mareksmid.cz/api/states/'
INTERVAL_SECS = 30
TOKEN = os.environ['HASS_TOKEN']


def get_state(entity_id: str, attribute: str = None, unit: str = None):
    resp = requests.get(STATES_URL + entity_id, headers={"Authorization": f"Bearer {TOKEN}"})
    if resp.status_code == 200:
        data = resp.json()
        if unit is None:
            unit = data['attributes']['unit_of_measurement']
        if attribute is None:
            value = data['state']
        else:
            value = data['attributes'][attribute]
        return f"{value} {unit}"
    else:
        return '---'


def fetch():
    return {
        'Venkovni teplota': get_state('sensor.temperature_out_temperature'),
        'Vnitrni teplota': get_state('sensor.temperature_in_temperature'),
        'Termostat pro kotel':  get_state("climate.dum", "current_temperature", "°C"),  # icon: mdi:thermometer
        'Hladina': get_state('sensor.hladina'), # icon: mdi:water
        'Ele. vyroba': get_state('sensor.pv_power'),
        'Ele. spotreba': get_state('sensor.house_consumption'),
        'Ele. dnes vyrobeno': get_state('sensor.today_s_pv_generation'),
        'Baterie': get_state('sensor.battery_state_of_charge'),
        'Wallbox vykon': get_state('sensor.wallbox2_copper_business_sn_443968_nabijeci_vykon'),
    }

async def disp(epd, data: dict[str, str]) -> None:
    image = Image.new('1', (360, 240), 1) # 'RGB', (360, 240), (255, 255, 255)
    fnt = ImageFont.truetype("/usr/local/share/fonts/v/VCR_OSD_MONO_1.001.ttf", 21)
    d = ImageDraw.Draw(image)
    for i, (label, value) in enumerate(data.items()):
        y = 2 + i * 24
        d.text((2, y), label, font=fnt, fill=0)
        d.text((250, y), value, font=fnt, fill=0)
    # image.save('x.png')
    epd.display(epd.getbuffer(image))
    epd.lut_GC()
    epd.refresh()
    time.sleep(INTERVAL_SECS)


async def work(epd):
    while True:
        data = fetch()
        await disp(epd, data)


if __name__ == '__main__':
    epd = epd3in52.EPD()
    epd.init()
    epd.display_NUM(epd.WHITE)
    epd.lut_GC()
    epd.refresh()

    epd.send_command(0x50)
    epd.send_data(0x17)
    asyncio.run(work(epd))
    
    epd.Clear()
    epd.sleep()
    epd3in52.epdconfig.module_exit(cleanup=True)
