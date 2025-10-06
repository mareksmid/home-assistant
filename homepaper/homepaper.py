#!/usr/bin/python3

#waveshare_epd/epdconfig.py 
#waveshare_epd/epd3in52.py 
#cp e-Paper/RaspberryPi_JetsonNano/python/pic/100x100.bmp .
#waveshare_epd/epd3in52.py 
#sudo pip3 install pyppeteer


from waveshare_epd import epd3in52
import time
from PIL import Image
import asyncio
from pyppeteer import launch
import logging

url = 'https://hass.mareksmid.cz/dash-dash/0'
image_path = '/dev/shm/hass.png'
zoom = 1
interval = 120
logger = logging.getLogger('homepaper')


async def start():
    browser = await launch(headless=True, executablePath='/usr/bin/chromium-browser', args=['--no-sandbox', '--disable-gpu', '--hide-scrollbars'])
    page = await browser.newPage()
    await page.setViewport({'width': 360*zoom, 'height': 240*zoom, 'deviceScaleFactor': 1/zoom})
    page.setDefaultNavigationTimeout(30000)
    return browser, page


async def disp(epd, page):
    await page.goto(url, {'waitUntil': 'networkidle2'})
    time.sleep(30)
    await page.screenshot({'path': image_path})
    image = Image.open(image_path)
    epd.display(epd.getbuffer(image))
    epd.lut_GC()
    epd.refresh()
    time.sleep(interval)


async def work(epd):
    try:
        browser, page = await start()
        while True:
            await disp(epd, page)
        await browser.close()
    except Exception as ex:
        logger.warning(f"Failed: {ex}")
        exit(1)


if __name__ == '__main__':
    epd = epd3in52.EPD()
    epd.init()
    epd.display_NUM(epd.WHITE)
    epd.lut_GC()
    epd.refresh()

    epd.send_command(0x50)
    epd.send_data(0x17)
    
    asyncio.get_event_loop().run_until_complete(work(epd))
    
    epd.Clear()
    epd.sleep()
    epd3in52.epdconfig.module_exit(cleanup=True)
