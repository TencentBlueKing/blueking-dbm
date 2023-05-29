# 蓝鲸智云 DB 平台

## 代码规范

为规范代码风格，建议启用本地`pre-commit`

引入包这里可以自动化排序和格式化，可以装下isort和black(可以保证整个项目代码格式规范一致)。
在.pre-commit-config.yaml中这样的配置
```yaml
- repo: https://github.com/timothycrosley/isort
  rev: 5.7.0
  hooks:
  - id: isort
    exclude: >
      (?x)^(
          .*/migrations/.*
          | backend/packages/.*
      )$
    additional_dependencies: [toml]
```

### 使用方法
```bash
# 直接使用pip安装即可
pip install pre-commit

# 直接执行此命令，设置git hooks钩子脚本
pre-commit install

# 直接执行此命令，进行全文件检查
pre-commit run --all-storages
```

### pytest
```bash
# 执行命令
pytest backend/tests
```

### 其他快速脚本见 /bin/xxx.sh


### 异常类封装
1. 异常类统一继承 `backend.exceptions` 中的 `AppBaseException`
2. 各模块继承 `AppBaseException` 实现自己的异常类，可参考 `ticket.exceptions`
3. 可在异常类中定义 `MESSAGE_TPL`，以支持异常信息的格式化
4. 错误码由 `PLAT_CODE`、`MODULE_CODE`、`ERROR_CODE` 组成
5. 尽量在代码中抛出封装好的异常，会由 `backend.bk_web.middleware.AppBaseExceptionHandlerMiddleware`统一捕获处理，
其他异常会被统一返回为系统异常


### API请求封装
1. 第三方系统的接口请求统一使用 `backend.api`，使用方法为
   ```
   from backend.api import CCApi
   CCApi.search_business({...})
   ```
2. 此封装默认自动处理标准接口返回对 `code`,`result`,`message`,`data`进行处理，
若接口成功则直接返回`data`数据， 若接口失败则抛出`ApiError`异常由中间件捕获处理，
告知调用什么系统失败，失败原因及错误码等。
3. 如接口返回非蓝鲸标准返回，可传入参数`raw=True`进行请求，则直接返回`response`结果，`CCApi.search_business({...}, raw=True)`
4. 封装的API请求会根据不同的环境自动追加 `app_code`,`app_secret`,`bk_ticket`/`bk_token` 等必要的认证参数
（其他非认证参数如 `bk_biz_id` 不应该在此处添加）


### 环境变量
1. 环境变量统一在 `backend.env` 进行配置和使用
2. 避免环境变量散落在其他文件下，以便统一管理，明确本系统 所需/可配置 的环境变量



## BK-DBM 本地部署

>本机环境：
>
>MacBook Pro (13-inch, M1, 2020)

### 1. 资源准备

#### 1.1 准备本地RabbitMQ资源

在本地安装 `rabbitmq`，并启动 `rabbitmq-server`，服务监听的端口保持默认**5672**。

#### 1.2 准备本地Redis资源

在本地安装 `redis`，并启动 `redis-server`，服务监听的端口保持默认**6379**。

#### 1.3 准备本地MySQL资源

在本地安装 `mysql`，并启动 `mysql-server`，服务监听的端口保持默认**3306**。

#### 1.4 安装Python和依赖库

本地准备python环境，python版本要求在**>=3.6.2, <3.7**。

>python版本过高会导致后续poetry安装依赖报错

bk-dbm的依赖安装采用的是`poetry`，使用步骤如下:

首先安装`poetry`

```shell
pip install poetry
```

然后进入到工作目录中利用`poetry`安装依赖

```shell
poetry install
```

安装成功后会成功生成`.venv`虚拟环境，如果用Pycharm进行开发则可以直接使用该虚拟环境

### 2. 环境配置

#### 2.1 环境变量配置

在执行django的`manage.py`命令前，需要保证以下存在以下环境变量

```python
BK_LOG_DIR=/tmp/bkdbm; 
BK_COMPONENT_API_URL="{BK_COMPONENT_API_URL}";
BKPAAS_APP_ID=bk-dbm;
APP_TOKEN="{你的蓝鲸应用 APP_TOKEN}";
DBA_APP_BK_BIZ_ID="{DBA_APP_BK_BIZ_ID}";
BK_BASE_URL="{BK_BASE_URL}";
DBCONFIG_APIGW_DOMAIN="{DBCONFIG_APIGW_DOMAIN}";
BKREPO_USERNAME="{你的制品库用户名}";
BKREPO_PASSWORD="{你的制品库密码}";
BKREPO_PROJECT=bk-dbm;
BKREPO_PUBLIC_BUCKET=bk-dbm-package;
BKREPO_ENDPOINT_URL="{BKREPO_ENDPOINT_URL}";
BKLOG_APIGW_DOMAIN="{BKLOG_APIGW_DOMAIN}";
BKPAAS_LOGIN_URL="{BKPAAS_LOGIN_URL}";
BKPAAS_APIGW_OAUTH_API_URL="{BKPAAS_APIGW_OAUTH_API_URL}";
DJANGO_SETTINGS_MODULE=config.dev;
BK_IAM_V3_INNER_HOST="{BK_IAM_V3_INNER_HOST}";
BK_IAM_V3_SAAS_HOST="{BK_IAM_V3_SAAS_HOST}";
BK_LOGIN_URL="{BK_LOGIN_URL}";
```

#### 2.2 数据库准备

1. 修改项目目录的`./backend/settings/dev.py`中的数据库配置

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get('DB_NAME', 'bk-dbm'),  #'APP_CODE,
        'USER': os.environ.get('DB_USER', 'username'), # 本机数据库账号
        'PASSWORD': os.environ.get('DB_PASSWORD', 'password'), # 本地数据库密码
        'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
        'PORT': os.environ.get('DB_PORT', '3306'),
        'OPTIONS': {
            'init_command': """SET default_storage_engine=INNODB, sql_mode='STRICT_ALL_TABLES'""",
        },
    }
}
```

2. 在mysql中创建名为`bk-dbm`的数据库

```shell
CREATE DATABASE `bk-dbm` DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
```

3. 在项目目录下执行以下命令初始化数据库

```shell
python manage.py migrate
python manage.py createcachetable django_cache
```

#### 2.3 前端环境准备

1. 在工程目录下打包前端资源，进入`./frontend`执行命令：

```shell
npm install
npm run build
```

>如果install的时候提示某些依赖not found(比如 iconcool)，可以尝试切换npm腾讯源：
>
>```shell
>npm config set registry https://mirrors.tencent.com/npm/
>```

2. 打包成功后将`./frontend/dist`下的所有文件复制到`./backend/static`中

```shell
cp -rf ./frontend/dist/* ./backend/static/
```

3. 收集静态资源

```shell
python manage.py collectstatic --settings=config.dev --noinput
```

#### 2.4 配置本地hosts

* windows: 在 C:\Windows\System32\drivers\etc\host 文件中添加“127.0.0.1 dev.{BK_PAAS_HOST}”
* mac: 执行 “sudo vim /etc/hosts”，添加“127.0.0.1 dev.{BK_PAAS_HOST}”。

### 3. 启动进程

#### 3.1 启动celery

```shell
celery worker -A config.prod -Q er_execute,er_schedule -l info
```

>如果用pycharm进行配置的话，可以在运行/调试配置中新建python，在配置选项中选择模块名称(注意不是脚本路径)，然后选择.venv的celery文件夹(模块)，并在形参中配置celery启动参数

#### 3.2 启动Django

```shell
python manage.py runserver appdev.{BK_PAAS_HOST}:8000
```

使用浏览器开发 [http://appdev.{BK_PAAS_HOST}:8000/](http://appdev.{bk_paas_host}:8000/) 访问应用。

