# 医生模型的获取医生信息
import datetime
import time
from operator import *

import requests

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET


def get_doctors(codes, probs, age, gender, query_hospital_url, model,
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
        return [], True
    agename = ["age01", "age0118", "age18"]

    if gender in ["M", "男", "male"]:
        gender_index = 0
    elif gender in ["F", "女", "female"]:
        gender_index = 1
    else:
        return [], True

    # get the query list of doctors; check all the icd10 until find doctors; return None if no doctors for 5 icd10s.
    doctors_query = {}
    for code, prob in zip(codes[:5], probs[:5]):
        if (prob >= prob_threshold) and (code in model[agename[age_index]].keys()) and (
                    model[agename[age_index]][code]["gender"][gender_index] >= gender_threshold):
            for item in model[agename[age_index]][code]["doctors"]:
                if item["departmentId"] not in doctors_query:
                    doctors_query[item["departmentId"]] = {}
                    doctors_query[item["departmentId"]]["num"] = 1
                    doctors_query[item["departmentId"]]["doctors"] = []
                    doctors_query[item["departmentId"]]["doctors"].append(
                        {"docId": item["id"], "departmentId": item["departmentId"],
                         "departmentName": item["departmentName"]})
                else:
                    doctors_query[item["departmentId"]]["num"] += 1
                    doctors_query[item["departmentId"]]["doctors"].append(
                        {"docId": item["id"], "departmentId": item["departmentId"],
                         "departmentName": item["departmentName"]})
        if len(doctors_query) != 0:
            break
    if len(doctors_query) == 0:
        return [], True

    temp = sorted(doctors_query.items(), key=lambda x: getitem(x[1], 'num'), reverse=True)[:5]
    doctors_query = {"doctors": []}
    for i in range(len(temp)):
        doctors_query["doctors"].extend(temp[i][1]["doctors"])

    # rank doctors according to schedules policy:
    # rank doctors according to schedules
    # import datetime
    # today_date = datetime.date.today() ##2018-01-15
    doctors_recommendation = []
    # print("doctors_query", doctors_query)
    # 查询号源接口，并返回号源结果
    doctors_schedule, time_consuming, ok = query_doctors(doctors_query, query_hospital_url, clientId, debug)
    # print("doctors_schedule", doctors_schedule, ok)
    today_date = datetime.date.today()
    if ok:
        if doctors_schedule["status"] == "ok":
            doctors_info = doctors_schedule["doctors"]
            for item1 in doctors_query["doctors"]:
                flag = False
                for item2 in doctors_info:
                    if item2["docId"] == item1["docId"]:
                        for schedule in item2["schedule"]:
                            year, month, day = (
                                int(schedule["date"].split("-")[0]), int(schedule["date"].split("-")[1]),
                                int(schedule["date"].split("-")[2]))
                            delta_days = (today_date - datetime.date(year, month, day)).days
                            if delta_days <= 10 and schedule["available"] >= 0:
                                flag = True
                                break
                        if flag == True:
                            temp = {}
                            for key, value in item2.items():
                                if key != "schedule":
                                    temp[key] = value
                                # 历史遗留的的问题，当时定义api时候字段定义的不标准导致的。
                                if key == "docId":
                                    temp["id"] = value
                                # 金蝶他们获取不到科室id，增加一下
                                if key == "departmentId" and value == "":
                                    temp["departmentId"] = item1["departmentId"]
                                # 金蝶他们获取不到科室name，增加一下
                                if key == "deptName" and value == "":
                                    temp["deptName"] = item1["departmentName"]
                            doctors_recommendation.append(temp)
                        break
        else:
            # false表示获取号源错误，应该是获取号源接口失败
            return None, False
    else:
        # false表示获取号源错误，应该是通过了获取token
        return None, False
    return doctors_recommendation[:10], True


# 获取号源接口，如果失败返回false
def query_doctors(doctors, url, clientId, debug=False):
    start_time = time.time()
    # 处理金蝶的url校验，主要就是加上token校验
    if clientId == "jindie":
        token, ok = getToken_from_jindie()
        if ok:
            token = "&token=" + token
        else:
            time_consuming = round(1000 * (time.time() - start_time), 3)
            return None, time_consuming, False
    else:
        # 如果不是金蝶，token为空
        token = ""
    url = url + token
    try:
        temp = requests.post(url, json=doctors, timeout=30, headers={"Content-Type": "application/json"})
        doctors_schedule = temp.json()
        time_consuming = round(1000 * (time.time() - start_time), 3)
        return doctors_schedule, time_consuming, temp.ok
    except Exception as e:
        time_consuming = round(1000 * (time.time() - start_time), 3)
        return None, time_consuming, False


# 从金蝶isv处获得token，如果失败，返回false
def getToken_from_jindie():
    tenantId = "00331"
    channelCode = "1505819123134"
    service = "base.token"
    url = "http://api.mhealth100.com/open-api/openGateway.do?"
    # url = "http://test3.mhealth100.com/open-api/openGateway.do?"
    url = url + "version=3.0&format=xml&auth=partner&tenantId=" + tenantId + \
          "&channelCode=" + channelCode + "&service=" + service
    secert = "761A9F7DC0644073AD28CCA40A1F4CEB"
    XML = '<?xml version="1.0" encoding="UTF-8"?><req><channelCode>' + channelCode + '</channelCode><secert>' + secert + '</secert></req>'
    headers = {'Content-type': 'text/xml'}
    # print(url)
    # print(XML)
    res = requests.post(url, data=XML, headers=headers)
    # print(res)
    if res.ok:
        root = ET.fromstring(res.text)  # 从字符串传递xml
        # print(root.find('token').text)
        return root.find('token').text, res.ok
    else:
        return None, False
