# Gunicorn + gevent 搭配使用说明

gevent 的使用已经在 `gun.py` 中配置好了,并启用了 `gevent.monkey.patch_all()`

`gun.py` 为配置文件

配置信息：启动线程数量：一个线程占用内存4G左右，请合理分配线程个数。

# 启动方式

src目录下：`gunicorn -c gun.py -w 3 server:app`

### 参数意思
- -c 配置文件
- -w 启动几个worker
- server:app ： server为flask的主函数文件名字，app为flask的名字