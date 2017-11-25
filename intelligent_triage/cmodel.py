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
    def __init__(self, text_config, model_path='./model/model-wiki-hdf-5k.bin', seg_model_path="model/cws.model",
                 dict_var_path="./model/dict_var.npy",
                 disease_symptom_file_dir="./model/disease-symptom3.data",
                 all_symptom_count_file_path="./model/all-symptom-count.data",
                 doctors_distributions_path="./model/doctors_distributions.json",
                 doctors_id_path="./model/doctors_id.txt",
                 symptoms_distributions_file_dir=""):
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
        if os.path.isfile(dict_var_path):
            self.dict_var_path = dict_var_path
        else:
            raise RuntimeError("cannot find model file: " + seg_model_path)
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

        self.p_model = PredModel(self.seg_model_path, self.model_path, self.dict_var_path)
        self.segmentor = self.p_model.segmentor
        self.l3sym_dict, self.all_sym_count = dialogue.read_symptom_data(self.disease_symptom_file_dir,
                                                                         self.all_symptom_count_file_path)

        # 读丽娟给的doctor两个字典存到内存
        with open(self.doctors_distributions_path, 'r') as fp:
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

        with open(self.symptoms_distributions_file_dir, 'r') as fp:
            self.symptoms_dist = json.load(fp)

    # 丽娟的首轮推荐症状
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

    # 丽娟的获取医生信息
    def get_common_doctors(self, codes, probs, age, gender):
        # input: icd10 code: list; probs: list
        # get_common_doctors(['D39', 'L01'],gender='male',age=30)
        diff = -100 * np.diff(probs)
        x_stop = 4
        for ii in range(len(diff)):
            if diff[ii] > 1:
                x_stop = ii
                break

        codes = codes[0:x_stop + 1]
        probs = probs[0:x_stop + 1]

        rankings = dict()
        symptoms_rankings = {}
        ## diff pediatric and gyna and general
        if age <= 1:
            symptoms_rankings = self.symptoms_rankings['newborn']
        elif gender == 'male' and age <= 18:
            symptoms_rankings = self.symptoms_rankings['pediatrics']
        elif gender == 'female' and age <= 12:
            symptoms_rankings = self.symptoms_rankings['pediatrics']
        elif gender == 'female' and age > 18:
            count = 0
            for item in ['N46', 'Q96', 'Z31', 'E28', 'N97', 'E16', 'L70']:
                if item in codes:
                    count += 1
            if count >= len(codes) / 2:
                symptoms_rankings = self.symptoms_rankings['reproductive']
            else:
                symptoms_rankings = self.symptoms_rankings['gynaecology']
        elif gender == 'female':
            symptoms_rankings = self.symptoms_rankings['general']

        for i, code in enumerate(codes):
            if code in symptoms_rankings:
                for name, prob in symptoms_rankings[code]:
                    if code in rankings:
                        rankings[name] += prob / self.symptoms_rankings['doc_case_num'][name]
                    else:
                        rankings[name] = prob / self.symptoms_rankings['doc_case_num'][name]
            else:
                continue

        rankings = sorted(rankings.items(), key=lambda x: x[1], reverse=True)
        ## if no matched doctors, use general instead
        if len(rankings) == 0:
            if age <= 1:
                # print('newborn general')
                rankings = sorted(self.symptoms_rankings['gp_nb'].items(), key=lambda x: x[1][0], reverse=True)
            elif age <= 18:
                # print('pediatric general')
                rankings = sorted(self.symptoms_rankings['gp_ped'].items(), key=lambda x: x[1][0], reverse=True)
            elif gender == 'female' and age > 18:
                # print('gynaecology general')
                rankings = sorted(self.symptoms_rankings['gp_gyn'].items(), key=lambda x: x[1][0], reverse=True)

        ## remove '院际会诊' and get id of doctor
        results = []
        for name in rankings:
            if name[0] in self.doctors_id_map.keys() and '会诊' not in name[0]:
                # if name[0] in doctors_id_map.keys():
                results.append(self.doctors_id_map[name[0]])
            else:
                # print ('remove',name[0])
                continue
        return results[0:30]

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

    # 在session中设置log，这样方便在response前记录日志
    def update_session_log(self, session, all_log, log):
        if "all_log" not in session:
            session["all_log"] = [all_log]
        else:
            temp_all_log = session["all_log"]
            temp_all_log.append(all_log)
            session["all_log"] = temp_all_log

    # 核心模型、主要的逻辑实现
    def find_doctors(self, session, log, seqno, choice_now, age, gender, debug=False):
        # 过滤掉用户通过点击输入的“以上都没有”，相当于输入为空，如果有其他内容，继续处理
        choice_now = choice_now.replace(self.NO_SYMPTOMS_PROMPT, " ")
        all_log = {"info": []}
        # 得到用户选择的症状和没有选择的症状
        all_log["choice_now"] = choice_now
        all_log["seqno"] = seqno
        all_log["age"] = age
        all_log["gender"] = gender
        # 用户历史的选择和历史的没选择
        symptoms, symptoms_no_chioce = self.process_choice([question["choice"] for question in session["questions"]],
                                                           [question["choices"] for question in session["questions"]])
        if seqno == 1:
            # 当用户第一轮的输入为空时候，返回不可诊断
            if choice_now.strip() == "":
                all_log["info"].append("当用户第一轮的输入为空时候，返回不可诊断")
                self.update_session_log(session, all_log, log)
                recommendation = {
                    "all_log": all_log
                }
                return "other", None, recommendation
            # jingwei的代码，进来先判断3种科室，不在目标科室则继续,有则返回
            dis_out = ['遗传咨询', '男科', '产科', "无科室[程序继续往下走]"]
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
                self.update_session_log(session, all_log, log)
                return "department", None, recommendation

            # 进入jingwei的正常判断
            all_log["jingwei首轮模型输入"] = ",".join([question["choice"] for question in session["questions"]])
            # 诊断得到的疾病;识别到的症状
            diagnosis_disease_rate_dict, input_list = dialogue.get_diagnosis_first(
                input=",".join([question["choice"] for question in session["questions"]]),
                model=self.p_model,
                age=age, gender=gender)

            all_log["jingwei识别疾病："] = diagnosis_disease_rate_dict
            all_log["jingwei识别症状："] = input_list
            all_log["本轮为止,用户没有选择的所有症状"] = symptoms_no_chioce
            all_log["本轮为止,用户所有输入过的文本的分词"] = self.process_sentences_sl(
                [question["choice"] for question in session["questions"]])

            # 如果jingwei返回了空,则表示输入的东西无意义,直接返回
            if diagnosis_disease_rate_dict is None:
                self.update_session_log(session, all_log, log)
                recommendation = {
                    "all_log": all_log
                }
                return "other", None, recommendation

            # 丽娟的输入
            codes = []
            probs = []
            for v in diagnosis_disease_rate_dict.values():
                codes.append(v[1])
                probs.append(v[0])
            # 如果阈值大于 NO_CONTINUE ,则直接返回诊断结果,不进行下一轮
            if probs[0] >= self.NO_CONTINUE:
                all_log["丽娟输入"] = [codes, probs, age, gender]
                recommendation = {
                    "doctors": self.get_common_doctors(codes=codes, probs=probs, age=age, gender=gender)
                }
                if debug:
                    recommendation["all_log"] = all_log
                    recommendation["jingwei"] = diagnosis_disease_rate_dict
                self.update_session_log(session, all_log, log)
                return "doctors", None, recommendation

            # 记住jingwei的诊断结果,wangmeng下一轮使用
            session["diagnosis_disease_rate_dict"] = diagnosis_disease_rate_dict
            # wangmeng推荐算法
            ner_words, resp = ner.post(choice_now)
            if "ner" not in session:
                session["ner"] = ner_words
            else:
                session["ner"] = session["ner"].extend(ner_words)
            all_log["nlu历史记录"] = session["ner"]
            all_log["nlu输入"] = choice_now
            all_log["nlu-response"] = resp
            all_log["nlu-提取结果"] = ner_words
            symptoms_no_chioce.extend(session["ner"])
            # 记住ner的信息，之后还要用
            result = dialogue.core_method(self.l3sym_dict, diagnosis_disease_rate_dict, input_list, symptoms_no_chioce,
                                          choice_history_words=self.process_sentences_sl(
                                              [question["choice"] for question in session["questions"]]), seq=1,
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
            self.update_session_log(session, all_log, log)
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
                diagnosis_disease_rate_dict = session["diagnosis_disease_rate_dict"]
                input_list = choice_now.split(",")
                all_log["jingwei上一轮识别疾病"] = diagnosis_disease_rate_dict
                all_log["wangmeng推荐模型(相对概率)的输入"] = input_list
                all_log["本轮为止,用户没有选择的所有症状"] = symptoms_no_chioce
                all_log["本轮为止,用户所有输入过的文本的分词"] = self.process_sentences_sl(
                    [question["choice"] for question in session["questions"]])
                ner_words, resp = ner.post(choice_now)
                if "ner" not in session:
                    session["ner"] = ner_words
                else:
                    session["ner"] = session["ner"].extend(ner_words)
                all_log["nlu历史记录"] = session["ner"]
                all_log["nlu输入"] = choice_now
                all_log["nlu-response"] = resp
                all_log["nlu-提取结果"] = ner_words
                symptoms_no_chioce.extend(session["ner"])
                symptoms_no_chioce.extend(symptoms)
                result = dialogue.core_method(self.l3sym_dict, diagnosis_disease_rate_dict, input_list,
                                              symptoms_no_chioce,
                                              choice_history_words=self.process_sentences_sl(
                                                  [question["choice"] for question in session["questions"]]), seq=2,
                                              all_sym_count=self.all_sym_count)
            else:
                # 如果有了新的用户输入(不是从列表里选择的),则进入jingwei的模型
                all_log["info"].append("用户输入了新的描述,进入jingwei模型")
                all_log["jingwei模型输入"] = ",".join([question["choice"] for question in session["questions"]])
                diagnosis_disease_rate_dict, input_list = dialogue.get_diagnosis_first(
                    input=",".join([question["choice"] for question in session["questions"]]),
                    model=self.p_model,
                    age=age,
                    gender=gender
                )
                # 如果阈值大于 NO_CONTINUE ,则直接返回诊断结果,不进行下一轮
                codes = []
                probs = []
                for v in diagnosis_disease_rate_dict.values():
                    codes.append(v[1])
                    probs.append(v[0])
                if probs[0] >= self.NO_CONTINUE:
                    all_log["丽娟输入"] = [codes, probs, age, gender]
                    recommendation = {
                        "doctors": self.get_common_doctors(codes=codes, probs=probs, age=age, gender=gender)
                    }
                    if debug:
                        recommendation["all_log"] = all_log
                        recommendation["jingwei"] = diagnosis_disease_rate_dict
                    self.update_session_log(session, all_log, log)
                    return "doctors", None, recommendation
                session["probs"] = probs[0]

                all_log["jingwei识别疾病"] = diagnosis_disease_rate_dict
                all_log["jingwei识别症状"] = input_list
                # jingwei识别的疾病记录到session中
                session["diagnosis_disease_rate_dict"] = diagnosis_disease_rate_dict

                ner_words, resp = ner.post(choice_now)
                if "ner" not in session:
                    session["ner"] = ner_words
                else:
                    session["ner"] = session["ner"].extend(ner_words)
                all_log["nlu历史记录"] = session["ner"]
                all_log["nlu输入"] = choice_now
                all_log["nlu-response"] = resp
                all_log["nlu-提取结果"] = ner_words
                symptoms_no_chioce.extend(session["ner"])
                symptoms_no_chioce.extend(symptoms)
                # 注意这里的seq=1
                result = dialogue.core_method(self.l3sym_dict, diagnosis_disease_rate_dict, input_list,
                                              symptoms_no_chioce,
                                              choice_history_words=self.process_sentences_sl(
                                                  [question["choice"] for question in session["questions"]]), seq=1,
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
            self.update_session_log(session, all_log, log)
            return "followup", question, None
        # 最后一轮会给出诊断结果
        elif seqno == 3:

            # 将历史所有记录进入jingwei的模型
            all_log["jingwei最后一轮输入"] = ",".join([question["choice"] for question in session["questions"]])
            diagnosis_disease_rate_dict, input_list = dialogue.get_diagnosis_first(
                input=",".join([question["choice"] for question in session["questions"]]),
                model=self.p_model,
                age=age,
                gender=gender
            )
            all_log["jingwei最终识别疾病,给丽娟进行获取医生"] = diagnosis_disease_rate_dict
            all_log["jingwei最终识别症状（没有使用）"] = input_list

            # 疾病的icd10id和概率
            codes = []
            probs = []
            for v in diagnosis_disease_rate_dict.values():
                codes.append(v[1])
                probs.append(v[0])
            all_log["丽娟输入"] = [codes, probs, age, gender]
            recommendation = {
                "doctors": self.get_common_doctors(codes=codes, probs=probs, age=age, gender=gender)
            }
            if debug:
                recommendation["all_log"] = all_log
                recommendation["jingwei"] = diagnosis_disease_rate_dict
            self.update_session_log(session, all_log, log)
            return "doctors", None, recommendation
