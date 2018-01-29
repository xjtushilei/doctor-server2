# coding=utf-8
import collections
import json
import re

sws = "[！|“|”|‘|’|…|′|｜|、|，|。|〈|〉:：|《|》|「|」|『|』|【|】|〔|〕|︿|！|＃|＄|％|＆|＇|（|）|＊|＋|－|,．||；|＜|＝|＞|？|＠|［|］|＿|｛|｜|｝|～|↑|→|≈|①|②|③|④|⑤|⑥|⑦|⑧|⑨|⑩|￥|Δ|Ψ|γ|μ|φ|!|\"|'|#|\$|%|&|\*|\+|,|\.|;|\?|\\\|@|\(|\)|\[|\]|\^|_|`|\||\{|\}|~|<|>|=]"


def remove_stopwords(line):
    return re.sub(sws, " ", line)

############ 文件位置，样例文件.###########################
symptoms_path="symptoms_2018_1_29.txt"
#########################################################


def read_disease_symptoms(dir=symptoms_path):
    class_names = []
    class_codes = []
    symptoms0 = []
    symptoms1 = []
    symptoms2 = []
    symptoms3 = []
    with open(dir, encoding='utf-8') as fp:
        for line in fp:
            line = line.encode('utf-8').decode('utf-8-sig')
            words = line.split('|')
            name = words[0]
            code = words[1]
            symp0 = remove_stopwords(words[2].strip()).split(' ')
            symp1 = remove_stopwords(words[3].strip()).split(' ')
            symp2 = remove_stopwords(words[4].strip()).split(' ')
            symp3 = remove_stopwords(words[5].strip()).split(' ')

            class_names.append(name)
            class_codes.append(code)
            symptoms0.append(symp0)
            symptoms1.append(symp1)
            symptoms2.append(symp2)
            symptoms3.append(symp3)
    return class_names, class_codes, symptoms0, symptoms1, symptoms2, symptoms3


def deal_symptom_txt():
    """
    生成dict文件，处理症状的文件
    :return: level3的dict
    """
    all_sym_count={}
    l3sym_map = {}
    class_names, class_codes, symptoms0, symptoms1, symptoms2, symptoms3 = read_disease_symptoms()
    for i in range(len(class_names)):
        l3name = class_names[i]
        l3code = class_codes[i]
        all_sym_dic = {}
        top3 = {}
        top2 = {}
        top1 = {}
        bite = float(1) / (len(symptoms0[i]) + 4 * len(symptoms1[i]) + 9 * len(symptoms2[i]))
        # top3
        for sys in symptoms0[i]:
            if sys == "":
                continue
            all_sym_dic[sys] = 1 * bite
            top3[sys] = 1 * bite
        # top2
        for sys in symptoms1[i]:
            if sys == "":
                continue
            all_sym_dic[sys] = 4 * bite
            top2[sys] = 4 * bite
        # top1
        for sys in symptoms2[i]:
            if sys == "":
                continue
            all_sym_dic[sys] = 9 * bite
            top1[sys] = 9 * bite

        l3sym_map[l3name] = {"l3name": l3name, "l3code": l3code, "all_sym_dic": all_sym_dic,
                             "top3": top3, "top2": top2, "top1": top1}

    with open("gen_data/disease-symptom3.data", "w", encoding="utf-8") as file:
        file.write(json.dumps(l3sym_map, ensure_ascii=False))
    return l3sym_map


def get_sym_count():
    str1 = []
    with open(symptoms_path, encoding='utf-8') as fp:
        for line in fp:
            line = line.encode('utf-8').decode('utf-8-sig')
            words = line.split('|')
            name = words[0]
            code = words[1]

            symp0 = remove_stopwords(words[2].strip()).split(" ")
            str1.extend(symp0)

            symp1 = remove_stopwords(words[3].strip()).split(" ")
            str1.extend(symp1)

            symp2 = remove_stopwords(words[4].strip()).split(" ")
            str1.extend(symp2)

    count = collections.Counter(str1)
    # print(count)
    with open("gen_data/all-symptom-count.data", "w", encoding="utf-8") as file:
        file.write(json.dumps(count, ensure_ascii=False))


deal_symptom_txt()
get_sym_count()
