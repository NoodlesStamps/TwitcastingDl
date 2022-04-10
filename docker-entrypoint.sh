#!/bin/bash
/usr/bin/supervisord
sleep 5
python3 download.py