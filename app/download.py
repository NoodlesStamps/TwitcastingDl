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
import threading

import msal
from office365.graph_client import GraphClient


logging.basicConfig(level=logging.INFO,
                    format="[%(levelname)s] [%(asctime)s] %(message)s",
                    datefmt='%Y-%m-%d %H:%M:%S'
                    )


class TwitcastingDl:

    ua = ""
    cookie = ""
    local_file_length = 0

    def __init__(self, twitcasting_url, onedrive_tenant_id, onedrive_client_id, onedrive_client_secret, onedrive_user_email):
        self.twitcasting_url = twitcasting_url
        if self.twitcasting_url is None:
            logging.error("no twitcasting url")
            sys.exit(-1)
        logging.info("set url to %s" % self.twitcasting_url)
        match = re.search(
            r'https://twitcasting\.tv/(.*)/movie/(.*)', self.twitcasting_url)
        if not match:
            logging.info("not twitcasting video url")
            sys.exit(-1)
        self.user_id = match.group(1)
        self.video_id = match.group(2)
        self.onedrive_tenant_id = onedrive_tenant_id
        self.onedrive_client_id = onedrive_client_id
        self.onedrive_client_secret = onedrive_client_secret
        self.onedrive_user_email = onedrive_user_email

    def __acquire_onedrive_token(self):
        authority_url = f'https://login.microsoftonline.com/{self.onedrive_tenant_id}'
        app = msal.ConfidentialClientApplication(
            authority=authority_url,
            client_id=f'{self.onedrive_client_id}',
            client_credential=f'{self.onedrive_client_secret}'
        )
        token = app.acquire_token_for_client(
            scopes=["https://graph.microsoft.com/.default"])

        return token

    def __upload_progress(self, range_pos):
        if self.local_file_length - range_pos <= 1000000:
            print("Uploaded ")
        else:
            print("Uploading %s" % round(
                  range_pos/self.local_file_length*100, 2))

    def get_video_urls(self):
        logging.info("start webdriver")
        options = webdriver.EdgeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Remote("127.0.0.1:9515", options=options)
        logging.info("open twitcasting page")
        driver.get(self.twitcasting_url)
        time.sleep(1)
        driver.refresh()
        time.sleep(1)
        logging.info("get browser ua")
        self.ua = driver.execute_script("return navigator.userAgent")
        logging.info("set ua to %s" % self.ua)
        logging.info("get cookie")
        self.cookie = driver.execute_script("return document.cookie")
        logging.info("set cookie to %s" % self.cookie)
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
        self.video_urls = urls

        return urls

    def download_and_upload_video(self, url, code=1):
        logging.info("[%s]start download %s" % (code, url))
        response = requests.get(url, headers={
            'Cookie': self.cookie,
            'Origin': 'https://twitcasting.tv',
            'Referer': 'https://twitcasting.tv/',
            'User-Agent': self.ua
        })
        if response.status_code != 200:
            logging.error("[%s]get real video fail %s" %
                          (code, response.status_code))
            return
        content = response.content.decode('utf8')
        if "Bad" in content:
            logging.error("[%s]get real video fail %s" % (code, content))
            return
        url_data = urlparse(url)
        media_url = url_data.scheme+"://"+url_data.netloc+content.split()[-1]
        output = "%s_%s_%s" % (self.user_id, self.video_id, code)
        logging.info("[%s]start download video stream" % code)
        subprocess.run(['minyami', '-d', '%s' % media_url, '--output', '%s.ts' % output, '--headers', 'Referer: https://twitcasting.tv/',
                       '--headers', 'User-Agent: %s' % self.ua, '--threads 3'], capture_output=False, check=True)
        logging.info("[%s]download success" % code)
        logging.info("[%s]start fix video stream" % code)
        subprocess.run(['mkvmerge', '--output', '%s.mkv' % output, '--language', '0:und', '--fix-bitstream-timing-information', '0:1',
                       '--language', '1:und', '%s.ts' % output, '--track-order', '0:0,0:1'], capture_output=False, check=True)
        logging.info("[%s]fix success" % code)
        os.remove('%s.ts' % output)
        logging.info("[%s]format video to mp4" % code)
        subprocess.run(['ffmpeg', '-i', '%s.mkv' % output, '-c:v', 'copy', '-c:a',
                       'copy', 'output/%s.mp4' % output], capture_output=False, check=True)
        logging.info("[%s]format success" % code)
        os.remove('%s.mkv' % output)
        filepath = "output/%s.mp4" % output
        filelength = 0
        with open(filepath, "rb") as f:
            filelength = len(f.read())
        logging.info("[%s]download finished %s size:%s" %
                     (code, output, filelength))
        logging.info("[%s]upload to onedrive" % code)
        client = GraphClient(self.__acquire_onedrive_token)
        file_item = client.users[self.onedrive_user_email].drive.root.get_by_path(
            "/downloads").resumable_upload(filepath, chunk_uploaded=self.__upload_progress).execute_query()
        logging.info("[%s]upload success" % code)
        os.remove(filepath)

    def run(self):
        urls = self.get_video_urls()

        count = 1
        for url in urls:
            logging.info("start video %s" % count)
            threading.Thread(target=self.download_and_upload_video,
                             args=(url, count,)).start()
            time.sleep(5)
            count += 1


if __name__ == "__main__":
    tc = TwitcastingDl(
        os.getenv("TWITCASTING_URL"), os.getenv(
            "ONEDRIVE_TENANT_ID"), os.getenv("ONEDRIVE_CLIENT_ID"),
        os.getenv("ONEDRIVE_CLIENT_SECRET"), os.getenv("ONEDRIVE_USER_EMAIL"))
    tc.run()
