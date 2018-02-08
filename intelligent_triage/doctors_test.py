# 医生模型的获取医生信息
import json

import os

import doctors

codes = [
    "J06",
    "J06",
    "J06",
    "N92",
    "N92"
]
probs = [
    0.7846577039087731,
    0.7519460352687259,
    0.7486890645155105,
    0.7403263709483923,
    0.7204414539601419
]
age = 13
gender = "female"
orgId = "orgId"
clientId = "jindie"
branchId = "branchId"
# query_hospital_url = "http://127.0.0.1:8087/test/query_doctors"
# query_hospital_url = "http://test3.mhealth100.com/open-api/V1/query_appointments?tenantId=00006&hospitalId=100201"
query_hospital_url = "http://test3.mhealth100.com/open-api/V1/query_appointments?tenantId=00006&hospitalId=100201&channelCode=1505819123134"
appointment = ""
debug = False
model = {}
model_path="C://data/model//hospital/东莞妇幼.doctor.json.v2"
# model_path = "/mdata/finddoctor/model/hospital/东莞妇幼.doctor.json.v2"
with open(model_path, encoding="utf-8") as file:
    model = json.load(file)
os.environ['http_proxy'] = 'http://dev-proxy.oa.com:8080'
docs = doctors.get_doctors(codes=codes, probs=probs, age=age, gender=gender,
                           orgId=orgId, clientId=clientId, branchId=branchId,
                           query_hospital_url=query_hospital_url,
                           model=model, appointment=appointment, debug=debug)
print(docs)