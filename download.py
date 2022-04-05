from selenium import webdriver

import logging
import time
import sys

logging.basicConfig(level=logging.INFO,
                    format="[%(levelname)s] [%(asctime)s] %(message)s",
                    datefmt='%Y-%m-%d %H:%M:%S'
                    )


logging.info("start webdriver")
options = webdriver.EdgeOptions()
#options.add_argument("--proxy-server=http://192.168.2.2:7890")
driver = webdriver.Remote("127.0.0.1:9515", options=options)
#driver = webdriver.Chrome()

logging.info("open twitcasting page")
driver.get('https://twitcasting.tv/cordelia_yurica/movie/717476623')
time.sleep(1)

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

if len(url) == 0:
    logging.error("no media found")
    sys.exit()

