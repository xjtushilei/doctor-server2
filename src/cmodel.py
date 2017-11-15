import random

import fastText
import os.path
import re
from pprint import pprint
from pyltp import Segmentor
from pmodel import PredModel

import dialogue

sws = "[！|“|”|‘|’|…|′|｜|、|，|。|〈|〉:：|《|》|「|」|『|』|【|】|〔|〕|︿|！|＃|＄|％|＆|＇|（|）|＊|＋|－|,．||；|＜|＝|＞|？|＠|［|］|＿|｛|｜|｝|～|↑|→|≈|①|②|③|④|⑤|⑥|⑦|⑧|⑨|⑩|￥|Δ|Ψ|γ|μ|φ|!|\"|'|#|\$|%|&|\*|\+|,|\.|;|\?|\\\|@|\(|\)|\[|\]|\^|_|`|\||\{|\}|~|<|>|=]"

class FindDoc:
    def __init__(self, model_path='./model/model-wiki-hdf-5k.bin', seg_model_path="model/cws.model",
                 dict_var_path="./model/dict_var.npy",
                 disease_symptom_file_dir="./model/disease-symptom3.data",
                 male_classifier_path="./model/model-hdf-5k-ml.ftz",
                 female_classifier_path="./model/model-hdf-5k-fm.ftz"):
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
        self.l3sym_dict = dialogue.read_symptom_data(self.disease_symptom_file_dir)
        # self.male_classifier = fastText.load_model(self.male_classifier_path)
        self.male_classifier = fastText.load_model("/tvm/mdata/jerryzchen/model/model-hdf-5k-ml.ftz")
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
        print(" ".join(words))
        print(self.model.predict(" ".join(words), 2))

    def find_doctors(self, session, log, seqno, choice_now, age, gender):
        # 得到用户选择的症状和没有选择的症状
        symptoms, symptoms_no_chioce = self.process_choice([question["choice"] for question in session["questions"]],
                                                           [question["choices"] for question in session["questions"]])
        seqno_now = seqno
        if seqno_now == 1:
            # 当用户第一轮的输入为空时候，返回不可诊断
            if choice_now.strip() == "":
                return "other", None, None
            log.debug("seqno_now:" + str(seqno_now))
            log.debug("老大进行第一轮的处理，分类器筛选掉诊断不了的病")
            words = self.process_sentences([choice_now])
            log.debug("老大分词结果:" +" ".join(words))
            print(gender,age)
            if gender == "male":
                print("m")
                pred, prob = self.male_classifier.predict(" ".join(words))
                if prob[0] > 0.9:
                    log.debug("分到科室：" + pred[0])
                    recommendation = {
                        "department":
                            {
                                "id": '174',
                                'name': pred[0]
                                ,"debug":"男科 和 男遗传"
                            }
                    }
                    return "department", None, recommendation
                    #男科 和 男遗传
                else:
                    log.debug("分到成人男性的全科医生")
                    #丽娟给医生
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
                    return "doctors", None, recommendation
            else:
                print("f")
                pred, prob = self.female_classifier.predict(" ".join(words))
                if prob[0] > 0.9 and pred[0] in ["__label__产科", "__label__女遗传"]:
                    #pass
                    log.debug("分到科室：" + pred[0])
                    recommendation = {
                        "department":
                            {
                                "id": '174',
                                'name': pred[0]
                                , "debug": "分到科室:产科，女性遗传"
                            }
                    }
                    return "department", None, recommendation
                else:
                    log.debug("进入后面的处理")
            print(pred, prob)
            log.debug("老大处理结束，this disease can deal")
            log.debug("seqno_now:" + str(seqno_now))
            # 进入土豪的节奏
            log.info(",".join([question["choice"] for question in session["questions"]]))
            diagnosis_disease_rate_dict, input_list = dialogue.get_diagnosis_first(
                input=",".join([question["choice"] for question in session["questions"]]),
                model=self.p_model,
                age=age, gender=gender)
            log.info(diagnosis_disease_rate_dict)

            # 记住经纬的诊断结果
            session["diagnosis_disease_rate_dict"] = diagnosis_disease_rate_dict
            log.debug(diagnosis_disease_rate_dict)
            # 王萌的推荐结果,让用户选择
            result = dialogue.core_method(self.l3sym_dict, diagnosis_disease_rate_dict, input_list, symptoms_no_chioce)

            question = {
                "type": "multiple",
                "seqno": seqno_now + 1,
                "query": "您有哪些不舒服的症状？",
                "choices": [r["name"] for r in result["recommend_sym_list"]]
            }
            log.debug(question)
            return "followup", question, None
        elif seqno_now <= 3:
            log.debug("seqno_now:" + str(seqno_now))

            log.debug("判断是否全部来自选择而没有人工输入？")
            # 用户所有的输入全部来自选择，没有自己人工输入？
            choices_last = [question["choices"] for question in session["questions"]][-1]
            input_flag = True
            log.debug(choice_now.split(","))
            log.debug(choices_last)
            for choice in choice_now.split(","):
                if choice.strip() not in choices_last and choice.strip() != "":
                    input_flag = False
                    break
            log.debug(input_flag)

            # 如果全部来自选择，则不经过土豪模型，而是取本次的结果和之前的症状，进输入王meng的模型
            if input_flag:
                diagnosis_disease_rate_dict = session["diagnosis_disease_rate_dict"]
                input_list = choice_now.split(",")
                input_list.extend(symptoms)
                result = dialogue.core_method(self.l3sym_dict, diagnosis_disease_rate_dict, input_list,
                                              symptoms_no_chioce)
            else:
                # 如果有了新的人工输入,则进入土豪的模型
                log.info(",".join([question["choice"] for question in session["questions"]]))
                diagnosis_disease_rate_dict, input_list = dialogue.get_diagnosis_first(
                    input=",".join([question["choice"] for question in session["questions"]]),
                    model=self.p_model,
                    age=age,
                    gender=gender
                )
                log.info(diagnosis_disease_rate_dict)
                session["diagnosis_disease_rate_dict"] = diagnosis_disease_rate_dict
                log.debug(diagnosis_disease_rate_dict)
                result = dialogue.core_method(self.l3sym_dict, diagnosis_disease_rate_dict, input_list,
                                              symptoms_no_chioce)
            question = {
                "type": "multiple",
                "seqno": seqno_now + 1,
                "query": "您有哪些不舒服的症状?",
                "choices": [r["name"] for r in result["recommend_sym_list"]]
            }
            # 2~3轮仅仅推荐症状,最后一轮推荐doctor
            log.debug(question)
            return "followup", question, None
        # 最后一轮会计算疾病的概率，并推荐医生（目前有两种策略，之后会进行对比评测）
        else:
            diagnosis_disease_rate_dict = session["diagnosis_disease_rate_dict"]
            choice_now = [question["choice"] for question in session["questions"]][-1].strip()
            input_list = choice_now.split(",")
            input_list.extend(symptoms)
            result = dialogue.core_method(self.l3sym_dict, diagnosis_disease_rate_dict, input_list, symptoms_no_chioce)
            log.debug("王萌的疾病排序:")
            log.debug([d["l3name"] for d in result["diagnosis_list"]])
            log.info(",".join([question["choice"] for question in session["questions"]]))
            diagnosis_disease_rate_dict, input_list = dialogue.get_diagnosis_first(
                input=",".join([question["choice"] for question in session["questions"]]),
                model=self.p_model,
                age=age,
                gender=gender
            )
            log.info(diagnosis_disease_rate_dict)
            # 土豪的诊断结果
            log.debug(diagnosis_disease_rate_dict.keys())
            recommendation = {
                "jingwei": diagnosis_disease_rate_dict,
                "wangmeng": [d["l3name"] for d in result["diagnosis_list"]]
                # "doctors": [
                #     {
                #         "id": '20874',
                #         'name': '周利娟'
                #     },
                #     {
                #         "id": '20877',
                #         'name': '李婷婷'
                #     }
                # ]
            }
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
        elif seqno_now == 3:
            question = {
                "type": "multiple",
                "seqno": seqno_now + 1,
                "query": "您有哪些不舒服的症状？",
                "choices": ['怀孕', '呕吐', '眼睛红肿']
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
