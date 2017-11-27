import json

import os
import pandas as pd
import sys


if __name__ == '__main__':
    # print(len(sys.argv))
    # if len(sys.argv) == 2:
    #     log_path = sys.argv[1]
    # else:
    #     print("参数不合法")
    #     exit(-1)
    log_path="logging_info.log"
    with open(log_path, "r") as file:
        all_lines = [L.strip() for L in file.readlines()]

    result = []
    result.append(["sessionId", "出生日期", "姓名", "性别", "就诊卡号", "回答轮数", "每一轮的问题和用户选择", "诊断结果", "开发人员每一轮的debug信息"])
    for x in all_lines[0:]:
        time, log_info, python_file, python_fun, python_line, content = x.split("---")
        if python_fun == "info_log":
            content_json = json.loads(content)
            sessionId = content_json["sessionId"]

            session = json.loads(content_json["sessionDataUpdate"])
            one_line = []
            one_line.append(sessionId)
            one_line.append(session["patient"]["dob"])
            one_line.append(session["patient"]["name"])
            one_line.append(session["patient"]["sex"])
            one_line.append(session["patient"]["cardNo"])
            one_line.append(len(session["questions"]))
            one_line.append(session["questions"])
            if "diagnosis_disease_rate_list" in session:
                one_line.append(session["diagnosis_disease_rate_list"])
            else:
                one_line.append([])
            one_line.append(session["all_log"])
            result.append(one_line)
    print(len(result))
    result = pd.DataFrame(result)
    if not os.path.exists("excel/"):
        os.makedirs("excel/")
    result.to_excel("excel/" + str(log_path) + '.xlsx', index=False, header=False)
