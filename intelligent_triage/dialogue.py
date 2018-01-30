# coding=utf-8
import json

import predictold


def read_symptom_data(disease_symptom_file_dir='./model/disease-symptom3.data',
                      all_symptom_count_file_path="./model/all-symptom-count.data"):
    """
    1.disease and 症状   2.还有所有症状的排序
    :return: 1.disease and 症状   2.还有所有症状的排序
    """
    with open(disease_symptom_file_dir, encoding='utf-8') as file1, open(all_symptom_count_file_path,
                                                                         encoding='utf-8') as file2:
        return json.load(file1), json.load(file2)




def disease_rate_list_to_dict(disease_rate_list):
    disease_rate_dict = {}
    for d in disease_rate_list:
        disease_rate_dict[d[0]] = [d[1], d[2]]
    return disease_rate_dict


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


def core_method(l3sym_dict, disease_rate_list=None, input_list=None, no_use_input_list=[],
                max_recommend_sym_num=5, choice_history_words=[], seq=2, all_sym_count={}):
    # print(input_list,no_use_input_list,choice_history_words)
    # 症状的排序,只返回5个
    disease_rate_dict = disease_rate_list_to_dict(disease_rate_list)
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
                                       "l3code": obj["l3code"],
                                       "all_sym_dic": obj["all_sym_dic"],
                                       "top3": obj["top3"],
                                       "top2": obj["top2"],
                                       "top1": obj["top1"],
                                       "suffer_sym_dic": suffer_sym_dic,
                                       "rate": 0.0})
    result = {"normal_recommendation": normal_recommendation, "recommend_sym_list": []}
    # 如果第一轮，直接推荐5个疾病中的top1
    if seq == 1:
        # recommend_set用来去重，避免推荐的症状中出现重复
        recommend_set = set()
        for i in range(5):
            for d_name in disease_rate_dict.keys():
                if d_name in l3sym_dict:
                    if len(l3sym_dict[d_name]["top2"]) >= i + 1:
                        top2 = l3sym_dict[d_name]["top2"]
                        sym_key = list(top2.keys())[i]
                        # input_list 是京伟的识别结果，choice_history_words是原始输入的分词结果
                        if sym_key in recommend_set or sym_key in input_list or sym_key in choice_history_words or sym_key in no_use_input_list:
                            continue
                        recommend_set.add(sym_key)
                        # 给增加的症状添加概率
                        if sym_key in all_sym_count:
                            sym_value = all_sym_count[sym_key]
                        else:
                            sym_value = 0
                        result["recommend_sym_list"].append(
                            {
                                "name": sym_key,
                                "rate": sym_value
                            })
                        if len(result["recommend_sym_list"]) >= len(disease_rate_dict):
                            break
            if len(result["recommend_sym_list"]) >= len(disease_rate_dict):
                break
        result["recommend_sym_list"].sort(key=lambda s: s["rate"], reverse=True)
    # 其他轮,则计算概率模型进行排序
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
    return result
