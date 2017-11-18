# -*-coding:utf-8 -*-

import requests
import json
from pprint import pprint

def post(data, url='http://127.0.0.1:6000/v1/engine'):
    res = requests.post(url, json=data)
    return res.json()

def print_response(res):

    toUserResponse = res["toUserResponse"]
    content = json.loads(toUserResponse["content"])
    pprint(content)

def create_session():
    client_request_body={
        "patient": {
            "name": "韩梅梅",
            "dob": "2010-01-01",
            "sex": "female",
            "cardNo": "abc123"
            },
        "wechatOpenId": "weichat1icdmqq23123mmq"
    }

    session = {
        "sessionId": "org_weichat1icdmqq23123mmq"
    }

    create_session_req = {
        "sessionId": "weichat1icdmqq23123mmq",
        "requestUrl": "/v1/sessions?clientId=mobimedical&orgId=org",
        "requestBody": json.dumps(client_request_body),
        "sessionData": json.dumps(session)
    }
    print_response(post(create_session_req))

def get_doctors():
    client_request_body={
        "patient": {
            "name": "韩梅梅",
            "dob": "2010-01-01",
            "sex": "male",
            "cardNo": "abc123"
        },
        "wechatOpenId": "weichat1icdmqq23123mmq"
    }

    session = {
        "sessionId": "org_weichat1icdmqq23123mmq",
        "api_version": "v1",
        "patient":{
            "name": "韩梅梅",
            "dob": "2010-01-01",
            "sex": "female",
            "cardNo": "abc123"
        },
        "wechatOpenId": "weichat1icdmqq23123mmq",
        "last_timestamp": 12345,
        "questions": [
            {'choices': ['发热', '咳嗽', '疲乏', '流鼻涕', '发绀'],
             'query': '你有哪些不舒服的症状',
             'seqno': 1,
             'type': 'multiple'
             }
        ]
    }

    create_session = {
        "sessionId": "org_weichat1icdmqq23123mmq",
        "requestUrl": "/v1/doctors?clientId=mobimedical&orgId=org&sessionId=org_weichat1icdmqq23123mmq&seqno=1&query=你有哪些不舒服的症状&choice=疲乏,我今天拉肚子腹泻",
        # "requestUrl": "/v1/sessions?clientId=mobimedical&orgId=abc&sessionId=12345",
        "requestBody": json.dumps(client_request_body),
        "sessionData": json.dumps(session)
    }
    print_response(post(create_session))

#create_session()
get_doctors()
