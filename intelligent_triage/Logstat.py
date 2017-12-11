#!/usr/local/app/python3.5.1/bin/python3
# -*- coding: utf-8 -*-
#
import socket
import struct
import time
import random
import re

class logstat():
    def __init__(self):
        self.connect = self.get_connect()
        self.lastime = time.time()
        self.lastcount = 0

    def get_connect(self):
        sc = 0
        servers = self.get_logstat_server()
        if len(servers) > 0:
            sc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            for i in range(5):
                one = random.randint(0,len(servers)-1)
                ip,port = servers[one].split(':')
                try:
                    sc.connect((ip,int(port)))
                    break
                except Exception as e:
                    print(e)
        else:
            print("can't get logstatNoTafObj from logclient.conf !!! please rtx hansli")
        return sc

    def close(self):
        self.lastime = time.time()
        self.lastcount = 0
        if self.connect != 0:
            try:
                self.connect.close()
            except Exception as e:
                print(e)
        else:
            print('Connection closed')

    def get_logstat_server(self):
        servers = []
        with open ('/usr/local/support/conf/logclient.conf','r') as f:
            for line in f.readlines():
                line = re.sub(" +", " ", line)
                if line.find('=') != -1:
                    name,ipport = line.split('=')
                    if name == 'logstatNoTafObj':
                        servers = ipport.split(';')
                        return servers
        return servers

    def send(self, logname, text):
        ver = 200
        cmd = 1
        ftime = 1
        logname = logname.encode('utf-8')
        loglen = len(logname)
        text = text.encode('utf-8')
        txlen = len(text)
        allen = 12 + loglen + txlen + 4
        msg = struct.pack(">Ihhih%dsh%ds" % (loglen,txlen), allen,ver,cmd,ftime,loglen,logname,txlen,text)
        now_time = time.time()
        if self.connect != 0 and now_time - self.lastime < 0.1 and self.lastcount < 10000:
            result = self.connect.send(msg)
            self.lastime = now_time
            self.lastcount += 1
            #print('result=',result)
        else:
            self.close()
            self.connect = self.get_connect()
            if self.connect != 0:
                result = self.connect.send(msg)


if __name__ == '__main__':
    slog = logstat()
    for i in range(10000):
        slog.send('hanstest13','aa|ss|dd|ff|gg|13')
