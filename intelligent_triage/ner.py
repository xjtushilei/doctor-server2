# coding=utf-8

import re
import time

import requests


def post(content, userID="jerryz"):
    body = {
        "version": '1.0',
        "text": content,
        "userId": userID
    }
    start_time = time.time()
    try:
        resp = requests.post("http://172.27.0.6:8802/nlu", json=body, timeout=0.75).json()
        nerList = resp["reply"]["ner_norms"]
        slots = resp["reply"]["slots"]
        result = []
        for w in nerList:
            result.extend(re.split("[-|,]", w))
        for l in slots.values():
            result.extend(l[0:2])
        result = list(set(result))
        time_consuming = round(1000 * (time.time() - start_time), 3)
        return result, resp, time_consuming
    except Exception:
        time_consuming = round(1000 * (time.time() - start_time), 3)
        return [], "超时（250ms）或者json解析错误", time_consuming
