# coding=utf-8
import json
import os
import time

import pandas as pd


def get_questions(content_json):
    yonghuhouxushuru = ""
    koushu = ""
    sanlunwenti = ""
    huidalunshu = len(content_json["questions"])
    for index, q in enumerate(content_json["questions"]):
        seqno = q["seqno"]
        choices = q["choices"]
        if "choice" in q:
            choice = q["choice"]
        else:
            choice = ""
        if seqno == 1:
            koushu = choice
            sanlunwenti = sanlunwenti + str(choices) + "\n"
        else:
            sanlunwenti = sanlunwenti + str(choices) + "\n"
            yonghuhouxushuru = yonghuhouxushuru + str(index) + ":" + str(choice) + "\n"

    return huidalunshu, koushu, yonghuhouxushuru, sanlunwenti


def get_recommendations(content_json):
    recommendation = content_json["recommendation"]
    if "department" in recommendation:
        return recommendation["department"]["name"]
    elif "other" in recommendation:
        return recommendation["other"]
    elif "doctors" in recommendation:
        one_line = ""
        for index, item in enumerate(recommendation["doctors"]):
            name = item["name"]
            label = item["label"]
            one_line = one_line + str(index) + ":" + str(name) + "(" + label + ")\n"
        return one_line
    else:
        return "暂时不能为您找到合适的医生"


def get_sex(sex):
    if sex == "male":
        return "男"
    else:
        return "女"


def deal_one_log_file(result, log_path):
    with open(log_path, "r", encoding="utf-8") as file:
        all_lines = [L.strip() for L in file.readlines()]
    for x in all_lines[0:]:
        all = x.split("---")
        if len(all) == 6:
            time, log_info, python_file, python_fun, python_line, content = all
            if python_fun == "info_log":
                content_json = json.loads(content)
                one_line = []
                one_line.append(content_json["time"])
                one_line.append(content_json["sessionId"])
                one_line.append(content_json["status"])
                one_line.append(content_json["patient"]["dob"])
                one_line.append(get_sex(content_json["patient"]["sex"]))
                if len("020000000322") != len(content_json["patient"]["cardNo"]):
                    continue
                one_line.append(content_json["patient"]["cardNo"])
                huidalunshu, koushu, yonghuhouxushuru, sanlunwenti = get_questions(content_json)
                one_line.append(huidalunshu)
                one_line.append(koushu)
                one_line.append(yonghuhouxushuru)
                one_line.append(get_recommendations(content_json))
                one_line.append(sanlunwenti)
                result.append(one_line)


def get_list_files(path):
    ret = []
    for file in os.listdir(path):
        if os.path.isfile(file):
            if "log" in file and ".py" not in file:
                print(file, "加入待处理文件！")
                ret.append(file)
    return ret


if __name__ == '__main__':

    result = []
    result.append(
        ["时间", "sessionId", "最终状态", "出生日期", "性别", "就诊卡号", "回答轮数", "口述", "用户回答", "问诊推荐", "三轮问题"])
    print("====================开始搜索文件==================")
    log_paths = get_list_files("./")
    print("====================搜索结束==================")
    print("搜索到文件个数：", len(log_paths))
    print("====================开始处理日志==================")

    for log_path in log_paths:
        deal_one_log_file(result=result, log_path=log_path)
    print("====================处理日志结束==================")

    print("一共处理记录条数:", len(result))
    result = pd.DataFrame(result)
    if not os.path.exists("excel/"):
        os.makedirs("excel/")
    nowtime = time.strftime('%Y_%m_%d_%H_%M_%S', time.localtime(time.time()))

    result.to_excel("excel/" + str(nowtime) + '.xlsx', index=False, header=False)
    print("输出文件位置:", "excel/" + str(nowtime) + '.xlsx')
