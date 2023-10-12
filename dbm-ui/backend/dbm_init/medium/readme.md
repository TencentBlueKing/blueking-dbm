# 版本文件初始化镜像

## 打包

在blueking目录下执行
```shell
docker build -t dbm-sync-medium -f dbm-ui/backend/dbm_init/medium/Dockerfile . \                                                                             
--build-arg MEDIUM_BUILDER_BRANCH=master \
--build-arg GITHUB_TOKEN=token \
--build-arg GITHUB_USERNAME=user \
--build-arg GITHUB_USER_EMAIL=example@example.com
```

## 脚本用法

使用之前需要配置相关环境变量
```shell
PYTHONUNBUFFERED=1;
APP_CODE=bk_dbm;
APP_ID=bk_dbm;
APP_TOKEN=;
BKREPO_ENDPOINT_URL=http://bkrepo.example.com;
BKREPO_PASSWORD=xxx;
BKREPO_PROJECT=blueking;
BKREPO_PUBLIC_BUCKET=bkdbm;
BKREPO_USERNAME=xxx;
DBM_SAAS_URL=http://dbm.example.com/;
DJANGO_SETTINGS_MODULE=settings
```

相关命令
```shell
python main.py --type build # 打包二进制文件
python main.py --type upload --db xx # 上传制定dbtype到制品库
python main.py --type sync --db xx # 同步到Package表
```
