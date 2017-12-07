# coding=utf-8
import json
import os.path
import re
from datetime import datetime

import numpy as np
import pandas as pd

import dialogue
import ner
from pmodel import PredModel

sws = "[！|“|”|‘|’|…|′|｜|、|，|。|〈|〉:：|《|》|「|」|『|』|【|】|〔|〕|︿|！|＃|＄|％|＆|＇|（|）|＊|＋|－|,．||；|＜|＝|＞|？|＠|［|］|＿|｛|｜|｝|～|↑|→|≈|①|②|③|④|⑤|⑥|⑦|⑧|⑨|⑩|￥|Δ|Ψ|γ|μ|φ|!|\"|'|#|\$|%|&|\*|\+|,|\.|;|\?|\\\|@|\(|\)|\[|\]|\^|_|`|\||\{|\}|~|<|>|=]"


class FindDoc:
    def __init__(self, text_config, model_path='./model/model-wiki-hdf-5k.bin',
                 seg_model_path="./model/cws.model",
                 pos_model_path="./model/pos.model",
                 dict_var_path="./model/dict_var.npy",
                 disease_symptom_file_dir="./model/disease-symptom3.data",
                 all_symptom_count_file_path="./model/all-symptom-count.data",
                 doctors_distributions_path="./model/doctors_distributions.json",
                 doctors_id_path="./model/doctors_id.txt",
                 symptoms_distributions_file_dir=""
                 ):
        self.text_config = text_config

        if os.path.isfile(all_symptom_count_file_path):
            self.all_symptom_count_file_path = all_symptom_count_file_path
        else:
            raise RuntimeError("cannot find model file: " + all_symptom_count_file_path)
        if os.path.isfile(model_path):
            self.model_path = model_path
        else:
            raise RuntimeError("cannot find model file: " + model_path)

        if os.path.isfile(seg_model_path):
            self.seg_model_path = seg_model_path
        else:
            raise RuntimeError("cannot find model file: " + seg_model_path)

        if os.path.isfile(pos_model_path):
            self.pos_model_path = pos_model_path
        else:
            raise RuntimeError("cannot find model file: " + pos_model_path)

        if os.path.isfile(dict_var_path):
            self.dict_var_path = dict_var_path
        else:
            raise RuntimeError("cannot find model file: " + dict_var_path)
        if os.path.isfile(disease_symptom_file_dir):
            self.disease_symptom_file_dir = disease_symptom_file_dir
        else:
            raise RuntimeError("cannot find model file: " + disease_symptom_file_dir)

        if os.path.isfile(doctors_distributions_path):
            self.doctors_distributions_path = doctors_distributions_path
        else:
            raise RuntimeError("cannot find model file: " + doctors_distributions_path)

        if os.path.isfile(doctors_id_path):
            self.doctors_id_path = doctors_id_path
        else:
            raise RuntimeError("cannot find model file: " + doctors_id_path)

        if os.path.isfile(symptoms_distributions_file_dir):
            self.symptoms_distributions_file_dir = symptoms_distributions_file_dir
        else:
            raise RuntimeError("cannot find model file: " + symptoms_distributions_file_dir)

    def load(self):

        # 不继续进行询问诊断的阈值,直接返回诊断结果
        self.NO_CONTINUE = self.text_config["NO_CONTINUE"]
        # 第2轮的提问文案
        self.NO_2_PROMPT = self.text_config["NO_2_PROMPT"]
        # 第3轮的提问文案
        self.NO_3_PROMPT = self.text_config["NO_3_PROMPT"]
        # 第x轮的"没有其他症状"的文案
        self.NO_SYMPTOMS_PROMPT = self.text_config["NO_SYMPTOMS_PROMPT"]

        self.p_model = PredModel(self.seg_model_path, self.pos_model_path, self.model_path, self.dict_var_path)
        self.segmentor = self.p_model.segmentor
        self.l3sym_dict, self.all_sym_count = dialogue.read_symptom_data(self.disease_symptom_file_dir,
                                                                         self.all_symptom_count_file_path)

        # 读医生模型给的doctor两个字典存到内存
        with open(self.doctors_distributions_path, 'r', encoding='utf-8') as fp:
            self.symptoms_rankings = json.load(fp)

        self.doctors_id_map = {}
        doctors_id_txt = pd.read_csv(self.doctors_id_path, sep='\t')
        doctor_id_temp = zip(doctors_id_txt['names'], doctors_id_txt['name_id'], doctors_id_txt['label'])
        for line in doctor_id_temp:
            self.doctors_id_map[line[0]] = {
                "name": line[0],
                "id": line[1],
                "label": line[2]
            }

        with open(self.symptoms_distributions_file_dir, 'r', encoding='utf-8') as fp:
            self.symptoms_dist = json.load(fp)

    # 医生模型的首轮推荐症状
    def get_common_symptoms(self, age, gender, month=None):
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
        index = 'M' + str(months[m - 1]) + 'M' + str(months[m]) + 'A' + str(ages[a - 1]) + 'A' + str(ages[a]) + gender
        return [item[0] for item in self.symptoms_dist[index]][0:5]

    # 医生模型的获取医生信息
    def get_doctors(self, codes, probs, age, gender):
        # get_doctors(['D39', 'L01'],[0.877,0.876,0.875,0.86],[0.557,0.556,0.555,0.55],gender='male',age=30)
        # sort input
        probs1 = [y for y, x in sorted(zip(probs, codes), reverse=True)]
        codes1 = [x for y, x in sorted(zip(probs, codes), reverse=True)]
        codes, probs = codes1, probs1

        doctors_rankings = {}
        ## diff pediatric and gyna and general
        if age <= 0.083:
            doctors_rankings = self.symptoms_rankings['newborn']
        elif gender == 'male' and age <= 18:
            doctors_rankings = self.symptoms_rankings['pediatrics']
        elif gender == 'female' and age <= 12:
            doctors_rankings = self.symptoms_rankings['pediatrics']
        elif gender == 'female' and age > 18:
            count = 0
            for item in ['N46', 'Q96', 'Z31', 'E28', 'N97', 'E16', 'L70', 'N92']:
                if item in codes:
                    count += 1
            if count >= len(codes) / 2:
                doctors_rankings = self.symptoms_rankings['reproductive']
            else:
                doctors_rankings = self.symptoms_rankings['gynaecology']
        elif gender == 'female':
            doctors_rankings = self.symptoms_rankings['general']

        rankings1 = []
        ## Find 6 doctors for the first disease
        if len(codes) > 0:
            code = codes[0]
            if code == 'J11':
                code = 'J06'
            temp = doctors_rankings[code]
            # temp = sorted(temp, key=lambda x: x[1] / (self.symptoms_rankings['doc_case_num'][x[0].strip()]),
            #               reverse=True)
            j = 0
            for tem in temp:
                if (tem[0] not in set(rankings1)) and (j < 10):
                    rankings1.append(tem[0])
                    j += 1

        ## remove '院际会诊' and get id of doctor
        results = []
        for name in rankings1:
            if name in self.doctors_id_map:
                # if name[0] in doctors_id_map.keys() and '会诊' not in name[0]:
                results.append(self.doctors_id_map[name])
            else:
                continue
        return results

    # 去掉停用词，并用空格替换
    def remove_stopwords(self, line):
        return re.sub(sws, " ", line)

    # 老大用的分词函数
    def process_sentences(self, sentences):
        words = []
        for sentence in sentences:
            sent = self.remove_stopwords(sentence)
            for word in self.segmentor.segment(sent):
                words.append(word)
        return words

    # shilei用的分词函数,包括老大的分词和使用标点分词的结果
    def process_sentences_sl(self, sentences):
        words = []
        for sentence in sentences:
            sent = self.remove_stopwords(sentence)
            for word in self.segmentor.segment(sent):
                words.append(word)
            sent = self.remove_stopwords(sentence)
            words.extend(sent.split(" "))
        return words

    # 得到用户历史所有已经选择的症状，和用户历史没有选择的症状列表
    def process_choice(self, sentences, all_choices):
        words_choices = []
        for sentence in sentences:
            sent = self.remove_stopwords(sentence)
            words_choices.extend(sent.split(" "))
        words_all_choices = []
        for all_choice in all_choices:
            words_all_choices.extend(all_choice)
        words_no_choices = []
        for choice in words_all_choices:
            if choice not in words_choices:
                words_no_choices.append(choice)
        return words_choices, words_no_choices

    # 在session中设置all_log，从而保存这个session的所有log,方便一次查看,缺点是会浪费taf的session内存
    # 同时注意不要被而已用户大量注入垃圾信息，所以设计了+1这样的设置。
    def update_session_log(self, session, all_log):
        if "all_log" not in session:
            session["all_log"] = [all_log]
        else:
            temp_all_log = []
            seqno = all_log["seqno"]
            for log in session["all_log"]:
                if log["seqno"] < seqno:
                    temp_all_log.append(log)
                elif log["seqno"] == seqno:
                    temp_all_log.append(all_log)
                elif log["seqno"] == seqno + 1:
                    temp_all_log.append(all_log)
            session["all_log"] = temp_all_log

    def get_all_choice_from_session_questions(self, session):
        result = []
        for question in session["questions"]:
            if "choice" in question:
                result.append(question["choice"])
        return result

    # 核心模型、主要的逻辑实现
    def find_doctors(self, session, seqno, choice_now, age, gender, debug=False):
        # 过滤掉用户通过点击输入的“以上都没有”，相当于输入为空，如果有其他内容，继续处理
        choice_now = choice_now.replace(self.NO_SYMPTOMS_PROMPT, " ")
        if "cardNo" in session["patient"]:
            userID = session["patient"]["cardNo"]
        else:
            userID = "没有从上游获取到"
        all_log = {"info": []}
        # 得到用户选择的症状和没有选择的症状
        all_log["choice_now"] = choice_now
        all_log["seqno"] = seqno
        all_log["age"] = age
        all_log["gender"] = gender
        # 用户历史的选择和历史的没选择
        symptoms, symptoms_no_chioce = self.process_choice(self.get_all_choice_from_session_questions(session),
                                                           [question["choices"] for question in session["questions"]])
        if seqno == 1:
            # 当用户第一轮的输入为空时候，返回不可诊断
            if choice_now.strip() == "":
                all_log["info"].append("当用户第一轮的输入为空时候，返回不可诊断")
                self.update_session_log(session, all_log)
                recommendation = {
                    "all_log": all_log
                }
                return "other", None, recommendation
            # jingwei的代码，进来先判断3种科室，不在目标科室则继续,有则返回
            dis_out = ['遗传咨询', '男科', '产科', "（非'遗传咨询', '男科', '产科'）[程序继续往下走]"]
            dis_out_id = ['6', '5', '8']
            all_log["jingwei的预测专科模型输入"] = choice_now.strip()
            label, prob_max = self.p_model.pre_predict(choice_now.strip(), age, gender)
            all_log["jingwei  pre_predict的计算值"] = str(prob_max)
            all_log["jingwei  pre_predict分到科室"] = dis_out[label]
            if label != 3:
                recommendation = {
                    "department":
                        {
                            'name': dis_out[label],
                            'id': dis_out_id[label]
                        }
                }
                if debug:
                    recommendation["all_log"] = all_log
                self.update_session_log(session, all_log)
                return "department", None, recommendation

            # if gender == "male" and age >= 18:
            #     all_log["info"].append("gender == 'male' and age >= 18,并且没有识别出是‘遗传咨询’,返回男科")
            #     recommendation = {
            #         "department":
            #             {
            #                 'name': "男科",
            #         'id': "5"
            #             }
            #     }
            #     if debug:
            #         recommendation["all_log"] = all_log
            #     self.update_session_log(session, all_log)

            if gender == "male" and age >= 18:
                all_log["info"].append("gender == 'male' and age >= 18,并且没有识别出是‘遗传咨询’,返回男科")
                self.update_session_log(session, all_log)
                recommendation = {
                    "all_log": all_log
                }
                return "other", None, recommendation

            # 进入jingwei的正常判断
            all_log["jingwei首轮模型输入"] = ",".join(self.get_all_choice_from_session_questions(session))
            # 诊断得到的疾病;识别到的症状
            diagnosis_disease_rate_list, input_list = dialogue.get_diagnosis_first(
                input=",".join(self.get_all_choice_from_session_questions(session)),
                model=self.p_model,
                age=age, gender=gender)

            all_log["jingwei识别疾病："] = diagnosis_disease_rate_list
            all_log["jingwei识别症状："] = input_list
            all_log["本轮为止,用户没有选择的所有症状"] = symptoms_no_chioce
            all_log["本轮为止,用户所有输入过的文本的分词"] = self.process_sentences_sl(
                self.get_all_choice_from_session_questions(session))

            # 如果jingwei返回了空,则表示输入的东西无意义,直接返回
            if diagnosis_disease_rate_list is None:
                all_log["info"].append("jingwei识别出输入的东西无意义,直接返回")
                self.update_session_log(session, all_log)
                recommendation = {
                    "all_log": all_log
                }
                return "other", None, recommendation

            # 医生模型的输入
            codes = []
            probs = []
            for v in diagnosis_disease_rate_list:
                codes.append(v[2])
                probs.append(v[1])
            # 如果阈值大于 NO_CONTINUE ,则直接返回诊断结果,不进行下一轮
            if probs[0] >= self.NO_CONTINUE:
                all_log["医生模型输入"] = [codes, probs, age, gender]
                recommendation = {
                    "doctors": self.get_doctors(codes=codes, probs=probs, age=age, gender=gender)
                }
                if debug:
                    recommendation["all_log"] = all_log
                    recommendation["jingwei"] = diagnosis_disease_rate_list
                self.update_session_log(session, all_log)
                return "doctors", None, recommendation

            # 记住jingwei的诊断结果,wangmeng下一轮使用
            session["diagnosis_disease_rate_list"] = diagnosis_disease_rate_list
            # wangmeng推荐算法
            ner_words, resp = ner.post(choice_now, userID)
            if "ner" not in session:

                session["ner"] = ner_words
            else:
                temp_ner = session["ner"]
                temp_ner.extend(ner_words)
                temp_ner = list(set(temp_ner))
                session["ner"] = temp_ner
            all_log["nlu历史记录"] = session["ner"]
            all_log["nlu输入"] = choice_now
            all_log["nlu-response"] = resp
            all_log["nlu-提取结果"] = ner_words
            symptoms_no_chioce.extend(session["ner"])
            # 记住ner的信息，之后还要用
            result = dialogue.core_method(self.l3sym_dict, diagnosis_disease_rate_list, input_list, symptoms_no_chioce,
                                          choice_history_words=self.process_sentences_sl(
                                              self.get_all_choice_from_session_questions(session)), seq=1,
                                          all_sym_count=self.all_sym_count)
            all_log["wangmeng症状推荐算法结果"] = result

            # 从结果中筛选出所有可以选择的症状,并增加"以上都没有"选项
            choices = [r["name"] for r in result["recommend_sym_list"]]
            choices.append(self.NO_SYMPTOMS_PROMPT)

            question = {
                "type": "multiple",
                "seqno": seqno + 1,
                "query": self.NO_2_PROMPT,
                "choices": choices
            }
            if debug:
                question["all_log"] = all_log
            self.update_session_log(session, all_log)
            return "followup", question, None
        elif seqno == 2:

            # 和上一轮的选择列表进行对比,判断用户本轮所有的输入是否全部来自选择，没有自己人工输入？
            choices_last = [question["choices"] for question in session["questions"]][-1]
            input_flag = True
            for choice in choice_now.split(","):
                if choice.strip() not in choices_last and choice.strip() != "":
                    input_flag = False
                    break
            all_log["info"].append("上一轮待选择:" + str(choices_last))
            all_log["info"].append("本轮选择:" + str(choice_now))
            all_log["info"].append("和上一轮的选择列表进行对比,判断用户本轮所有的输入是否全部来自选择，没有自己人工输入:" + str(input_flag))

            # 如果全部来自选择，则不经过土豪模型，而是取本次的结果和之前的症状，进输入王meng的模型
            if input_flag:
                all_log["info"].append("没有进入jingwei,进入wangmeng逻辑,直接推荐症状")

                # 获取到上一轮记录在session中jingwei识别出的疾病列表,避免重复访问jingwei模型
                diagnosis_disease_rate_list = session["diagnosis_disease_rate_list"]
                input_list = choice_now.split(",")
                all_log["jingwei上一轮识别疾病"] = diagnosis_disease_rate_list
                all_log["wangmeng推荐模型(相对概率)的输入"] = input_list
                all_log["本轮为止,用户没有选择的所有症状"] = symptoms_no_chioce
                all_log["本轮为止,用户所有输入过的文本的分词"] = self.process_sentences_sl(
                    self.get_all_choice_from_session_questions(session))
                ner_words, resp = ner.post(choice_now, userID)
                if "ner" not in session:
                    session["ner"] = ner_words
                else:
                    temp_ner = session["ner"]
                    temp_ner.extend(ner_words)
                    temp_ner = list(set(temp_ner))
                    session["ner"] = temp_ner
                all_log["nlu历史记录"] = session["ner"]
                all_log["nlu输入"] = choice_now
                all_log["nlu-response"] = resp
                all_log["nlu-提取结果"] = ner_words
                symptoms_no_chioce.extend(session["ner"])
                symptoms_no_chioce.extend(symptoms)
                result = dialogue.core_method(self.l3sym_dict, diagnosis_disease_rate_list, input_list,
                                              symptoms_no_chioce,
                                              choice_history_words=self.process_sentences_sl(
                                                  self.get_all_choice_from_session_questions(session)), seq=2,
                                              all_sym_count=self.all_sym_count)
            else:
                # 如果有了新的用户输入(不是从列表里选择的),则进入jingwei的模型
                all_log["info"].append("用户输入了新的描述,进入jingwei模型")
                all_log["jingwei模型输入"] = ",".join(self.get_all_choice_from_session_questions(session))
                diagnosis_disease_rate_list, input_list = dialogue.get_diagnosis_first(
                    input=",".join(self.get_all_choice_from_session_questions(session)),
                    model=self.p_model,
                    age=age,
                    gender=gender
                )
                # 如果阈值大于 NO_CONTINUE ,则直接返回诊断结果,不进行下一轮
                codes = []
                probs = []
                for v in diagnosis_disease_rate_list:
                    codes.append(v[2])
                    probs.append(v[1])
                if probs[0] >= self.NO_CONTINUE:
                    all_log["医生模型输入"] = [codes, probs, age, gender]
                    recommendation = {
                        "doctors": self.get_doctors(codes=codes, probs=probs, age=age, gender=gender)
                    }
                    if debug:
                        recommendation["all_log"] = all_log
                        recommendation["jingwei"] = diagnosis_disease_rate_list
                    self.update_session_log(session, all_log)
                    return "doctors", None, recommendation
                session["probs"] = probs[0]

                all_log["jingwei识别疾病"] = diagnosis_disease_rate_list
                all_log["jingwei识别症状"] = input_list
                # jingwei识别的疾病记录到session中
                session["diagnosis_disease_rate_list"] = diagnosis_disease_rate_list

                ner_words, resp = ner.post(choice_now, userID)
                if "ner" not in session:
                    session["ner"] = ner_words
                else:
                    temp_ner = session["ner"]
                    temp_ner.extend(ner_words)
                    temp_ner = list(set(temp_ner))
                    session["ner"] = temp_ner
                all_log["nlu历史记录"] = session["ner"]
                all_log["nlu输入"] = choice_now
                all_log["nlu-response"] = resp
                all_log["nlu-提取结果"] = ner_words
                symptoms_no_chioce.extend(session["ner"])
                symptoms_no_chioce.extend(symptoms)
                # 注意这里的seq=1
                result = dialogue.core_method(self.l3sym_dict, diagnosis_disease_rate_list, input_list,
                                              symptoms_no_chioce,
                                              choice_history_words=self.process_sentences_sl(
                                                  self.get_all_choice_from_session_questions(session)), seq=1,
                                              all_sym_count=self.all_sym_count)
                all_log["wangmeng症状推荐算法结果"] = result

            # 从结果中筛选出所有可以选择的症状,并增加"以上都没有"选项
            choices = [r["name"] for r in result["recommend_sym_list"]]
            choices.append(self.NO_SYMPTOMS_PROMPT)

            question = {
                "type": "multiple",
                "seqno": seqno + 1,
                "query": self.NO_3_PROMPT,
                "choices": choices
            }
            if debug:
                question["all_log"] = all_log
            self.update_session_log(session, all_log)
            return "followup", question, None
        # 最后一轮会给出诊断结果
        else:

            # 将历史所有记录进入jingwei的模型
            all_log["jingwei最后一轮输入"] = ",".join(self.get_all_choice_from_session_questions(session))
            diagnosis_disease_rate_list, input_list = dialogue.get_diagnosis_first(
                input=",".join(self.get_all_choice_from_session_questions(session)),
                model=self.p_model,
                age=age,
                gender=gender
            )
            # jingwei识别的疾病记录到session中
            session["diagnosis_disease_rate_list"] = diagnosis_disease_rate_list

            all_log["jingwei最终识别疾病,给医生模型进行获取医生"] = diagnosis_disease_rate_list
            all_log["jingwei最终识别症状（没有使用）"] = input_list

            # 疾病的icd10id和概率
            codes = []
            probs = []
            for v in diagnosis_disease_rate_list:
                codes.append(v[2])
                probs.append(v[1])
            all_log["医生模型输入"] = [codes, probs, age, gender]
            recommendation = {
                "doctors": self.get_doctors(codes=codes, probs=probs, age=age, gender=gender)
            }
            if debug:
                recommendation["all_log"] = all_log
                recommendation["jingwei"] = diagnosis_disease_rate_list
            self.update_session_log(session, all_log)
            return "doctors", None, recommendation
