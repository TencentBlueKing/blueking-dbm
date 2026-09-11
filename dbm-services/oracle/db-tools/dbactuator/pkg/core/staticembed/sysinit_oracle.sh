#!/bin/bash
set -eo pipefail

# 初始化os的shell脚本
# 注入占位符：
#   {{user}}       oracle 用户名
#   {{group}}      oracle 主组名（oinstall）
#   {{dba_group}}  dba 组名
#   {{password}}   oracle 用户密码
#   {{oracle_sid}} ORACLE_SID
#   {{cf_ssn}}     CF_SSN
#   {{cf_schema}}  CF_SCHEMA

# =========================================================
# 1. 创建 oracle 用户与相关组，配置 pam 与 sshd_special_user
# =========================================================
# 主组 {{group}}
if ! egrep -q "^{{group}}:" /etc/group; then
    groupadd {{group}}
fi

# oracle 用户
if ! id {{user}} >/dev/null 2>&1; then
    useradd {{user}} -g {{group}}
fi

# pam_limits.so 幂等追加
for f in /etc/pam.d/login /etc/pam.d/su /etc/pam.d/xdm; do
    if [ -f "$f" ] && ! grep -q 'session[[:space:]]\+required[[:space:]]\+pam_limits.so' "$f"; then
        echo 'session required pam_limits.so' >> "$f"
    fi
done

# dba 组（用户原文使用 shadow-group 风格：{{dba_group}}:!:202:{{user}}）
if ! grep -q '^{{dba_group}}:' /etc/group; then
    echo '{{dba_group}}:!:202:{{user}}' >> /etc/group
fi

# sshd_special_user
if [ -f /etc/sshd_special_user ]; then
    if ! grep -qx '{{user}}' /etc/sshd_special_user; then
        echo '{{user}}' >> /etc/sshd_special_user
    fi
else
    echo '{{user}}' > /etc/sshd_special_user
fi

# 密码 / 有效期
echo '{{user}}:{{password}}' | chpasswd
chage -M 999999 {{user}}

# 用户/组一致性校验（非零退出不阻断流程）
echo 'y' | pwck  || true
echo 'y' | grpck || true

# 主组切到 dba，附加组保留 oinstall
/usr/sbin/usermod -g {{dba_group}} -G {{group}} {{user}}

# 处理与 mysql 用户组 gid=202 的冲突（仅在完全匹配 mysql:x:202: 时注释）
if grep -q '^mysql:x:202:$' /etc/group; then
    sed -i 's/^mysql:x:202:$/#mysql:x:202:/' /etc/group
fi

# =========================================================
# 2. oracle 用户环境变量 .bash_profile
#    固定段：全量覆盖（不含变量部分）
#    变量段：追加（ORACLE_SID / CF_SSN / CF_SCHEMA 会随实例变化）
# =========================================================
BP=/home/{{user}}/.bash_profile

cat > "$BP" <<'ORACLE_PROFILE_EOF'
# Get the aliases and functions
if [ -f ~/.bashrc ]; then
        . ~/.bashrc
fi

# User specific environment and startup programs

PATH=$PATH:$HOME/.local/bin:$HOME/bin
export PATH
export ORACLE_BASE=/u/ora11g
export ORACLE_HOME=$ORACLE_BASE/product/11.2.0/db_1
export PATH=$ORACLE_HOME/bin:$PATH
export NLS_LANG=AMERICAN_AMERICA.ZHS16GBK
export LD_LIBRARY_PATH=$ORACLE_HOME/lib:/lib:/usr/lib
export CLASSPATH=$ORACLE_HOME/JRE:$ORACLE_HOME/jlib:$ORACLE_HOME/rdbms/jlib
export NLS_DATE_FORMAT='MM/DD/YYYY HH24:MI:SS'
export LANG=C
export ORACLE_GG_HOME=/home/{{user}}/txu/ogg/ogg
export PATH=$PATH:$ORACLE_GG_HOME
export JAVA_HOME=/home/{{user}}/txu/ogg/jdk1.8.0_121/jre
export PATH=$PATH:$JAVA_HOME/bin
export LD_LIBRARY_PATH=/lib64:/usr/lib:$ORACLE_HOME/lib:/lib:$JAVA_HOME/lib:$JAVA_HOME/lib/amd64:$JAVA_HOME/lib/amd64/server:$JAVA_HOME/lib/amd64/libjsig.so:$JAVA_HOME/lib/amd64/server/libjvm.so
ORACLE_PROFILE_EOF

# 变量段追加（幂等：每次先删掉旧的，再按需追加新的）
# 说明：CF_SSN / CF_SCHEMA 允许为空。传空则本次跳过写入（保留 .bash_profile 里的原值）；
#       传非空则先删旧行、再写新行，保证幂等。
sed -i '/^export ORACLE_SID=/d' "$BP"
echo "export ORACLE_SID={{oracle_sid}}" >> "$BP"

if [ -n "{{cf_ssn}}" ]; then
    sed -i '/^export CF_SSN=/d' "$BP"
    echo "export CF_SSN={{cf_ssn}}" >> "$BP"
fi

if [ -n "{{cf_schema}}" ]; then
    sed -i '/^export CF_SCHEMA=/d' "$BP"
    echo "export CF_SCHEMA={{cf_schema}}" >> "$BP"
fi

chown {{user}}:{{group}} "$BP"
chmod 644 "$BP"

# =========================================================
# 3. /etc/security/limits.conf
# =========================================================
LIMITS=/etc/security/limits.conf
for line in \
    '{{user}} soft nproc 16240' \
    '{{user}} hard nproc 16384' \
    '{{user}} soft nofile 75536' \
    '{{user}} hard nofile 75536' \
    '{{user}} hard memlock unlimited' \
    '{{user}} soft memlock unlimited'; do
    if ! grep -qxF "$line" "$LIMITS"; then
        echo "$line" >> "$LIMITS"
    fi
done

# =========================================================
# 4. /etc/profile 中的 ulimit -n 注释
# =========================================================
sed -i 's/^ulimit -n/#ulimit -n/' /etc/profile
