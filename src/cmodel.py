import json
import random

import fastText
import os.path
import re

from pmodel import PredModel

import dialogue

sws = "[！|“|”|‘|’|…|′|｜|、|，|。|〈|〉:：|《|》|「|」|『|』|【|】|〔|〕|︿|！|＃|＄|％|＆|＇|（|）|＊|＋|－|,．||；|＜|＝|＞|？|＠|［|］|＿|｛|｜|｝|～|↑|→|≈|①|②|③|④|⑤|⑥|⑦|⑧|⑨|⑩|￥|Δ|Ψ|γ|μ|φ|!|\"|'|#|\$|%|&|\*|\+|,|\.|;|\?|\\\|@|\(|\)|\[|\]|\^|_|`|\||\{|\}|~|<|>|=]"


class FindDoc:
    def __init__(self, model_path='./model/model-wiki-hdf-5k.bin', seg_model_path="model/cws.model",
                 dict_var_path="./model/dict_var.npy",
                 disease_symptom_file_dir="./model/disease-symptom3.data",
                 all_symptom_count_file_path="./model/all-symptom-count.data",
                 male_classifier_path="./model/model-hdf-5k-ml.ftz",
                 female_classifier_path="./model/model-hdf-5k-fm.ftz"):
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

        if os.path.isfile(male_classifier_path):
            self.male_classifier_path = male_classifier_path
        else:
            raise RuntimeError("cannot find model file: " + male_classifier_path)
        if os.path.isfile(female_classifier_path):
            self.female_classifier_path = female_classifier_path
        else:
            raise RuntimeError("cannot find model file: " + female_classifier_path)

    def load(self):
        self.p_model = PredModel(self.seg_model_path, self.model_path, self.dict_var_path)
        self.segmentor = self.p_model.segmentor
        self.l3sym_dict, self.all_sym_count = dialogue.read_symptom_data(self.disease_symptom_file_dir,
                                                                         self.all_symptom_count_file_path)
        self.male_classifier = fastText.load_model(self.male_classifier_path)
        self.female_classifier = fastText.load_model(self.female_classifier_path)

    def remove_stopwords(self, line):
        return re.sub(sws, " ", line)

    def process_sentences(self, sentences):
        words = []
        for sentence in sentences:
            sent = self.remove_stopwords(sentence)
            for word in self.segmentor.segment(sent):
                words.append(word)
        return words

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

    def classify(self, sentences):
        words = self.process_sentences(sentences)
        # print(" ".join(words))
        # print(self.model.predict(" ".join(words), 2))

    def find_doctors(self, session, log, seqno, choice_now, age, gender):
        all_log = {"info": []}
        # 得到用户选择的症状和没有选择的症状
        all_log["choice_now"] = choice_now
        all_log["seqno"] = seqno
        all_log["age"] = age
        all_log["gender"] = gender
        symptoms, symptoms_no_chioce = self.process_choice([question["choice"] for question in session["questions"]],
                                                           [question["choices"] for question in session["questions"]])
        seqno_now = seqno
        if seqno_now == 1:
            # 当用户第一轮的输入为空时候，返回不可诊断
            if choice_now.strip() == "":
                all_log["info"].append("当用户第一轮的输入为空时候，返回不可诊断")
                return "other", None, None
            if age >= 18:
                all_log["info"].append("年龄小于18岁")
                words = self.process_sentences([choice_now])
                all_log["info"].append("老大分词结果:" + " ".join(words))
                if gender == "male":
                    pred, prob = self.male_classifier.predict(" ".join(words))
                    all_log["info"].append("老大-male-pred:" + str(pred))
                    all_log["info"].append("老大-male-prob:" + str(prob))
                    if prob[0] > 0.9:
                        all_log["info"].append("分到科室：" + pred[0])
                        recommendation = {
                            "department":
                                {
                                    "id": '174',
                                    'name': pred[0]
                                }
                        }
                        log.debug(all_log)
                        return "department", None, recommendation
                        # 男科 和 男遗传
                    else:
                        all_log["info"].append("'男科和男遗传'分到成人男性的全科医生")
                        # 丽娟给医生
                        recommendation = {
                            "doctors": [
                                {
                                    "id": '20874',
                                    'name': '成人男性的全科医生AAA'
                                },
                                {
                                    "id": '20877',
                                    'name': '成人男性的全科医生BBB'
                                }
                            ]
                        }
                        log.debug(all_log)
                        return "doctors", None, recommendation
                else:
                    pred, prob = self.female_classifier.predict(" ".join(words))
                    all_log["info"].append("老大-female-pred:" + str(pred))
                    all_log["info"].append("老大-female-prob:" + str(prob))
                    if prob[0] > 0.9 and pred[0] in ["__label__产科", "__label__女遗传"]:
                        all_log["info"].append("分到科室:" + str(pred[0]))
                        recommendation = {
                            "department":
                                {
                                    "id": '174',
                                    'name': pred[0]
                                }
                        }
                        log.debug(all_log)
                        return "department", None, recommendation
                    else:
                        all_log["info"].append("女性大于18，且没有分到专科，进入后面的处理")
                        # print(pred, prob)
            all_log["info"].append("老大处理结束,进入jingwei的节奏")
            # 进入土豪的节奏
            diagnosis_disease_rate_dict, input_list = dialogue.get_diagnosis_first(
                input=",".join([question["choice"] for question in session["questions"]]),
                model=self.p_model,
                age=age, gender=gender)
            all_log["jingwei识别疾病："] = diagnosis_disease_rate_dict
            all_log["jingwei识别症状："] = input_list
            # 记住经纬的诊断结果
            session["diagnosis_disease_rate_dict"] = diagnosis_disease_rate_dict
            # 王萌的推荐结果,让用户选择
            all_log["symptoms_推荐结果，用户没有选择的历史纪录:"] = symptoms_no_chioce
            all_log["symptoms_chioce分词:"] = self.process_sentences(
                [question["choice"] for question in session["questions"]])
            result = dialogue.core_method(self.l3sym_dict, diagnosis_disease_rate_dict, input_list, symptoms_no_chioce,
                                          choice_history_words=self.process_sentences(
                                              [question["choice"] for question in session["questions"]]), seq=1,
                                          all_sym_count=self.all_sym_count)
            all_log["王萌推介结果"] = result
            question = {
                "type": "multiple",
                "seqno": seqno_now + 1,
                "query": "您有哪些不舒服的症状？",
                "choices": [r["name"] for r in result["recommend_sym_list"]],
                "all_log": all_log
            }
            log.debug(all_log)
            return "followup", question, None
        elif seqno_now == 2:

            # 用户所有的输入全部来自选择，没有自己人工输入？
            choices_last = [question["choices"] for question in session["questions"]][-1]
            input_flag = True
            for choice in choice_now.split(","):
                if choice.strip() not in choices_last and choice.strip() != "":
                    input_flag = False
                    break
            all_log["info"].append("choices_last:" + str(choices_last))
            all_log["info"].append("choice_now:" + str(choice_now))
            all_log["info"].append("判断是否全部来自选择而没有人工输入:" + str(input_flag))

            # 如果全部来自选择，则不经过土豪模型，而是取本次的结果和之前的症状，进输入王meng的模型
            if input_flag:
                all_log["info"].append("进入wangmeng")
                diagnosis_disease_rate_dict = session["diagnosis_disease_rate_dict"]
                input_list = choice_now.split(",")
                input_list.extend(symptoms)
                all_log["jingwei上一轮识别疾病"] = diagnosis_disease_rate_dict
                all_log["wangmeng input_list"] = input_list
                all_log["历史chioce分词:"] = self.process_sentences(
                    [question["choice"] for question in session["questions"]])
                result = dialogue.core_method(self.l3sym_dict, diagnosis_disease_rate_dict, input_list,
                                              symptoms_no_chioce,
                                              choice_history_words=self.process_sentences(
                                                  [question["choice"] for question in session["questions"]]), seq=2,
                                              all_sym_count=self.all_sym_count)
            else:
                all_log["info"].append("进入jingwei")
                # 如果有了新的人工输入,则进入土豪的模型
                all_log["jingwei输入"] = ",".join([question["choice"] for question in session["questions"]])
                diagnosis_disease_rate_dict, input_list = dialogue.get_diagnosis_first(
                    input=",".join([question["choice"] for question in session["questions"]]),
                    model=self.p_model,
                    age=age,
                    gender=gender
                )
                all_log["jingwei识别疾病"] = diagnosis_disease_rate_dict
                all_log["jingwei识别症状"] = input_list
                session["diagnosis_disease_rate_dict"] = diagnosis_disease_rate_dict

                result = dialogue.core_method(self.l3sym_dict, diagnosis_disease_rate_dict, input_list,
                                              symptoms_no_chioce,
                                              choice_history_words=self.process_sentences(
                                                  [question["choice"] for question in session["questions"]]), seq=2,
                                              all_sym_count=self.all_sym_count)
                all_log["王萌推介结果"] = result
            question = {
                "type": "multiple",
                "seqno": seqno_now + 1,
                "query": "您有哪些不舒服的症状?",
                "choices": [r["name"] for r in result["recommend_sym_list"]],
                "all_log": all_log
            }
            # 2仅仅推荐症状,最后一轮推荐doctor
            log.debug(all_log)
            return "followup", question, None
        # 最后一轮会计算疾病的概率，并推荐医生（目前有两种策略，之后会进行对比评测）
        else:
            diagnosis_disease_rate_dict = session["diagnosis_disease_rate_dict"]
            input_list = choice_now.split(",")
            input_list.extend(symptoms)
            all_log["jingwei上一轮识别疾病"] = diagnosis_disease_rate_dict
            all_log["wangmeng input_list"] = input_list
            all_log["历史chioce分词:"] = self.process_sentences([question["choice"] for question in session["questions"]])
            result = dialogue.core_method(self.l3sym_dict, diagnosis_disease_rate_dict, input_list, symptoms_no_chioce,
                                          choice_history_words=self.process_sentences(
                                              [question["choice"] for question in session["questions"]]), seq=3,
                                          all_sym_count=self.all_sym_count)
            all_log["王萌疾病排序"] = [d for d in result["diagnosis_list"]]
            all_log["jingwei最后一轮输入"] = ",".join([question["choice"] for question in session["questions"]])
            diagnosis_disease_rate_dict, input_list = dialogue.get_diagnosis_first(
                input=",".join([question["choice"] for question in session["questions"]]),
                model=self.p_model,
                age=age,
                gender=gender
            )
            all_log["jingwei最终识别疾病"] = diagnosis_disease_rate_dict
            all_log["jingwei最终识别症状（没有使用）"] = input_list
            recommendation = {
                "all_log": all_log,
                "jingwei": diagnosis_disease_rate_dict,
                "wangmeng": [d["l3name"] for d in result["diagnosis_list"]],
                "doctors": [
                    {
                        "id": '20874',
                        'name': '周利娟'
                    },
                    {
                        "id": '20877',
                        'name': '李婷婷'
                    }
                ]
            }
            log.debug(all_log)
            return "doctors", None, recommendation

    def find_doctors_test(self, seqno):
        seqno_now = seqno
        if seqno_now == 1:

            question = {
                "type": "multiple",
                "seqno": seqno_now + 1,
                "query": "您有哪些不舒服的症状？",
                "choices": ['拉肚子', '头部不舒服', '感冒']
            }
            return "followup", question, None
        elif seqno_now == 2:
            question = {
                "type": "multiple",
                "seqno": seqno_now + 1,
                "query": "您有哪些不舒服的症状？",
                "choices": ['拉肚子', '头部不舒服', '感冒']
            }
            return "followup", question, None
        else:
            a = random.randint(1, 3)
            if a == 1:
                recommendation = {
                    "doctors": [
                        {
                            "id": '20874',
                            'name': '周利娟'
                        },
                        {
                            "id": '20877',
                            'name': '李婷婷'
                        }
                    ]
                }
                return "doctors", None, recommendation
            elif a == 2:
                recommendation = {
                    "department":
                        {
                            "id": '174',
                            'name': '产科'
                        }
                }
                return "department", None, recommendation
            elif a == 3:
                return "other", None, None
