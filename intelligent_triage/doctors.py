# 医生模型的获取医生信息
import time

import requests


def get_doctors(codes, probs, age, gender, query_hospital_url, query_hospital_id, model,
                orgId=None, clientId=None, branchId=None, appointment=None, debug=False):
    prob_threshold = 0.5
    gender_threshold = 0.05

    if 0 < age <= 1:
        age_index = 0
    elif 1 < age <= 18:
        age_index = 1
    elif 18 < age <= 120:
        age_index = 2
    else:
        return []
    agename = ["age01", "age0118", "age18"]

    if gender in ["M", "男", "male"]:
        gender_index = 0
    elif gender in ["F", "女", "female"]:
        gender_index = 1
    else:
        return []

    # get the query list of doctors
    doctors_query = {}
    doctors_query["doctors"] = []
    for code, prob in zip(codes, probs):
        if (prob >= prob_threshold) and (code in model[agename[age_index]].keys()) and (
                    model[agename[age_index]][code]["gender"][gender_index] >= gender_threshold):
            for item in model[agename[age_index]][code]["doctors"]:
                item["registration"] = True
                doctors_query["doctors"].append({"docId": item["id"], "departmentId": item["departmentId"]})

    # rank doctors according to schedules
    # import datetime
    # today_date = datetime.date.today() ##2018-01-15
    doctors_recommendation = []

    # 如果是测试环境，直接返回结果
    if orgId == "testorg":
        tempdocs = {
            "doctors": [
                {
                    "docId": "410",
                    "departmentId": "10001"
                }
            ]
        }
        doctors_schedule, time_consuming, ok = query_doctors(tempdocs, query_hospital_id, query_hospital_url, debug)
        if ok:
            for item in doctors_schedule["doctors"]:
                temp = {}
                for key, value in item.items():
                    # 去掉这个字段
                    if key != "schedule":
                        temp[key] = value
                doctors_recommendation.append(temp)
            return doctors_recommendation, True
        else:
            return None, False
    # 非测试环境，丽娟进行推荐医生
    else:
        doctors_schedule, time_consuming, ok = query_doctors(doctors_query, query_hospital_id,
                                                             query_hospital_url, debug)
        if ok:
            if doctors_schedule["status"] == "ok":
                doctors_info = doctors_schedule["doctors"]
                for item1 in doctors_query:
                    flag = False
                    for item2 in doctors_info:
                        if item2["docId"] == item1["id"]:
                            for schedule in item2["schedule"]:
                                if schedule["available"] > 0:
                                    flag = True
                                    break
                            if flag == True:
                                temp = {}
                                for key, value in item2.items():
                                    if key != "schedule":
                                        temp[key] = value
                                doctors_recommendation.append(temp)
        else:
            return None, False
        return doctors_recommendation, True


def query_doctors(doctors, hospital_id, url, debug=False):
    url = url + hospital_id

    start_time = time.time()
    try:
        temp = requests.post(url, json=doctors, timeout=25)
        doctors_schedule = temp.json()
        time_consuming = round(1000 * (time.time() - start_time), 3)
        return doctors_schedule, time_consuming, temp.ok
    except Exception as e:
        time_consuming = round(1000 * (time.time() - start_time), 3)
        return None, time_consuming, False
