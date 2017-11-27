# -*-coding:utf-8 -*-

import json
import logging.config
import os
import random
import sys
import time
import traceback
from datetime import datetime
from urllib.parse import urlparse, parse_qs

import yaml
from flask import Flask
from flask import request

from cmodel import FindDoc

app = Flask(__name__)


# heartbeat handler
@app.route('/')
def index():
    return "OK", 200


# 内部测试错误api
@app.route("/test/", methods=['Get'])
def test():
    if random.randint(1, 10) > 5:
        1 / 0
    return "内部错误测试api"


@app.errorhandler(Exception)
def unknow_error(error):
    """"处理所有未处理的异常"""
    req = request.get_json()
    exstr = traceback.format_exc()
    error_data = {
        "req": req,
        "traceback": exstr,
        "error": str(error),
        "time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
    }
    log_unkonw_error.error(error_data)
    return "内部错误", 500


# main handler
@app.route('/v1/engine', methods=['POST'])
def do():
    log_info.setLevel(log_level)
    req = request.get_json()
    log_info.info(json.dumps(req, ensure_ascii=False))
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
    elif url.path == CLIENT_API_DOCTORS:
        res = find_doctors(req)
        res = json.dumps(res, ensure_ascii=False)
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


def create_client_response(code, sessionId, userRes, session):
    return {
        'sessionId': sessionId,
        'toUserResponse': {
            'code': code,
            'content': json.dumps(userRes, ensure_ascii=False)
            # 'content': userRes  这里一定要这个格式。taf那边写死了
        },
        # 'sessionDataUpdate': session
        'sessionDataUpdate': json.dumps(session, ensure_ascii=False)
        # 'content': userRes  这里一定要这个格式。taf那边写死了
    }


def create_session(req):
    sessionId = req["sessionId"]
    requestBody = req["requestBody"]
    clientSessionReq = json.loads(requestBody)
    patient = clientSessionReq["patient"]
    dob = patient["dob"]
    age = get_age_from_dob(dob)
    gender = patient["sex"]
    symptoms = cm.get_common_symptoms(age, gender)
    if len(symptoms) >= 5:
        symptoms = symptoms[:5]
    question = create_question('multiple', 1, NO_1_PROMPT, symptoms)
    userRes = {
        'sessionId': sessionId,
        'greeting': GREETING_PROMPT,
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
    # print(questions)
    updatedQuestions = []
    for question in questions:
        if "seqno" in question:
            if question["seqno"] < seqno:
                updatedQuestions.append(question)
            elif question["seqno"] == seqno:
                question["choice"] = choice
                updatedQuestions.append(question)
    session["questions"] = updatedQuestions
    # print(session["questions"])

    return session


def info_log(sessionId, status, recommendation, debug, session):
    if "patient" in session:
        patient = session['patient']
    else:
        patient = {}
    if "diagnosis_disease_rate_list" in session:
        final_disease = session["diagnosis_disease_rate_list"]
    else:
        final_disease = []
    if "questions" in session:
        questions = session["questions"]
    else:
        questions = []
    if "all_log" in session:
        all_log = session["all_log"]
    else:
        all_log = []
    data = {
        "sessionId": sessionId,
        "time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())),
        "patient": patient,
        "status": status,
        "final_disease": final_disease,
        "recommendation": recommendation,
        "questions": questions,
        "all_log": all_log,
        "debug": debug
    }
    session["log_data"] = data
    # 本地文件日志
    log_info.setLevel(log_level)
    log_info.info(json.dumps(data, ensure_ascii=False))


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
        choice = choice.replace(NO_SYMPTOMS_PROMPT, " ")
    # 是否在测试页面展示debug信息
    if "debug" in params:
        debug = True
    else:
        debug = False
    session = update_session(session, seqno, choice)
    dob = session["patient"]["dob"]
    age = get_age_from_dob(dob)
    sex = session["patient"]["sex"]
    status, question, recommendation = cm.find_doctors(session, seqno, choice, age, sex, debug)
    if status == "followup":
        userRes = {
            'sessionId': sessionId,
            'status': status,
            'question': question
        }
        session["questions"].append(question)
    elif status == "doctors" or status == "department":
        userRes = {
            'sessionId': sessionId,
            'status': status,
            'recommendation': recommendation
        }
        # 记录芒果db的日志
        info_log(sessionId=sessionId,
                 status=status,
                 recommendation=recommendation,
                 debug=debug,
                 session=session)
        # 文件日志记录日志

    else:
        userRes = {
            'sessionId': sessionId,
            'status': 'other',
            'recommendation': {
                "other": STATUS_OTHER
            }

        }
        # 文件日志记录日志
        info_log(sessionId=sessionId,
                 status=status,
                 recommendation={},
                 debug=debug,
                 session=session
                 )
        if debug:
            userRes["debug"] = recommendation
    res = create_client_response(200, sessionId, userRes, session)
    return res


# 获取当前文件的绝对路径，加在配置文件前，这样才能读出来
def src_path():
    return os.path.dirname(os.path.realpath(__file__))


# 获取配置文件
def load_config(yaml_path="app_config.yaml"):
    with open(yaml_path) as config_file:
        return yaml.load(config_file)


def src_dir():
    return os.path.dirname(os.path.realpath(__file__))


if __name__ == '__main__':

    # ###################文案#################################
    # 获取文案信息
    text_config = load_config(src_path() + "/conf/text_config.yaml")
    # 创建session的打招呼用语
    GREETING_PROMPT = text_config["GREETING_PROMPT"]
    # 第1轮的提问文案
    NO_1_PROMPT = text_config["NO_1_PROMPT"]
    # 第x轮的"没有其他症状"的文案
    NO_SYMPTOMS_PROMPT = text_config["NO_SYMPTOMS_PROMPT"]
    # other状态的文案
    STATUS_OTHER = text_config["STATUS_OTHER"]
    ######################其他配置文件加载##################################
    # 获取配置文件
    # 获取命令行参数
    if len(sys.argv) == 3:
        config_path = sys.argv[1]
        log_config_path = sys.argv[2]
    else:
        if not os.path.exists("log/"):
            os.makedirs("log/")
        config_path = src_path() + "/conf/app_config.yaml"
        log_config_path = src_path() + "/conf/logger.conf"
    # 获取yaml配置文件
    app_config = load_config(config_path)
    ############################API名字############################
    CLIENT_API_SESSIONS = app_config["api"]["CLIENT_API_SESSIONS"]
    CLIENT_API_DOCTORS = app_config["api"]["CLIENT_API_DOCTORS"]
    ################################LOG日志文件#######################
    # 获取log配置文件
    logging.config.fileConfig(log_config_path)
    # 通用日志
    log_info = logging.getLogger("myinfo")
    # 记录我们检测到的error，比如url错误或者orgid不对等
    log_error = logging.getLogger("error")
    # 记录程序中位置的错误，比如jignwei的模型突然出现不可预知的except，就捕获
    log_unkonw_error = logging.getLogger("unknown_error")
    # DEBUG--INFO--ERROR
    log_level = "INFO"
    ############################模型文件位置############################
    # 配置核心模型
    cm = FindDoc(model_path=app_config["model"]["model_path"],
                 seg_model_path=app_config["model"]["seg_model_path"],
                 dict_var_path=app_config["model"]["dict_var_path"],
                 all_symptom_count_file_path=app_config["model"]["all_symptom_count_file_path"],
                 disease_symptom_file_dir=app_config["model"]["disease_symptom_file_dir"],
                 doctors_distributions_path=app_config["model"]["doctors_distributions_path"],
                 doctors_id_path=app_config["model"]["doctors_id_path"],
                 text_config=text_config,
                 symptoms_distributions_file_dir=app_config["model"]["symptoms_distributions_file_dir"]
                 )
    ###############################模型文件加载#########################
    # 统计加载模型时间
    starttime = datetime.now()
    cm.load()
    endtime = datetime.now()
    log_info.setLevel(log_level)
    log_info.info(
        "模型加载一共用时：" + str((endtime - starttime).seconds) + "秒" + " finished loading models. server started .")
    print("模型加载一共用时：" + str((endtime - starttime).seconds) + "秒" + "\nfinished loading models.\n server started .")
    ######################### flask 启动#############################
    app.run(debug=app_config["app"]["debug"],
            host=app_config["app"]["host"],
            port=app_config["app"]["port"],
            threaded=app_config["app"]["threaded"])
