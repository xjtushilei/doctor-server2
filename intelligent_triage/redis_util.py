#!/usr/bin/env python3
# coding:utf8

import redis

pool = redis.ConnectionPool(host='127.0.0.1', port=6379)
r = redis.Redis(connection_pool=pool)
r.set('name', 'zhangsan')  # 添加
r.set('name1', '22')  # 添加
for x in r.keys():
    print(r.get(x))
