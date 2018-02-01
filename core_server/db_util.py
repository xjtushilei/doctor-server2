#!/usr/bin/env python3
# coding:utf8

from pymongo import MongoClient


class Mongo:
    def __init__(self, app_config):
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

        self.info_log = self.db.get_collection("info")

        self.error_log = self.db.get_collection("error")

        self.unknow_error_log = self.db.get_collection("unknow_error")

    def info(self, item):
        self.info_log.insert(item)

    def error(self, item):
        self.error_log.insert(item)

    def unknow_error(self, item):
        self.unknow_error_log.insert(item)
