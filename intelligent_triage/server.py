# coding=utf-8
import hashlib
import json
import logging.config
import os
import random
import re
import socket
import sys
import time
import traceback
from datetime import datetime
from urllib.parse import urlparse, parse_qs

from flask import Flask, jsonify
from flask import request
from flask_cors import CORS

from db_util import RedisCache, Mongo
from pipeline import Pipeline

app = Flask(__name__)

# 允许跨域访问
CORS(app, supports_credentials=True)

CLIENT_API_SESSIONS = "/v2/sessions"
CLIENT_API_DOCTORS = "/v2/doctors"
CLIENT_API_RECORD = "/v2/appointments"


# heartbeat handler
@app.route('/')
def index():
    return "OK", 200


# 负载均衡测试api
@app.route('/load-balance')
def load_balance():
    userIp = request.remote_addr
    return "用户ip:" + str(userIp) + "-后台服务标识码:" + str(server_ip).split(".")[3], 200


# 内部测试错误api
@app.route("/test-error/", methods=['Get'])
def t_error():
    if random.randint(1, 10) > 5:
        1 / 0
    return "内部错误测试api随机通过,没有错误！"


# @app.errorhandler(Exception)
def unknow_error(error):
    """"处理所有未处理的异常"""
    req = request.get_json()
    exstr = traceback.format_exc()
    error_data = {
        "req": req,
        "traceback": exstr,
        "error": str(error)
    }

    # 先在本地记录日志，防止mongo挂掉记不住日志
    log_unkonw_error.error(req)
    log_unkonw_error.exception(error)

    mongo.unknow_error(
        {"type": "unknow_error", "code": 500, "error_data": error_data, "url": request.url,
         "time": datetime.utcnow(), "ip": request.remote_addr})
    return "内部错误", 500


# 上报挂号成功！
@app.route(CLIENT_API_RECORD, methods=["POST"])
def record():
    ok, res, code = record_data_check(request)
    if not ok:
        mongo.error({"type": "record_check", "code": code, "res": res, "url": request.url, "data": request.json,
                     "time": datetime.utcnow(), "ip": request.remote_addr})
        return jsonify(res), code

    req = request.get_json()
    params = parse_qs(urlparse(request.url).query)
    req["params"] = params
    req["time"] = datetime.utcnow()
    req["ip"] = request.remote_addr
    mongo.record(req)
    return "ok"


# 创建session
@app.route(CLIENT_API_SESSIONS, methods=["POST"])
def creat_session():
    start_time = time.time()
    # 检查数据是否有效和url合法性
    ok, res, code = session_data_check(request)
    if not ok:
        mongo.error({"type": "creat_session_check", "code": code, "res": res, "url": request.url, "data": request.json,
                     "time": datetime.utcnow(), "ip": request.remote_addr})
        return jsonify(res), code

    req = request.get_json()
    params = parse_qs(urlparse(request.url).query)
    # clientId = params["clientId"][0]
    orgId = params["orgId"][0]
    # branchId = None
    # if "branchId" in params and len(params["branchId"]) > 0:
    #     branchId = params["branchId"][0]

    patient = req["patient"]
    dob = patient["dob"]
    gender = patient["sex"]
    cardNo = patient["cardNo"]
    wechatOpenId = req["wechatOpenId"]
    age = get_age_from_dob(dob)
    sessionId = wechatOpenId + "_" + cardNo + "_" + create_random_num_by_md5()
    # 获取推荐的初始症状
    symptoms = pipline.get_common_symptoms(age, gender, orgId)
    question = create_question('multiple', 1, app_config["text"]["NO_1_PROMPT"], symptoms)
    userRes = {
        'sessionId': sessionId,
        'greeting': app_config["text"]["GREETING_PROMPT"],
        'question': question
    }
    session = {"sessionId": sessionId, 'patient': patient, 'wechatOpenId': wechatOpenId, 'questions': [question]}
    dump_session(sessionId, session)
    time_consuming = round(1000 * (time.time() - start_time), 3)
    mongo.info({"type": "creat_session_done", "sessionId": sessionId,
                "session": session, "params": params,
                "time": datetime.utcnow(), "ip": request.remote_addr,
                "time_consuming": time_consuming})

    res = jsonify(userRes)
    return res


# 诊断并推荐症状、医生
@app.route(CLIENT_API_DOCTORS, methods=["GET"])
def find_doctors():
    start_time = time.time()
    # url检查
    ok, res, code = find_doctor_data_check(request)
    if not ok:
        mongo.error({"type": "find_doctors_check", "code": code, "res": res, "url": request.url, "data": request.json,
                     "time": datetime.utcnow(), "ip": request.remote_addr})
        return jsonify(res), code
    # 获取有用的信息
    params = parse_qs(urlparse(request.url).query)
    clientId = params["clientId"][0]
    orgId = params["orgId"][0]
    branchId = None
    # 和医院约定的参数
    appointment = None
    if "branchId" in params and len(params["branchId"]) > 0:
        branchId = params["branchId"][0]
    if "appointment" in params and len(params["appointment"]) > 0:
        appointment = params["appointment"][0]
    sessionId = params["sessionId"][0]
    seqno = int(params["seqno"][0])
    # python的特色，传空的时候取不到该值，其他语言或框架请忽略
    if "choice" not in params:
        choice = " "
    else:
        choice = params["choice"][0]
        xss_status, xss_desc = xss_defense_check(choice)
        if not xss_status:
            return error("错误的请求:" + xss_desc), 400

    # 是否在测试页面展示debug信息
    if "debug" in params and params["debug"][0] == "true":
        debug = True
    else:
        debug = False

    ok, session = load_session(sessionId)
    if not ok:
        mongo.error({"type": "redis错误", "sessionId": sessionId, "url": request.url,
                     "params": params, "session": session,
                     "time": datetime.utcnow(), "ip": request.remote_addr})
        return jsonify(error("sessionId错误（sessionId可能已经超时失效），请重新访问开始问诊")), 440
    session = update_session(session, seqno, choice)
    dob = session["patient"]["dob"]
    sex = session["patient"]["sex"]
    age = get_age_from_dob(dob)

    # 进入主要逻辑函数
    status, question, recommendation = pipline.process(session, seqno, choice, age, sex, orgId, clientId,
                                                       branchId, appointment, debug=debug)
    if status == "error":
        res = error("获取医生号源接口调用异常")
        time_consuming = round(1000 * (time.time() - start_time), 3)
        mongo.info({"type": status, "sessionId": sessionId, "url": request.url,
                    "params": params, "session": session,
                    "time": datetime.utcnow(), "ip": request.remote_addr,
                    "time_consuming": time_consuming})
        return jsonify(res), 502
    elif status == "followup":
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
                },
            }
    else:
        userRes = {
            'sessionId': sessionId,
            'status': 'other',
            'recommendation': {
                "other": app_config["text"]["STATUS_OTHER"]
            }
        }
    # 计算主要逻辑运行时间
    time_consuming = round(1000 * (time.time() - start_time), 3)

    mongo.info({"type": status, "sessionId": sessionId, "url": request.url,
                "params": params, "session": session,
                "time": datetime.utcnow(), "ip": request.remote_addr,
                "time_consuming": time_consuming})
    dump_session(sessionId, session)
    res = jsonify(userRes)
    return res


# 错误数据结构定义
def error(error_msg):
    return {
        "error": error_msg
    }


# 授权检查
def auth_check(request):
    url = urlparse(request.url)
    query = url.query
    query_params = parse_qs(query)
    if not ("clientId" in query_params and "orgId" in query_params
            and query_params["clientId"][0] in auth_clientId_set
            and query_params["orgId"][0] in auth_orgId_set):
        return False, error("未授权用户"), 401
    return True, None, None


# find_doctor_data函数的参数检查
def find_doctor_data_check(request):
    ok, res, code = auth_check(request)
    if not ok:
        return False, res, code
    url = urlparse(request.url)
    query = url.query
    query_params = parse_qs(query)
    if not ("sessionId" in query_params and
                    "seqno" in query_params and "query" in query_params and len(query_params["seqno"]) > 0):
        return False, error("错误的请求: url中没有包含choice或query或seqno"), 400
    return True, None, None


# 　参数检查
def record_data_check(request):
    ok, res, code = auth_check(request)
    if not ok:
        return False, res, code

    req = request.get_json()
    # 检查数据是否为空
    if req is None:
        res = error("错误的请求: 无法解析JSON 或 请求中请设置 'content-type' 为 'application/json' ")
        return False, res, 400
    # 检查数据是否有效
    if "patient" not in req or "doctor" not in req or "sessionId" not in req or "appointmentId" not in req or "wechatOpenId" not in req:
        return False, error("错误的请求: 错误的数据上报格式(字段缺失)"), 400
    if "cardNo" not in req["patient"] or "doctorId" not in req["doctor"]:
        return False, error("错误的请求: 错误的数据上报格式(cardNo或doctorId字段缺失)"), 400

    return True, None, None


# ｓｅｓｓｉｏｎ的参数检查
def session_data_check(request):
    ok, res, code = auth_check(request)
    if not ok:
        return False, res, code

    req = request.get_json()
    # 检查数据是否为空
    if req is None:
        res = error("错误的请求: 无法解析JSON 或 请求中请设置 'content-type' 为 'application/json' ")
        return False, res, 400
    # 检查数据是否有效
    if "patient" not in req or "wechatOpenId" not in req:
        return False, error("错误的请求: 错误的数据格式(字段缺失)"), 400
    patient = req["patient"]
    if "dob" not in patient or "cardNo" not in patient or "sex" not in patient or "name" not in patient:
        return False, error("错误的请求: 错误的数据格式(patient中字段缺失)"), 400
    dob = patient["dob"]
    gender = patient["sex"]
    # 出生日期一定要检测，这里是个坑。isv经常传错,造成后面程序bug！一定要检测！！一定要检测！！一定要检测！！
    if not (is_valid_date(dob) and len(dob) == 10):
        return False, error("错误的请求: 错误的数据格式(出生年月格式不对,示例：2018-02-01)"), 400
    if not (gender == "male" or gender == "female"):
        return False, error("错误的请求: 错误的数据格式(sex格式不对,应该是male或female)"), 400

    return True, None, None


# 从redis中loadsession
def load_session(id):
    try:
        sessionData = RedisCache(app_config).get_data(id).decode()
        session = json.loads(sessionData)
        return True, session
    except:
        return False, None


# 持久化session到redis中
def dump_session(sessionId, session):
    sessionData = json.dumps(session, ensure_ascii=False)
    RedisCache(app_config).set_data(sessionId, sessionData)
    # reidis最多 session保留24分钟
    RedisCache(app_config).get_connection().expire(sessionId, 60 * 24)


# 计算年龄
def get_age_from_dob(dob):
    birth = datetime.strptime(dob, "%Y-%m-%d")
    today = datetime.today()
    diff = (today - birth)
    ageInDays = diff.days
    return ageInDays / 365.


# 返回的问题的数据结构定义
def create_question(qtype, seqno, query, choices):
    return {
        'type': qtype,
        'seqno': seqno,
        'query': query,
        'choices': choices
    }


# 判断日期合法性
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


# 更新session
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


sql_key = ["select", "in", "from", "between", "aliases", "join", "union", "create", "null",
           "unique", "alter", "nulls", "avg", "sum", "max", "min", "len", "like", "where",
           "and", "order", "insert", "delete", "update", "top"]


# 检查异常请求
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


# 获取本机内网ip
def get_host_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip


# 获取本机内网ip
server_ip = get_host_ip()

if __name__ == '__main__':
    ######################其他配置文件加载##################################
    # 获取配置文件
    # 获取命令行参数
    if len(sys.argv) == 2:
        config_path = sys.argv[1]
        if "windows" in config_path:
            os.environ['http_proxy'] = 'http://dev-proxy.oa.com:8080'
    else:
        config_path = src_path() + "/conf/app_config.json"
    # 获取yaml配置文件
    app_config = load_config(config_path)

    ################################获得授权集合#######################
    auth_orgId_set = set()
    auth_clientId_set = set()
    for hospital in app_config["model_file"]["hospital"].values():
        auth_orgId_set.add(hospital["orgId"])
        auth_clientId_set.add(hospital["clientId"])
    ################################LOG日志文件#######################
    # 获取log配置文件
    if not os.path.exists("log/"):
        os.makedirs("log/")
    log_config_path = src_path() + "/conf/logger.conf"
    logging.config.fileConfig(log_config_path)
    # 通用日志
    log_info = logging.getLogger("myinfo")
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
    print("模型加载一共用时:" + str((endtime - starttime).seconds) + "秒" + "\nfinished loading models.\n server started .")

    ###########################初始化mongodb驱动###########################
    mongo = Mongo(app_config)
    mongo.info_log.insert({"loadtime": str((endtime - starttime).seconds), "type": "loadtime",
                           "time": datetime.utcnow(), "ip": server_ip})
    ######################### flask 启动##################################
    app.run(debug=app_config["app"]["debug"],
            host=app_config["app"]["host"],
            port=app_config["app"]["port"],
            threaded=app_config["app"]["threaded"])
