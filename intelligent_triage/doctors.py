# 医生模型的获取医生信息
def get_doctors(codes, probs, age, gender, orgId=None, clientId=None, branchId=None, model=None):
    return [
        {
            "id": "1111",
            "name": "医生小明",
            "departmentId": "abc1",
            "branchId": "1"
        },
        {
            "id": "222",
            "name": "小红",
            "departmentId": "abc2",
            "branchId": "2"

        },
        {
            "id": "333",
            "name": "小李",
            "departmentId": "abc1",
            "branchId": "12"

        },
        {
            "id": "444",
            "name": "小白",
            "departmentId": "abc2",
            "branchId": "12"

        },
        {
            "id": "555",
            "name": "小熊",
            "departmentId": "abc2",
            "branchId": "2"

        }
    ]
