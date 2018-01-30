#!/bin/bash
export LANG=en_US.utf-8
killall -9  python
sleep 2
source /home/dev/.py3/bin/activate
cd /cfs_chengdu/finddoctor/py/prod/intelligent_triage/
nohup python server.py conf/app_config_server_prod.json &
