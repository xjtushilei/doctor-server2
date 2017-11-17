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
        "dob": "1990-03-09",
        "sex": "famale",
        "cardNo": "abc1231"
    },
    "wechatOpenId":wechatOpenId
}
print(client_request_body)
res = requests.post('http://docfinder.sparta.html5.qq.com/v1/sessions?clientId=mobimedical&orgId=org',
                    json=client_request_body).json()
print(res)
print(res["question"]["query"])
print("--------------  口述环节(根据年龄和性别推荐常见的病，同时可以自己输入自己的) -------------------")
print(",".join(res["question"]["choices"]))
print("--------------  口述环节(根据年龄和性别推荐常见的病，同时可以自己输入自己的) -------------------")
user_input = input("请输入:")

data = "clientId=mobimedical&orgId=org&sessionId=org_"+wechatOpenId+"&seqno=1&query=您有哪些不舒服的症状？&choice=" + user_input
res = doctor(data)
print(res)
print(res["question"]["query"])
print("------------ Round 1 ---------------------")
print(",".join(res["question"]["choices"]))
print("------------ Round 1 ---------------------")
user_input = input("请输入:")

data = "clientId=mobimedical&orgId=org&sessionId=org_"+wechatOpenId+"&seqno=2&query=您有哪些不舒服的症状？&choice=" + user_input
res = doctor(data)
print(res)
print(res["question"]["query"])
print("------------ Round 2 ---------------------")
print(",".join(res["question"]["choices"]))
print("------------ Round 2 ---------------------")
user_input = input("请输入:")

data = "clientId=mobimedical&orgId=org&sessionId=org_"+wechatOpenId+"&seqno=3&query=您有哪些不舒服的症状？&choice=" + user_input
res = doctor(data)
print(res["question"]["query"])
print("------------ Round 3 ---------------------")
print(",".join(res["question"]["choices"]))
print("------------ Round 3 ---------------------")
user_input = input("请输入:")
print("------------ 结果 ---------------------")
data = "clientId=mobimedical&orgId=org&sessionId=org_"+wechatOpenId+"&seqno=4&query=您有哪些不舒服的症状？&choice=" + user_input
res = doctor(data)
print(res)
print("----------------------------最后一轮根据症状数量和权重进行排序的结果：--------------------")
for x in res["recommendation"]["wangmeng"]:
    print(x)
print("----------------------------最后一轮再经过京伟的模型的结果：--------------------")
for x, y in res["recommendation"]["jingwei"].items():
    print(x, y)
