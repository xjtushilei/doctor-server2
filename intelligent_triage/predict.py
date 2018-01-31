# coding=utf-8

import time

import requests


# 返回结果，超时时间，结果是否可以用
def get(input, age, gender, k_disease, k_symptom, sessionId, userId, seqno, url):
    params = {
        "input": input,
        "age": age,
        "gender": gender,
        "k_disease": k_disease,
        "k_symptom": k_symptom,
        "sessionId": sessionId,
        "userId": userId,
        "seqno": seqno
    }
    start_time = time.time()
    try:
        # 最长等待5秒，不返回，则人为没有匹配到疾病
        resp = requests.get(url, params=params, timeout=5)
        result = resp.json()
        time_consuming = round(1000 * (time.time() - start_time), 3)
        return result, time_consuming, resp.ok
    except Exception:
        time_consuming = round(1000 * (time.time() - start_time), 3)
        return None, time_consuming, False


print(get("乏力,头疼,", 11.12312312, "female", 5, 5, "12", "userid", 1, "http://127.0.0.1:8082/v1/predict"))
