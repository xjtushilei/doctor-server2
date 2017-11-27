# 联系人

- 上游taf服务开发工程师:justinma
- 容器的运维工程师:joecao

#  配置
- 注意：yaml文件的冒号后面，一定要有空格。

- `text_config.yaml`

    所有文案的配置，在这里进行修改。
- `app_config_prod.yaml`和`logger_prod.conf`两个文件，这里配置不生效，配置在[米格云控](http://sumeru.wsd.com)的配置文件里进行,之后不用idc我们人工启动后，除了`text_config.yaml`还有用，其他的都不在使用

# 文件离线处理

- 推荐模型的两个文件
    
    1. 处理文件位置`/home/script/PycharmProjects/tencent-server2/intelligent_triage/utils/recommend_symp/get_sys_data.py`
    2. 输入位置,12行左右，并在该目录放置新的文件。
    ```
    ############ 文件位置，样例文件.###########################
    symptoms_path="symptoms_nov26.txt"
    #########################################################
    ```
    3. 运行生成`gen_data`文件夹下面，两个文件，放到ｍｏｄｅｌ处。

- 日志
    - 注意事项:日志会有分割，注意多个文件,文件名头一样。
    - 错误日志
        1. ｉｄｃ的`/ceph/10646/intelligent_triage/log/logging_unkown_error.log`目录下，用 `tail`查看日志（不要用ｃａｔ），例如查看倒数１０行的日志 `tail logging_unkown_error.log -n 10`
    
    - 用户使用日志
        - idc info 日志处理
            1. 处理文件位置`/home/script/PycharmProjects/tencent-server2/intelligent_triage/utils/log_to_excel/get_info_log_to_excel.py`
            2. 放到服务器，ｉｄｃ服务器里，在`/tvm/`任何目录下，运行即可。命令行参数是`logging_info1.log`　，例如
            ```
            python get_info_log_to_excel.py　xxx目录/logging_info.log
            ```
        - 腾讯mysql集群中的日志
            - 暂时没有写访问方式

# 监听（暂时没用）

``http://ip:port/`` 返回"OK",状态码200

# 运维脚本
``script``目录下，不要修改。运维工程师会进行修改。

# 启动方式
- 本地使用
    - 准备model文件到指定目录(conf中有说明)
    - `cd src/`
    - `mkdir log/`（默认日志目录在这里，首次启动需要创建文件夹）
    - `python server.py` 或者 `python server.py "配置文件路径" ` （默认配置文件在src/conf/app-config.yaml里有）
- 容器里
    - `sh script/start.sh`


