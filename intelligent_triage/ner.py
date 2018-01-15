# coding=utf-8

import requests
import time


def post(content, userID="jerryz"):
    body = {
        "version": '1.0',
        "text": content,
        "userId": userID
    }
    start_time = time.time()
    try:
        resp = requests.post("http://walleai_nlu.ext.wsd.com/nlu", json=body, timeout=0.01).json()
        nerList = resp["reply"]["ner_norms"]
        slots = resp["reply"]["slots"]
        result = []
        for w in nerList:
            result.extend(w.split("-"))
        for l in slots.values():
            result.extend(l[0:2])
        result = list(set(result))
        return result, resp, str(1000*(time.time() - start_time)).split('.')[0]
    except Exception:
        return [], "超时（250ms）或者json解析错误", str(1000*(time.time() - start_time)).split('.')[0]