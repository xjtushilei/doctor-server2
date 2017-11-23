#!/bin/bash

local_ip=`/sbin/ifconfig eth1|grep "inet addr:"|cut -d: -f 2|cut -d" " -f1`
BASEDIR=`cd "$(dirname "$0")"; cd ..;  pwd `

py_bin="/usr/bin/python3.4"

APP="sl_guangdu_tongji"

uid=`id -u`
if [ "$uid" -ne  0 ]; then
	
	###停止服务
	/bin/bash $BASEDIR/script/kill.sh
	sleep 1
	###启动服务
    $py_bin  $BASEDIR/server.py $BASEDIR/conf/app_config_prod.yaml $BASEDIR/conf/logger_prod.conf &
else
    
	echo "ERROR: root is not allowed to start service!"

fi
