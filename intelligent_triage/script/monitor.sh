#!/bin/sh
local_ip=`/sbin/ifconfig eth1|grep "inet addr:"|cut -d: -f 2|cut -d" " -f1`
BASEDIR=`cd "$(dirname "$0")"; cd ..;  pwd `


####################补充监控进程需要执行的操作####################

exist=`killall -0 python;echo $?`


if [ $exist -ne 0 ]
then
	cd $BASEDIR/script
	echo "restart"
	./start.sh
	/data/syos/common/smsproxy joecao jerryzliu"intelligent triage start from[$local_ip]"
	wget -q -O /dev/null -T10  "http://10.198.139.178:8080/SendEmail.do?name=g_td_BPC_BE&msg=intelligent_triage start&"
fi
echo "exist="$exist
