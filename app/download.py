from selenium import webdriver
from urllib.parse import urlparse

import logging
import time
import sys
import json
import subprocess
import os
import requests
import re


logging.basicConfig(level=logging.INFO,
                    format="[%(levelname)s] [%(asctime)s] %(message)s",
                    datefmt='%Y-%m-%d %H:%M:%S'
                    )

twitcasting_url = os.getenv("TWITCASTING_URL")

if twitcasting_url is None:
    logging.error("no twitcasting url")
    sys.exit(-1)

logging.info("set url to %s"%twitcasting_url)

match = re.search(r'https://twitcasting\.tv/(.*)/movie/(.*)', twitcasting_url)
if not match:
    logging.info("not twitcasting video url")
    sys.exit(-1)

user_id = match.group(1)
video_id = match.group(2)

logging.info("start webdriver")
driver = webdriver.Remote("127.0.0.1:9515")

logging.info("open twitcasting page")
driver.get(twitcasting_url)
time.sleep(1)
driver.refresh()
time.sleep(1)

logging.info("get browser ua")
ua = driver.execute_script("return navigator.userAgent")
logging.info("set ua to %s" % ua)

logging.info("get cookie")
cookie = driver.execute_script("return document.cookie")
logging.info("set cookie to %s" % cookie)


logging.info("get media urls")
get_url_js = """
let urls = []; 
for (let _ of JSON.parse(document.querySelector("video")["dataset"]["moviePlaylist"])[2]) urls.push(_.source?.url); 
let content = ""
urls.forEach(url=>{
    content += `<p>${url}</p>`
})
document.body.innerHTML = content
"""
driver.execute_script(get_url_js)
time.sleep(1)


urls = []

for p in driver.find_elements(webdriver.common.by.By.TAG_NAME, 'p'):
    url = p.text
    logging.info("got media %s" % url)
    urls.append(url)

logging.info("close wedriver")
driver.close()

if len(url) == 0:
    logging.error("no media found")
    sys.exit(-1)

c = 1
for url in urls:
    logging.info("[%s/%s]start download %s" % (c, len(urls), url))
    response = requests.get(url, headers={
        'Cookie': cookie,
        'Origin': 'https://twitcasting.tv',
        'Referer': 'https://twitcasting.tv/',
        'User-Agent': ua
    })
    if response.status_code != 200:
        logging.error("get real video fail %s" % response.status_code)
        continue
    content = response.content.decode('utf8')
    if "Bad" in content:
        logging.error("get real video fail %s" % content)
        continue
    url_data = urlparse(url)
    media_url = url_data.scheme+"://"+url_data.netloc+content.split()[-1]
    output = "%s_%s_%s" % (user_id, video_id, c)
    logging.info("start download video stream")
    download_command = 'minyami -d "%s" --output "%s.ts" --headers "Referer: https://twitcasting.tv/" --headers "User-Agent: %s" --threads 3' % (
        media_url, output, ua)
    os.system(download_command)
    logging.info("start fix video stream")
    fix_command = 'mkvmerge --output %s.mkv --language 0:und --fix-bitstream-timing-information 0:1 --language 1:und %s.ts --track-order 0:0,0:1' % (
        output, output)
    os.system(fix_command)
    logging.info("format video to mp4")
    format_command = 'ffmpeg -i %s.mkv -c:v copy -c:a copy output/%s.mp4' % (
        output, output)
    os.system(format_command)
    logging.info("finished")
