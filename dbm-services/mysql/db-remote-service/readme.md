## 依赖
* 严重依赖 _tmysqlparse_ / _redis-cli_ 程序
* 人工部署缺少 _tmysqlparse_ / _redis-cli_ 无法运行
*  _redis-cli_ 版本需要大于4.0
* 推荐使用 _db-remote-service:test-v0.0.3_
* 启用 _tls_ 模式时, 必须同时提供 _CA/Cert/Key_ 这 _3_ 个文件

## _server start env_
```shell
# 以下为默认值

export DRS_CONCURRENT=500 
export DRS_MYSQL_ADMIN_PASSWORD="123" 
export DRS_MYSQL_ADMIN_USER="root"
export DRS_PROXY_ADMIN_PASSWORD="123"
export DRS_PROXY_ADMIN_USER="root"
export DRS_PORT=8888
export DRS_LOG_JSON=true # 是否使用 json 格式日志
export DRS_LOG_CONSOLE=true # 是否在 stdout 打印日志
export DRS_LOG_DEBUG=true # 启用 debug 日志级别
export DRS_LOG_SOURCE=true # 日志记录源文件位置
export DRS_CA_FILE="" # CA 文件
export DRS_CERT_FILE="" # Cert
export DRS_KEY_FILE="" # Key
export DRS_TLS=false 

# 容器环境不要使用
export DRS_TMYSQLPARSER_BIN="tmysqlparse"
export DRS_LOG_FILE_DIR=/log/dir # 是否在文件打印日志, 文件目录
```

## _MySQL RPC_

`POST /mysql/rpc`

**注意，数据如果 mysql 字段定义是 timestamp 类型，返回的是 +00:00 时间**

## _Request_
```go
type queryRequest struct {
	Addresses      []string `form:"addresses" json:"addresses"`
	Cmds           []string `form:"cmds" json:"cmds"`
	Force          bool     `form:"force" json:"force"`
	ConnectTimeout int      `form:"connect_timeout" json:"connect_timeout"`
	QueryTimeout   int      `form:"query_timeout" json:"query_timeout"`
}
```

|参数名|默认值||
| --- | --- | --- |
| addresses | 无 | 必须 |
| cmds | 无 | 必须 |
| force | false | 可选 |
| connect_timeout | 2 | 可选 |
| query_timeout | 30 | 可选 |

_Addresses_ 是如 _127.0.0.1:20000_ 这样的字符串数组

## _Response_
```go
type tableDataType []map[string]interface{}

type cmdResult struct {
	Cmd       string        `json:"cmd"`
	TableData tableDataType `json:"table_data"`
	RowsAffected int64       `json:"rows_affected"`	
	ErrorMsg  string        `json:"error_msg"`
}

type oneAddressResult struct {
	Address    string      `json:"address"`
	CmdResults []cmdResult `json:"cmd_results"`
	ErrorMsg   string      `json:"error_msg"`
}

type queryResponseData []oneAddressResult
```

接口返回的 _json_ 结构是
```json
{
  code: int,
  data: queryResponseData,
  msg: string
}
```

### _tableDataType_
_sql_ 执行后的返回结果

`SELECT user, host from mysql.user limit 2` 的结果看起来像

```json
[
  {"host": "localhost", "user": "root"},
  {"host": "127.0.0.1", "user": "system"}
]
```

### _cmdResult_
_TableData_ 和 _ErrorMsg_ 是互斥的, 不会同时有意义

访问的方法大概这样子
```go
var cr cmdResult
if cr.ErrorMsg != "" {
  // sql execute failed
}
```

### _oneAddressResult_
* 当 _api_ 参数中的 _force == true_ 时, _ErrorMsg_ 只会包含诸如连接错误这样地址级别的错误. _sql_ 的执行报错不会记录在这里
* 当 _api_ 参数中的 _force == false_ 时, _ErrorMsg_ 还可能是最后一条 _sql_ 执行出错的信息; _CmdResults_ 的最后一个元素也是执行出错的那条 _sql_


## 支持的命令
全量的 _sql commands_ 可以参考 _all_sql_commands.txt_

```go
	"change_db",
	"explain_other",
	"select",
	"show_binlog_events",
	"show_binlogs",
	"show_charsets",
	"show_client_stats",
	"show_collations",
	"show_create",
	"show_create_db",
	"show_create_event",
	"show_create_func",
	"show_create_proc",
	"show_create_trigger",
	"show_create_user",
	"show_databases",
	"show_engine_logs",
	"show_engine_mutex",
	"show_engine_status",
	"show_errors",
	"show_events",
	"show_fields",
	"show_func_code",
	"show_grants",
	"show_index_stats",
	"show_keys",
	"show_master_stat",
	"show_open_tables",
	"show_plugins",
	"show_privileges",
	"show_proc_code",
	"show_processlist",
	"show_profile",
	"show_profiles",
	"show_relaylog_events",
	"show_slave_hosts",
	"show_slave_stat",
	"show_status",
	"show_status_func",
	"show_status_proc",
	"show_storage_engines",
	"show_table_stats",
	"show_table_status",
	"show_tables",
	"show_thread_stats",
	"show_triggers",
	"show_user_stats",
	"show_variables",
	"show_warns",
	"alter_user",
	"change_master",
	"change_replication_filter",
	"create_db",
	"create_event",
	"create_function",
	"create_procedure",
	"create_table",
	"create_trigger",
	"create_user",
	"create_view",
	"delete",
	"delete_multi",
	"drop_compression_dictionary",
	"drop_db",
	"drop_event",
	"drop_function",
	"drop_index",
	"drop_procedure",
	"drop_server",
	"drop_table",
	"drop_trigger",
	"drop_user",
	"drop_view",
	"flush",
	"grant",
	"insert",
	"kill",
	"rename_table",
	"rename_user",
	"replace",
	"reset",
	"revoke",
	"revoke_all",
	"set_option",
	"slave_start",
	"slave_stop",
	"truncate",
	"update",
	"update_multi",
```

## _Proxy Admin RPC_

`POST /proxy-admin/rpc`

_request_ 和 _response_ 同 _MySQL RPC_

### 支持的命令
```go
    "select"
    "refresh_users"
```