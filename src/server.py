# -*-coding:utf-8 -*-

import json
from datetime import datetime
from urllib.parse import urlparse, parse_qs
import numpy as np
from flask import Flask
from flask import request
from cmodel import FindDoc
import logging.config

logging.config.fileConfig("logger.conf")
# 通用日志
log_info = logging.getLogger("myinfo")
# 记录我们检测到的error，比如url错误或者orgid不对等
log_error = logging.getLogger("error")
# 记录程序中位置的错误，比如jignwei的模型突然出现不可预知的except，就捕获
log_unkonw_error = logging.getLogger("unknown_error")

app = Flask(__name__)
CLIENT_API_SESSIONS = "/v1/sessions"
CLIENT_API_DOCTORS = "/v1/doctors"
log_level = "DEBUG"

symptoms_distributions_file_dir = '/tvm/mdata/jerryzchen/model/symptoms_distributions.json'
# symptoms_distributions_file_dir = './model/symptoms_distributions.json'
cm = FindDoc(model_path="/tvm/mdata/jerryzchen/model/model-webqa-hdf-2c.bin",
             seg_model_path="/tvm/mdata/jerryzchen/model/cws-3.4.0.model",
             dict_var_path="/tvm/mdata/jerryzchen/model/dict_var.npy",
             all_symptom_count_file_path="/tvm/mdata/jerryzchen/model/all-symptom-count.data",
             disease_symptom_file_dir="/tvm/mdata/jerryzchen/model/disease-symptom3.data",
             doctors_distributions_path="/tvm/mdata/jerryzchen/model/doctors_distributions.json",
             doctors_id_path="/tvm/mdata/jerryzchen/model/doctors_id.txt"
             )


# cm = FindDoc()


## heartbeat handler
@app.route('/')
def index():
    return "OK", 200


##main handler
@app.route('/v1/engine', methods=['POST'])
def do():
    log_info.setLevel(log_level)
    req = request.get_json()
    log_info.info(req)
    if req is None:
        res = upstream_error("错误的请求: 无法解析JSON")
        res = json.dumps(res, ensure_ascii=False)
        log_error.error(res)
        return res, 400

    isOk, res = request_sanity_check(req)
    if not isOk:
        res = json.dumps(res, ensure_ascii=False)
        log_error.error(res)
        return res, 400

    requestUrl = req["requestUrl"]
    url = urlparse(requestUrl)
    if not url_params_check(url):
        res = client_error(req, 401, "未授权用户")
        res = json.dumps(res, ensure_ascii=False)
        log_error.error(res)
    elif url.path == CLIENT_API_SESSIONS:
        res = create_session(req)
        res = json.dumps(res, ensure_ascii=False)
        log_info.info(res)
    elif url.path == CLIENT_API_DOCTORS:
        res = find_doctors(req)
        res = json.dumps(res, ensure_ascii=False)
        log_info.info(res)
    else:
        res = client_error(req, 404, " 错误的路径: " + url.path)
        res = json.dumps(res, ensure_ascii=False)
        log_error.error(res)

    return res, 200


def request_sanity_check(req):
    if not ("requestUrl" in req and "sessionId" in req and "requestBody" in req and "sessionData" in req):
        return False, upstream_error("错误的请求: JSON格式错误")
    return True, None


def upstream_error(error_msg):
    return {
        "error": error_msg
    }


def client_error(req, code, error_msg):
    sessionId = req["sessionId"]
    userRes = {
        "error": error_msg
    }
    session = load_session(req)
    return create_client_response(code, sessionId, userRes, session)


def url_params_check(url):
    query = url.query
    query_params = parse_qs(query)
    if "clientId" in query_params and "orgId" in query_params and "mobimedical" in query_params["clientId"]:
        return True
    return False


def load_session(req):
    sessionData = req["sessionData"]
    session = json.loads(sessionData)
    return session


def get_age_from_dob(dob):
    birth = datetime.strptime(dob, "%Y-%m-%d")
    today = datetime.today()
    diff = (today - birth)
    ageInDays = diff.days
    return ageInDays / 365.


def create_question(qtype, seqno, query, choices):
    return {
        'type': qtype,
        'seqno': seqno,
        'query': query,
        'choices': choices
    }


def get_common_symptoms(age, gender, month=None):
    # input: age: int, age>0; gender: {'F','M'}; month:int, [1,..12]
    # age = 12
    # gender = 'F'
    # month = 10
    # get_common_symptoms(age,gender,month)
    if gender == "female":
        gender = "F"
    else:
        gender = "M"
        # 疾病是男性，切性别大于18，则不进行推荐
        if gender == "M" and age >= 18:
            return []
    if month is None:
        month = datetime.now().month
    with open(symptoms_distributions_file_dir, 'r') as fp:
        symptoms_rankings = json.load(fp)
    # months = [1,2,3,4,5,6,7,8,9,10,11,12] # 12 months
    # genders = ['F', 'M']
    ages = [0, 0.08, 1, 3, 6, 12, 18, 40, 100]  # 8 phases
    a = np.argmax(np.array(ages) > age)
    index = 'M' + str(month) + 'A' + str(ages[a - 1]) + 'A' + str(ages[a]) + gender
    return [item[0] for item in symptoms_rankings[index]]


def create_client_response(code, sessionId, userRes, session):
    return {
        'sessionId': sessionId,
        'toUserResponse': {
            'code': code,
            'content': json.dumps(userRes, ensure_ascii=False)
        },
        'sessionDataUpdate': json.dumps(session, ensure_ascii=False)
    }


def create_session(req):
    sessionId = req["sessionId"]
    requestBody = req["requestBody"]
    clientSessionReq = json.loads(requestBody)
    patient = clientSessionReq["patient"]
    dob = patient["dob"]
    age = get_age_from_dob(dob)
    gender = patient["sex"]
    symptoms = get_common_symptoms(age, gender)
    if len(symptoms) >= 5:
        symptoms = symptoms[:5]
    question = create_question('multiple', 1, '您有哪些不舒服的症状？', symptoms)
    userRes = {
        'sessionId': sessionId,
        'greeting': '欢迎使用智能分诊助手，帮您找到合适医生。',
        'question': question
    }
    session = load_session(req)
    session['patient'] = patient
    session['wechatOpenId'] = clientSessionReq["wechatOpenId"]
    session['questions'] = [question]
    res = create_client_response(200, sessionId, userRes, session)
    return res


def update_session(session, seqno, choice):
    questions = session["questions"]
    updatedQuestions = []
    for question in questions:
        if question["seqno"] < seqno:
            updatedQuestions.append(question)
        elif question["seqno"] == seqno:
            question["choice"] = choice
            updatedQuestions.append(question)
    session["questions"] = updatedQuestions
    return session


def find_doctors(req):
    sessionId = req["sessionId"]
    requestUrl = req["requestUrl"]
    url = urlparse(requestUrl)
    params = parse_qs(url.query)
    session = load_session(req)

    if not ("seqno" in params and "query" in params and len(params["seqno"]) > 0):
        return client_error(req, "400", "错误的请求: 错误的数据格式")

    seqno = int(params["seqno"][0])
    if "choice" not in params:
        choice = " "
    else:
        choice = params["choice"][0]
    session = update_session(session, seqno, choice)
    dob = session["patient"]["dob"]
    age = get_age_from_dob(dob)
    sex = session["patient"]["sex"]
    # 不包含key=mmq的话，则不进行展示我们的成果

    if "icdmqq" in sessionId:
        status, question, recommendation = cm.find_doctors(session, log_info, seqno, choice, age, sex)
    else:
        status, question, recommendation = cm.find_doctors_test(seqno)
    if status == "followup":
        userRes = {
            'sessionId': sessionId,
            'status': status,
            'question': question
        }
    elif status == "doctors" or status == "department":
        userRes = {
            'sessionId': sessionId,
            'status': 'doctors',
            'recommendation': recommendation
        }
        session["recommendation"] = recommendation
    else:
        userRes = {
            'sessionId': sessionId,
            'status': 'other',
            "other": "不在华西二院的诊疗范围"
        }
    session["questions"].append(question)
    res = create_client_response(200, sessionId, userRes, session)
    return res


if __name__ == '__main__':
    # 统计加载模型时间
    starttime = datetime.now()
    cm.load()
    endtime = datetime.now()
    log_info.setLevel(log_level)
    log_info.info("模型加载一共用时：" + str((endtime - starttime).seconds) + "秒" + "\n finished loading models.\n server started .")
    print("模型加载一共用时：" + str((endtime - starttime).seconds) + "秒" + "\n finished loading models.\n server started .")
    app.run(debug=False, host="0.0.0.0", port=6000, threaded=True)
