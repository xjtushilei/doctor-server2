# 医生模型的获取医生信息
import json


def get_doctors(codes, probs, age, gender, orgId=None, clientId=None, branchId=None, model=None, appointment=None):
    # example
    # get_doctors(['M80', 'R04', 'G80', 'B80', 'H52'],[0.9,0.9,0.9,0.9,0.9],22,"F")
    prob_threshold = 0.5
    gender_threshold = 0.05

    if 0 < age <= 1:
        age_index = 0
    elif 1 < age <= 18:
        age_index = 1
    elif 18 < age <= 120:
        age_index = 2
    else:
        return []
    agename = ["age01", "age0118", "age18"]

    if gender in ["M", "男", "male"]:
        gender_index = 0
    elif gender in ["F", "女", "female"]:
        gender_index = 1
    else:
        return []

    for code, prob in zip(codes, probs):
        if (prob >= prob_threshold) and (code in model[agename[age_index]].keys()) and (
                    model[agename[age_index]][code]["gender"][gender_index] >= gender_threshold):
            return model[agename[age_index]][code]["doctors"][:30]
    return []

# with open("/mdata/finddoctor/model/hospital/深圳南山区妇幼.doctor.json.v1") as file:
#     model = json.load(file)
#
# print(get_doctors(['J02', 'J40', 'J06', 'J35', 'J38'],
#                   [0.74853809402643345, 0.7108708211696062, 0.70845967670456367, 0.7077403685609519,
#                    0.70313291072985629],
#                   11.898630136986302,
#                   "female", model=model))

#     return [
#         {
#             "id": "1111",
#             "name": "医生小明",
#             "departmentId": "abc1",
#             "branchId": "1"
#         },
#         {
#             "id": "222",
#             "name": "小红",
#             "departmentId": "abc2",
#             "branchId": "2"

#         },
#         {
#             "id": "333",
#             "name": "小李",
#             "departmentId": "abc1",
#             "branchId": "12"

#         },
#         {
#             "id": "444",
#             "name": "小白",
#             "departmentId": "abc2",
#             "branchId": "12"

#         },
#         {
#             "id": "555",
#             "name": "小熊",
#             "departmentId": "abc2",
#             "branchId": "2"

#         }
#     ]
