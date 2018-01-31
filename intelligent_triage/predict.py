# coding=utf-8

import time

import requests


# 返回结果，超时时间，结果是否可以用
def get(all_choice, all_choices, age, gender, k_disease, k_recommendation_symtom, sessionId, userId, seqno, url):
    data = {
        "session_id": sessionId,
        "user_id": userId,
        "seqno": seqno,
        "gender": gender,
        "age": age,
        "k_disease": k_disease,
        "k_recommendation_symtom": k_recommendation_symtom,
        "all_choice": all_choice,
        "all_choices": all_choices
    }
    start_time = time.time()
    try:
        # 最长等待5秒，不返回，则人为没有匹配到疾病
        resp = requests.post(url, json=data, timeout=5)
        result = resp.json()
        time_consuming = round(1000 * (time.time() - start_time), 3)
        return result, time_consuming, resp.ok
    except Exception:
        time_consuming = round(1000 * (time.time() - start_time), 3)
        return None, time_consuming, False

#
# result, time_consuming, ok=get("乏力,头疼,", 11.12312312, "female", 5, 5, "12", "userid", 1, "http://127.0.0.1:8082/v1/predict")
#
# print(type(result["rate"][0]))
