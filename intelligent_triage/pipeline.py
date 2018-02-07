import json
import os
from datetime import datetime

import numpy as np

import predict
from doctors import get_doctors


class Pipeline:
    # 检查模型文件在不在
    def __init__(self, app_config):
        self.root_path = app_config["model_file"]["root_path"]
        for hospital in app_config["model_file"]["hospital"].values():
            for file_type in ["doctor_path", "symptoms_distributions_path"]:
                hospital_file_path = self.root_path + hospital[file_type]
                if os.path.isfile(hospital_file_path):
                    self.symptoms_distributions_file_dir = hospital_file_path
                else:
                    raise RuntimeError("cannot find model file: " + hospital_file_path)

        self.app_config = app_config
        # 所有doctor,symptoms_distributions_path文件
        self.doctor_model_dict = {}
        self.symptoms_distributions_dict = {}

    # load模型文件
    def load(self):
        # 加载医院定制的所有doctor等文件
        for hospital in self.app_config["model_file"]["hospital"].values():
            # 加载推荐医生模型
            with open(self.root_path + hospital["doctor_path"], encoding="utf-8") as file:
                self.doctor_model_dict[hospital["orgId"]] = json.load(file)
            # 加载首轮推荐模型
            with open(self.root_path + hospital["symptoms_distributions_path"], encoding="utf-8") as file:
                self.symptoms_distributions_dict[hospital["orgId"]] = json.load(file)

    # 医生模型的首轮推荐症状,苏丽娟
    def get_common_symptoms(self, age, gender, orgid, month=None):
        # input: age: int, age>0; gender: {'F','M'}; month:int, [1,..12]
        # age = 12
        # gender = 'F'
        # month = 10
        # get_common_symptoms(age,gender,month)
        if gender == "female":
            gender = "F"
        else:
            gender = "M"

        # 成人男性，推荐以下男科症状
        if gender == "M" and age >= 18:
            return ["男性不育", "勃起困难", "排尿异常", "阴囊肿胀", "龟头疼痛"]

        if month is None:
            month = datetime.now().month

        # months = [1,2,3,4,5,6,7,8,9,10,11,12] # 12 months
        # genders = ['F', 'M']
        months = [0, 3, 6, 9, 12]  # 4 seasons
        genders = ['F', 'M']  # gender
        ages = [0, 0.083, 1, 6, 18, 30, 45, 150]  # 7 phases in year
        m = np.argmax(np.array(months) >= month)
        a = np.argmax(np.array(ages) >= age)
        index = 'M' + str(months[m - 1]) + 'M' + str(months[m]) + 'A' + str(ages[a - 1]) + 'A' + str(
            ages[a]) + gender
        return [item[0] for item in self.symptoms_distributions_dict[orgid][index]][0:5]

    # 获取历史所有的输入，用来icd10分类预测
    def get_all_choice_from_session_questions(self, session):
        result = []
        for question in session["questions"]:
            if "choice" in question:
                result.append(question["choice"])
        return ",".join(result)

    # 获取历史所有的症状选项,用来去重
    def get_all_choices_from_session_questions(self, session):
        result = []
        for question in session["questions"]:
            if "choices" in question:
                result.extend(question["choices"])
        return result

    # predict模型封装
    def get_diagnosis_first(self, session, age, gender, sessionId, userId, seqno):
        # 返回前k个疾病
        k_disease = 5
        # 返回前k个症状
        k_recommendation_symtom = 5
        # 调用predict
        # all_choice, all_choices, age, gender, k_disease, k_recommendation_symtom, sessionId, userId, seqno, url
        result, time_consuming, ok = predict.get(all_choice=self.get_all_choice_from_session_questions(session),
                                                 all_choices=self.get_all_choices_from_session_questions(session),
                                                 age=age, gender=gender, seqno=seqno,
                                                 k_disease=k_disease, k_recommendation_symtom=k_recommendation_symtom,
                                                 sessionId=sessionId, userId=userId, url=self.app_config["predict_url"])

        if not ok or len(result["diseases"]) == 0:
            return None, None, None, None, None
        else:
            diseases = result["diseases"]
            icd10 = result["icd10"]
            rate = result["rate"]
            recommendation_symtom = result["recommendation_symtom"]
            no_continue = result["no_continue"]
            return diseases, icd10, rate, recommendation_symtom, no_continue

    # 医生模型封装
    def get_doctors_impl(self, codes, probs, age, gender, orgId, clientId, branchId,
                         query_hospital_url, query_hospital_id, model, appointment, debug=False):
        doctors, ok = get_doctors(codes=codes, probs=probs, age=age, gender=gender,
                                  orgId=orgId, clientId=clientId, branchId=branchId,
                                  query_hospital_url=query_hospital_url,
                                  query_hospital_id=query_hospital_id,
                                  model=model, appointment=appointment, debug=debug)
        return doctors, ok

    # 核心模型、主要的逻辑实现
    def process(self, session, seqno, choice_now, age, gender, orgId, clientId, branchId, appointment, debug=False):

        userID = session["patient"]["cardNo"]

        # 当用户第一轮的输入为空时候，返回不可诊断
        if seqno == 1 and choice_now.strip() == "":
            return "other", None, None

        # 诊断得到的疾病;识别到的症状
        diseases, icd10, rate, recommendation_symtom, no_continue = self.get_diagnosis_first(
            session=session, age=age, gender=gender, sessionId=session["sessionId"], userId=userID, seqno=seqno)

        # 如果predict返回了空,则表示输入的东西无意义,直接返回
        if diseases is None:
            return "other", None, None

        # 如果 NO_CONTINUE(分类可信度很高，不需要进行继续提问) ,则直接返回诊断结果,不进行下一轮
        if no_continue:
            doctors, ok = self.get_doctors_impl(codes=icd10, probs=rate, age=age, gender=gender,
                                                query_hospital_url=self.app_config["query_hospital_url"],
                                                query_hospital_id=self.app_config["model_file"]["hospital"][orgId][
                                                    "query_hospital_id"],
                                                orgId=orgId, clientId=clientId, branchId=branchId,
                                                model=self.doctor_model_dict[orgId], appointment=appointment,
                                                debug=debug)
            # 如果ok=false，说明调用号源接口发生了异常
            if ok:
                recommendation = {
                    "doctors": doctors
                }
            else:
                return "error", None, None
            if debug:
                disease_rate_list = []
                for i, d in enumerate(diseases):
                    disease_rate_list.append([d, rate[i], icd10[i]])
                recommendation["jingwei"] = disease_rate_list
            return "doctors", None, recommendation
        if seqno < 3:
            question = {
                "type": "multiple",
                "seqno": seqno + 1,
                "query": self.app_config["text"]["NO_2_PROMPT"],
                "choices": recommendation_symtom
            }
            return "followup", question, None
        else:
            doctors, ok = self.get_doctors_impl(codes=icd10, probs=rate, age=age, gender=gender,
                                                query_hospital_url=self.app_config["query_hospital_url"],
                                                query_hospital_id=self.app_config["model_file"]["hospital"][orgId][
                                                    "query_hospital_id"],
                                                orgId=orgId, clientId=clientId, branchId=branchId,
                                                model=self.doctor_model_dict[orgId], appointment=appointment,
                                                debug=debug)
            if ok:
                recommendation = {
                    "doctors": doctors
                }
            else:
                return "error", None, None
            if debug:
                disease_rate_list = []
                for i, d in enumerate(diseases):
                    disease_rate_list.append([d, rate[i], icd10[i]])
                recommendation["jingwei"] = disease_rate_list
            return "doctors", None, recommendation
