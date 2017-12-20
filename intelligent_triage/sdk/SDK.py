import time

import requests


class FindDoctor:
    def __init__(self, clientId, orgId, name, dob, gender, card_no, wechatOpenId,
                 apiUrl="http://api.doctor.qq.com"):
        self.__clientId = clientId
        self.__orgId = orgId
        self.__name = name
        if not self.__is_valid_date(dob):
            raise Exception("出生日期格式有问题！请满足：'2006-03-09'格式")
        self.__dob = dob
        if not (gender == "male" or gender == "female"):
            raise Exception("性别格式有问题！请满足：gender == 'male' or gender == 'female'")
        self.__gender = gender
        self.__cardNo = card_no
        self.__wechatOpenId = wechatOpenId
        self.__apiUrl = apiUrl
        # 本次问诊结束则不能再次问诊
        self.__done = False

    def __is_valid_date(self, strdate):
        if len(strdate) != 10:
            return False
        try:
            time.strptime(strdate, "%Y-%m-%d")
            return True
        except:
            return False

    def create_session(self):
        """
        创建对话的session，并返回初始轮的症状推荐
        :return:
        """
        if self.__done:
            raise Exception("本次问诊已经结束!")
        url = self.__apiUrl + "/v1/sessions?clientId=" + self.__clientId + "&orgId=" + self.__orgId
        data = {"patient":
                    {"name": self.__name,
                     "dob": self.__dob,
                     "sex": self.__gender,
                     "cardNo": self.__cardNo
                     },
                "wechatOpenId": self.__wechatOpenId
                }
        res = requests.post(url, json=data)
        if res.status_code != 200:
            raise Exception(res.json())
        self.__sessionId = res.json()["sessionId"]
        self.__next_seqno = 1
        self.__next_query = res.json()["question"]["query"]
        self.__status = "followup"
        return res.json()

    def find_doctor(self, choice, seqno=None):
        """
        连续问诊，自动控制sessionid和对话轮次。同时满足重新回答功能，自己加上seqno就可以。问诊结束若继续对话，会抛出异常。
        :param choice: 用户的回答
        :param seqno: 现在是第几轮问答（该字段自动控制，如若不需要重新回答，请不要加该参数）
        :return: 响应结果, python的json对象
        """
        if self.__done:
            raise Exception("本次问诊已经结束!")
        if seqno is not None:
            if int(seqno) > self.__next_seqno + 1 or int(seqno) < 0:
                raise Exception("seqno参数不正确！")
        else:
            seqno = self.__next_seqno

        url = self.__apiUrl + "/v1/doctors?clientId=" + self.__clientId + "&orgId=" + self.__orgId + \
              "&sessionId=" + self.__sessionId + "&seqno=" + str(seqno) + "&query=" + self.__next_query + \
              "&choice=" + choice
        res = requests.get(url)

        if res.status_code != 200:
            raise Exception(res.json())
        res_json = res.json()
        self.__status = res_json["status"]
        if self.__status == "followup":
            self.__next_query = res_json["question"]["query"]
            self.__next_seqno = res_json["question"]["seqno"]
        else:
            self.__done = True
        return res.json()
