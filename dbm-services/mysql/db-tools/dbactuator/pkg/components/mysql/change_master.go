/*
 * @Description:
 	建立主从关系,并不实际操作建立主从关系之前的操作比如数据同步
	并判断主从关系是否正常

	预检查
	1 master: 端口连通性
	2 master: repl 账户权限
	3 当前实例: 是否已经存在主从关系
		3.1 存在主从关系,但是主从关系错误 reset slave后继续执行
		3.2 存在主从关系,但是主从关系ok  直接抛错
		3.3 增加 force 参数，reset slave 继续执行
	4 当前实例: 端口连通性`
*/

package mysql

import (
	"fmt"
	"time"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/common"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil"
)

type BuildMSRelationComp struct {
	// 本地使用 ADMIN, change master 使用 repl
	GeneralParam *components.GeneralParam `json:"general"`
	Params       *BuildMSRelationParam    `json:"extend"`
	db           *native.DbWorker         // 本地db链接
	mdb          *native.DbWorker         // 使用repl账户去连接master db
	checkVars    []string                 // 同步前需要检查的参数
}

type BuildMSRelationParam struct {
	// 具体操作内容需要操作的参数
	Host        string `json:"host"  validate:"required,ip"`                        // 当前实例的主机地址
	Port        int    `json:"port"  validate:"required,lte=65535,gte=3306"`        // 当前实例的端口
	MasterHost  string `json:"master_host"  validate:"required,ip" `                // change master to 主库ip
	MasterPort  int    `json:"master_port"  validate:"required,lte=65535,gte=3306"` // change master to 主库端口
	IsGtid      bool   `json:"is_gtid"`                                             // 是否启动GID方式进行建立主从
	BinFile     string `json:"bin_file" validate:"required"`                        // binlog 文件名称
	BinPosition int64  `json:"bin_position" validate:"required,gte=0"`              // binlog 位点信息
	// 最大容忍延迟, 当 主从延迟 小于 该值, 认为建立主从关系成功. 不传或者为 0 时，表示不检查
	MaxTolerateDelay int `json:"max_tolerate_delay"`
	// 如果当前实例存在主从关系是否直接reset slave后,强制change master
	Force bool `json:"force" example:"false"`
	// 不启动 io_thread。默认false 表示启动 io_thread
	NotStartIOThread bool `json:"not_start_io_thread" example:"false"`
	// 不启动 sql_thread。默认false 表示启动 sql_thread
	NotStartSQLThread bool `json:"not_start_sql_thread" example:"false"`
}

func (b *BuildMSRelationComp) Example() interface{} {
	comp := BuildMSRelationComp{
		GeneralParam: &components.GeneralParam{
			RuntimeAccountParam: components.RuntimeAccountParam{
				MySQLAccountParam: common.MySQLAdminReplExample,
			},
		},
		Params: &BuildMSRelationParam{
			Host:              "1.1.1.1",
			Port:              3306,
			MasterHost:        "1.1.1.2",
			MasterPort:        3306,
			BinFile:           "binlog20000.001234",
			BinPosition:       4,
			NotStartIOThread:  false,
			NotStartSQLThread: false,
			Force:             false,
		},
	}
	return comp
}

func (b *BuildMSRelationComp) Init() (err error) {
	b.db, err = native.InsObject{
		Host: b.Params.Host,
		Port: b.Params.Port,
		User: b.GeneralParam.RuntimeAccountParam.AdminUser,
		Pwd:  b.GeneralParam.RuntimeAccountParam.AdminPwd,
	}.Conn()
	if err != nil {
		logger.Error("connect %s:%d failed,err:%s", b.Params.Host, b.Params.Port, err.Error())
		return err
	}
	b.mdb, err = native.InsObject{
		Host: b.Params.MasterHost,
		Port: b.Params.MasterPort,
		User: b.GeneralParam.RuntimeAccountParam.ReplUser,
		Pwd:  b.GeneralParam.RuntimeAccountParam.ReplPwd,
	}.Conn()
	if err != nil {
		logger.Error("connect master %s:%d failed,err:%s", b.Params.MasterHost, b.Params.MasterPort, err.Error())
		return err
	}
	b.checkVars = []string{
		"character_set_system", "character_set_server",
		"collation_server", "character_set_client",
	}
	return nil
}

// CheckMSVersion 检查主从的版本
//
//	@receiver b
//	@return err
func (b *BuildMSRelationComp) CheckMSVersion() (err error) {
	slaveVersion, err := b.db.SelectVersion()
	if err != nil {
		return fmt.Errorf("get slave version failed:%w", err)
	}
	masterVersion, err := b.mdb.SelectVersion()
	if err != nil {
		return fmt.Errorf("get master version failed:%w", err)
	}
	return mysqlutil.VersionCompare(masterVersion, slaveVersion)
}

// CheckCharSet 检查主从的字符集是否一致
//
//	@receiver b
//	@return err
func (b *BuildMSRelationComp) CheckCharSet() (err error) {
	return b.db.MySQLVarsCompare(b.mdb, b.checkVars)
}

// CheckCurrentSlaveStatus 检查当前实例是否存在复制关系 如果force= false,会退出
//
//	@receiver b
//	@return err
func (b *BuildMSRelationComp) CheckCurrentSlaveStatus() (err error) {
	// 检查当前实例是否已经存在进程
	slaveStatus, err := b.db.ShowSlaveStatus()
	if err != nil {
		logger.Error("%s:err:%s", util.AtWhere())
		return err
	}
	var emptySlaveStatus native.ShowSlaveStatusResp
	// 当前实例无同步信息
	if slaveStatus == emptySlaveStatus {
		return nil
	}
	//  如果没有加强制参数，只要存在关系，就抛出错误
	if !b.Params.Force {
		return fmt.Errorf("当前实例实际存在主从关系, master_host=%s, master_port=%d",
			slaveStatus.MasterHost, slaveStatus.MasterPort)
	}
	logger.Info("show slave status Info is %v", slaveStatus)
	// 强制参数force=true，直接执行stop slave && reset slave
	// Stop Slave
	if err = b.stopSlave(); err != nil {
		logger.Error("Force Change Master,Stop Slave Failed %s", err.Error())
		return
	}
	// Reset Slave All
	if err = b.resetSlaveAll(); err != nil {
		logger.Error("Force Change Master,Reset Slave All Failed %s", err.Error())
		return
	}
	return
}

/**
 * @description: 执行change master,建立主从关系
 * @return {*}
 */
func (b *BuildMSRelationComp) BuildMSRelation() (err error) {
	logger.Info("begin change Master to %s:%d", b.Params.MasterHost, b.Params.Port)
	changeMasterSql := b.getChangeMasterSql()
	logger.Info("change master sql: %s", changeMasterSql)
	if _, err = b.db.Exec(changeMasterSql); err != nil {
		logger.Error("change master to %s:%d failed,err:%s", b.Params.MasterHost, b.Params.MasterPort, err.Error())
		return err
	}
	if err = b.startSlaveThread(!b.Params.NotStartIOThread, !b.Params.NotStartSQLThread); err != nil {
		logger.Error("start slave failed:%s", err.Error())
		return err
	}
	return
}

/**
 * @description: 尝试多次去check show slave status,建立主从关系可能会因为网络等原因,会比较慢
 * @return {*}
 */
func (b *BuildMSRelationComp) CheckBuildOk() (err error) {
	return util.Retry(
		util.RetryConfig{Times: 60, DelayTime: 2 * time.Second},
		func() error { return b.checkSlaveStatus() },
	)
}

/**
 * @description: 根据show slave status 检查主从是否建立正常
 * @return {*}
 */
func (b *BuildMSRelationComp) checkSlaveStatus() (err error) {
	ss, err := b.db.ShowSlaveStatus()
	if err != nil {
		logger.Error("%s exec show slave status failed:%s", util.AtWhere(), err.Error())
	}
	if !ss.ReplSyncIsOk() {
		errMsg := fmt.Sprintf("IOThread:%s,SQLThread:%s", ss.SlaveIORunning, ss.SlaveSQLRunning)
		return fmt.Errorf(errMsg)
	}
	if b.Params.MaxTolerateDelay > 0 && int(ss.SecondsBehindMaster.Int64) > b.Params.MaxTolerateDelay {
		errMsg := fmt.Sprintf(
			"同步线程IO已经正常, 主从延迟%d 大于%d",
			ss.SecondsBehindMaster.Int64,
			b.Params.MaxTolerateDelay,
		)
		return fmt.Errorf(errMsg)
	}
	return nil
}

/**
 * @description: 执行 stop slave
 * @return {*}
 */
func (b *BuildMSRelationComp) stopSlave() (err error) {
	_, err = b.db.Exec("stop slave;")
	return
}

/**
 * @description: 执行 start slave
 * @return {*}
 */
func (b *BuildMSRelationComp) startSlave() (err error) {
	_, err = b.db.Exec("start slave;")
	return
}

func (b *BuildMSRelationComp) startSlaveThread(ioThread, sqlThread bool) (err error) {
	if ioThread && sqlThread {
		_, err = b.db.Exec("start slave;")
	} else if ioThread {
		_, err = b.db.Exec("start slave io_thread;")
	} else if sqlThread {
		_, err = b.db.Exec("start slave sql_thread;")
	}
	return
}

/**
 * @description: 执行reset slave all
 * @return {*}
 */
func (b *BuildMSRelationComp) resetSlaveAll() (err error) {
	_, err = b.db.Exec("reset slave all;")
	return
}

/**
 * @description: 拼接 change master sql
 * @return {*}
 */
func (b *BuildMSRelationComp) getChangeMasterSql() (changeMastersql string) {
	replUser := b.GeneralParam.RuntimeAccountParam.ReplUser
	replPwd := b.GeneralParam.RuntimeAccountParam.ReplPwd
	changeMastersql = fmt.Sprintf(
		`CHANGE MASTER TO MASTER_HOST='%s', 
	MASTER_USER ='%s', 
	MASTER_PASSWORD='%s',
	MASTER_PORT=%d,MASTER_LOG_FILE='%s',
	MASTER_LOG_POS=%d`,
		b.Params.MasterHost, replUser, replPwd, b.Params.MasterPort, b.Params.BinFile, b.Params.BinPosition,
	)

	if b.Params.IsGtid {
		// 如果是gitd，则使用gitd方式构建主从复制命令
		changeMastersql = fmt.Sprintf(
			`CHANGE MASTER TO MASTER_HOST='%s', 
		MASTER_USER ='%s', MASTER_PASSWORD='%s',MASTER_PORT=%d, MASTER_AUTO_POSITION = 1;`,
			b.Params.MasterHost, replUser, replPwd, b.Params.MasterPort,
		)
	}
	return
}
