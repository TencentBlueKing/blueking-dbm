# 简介
1. 集中管理遗留的定时任务脚本, 需要统一放入 _collect_ 文件夹
2. 新增的定时任务建议用 _go_ 实现
3. 所有定时任务都暴露出唯一的 _http_ 接口, 在 _dbm django_ 工程中用 _celery_ 调度

# 启动
`celery-service run`

```shell
build/celery-service run --help
usage: celery-service run [<flags>]

start service


Flags:
  --[no-]help                Show context-sensitive help (also try --help-long and --help-man).
  --external-task-config=/external-tasks.yaml  
                             external tasks ($CS_EXTERNAL_TASK)
  --[no-]log-console         print log to console ($CS_LOG_CONSOLE)
  --address=0.0.0.0:80       service listen address ($CS_ADDRESS)
  --db-address=DB-ADDRESS    result db address ($CS_DB_ADDRESS)
  --db-user=DB-USER          result db user ($CS_DB_USER)
  --db-password=DB-PASSWORD  result db password ($CS_DB_PASSWORD)
  --db-name=DB-NAME          result database name ($CS_DB_NAME)
```

_--log-console_ 会把日志打印到标准输出, 方便调试. 改成 _--no-log-console_ 禁用

# _API_
## 通用 _API_
### 获取 _API_ 列表
`GET /list`

#### _response_

```json
{
  "code": 0,
  "data": [
    {
      "method": "POST",
      "path": "/async/tendb-cluster/shell-echo"
    },
    {
      "method": "POST",
      "path": "/sync/tendb-ha/counter"
    },
    ...
    {
      "method": "POST",
      "path": "/async/kill"
    },
    {
      "method": "POST",
      "path": "/async/query"
    },
    {
      "method": "GET",
      "path": "/list"
    }
  ],
  "msg": ""
}
```

### 查询异步会话
`POST /async/query`

#### 参数
```json
{
  "session_id": STRING
}
```
当不传入参数时 `curl -XPOS /async/query` , 会返回所有会话信息

#### _response_
```json
{
  "code": 0,
  "data": [
    {
      "id": "9e9dee40-2fd8-4226-a462-fadaff2bd2c3",
      "message": "",
      "error": "unexpected end of JSON input",
      "done": true,
      "start_at": "2023-08-14T09:16:37.961224+08:00"
    },
    ...
  ],
  "msg": ""
}
```

### 结束异步会话
`POST /async/kill`

#### 参数
```json
{
  "session_id": STRING
}
```

## 合成 _API_
每一个任务会自动生成`同步, 异步` _2_ 个 _API_

如
```json
    {
      "method": "POST",
      "path": "/sync/tendb-cluster/shell-echo"
    },
    {
      "method": "POST",
      "path": "/async/tendb-cluster/shell-echo"
    },
```

### 参数
1. 用 _golang_ 实现的任务需要和开发者协商
2. 由参数文件配置的外部任务接收字符串数组

### _response_
1. 用 _golang_ 实现的任务需要和开发者协商
2. 外部任务在同步模式下
    ```json
    {
    "code": 0, # 有错误时为 1
    "data": "hello aaa bbb fasdfas g34efasd", # 最后一行标准输出
    "msg": "" # 最后一行标准错误
    }
    ```
3. 外部任务在异步模式下
    ```json
    {
      "code": 0,
      "data": "a660e652-5f40-4424-981d-eb2ba383d96a",
      "msg": ""
    }
    ```
   
# 会话清理
状态 `done == true` 的异步会话会被自动清理

# 遗留脚本接入

1. 目前支持 `python, perl, shell` 脚本
2. 需要全部放入 _collect_ 文件夹
3. 脚本需要有可执行权限
4. 修改 `--external-task-config e.yaml` 指定的文件, 如 `e.yaml`

## 一些必要的改造
为了能
1. 准确捕捉脚本执行状态
2. 正确记录脚本执行日志

最好能做到这么几件事情
1. 严格区分 `stdout, stderr` 的输出
2. 正确使用 `exit code`
3. 对于 `bash sh` 脚本, 强烈推荐添加 `set -e`

同时, 由于计划使用 _mongodb_ 存储结果, 入库部分可能需要改造

## _external task config_
```yaml
- name: demo1
  cluster_type: TendbCluster
  language: sh
  executable: echo hello
  args: ["aaa", "bbb"]
  collected: false
- name: demo2
  cluster_type: TendbCluster
  language: sh
  executable: s.sh
  collected: true
- name: demo3
  cluster_type: TendbCluster
  language: binary
  executable: testbin
  collected: true  
- name: demopython
  cluster_type: sqlsvr
  language: binary
  executable: aaa
  collected: true
- name: demoperl
  cluster_type: redis
  language: perl
  executable: kkk.pl
  collected: true
```

```golang
type ExternalTask struct {
	Name         string   `yaml:"name" validate:"required"`
	ClusterType  string   `yaml:"cluster_type" validate:"required"`
	Language     string   `yaml:"language" validate:"required,oneof=python python2 python3 perl sh bash binary"`
	Executable   string   `yaml:"executable" validate:"required"`
	Args         []string `yaml:"args"`
	Collected    *bool    `yaml:"collected" validate:"required"`
}
```

* _language_: 指定脚本的实现语言, 决定如何执行脚本
  * 值为 `sh, shell` 时会以 `sh -c $Executable $Args` 方式执行
  * 值为 `binary` 时会直接以 `$Executable $Args` 方式执行, 对于设置了 `Shebang` 的脚本也可以用这种方式执行
  * 其他值会以 `$Language $Executable $Args` 方式执行
* _executable_: 包含脚本文件名的路径, 可以是绝对路径和相对路径
* _collected_: 是否统一管理
  * 为 _true_ 时执行的脚本路径是 `collect/$executable`, 所以此时 _executable_ 不能是绝对路径
  * 为 _false_ 时执行的脚本路径就是 `$executable`, 只要在 `$PATH` 能找到就可以
  
## 参数
有 _3_ 个地方可以传入参数
1. `$executable` 实际上可以是如 _somescriptpath 1 2 3_ 这样的字符串, 会被切分成两部分
    * _somescriptpath_ 是实际的脚本
    * _["1", "2", "3"]_ 作为参数
2. `$args` 直接接受字符串数组
3. 导出的 _http_ 接口可以用 `post` 的方式传入字符串数组
4. 参数的拼接顺序按上面 _1_ 到 _3_ 的顺序

如
```yaml
- name: demo1
  cluster_type: TendbCluster
  language: sh
  executable: echo hello
  args: ["aaa", "bbb"]
  collected: false
```

的调用 _url_ 是 `/tendb-cluster/demo1`

当用 `curl -XPOST http://localhost/tendb-cluster/demo1 -d '["123", "456"]'` 调用时, 实际执行的命令是

`sh -c 'echo hello aaa bbb 123 456'`

# 新增/开发
新增的定时任务推荐在本工程内用 _go_ 开发

1. 定义一个专用的 `struct` 如 `SomeTask`
2. `SomeTask` 必须匿名包含 `pkg.handler.InternalBase`
3. `SomeTask` 必须实现 `pkg.handler.IHandler`
4. 调用 `pkg.handler.addInternalHandler` 注册

具体示例可以参考 `dbm-services/common/celery-service/pkg/handler/internalhandler/democounter`

## 参数
没有任何强制性要求, 可以随意实现并用 `post` 方法传入

# 环境变量
1. 父进程的所有环境变量会传递到任务所属子进程
2. [ ] <span style="color:read">ToDo 确定上报结果的数据库连接串环境变量</span>

# 日志

1. 所有日志都收集到 _logs_ 目录
2. 各任务有自己独立的日志文件 `$Name.log`

# 结果入库
1. 目前还没有统一接管结果入库的计划
2. 考虑使用 _mongodb_ 存储结果
3. 会通过环境变量的方式传入 _mongodb_ 的连接串