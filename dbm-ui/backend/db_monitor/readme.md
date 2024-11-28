# 如何提取同步监控采集和告警策略

## 首先配置好对应环境的环境变量

## bkcc初始化

```
python manage.py services_init bkcc
```

- 业务拓扑初始化
  - 监控插件服务发现拓扑（db.{db_type}.{role_type})
  - 回收中转池/待回收
- 主机自定义字段初始化（dbm_meta）

## 提取数据采集模板

> python manage.py export_collect dbtype collect_list [-m machine_types]
> collect_list来源：监控测试环境 -> 集成 -> 数据采集 -> dbm_开头的ID

采集模板数据表：db_monitor_collecttemplate

```
source paasdb.local.env
python manage.py export_collect mysql 7 91
python manage.py export_collect mysql 14 -m spider
python manage.py export_collect redis 5 9 10
python manage.py export_collect es 1
python manage.py export_collect kafka 3 8
python manage.py export_collect pulsar 4 12 13
python manage.py export_collect hdfs 11
python manage.py export_collect influxdb 6
python manage.py export_collect sqlserver 93
python manage.py export_collect tbinlogdumper 110
```


## 提取告警策略模板
> 如需部署 DBM 时自动更新，需修改此文件中的 version 值，backend/db_monitor/management/commands/export_alarm.py

> python manage.py export_alarm dbtype alarm_list [-d]

> alarm_list来源：监控测试环境(paasdb) -> 配置 -> 告警策略 -> 带DBM_{db_type}标签的策略

告警策略模板数据表：db_monitor_ruletemplate

paasdb 策略:
```
source paasdb.local.env
python manage.py export_alarm mysql 39901 39900 39763 39759 39783 39760 39785 39779 39723 39738 39739 39787 39767 39751 39733 39762 39729 39782 39734 39788 39730 39768 39731 39769 39737 39721 39773 39786 39771 39742 39755 39745 39789 39991 39992 39993 39994 39996 40004 46286 46287
python manage.py export_alarm redis 46031
python manage.py export_alarm es 39777 39752 39717 39747 39756 39740 39757 39725
python manage.py export_alarm kafka 39770 39724 39765 39772 39775 -d -c consumergroup topic
python manage.py export_alarm pulsar 39741 39753 39778 39726 39933
python manage.py export_alarm hdfs 39735 39716 39766 39781 39736 39720
python manage.py export_alarm influxdb 39784 39780 39732 39749 39746 39719 39761
python manage.py export_alarm riak 39904 39905 39909 39903 39899 39902 39906
python manage.py export_alarm cloud 46288
python manage.py export_alarm sqlserver 46653 46660 46659 46665 46664 46663 46662 46661 46658 46657 46656 46655 46654 46652 46649 46651
python manage.py export_alarm tbinlogdumper 46679 46680
python manage.py export_alarm mongodb 144012 144013 144014 144015 144016 144017 144018

```

prod 策略:
```
source prod.local.env
python manage.py export_alarm mysql 98056 98061 98058
python manage.py export_alarm redis 106455 106497
python manage.py export_alarm es 98003 98004 98005 98006 98007 98008 98009 98010 
python manage.py export_alarm kafka 98027 -d -c consumergroup topic
python manage.py export_alarm pulsar 98065 98063
python manage.py export_alarm hdfs 
python manage.py export_alarm influxdb 
python manage.py export_alarm riak 
python manage.py export_alarm cloud 100371 100372 100373 113059 100368 100369 117596 114983
```



备注：目前事件告警创建到了生产环境，需要调整监控接口地址和DB业务ID


## 导入到生产环境

```
python manage.py services_init bkmonitor
```
