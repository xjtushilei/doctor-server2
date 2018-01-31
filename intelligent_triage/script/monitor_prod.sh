#!/bin/sh
PATH=/usr/local/bin:/bin:/usr/bin:/usr/local/sbin:/usr/sbin:/sbin

####################补充监控进程需要执行的操作####################
export LANG=en_US.utf-8
exist=`killall -0 python;echo $?`

IP=$(ifconfig $1|sed -n 2p)
if [ $exist -ne 0 ]
then
	echo $IP
	echo "restart"
	sh /cfs_chengdu/finddoctor/sh/start_prod.sh	
fi
echo "exist="$exist$IP
