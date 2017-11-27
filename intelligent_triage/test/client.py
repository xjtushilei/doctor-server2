# -*-coding:utf-8 -*-
import hashlib
import json
import time
from pprint import pprint

import requests


def get_response(res):
    toUserResponse = res["toUserResponse"]
    print(toUserResponse)
    content = json.loads(toUserResponse["content"])
    pprint(content)


def create_md5():  # 通过MD5的方式创建
    m = hashlib.md5()
    m.update(bytes(str(time.time()), encoding='utf-8'))
    return m.hexdigest()


def post(data, url='http://127.0.0.1:6000/v1/engine'):
    res = requests.post(url, json=data)
    return res.json()


wechatid = create_md5()
client_request_body = {
    "patient": {
        "name": "J",
        "dob": "1991-03-09",
        "sex": "female",
        "cardNo": "abc1231"
    },
    "wechatOpenId": wechatid
}

session = {
    "sessionId": "org_" + wechatid,
}

create_session_req = {
    "sessionId": "org_" + wechatid,
    "requestUrl": "/v1/sessions?clientId=mobimedical&orgId=org",
    "requestBody": json.dumps(client_request_body),
    "sessionData": json.dumps(session)
}
res = post(create_session_req)
# print(res)
session = res["sessionDataUpdate"]
print(1, res["toUserResponse"]["content"])
# user_input = "今天很开心"
user_input = "白带增多"
# user_input = input("请问您哪里不舒服？")

create_session_req = {
    "sessionId": "org_" + wechatid,
    "requestUrl": "/v1/doctors?clientId=mobimedical&de_bug=true&orgId=org&sessionId=" + "org_" + wechatid + "&seqno=1&query=您有什么不舒服的？&choice=" + user_input,
    "requestBody": json.dumps(client_request_body),
    "sessionData": session
}
res = post(create_session_req)
session = res["sessionDataUpdate"]
print(2, res["toUserResponse"]["content"])

user_input = "阴道不规则出血,没有其他症状了"
# user_input = input("请问您哪里不舒服？")
create_session_req = {
    "sessionId": "org_" + wechatid,
    "requestUrl": "/v1/doctors?clientId=mobimedical&de_bug=true&orgId=org&sessionId=" + "org_" + wechatid + "&seqno=2&query=您有什么不舒服的？&choice=" + user_input,
    "requestBody": json.dumps(client_request_body),
    "sessionData": session
}
res = post(create_session_req)
session = res["sessionDataUpdate"]
print(3, res["toUserResponse"]["content"])

user_input = "肚疼"
# user_input = input("请问您哪里不舒服？")
create_session_req = {
    "sessionId": "org_" + wechatid,
    "requestUrl": "/v1/doctors?clientId=mobimedical&de_bug=true&orgId=org&sessionId=" + "org_" + wechatid + "&seqno=3&query=您有什么不舒服的？&choice=" + user_input,
    "requestBody": json.dumps(client_request_body),
    "sessionData": session
}
res = post(create_session_req)
session = res["sessionDataUpdate"]
print(4, res["toUserResponse"]["content"])
session_json = json.loads(session)
# print(session_json)
print("----------1----------")
# print(json.dumps(session_json["log_data"], ensure_ascii=False))
print("----------2----------")
print(session_json)
