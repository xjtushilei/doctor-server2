import json

from pmodel import PredModel


def read_symptom_data(disease_symptom_file_dir='./model/disease-symptom3.data'):
    """
    disease and 症状
    :return: level3的dict
    """
    with open(disease_symptom_file_dir, encoding="utf-8") as file:
        return json.load(file)


def get_diagnosis_first(input, model, age=20, gender="m"):
    """
    接受京伟的数据
    :return: 两个东西(1.疾病的名字和概率的dict；2.京伟给出的症状列表，之后作为我们的输入)
    """

    K_Top_dis = 5
    K_Top_symp = 5

    diseases, icd10, val, symp_out, Coeff_sim_out = model.predict(input, age, gender, K_Top_dis, K_Top_symp)
    nvs = zip(symp_out, Coeff_sim_out)
    symp_list = [symp for symp, value in nvs]
    disease_rate_dict = {}
    for i, d in enumerate(diseases):
        disease_rate_dict[d] = [val[i], icd10[i]]
    return disease_rate_dict, symp_list


def calculate_p_sym(l3sym_map_less, S_i_name, S_j_name):
    """
    计算症状j 在症状i出现的情况下症状j出现的概率
    :param l3sym_map_less: 待计算的疾病集合
    :param S_i_name: 症状i名字
    :param S_j_name: 症状j名字
    :return: 概率
    """
    Cj = 0.0
    Cij = 0.0
    for obj in l3sym_map_less:
        if S_j_name in obj["all_sym_dic"]:
            Cj += 1
            if S_i_name in obj["all_sym_dic"]:
                Cij += 1
    return Cij / Cj


def calculate_p_sym_plus(rateList):
    """
    n个事件的概率加法公式计算
    :param rateList: n个独立事件的概率
    :return: 概率和
    """
    p = 0.0
    for (i, rate) in enumerate(rateList):
        if i == 0:
            p = rate
        else:
            p = p + rate - p * rate
    return p


def core_method(l3sym_dict, disease_rate_dict=None, input_list=None, no_use_input_list=[],
                max_recommend_sym_num=5, choice_history_words=[], seq=1):
    rate_matrix = {}
    # disease that we need from all disease
    l3sym_dict_we_need = []
    # 是否匹配到症状，大于0则匹配到
    normal_recommendation = False

    # select disease that we need from all disease
    for (d, obj) in l3sym_dict.items():
        # select 京伟给的疾病
        if d in disease_rate_dict:
            # 遭受了什么症状
            suffer_sym_dic = {}
            for (sym_name, sym_rate) in obj["all_sym_dic"].items():
                if sym_name in input_list:
                    suffer_sym_dic[sym_name] = sym_rate
                    normal_recommendation = True
            # 将该疾病的其他症状加入待计算列表里
            for (s, r) in obj["all_sym_dic"].items():
                # 这个症状不在待计算里，不在输入里，不在原始输入分词后的结果里
                if s not in rate_matrix and s not in input_list and s not in choice_history_words:
                    rate_matrix[s] = {"name": s, "rate": r, "rate_list": [], "rate_calculate": 0.0}
            l3sym_dict_we_need.append({"l3name": obj["l3name"],
                                       "all_sym_dic": obj["all_sym_dic"],
                                       "top3": obj["top3"],
                                       "top2": obj["top2"],
                                       "top1": obj["top1"],
                                       "suffer_sym_dic": suffer_sym_dic,
                                       "rate": 0.0})
    result = {"normal_recommendation": normal_recommendation, "recommend_sym_list": [], "diagnosis_list": [],
              "disease_rate_dict": disease_rate_dict}
    # 如果第一轮，直接推荐5个疾病中的top1
    if seq == 1:
        for d_name in disease_rate_dict.keys():
            if len(l3sym_dict[d_name]["top2"]) >= 1:
                top2 = l3sym_dict[d_name]["top2"]
                sym_key = list(top2.keys())[0]
                sym_value = top2[sym_key]
                result["recommend_sym_list"].append(
                    {
                        "name": sym_key,
                        "rate": sym_value,
                        "rate_calculate": sym_value
                    })
    else:
        if normal_recommendation:
            # 计算每一个症状的概率
            for name_i in input_list:
                for (sym_name_j, sym_obj) in rate_matrix.items():
                    sym_obj["rate_list"].append(calculate_p_sym(l3sym_dict_we_need, name_i, sym_name_j))
            # 将上一步求出的n（症状的个数）个概率进行融合
            for (sym_name_j, sym_obj) in rate_matrix.items():
                sym_obj["rate_calculate"] = 1 - (calculate_p_sym_plus(sym_obj["rate_list"]) - 0.5) ** 2

        else:
            # 如果没有得到正常的初始化，就根据疾病的概率进行排序
            for (sym_name, sym_obj) in rate_matrix.items():
                sym_obj["rate_calculate"] = sym_obj["rate"]

        # 得到最值得推荐的症状的概率，之后直接取top - n就行了
        rate_matrix = sorted(rate_matrix.values(), key=lambda d: d["rate_calculate"], reverse=True)
        for sym in rate_matrix:
            if len(result["recommend_sym_list"]) >= max_recommend_sym_num:
                break
            if sym["name"] in no_use_input_list:
                continue
            result["recommend_sym_list"].append(
                {
                    "name": sym["name"],
                    "rate": sym["rate"],
                    "rate_calculate": sym["rate_calculate"]
                })
    # 计算每个疾病的概率
    # 公式是: 京伟给的该疾病的概率 *【(n个患有的症状对该疾病的贡献率的和)】
    for d in l3sym_dict_we_need:
        rate = 0.0
        # n个患有的症状对该疾病的贡献率的和
        for (sym_name, sym_rate) in d["suffer_sym_dic"].items():
            rate += sym_rate
        # n个患有的症状对该疾病的贡献率的和
        # 京伟给的该疾病的概率 *【n个患有的症状对该疾病的贡献率的和】
        if d["l3name"] in disease_rate_dict:
            rate = rate * disease_rate_dict[d["l3name"]][0]
        # 若京伟没有给概率，将该疾病设置为0
        else:
            rate = rate * 0
        d["rate"] = rate
    # 得到疾病概率的排序
    l3sym_dict_we_need = sorted(l3sym_dict_we_need, key=lambda d: d["rate"], reverse=True)
    for obj in l3sym_dict_we_need:
        result["diagnosis_list"].append(
            {"l3name": obj["l3name"],
             "rate": obj["rate"],
             "suffer_sym_dic": obj["suffer_sym_dic"],
             "suffer_sym_num": len(obj["suffer_sym_dic"])
             }
        )
    return result


def test_some_round_by_console():
    """
    通过3~4轮对话，来测试模型
    :return: None
    """
    # 每一轮最多推荐几个症状
    model = PredModel()
    max_recommend_sym = 5
    what_user_input = []
    koushu = "原发性闭经卵巢早衰，最近半年一直看不到卵泡"
    age = 50
    gender = "female"
    # 得到京伟的诊断结果 和 初始输入
    disease_rate_dict, input_list = get_diagnosis_first(koushu, model, age, gender)
    print(disease_rate_dict.keys())
    print(input_list)
    # 病人没有采用的垃圾症状（第0轮初始时候是没有的）
    no_use_input_list = []
    # 总轮数（不包括初始化轮）
    round_sum = 3

    # 第0轮结果
    print("输入提示：回复数字编号，多个请用空格分割。最后按一个enter键确认！")

    for round in range(round_sum):
        result = core_method(read_symptom_data(), disease_rate_dict, input_list, no_use_input_list, max_recommend_sym,
                             seq=round + 1)
        print("-----------------" + "Round " + str(round + 1) + "--------------------------")
        for index, sym in enumerate(result["recommend_sym_list"]):
            print(index, ".", sym["name"])
        print(len(result["recommend_sym_list"]), ".", "以上都没有")
        print("-----------------" + "Round " + str(round + 1) + "--------------------------")
        user_input = input("请选择以上几个症状您是否患有？\n")
        user_input_list = [int(num) for num in user_input.strip().split(" ")]
        for index, sym in enumerate(result["recommend_sym_list"]):
            if index in user_input_list:
                input_list.append(sym["name"])
                what_user_input.append(sym["name"])
            else:
                no_use_input_list.append(sym["name"])
        user_input = input("do you have another symtoms? write by yourself!\nif you don't have ,press enter!\n")
        if len(user_input) == 0:
            print("into wangmneg")
            result = core_method(read_symptom_data(), result["disease_rate_dict"], input_list, no_use_input_list,
                                 max_recommend_sym)
        else:
            print("into jingwei")
            disease_rate_dict, input_list = get_diagnosis_first(koushu + "," + ",".join(what_user_input), model, age,
                                                                gender)
            result = core_method(read_symptom_data(), result["disease_rate_dict"], input_list, no_use_input_list,
                                 max_recommend_sym)
    # 打印最后的诊断结果
    print("----------------------------------------------")
    for index, d in enumerate(result["diagnosis_list"]):
        print(index, " : ", d["l3name"], d["rate"], "遭受症状个数:" + str(d["suffer_sym_num"]))
        print(d["suffer_sym_dic"])
    print("----------------------------------------------")
    print("user_input", what_user_input)
    print("----------------------------------------------")
    disease_rate_dict, input_list = get_diagnosis_first(koushu + "," + ",".join(what_user_input), model, age, gender)
    print(disease_rate_dict)


# test_some_round_by_console()
