# 医生模型的获取医生信息


from flask import Flask, jsonify, request

app = Flask(__name__)


@app.route('/')
def hello_world():
    return 'Hello! test/query_doctors'


@app.route("/test/query_doctors", methods=["POST"])
def record():
    res = request.get_json()
    print(res)
    de = set()
    for x in res["doctors"]:
        de.add(x["departmentId"])
    print(len(de))
    res = {
        "status": "ok",
        "doctors": [
            {
                "docId": "130011",
                "branchId": "b001",
                "name": "张三",
                "departmentId": "002",
                "自定义字段1": "自定义字段1内容",
                "自定义字段2": "自定义字段2内容",
                "自定义字段3": "自定义字段3内容",
                "schedule": [
                    {
                        "date": "2018-02-08",
                        "type": "普通",
                        "total": 10,
                        "available": 5
                    },
                    {
                        "date": "2018-02-09",
                        "type": "专家",
                        "total": 10,
                        "available": 5
                    }
                ]
            }
        ]
    }
    return jsonify(res)


if __name__ == '__main__':
    app.run(port=8087)
