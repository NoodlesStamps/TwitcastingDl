#!/bin/bash
cd /root/app
nohup /usr/bin/Xvfb :99 -ac -screen 0 1280x960x24 > Xvfb.log &
nohup /usr/bin/msedgedriver --verbose > msedgedriver.log &
python3 download.py