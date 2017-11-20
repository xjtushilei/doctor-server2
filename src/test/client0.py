# -*-coding:utf-8 -*-

import requests
wechatOpenId="weichat1icdmqq23123mmq"
def doctor(data):
    url = 'http://docfinder.sparta.html5.qq.com/v1/doctors?' + data
    print(url)
    res = requests.get(url)
    return res.json()


client_request_body = {
    "patient": {
        "name": "J",
        "dob": "1976-03-09",
        "sex": "female",
        "cardNo": "abc1231"
    },
    "wechatOpenId":wechatOpenId
}
print(client_request_body)
res = requests.post('http://docfinder.sparta.html5.qq.com/v1/sessions?clientId=mobimedical&orgId=org',
                    json=client_request_body).json()
print(res)

