# coding=utf-8
import collections
import re
from pyltp import Segmentor, Postagger

import fastText
import numpy as np


class PredModel:
    # def __init__(self, seg_model_path="./model/cws.model", w2v_model_path="./model/model-wiki-hdf-5k.bin", dict_var_path="./val/dict_var.npy"):
    # def __init__(self, seg_model_path="./model/cws.model", w2v_model_path="./model/word2vec.model", dict_var_path="./val/dict_var.npy"):

    def __init__(self, seg_model_path="./model/cws.model", pos_model_path="./model/pos.model",
                 w2v_model_path="./model/model-webqa-hdf-2c.bin", dict_var_path="./val/dict_var.npy"):
        self.segmentor = Segmentor()
        self.postagger = Postagger()
        self.segmentor.load(seg_model_path)
        self.postagger.load(pos_model_path)
        self.ft = fastText.load_model(w2v_model_path)
        self.dict = np.load(dict_var_path)
        self.prog = re.compile("[\.|\,|\?|\!|。|，|？|！|\s]")
        self.wv_dim = 250
        self.name_weight = 0.1
        self.th_word_mask = 0.04

        # self.segmentor = CustomizedSegmentor()
        # #segmentor.load("/home/dev/workspace/ltp/ltp_data_v3.4.0/cws.model")
        # #segmentor.load_with_lexicon("/home/dev/workspace/ltp/ltp_data_v3.3.1/cws.model", 'data/meddict.txt')
        # segmentor.load_with_lexicon("/home/dev/workspace/ltp/ltp_data_v3.4.0/cws.model", "model/hdf-cws.model", 'data/meddict.txt')

    def segment(self, sentence):
        words = self.segmentor.segment(sentence)
        return words

    def poser(self, sentence):
        postags = list(self.postagger.postag(sentence))
        return postags

    def split_into_chunks(self, sentence):
        return self.prog.split(sentence)

    def unitvec(self, vec):
        veclen = np.sqrt(np.sum(vec * vec))
        if veclen > 0.0:
            return vec / veclen
        else:
            return vec

    def top_k(self, alist, k):
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

    def Masking(self, mask_matrix, age, gender):

        mask_layer = np.ones(len(mask_matrix[0]))

        if age < 1:

            mask_layer[np.where(mask_matrix[2] == 0)] = 0

        elif age < 12.1:

            mask_layer[np.where(mask_matrix[3] == 0)] = 0

        elif age < 18.1:

            mask_layer[np.where(mask_matrix[4] == 0)] = 0

        elif age < 65.1:

            mask_layer[np.where(mask_matrix[5] == 0)] = 0

        else:
            mask_layer[np.where(mask_matrix[6] == 0)] = 0

        if gender in ['M', 'm', 'male', 'Male', '男', '男性', '男孩']:

            mask_layer[np.where(mask_matrix[0] == 0)] = 0

        else:

            if gender in ['F', 'f', 'Female', 'female', '女', '女性', '女孩']:
                mask_layer[np.where(mask_matrix[1] == 0)] = 0

        return mask_layer

    def pre_predict(self, input, age, gender):

        Dis_class = self.dict[9]
        dim = self.wv_dim
        sent_vec = []
        word_bag = []
        word_vec_bag = []
        prob_max = 0
        for chunk in self.split_into_chunks(input):
            chunk = chunk.strip()
            if len(chunk) == 0:
                continue
            words = self.segment(chunk)
            chunk_wv = []
            word_bag_tmp = []
            for word in words:
                wv = self.ft.get_word_vector(word)
                # wv = self.ft[word]
                chunk_wv.append(wv)
                word_bag_tmp.append(word)

                # if word in ['不','不是','没有','没','无']:
                #     chunk_wv = []
                #     break

            if len(chunk_wv) > 0:

                # #sent_vec.append(self.unitvec(np.sum(chunk_wv, axis=0)))
                #
                # chunk_matrix = np.reshape(chunk_wv,[len(chunk_wv),dim])
                # chunk_sim = np.dot(chunk_matrix,Dis_class.T)
                # chunk_std = np.std(chunk_sim,axis = 1)
                # chunk_max = np.max(chunk_sim, axis=1)
                #
                # for jj in range(len(chunk_std)):
                #     if chunk_std[len(chunk_std)-1-jj]<self.th_word_mask:
                #
                #
                #         del word_bag_tmp[len(chunk_std)-1-jj]
                #         del chunk_wv[len(chunk_std)-1-jj]
                if len(word_bag_tmp) > 0:
                    word_bag.append(word_bag_tmp)
                    word_vec_bag.append(chunk_wv)
                    sent_vec.append(self.unitvec(np.sum(chunk_wv, axis=0)))

        if len(sent_vec) == 0:
            Label = 3
            prob_max = 0
            return Label, prob_max

            # print(input)
            # print('没有找到匹配的疾病，请具体描述您的症状')
            # assert(False)

        input_vec = self.unitvec(np.sum(sent_vec, axis=0))
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
                    Label = 3  # 男科

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

    def predict(self, input, age, gender, k_disease, k_symptom):
        seg_bag = self.dict[0]  #
        symp_wv = self.dict[1]
        seg_matrix = self.dict[2]
        # coeff_num_wordcut = self.dict[3]
        disease_name_vec = self.dict[4]
        diseases = self.dict[5]
        index = self.dict[6]
        mask_matrix = self.dict[7]
        mask_vec = self.dict[8]
        dis_seg_vec = self.dict[10]

        mask_layer = self.Masking(mask_matrix, age, gender)

        dim = self.wv_dim
        sent_vec = []
        word_bag = []
        word_vec_bag = []

        for chunk in self.split_into_chunks(input):
            chunk = chunk.strip()
            if len(chunk) == 0:
                continue
            words = self.segment(chunk)
            pos_cut = self.poser(words)
            chunk_wv = []
            word_bag_tmp = []
            count = 0
            coef = np.zeros(len(words))
            for word in words:
                wv = self.ft.get_word_vector(word)

                # wv = self.ft[word]
                if pos_cut[count] == 'n':
                    coef[count] = 5
                else:
                    coef[count] = 1
                chunk_wv.append(self.unitvec(wv))
                word_bag_tmp.append(word)
                count = count + 1

                # if word in ['不','不是','没有','没','无']:
                #     chunk_wv = []
                #     break

            if len(chunk_wv) > 0:

                # sent_vec.append(self.unitvec(np.sum(chunk_wv, axis=0)))

                chunk_matrix = np.reshape(chunk_wv, [len(chunk_wv), dim])
                chunk_sim = np.dot(chunk_matrix, symp_wv.T)
                chunk_std = np.std(chunk_sim, axis=1)
                chunk_max = np.max(chunk_sim, axis=1)

                for jj in range(len(chunk_std)):
                    if chunk_std[len(chunk_std) - 1 - jj] < self.th_word_mask and chunk_max[
                        len(chunk_std) - 1 - jj] < 0.45 and len(chunk) < 4:

                        del word_bag_tmp[len(chunk_std) - 1 - jj]
                        del chunk_wv[len(chunk_std) - 1 - jj]

                    else:

                        chunk_wv[len(chunk_std) - 1 - jj] = coef[len(chunk_std) - 1 - jj] * chunk_wv[
                            len(chunk_std) - 1 - jj]
                if len(word_bag_tmp) > 0:
                    word_bag.append(word_bag_tmp)
                    word_vec_bag.append(chunk_wv)
                    sent_vec.append(self.unitvec(np.sum(chunk_wv, axis=0)))

        if len(sent_vec) == 0:
            # print(input)
            # print('没有找到匹配的疾病，请具体描述您的症状')
            # assert(False)
            return None, None, None, None, None, None

        # Dis_vec_HX = self.unitvec(np.sum(symp_wv,axis =0))
        # Dis_vec_all = np.reshape(Dis_mask_vec.append(Dis_vec_HX),[4,dim])

        input_vec = self.unitvec(np.sum(sent_vec, axis=0))
        # input_vec = np.reshape(input_vec, [1, dim])
        # symtom_dis = np.dot(input_vec, symp_wv.T)
        # name_dis = np.dot(input_vec, disease_name_vec.T)[0]
        # combined_dis =(self.name_weight*name_dis+(1-self.name_weight)*symtom_dis)[0]*mask_layer*mask_vec[0]
        # #combined_dis =(self.name_weight*name_dis+(1-self.name_weight)*symtom_dis)[0]
        # val, pos = self.top_k(combined_dis, k_disease)
        combined_dis = []
        for ll in range(len(sent_vec)):
            dis_tmp = np.reshape(sent_vec[ll], [1, dim])
            symtom_dis = np.dot(dis_tmp, symp_wv.T)
            name_dis = np.dot(dis_tmp, disease_name_vec.T)[0]
            name_dis = name_dis * name_dis
            combined_dis_tmp = (self.name_weight * name_dis + (1 - self.name_weight) * symtom_dis)[0] * mask_layer * \
                               mask_vec[0]
            # combined_dis_tmp = symtom_dis[0] * mask_layer * mask_vec[0]
            combined_dis.append(combined_dis_tmp * combined_dis_tmp)
        combined_dis_out = np.sqrt(np.mean(combined_dis, axis=0))
        val, pos = self.top_k(combined_dis_out, k_disease)
        # diff = -100*np.diff(val)
        # x_stop = k_disease
        # for ii in range(len(diff)):
        #
        #     if diff[ii] > 200 and val[0]>0.84:
        #
        #         x_stop = ii
        #
        #         break
        #
        #
        # pos = pos[0:x_stop+1]
        # val = val[0:x_stop+1]

        # coeff_mask = np.zeros([1,len(pos)])
        # coeff_mask[0][pos[0:10]] = 1
        # neg_plane =  np.sum(symp_wv[pos[len(pos)-50:len(pos)]],axis =0)
        # neg_plane = self.unitvec(neg_plane)
        # neg_plane = np.reshape(neg_plane,[1,len(neg_plane)])
        # coeff_shrink = 0.5+0.5*(1-np.dot(neg_plane,symp_wv.T))
        # coeff_matrix = np.dot(coeff_shrink.T,np.ones([1,dim]))
        # symp_wv_shrink = symp_wv*coeff_matrix
        # symtom_dis = np.dot(input_vec, symp_wv_shrink.T)*coeff_mask
        # combine_symtom_dis = symtom_dis[0]
        # val, pos = self.top_k(combine_symtom_dis, k_disease)

        seg_vec_cur = np.array(seg_matrix)[pos]

        seg_bag_cur = np.array(seg_bag)[pos]

        seg_vec_bag = []

        sympt_bag_cur = []

        # seg_vec_all=  []
        # sympt_bag_all = []
        symps_selected = []

        # for ii in range(len(seg_bag_all)):
        #     sympt_bag_all.extend(seg_bag_all[ii])
        #     seg_vec_all.extend(seg_bag_all[ii])
        #
        #     if mask_layer[ii] == 0:
        #
        #        symps_selected.append()

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
        val_simp, pos_simp = self.top_k(Coeff_sim_out, K_symp)
        symp_out_fin = np.array(symp_out_fin)[pos_simp]

        if val[0] < 0.5:
            return None, None, None, None, None, None
        else:
            return np.array(diseases)[pos], np.array(index)[pos], val, symp_out_fin, val_simp, word_bag
