from pymongo import MongoClient


class Mongo:
    def __init__(self, host="127.0.0.1", port=27017, db_name="intelligent_triage"):
        # 建立数据库连接
        self.client = MongoClient(host=host, port=port)
        # 选择相应的数据库名称
        self.db = self.client.get_database(db_name)

        self.info_log = self.db.get_collection("info")
        self.error_log = self.db.get_collection("error")
        self.unknow_error_log = self.db.get_collection("unknow_error")

    def info(self, item):
        self.info_log.insert(item)

    def error(self, item):
        self.error_log.insert(item)

    def unknow_error(self, item):
        self.unknow_error_log.insert(item)
