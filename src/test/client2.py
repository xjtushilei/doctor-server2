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
            "sex": "male",
            "cardNo": "abc123"
            },
        "wechatOpenId": "abcdefg"
    }

    session = {
        "sessionId": "123456"
    }

    create_session_req = {
        "sessionId": "12345",
        "requestUrl": "/v1/sessions?clientId=mobimedical&orgId=abc",
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
        "wechatOpenId": "abcdefg"
    }

    session = {
        "sessionId": "123456",
        "api_version": "v1",
        "patient":{
            "name": "韩梅梅",
            "dob": "2010-01-01",
            "sex": "female",
            "cardNo": "abc123"
        },
        "wechatOpenId": "abcdefg",
        "last_timestamp": 12345,
        "diagnosis_disease_rate_dict": {'缺铁性贫血': [0.80425453633929289, 'D50'], '其他贫血': [0.79569743879495791, 'D64'], '淋巴样白血病': [0.80135929659925798, 'C91'], '甲状腺毒症[甲状腺功能亢进症]': [0.79446696973625786, 'E05'], '其他遗传性溶血性贫血': [0.80470183954059793, 'D58']}
,

        "questions": [
            {'choices': ['发热', '咳嗽', '疲乏', '流鼻涕', '发绀'],
             'query': '你有哪些不舒服的症状',
             'seqno': 1,
             'type': 'multiple',
             'choice': '疲乏,我今天拉肚子腹泻'
             }
            ,
            {'type': 'multiple', 'query': '您有哪些不舒服的症状？', 'choices': ['呼吸异常', '眼前发黑', '血压低', '结节', '心悸'], 'seqno': 2}

        ]
    }

    create_session = {
        "sessionId": "12345",
        "requestUrl": "/v1/doctors?clientId=mobimedical&orgId=abc&sessionId=weichat1icdmqq23123mmq&seqno=2&query=你有哪些不舒服的症状&choice=眼前发黑,",
        "requestBody": json.dumps(client_request_body),
        "sessionData": json.dumps(session)
    }
    print_response(post(create_session))

#create_session()
get_doctors()
