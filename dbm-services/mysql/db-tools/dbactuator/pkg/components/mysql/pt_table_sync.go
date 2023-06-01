// 通过工具pt-table-sync 工具对主从数据做数据修复
// 修复前会做一系列的前置检查行为，尽量保证数据能修复正常
// 原子任务需要兼容两个触发场景：手动检验而发起修复场景、例行检验而发起修复场景。两种场景因为处理逻辑稍微不同，需要部分区别对待

package mysql

import (
	"crypto/rand"
	"fmt"
	"math/big"
	"strings"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/tools"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
)

const checkSumDB = native.INFODBA_SCHEMA
const slaveBehindMasterLimit = 1800 // slave不能落后master 半小时以上
const chunkSize = "10000"           // pt-table-sync每次修复的chunk单位,检验时候会用到
// Charset TODO
const Charset = "binary" // 目前统一使用binary字符集
// SyncExitStatus2 TODO
const SyncExitStatus2 = "exit status 2" // 如果执行信息返回状态为2，是代表真的有数据不一致的情况，视为程序执行正常

// PtTableSyncComp TODO
type PtTableSyncComp struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Params       *PtTableSyncParam        `json:"extend"`
	PtTableSyncCtx
	tools *tools.ToolSet
}

// PtTableSyncParam TODO
// 2023/0203 增加例行校验发起修复所需要的参数：start_time、end_time、is_routine_trigger
type PtTableSyncParam struct {
	Host                string `json:"host" validate:"required,ip"`
	Port                int    `json:"port" validate:"required,lt=65536,gte=3306"`
	MasterHost          string `json:"master_host" validate:"required,ip"`
	MasterPort          int    `json:"master_port" validate:"required,lt=65536,gte=3306"`
	IsSyncNonInnodbTbls bool   `json:"is_sync_non_innodb"`
	SyncUser            string `json:"sync_user" validate:"required"`
	SyncPass            string `json:"sync_pass" validate:"required"`
	CheckSumTable       string `json:"check_sum_table" validate:"required"`
	StartTime           string `json:"start_time"`
	EndTime             string `json:"end_time"`
	IsRoutineTrigger    bool   `json:"is_routine_trigger"`
	// Synctables        []string `json:"sync_tables"`
	// SyncDbs           []string `json:"SyncDbs"`
}

// PtTableSyncCtx 定义任务执行时需要的上下文
type PtTableSyncCtx struct {
	tableSyncMap          []TableSyncInfo
	dbConn                *native.DbWorker
	masterDbConn          *native.DbWorker
	tempCheckSumTableName string
}

// TableSyncInfo 定义待修复表的信息结构体
type TableSyncInfo struct {
	DbName    string `db:"DbName"`
	TableName string `db:"TableName"`
}

// TableInfo TODO
type TableInfo struct {
	DbName    string `db:"TABLE_SCHEMA"`
	TableName string `db:"TABLE_NAME"`
	Engine    string `db:"ENGINE"`
}

// Example TODO
func (c *PtTableSyncComp) Example() interface{} {
	comp := PtTableSyncComp{
		Params: &PtTableSyncParam{
			Host:                "1.1.1.1",
			Port:                10000,
			MasterHost:          "1.1.1.2",
			MasterPort:          10000,
			IsSyncNonInnodbTbls: false,
			CheckSumTable:       "checksum",
			SyncUser:            "xxx",
			SyncPass:            "xxx",
		},
	}
	return comp
}

// Init 定义act的初始化内容
func (c *PtTableSyncComp) Init() (err error) {

	// 连接本地实例的db（其实是从实例）
	c.dbConn, err = native.InsObject{
		Host: c.Params.Host,
		Port: c.Params.Port,
		User: c.GeneralParam.RuntimeAccountParam.AdminUser,
		Pwd:  c.GeneralParam.RuntimeAccountParam.AdminPwd,
	}.Conn()
	if err != nil {
		logger.Error("Connect %d failed:%s", c.Params.Port, err.Error())
		return err
	}
	// 远程连接传入过来的master实例，用临时账号
	c.masterDbConn, err = native.InsObject{
		Host: c.Params.MasterHost,
		Port: c.Params.MasterPort,
		User: c.Params.SyncUser,
		Pwd:  c.Params.SyncPass,
	}.Conn()
	if err != nil {
		logger.Error("Connect %d failed:%s", c.Params.Port, err.Error())
		return err
	}

	// 获取checksum 表中数据校验异常的表信息
	err = c.getTableSyncMap()
	if err != nil {
		return err
	}
	// 拼接临时表的名称
	randomNum, _ := rand.Int(rand.Reader, big.NewInt(100000))
	c.PtTableSyncCtx.tempCheckSumTableName = fmt.Sprintf("checksum_%s_%d", c.Params.SyncUser, randomNum)

	return nil
}

// Precheck 定义act的前置检测行为
// 检测记录异常的表,现在是否存在；
// 现在的节点的同步是否还是现在的主库，同步是否正常
func (c *PtTableSyncComp) Precheck() (err error) {

	// 判断传入过来的checksum表是否存在
	if !c.isExistCheckSumTable() {
		return fmt.Errorf("The checksum table [%s.%s] maybe not exit ", checkSumDB, c.Params.CheckSumTable)
	}

	slaveStatus, err := c.dbConn.ShowSlaveStatus()
	if err != nil {
		return err
	}
	// 同步是否正常
	if !slaveStatus.ReplSyncIsOk() {
		errMsg := fmt.Sprintf(
			"IOThread:%s,SQLThread:%s",
			slaveStatus.SlaveIORunning, slaveStatus.SlaveSQLRunning,
		)
		return fmt.Errorf(errMsg)
	}
	// 目前节点的master是否是参数传入的master
	if slaveStatus.MasterHost != c.Params.MasterHost || slaveStatus.MasterPort != c.Params.MasterPort {
		errMsg := fmt.Sprintf(
			"The current node syncs this node[%s:%d], not this node[%s:%d]",
			slaveStatus.MasterHost, slaveStatus.MasterPort, c.Params.MasterHost, c.Params.MasterPort,
		)
		return fmt.Errorf(errMsg)
	}
	// 如果该节点如果了落后时间时间大于1800s ，则程序先异常退出，可等待主从复制同步后再重试任务
	if slaveStatus.SecondsBehindMaster.Int64 >= slaveBehindMasterLimit {
		errMsg := fmt.Sprintf(
			"The slave node [%s:%d] data lags behind the master [%s:%d] by more than 1800s, so exit first",
			c.Params.Host, c.Params.Port, c.Params.MasterHost, c.Params.MasterPort,
		)
		return fmt.Errorf(errMsg)
	}
	// 判断最终待修复的表信息列表是否为空,后续引入忽略表的参数，最终可能会为空
	if len(c.tableSyncMap) == 0 {
		return fmt.Errorf("Check that the list to be fixed is empty ")
	}
	// 加载pt-table-sync 工具路径
	c.tools, err = tools.NewToolSetWithPick(tools.ToolPtTableSync)
	if err != nil {
		logger.Error("init toolset failed: %s", err.Error())
		return err
	}

	return nil
}

// ExecPtTableSync 定义下发pt-table-sync工具去执行数据修复的过程
// 目前的按照表的维度来下发修复，每修复进程完，记录对应的表已修复完成，打印到日志上
// 如果其中某张表修复出现异常，db-act进程不中断，对下一张表进行修复。失败的表打印到日志上
// 修复表之前看看表是否满足修复条件，如果不满足，则跳过对这个表的修复
func (c *PtTableSyncComp) ExecPtTableSync() (err error) {
	// 定义出现修复异常表的失败的表数量
	var errTableCount int = 0
	// 定义出现跳过表修复的数量
	var skipTableCount int = 0

	// 定义数据修复的checksum表名
	var getChecksumName string

	// 获取工具文件路径
	PtTableSyncPath, err := c.tools.Get(tools.ToolPtTableSync)
	if err != nil {
		logger.Error("get %s failed: %s", tools.ToolPtTableSync, err.Error())
		return err
	}

	for _, syncTable := range c.tableSyncMap {
		// 先在master实例判断表是否符合修复条件
		if !c.checkTable(syncTable.DbName, syncTable.TableName) {
			skipTableCount++
			logger.Warn(
				fmt.Sprintf(
					"The table [%s.%s] does not conform to the behavior of this data repair, skip sync",
					syncTable.DbName, syncTable.TableName,
				),
			)
			continue
		}

		if c.Params.IsRoutineTrigger {
			// 例行检查发起的数据修复，用临时表作为修复依据
			getChecksumName = c.PtTableSyncCtx.tempCheckSumTableName
			if !c.CopyTableCheckSumReport(syncTable.DbName, syncTable.TableName, getChecksumName) {
				return fmt.Errorf("copy table data error")
			}

		} else {
			// 否则使用传入记录表
			getChecksumName = c.Params.CheckSumTable
		}

		// 拼接pt-table-sync 的执行命令
		syncCmd := fmt.Sprintf(
			"%s --execute --replicate=%s.%s --sync-to-master --no-buffer-to-client --no-check-child-tables "+
				"--chunk-size=%s --databases=%s --tables=%s --charset=%s h=%s,P=%d,u=%s,p=%s",
			PtTableSyncPath, checkSumDB, getChecksumName, chunkSize, syncTable.DbName,
			syncTable.TableName, Charset, c.Params.Host, c.Params.Port, c.Params.SyncUser, c.Params.SyncPass,
		)

		// logger.Info("executing %s", syncCmd)
		output, err := osutil.ExecShellCommand(false, syncCmd)

		if err != nil && !strings.Contains(err.Error(), SyncExitStatus2) {
			// 如果修复某张表时候进程查询异常，不中断，记录异常信息，执行下张表的修复
			logger.Error("exec cmd get an error:%s,%s", output, err.Error())
			errTableCount++
			continue
		}
		logger.Info("syncing-table [%s.%s] has been executed successfully", syncTable.DbName, syncTable.TableName)
	}
	logger.Info(
		"Number of successful fixes: %d ,Number of failed fixes: %d, Number of skip fixes: %d",
		len(c.tableSyncMap)-errTableCount-skipTableCount, errTableCount, skipTableCount,
	)

	// 如果真的存在部分表修复异常，则返回失败
	if errTableCount != 0 {
		return fmt.Errorf("error")
	}
	return nil
}

// getTableSyncMap 查询本地实例的checksum检测结果异常的表信息
func (c *PtTableSyncComp) getTableSyncMap() (err error) {
	var checkSQL string
	if c.Params.IsRoutineTrigger {
		// 例行检测校验触发的数据修复场景
		checkSQL = fmt.Sprintf(
			`select db as DbName ,tbl as TableName from %s.%s where (this_crc <> master_crc or this_cnt <> master_cnt) 
			 and (ts between '%s' and '%s')  group by db, tbl`,
			checkSumDB, c.Params.CheckSumTable, c.Params.StartTime, c.Params.EndTime,
		)
	} else {
		// 常规校验而触发数据修复
		checkSQL = fmt.Sprintf(
			"select db as DbName ,tbl as TableName from %s.%s where this_crc <> master_crc or this_cnt <> master_cnt group by db, tbl",
			checkSumDB, c.Params.CheckSumTable,
		)
	}

	// 这里查询返回空的话，先不在这里报错退出
	err = c.dbConn.Queryx(&c.tableSyncMap, checkSQL)
	if err != nil && !c.dbConn.IsNotRowFound(err) {
		logger.Error(err.Error())
		return err
	}

	return nil

}

// isExistCheckSumTable 判断本地实例是否存在checksum表
func (c *PtTableSyncComp) isExistCheckSumTable() bool {
	checkSumSql := fmt.Sprintf(
		"select 1 from information_schema.tables where TABLE_SCHEMA = '%s' and TABLE_NAME = '%s' ;",
		checkSumDB, c.Params.CheckSumTable,
	)
	_, err := c.dbConn.Query(checkSumSql)
	if err != nil {
		logger.Error(err.Error())
		return false
	}
	return true
}

// checkTable 在master实例检验表是否符合修复规格: 检测表是否在主库存在；表的引擎是否事务引擎
func (c *PtTableSyncComp) checkTable(dbName string, tableName string) bool {

	var tableInfo []TableInfo

	checkSumSql := fmt.Sprintf(
		"select TABLE_SCHEMA, TABLE_NAME, ENGINE from information_schema.tables where TABLE_SCHEMA = '%s' and TABLE_NAME = '%s' ;",
		dbName, tableName,
	)
	err := c.masterDbConn.Queryx(&tableInfo, checkSumSql)
	if err != nil {
		logger.Error(err.Error())
		return false
	}
	// 检测是否是非事务引擎表，目前事务引擎只有 innodb和tokudb
	if !c.Params.IsSyncNonInnodbTbls && !(tableInfo[0].Engine == "InnoDB" || tableInfo[0].Engine == "TokuDB") {
		logger.Error(fmt.Sprintf("The table [%s.%s] is not a transaction engine table", dbName, tableName))
		return false
	}
	return true
}

// DropSyncUser 修复后删除主从节点的临时数据修复账号
func (c *PtTableSyncComp) DropSyncUser() (err error) {

	logger.Info("droping sync user ....")
	userHost := fmt.Sprintf("%s@%s", c.Params.SyncUser, c.Params.Host)

	// 在主节点删除
	if _, err := c.masterDbConn.Exec(fmt.Sprintf("drop user %s;", userHost)); err != nil {
		logger.Error(
			"drop %s failed:%s in the instance [%s:%d]", userHost, err.Error(), c.Params.MasterHost,
			c.Params.MasterPort,
		)
		return err
	}
	// 在本地节点删除
	if _, err := c.dbConn.Exec(fmt.Sprintf("drop user %s;", userHost)); err != nil {
		logger.Error("drop %s failed:%s in the instance [%s:%d]", userHost, err.Error(), c.Params.Host, c.Params.Port)
		return err
	}
	logger.Info("drop-user has been executed successfully")
	return nil
}

// CopyTableCheckSumReport 处理将需要修复表的异常检验结果复制到临时表
// 这个针对巡检例行校验而触发的数据修复场景
// 原因是实例的checksum-report是历史表，包括存在很多历史记录，影响到pt-table-sync工具修复进度
func (c *PtTableSyncComp) CopyTableCheckSumReport(DBName string, tableName string, tempCheckSumTableName string) bool {
	// 定义复制数据SQL列表
	var copySQLs []string

	// 校验必要参数的逻辑
	if !(c.Params.IsRoutineTrigger && len(c.Params.StartTime) != 0 && len(c.Params.EndTime) != 0) {
		logger.Error(
			"The required parameter is unreasonable,if is_routine_trigger is true, start_time and end_time is not null ",
		)
		return false
	}

	// 在master创建临时checksum临时表
	if _, err := c.masterDbConn.Exec(
		fmt.Sprintf(
			"create table if not exists %s.%s like %s.%s ;",
			checkSumDB, tempCheckSumTableName, checkSumDB, c.Params.CheckSumTable,
		),
	); err != nil {
		logger.Error("create table %s failed:[%s]", tempCheckSumTableName, err.Error())
		return false
	}

	// 导入异常记录在临时表上
	copySQLs = append(copySQLs, "set binlog_format = 'Statement' ;")
	copySQLs = append(copySQLs, fmt.Sprintf("truncate table %s.%s ;", checkSumDB, tempCheckSumTableName))
	copySQLs = append(
		copySQLs,
		fmt.Sprintf(
			"insert into %s.%s select * from %s.%s  where db = '%s' and tbl = '%s' and ts between '%s' and '%s' ",
			checkSumDB,
			tempCheckSumTableName,
			checkSumDB,
			c.Params.CheckSumTable,
			DBName,
			tableName,
			c.Params.StartTime,
			c.Params.EndTime,
		),
	)
	copySQLs = append(copySQLs, "set binlog_format = 'ROW' ;")

	if _, err := c.masterDbConn.ExecMore(copySQLs); err != nil {
		logger.Error("create table %s failed:[%s]", tempCheckSumTableName, err.Error())
		return false
	}

	return true
}

// DropTempTable 删除临时表
func (c *PtTableSyncComp) DropTempTable() (err error) {

	if len(c.PtTableSyncCtx.tempCheckSumTableName) == 0 {
		// 判断临时表是否为空，为空则跳过
		logger.Info("temp-table is null, skip")
		return nil
	}

	logger.Info(fmt.Sprintf("droping Temp table :%s ....", c.PtTableSyncCtx.tempCheckSumTableName))
	if _, err := c.masterDbConn.Exec(
		fmt.Sprintf(
			"drop table if exists %s.%s;",
			checkSumDB,
			c.PtTableSyncCtx.tempCheckSumTableName,
		),
	); err != nil {
		logger.Error("drop temp table failed")
		return err
	}
	logger.Info("drop-temp-table has been executed successfully")
	return nil
}
