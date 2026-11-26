#!/bin/bash

# 将本地设置文件放到配置目录，该配置会优先生效，用于配置测试DB等
# -f 表示直接覆盖文件不提示
SCRIPT_DIR=$(dirname $(readlink -f "$0"))
DBM_DIR="./dbm-ui"
FAILED_COUNT=0

cat << EOF
dollar_zero -> "$0"
SCRIPT_DIR -> "$SCRIPT_DIR"
EOF

# 安装pip依赖
echo "开始执行 poetry & pip 安装依赖"
source "${VENV_DIR}/bin/activate"
pip install poetry >> /tmp/pip_install.log

# 进入dbm-ui进行操作
cd $DBM_DIR
poetry self add poetry-plugin-export
poetry export --without-hashes -f requirements.txt --output requirements.txt

pip install -r requirements.txt >> /tmp/pip_install.log
if [[ $? -ne 0 ]];
then
  echo -e "\033[1;31m Error: pip install -r requirements.txt error! \033[0m"
  cat /tmp/pip_install.log
  FAILED_COUNT=$[$FAILED_COUNT+1]
fi
# 删除遗留数据库，并新建一个空的本地数据库
CREATE_DB_SQL="
set names utf8mb4;
drop database if exists \`${DB_NAME}\`;
drop database if exists \`${DB_NAME}_test\`;
create database \`${DB_NAME}\` default character set utf8mb4 collate utf8mb4_general_ci;

drop database if exists \`${REPORT_DB_NAME}\`;
drop database if exists \`${REPORT_DB_NAME}_test\`;
create database \`${REPORT_DB_NAME}\` default character set utf8mb4 collate utf8mb4_general_ci;
SELECT schema_name, default_character_set_name FROM information_schema.SCHEMATA;

drop database if exists \`${STATS_DB_NAME}\`;
drop database if exists \`${STATS_DB_NAME}_test\`;
create database \`${STATS_DB_NAME}\` default character set utf8mb4 collate utf8mb4_general_ci;

"

echo $CREATE_DB_SQL

if [ "$DB_PASSWORD" ]; then
  mysql -h"$DB_HOST" -P"$DB_PORT" -u"$DB_USER" -p"$DB_PASSWORD" -sNe "$CREATE_DB_SQL"
else
  # 没有密码时无需-p，防止回车阻塞
  mysql -h"$DB_HOST" -P"$DB_PORT" -u"$DB_USER" -sNe "$CREATE_DB_SQL"
fi

echo "开始执行 python manage.py migrate --database=report_db"
python manage.py migrate --database=report_db >> /tmp/migrate_report_db.log
if [[ $? -ne 0 ]];
then
  echo -e "\033[1;31m Error: python manage.py migrate --database=report_db 执行失败！请检查 migrations 文件 \033[0m"
  cat /tmp/migrate_report_db.log
  FAILED_COUNT=$[$FAILED_COUNT+1]
fi

echo "开始执行 python manage.py migrate"
python manage.py migrate >> /tmp/migrate.log
if [[ $? -ne 0 ]];
then
  echo -e "\033[1;31m Error: python manage.py migrate 执行失败！请检查 migrations 文件 \033[0m"
  cat /tmp/migrate.log
  FAILED_COUNT=$[$FAILED_COUNT+1]
fi

python manage.py createcachetable django_cache

python manage.py language_finder -p backend/ -m error
if [[ $? -ne 0 ]];
then
  echo -e "\033[1;31m Error: python manage.py language_finder -p backend/ -m error 执行失败！请检查中文是否已标记并且是否存在非法导入 \033[0m"
  FAILED_COUNT=$[$FAILED_COUNT+1]
fi

# 只检查 backend 目录下的自有 app：site-packages 里的 SDK app（如 aidev_bkplugin）
# 自身没有生成 migrations 不受本仓库控制，不应阻断流水线
echo "正在检查是否有未提交的数据库迁移文件（仅 backend 目录下自有 app）..."
LOCAL_APP_LABELS=$(python "${SCRIPT_DIR}/local_app_labels.py")
if [[ $? -ne 0 || -z "${LOCAL_APP_LABELS}" ]];
then
  echo -e "\033[1;31m Error: 未获取到 backend 目录下的 app 列表，migrations 检查无法执行！ \033[0m"
  FAILED_COUNT=$[$FAILED_COUNT+1]
else
  echo "检查范围: $(echo ${LOCAL_APP_LABELS} | tr '\n' ' ')"
  # shellcheck disable=SC2086 # 需要按空白拆分成多个 app label
  python manage.py makemigrations ${LOCAL_APP_LABELS} --dry-run --check --noinput
  if [[ $? -ne 0 ]];
  then
    echo -e "\033[1;31m Error: 检测到模型变更但未生成对应的迁移文件！请检查上面的迁移详情 \033[0m"
    FAILED_COUNT=$[$FAILED_COUNT+1]
  else
    echo "✅ 检查通过：没有未提交的模型变更。"
  fi
fi

if [[ $FAILED_COUNT -ne 0 ]];
then
  echo -e "\033[1;31m Error: 前置命令未通过! 前置命令执行失败数量: $FAILED_COUNT \033[0m"
  exit 1
else
  echo "前置命令已通过"
fi

