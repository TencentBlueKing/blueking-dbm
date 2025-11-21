为了解决 binlog 文件里面所包含事件的结束时间，不依赖 file_mtime。file_mtime 可能会被修改，如果是从库存在延迟，不能代表 binlog 结束时间。

`mysqlbinlog-parse-time` 命令会从文件尾部读取后面的字节，直到成功获取`RotateEvent` / `StopEvent`。

实测解析 1000 个 binlog 开始和结束时间，耗时 0.305s。

## Compile
```
go build -o mysqlbinlog-parse-time .
```

## Usage

```
./mysqlbinlog-parse-time -f binlog.000003,binlog.000004

{
    "binlog.000003": [
        {
            "event_type": "FormatDescriptionEvent",
            "event_time": "2022-06-20T15:17:47+08:00",
            "timestamp": 1655709467,
            "server_id": 81482679,
            "event_size": 137
        },
        {
            "event_type": "RotateEvent",
            "event_time": "2022-07-07T23:38:36+08:00",
            "timestamp": 1657208316,
            "server_id": 81482679,
            "event_size": 49
        }
    ],
    "binlog.000004": [
        {
            "event_type": "FormatDescriptionEvent",
            "event_time": "2022-07-07T23:38:36+08:00",
            "timestamp": 1657208316,
            "server_id": 81482679,
            "event_size": 137
        },
        {
            "event_type": "RotateEvent",
            "event_time": "2023-11-03T12:40:14+08:00",
            "timestamp": 1698986414,
            "server_id": 81482679,
            "event_size": 49
        }
    ]
}
```