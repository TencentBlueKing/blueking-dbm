# 版本文件初始化镜像

## 将介质纳入自动化管理
每次想将新介质纳入安装包管理，需要根据介质不同的类似，编写不同的lock文件和dockerfile

### medium.lock文件
lock文件记录了每种db类型打包的介质文件信息，以redis为例：
```yaml
redis: # dbtype
- actuator:
    buildPath: /blueking-dbm/dbm-services/redis/db-tools/dbactuator/build/dbactuator_redis # 介质路径
    commitId: xxx # 最新编译代码的commit id，这个一般自动生成
    name: dbactuator_redis # 介质文件名称
    version: 1.0.1 # 介质文件版本
- dbmon:
    buildPath: /blueking-dbm/dbm-services/redis/db-tools/dbmon/build/bk-dbmon-*.tar.gz
    commitId: xxx
    name: dbmon
    version: 1.0.1
```
如果我们有新加的打包文件，只需按照上面格式填写即可，commit id可以为xxx，version按照x.y.z格式填写

如果是非编译介质，即安装包模式，默认是上传到 github release，然后yaml格式如下：
```yaml
- redis-modules:
    buildPath: /toolkit/redis_modules.tar.gz
    name: redis_modules.tar.gz
    version: 1.0.0
```
其中buildPath固定为 /toolkit/{pkg_name}，version固定为1.0.0

### Dockerfile
dockerfile 分为 `Dockerfile`、 `BaseDockerfile`、`installs/Dockerfile-{dbtype}`，其中 `Dockerfile` 构建编译介质的安装包，
`BaseDockerfile` 构建上传工具tar介质的安装包，`installs`里面的 dockerfile 是构建基础DB组件安装包和exporter。

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
