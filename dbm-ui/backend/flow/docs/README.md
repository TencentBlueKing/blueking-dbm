# `bamboo-pipeline`编排流程
* 此处以install_mysql为例，其它流程基本类似；

![img.png](bk-dbm-tendbha.png)

# 操作步骤
* 准备条件
```python
# 需要准备下面几个环境变量
BK_BASE_URL = os.getenv("BK_BASE_URL", "")
BK_APP_CODE = os.getenv("BK_APP_CODE", "")
BK_APP_SECRET = os.getenv("BK_APP_SECRET", "")
BK_USERNAME = os.getenv("BK_USERNAME", "")

# python版本
version = 3.6
```

1. 初始化数据
```bash
conda activate bk-dbm
python manage.py migrate
python manage.py 

```

2. 启动服务
```bash
# celery
DJANGO_SETTINGS_MODULE=config.prod celery worker -A config.prod -Q er_execute,er_schedule -l info
# django server
python manage.py runserver 0.0.0.0:6000
# jobserver
./job-sesrver
```
