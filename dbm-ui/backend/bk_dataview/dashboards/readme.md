# 导出仪表盘
到开发环境中，配置好仪表盘后，在设置中点击 JSON Model，复制对应的仪表盘到本目录对应的 json 文件中
保留 __inputs 为:
```
{
    "__inputs": [
        {
          "name": "DS_蓝鲸监控_- 指标数据",
          "label": "蓝鲸监控 - 指标数据",
          "description": "",
          "type": "datasource",
          "pluginId": "bkmonitor-timeseries-datasource",
          "pluginName": "BlueKing Monitor TimeSeries"
        }
      ],
    这里粘贴从 JSON Model 复制出来的内容，如:
    "annotations": {},
    "templating": {},
    ....
}
```
![export_dashboard.png](export_dashboard.png)

# 添加tags

"tags": ["{cluster_type}"]
___________________________________
"tags": ["es"],
"tags": ["hdfs"],
"tags": ["kafka"],
"tags": ["pulsar"],
"tags": ["tendbha"],
"tags": ["tendbsingle"],
"tags": ["tendbcluster"],
"tags": ["influxdb"],
"tags": ["TwemproxyRedisInstance"],
"tags": ["PredixyTendisplusCluster"],
"tags": ["TwemproxyTendisSSDInstance"],

# 刷新监控数据源ID：bkmonitor_timeseries
```
cd backend/bk_dataview/dashboards/json
find . -type f -name "*.json" -exec sed -i '' -e 's#${DS_蓝鲸监控_-_指标数据}#bkmonitor_timeseries#g' {} \;
find . -type f -name "*.json" -exec sed -i '' -e 's#${DS_蓝鲸监控_- 指标数据}#bkmonitor_timeseries#g' {} \;
find . -type f -name "*.json" -exec sed -i '' -e 's#"editable": true#"editable": false#g' {} \;
find . -type f -name "*.json" -exec sed -i '' -e 's#bkmonitor:system:#bkmonitor:dbm_system:#g' {} \;
```
# 批量替换基础指标来源：system -> dbm_system
```
find . -type f -name "*.json" -exec sed -i '' -e 's#bkmonitor:system:#bkmonitor:dbm_system:#g' {} \;
find . -type f -name "*.json" -exec sed -i '' -e 's#"result_table_id": "system.#"result_table_id": "dbm_system.#g' {} \;
```

# 导入监控的方法，还原模板后导入
```
find . -type f -name "*.json" -exec sed -i '' -e 's#bkmonitor_timeseries#${DS_蓝鲸监控_-_指标数据}#g' {} \;
find . -type f -name "*.json" -exec sed -i '' -e 's#bkmonitor_timeseries#${DS_蓝鲸监控_- 指标数据}#g' {} \;
find . -type f -name "*.json" -exec sed -i '' -e 's#"editable": false#"editable": true#g' {} \;
```