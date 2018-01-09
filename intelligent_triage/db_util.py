#!/usr/bin/env python3
# coding:utf8

import redis
from pymongo import MongoClient


class RedisCache(object):

    def __init__(self, app_config):
        self.app_config = app_config
        if not hasattr(RedisCache, 'pool'):
            RedisCache.create_pool(app_config)
        self._connection = redis.Redis(connection_pool=RedisCache.pool)

    @staticmethod
    def create_pool(app_config):
        if app_config["DB"]["redis"]["auth"]:
            RedisCache.pool = redis.ConnectionPool(
                host=app_config["DB"]["redis"]["host"],
                port=app_config["DB"]["redis"]["port"],
                db=app_config["DB"]["redis"]["DBID"],
                password=app_config["DB"]["redis"]["passwd"])
        else:
            RedisCache.pool = redis.ConnectionPool(
                host=app_config["DB"]["redis"]["host"],
                port=app_config["DB"]["redis"]["port"],
                db=app_config["DB"]["redis"]["DBID"])

    def get_connection(self):
        return self._connection

    def set_data(self, key, value):
        """
        set data with (key, value)
        """
        return self._connection.set(key, value)

    def get_data(self, key):
        """
        get data by key
        """
        return self._connection.get(key)

    def del_data(self, key):
        """
        delete cache by key
        """
        return self._connection.delete(key)


class Mongo:
    def __init__(self, app_config, prod=True):
        # 建立数据库连接
        self.client = MongoClient(host=app_config["DB"]["mongodb"]["host"], port=app_config["DB"]["mongodb"]["port"])
        # 选择相应的数据库名称
        if app_config["DB"]["mongodb"]["auth"]:
            self.db = self.client.get_database("admin")
            self.db.authenticate(name=app_config["DB"]["mongodb"]["user"],
                                 password=app_config["DB"]["mongodb"]["passwd"])
            self.db = self.client.get_database(app_config["DB"]["mongodb"]["db_name"])
        else:
            self.db = self.client.get_database(app_config["DB"]["mongodb"]["db_name"])

        if prod:
            self.recordCollection = self.db.get_collection("record")
        else:
            self.recordCollection = self.db.get_collection("record_test")
        if prod:
            self.info_log = self.db.get_collection("info")
        else:
            self.info_log = self.db.get_collection("info_test")

        if prod:
            self.error_log = self.db.get_collection("error")
        else:
            self.error_log = self.db.get_collection("error_test")

        if prod:
            self.unknow_error_log = self.db.get_collection("unknow_error")
        else:
            self.unknow_error_log = self.db.get_collection("unknow_error_test")

    def record(self, item):
        self.recordCollection.insert(item)

    def info(self, item):
        self.info_log.insert(item)

    def error(self, item):
        self.error_log.insert(item)

    def unknow_error(self, item):
        self.unknow_error_log.insert(item)
