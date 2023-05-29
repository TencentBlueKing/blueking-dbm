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