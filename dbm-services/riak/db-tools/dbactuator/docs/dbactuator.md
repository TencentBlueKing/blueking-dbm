# dbactuator 

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