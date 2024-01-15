# bkcc初始化

> python manage.py services_init bkcc

- 业务拓扑初始化
  - 监控插件服务发现拓扑（db.{db_type}.{role_type})
  - 回收中转池/待回收
- 主机自定义字段初始化（dbm_meta）

# 提取数据采集模板

> python manage.py export_collect dbtype collect_list [-m machine_types]
> collect_list来源：监控测试环境 -> 集成 -> 数据采集 -> dbm_开头的ID

采集模板数据表：db_monitor_collecttemplate

python manage.py export_collect mysql 7 91
python manage.py export_collect mysql 14 -m spider
python manage.py export_collect redis 5 9 10
python manage.py export_collect es 1
python manage.py export_collect kafka 3 8
python manage.py export_collect pulsar 4 12 13
python manage.py export_collect hdfs 11
python manage.py export_collect influxdb 6


# 提取告警策略模板

> python manage.py export_alarm dbtype alarm_list [-d]
> alarm_list来源：监控测试环境(paasdb) -> 配置 -> 告警策略 -> 带DBM_{db_type}标签的策略

告警策略模板数据表：db_monitor_ruletemplate

python manage.py export_alarm mysql 39901 39900 39763 39759 39783 39760 39785 39779 39723 39738 39739 39787 39767 39751 39733 39762 39729 39782 39734 39788 39730 39768 39731 39769 39737 39721 39773 39786 39771 39742 39755 39745 39789 39991 39992 39993 39994 39996 40004
python manage.py export_alarm redis 46031 46032 46033 46034 46035 46036 46037 46038 46039 46040 46041 46042 46043 46044 46045 46046 46047 46048 46049 46050 46051 46052 46053 46054 46055 46056 46057 46058 46059 46060 46061 46062 46063 46064 46065 46066 46067 46068 46069 46070 46071 46072 46073 46074 46075 46076 46077 46078 46079 46080 46081 46082 46083 46084 46085 46086 46087 46088 46089 46090 46091 46092 46093 46094 46095 46096 46097
python manage.py export_alarm es 39777 39752 39717 39747 39756 39740 39757 39725
python manage.py export_alarm kafka 39770 39724 39765 39772 39775 -d -c consumergroup topic
python manage.py export_alarm pulsar 39741 39753 39778 39726 39933
python manage.py export_alarm hdfs 39735 39716 39766 39781 39736 39720
python manage.py export_alarm influxdb 39784 39780 39732 39749 39746 39719 39761
python manage.py export_alarm riak 39904 39905 39909 39903 39899 39902 39906
python manage.py export_alarm cloud 46288


备注：目前事件告警创建到了生产环境，需要调整监控接口地址和DB业务ID

# 导出模板到文件 - 废弃，直接从监控接口到文件，不经过db

> python manage.py export_template -t all
> python manage.py export_template -t collect -d mysql
> python manage.py export_template -t alarm -d hdfs

# 导入到生产环境

> python manage.py services_init bkmonitor