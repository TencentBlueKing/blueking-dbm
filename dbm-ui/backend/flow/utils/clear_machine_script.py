"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from backend.configuration.constants import DBType
from backend.flow.consts import DBA_ROOT_USER, WINDOW_SYSTEM_JOB_USER

os_script_language_map = {"linux": 1, "window": 5}

mysql_clear_machine_script = """
echo "clear mysql crontab...."
crontab -u mysql -r
echo "crontab completed"

echo "killing -9 mysql process ...."
ps uax | grep mysql-proxy | grep -v grep | awk -F ' ' '{print $2}' | xargs -i kill -9 {}
ps uax | grep mysql-crond | grep -v grep | awk -F ' ' '{print $2}' | xargs -i kill -9 {}
ps uax | grep mysqld | grep -v grep | awk -F ' ' '{print $2}' | xargs -i kill -9 {}
ps uax | grep exporter | grep -v grep | awk -F ' ' '{print $2}' | xargs -i kill -9 {}
echo "kill completed"

echo "rm home-mysql-dir ...."
if [ -d "/home/mysql" ]; then
    rm -rf /home/mysql/*
fi
echo "rm /home/mysql dir completed"

echo "rm data-dir ...."
if [ -d "/data" ]; then
    rm -rf /data/backup_stm/
    rm -rf /data/install/
    rm -rf /data/dbha/
    rm -rf /data/dbbak/
    rm -rf /data/mysqldata/
    rm -rf /data/mysqllog/
    rm -rf /data/mysql-proxy/
    rm -rf /data/idip_cache/
fi
echo "rm data-dir completed"

echo "rm data1-dir ...."
if [ -d "/data1" ]; then
    rm -rf /data1/mysqldata/
    rm -rf /data1/mysqllog/
    rm -rf /data1/dbbak/
    rm -rf /data1/dbha/
fi
echo "rm data1-dir completed"
"""

sqlserver_clear_machine_script = """
echo 1
"""

es_clear_machine_script = """
source /etc/profile
echo "Step 1: [crontab -u mysql -r]"
crontab -u mysql -r
echo "Step 1 completed"

echo "Step 2: [supervisorctl stop all]"
supervisorctl stop all
echo "Step 2 completed"

echo "Step 3: [ps -ef|egrep 'java|supervisord|exporter|telegraf|x-pack-ml|node'|grep -v grep |awk {'print "kill -9 " $2'}|sh]"
ps -ef | egrep 'java|supervisord|exporter|telegraf|x-pack-ml|node'|grep -v grep |awk {'print "kill -9 " $2'}|sh
echo "Step 3 completed"

echo "Step 4: [rm -f /etc/supervisord.conf /usr/local/bin/supervisorctl /usr/local/bin/supervisord /usr/bin/java]"
rm -f /etc/supervisord.conf /usr/local/bin/supervisorctl /usr/local/bin/supervisord /usr/bin/java
echo "Step 4 completed"

echo "Step 5: [sed -i '/esprofile/d' /etc/profile]"
sed -i '/esprofile/d' /etc/profile
echo "Step 5 completed"

echo "Step 6: clear esenv/eslog/esdata"
rm -rf /data/esenv*
rm -rf /data*/esdata*
rm -rf /data*/eslog*
echo "Step 6 completed"
"""

kafka_clear_machine_script = """
source /etc/profile
echo "Step 1: [crontab -u mysql -r]"
crontab -u mysql -r
echo "Step 1 completed"

echo "Step 2: [supervisorctl stop all]"
supervisorctl stop all
echo "Step 2 completed"

echo "Step 3: [ps -ef|egrep 'supervisord|burrow|telegraf|java|exporter'|grep -v grep |awk {'print "kill -9 " $2'}|sh]"
ps -ef | egrep 'supervisord|burrow|telegraf|java|exporter'|grep -v grep |awk {'print "kill -9 " $2'}|sh
echo "Step 3 completed"

echo "Step 4: [rm -f /etc/supervisord.conf /usr/local/bin/supervisorctl /usr/local/bin/supervisord /usr/bin/java]"
rm -f /etc/supervisord.conf /usr/local/bin/supervisorctl /usr/local/bin/supervisord /usr/bin/java
echo "Step 4 completed"

echo "Step 5: [rm -f /etc/profile.d/kafka.sh]"
rm -f /etc/profile.d/kafka.sh
echo "Step 5 completed"

echo "Step 6: clear kafkaenv/kafkalog/kafkadata/zk"
rm -rf /data/kafkaenv*
rm -rf /data*/kafkadata*
rm -rf /data*/kafkalog*
rm -rf /data*/zklog*
echo "Step 6 completed"
"""

hdfs_clear_machine_script = """
source /etc/profile
echo "Step 1: [crontab -u mysql -r]"
crontab -u mysql -r ; crontab -u hadoop -r
userdel hadoop
echo "Step 1 completed"

echo "Step 2: [supervisorctl stop all]"
supervisorctl stop all
echo "Step 2 completed"

echo "Step 3: [ps -ef|egrep 'supervisord|telegraf|consul'|grep -v grep |awk {'print "kill -9 " $2'}|sh]"
ps -ef | egrep 'supervisord|telegraf|consul'|grep -v grep |awk {'print "kill -9 " $2'}|sh
echo "Step 3 completed"

echo "Step 4: [rm -f /etc/supervisord.conf /usr/local/bin/supervisorctl /usr/local/bin/supervisord /usr/bin/java]"
rm -f /etc/supervisord.conf /usr/local/bin/supervisorctl /usr/local/bin/supervisord /usr/bin/java
echo "Step 4 completed"

echo "Step 5: [sed -i '/hdfsProfile/d' /etc/profile]"
sed -i '/hdfsProfile/d' /etc/profile
echo "Step 5 completed"

echo "Step 6: clear hadoopenv/hadoopdata"
rm -rf /data/hadoopenv
df |grep data|grep -vw '/data'|awk '{print $NF}'|while read line;do mv $line/hadoopdata $line/bak_hadoopdata;done
echo "Step 6 completed"
"""

pulsar_clear_machine_script = """
source /etc/profile
echo "Step 1: [crontab -u mysql -r]"
crontab -u mysql -r
echo "Step 1 completed"

echo "Step 2: [supervisorctl stop all]"
supervisorctl stop all
echo "Step 2 completed"

echo "Step 3: [ps -ef|egrep 'java|supervisord|exporter'|grep -v grep |awk {'print "kill -9 " $2'}|sh]"
ps -ef | egrep 'java|supervisord|exporter'|grep -v grep |awk {'print "kill -9 " $2'}|sh
echo "Step 3 completed"

echo "Step 4: [rm -f /etc/supervisord.conf /usr/local/bin/supervisorctl /usr/local/bin/supervisord /usr/bin/java]"
rm -f /etc/supervisord.conf /usr/local/bin/supervisorctl /usr/local/bin/supervisord /usr/bin/java
echo "Step 4 completed"

echo "Step 5: [sed -i '/pulsarprofile/d' /etc/profile]"
sed -i '/pulsarprofile/d' /etc/profile
echo "Step 5 completed"

echo "Step 6: clear pulsarenv/pulsarlog/pulsardata"
rm -rf /data/pulsarenv*
rm -rf /data*/pulsar*
echo "Step 6 completed"
"""

doris_clear_machine_script = """
source /etc/profile
echo "Step 1: [crontab -u mysql -r]"
crontab -u mysql -r
echo "Step 1 completed"

echo "Step 2: [supervisorctl stop all]"
supervisorctl stop all
echo "Step 2 completed"

echo "Step 3: [ps -ef|egrep 'supervisord|java|exporter'|grep -v grep |awk {'print "kill -9 " $2'}|sh]"
ps -ef | egrep 'supervisord|java|exporter'|grep -v grep |awk {'print "kill -9 " $2'}|sh
echo "Step 3 completed"

echo "Step 4: [rm -f /etc/supervisord.conf /usr/local/bin/supervisorctl /usr/local/bin/supervisord /usr/bin/java]"
rm -f /etc/supervisord.conf /usr/local/bin/supervisorctl /usr/local/bin/supervisord /usr/bin/java
echo "Step 4 completed"

echo "Step 5: [sed -i '/dorisprofile/d' /etc/profile]"
sed -i '/dorisprofile/d' /etc/profile
echo "Step 5 completed"

echo "Step 6: clear doris dir"
rm -rf /data/doris*
df |grep data|grep -vw '/data'|awk '{print $NF}'|while read line;do rm -rf $line/dorisdata*;done
echo "Step 6 completed"
"""

vm_clear_machine_script = """
source /etc/profile
echo "Step 1: [crontab -u mysql -r]"
crontab -u mysql -r
echo "Step 1 completed"

echo "Step 2: [supervisorctl stop all]"
supervisorctl stop all
echo "Step 2 completed"

echo "Step 3: [ps -ef|egrep 'supervisord|exporter|vminsert|vmstorage|vmselect'|grep -v grep |awk {'print "kill -9 " $2'}|sh]"
ps -ef|egrep 'supervisord|node_exporter|telegraf|vminsert|vmstorage|vmselect'|grep -v grep|awk {'print "kill -9 " $2'}|sh
echo "Step 3 completed"

echo "Step 4: [rm -f /etc/supervisord.conf /usr/local/bin/supervisorctl /usr/local/bin/supervisord /usr/bin/java]"
rm -f /etc/supervisord.conf /usr/local/bin/supervisorctl /usr/local/bin/supervisord /usr/bin/java
echo "Step 4 completed"

echo "Step 5: [rm -f /etc/profile.d/vm.sh]"
rm -f /etc/profile.d/vm.sh
echo "Step 5 completed"

echo "Step 6: clear vm dir"
rm -rf /data/vmenv*
rm -rf /data*/vmd*
rm -rf /data*/vm*
echo "Step 6 completed"
"""

db_type_script_map = {
    DBType.MySQL.value: mysql_clear_machine_script,
    DBType.Sqlserver.value: sqlserver_clear_machine_script,
    DBType.Es.value: es_clear_machine_script,
    DBType.Kafka.value: kafka_clear_machine_script,
    DBType.Hdfs.value: hdfs_clear_machine_script,
    DBType.Pulsar.value: pulsar_clear_machine_script,
    DBType.Doris.value: doris_clear_machine_script,
    DBType.Vm.value: vm_clear_machine_script,
}

db_type_account_user_map = {
    DBType.MySQL.value: DBA_ROOT_USER,
    DBType.Sqlserver.value: WINDOW_SYSTEM_JOB_USER,
    DBType.Es.value: DBA_ROOT_USER,
    DBType.Kafka.value: DBA_ROOT_USER,
    DBType.Hdfs.value: DBA_ROOT_USER,
    DBType.Pulsar.value: DBA_ROOT_USER,
    DBType.Doris.value: DBA_ROOT_USER,
    DBType.Vm.value: DBA_ROOT_USER,
}
