# coding=utf-8
import json
import os
import sys

import pandas as pd

if __name__ == '__main__':
    print("用户输入参数个数:", len(sys.argv) - 1)
    if len(sys.argv) == 2:
        log_path = sys.argv[1]
    else:
        print("参数不合法,请输入logging_info文件所在位置!")
        exit(-1)
    with open(log_path, "r") as file:
        all_lines = [L.strip() for L in file.readlines()]

    result = []
    result.append(
        ["时间", "sessionId", "最终状态", "出生日期", "姓名", "性别", "就诊卡号", "回答轮数", "每一轮的问题和用户选择", "诊断结果", "推荐结果",
         "开发人员每一轮的debug信息"])
    for x in all_lines[0:]:
        time, log_info, python_file, python_fun, python_line, content = x.split("---")
        if python_fun == "info_log":
            content_json = json.loads(content)
            one_line = []
            one_line.append(content_json["time"])
            one_line.append(content_json["sessionId"])
            one_line.append(content_json["status"])
            one_line.append(content_json["patient"]["dob"])
            one_line.append(content_json["patient"]["name"])
            one_line.append(content_json["patient"]["sex"])
            one_line.append(content_json["patient"]["cardNo"])
            one_line.append(len(content_json["questions"]))
            one_line.append(content_json["questions"])
            one_line.append(content_json["final_disease"])
            one_line.append(content_json["recommendation"])
            one_line.append(content_json["all_log"])
            result.append(one_line)
    print("处理日志结束！")
    print("一共处理记录条数:", len(result))
    result = pd.DataFrame(result)
    if not os.path.exists("excel/"):
        os.makedirs("excel/")
    result.to_excel("excel/" + str(log_path.split("/")[-1]) + '.xlsx', index=False, header=False)
    print("输出文件位置:", "excel/" + str(log_path.split("/")[-1]) + '.xlsx')
