# git.tencent.com/dbs/bk-dbactuator

## dbactuator 

数据库操作指令集合，实现MySQL、Proxy、监控、备份 部署，MySQL、Proxy 变更等原子任务操作，由上层Pipeline 编排组合不同的指令，来完成不同的场景化的任务
```
Db Operation Command Line Interface
Version: 0.0.1 
Githash: 212617a717c3a3a968eb0c7d3a2c4ea2bc21abc2
Buildstamp:2022-05-27_06:42:56AM

Usage:
  dbactuator [flags]
  dbactuator [command]

Available Commands:
  completion  Generate the autocompletion script for the specified shell
  help        Help about any command
  mysql       MySQL Operation Command Line Interface
  proxy       MySQL Proxy Operation Command Line Interface
  sysinit     Exec sysinit_mysql.sh,Init mysql default os user,password

Flags:
  -h, --help             help for dbactuator
  -n, --node_id string   节点id
  -p, --payload string   command payload <base64>
  -r, --rollback         回滚任务
  -x, --show-payload     show payload for man
  -u, --uid string       单据id

Use "dbactuator [command] --help" for more information about a command.
```

## 文档

### subcommand 开发

#### 给 payload 添加说明和 example (swagger)
##### **查看注释**  
```
./dbactuator mysql find-local-backup --helper
```

##### **怎么增加注释到 --helper**  
在 subcommand 定义上添加注释，示例：
```
// FindLocalBackupCommand godoc
//
// @Summary      查找本地备份
// @Description  查找本地备份
// @Tags         mysql
// @Accept       json
// @Param        body body      mysql.FindLocalBackupParam  true  "short description"
// @Success      200  {object}  mysql.FindLocalBackupResp
// @Router       /mysql/find-local-backup [post]
func FindLocalBackupCommand() *cobra.Command {
...
```

- `@Param` 把中间的 `mysql.FindLocalBackupParam` 替换成 subcommand 的参数 struct 定义，且 struct 需要能被当前包引用
 swagger 使用 `@param` 来解析参数，所以不要与其它函数注释冲突，否则可能 build doc 失败，output example 见下文
- `@Router` 格式 `/cmd/subcmd [post]`，保留后面的`[post]`
- 如果没有输出则去掉 `@Success` 这行，output example 见下文

**param struct 的字段注释示例：**
```
// field 枚举说明. 字段注释可以在字段上一行，或者字段行后
Field1 int `json:"field1" enums:"0,1,2"` // 枚举类型
Field2 string `json:"field2" validate:"required" example:"test"`  // 必填项，example内容
Field3 int `json:"field2" valildate:"gte:999,lte:0" default:"2"` // 最大值最小值，默认值
```

##### **怎么增加 example**  
在 component 的 struct 增加 `Example() interface()` 方法，示例：
```
func (f *FindLocalBackupComp) Example() interface{} {
	comp := FindLocalBackupComp{
		Params: FindLocalBackupParam{
			BackupDirs:  []string{"/data/dbbak", "/data1/dbbak"},
			TgtInstance: &common.InstanceExample,
			FileServer:  false,
		},
	}
	return comp
}
```
填充你需要的示例字段，能序列化成 json 格式。

然后在 subcommand 定义里面完善 `Example` 字段，示例：
```
cmd := &cobra.Command{
		Use:   "find-local-backup",
		Example: fmt.Sprintf(`dbactuator mysql find-local-backup %s %s`,
			subcmd.CmdBaseExampleStr, common.ToPrettyJson(act.Service.Example())),
		...
	}
```

如果有输出 output 示例需求，可以参照 `mysql restore-dr` 写一个 `ExampleOutput()`。

##### **生成注释**
需要先从 https://github.com/swaggo/swag 下载 `swag` 命令(推荐 v1.8.12，低版本可能不适应go1.19)。
```
# 需要想先让 swagger 生成注释 docs/swagger.json
# 需要关注注释是否编译成功
./build_doc.sh

# 再编译打包进二进制
make
```
或者一步 `./build.sh`

目前为了避免代码冲突，.gitignore 忽略了 docs/swagger.json, docs/swagger.yaml

### Go开发规范
[https://github.com/golang/go/wiki/CodeReviewComments](https://github.com/golang/go/wiki/CodeReviewComments)


#### 格式化
-  代码都必须用 `gofmt` 格式化。(使用不用ide的同学注意调整)

#### import 规范
- 使用 `goimports` 自动格式化引入的包名，import 规范原则上以 `goimports` 规则为准。

#### 包命名
- 保持 `package` 的名字和目录一致。
- 包名应该为小写单词，不要使用下划线或者混合大小写，使用多级目录来划分层级。
- 不要使用无意义的包名，如：`util`、`common`、`misc`、`global`。`package`名字应该追求清晰且越来越收敛，符合‘单一职责’原则。而不是像`common`一样，什么都能往里面放，越来越膨胀，让依赖关系变得复杂，不利于阅读、复用、重构。注意，`xx/util/encryption`这样的包名是允许的。

#### 文件命名
- 文件名应该采用小写，并且使用下划线分割各个单词。

#### 变量命名
- 变量名必须遵循驼峰式，首字母根据访问控制决定使用大写或小写。
