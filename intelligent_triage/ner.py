import requests


def post(content):
    body = {
        "version": '1.0',
        "text": content,
        "userId": "jerryz"
    }
    try:
        resp = requests.post("http://100.115.147.209:8802/nlu", json=body, timeout=0.25).json()
        nerList = resp["reply"]["ner_norms"]
        result = []
        for w in nerList:
            result.extend(w.split("-"))
        result = list(set(result))
        return result, resp
    except Exception:
        return [], "超时（250ms）或者json解析错误"
