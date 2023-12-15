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
cd backend/bk_dataview/dashboards/json
find . -type f -name "*.json" -exec sed -i '' -e 's#${DS_蓝鲸监控_-_指标数据}#bkmonitor_timeseries#g' {} \;
find . -type f -name "*.json" -exec sed -i '' -e 's#${DS_蓝鲸监控_- 指标数据}#bkmonitor_timeseries#g' {} \;
find . -type f -name "*.json" -exec sed -i '' -e 's#"editable": true#"editable": false#g' {} \;
find . -type f -name "*.json" -exec sed -i '' -e 's#bkmonitor:system:#bkmonitor:dbm_system:#g' {} \;
# 批量替换基础指标来源：system -> dbm_system
find . -type f -name "*.json" -exec sed -i '' -e 's#bkmonitor:system:#bkmonitor:dbm_system:#g' {} \;
find . -type f -name "*.json" -exec sed -i '' -e 's#"result_table_id":"system.#"result_table_id":"dbm_system.#g' {} \;

# 导入监控的方法，还原模板后导入
find . -type f -name "*.json" -exec sed -i '' -e 's#bkmonitor_timeseries#${DS_蓝鲸监控_-_指标数据}#g' {} \;
find . -type f -name "*.json" -exec sed -i '' -e 's#bkmonitor_timeseries#${DS_蓝鲸监控_- 指标数据}#g' {} \;
find . -type f -name "*.json" -exec sed -i '' -e 's#"editable": false#"editable": true#g' {} \;