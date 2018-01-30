# coding=utf-8
import json
import logging.config
import os
import random
import socket
import sys
import traceback
from datetime import datetime
from urllib.parse import urlparse, parse_qs

from flask import Flask, jsonify
from flask import request
from flask_cors import CORS

from db_util import Mongo

app = Flask(__name__)
# 返回的json串支持中文显示
app.config['JSON_AS_ASCII'] = False
# 允许跨域访问
CORS(app, supports_credentials=True)

# api版本信息和url
CLIENT_API_PREDICT = "/v1/predict"


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
def test():
    if random.randint(1, 10) > 5:
        1 / 0
    return "内部错误测试api随机通过,没有错误异常！"


# 处理所有未处理的异常
@app.errorhandler(Exception)
def unknow_error(error):
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


@app.route(CLIENT_API_PREDICT, methods=["GET"])
def predict():
    query_params = parse_qs(urlparse(request.url).query)
    # 记录请求日志
    log = {"type": "get", "url": request.url, "time": datetime.utcnow(), "ip": request.remote_addr}
    mongo.info(log)
    # 检查url参数合法性
    ok, res, code = predict_url_check(query_params)
    if not ok:
        mongo.error({"type": "predict_url_check", "code": code, "res": res, "url": request.url,
                     "time": datetime.utcnow(), "ip": request.remote_addr, "params": query_params})
        return jsonify(res), code

    sessionId = query_params["sessionId"][0]
    seqno = query_params["seqno"][0]
    input = query_params["input"][0]
    userId = query_params["userId"][0]
    gender = query_params["gender"][0]
    age = query_params["age"][0]
    k_disease = query_params["k_disease"][0]
    k_symptom = query_params["k_symptom"][0]

    # 记录返回日志
    log = {"type": "return", "params": query_params, "time": datetime.utcnow(),
           "ip": request.remote_addr, "url": request.url, }
    mongo.info(log)
    return jsonify({})


# 定义错误异常
def error(error_msg):
    return {
        "error": error_msg
    }


# 检查url参数合法性
def predict_url_check(query_params):
    if not ("sessionId" in query_params and "seqno" in query_params
            and "input" in query_params and "userId" in query_params
            and "k_disease" in query_params and "k_symptom" in query_params
            and "age" in query_params and "gender" in query_params):
        return False, error("错误的请求: url中没有包含sessionId或input或seqno或userId或age或gender或k_disease或k_symptom"), 400
    gender = query_params["gender"][0]
    if not (gender == "male" or gender == "female"):
        return False, error("错误的请求: 错误的数据格式(gender格式不对,应该是male或female)"), 400
    age = query_params["age"][0]
    try:
        age = float(age)
        if age < 0:
            return False, error("错误的请求: 错误的数据格式(age格式不对,应该是正整数或正浮点数)"), 400
    except ValueError:
        return False, error("错误的请求: 错误的数据格式(age格式不对,应该是正整数或正浮点数)"), 400
    k_disease = query_params["k_disease"][0]
    try:
        k_disease = int(k_disease)
        if k_disease < 0:
            return False, error("错误的请求: 错误的数据格式(k_disease格式不对,应该是正整数)"), 400
    except ValueError:
        return False, error("错误的请求: 错误的数据格式(k_disease格式不对,应该是正整数)"), 400
    k_symptom = query_params["k_symptom"][0]
    try:
        k_symptom = int(k_symptom)
        if k_symptom < 0:
            return False, error("错误的请求: 错误的数据格式(k_symptom 格式不对,应该是正整数)"), 400
    except ValueError:
        return False, error("错误的请求: 错误的数据格式(k_symptom 格式不对,应该是正整数)"), 400
    return True, None, None


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
    else:
        config_path = src_path() + "/conf/app_config.json"
    # 获取yaml配置文件
    app_config = load_config(config_path)
    ################################LOG日志文件#######################
    # 获取log配置文件
    if not os.path.exists("log/"):
        os.makedirs("log/")
    log_config_path = src_path() + "/conf/logger.conf"
    logging.config.fileConfig(log_config_path)
    # 记录程序中位置的错误，比如jignwei的模型突然出现不可预知的except，就捕获
    log_unkonw_error = logging.getLogger("unknown_error")
    ###############################模型文件加载#########################
    # 统计加载模型时间
    starttime = datetime.now()

    endtime = datetime.now()
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
