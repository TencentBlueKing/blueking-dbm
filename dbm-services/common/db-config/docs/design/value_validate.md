# 设置 value_default, value_allowed, value_type, value_type_sub

## value_type
value_type 是直接定义 value_default 字段的数据类型，支持以下基本数据类型：
1. STRING：字符串
2. INT: 数字类型，整型
3. FLOAT： 浮点类型
4. NUMBER：数字类型
5. BOOL: 布尔类型

### 数字类型 value_type=INT | FLOAT | NUMBER
value_type_sub 可以为 ENUM、RANGE，为 空 时会自动检测 value_allowed 是 RANGE / ENUM

### 布尔类型 value_type=BOOL
value_type_sub 可以为 ENUM、FLAG，为 空 时等价于 ENUM。
 - `ENUM` 通过 value_allowed 定义 true/false 字符串：  
   - true: 允许 "1", "t", "T", "true", "TRUE", "True"
   - false: 允许 "0", "f", "F", "false", "FALSE", "False"
 - `FLAG` 表示这个 BOOL 值是通过 flag 配置项是否出现来决定 true / false
  比如 `--skip-name-resolve`，不需要`--skip-name-resolve=on`。strict模式返回时会返回 `"skip-name-resolve":"flag"` 以做区分,

### 字符串 value_type=STRING
STRING 类型是最灵活的，value_type_sub 子类支持：
 - `STRING`  
  value_type_sub 为空时，与 STRING 等价，表示最普通的 STRING 类型，不会校验 value_allowed
 - `ENUM`, `ENUMS`  
  ENUMS 字符串类型的枚举, 如 binlog_format value_allowed = `ROW | STATEMENT | MIXED`，最终 conf_value 取值为其中一个
  ENUMS 代表枚举值可以多个, 比如 sql_mode value_allowed = `ONLY_FULL_GROUP_BY | STRICT_TRANS_TABLES | NO_ENGINE_SUBSTITUTION | `, 最终 conf_value 可以取值 `ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES`, 这里 sql_mode 还允许选择 空值，客户端渲染的时候需要注意。
 - `BYTES`  
  字节单位类型，比如 `1b`, `2k`, `3m`, `4g`，可一个 `3 mb`, `4gb` 这种带b格式，1b 代表一字节，纯数字代表秒b。
  BYTES 子类型，会自动判断 value_allowed 是 range 还是 enum，range格式 `[m, n]`, enum格式 `a |b | c`。
  range 左右区间可以是带单位的，如 `[1024, 64m]`
 - `DURATION`   
   时间单位类型，比如 `1s`, `2m`, `3h`，一天 24h 的可以用 `1d`, `1w` 扩展过的 golang duration，纯数字代表秒s。
   DURATION 子类型，会自动判断 value_allowed 是 range 还是 enum，range格式 `[m, n]`, enum格式 `a | b | c`。
   range 左右区间可以是带单位的，如 `[3600, 24h]`
 - `JSON`, `MAP`  
  会验证 value 是否是一个合法的 json. MAP  与 JSON 的区别在于，MAP strict模式返回时会返回 json 而不是 string。
  一般 value_allowed 为空
 - `REGEX`   
  会验证 value 是否满足 value_allowed 定义的正则，需要配合 value_allowed使用。
  比如：value_type_sub=REGEX value_allowed=`^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,4}$`，代表合法的email（当然用下面的 validate更简单）
 - `GOVALIDATE`  
   基于 https://github.com/go-playground/validator ，value_allowed 填写 validate 内容，比如 `email`, `json`, `ipv4`, `min=1,max=9`
 - `LIST`  
  不会做校验，只影响以 map strict 格式返回时，是否自动对值进行转换成 list。
  比如 value_type=`STRING` value_type_sub=`LIST`,conf_value=`a, b,c`，返回时将会是`"conf_value": ["a", "b", "c"]`
### 怎么选择合适的 value_type, value_type_sub
- 例 1：  
字节类型 max_allowed_packet 可以设置为 STRING BYTES `64m`,`[1, 1g]` ，也可以设置为 INT RANGE `67108864`,`[1, 1073741824]`，看实际需求

- 例 2：  
timeout_ms 这种已经带单位的，值一般是 INT，不使用 STRING DURATION。同理 disk_size_mb 应该是个 INT
没带单位的，按照实际客户端程序可识别的配置进行设置。

- 例 3：
value_type=`STRING` value_type_sub=`ENUM` value_allowed=`true | false` 可以当做布尔来用
效果相当于 value_type=`BOOL` value_type_sub=`ENUM`, 区别在于如果启用strict模式按照数据类型返回，STRING ENUM 返回`"xxx": "true"`，而 BOOL ENUM  返回`"xxx": true`