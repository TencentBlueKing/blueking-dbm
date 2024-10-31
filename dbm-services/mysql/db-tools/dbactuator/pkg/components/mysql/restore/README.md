## 已支持恢复类型
- gztab
- xtrabackup
- logical (dbloader)
- physical (dbloader)

## 开发说明
增加不同的恢复类型，需要实现接口 `Restore` 的以下方法:
```
type Restore interface {
	Init() error
	PreCheck() error
	Start() error
	WaitDone() error
	PostCheck() error
	ReturnChangeMaster() (*mysqlutil.ChangeMaster, error)
}
```
比如 mload_restore, xload_restore, dbloader_restore 都是该接口的实现，`RestoreDRComp` 封装了这个接口对外提供恢复指令，它的`ChooseType`方法决定使用哪种 Restore 实现

dbloader 又分为 logical / physical，恢复行为由 `dbbackup-go/dbbackup` 完成

## actuator 恢复备份数据示例
```
./dbactuator mysql restore-dr --payload-format raw --payload '{
    "general": {
        "runtime_account": {
            "repl_user": "repl",
            "repl_pwd": "xxx"
        }
    },
    "extend": {
        "work_dir": "/data1/dbbak/",
        "backup_dir": "/data/dbbak/",
        "backup_files": {
            "index": [
                "10_123_x.x.x.x_3306_20241030030300_logical.index"
            ]
        },
        "tgt_instance": {
            "host": "1.1.1.1",
            "port": 3306,
            "user": "test",
            "pwd": "test",
            "charset": "",
        },
        "src_instance": {
            "host": "2.2.2.2",
            "port": 3306
        },
        "change_master": false,
        "restore_opts": {
            "databases": [
                "*"
            ],
            "tables": [
                "*"
            ],
            "ignore_databases": null,
            "ignore_tables": null,
            "recover_privs": false,
            "recover_binlog": false,
            "enable_binlog": false,
            "init_command": "",
            "source_binlog_format": ""
        }
    }
}
'
```