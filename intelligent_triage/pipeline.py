import json
import os
import re
from datetime import datetime
from pyltp import Segmentor, Postagger

import fastText
import numpy as np

import dialogue
import ner
import predict
from doctors import get_doctors


class Pipeline:
    # 检查模型文件在不在
    def __init__(self, app_config):
        self.root_path = app_config["model_file"]["root_path"]
        for hospital in app_config["model_file"]["hospital"]:
            for file_type in ["doctor_path", "predict_path", "symptoms_distributions_path"]:
                hospital_file_path = self.root_path + hospital[file_type]
                if os.path.isfile(hospital_file_path):
                    self.symptoms_distributions_file_dir = hospital_file_path
                else:
                    raise RuntimeError("cannot find model file: " + hospital_file_path)

        fasttext_model_dir = app_config["model_file"]["other"]["fasttext_model"]
        if os.path.isfile(self.root_path + fasttext_model_dir):
            self.fasttext_model_dir = self.root_path + fasttext_model_dir
        else:
            raise RuntimeError("cannot find model file: " + self.root_path + fasttext_model_dir)

        seg_model_dir = app_config["model_file"]["other"]["seg_model"]
        if os.path.isfile(self.root_path + seg_model_dir):
            self.seg_model_dir = self.root_path + seg_model_dir
        else:
            raise RuntimeError("cannot find model file: " + self.root_path + seg_model_dir)

        pos_model_dir = app_config["model_file"]["other"]["pos_model"]
        if os.path.isfile(self.root_path + pos_model_dir):
            self.pos_model_dir = self.root_path + pos_model_dir
        else:
            raise RuntimeError("cannot find model file: " + self.root_path + pos_model_dir)

        all_symptom_count_file_path = app_config["model_file"]["other"]["all_symptom_count_file_path"]
        if os.path.isfile(self.root_path + all_symptom_count_file_path):
            self.all_symptom_count_file_path = self.root_path + all_symptom_count_file_path
        else:
            raise RuntimeError("cannot find model file: " + self.root_path + all_symptom_count_file_path)

        disease_symptom_file_dir = app_config["model_file"]["other"]["disease_symptom_file_dir"]
        if os.path.isfile(self.root_path + disease_symptom_file_dir):
            self.disease_symptom_file_dir = self.root_path + disease_symptom_file_dir
        else:
            raise RuntimeError("cannot find model file: " + self.root_path + disease_symptom_file_dir)
        self.app_config = app_config
        # 所有doctor,predict,symptoms_distributions_path文件
        self.doctor_model_dict = {}
        self.predict_model_dict = {}
        self.symptoms_distributions_dict = {}

    # load模型文件
    def load(self):
        # 加载医院定制的所有doctor和predict文件
        for hospital in self.app_config["model_file"]["hospital"]:
            # 加载推荐医生模型
            with open(self.root_path + hospital["doctor_path"], encoding="utf-8") as file:
                self.doctor_model_dict[hospital["orgId"]] = json.load(file)
            # 加载首轮推荐模型
            with open(self.root_path + hospital["symptoms_distributions_path"], encoding="utf-8") as file:
                self.symptoms_distributions_dict[hospital["orgId"]] = json.load(file)
            # 加载医院推荐模型
            self.predict_model_dict[hospital["orgId"]] = np.load(self.root_path + hospital["predict_path"])
        # 加载字典模型
        self.segmentor = Segmentor()
        self.postagger = Postagger()
        self.segmentor.load(self.seg_model_dir)
        self.postagger.load(self.pos_model_dir)
        # 加载fasttext
        self.ft = fastText.load_model(self.fasttext_model_dir)
        # 加载多轮推荐症状字典
        self.l3sym_dict, self.all_sym_count = dialogue.read_symptom_data(self.disease_symptom_file_dir,
                                                                         self.all_symptom_count_file_path)

    # 医生模型的首轮推荐症状
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

    # 去掉停用词，并用空格替换
    def remove_stopwords(self, line):
        sws = "[！|“|”|‘|’|…|′|｜|、|，|。|〈|〉:：|《|》|「|」|『|』|【|】|〔|〕|︿|！|＃|＄|％|＆|＇|（|）|＊|＋|－|,．||；|＜|＝|＞|？|＠|［|］|＿|｛|｜|｝|～|↑|→|≈|①|②|③|④|⑤|⑥|⑦|⑧|⑨|⑩|￥|Δ|Ψ|γ|μ|φ|!|\"|'|#|\$|%|&|\*|\+|,|\.|;|\?|\\\|@|\(|\)|\[|\]|\^|_|`|\||\{|\}|~|<|>|=]"
        return re.sub(sws, " ", line)

    # 处理输入用的分词函数,包括ltp的分词和使用标点分词的结果
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

    # 在session中设置all_log，从而保存这个session的所有log,方便一次查看,缺点是会浪费session存储
    # 同时注意不要被已用户大量注入垃圾信息，所以设计了+1这样的设置。
    def update_session_log(self, session, all_log):
        if "all_log" not in session:
            session["all_log"] = [all_log]
        else:
            temp_all_log = []
            seqno = all_log["seqno"]
            for log in session["all_log"]:
                if log["seqno"] < seqno:
                    temp_all_log.append(log)
            temp_all_log.append(all_log)
            session["all_log"] = temp_all_log

    # 获取历史所有的输入
    def get_all_choice_from_session_questions(self, session):
        result = []
        for question in session["questions"]:
            if "choice" in question:
                result.append(question["choice"])
        return result

    # 京伟的predict模型封装
    def get_diagnosis_first(self, input, age, gender, k_disease, k_symptom, sessionId, userId, seqno):
        """
        接受京伟的数据,返回推荐列表，对话推荐需要的症状列表,还有丽娟需要的codes,probs
        """
        result, time_consuming, ok = predict.get(input=input, age=age, gender=gender,
                                                 k_disease=k_disease, k_symptom=k_symptom,
                                                 sessionId=sessionId, userId=userId, seqno=seqno)

        diseases = result["diseases"]
        icd10 = result["icd10"]
        rate = result["rate"]
        symptom = result["symptom"]
        if not ok:
            return None, None, None, None
        disease_rate_list = []
        for i, d in enumerate(diseases):
            disease_rate_list.append([d, rate[i], icd10[i]])
        return disease_rate_list, symptom, icd10, symptom

    # 核心模型、主要的逻辑实现
    def process(self, session, seqno, choice_now, age, gender, orgId, clientId, branchId, appointment, debug=False):

        userID = session["patient"]["cardNo"]
        all_log = {"info": []}

        all_log["choice_now"] = choice_now
        all_log["seqno"] = seqno
        all_log["age"] = age
        all_log["gender"] = gender
        # 用户历史的选择和历史的没选择
        symptoms, symptoms_no_chioce = self.process_choice(self.get_all_choice_from_session_questions(session),
                                                           [question["choices"] for question in
                                                            session["questions"]])
        # 第一轮
        if seqno == 1:
            # 当用户第一轮的输入为空时候，返回不可诊断
            if choice_now.strip() == "":
                all_log["info"].append("当用户第一轮的输入为空时候，返回不可诊断")
                self.update_session_log(session, all_log)
                recommendation = {
                    "all_log": all_log
                }
                return "other", None, recommendation

            # 进入jingwei的正常判断
            all_log["predict模型输入"] = ",".join(self.get_all_choice_from_session_questions(session))
            # 诊断得到的疾病;识别到的症状
            diagnosis_disease_rate_list, input_list, codes, probs = self.get_diagnosis_first(
                input=",".join(self.get_all_choice_from_session_questions(session)),
                age=age, gender=gender, dict_npy=self.predict_model_dict[orgId],
                segmentor=self.segmentor, postagger=self.postagger, fasttext=self.ft)

            all_log["predict识别疾病："] = diagnosis_disease_rate_list
            all_log["predict识别症状："] = input_list
            all_log["本轮为止,用户没有选择的所有症状"] = symptoms_no_chioce
            all_log["本轮为止,用户所有输入过的文本的分词"] = self.process_sentences_sl(
                self.get_all_choice_from_session_questions(session))

            # 如果predict返回了空,则表示输入的东西无意义,直接返回
            if diagnosis_disease_rate_list is None:
                all_log["info"].append("jingwei识别出输入的东西无意义,直接返回")
                self.update_session_log(session, all_log)
                recommendation = {
                    "all_log": all_log
                }
                return "other", None, recommendation

            # 如果阈值大于 NO_CONTINUE ,则直接返回诊断结果,不进行下一轮
            if probs[0] >= self.app_config["text"]["NO_CONTINUE"]:
                all_log["医生模型输入"] = [codes, probs, age, gender]
                recommendation = {
                    "doctors": get_doctors(codes=codes, probs=probs, age=age, gender=gender,
                                           orgId=orgId, clientId=clientId, branchId=branchId,
                                           model=self.doctor_model_dict[orgId], appointment=appointment)
                }
                if debug:
                    recommendation["all_log"] = all_log
                    recommendation["jingwei"] = diagnosis_disease_rate_list
                self.update_session_log(session, all_log)
                return "doctors", None, recommendation

            # 记住jingwei的诊断结果,wangmeng下一轮使用
            session["diagnosis_disease_rate_list"] = diagnosis_disease_rate_list

            # ner识别，用来避免推荐时候发生语义相近的重复推荐
            ner_words, resp, ner_time = ner.post(choice_now, userID)
            if "ner" not in session:
                session["ner_time"] = [ner_time]
                session["ner"] = ner_words
            else:
                # 记住ner的信息，之后还要用
                temp_ner = session["ner"]
                temp_ner.extend(ner_words)
                temp_ner = list(set(temp_ner))
                session["ner"] = temp_ner
                session["ner_time"].append(ner_time)
            all_log["nlu历史记录"] = session["ner"]
            all_log["nlu输入"] = choice_now
            all_log["nlu-response"] = resp
            all_log["nlu-提取结果"] = ner_words
            symptoms_no_chioce.extend(session["ner"])

            # wangmeng推荐算法
            result = dialogue.core_method(self.l3sym_dict, diagnosis_disease_rate_list, input_list,
                                          symptoms_no_chioce,
                                          choice_history_words=self.process_sentences_sl(
                                              self.get_all_choice_from_session_questions(session)), seq=1,
                                          all_sym_count=self.all_sym_count)
            all_log["wangmeng症状推荐算法结果"] = result

            # 从结果中筛选出所有可以选择的症状,并增加"以上都没有"选项
            choices = [r["name"] for r in result["recommend_sym_list"]]
            choices.append(self.app_config["text"]["NO_SYMPTOMS_PROMPT"])

            question = {
                "type": "multiple",
                "seqno": seqno + 1,
                "query": self.app_config["text"]["NO_2_PROMPT"],
                "choices": choices
            }
            # 如果开启了debug，则返回的结果中有过程信息
            if debug:
                question["all_log"] = all_log
            # 把日志更新到session中，方便session持久化时候能够记录日志
            self.update_session_log(session, all_log)
            return "followup", question, None

        # 第二轮
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

            # 如果全部来自选择，则不经过土豪模型，而是取本次的结果和之前的症状，进输入wangmeng的模型
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
                ner_words, resp, ner_time = ner.post(choice_now, userID)

                # ner识别，用来避免推荐时候发生语义相近的重复推荐
                if "ner" not in session:
                    session["ner_time"] = [ner_time]
                    session["ner"] = ner_words
                else:
                    temp_ner = session["ner"]
                    temp_ner.extend(ner_words)
                    temp_ner = list(set(temp_ner))
                    session["ner"] = temp_ner
                    session["ner_time"].append(ner_time)
                all_log["nlu历史记录"] = session["ner"]
                all_log["nlu输入"] = choice_now
                all_log["nlu-response"] = resp
                all_log["nlu-提取结果"] = ner_words
                # 将ner结果 和用户输入过得信息都放入一个里，以后不能推荐这些信息
                symptoms_no_chioce.extend(session["ner"])
                symptoms_no_chioce.extend(symptoms)
                # wangmeng推荐算法
                result = dialogue.core_method(self.l3sym_dict, diagnosis_disease_rate_list, input_list,
                                              symptoms_no_chioce,
                                              choice_history_words=self.process_sentences_sl(
                                                  self.get_all_choice_from_session_questions(session)), seq=2,
                                              all_sym_count=self.all_sym_count)
            else:
                # 如果有了新的用户输入(不是从列表里选择的),则进入jingwei的模型
                all_log["info"].append("用户输入了新的描述,进入jingwei模型")
                all_log["jingwei模型输入"] = ",".join(self.get_all_choice_from_session_questions(session))
                # jingwei的predict
                diagnosis_disease_rate_list, input_list, codes, probs = self.get_diagnosis_first(
                    input=",".join(self.get_all_choice_from_session_questions(session)),
                    age=age, gender=gender, dict_npy=self.predict_model_dict[orgId],
                    segmentor=self.segmentor, postagger=self.postagger, fasttext=self.ft)

                # 如果jingwei返回了空,则表示输入的东西无意义,直接返回
                if diagnosis_disease_rate_list is None:
                    all_log["info"].append("jingwei识别出输入的东西无意义,直接返回")
                    self.update_session_log(session, all_log)
                    recommendation = {
                        "all_log": all_log
                    }
                    return "other", None, recommendation

                # 如果阈值大于 NO_CONTINUE ,则直接返回诊断结果,不进行下一轮
                if probs[0] >= self.app_config["text"]["NO_CONTINUE"]:
                    all_log["医生模型输入"] = [codes, probs, age, gender]
                    recommendation = {
                        "doctors": get_doctors(codes=codes, probs=probs, age=age, gender=gender,
                                               orgId=orgId, clientId=clientId, branchId=branchId,
                                               model=self.doctor_model_dict[orgId], appointment=appointment)
                    }
                    if debug:
                        recommendation["all_log"] = all_log
                        recommendation["jingwei"] = diagnosis_disease_rate_list
                    self.update_session_log(session, all_log)
                    return "doctors", None, recommendation

                all_log["jingwei识别疾病"] = diagnosis_disease_rate_list
                all_log["jingwei识别症状"] = input_list
                # jingwei识别的疾病记录到session中
                session["diagnosis_disease_rate_list"] = diagnosis_disease_rate_list

                # ner处理
                ner_words, resp, ner_time = ner.post(choice_now, userID)
                if "ner" not in session:
                    session["ner_time"] = [ner_time]
                    session["ner"] = ner_words
                else:
                    temp_ner = session["ner"]
                    temp_ner.extend(ner_words)
                    temp_ner = list(set(temp_ner))
                    session["ner"] = temp_ner
                    session["ner_time"].append(ner_time)

                all_log["nlu历史记录"] = session["ner"]
                all_log["nlu输入"] = choice_now
                all_log["nlu-response"] = resp
                all_log["nlu-提取结果"] = ner_words
                symptoms_no_chioce.extend(session["ner"])
                symptoms_no_chioce.extend(symptoms)

                # wangmeng的推荐算法，注意这里的seq=1（意思是用户有新的输入，京伟会重新产生症状，推荐会重新开始）
                result = dialogue.core_method(self.l3sym_dict, diagnosis_disease_rate_list, input_list,
                                              symptoms_no_chioce,
                                              choice_history_words=self.process_sentences_sl(
                                                  self.get_all_choice_from_session_questions(session)), seq=1,
                                              all_sym_count=self.all_sym_count)
                all_log["wangmeng症状推荐算法结果"] = result

            # 从结果中筛选出所有可以选择的症状,并增加"以上都没有"选项
            choices = [r["name"] for r in result["recommend_sym_list"]]
            choices.append(self.app_config["text"]["NO_SYMPTOMS_PROMPT"])

            question = {
                "type": "multiple",
                "seqno": seqno + 1,
                "query": self.app_config["text"]["NO_3_PROMPT"],
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
            # jingwei的predict
            diagnosis_disease_rate_list, input_list, codes, probs = self.get_diagnosis_first(
                input=",".join(self.get_all_choice_from_session_questions(session)),
                age=age, gender=gender, dict_npy=self.predict_model_dict[orgId],
                segmentor=self.segmentor, postagger=self.postagger, fasttext=self.ft)
            # jingwei识别的疾病记录到session中
            session["diagnosis_disease_rate_list"] = diagnosis_disease_rate_list

            all_log["jingwei最终识别疾病,给医生模型进行获取医生"] = diagnosis_disease_rate_list
            all_log["jingwei最终识别症状（没有使用）"] = input_list

            # 如果jingwei返回了空,则表示输入的东西无意义,直接返回
            if diagnosis_disease_rate_list is None:
                all_log["info"].append("jingwei识别出输入的东西无意义,直接返回")
                self.update_session_log(session, all_log)
                recommendation = {
                    "all_log": all_log
                }
                return "other", None, recommendation

            all_log["医生模型输入"] = [codes, probs, age, gender]
            recommendation = {
                "doctors": get_doctors(codes=codes, probs=probs, age=age, gender=gender,
                                       orgId=orgId, clientId=clientId, branchId=branchId,
                                       model=self.doctor_model_dict[orgId], appointment=appointment)
            }
            if debug:
                recommendation["all_log"] = all_log
                recommendation["jingwei"] = diagnosis_disease_rate_list
            self.update_session_log(session, all_log)
            return "doctors", None, recommendation
