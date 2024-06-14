#!/bin/bash
# 从grafana导出dashboard文件. 可以导出，也可以直接使用JSON MODEL中复制出来
# 使用jq编辑grafana dashboard文件，添加inputs和requires
# 修改templating.list中的hide属性： 为2表示隐藏Value和Name
# .id 设置为null
# 使用方法：./format_dashboard.sh dashboardFile

dashboardFile=$1
if [ ! -f "$dashboardFile" ];then
	echo dashboardFile $dashboardFile not exists
	exit;
fi

jqTest=$(jq --version)
if [ -z "$jqTest" ];then
  echo jq not found, please install jq first
  exit;
fi

tmpFile="${dashboardFile}.tmp"

# 1 add inputs
  jq '."__inputs" =  [
    {
      "name": "DS_蓝鲸监控_- 指标数据", "label": "蓝鲸监控 - 指标数据",
      "description": "", "type": "datasource",
      "pluginId": "bkmonitor-timeseries-datasource", "pluginName": "Blueing Monitor TimeSeries"
    }
  ] |
  ."__elements" = {} |
  ."__requires" = [
    { "type": "datasource", "id": "bkmonitor-timeseries-datasource", "name": "Blueing Monitor TimeSeries", "version": "3.6.0" },
    { "type": "grafana", "id": "grafana", "name": "Grafana", "version": "9.1.0" },
    { "type": "panel", "id": "stat", "name": "Stat", "version": "" },
    { "type": "panel", "id": "timeseries", "name": "Time series", "version": "" }
  ] ' $dashboardFile > $tmpFile
mv $tmpFile  $dashboardFile

# 2 update .editable && .id
jq '."editable"=false | ."id"=null ' $dashboardFile  > $tmpFile
mv $tmpFile $dashboardFile

#3 update templating.list[] hide = 2, set current value to "unknown"
len=$(jq -r '.templating.list | length' $dashboardFile)
echo length of .templating.list: $len
for ((i = 0; i < $len; i++))
do
  jq "
  .templating.list[$i].hide=2 |
  .templating.list[$i].current={\"selected\": false,\"text\": \"unknown\",\"value\": \"unknown\"}
  " $dashboardFile > $tmpFile
  mv $tmpFile  $dashboardFile
done

