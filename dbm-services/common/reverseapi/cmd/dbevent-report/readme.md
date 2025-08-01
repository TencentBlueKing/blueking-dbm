
## 快速实现一个上报
实现 `common/reverseapi/define/common` ISyncReportEvent 接口:
```
type ISyncReportEvent interface {
	ClusterType() string
	EventType() string
	EventCreateTimeStamp() int64  // EventCreateTimeStamp 微妙
	EventBkBizId() int64
}
```

- EventType()
  上报的事件名，直接对应的就是一个 topic name. 事件名需要先在管理入口配置 `REVERSE_REPORT_EVENT_TYPES`允许列表，才能上报
- EventCreateTimeStamp()
  事件产生时间，单位微妙。通常返回 `time.Now().UnixMicro()` 就行
- ClusterType()
  必须是合法的 cluster_type 名字(不一定需要跟真实 cluster所属 cluster_type相同)
- EventBkBizId()
  事件归属哪个业务，不能是 0。

已实现可参考示例：
- cmd/dbevent-report/`oneEvent`
- example/`demoEvent`
- `MysqlBinlogResultEvent`
- `MysqlBackupResultEvent`
- `MysqlBackupStatusEvent`

(事件消费入库，可参考  db-event-consumer/README.md )


## dbevent-report 上报客户端(测试)
```
./dbevent-report --cluster-type tendbha --event-name "xiaogtest1" --bk-biz-id 1 --event-body '{
    "code": 401,
    "message": "invalid param",
    "data": ""
}'

./dbevent-report --cluster-type tendbha --event-name "xiaogtest1" --bk-biz-id 1 --event-body '
[
    {
        "code": 401,
        "message": "invalid param",
        "data": ""
    },
    {
        "code": 200,
        "message": "",
        "data": "{}"
    }
]'
```

## 直接使用 http 协议上报
```
cloud_nginx_addr=xxx:80
curl -H "Content-Type: application/json" \
 -XPOST http://$cloud_nginx_addr/apis/proxypass/reverse_api/common/sync_report/?bk_cloud_id=0 -d \
  '[
      {"cluster_type":"tendbha","event_type":"binlog-backup","bk_biz_id":123, "name":"binlog.0001", "time": 10}, 
      {"cluster_type":"tendbha","event_type":"binlog-backup","bk_biz_id":123, "name":"binlog.0002", "time":11}
  ]'
```