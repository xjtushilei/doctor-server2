import requests


def post(content):
    body = {
        "version": '1.0',
        "content": content
    }
    try:
        rep = requests.post("http://100.115.147.209:8802/ner", json=body, timeout=0.25).json()
        return rep["ners"]
    except Exception:
        return []
