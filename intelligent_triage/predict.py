# coding=utf-8

import collections
import re

import numpy as np

prog = re.compile("[\.|\,|\?|\!|。|，|？|！|\s]")
wv_dim = 250
name_weight = 0.1
th_word_mask = 0.04


def segment(segmentor, sentence):
    words = segmentor.segment(sentence)
    return words


def poser(postagger, sentence):
    postags = list(postagger.postag(sentence))
    return postags


def split_into_chunks(sentence):
    return prog.split(sentence)


def unitvec(vec):
    veclen = np.sqrt(np.sum(vec * vec))
    if veclen > 0.0:
        return vec / veclen
    else:
        return vec


def top_k(alist, k):
    alist_tmp = alist
    length = len(alist_tmp)
    if k <= 0 or k > length:
        return
    pos = []
    val = []
    for ii in range(k):
        pos.append(np.where(alist_tmp == max(alist_tmp))[0][0])
        val.append(alist[pos[ii]])
        alist[pos[ii]] = -10

    return val, pos


def Masking(mask_matrix, age, gender):
    mask_layer = np.ones(len(mask_matrix[0]))

    if age < 1:

        mask_layer[np.where(mask_matrix[6] == 0)] = 0

    elif age < 12.1:

        mask_layer[np.where(mask_matrix[5] == 0)] = 0

    elif age < 18.1:

        mask_layer[np.where(mask_matrix[4] == 0)] = 0

    elif age < 40.1:

        mask_layer[np.where(mask_matrix[3] == 0)] = 0

    else:
        mask_layer[np.where(mask_matrix[2] == 0)] = 0

    if gender in ['M', 'm', 'male', 'Male', '男', '男性', '男孩']:

        mask_layer[np.where(mask_matrix[0] == 0)] = 0

    else:

        if gender in ['F', 'f', 'Female', 'female', '女', '女性', '女孩']:
            mask_layer[np.where(mask_matrix[1] == 0)] = 0

    return mask_layer


def pre_predict(input, age, gender, dict_npy, segmentor, postagger, fasttext):
    Dis_class = dict_npy[9]
    dim = wv_dim
    sent_vec = []
    word_bag = []
    word_vec_bag = []
    prob_max = 0
    for chunk in split_into_chunks(input):
        chunk = chunk.strip()
        if len(chunk) == 0:
            continue
        words = segment(segmentor, chunk)
        chunk_wv = []
        word_bag_tmp = []
        for word in words:
            wv = fasttext.get_word_vector(word)
            # wv = ft[word]
            chunk_wv.append(wv)
            word_bag_tmp.append(word)

            # if word in ['不','不是','没有','没','无']:
            #     chunk_wv = []
            #     break

        if len(chunk_wv) > 0:

            # #sent_vec.append(unitvec(np.sum(chunk_wv, axis=0)))
            #
            # chunk_matrix = np.reshape(chunk_wv,[len(chunk_wv),dim])
            # chunk_sim = np.dot(chunk_matrix,Dis_class.T)
            # chunk_std = np.std(chunk_sim,axis = 1)
            # chunk_max = np.max(chunk_sim, axis=1)
            #
            # for jj in range(len(chunk_std)):
            #     if chunk_std[len(chunk_std)-1-jj]<th_word_mask:
            #
            #
            #         del word_bag_tmp[len(chunk_std)-1-jj]
            #         del chunk_wv[len(chunk_std)-1-jj]
            if len(word_bag_tmp) > 0:
                word_bag.append(word_bag_tmp)
                word_vec_bag.append(chunk_wv)
                sent_vec.append(unitvec(np.sum(chunk_wv, axis=0)))

    if len(sent_vec) == 0:
        Label = 3
        prob_max = 0
        return Label, prob_max

        # print(input)
        # print('没有找到匹配的疾病，请具体描述您的症状')
        # assert(False)

    input_vec = unitvec(np.sum(sent_vec, axis=0))
    input_vec = np.reshape(input_vec, [1, dim])
    pre_sim = []
    if age < 19:
        Label = 3  # 进入后面的判断

    else:

        for ii in range(len(Dis_class)):
            Dis_class_tmp = np.reshape(Dis_class[ii], [len(Dis_class[ii]), dim])
            pre_sim.append(np.max(np.dot(input_vec, Dis_class_tmp.T)[0]))
        prob_max = np.max(pre_sim)

        if gender in ['M', 'm', 'male', 'Male', '男', '男性', '男孩']:
            # pre_sim = np.dot(input_vec,Dis_class[0:2].T)
            # prob_max = np.max(pre_sim[0])
            # x_max = np.where(pre_sim[0] == prob_max)[0][0]

            if pre_sim[0] > 0.83:

                Label = 0  # 遗传咨询

            elif pre_sim[1] > 0.83:
                Label = 1  # 男科

            else:
                Label = 3

        elif gender in ['F', 'f', 'Female', 'female', '女', '女性', '女孩']:

            # pre_sim = np.dot(input_vec,Dis_class.T)[0]
            # pre_sim[1]= 0
            # prob_max = np.max(pre_sim)
            # x_max = np.where(pre_sim == prob_max)[0][0]

            if pre_sim[0] > 0.83:

                Label = 0  # 遗传咨询

            elif pre_sim[2] > 0.83:

                Label = 2  # 产科
            else:
                Label = 3

    return Label, prob_max


def predict(input, age, gender, k_disease, k_symptom, dict_npy, segmentor, postagger, fasttext):
    seg_bag = dict_npy[0]  #
    symp_wv = dict_npy[1]
    seg_matrix = dict_npy[2]
    # coeff_num_wordcut = dict[3]
    disease_name_vec = dict_npy[4]
    diseases = dict_npy[5]
    index = dict_npy[6]
    mask_matrix = dict_npy[7]
    mask_vec = dict_npy[8]
    dis_seg_vec = dict_npy[10]

    mask_layer = Masking(mask_matrix, age, gender)

    dim = wv_dim
    sent_vec = []
    word_bag = []
    word_vec_bag = []

    for chunk in split_into_chunks(input):
        chunk = chunk.strip()
        if len(chunk) == 0:
            continue
        words = segment(segmentor, chunk)
        pos_cut = poser(postagger, words)
        chunk_wv = []
        word_bag_tmp = []
        count = 0
        coef = np.zeros(len(words))
        for word in words:
            wv = fasttext.get_word_vector(word)

            # wv = ft[word]
            if pos_cut[count] == 'n':
                coef[count] = 5
            else:
                coef[count] = 1
            chunk_wv.append(unitvec(wv))
            word_bag_tmp.append(word)
            count = count + 1

            # if word in ['不','不是','没有','没','无']:
            #     chunk_wv = []
            #     break

        if len(chunk_wv) > 0:

            # sent_vec.append(unitvec(np.sum(chunk_wv, axis=0)))

            chunk_matrix = np.reshape(chunk_wv, [len(chunk_wv), dim])
            chunk_sim = np.dot(chunk_matrix, symp_wv.T)
            chunk_std = np.std(chunk_sim, axis=1)
            chunk_max = np.max(chunk_sim, axis=1)

            for jj in range(len(chunk_std)):
                if chunk_std[len(chunk_std) - 1 - jj] < th_word_mask and chunk_max[
                    len(chunk_std) - 1 - jj] < 0.45 and len(chunk) < 4:

                    del word_bag_tmp[len(chunk_std) - 1 - jj]
                    del chunk_wv[len(chunk_std) - 1 - jj]

                else:

                    chunk_wv[len(chunk_std) - 1 - jj] = coef[len(chunk_std) - 1 - jj] * chunk_wv[
                        len(chunk_std) - 1 - jj]
            if len(word_bag_tmp) > 0:
                word_bag.append(word_bag_tmp)
                word_vec_bag.append(chunk_wv)
                sent_vec.append(unitvec(np.sum(chunk_wv, axis=0)))

    if len(sent_vec) == 0:
        # print(input)
        # print('没有找到匹配的疾病，请具体描述您的症状')
        # assert(False)
        return None, None, None, None, None

    input_vec = unitvec(np.sum(sent_vec, axis=0))

    combined_dis = []
    for ll in range(len(sent_vec)):
        dis_tmp = np.reshape(sent_vec[ll], [1, dim])
        symtom_dis = np.dot(dis_tmp, symp_wv.T)
        name_dis = np.dot(dis_tmp, disease_name_vec.T)[0]
        name_dis = name_dis * name_dis
        combined_dis_tmp = (name_weight * name_dis + (1 - name_weight) * symtom_dis)[0] * mask_layer * \
                           mask_vec[0]
        # combined_dis_tmp = symtom_dis[0] * mask_layer * mask_vec[0]
        combined_dis.append(combined_dis_tmp * combined_dis_tmp)
    combined_dis_out = np.sqrt(np.mean(combined_dis, axis=0))
    val, pos = top_k(combined_dis_out, k_disease)
    diff = -100 * np.diff(val)
    x_stop = k_disease
    for ii in range(len(diff)):

        if diff[ii] > 200 and val[0] > 0.84:
            x_stop = ii

            break

    pos = pos[0:x_stop + 1]
    val = val[0:x_stop + 1]

    seg_vec_cur = np.array(seg_matrix)[pos]

    seg_bag_cur = np.array(seg_bag)[pos]

    seg_vec_bag = []

    sympt_bag_cur = []

    symps_selected = []

    for ii in range(len(seg_bag_cur)):
        seg_vec_bag.extend(seg_vec_cur[ii])
        sympt_bag_cur = sympt_bag_cur + seg_bag_cur[ii]
        symps_selected.append(ii)

    sym_list_all = list(collections.Counter(sympt_bag_cur))
    vec_list_all = np.zeros([len(sym_list_all), dim])
    for ii in range(len(sym_list_all)):
        index_sym_list = sympt_bag_cur.index(sym_list_all[ii])
        vec_list_all[ii] = seg_vec_bag[index_sym_list]

    sent_vec = np.reshape(sent_vec, [len(sent_vec), dim])
    Coeff_sim = np.dot(sent_vec, vec_list_all.T)  # 每个段落和每个症状的匹配程度

    symp_out = []
    Coeff_symp_out = []
    for kk in range(k_symptom):
        num_out = np.argmax(Coeff_sim, axis=1)
        for ii in range(len(num_out)):
            if Coeff_sim[ii][num_out[ii]] > 0.0:
                symp_out.append(sym_list_all[num_out[ii]])
                Coeff_symp_out.append(Coeff_sim[ii][num_out[ii]])
            Coeff_sim[ii][num_out[ii]] = 0

    symp_out_all = list(collections.Counter(symp_out))
    symp_out_fin = []
    Coeff_sim_out = []
    for ii in range(len(symp_out_all)):
        index_sym_out_list = symp_out_all.index(symp_out_all[ii])
        symp_out_fin.append(symp_out[index_sym_out_list])
        Coeff_sim_out.append(Coeff_symp_out[index_sym_out_list])

    K_symp = min([len(symp_out_fin), k_symptom])
    if Coeff_sim_out == []:
        return None, None, None, None, None
    val_simp, pos_simp = top_k(Coeff_sim_out, K_symp)
    symp_out_fin = np.array(symp_out_fin)[pos_simp]

    if val[0] < 0.5:
        return None, None, None, None, None
    else:
        return np.array(diseases)[pos], np.array(index)[pos], val, symp_out_fin, val_simp
