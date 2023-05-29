# DB个性化配置管理

develop build:

```
./build.sh
```

api docs:
链接: http://localhost:8080/swagger/

# 1. 名词定义

## 配置级别 level_name

表现配置上下级继承关系字段，的当前配置允许的 level_name 有：

- `plat` 平台级
- `app` 业务级
- `module` 模块级
- `cluster` 集群级 请求配置(查询/更新)需要提供 level_name level_value，代表用户想操作的配置级别节点。

## 配置类型 conf_type

比如数据库配置、备份配置，代表某namespace 下的一类配置，一般与一个应用程序或者服务挂钩。

## 配置文件 conf_file

某一个 conf_type 下的独立的子类，通过 conf_file 区分。可以是一个逻辑概念，不一定要有一个这样的实体配置文件名，可以一次 conf_type 请求可以拿到多个 conf_file 的配置项。 大多数情况一个
conf_type 可能只有一个 conf_file，像数据库不同的db大版本如果配置不兼容，也可以通过 conf_file 来区分db大版本。

- 比如 `conf_type = 'dbconf'`, `conf_file` 可以是`MySQL-5.6`、`MySQL-5.7`，代表不同的版本配置
- 比如 `conf_type = 'init_user'`, `conf_file` 可以是`mysql#user`、`proxy#user`，代表不同的子配置类型

配置文件有几个属性：

- 是否版本化 versioned
- 是否校验 conf_name
- 是否校验 conf_value

不支持跨多个 `conf_type` 查询配置，但可以一次查询相同 conf_type 下的多个 conf_file。

### 版本化 versioned

一个配置文件可以设置是否支持版本化，启用版本化后，修改 conf_file 的配置项 需要发布才会生效，发布后会生成一个新 version，可以看到历史 version。对应非版本化配置文件 称作 un-versioned
conf_file。

- 修改 版本化的 conf_file 配置项，使用接口 `confitem/upsert`
- 修改 非版本化的 conf_file 配置项，使用接口 `confitem/save`
- 生成一个新版本配置文件，使用接口 `version/generate`，它有发布版本和获取最新版本配置项的作用。
- 查询配置项接口 不区分是否版本化 `confitem/query`

### 校验配置名

启用校验配置名 conf_name_validate=1，在写入配置时会校验该conf_file 这个 conf_name 是否已定义。不在预定义列表的配置名不允许写入

### 校验配置值

启用校验配置值 conf_value_validate=1，在写入配置时会与对应 conf_name 的 value_type，value_type_sub，value_allowed 进行检查。

- 数据类型 value_type，当前允许值 `STRING`, `INT`, `FLOAT`, `NUMBER`
- 为了更好的检验值，value_type_sub 指定具体的类型子类，当前允许值
    - `RANGE`: 指定范围，格式如 `(0,100]`
    - `ENUM`: 枚举值，格式如  `ON|OFF`、`0|1|2|`。当允许为空时，表示值为空
    - `ENUMS`: 枚举值，值可以是,分隔的多个枚举
    - `JSON`： 一种特殊的STRING，会验证 value 是否是一个合法的json字符串
    - `REGEX`: 一种特殊的STRING，会验证 value 是否满足 value_allowed 正则
    - `BYTES`: 一种特殊的STRING，比如 64m, 128k格式，会转换成bytes与 value_allowed 的范围进行比较
    - `BOOL`: 一种特殊的 ENUM，参数值允许为空, value_allowed 类似格式 `ON | OFF |`。 当允许为空时，表示该配置生效标志(即`--skip-name-resolve`,
      不需要`--skip-name-resolve=ON`)


value_default 设置配置项的默认值，当它带占位符时，有两种设置：
- 可以把 tb_config_name_def 里面 flag_status=2 代表只读，前端对应的对只读字段不允许修改（需要前端配合实现）
 即不允许修改的占位符，只能自动计算出 conf_value
- 允许值默认值里加上 on | yes | {{cluster-enabled}}，就是可以由程序生成，但也可以强制设置成 1 个固定值
 级允许修改的占位符，可以自由选择是设置一个值，或者自动计算

## 配置项 conf_item

配置文件里面的多个配置项，配置项有几个关键属性：

- 配置名 conf_name
- 配置值 conf_value
- 配置级别level_name level_value
- 是否锁定，该配置项是否在当前级别锁定
- 是否需要重启，该配置项修改值后是否需要重启

## 配置项返回格式

请求配置项(都是合并了上级配置)，主要有 list 和 map 两种返回格式。

- `list` 会返回更多的配置项信息，包括 flag_locked，description 登
- `map` 以 key:value 星期返回 conf_name:conf_value
- `map.`, `map#`, `map|` 是特殊的map格式，返回结果会以 `.` 或者 `#` 或者 `|` 拆分 conf_name

## 配置项继承

目前有 `plat`, `app`, `module`, `cluster` 几个层级的继承关系。
我们根据配置的层级分为：
- plat_config  
 全局公共配置，包括配置项的定义(值数据类型、默认值、是否需要重启等)
- level_config  
 level_config 是具有继承关系的配置中间节点，不会体现在物理的集群或者实例上，是增量配置。
 如果查看某个中间节点的全量配置，叫 merged_config，合并了上层级配置
- versioned_config  
 versioned_config 即已经为目标物理集群或者实例，生成的一份配置，通过版本化来管理，是一种特殊的 merged_config。
 非版本化的配置，不会生成 versioned_config
- runtime_config  
 实际跑在目标集群或者机器上的配置。

## 配置项锁定

conf_name的字段 flag_locked代表在该 level_name 配置的锁定状态。锁定之后，它的下层级配置不允许修改，只能继承它的配置。如果下层级已经存在配置，当前层级进行锁定时，会提示删除下层级配置。
锁定配置项的conf_value修改，会提示更新它的下级配置文件。

## 配置发布 publish

- 查询配置 查询配置 隐含了从上层级合并配置再返回
- 编辑配置 编辑配置，一般指编辑配置项，编辑后可以选择 仅保存 或者 保存并发布（目前只用 保存并发布）
- 查询配置文件 查询配置文件，会连同配置文件的描述信息、配置项一起返回
- 查询配置版本 查询版本列表或者历史某个版本详情，详情里包括修改行数、差异对比

## 配置应用 apply
- level_config 应用是指将当前层级配置修改，同步给它的直接下级，也可以叫 配置同步  
 同步时时根据是否当前配置项是否锁定，分为强制应用和普通应用。如果修改的是非锁定状态配置，目前不需要同步给下级。
 level_config 的`应用到下级`，会给它下层级发布版本(但不应用)
 锁定配置应用，会强制应用给所有直接下级。
- versioned_config 应用是指将已发布配置，`应用到目标实例`上  

## 配置值加密
在 tb_config_name_def 的 `flag_encrypt` 字段 控制是否对 value 进行加密
在 `conf/config.yaml` 里面 `encrypt.keyPrefix` 用于设置加密 key 的前缀。注意这个值在一个新环境下用于保持不变，否则无法解密已加密字段。

# 2. 字段定义

**配置文件相关**

- `bk_biz_id` bkcc 业务ID
- `namespace` 命名空间
- `namespace_info` 命名空间信息
- `conf_type` 配置类型
- `conf_file` 配置文件

**配置项相关**

- `conf_item` 配置条目，也叫配置项
- `conf_name` 配置项名字
- `conf_value` 配置值
- `level_name` 配置层级名
- `level_value` 配置层级的值

**配置定义相关**

- `value_default` 配置项默认值
- `value_allowed` 配置项允许值
- `flag_locked` 配置项是否锁定
- `flag_encrypt` 配置项的值是否透明加密保存

# 3. 怎么定义可存取数据

1. 只有注册过的 namespace,conf_type，才能往里面写数据，且需设定 conf_name_validate, conf_value_validate, level_versioned
2. 只有平台配置里面 flag_status >= 1 的配置项，才会出现在公共配置里。 
 - flag_status = -1 的配置表示预定义的可引用的 预定义配置名列表，不会出现在渲染后的公共配置中
 - flag_status = 1 可读、可修改默认值和允许值的公共配置，会出现在渲染结果中
 - flag_status = 2 只读配置，无论在哪都不能修改，但会出现在渲染结果中
3. 编辑任意平台配置，且 flag_status = -1 时，也会自动渲染在公共配置里

## 缓存

freecache 里面的内容：

1. conf_file_def
2. conf_level_def

目前内置了几个 level_name, 如果不够用也需要手动插入数据库 tb_config_level_def

# migrate
migrate db名需要提前创建，否则服务无法启动。
可以有 2 种 migrate 方法
## go migrate
```
migrate -source file://assets/migrations \
 -database mysql://user:pass@tcp(localhost:3306)/bk_dbconfig?charset=utf8 up
```
migrate 二进制命令可从 https://github.com/golang-migrate/migrate 下载

## ./bkconfigsvr --migrate
```
Usage of ./bkconfigsvr:
      --migrate                 run migrate to databases and exit. set migrate.enable to config.yaml will run migrate and continue 
      --migrate.force int       force the version to be clean if it's dirty
      --migrate.source string   migrate source path
```
- `--migrate` 参数运行后 bkconfigsvr 会退出。
 如果想每次启动 bkconfigsvr 自动 migrate，可以在 conf/config.yaml 中设置`migrate.enable`
- `--migrate` 也会自动读取 config.yaml 中的 force 和 source 配置，当然也可以在命令行读取
 source 遵循 https://github.com/golang-migrate/migrate#migration-sources 里面的地址

## db 表说明
tb_config_file_def: 配置类型和配置文件定义
tb_config_name_def: 平台配置项定义
tb_config_node: 业务、模块、集群等配置项
tb_config_versioned： 已发布配置文件版本