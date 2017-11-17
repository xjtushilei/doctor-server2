import gevent.monkey
gevent.monkey.patch_all()

import multiprocessing

debug = True
# 监听任何ip的port端口
bind = '0.0.0.0:6000'
pidfile = 'log/gunicorn.pid'

#  gunicorn 默认使用同步阻塞的网络模型(sync)，对于大并发的访问可能表现不够好， 它还支持其它更好的模式，比如：gevent
worker_class = 'gunicorn.workers.ggevent.GeventWorker'

x_forwarded_for_header = 'X-FORWARDED-FOR'


