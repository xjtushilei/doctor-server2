# 监听

``http://ip:port/`` 返回"OK",状态码200

# 启动方式一
- 准备model文件到指定目录(conf中有说明)
- `cd src/`
- `mkdir log/`（默认日志目录在这里，首次启动需要创建文件夹）
- `python server.py` 或者 `python server.py "配置文件路径" ` （默认配置文件在src/conf/app-config.yaml里有）

# 启动方式2

- 准备好路径和文件
- 根目录下 `sh run.sh`

