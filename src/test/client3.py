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
    client_request_body = {
        "patient": {
            "name": "韩梅梅",
            "dob": "2010-01-01",
            "sex": "male",
            "cardNo": "abc123"
        },
        "wechatOpenId": "abcdefg"
    }

    session = {
        "sessionId": "weichat1icdmqq23123mmq"
    }

    create_session_req = {
        "sessionId": "weichat1icdmqq23123mmq",
        "requestUrl": "/v1/sessions?clientId=mobimedical&orgId=abc",
        "requestBody": json.dumps(client_request_body),
        "sessionData": json.dumps(session)
    }
    print_response(post(create_session_req))


def get_doctors():
    client_request_body = {
        "patient": {
            "name": "韩梅梅",
            "dob": "2010-01-01",
            "sex": "male",
            "cardNo": "abc123"
        },
        "wechatOpenId": "abcdefg"
    }

    session = {
        "sessionId": "weichat1icdmqq23123mmq",
        "api_version": "v1",
        "patient": {
            "name": "韩梅梅",
            "dob": "2010-01-01",
            "sex": "female",
            "cardNo": "abc123"
        },
        "wechatOpenId": "abcdefg",
        "last_timestamp": 12345,
        "diagnosis_disease_rate_dict": {'流行性感冒,病毒未标明': [0.8111172295658331, 'J11'],
                                        '肺炎,病原体未特指': [0.80124315307969052, 'J18'],
                                        '巨细胞病毒病': [0.82083892808668846, 'B25'], '水痘': [0.81742126963136796, 'B01'],
                                        '其他呼吸性疾患': [0.80017585450968998, 'J98']},
        "questions": [
            {'choices': ['发热', '咳嗽', '疲乏', '流鼻涕', '发绀'],
             'query': '你有哪些不舒服的症状',
             'seqno': 1,
             'type': 'multiple',
             'choice': '疲乏,我今天拉肚子腹泻'
             }
            ,
            {'type': 'multiple',
             'query': '您有哪些不舒服的症状？',
             'choice': '眼前发黑',
             'choices': ['呼吸异常', '眼前发黑', '血压低', '结节', '心悸'],
             'seqno': 2}
            ,
            {'choices': ['肝区肿大', '咽部异物感', '呕血', '甲状腺机能亢进', '过敏'], 'query': '您有哪些不舒服的症状？', 'seqno': 3,
             'type': 'multiple'}

        ]
    }

    create_session = {
        "sessionId": "12345",
        "requestUrl": "/v1/doctors?clientId=mobimedical&orgId=abc&sessionId=weichat1icdmqq23123mmq&seqno=3&query=你有哪些不舒服的症状&choice=咽部异物感",
        "requestBody": json.dumps(client_request_body),
        "sessionData": json.dumps(session)
    }
    print_response(post(create_session))


# create_session()
get_doctors()
