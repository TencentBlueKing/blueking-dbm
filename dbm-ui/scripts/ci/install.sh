#!/bin/bash

# 将本地设置文件放到配置目录，该配置会优先生效，用于配置测试DB等
# -f 表示直接覆盖文件不提示
SCRIPT_DIR=$(dirname $(readlink -f "$0"))
DBM_DIR="./dbm-ui"

cat << EOF
dollar_zero -> "$0"
SCRIPT_DIR -> "$SCRIPT_DIR"
EOF


# 安装pip依赖
source "${VENV_DIR}/bin/activate"
pip install poetry

# 进入dbm-ui进行操作
cd $DBM_DIR
poetry export --without-hashes -f requirements.txt --output requirements.txt
pip install -r requirements.txt

# 删除遗留数据库，并新建一个空的本地数据库
CREATE_DB_SQL="
set names utf8mb4;
drop database if exists \`${DB_NAME}\`;
drop database if exists \`${DB_NAME}_test\`;
create database \`${DB_NAME}\` default character set utf8mb4 collate utf8mb4_general_ci;
SELECT schema_name, default_character_set_name FROM information_schema.SCHEMATA;
"

echo $CREATE_DB_SQL

if [ "$DB_PASSWORD" ]; then
  mysql -h"$DB_HOST" -P"$DB_PORT" -u"$DB_USER" -p"$DB_PASSWORD" -sNe "$CREATE_DB_SQL"
else
  # 没有密码时无需-p，防止回车阻塞
  mysql -h"$DB_HOST" -P"$DB_PORT" -u"$DB_USER" -sNe "$CREATE_DB_SQL"
fi

# 清空redis数据
redis-cli -h ${REDIS_IP} -p ${REDIS_PORT} -a ${REDIS_PASSWORD} FLUSHALL
redis-cli -h ${REDIS_IP} -p ${REDIS_PORT} -a ${REDIS_PASSWORD} DBSIZE

FAILED_COUNT=0

python manage.py migrate
FAILED_COUNT=$[$FAILED_COUNT+$?]

python manage.py createcachetable django_cache
FAILED_COUNT=$[$FAILED_COUNT+$?]

python manage.py language_finder -p backend/ -m error
FAILED_COUNT=$[$FAILED_COUNT+$?]

echo "前置命令执行失败数量：$FAILED_COUNT"
if [[ $FAILED_COUNT -ne 0 ]];
then
  echo "前置命令未通过!"
  exit 1
else
  echo "前置命令已通过"
fi
