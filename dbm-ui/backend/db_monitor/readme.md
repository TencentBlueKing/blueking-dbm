# bkcc初始化

> python manage.py services_init bkcc

- 业务拓扑初始化
  - 监控插件服务发现拓扑（db.{db_type}.{role_type})
  - 回收中转池/待回收
- 主机自定义字段初始化（dbm_meta）

# 提取数据采集模板

> python manage.py extract_collect dbtype collect_list
> collect_list来源：监控测试环境 -> 集成 -> 数据采集 -> dbm_开头的ID

采集模板数据表：db_monitor_collecttemplate

python manage.py extract_collect mysql proxy 7
python manage.py extract_collect mysql mysql 2
python manage.py extract_collect mysql spider 14
python manage.py extract_collect redis predixy 10
python manage.py extract_collect redis twemproxy 5
python manage.py extract_collect redis redis 9
python manage.py extract_collect es es 1
python manage.py extract_collect kafka zookeeper 8
python manage.py extract_collect kafka kafka 3
python manage.py extract_collect pulsar bookkeeper 12
python manage.py extract_collect pulsar zookeeper 13
python manage.py extract_collect pulsar broker 4
python manage.py extract_collect hdfs hdfs 11
python manage.py extract_collect influxdb influxdb 6


# 提取告警策略模板

> python manage.py extract_alarm dbtype alarm_list
> alarm_list来源：监控测试环境 -> 配置 -> 告警策略 -> 带DBM_{db_type}标签的策略

告警策略模板数据表：db_monitor_ruletemplate

- 指标
python manage.py extract_alarm mysql 5629 5623 5630 5624 5627 5621 5614 5625 5626 5704 5703 5762 5758 5763
python manage.py extract_alarm redis 5765 5779 5780 5781 5782
python manage.py extract_alarm es 5668 5670 5671 5757 5669 5673 5674 5675
python manage.py extract_alarm kafka 5676 5677 5678 5679 5685
python manage.py extract_alarm pulsar 5683 5682 5681 5680
python manage.py extract_alarm hdfs 5891 5894 5895 5898 5899
python manage.py extract_alarm influxdb 5946 5947 5948 5949 5950 5951 5952
python manage.py extract_alarm riak 39876 39877 39878 39879 39882 39881 39882

- 事件
python manage.py extract_alarm mysql 73474 73473 73472 73471 73418 73456 73370 73382 73381 73379 73380 73378 73377 73363 73376 73670 73669
python manage.py extract_alarm redis 73762 73761 73760 73759 73757 73756 73742 73741

备注：目前事件告警创建到了生产环境，需要调整监控接口地址和DB业务ID

# 导出模板到文件

> python manage.py export_template -t all
> python manage.py export_template -t collect -d mysql
> python manage.py export_template -t alarm -d hdfs

# 导入到生产环境

> python manage.py services_init bkmonitor