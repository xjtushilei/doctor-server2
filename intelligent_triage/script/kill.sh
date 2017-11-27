#!/bin/bash
local_ip=`/sbin/ifconfig eth1|grep "inet addr:"|cut -d: -f 2|cut -d" " -f1`
BASEDIR=`cd "$(dirname "$0")"; cd ..;  pwd `

####################补充停止进程需要执行的操作####################


killall -9 python3.4
