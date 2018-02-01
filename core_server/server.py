# coding=utf-8
import json
import logging.config
import os
import random
import re
import socket
import sys
import traceback
from datetime import datetime

from flask import Flask, jsonify
from flask import request
from flask_cors import CORS

import ner
from db_util import Mongo
from dialogue import Dialogue
from pmodel import PredModel

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
def ping_error():
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


@app.route(CLIENT_API_PREDICT, methods=["POST"])
def predict():
    post_data = request.get_json()
    # 记录请求日志
    log = {"type": "get", "url": request.url, "time": datetime.utcnow(),
           "ip": request.remote_addr, "post_data": post_data}
    mongo.info(log)
    # 检查url参数合法性
    ok, res, code = predict_data_check(post_data)
    if not ok:
        mongo.error({"type": "predict_url_check", "code": code, "res": res, "url": request.url,
                     "time": datetime.utcnow(), "ip": request.remote_addr, "post_data": post_data})
        return jsonify(res), code

    input = post_data["all_choice"]
    # 过滤掉用户通过点击输入的“以上都没有”，相当于输入为空，如果有其他内容，继续处理
    for x in app_config["no_symptoms"]:
        input = input.replace(x, " ")
    # predict的预测
    diseases, icd10, rate, symptoms, Coeff_sim_out, vcb = predictModel.predict(input=input,
                                                                               age=post_data["age"],
                                                                               gender=post_data["gender"],
                                                                               k_disease=post_data["k_disease"],
                                                                               k_symptom=5)
    nerlog = {}
    if diseases is None:
        result = {"diseases": [], "icd10": [], "rate": [], "recommendation_symtom": [], "no_continue": None}
    else:
        diseases = diseases.tolist()
        icd10 = icd10.tolist()
        symptoms = symptoms.tolist()
        # 疾病name,概率，icd10编号
        disease_rate_list = []
        for i, d in enumerate(diseases):
            disease_rate_list.append([d, rate[i], icd10[i]])

        # 用户输入过的东西分词后不再次推荐
        no_use_symtom_list = process_sentences_sl(post_data["all_choice"])
        # 用户没有选择过的选项不再次推荐
        no_use_symtom_list.extend(post_data["all_choices"])
        # ner识别出的同义词不再推荐
        ner_words, resp, ner_time = ner.post(post_data["all_choice"], post_data["user_id"])
        # 记录ner日志到mongo中
        nerlog = {"ner_words": ner_words, "resp": resp, "ner_time": ner_time}
        no_use_symtom_list.extend(ner_words)

        recommendation_symtom = dialogue.core_method(disease_rate_list=disease_rate_list, input_list=symptoms,
                                                     no_use_symtom_list=no_use_symtom_list, seqno=post_data["seqno"],
                                                     max_recommend_sym_num=post_data["k_recommendation_symtom"])
        result = {"diseases": diseases, "icd10": icd10, "rate": rate, "recommendation_symtom": recommendation_symtom}

        if rate[0] >= app_config["no_continue"]:
            result["no_continue"] = True
        else:
            result["no_continue"] = False

    # 记录返回日志
    log = {"type": "return", "post_data": post_data, "time": datetime.utcnow(),
           "ip": request.remote_addr, "url": request.url, "result": result,
           "ner": nerlog}
    mongo.info(log)
    return jsonify(result)


# 定义错误异常
def error(error_msg):
    return {
        "error": error_msg
    }


# 去掉停用词，并用空格替换
def remove_stopwords(line):
    sws = "[！|“|”|‘|’|…|′|｜|、|，|。|〈|〉:：|《|》|「|」|『|』|【|】|〔|〕|︿|！|＃|＄|％|＆|＇|（|）|＊|＋|－|,．||；|＜|＝|＞|？|＠|［|］|＿|｛|｜|｝|～|↑|→|≈|①|②|③|④|⑤|⑥|⑦|⑧|⑨|⑩|￥|Δ|Ψ|γ|μ|φ|!|\"|'|#|\$|%|&|\*|\+|,|\.|;|\?|\\\|@|\(|\)|\[|\]|\^|_|`|\||\{|\}|~|<|>|=]"
    return re.sub(sws, " ", line)


# 处理输入用的分词函数,包括ltp的分词和使用标点分词的结果
def process_sentences_sl(sentences):
    words = []
    for sentence in sentences:
        sent = remove_stopwords(sentence)
        for word in segmentor.segment(sent):
            words.append(word)
        sent = remove_stopwords(sentence)
        words.extend(sent.split(" "))
    return words


# 检查post参数合法性
def predict_data_check(post_data):
    # 检查数据是否为空
    if post_data is None:
        res = error("错误的请求: 无法解析JSON 或 请求中请设置 'content-type' 为 'application/json' ")
        return False, res, 400
    if not ("session_id" in post_data and "seqno" in post_data and "user_id" in post_data
            and "k_disease" in post_data and "k_recommendation_symtom" in post_data
            and "age" in post_data and "gender" in post_data
            and "all_choice" in post_data and "all_choices" in post_data):
        return False, error("错误的请求: json中缺少字段"), 400
    gender = post_data["gender"]
    if not (gender == "male" or gender == "female"):
        return False, error("错误的请求: 错误的数据格式(gender格式不对,应该是male或female)"), 400
    age = post_data["age"]
    try:
        age = float(age)
        if age < 0:
            return False, error("错误的请求: 错误的数据格式(age格式不对,应该是正整数或正浮点数)"), 400
    except ValueError:
        return False, error("错误的请求: 错误的数据格式(age格式不对,应该是正整数或正浮点数)"), 400
    k_disease = post_data["k_disease"]
    try:
        k_disease = int(k_disease)
        if k_disease < 0:
            return False, error("错误的请求: 错误的数据格式(k_disease格式不对,应该是正整数)"), 400
    except ValueError:
        return False, error("错误的请求: 错误的数据格式(k_disease格式不对,应该是正整数)"), 400
    k_recommendation_symtom = post_data["k_recommendation_symtom"]
    try:
        k_recommendation_symtom = int(k_recommendation_symtom)
        if k_recommendation_symtom < 0:
            return False, error("错误的请求: 错误的数据格式(k_recommendation_symtom 格式不对,应该是正整数)"), 400
    except ValueError:
        return False, error("错误的请求: 错误的数据格式(k_recommendation_symtom 格式不对,应该是正整数)"), 400
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
    predictModel = PredModel(
        seg_model_path=app_config["model_file"]["root_path"] + app_config["model_file"]["seg_model"],
        pos_model_path=app_config["model_file"]["root_path"] + app_config["model_file"]["pos_model"],
        w2v_model_path=app_config["model_file"]["root_path"] + app_config["model_file"]["fasttext_model"],
        dict_var_path=app_config["model_file"]["root_path"] + app_config["model_file"]["dict_var"])
    segmentor = predictModel.segmentor
    dialogue = Dialogue(
        disease_symptom_file_path=app_config["model_file"]["root_path"] + app_config["model_file"][
            "disease_symptom_file_dir"],
        all_symptom_count_file_path=app_config["model_file"]["root_path"] + app_config["model_file"][
            "all_symptom_count_file_path"])
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
