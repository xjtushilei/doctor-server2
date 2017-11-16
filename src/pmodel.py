import fastText
import numpy as np
import collections
from pyltp import Segmentor
from gensim.models import word2vec
import re

class PredModel:
    #def __init__(self, seg_model_path="./model/cws.model", w2v_model_path="./model/model-wiki-hdf-5k.bin", dict_var_path="./val/dict_var.npy"):
    #def __init__(self, seg_model_path="./model/cws.model", w2v_model_path="./model/word2vec.model", dict_var_path="./val/dict_var.npy"):

    def __init__(self, seg_model_path="./model/cws.model", w2v_model_path="./model/model-webqa-hdf-2c.bin", dict_var_path="./model/dict_var.npy"):
        self.segmentor = Segmentor()
        self.segmentor.load(seg_model_path)
        self.ft = fastText.load_model(w2v_model_path)
        #self.ft = word2vec.Word2Vec.load(w2v_model_path)
        self.dict = np.load(dict_var_path)
        self.prog = re.compile("[\.|\,|\?|\!|。|，|？|！]")
        self.wv_dim = 250
        self.name_weight = 0.25

    def segment(self, sentence):
        words = self.segmentor.segment(sentence)
        return words

    def split_into_chunks(self, sentence):
        return self.prog.split(sentence)

    def unitvec(self, vec):
        veclen = np.sqrt(np.sum(vec*vec))
        if veclen > 0.0:
            return vec / veclen
        else:
            return vec

    def top_k(self, alist, k):
        length = len(alist)
        if k <= 0 or k > length:
            return
        pos = []
        val = []
        for ii in range(k):
            pos.append(np.where(alist == max(alist))[0][0])
            val.append(alist[pos[ii]])
            alist[pos[ii]] = -10

        return val, pos

    def Masking(self,mask_matrix,age,gender):

        mask_layer = np.ones(len(mask_matrix[0]))

        if age< 2:

            mask_layer[np.where(mask_matrix[2]==0)] = 0
        else:
            if age<18:
                mask_layer[np.where(mask_matrix[3]==0)] = 0

            else:
                mask_layer[np.where(mask_matrix[3]==0)] = 0
                mask_layer[np.where(mask_matrix[2]==0)] = 0

        if gender in ['M','m','male','Male','男','男性','男孩']:

            mask_layer[np.where(mask_matrix[1]==0)] = 0

        else:

            if gender in ['F','f','Female','femal','女','女性','女孩']:

                mask_layer[np.where(mask_matrix[0]==0)] = 0

        return mask_layer


    def predict(self, input,age,gender,k_disease ,k_symptom):
        seg_bag = self.dict[0]   #
        symp_wv = self.dict[1]
        seg_matrix = self.dict[2]
        #coeff_num_wordcut = self.dict[3]
        disease_name_vec = self.dict[4]
        diseases = self.dict[5]
        index = self.dict[6]
        mask_matrix = self.dict[7]
        mask_vec = self.dict[8]

        mask_layer = self.Masking(mask_matrix,age,gender)


        dim = self.wv_dim
        sent_vec = []

        for chunk in self.split_into_chunks(input):
            chunk = chunk.strip()
            if len(chunk) == 0:
                continue
            words = self.segment(chunk)
            chunk_wv = []
            for word in words:
                wv = self.ft.get_word_vector(word)
                #wv = self.ft[word]
                chunk_wv.append(wv)

                # if word in ['不','不是','没有','没','无']:
                #     chunk_wv = []
                #     break

            if len(chunk_wv) > 0:
                sent_vec.append(self.unitvec(np.sum(chunk_wv, axis=0)))

        if len(sent_vec) == 0:
            print("something is wrong")
            assert(False)

        input_vec = self.unitvec(np.sum(sent_vec, axis=0))
        input_vec = np.reshape(input_vec, [1, dim])
        symtom_dis = np.dot(input_vec, symp_wv.T)
        name_dis = np.dot(input_vec, disease_name_vec.T)[0]
        combined_dis =(self.name_weight*name_dis+(1-self.name_weight)*symtom_dis)[0]*mask_layer*mask_vec[0]
        #combined_dis =(self.name_weight*name_dis+(1-self.name_weight)*symtom_dis)[0]
        val, pos = self.top_k(combined_dis, k_disease)



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
        Coeff_sim = np.dot(sent_vec, vec_list_all.T) #每个段落和每个症状的匹配程度

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

        K_symp= min([len(symp_out_fin),k_symptom])
        val_simp, pos_simp = self.top_k(Coeff_sim_out, K_symp)
        symp_out_fin = np.array(symp_out_fin)[pos_simp]


        return np.array(diseases)[pos], np.array(index)[pos],val,symp_out_fin, val_simp