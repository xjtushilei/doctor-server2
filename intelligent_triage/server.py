# coding=utf-8
import hashlib
import json
import logging.config
import os
import re
import sys
import time
from datetime import datetime
from urllib.parse import urlparse, parse_qs

from flask import Flask
from flask import request

from db_util import RedisCache, Mongo
from pipeline import Pipeline

app = Flask(__name__)

CLIENT_API_SESSIONS = "/v1/sessions"
CLIENT_API_DOCTORS = "/v1/doctors"


# heartbeat handler
@app.route('/')
def index():
    return "OK", 200


# @app.errorhandler(Exception)
# def unknow_error(error):
#     """"处理所有未处理的异常"""
#     req = request.get_json()
#     log_unkonw_error.error(req)
#     log_unkonw_error.exception(error)
#     return "内部错误", 500


@app.route('/v1/record', methods=["POST"])
def record():
    ok, res, code = record_data_check(request)
    if not ok:
        return res, code

    req = request.get_json()
    params = parse_qs(urlparse(request.url).query)
    clientId = params["clientId"][0]
    orgId = params["orgId"][0]
    req["clientId"] = clientId
    req["orgId"] = orgId
    mongo = Mongo(app_config)
    mongo.record(req)
    return "ok"


@app.route('/v1/sessions', methods=["POST"])
def creat_session():
    # 检查数据是否有效和url合法性
    ok, res, code = session_data_check(request)
    if not ok:
        return res, code

    req = request.get_json()
    patient = req["patient"]
    dob = patient["dob"]
    gender = patient["sex"]
    cardNo = patient["cardNo"]
    wechatOpenId = req["wechatOpenId"]
    age = get_age_from_dob(dob)
    sessionId = wechatOpenId + "_" + cardNo + "_" + create_random_num_by_md5()
    # 获取推荐的初始症状
    symptoms = pipline.get_common_symptoms(age, gender)
    question = create_question('multiple', 1, app_config["text"]["NO_1_PROMPT"], symptoms)
    userRes = {
        'sessionId': sessionId,
        'greeting': app_config["text"]["GREETING_PROMPT"],
        'question': question
    }
    session = {'patient': patient, 'wechatOpenId': wechatOpenId, 'questions': [question]}
    dump_session(sessionId, session)
    return json.dumps(userRes, ensure_ascii=False)


@app.route('/v1/doctors', methods=["GET"])
def find_doctors():
    # url检查
    ok, res, code = find_doctor_data_check(request)
    if not ok:
        return res, code
    # 获取有用的信息
    params = parse_qs(urlparse(request.url).query)
    sessionId = params["sessionId"][0]
    seqno = int(params["seqno"][0])
    if "choice" not in params:
        choice = " "
    else:
        choice = params["choice"][0]
        xss_status, xss_desc = xss_defense_check(choice)
        if not xss_status:
            return error("错误的请求:" + xss_desc), 400
        # 去掉“什么都没有“等垃圾信息
        for x in app_config["text"]["NO_1_PROMPT"]:
            choice = choice.replace(x, " ")
    # 是否在测试页面展示debug信息
    if "debug" in params and params["debug"][0] == "true":
        debug = True
    else:
        debug = False

    session = load_session(sessionId)
    print("之前", json.dumps(session, ensure_ascii=False, indent=4))
    session = update_session(session, seqno, choice)
    dob = session["patient"]["dob"]
    sex = session["patient"]["sex"]
    age = get_age_from_dob(dob)

    taskData = {"age": age, "sex": sex, "session": session}
    status, question, recommendation = pipline.process(taskData)

    # status, question, recommendation = pipline.process(session, seqno, choice, age, sex, debug)

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
        # 患者口述有疾病和症状，可以分到ICD10，但是不在医院诊疗范围,那么丽娟返回的doctor就是空
        if status == "doctors" and len(recommendation["doctors"]) == 0:
            userRes = {
                'sessionId': sessionId,
                'status': 'other',
                'recommendation': {
                    "other": app_config["text"]["STATUS_DOCTOR_0"]
                }
            }
        # 记录日志
        info_log(sessionId=sessionId,
                 status=status,
                 recommendation=recommendation,
                 debug=debug,
                 session=session)


    else:
        userRes = {
            'sessionId': sessionId,
            'status': 'other',
            'recommendation': {
                "other": app_config["text"]["STATUS_OTHER"]
            }
        }
        # 文件日志记录日志
        info_log(sessionId=sessionId,
                 status=status,
                 recommendation={},
                 debug=debug,
                 session=session)
        if debug:
            userRes["debug"] = recommendation

    print("之后", json.dumps(session, ensure_ascii=False, indent=4))
    dump_session(sessionId, session)
    return json.dumps(userRes, ensure_ascii=False)


def error(error_msg):
    return {
        "error": error_msg
    }


def auth_check(request):
    url = urlparse(request.url)
    query = url.query
    query_params = parse_qs(query)
    if not ("clientId" in query_params and "orgId" in query_params and "mobimedical" in query_params["clientId"]):
        return False, error("未授权用户"), 401
    return True, None, None


def find_doctor_data_check(request):
    url = urlparse(request.url)
    query = url.query
    query_params = parse_qs(query)
    if not ("clientId" in query_params and "orgId" in query_params and "mobimedical" in query_params["clientId"]):
        return False, error("未授权用户"), 401
    if not ("choice" in query_params and "sessionId" in query_params and
            "seqno" in query_params and "query" in query_params and len(query_params["seqno"]) > 0):
        return False, error("错误的请求: url中没有包含choice或query或seqno"), 400
    return True, None, None


def record_data_check(request):
    ok, res, code = auth_check(request)
    if not ok:
        return False, res, code

    req = request.get_json()
    # 检查数据是否为空
    if req is None:
        res = error("错误的请求: 无法解析JSON")
        return False, res, 400
    # 检查数据是否有效
    if "patient" not in req or "doctor" not in req or "sessionId" not in req or "appointmentId" not in req or "wechatOpenId" not in req:
        return False, error("错误的请求: 错误的数据上报格式(字段缺失)"), 400
    if "cardNo" not in req["patient"] or "doctorId" not in req["doctor"]:
        return False, error("错误的请求: 错误的数据上报格式(cardNo或doctorId字段缺失)"), 400

    return True, None, None


def session_data_check(request):
    ok, res, code = auth_check(request)
    if not ok:
        return False, res, code

    req = request.get_json()
    # 检查数据是否为空
    if req is None:
        res = error("错误的请求: 无法解析JSON")
        return False, res, 400
    # 检查数据是否有效
    if "patient" not in req or "wechatOpenId" not in req:
        return False, error("错误的请求: 错误的数据格式(字段缺失)"), 400
    patient = req["patient"]
    if "dob" not in patient or "cardNo" not in patient or "sex" not in patient or "name" not in patient:
        return False, error("错误的请求: 错误的数据格式(patient中字段缺失)"), 400
    dob = patient["dob"]
    gender = patient["sex"]
    if not (is_valid_date(dob) and len(dob) == 10):
        return False, error("错误的请求: 错误的数据格式(出生年月格式不对,示例：2018-02-01)"), 400
    if not (gender == "male" or gender == "female"):
        return False, error("错误的请求: 错误的数据格式(sex格式不对,应该是male或female)"), 400

    return True, None, None


def load_session(id):
    sessionData = RedisCache(app_config).get_data(id).decode()
    session = json.loads(sessionData)
    return session


def dump_session(sessionId, session):
    sessionData = json.dumps(session, ensure_ascii=False)
    RedisCache(app_config).set_data(sessionId, sessionData)


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


def is_valid_date(strdate):
    '''''判断是否是一个有效的日期字符串'''
    try:
        time.strptime(strdate, "%Y-%m-%d")
        return True
    except:
        return False


# 创建随机数
def create_random_num_by_md5():  # 通过MD5的方式创建
    m = hashlib.md5()
    m.update(bytes(str(time.time()), encoding='utf-8'))
    return m.hexdigest()


def update_session(session, seqno, choice):
    if "questions" in session:
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
    if "ner_time" in session:
        ner_time = session["ner_time"]
    else:
        ner_time = []
    if "main_time" in session:
        main_time = session["main_time"]
    else:
        main_time = []
    data = {
        "sessionId": sessionId,
        "time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())),
        "patient": patient,
        "status": status,
        "final_disease": final_disease,
        "recommendation": recommendation,
        "questions": questions,
        "all_log": all_log,
        "debug": debug,
        "ner_time": ner_time,
        "main_time": main_time
    }
    # session["log_data"] = data
    # 本地文件日志
    log_info.setLevel(log_level)
    log_info.info(json.dumps(data, ensure_ascii=False))


sql_key = ["select", "in", "from", "between", "aliases", "join", "union", "create", "null",
           "unique", "alter", "nulls", "avg", "sum", "max", "min", "len", "like", "where",
           "and", "order", "insert", "delete", "update", "top"]


def xss_defense_check(input):
    dr = re.compile(r'<[^>]+>', re.S)
    dd = dr.sub('', input)
    if len(dd) != len(input):
        return False, "请求字段包含html标签"
    input = input.lower()
    for key in sql_key:
        if key in input:
            return False, "请求字段包含SQL常见关键字"
    return True, None


# 获取当前文件的绝对路径，加在配置文件前，这样才能读出来
def src_path():
    return os.path.dirname(os.path.realpath(__file__))


# 获取配置文件
def load_config(json_path="app_config.json"):
    with open(json_path, encoding="utf-8") as config_file:
        return json.load(config_file)


def src_dir():
    return os.path.dirname(os.path.realpath(__file__))


if __name__ == '__main__':

    ######################其他配置文件加载##################################
    # 获取配置文件
    # 获取命令行参数
    if len(sys.argv) == 3:
        config_path = sys.argv[1]
        log_config_path = sys.argv[2]
    else:
        if not os.path.exists("log/"):
            os.makedirs("log/")
        config_path = src_path() + "/conf/app_config.json"
        log_config_path = src_path() + "/conf/logger.conf"
    # 获取yaml配置文件
    app_config = load_config(config_path)
    ###########################检测测试服还是正式服############################


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
    log_level = "DEBUG"
    ###############################模型文件加载#########################
    # 统计加载模型时间
    starttime = datetime.now()
    pipline = Pipeline(app_config)
    pipline.load()
    endtime = datetime.now()
    log_info.setLevel(log_level)
    log_info.info(
        "模型加载一共用时：" + str((endtime - starttime).seconds) + "秒" + " finished loading models. server started .")
    print("模型加载一共用时:" + str((endtime - starttime).seconds) + "秒" + "\nfinished loading models.\n server started .")
    ######################### flask 启动#############################
    # app.run(host='127.0.0.1', port=8000)
    app.run(debug=app_config["app"]["debug"],
            host=app_config["app"]["host"],
            port=app_config["app"]["port"],
            threaded=app_config["app"]["threaded"])
