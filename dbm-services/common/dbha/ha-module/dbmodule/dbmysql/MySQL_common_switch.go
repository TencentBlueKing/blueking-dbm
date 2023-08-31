/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package dbmysql mysql-related cluster's switch defined in this package, such as TenDBHA,TenDBCluster
package dbmysql

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"strconv"
	"strings"
	"time"

	"dbm-services/common/dbha/ha-module/client"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/dbutil"
	"dbm-services/common/dbha/ha-module/log"

	"gorm.io/driver/mysql"
	"gorm.io/gorm"
)

const (
	// GetPrimarySQL sql to get primary tdbctl
	GetPrimarySQL = "TDBCTL GET PRIMARY"
	// GetRouteSQL TendbCluster used to get all routes
	GetRouteSQL = "SELECT Server_name, Host, Username, Password, Port, Wrapper FROM mysql.servers"
	//FlushRouteSQL TendbCluster used to flush routes
	FlushRouteSQL = "TDBCTL FLUSH ROUTING"
	// ForcePrimarySQL enable primary tdbctl force
	ForcePrimarySQL = "TDBCTL ENABLE PRIMARY FORCE"
	// AlterNodeFormat TDBCTL alter node sql format
	AlterNodeFormat = "TDBCTL ALTER NODE %s OPTIONS(HOST '%s',USER '%s',PASSWORD '%s', Port %d)"
	// DropNodeFormat TDBCTL drop node sql format, valid string is server_name
	DropNodeFormat = "TDBCTL DROP NODE %s"
)

// MySQLCommonSwitch defined mysql-related switch struct
// TenDBHA, TenDBClusterHA usual include this
type MySQLCommonSwitch struct {
	dbutil.BaseSwitch
	//instance role type
	Role string
	//standby slave which master switch to
	StandBySlave dbutil.SlaveInfo
}

// MySQLCommonSwitchUtil common switch util for mysql-related instance used
type MySQLCommonSwitchUtil interface {
	// CheckSlaveStatus and blow func TenDB's backend, TenDBCluster's remote used
	CheckSlaveStatus() error
	GetSlaveCheckSum() (int, int, error)
	GetSlaveDelay() (int, int, error)
	FindUsefulDatabase() (bool, error)
	CheckSlaveSlow() error
	ResetSlave() (string, uint64, error)
	SetStandbySlave([]dbutil.SlaveInfo)

	// SetInstanceRole and blow func all meta-type instance used
	SetInstanceRole(string)
	UpdateMetaInfo() error
}

// SpiderCommonSwitch defined spider-related switch struct
// TenDBCluster special specify, spider/remote usual include this
type SpiderCommonSwitch struct {
	MySQLCommonSwitch
	//primary tdbctl info
	PrimaryTdbctl TdbctlInfo
	ClusterName   string
	//all node's route info, must fill by any-tdbctl
	RouteTable []RouteInfo
}

// DelayInfo defined slave delay info
type DelayInfo struct {
	// check whether SQL_Thread hang
	SlaveDelay float64 `gorm:"column:slave_delay"`
	// check whether IO_Thread hang
	TimeDelay float64 `gorm:"column:time_delay"`
}

// MySQLVariableInfo show variable's result struct
// not appropriate for string value
type MySQLVariableInfo struct {
	VariableName  string `gorm:"column:Variable_name"`
	VariableValue uint64 `gorm:"column:Value"`
}

// BinlogStatus binlog status info struct
type BinlogStatus struct {
	MasterLogFileIndex      int
	RelayMasterLogFileIndex int
	ReadMasterLogPos        uint64
	ExecMasterLogPos        uint64
	// RetrievedGtidSet		string
	// ExecutedGtidSet			string
	// MasterUuid				string
}

// SlaveStatus show slave status info struct
type SlaveStatus struct {
	SlaveIoState               string `gorm:"column:Slave_IO_State"`
	MasterHost                 string `gorm:"column:Master_Host"`
	MasterUser                 string `gorm:"column:Master_User"`
	MasterPort                 int    `gorm:"column:Master_Port"`
	ConnectRetry               int    `gorm:"column:Connect_Retry"`
	MasterLogFile              string `gorm:"column:Master_Log_File"`
	ReadMasterLogPos           uint64 `gorm:"column:Read_Master_Log_Pos"`
	RelayLogFile               string `gorm:"column:Relay_Log_File"`
	RelayLogPos                uint64 `gorm:"column:Relay_Log_Pos"`
	RelayMasterLogFile         string `gorm:"column:Relay_Master_Log_File"`
	SlaveIoRunning             string `gorm:"column:Slave_IO_Running"`
	SlaveSqlRunning            string `gorm:"column:Slave_SQL_Running"`
	ReplicateDoDb              string `gorm:"column:Replicate_Do_DB"`
	ReplicateIgnoreDb          string `gorm:"column:Replicate_Ignore_DB"`
	ReplicateDoTable           string `gorm:"column:Replicate_Do_Table"`
	ReplicateIgnoreTable       string `gorm:"column:Replicate_Ignore_Table"`
	ReplicateWildDoTable       string `gorm:"column:Replicate_Wild_Do_Table"`
	ReplicateWildIgnoreTable   string `gorm:"column:Replicate_Wild_Ignore_Table"`
	LastErrno                  int    `gorm:"column:Last_Errno"`
	LastError                  string `gorm:"column:Last_Error"`
	SkipCounter                int    `gorm:"column:Skip_Counter"`
	ExecMasterLogPos           uint64 `gorm:"column:Exec_Master_Log_Pos"`
	RelayLogSpace              uint64 `gorm:"column:Relay_Log_Space"`
	UntilCondition             string `gorm:"column:Until_Condition"`
	UntilLogFile               string `gorm:"column:Until_Log_File"`
	UntilLogPos                uint64 `gorm:"column:Until_Log_Pos"`
	MasterSslAllowed           string `gorm:"column:Master_SSL_Allowed"`
	MasterSslCaFile            string `gorm:"column:Master_SSL_CA_File"`
	MasterSslCaPath            string `gorm:"column:Master_SSL_CA_Path"`
	MasterSslCert              string `gorm:"column:Master_SSL_Cert"`
	MasterSslCipher            string `gorm:"column:Master_SSL_Cipher"`
	MasterSslKey               string `gorm:"column:Master_SSL_Key"`
	SecondsBehindMaster        int    `gorm:"column:Seconds_Behind_Master"`
	MasterSslVerifyServerCert  string `gorm:"column:Master_SSL_Verify_Server_Cert"`
	LastIoErrno                int    `gorm:"column:Last_IO_Errno"`
	LastIoError                string `gorm:"column:Last_IO_Error"`
	LastSqlErrno               int    `gorm:"column:Last_SQL_Errno"`
	LastSqlError               string `gorm:"column:Last_SQL_Error"`
	ReplicateIgnoreServerIds   string `gorm:"column:Replicate_Ignore_Server_Ids"`
	MasterServerId             uint64 `gorm:"column:Master_Server_Id"`
	MasterUuid                 string `gorm:"column:Master_UUID"`
	MasterInfoFile             string `gorm:"column:Master_Info_File"`
	SqlDelay                   uint64 `gorm:"column:SQL_Delay"`
	SqlRemainingDelay          string `gorm:"column:SQL_Remaining_Delay"`
	SlaveSqlRunningState       string `gorm:"column:Slave_SQL_Running_State"`
	MasterRetryCount           int    `gorm:"column:Master_Retry_Count"`
	MasterBind                 string `gorm:"column:Master_Bind"`
	LastIoErrorTimestamp       string `gorm:"column:Last_IO_Error_Timestamp"`
	LastSqlErrorTimestamp      string `gorm:"column:Last_SQL_Error_Timestamp"`
	MasterSslCrl               string `gorm:"column:Master_SSL_Crl"`
	MasterSslCrlpath           string `gorm:"column:Master_SSL_Crlpath"`
	RetrievedGtidSet           string `gorm:"column:Retrieved_Gtid_Set"`
	ExecutedGtidSet            string `gorm:"column:Executed_Gtid_Set"`
	AutoPosition               string `gorm:"column:Auto_Position"`
	ReplicateWildParallelTable string `gorm:"column:Replicate_Wild_Parallel_Table"`
}

// RouteInfo route in mysql.servers
type RouteInfo struct {
	ServerName string `gorm:"column:Server_name"`
	Host       string `gorm:"column:HOST"`
	UserName   string `gorm:"column:Username"`
	Password   string `gorm:"column:Password"`
	Port       int    `gorm:"column:PORT"`
	Wrapper    string `gorm:"column:Wrapper"`
}

// TdbctlInfo for tdbctl node
type TdbctlInfo struct {
	ServerName string `gorm:"column:SERVER_NAME"`
	Host       string `gorm:"column:HOST"`
	Port       int    `gorm:"column:PORT"`
	//if 1, indicate this server is primary
	CurrentServer int `gorm:"column:IS_THIS_SERVER"`
}

// SetStandbySlave only master instance could call this.
// Always use standbySlave.If no standby attribute slave found, use
// the first index slave
func (ins *MySQLCommonSwitch) SetStandbySlave(slaves []dbutil.SlaveInfo) {
	if len(slaves) > 0 {
		//try to found standby slave
		for _, slave := range slaves {
			if slave.IsStandBy {
				ins.StandBySlave = slave
				break
			}
		}
		ins.StandBySlave = slaves[0]
		log.Logger.Debugf("set standy slave success:%#v", ins.StandBySlave)
	} else {
		ins.StandBySlave = dbutil.SlaveInfo{}
	}
}

// SetInstanceRole set instance role type
func (ins *MySQLCommonSwitch) SetInstanceRole(role string) {
	ins.Role = role
}

// GetRole get mysql role type
func (ins *MySQLCommonSwitch) GetRole() string {
	return ins.Role
}

// CheckSlaveStatus check whether slave satisfy to switch
func (ins *MySQLCommonSwitch) CheckSlaveStatus() error {
	var (
		checksumCnt, checksumFailCnt, slaveDelay, timeDelay int
	)
	gmConf := ins.Config.GMConf
	// check_slave_status
	ins.ReportLogs(constvar.InfoResult, "try to check slave status info.")
	if err := ins.CheckSlaveSlow(); err != nil {
		return fmt.Errorf("check slave delay failed,err:%s", err.Error())
	}

	needCheck, err := ins.FindUsefulDatabase()
	if err != nil {
		log.Logger.Errorf("found user-created database failed. err:%s", err.Error())
	}

	ins.ReportLogs(constvar.InfoResult, "try to check slave checksum info.")
	checksumCnt, checksumFailCnt, err = ins.GetSlaveCheckSum()
	if err != nil {
		log.Logger.Errorf("check slave checksum info failed. err:%s", err.Error())
		return err
	}
	slaveDelay, timeDelay, err = ins.GetSlaveDelay()
	if err != nil {
		log.Logger.Errorf("check slave checksum info failed. err:%s", err.Error())
		return err
	}

	ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("checksumCnt:%d, checksumFail:%d, slaveDelay:%d, timeDelay:%d",
		checksumCnt, checksumFailCnt, slaveDelay, timeDelay))

	if needCheck {
		if ins.Status == constvar.AVAILABLE {
			checksumCnt = 1
			checksumFailCnt = 0
			slaveDelay = 0
			timeDelay = 0
			ins.ReportLogs(constvar.InfoResult, "instance is available, skip check delay and checksum")
		}

		if checksumCnt == 0 {
			return fmt.Errorf("none checksum done on this db")
		}

		log.Logger.Debugf("checksum have done on slave.")

		if checksumFailCnt > gmConf.GCM.AllowedChecksumMaxOffset {
			return fmt.Errorf("too many fail on tables checksum(%d > %d)", checksumFailCnt,
				gmConf.GCM.AllowedChecksumMaxOffset)
		}
		ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("checksum failedCnt[%d] in allowed range[%d]",
			checksumFailCnt, gmConf.GCM.AllowedChecksumMaxOffset))

	} else {
		ins.ReportLogs(constvar.InfoResult, "none user-created database, skip check checksum")
		return nil
	}

	if slaveDelay >= gmConf.GCM.AllowedSlaveDelayMax {
		return fmt.Errorf("SQL_Thread delay on slave too large than allowed range(%d >= %d)", slaveDelay,
			gmConf.GCM.AllowedSlaveDelayMax)
	}
	ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("SQL_THread delay [%d] in allowed range[%d]",
		slaveDelay, gmConf.GCM.AllowedSlaveDelayMax))

	if timeDelay >= gmConf.GCM.AllowedTimeDelayMax {
		return fmt.Errorf("IO_Thread delay on slave too large than master(%d >= %d)", timeDelay,
			gmConf.GCM.AllowedTimeDelayMax)
	}
	ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("IO_Thread delay [%d] in allowed range[%d]",
		timeDelay, gmConf.GCM.AllowedTimeDelayMax))

	return nil
}

// GetSlaveCheckSum return value:checksumCnt, checksumFailCnt
func (ins *MySQLCommonSwitch) GetSlaveCheckSum() (int, int, error) {
	var (
		checksumCnt, checksumFailCnt int
	)
	ip := ins.StandBySlave.Ip
	port := ins.StandBySlave.Port
	connParam := fmt.Sprintf("%s:%s@(%s:%d)/%s", ins.Config.DBConf.MySQL.User,
		ins.Config.DBConf.MySQL.Pass, ip, port, constvar.DefaultDatabase)
	db, err := gorm.Open(mysql.Open(connParam), &gorm.Config{
		Logger: log.GormLogger,
	})
	if err != nil {
		log.Logger.Errorf("open mysql failed. ip:%s, port:%d, err:%s", ip, port, err.Error())
		return 0, 0, err
	}
	defer func() {
		con, _ := db.DB()
		if con == nil {
			return
		}
		if err = con.Close(); err != nil {
			log.Logger.Warnf("close connect[%s#%d] failed:%s", ip, port, err.Error())
		}
	}()

	err = db.Raw(constvar.CheckSumSql).Scan(&checksumCnt).Error
	if err != nil {
		log.Logger.Errorf("mysql get checksumCnt failed. ip:%s, port:%d, err:%s", ip, port, err.Error())
		return 0, 0, err
	}

	err = db.Raw(constvar.CheckSumFailSql).Scan(&checksumFailCnt).Error
	if err != nil {
		log.Logger.Errorf("mysql get checksumFailCnt failed. ip:%s, port:%d, err:%s", ip, port, err.Error())
		return 0, 0, err
	}

	return checksumCnt, checksumFailCnt, nil
}

// GetSlaveDelay return value: slaveDelay, timeDelay
func (ins *MySQLCommonSwitch) GetSlaveDelay() (int, int, error) {
	var (
		delayInfo DelayInfo
	)
	ip := ins.StandBySlave.Ip
	port := ins.StandBySlave.Port
	connParam := fmt.Sprintf("%s:%s@(%s:%d)/%s", ins.Config.DBConf.MySQL.User,
		ins.Config.DBConf.MySQL.Pass, ip, port, constvar.DefaultDatabase)
	db, err := gorm.Open(mysql.Open(connParam), &gorm.Config{
		Logger: log.GormLogger,
	})
	if err != nil {
		log.Logger.Errorf("open mysql failed. ip:%s, port:%d, err:%s", ip, port, err.Error())
		return 0, 0, err
	}
	defer func() {
		con, _ := db.DB()
		if con == nil {
			return
		}
		if err = con.Close(); err != nil {
			log.Logger.Warnf("close connect[%s#%d] failed:%s", ip, port, err.Error())
		}
	}()

	slaveStatus := SlaveStatus{}
	err = db.Raw("show slave status").Scan(&slaveStatus).Error
	if err != nil {
		log.Logger.Errorf("show slave status failed. err:%s", err.Error())
		return 0, 0, err
	}
	log.Logger.Debugf("slave status info:%v", slaveStatus)

	err = db.Raw(constvar.CheckDelaySql, slaveStatus.MasterServerId).Scan(&delayInfo).Error
	if err != nil {
		log.Logger.Errorf("mysql get delay info failed. ip:%s, port:%d, err:%s", ip, port, err.Error())
		return 0, 0, err
	}

	return int(delayInfo.SlaveDelay), int(delayInfo.TimeDelay), nil
}

// FindUsefulDatabase found user created databases exclude system database
// return val:
//
//	true: found
//	false: not found
func (ins *MySQLCommonSwitch) FindUsefulDatabase() (bool, error) {
	var systemDbs = map[string]bool{
		"mysql":                  true,
		"information_schema":     true,
		"performance_schema":     true,
		"test":                   true,
		constvar.DefaultDatabase: true,
		"sys":                    true,
	}
	ip := ins.StandBySlave.Ip
	port := ins.StandBySlave.Port
	connParam := fmt.Sprintf("%s:%s@(%s:%d)/%s", ins.Config.DBConf.MySQL.User,
		ins.Config.DBConf.MySQL.Pass, ip, port, constvar.DefaultDatabase)
	db, err := gorm.Open(mysql.Open(connParam), &gorm.Config{
		Logger: log.GormLogger,
	})
	if err != nil {
		log.Logger.Errorf("open mysql failed. ip:%s, port:%d, err:%s", ip, port, err.Error())
		return false, err
	}
	var databases []string

	showDatabaseSql := "show databases"
	err = db.Raw(showDatabaseSql).Scan(&databases).Error
	if err != nil {
		log.Logger.Errorf("show databases faled. ip:%s, port:%d, err:%s", ip, port, err.Error())
		return false, err
	}

	for _, database := range databases {
		if _, ok := systemDbs[database]; !ok {
			return true, nil
		}
	}
	log.Logger.Infof("no user-created database found")

	return false, nil
}

// CheckSlaveSlow check whether slave replication delay
func (ins *MySQLCommonSwitch) CheckSlaveSlow() error {
	ip := ins.StandBySlave.Ip
	port := ins.StandBySlave.Port
	user := ins.Config.DBConf.MySQL.User
	pass := ins.Config.DBConf.MySQL.Pass
	allowSlowBytes := ins.Config.GMConf.GCM.ExecSlowKBytes
	connParam := fmt.Sprintf("%s:%s@(%s:%d)/%s", user, pass, ip, port, "infodba_schema")
	db, err := gorm.Open(mysql.Open(connParam), &gorm.Config{
		Logger: log.GormLogger,
	})
	if err != nil {
		log.Logger.Errorf("open mysql failed. ip:%s, port:%d, err:%s", ip, port, err.Error())
		return err
	}
	defer func() {
		con, _ := db.DB()
		if err = con.Close(); err != nil {
			log.Logger.Warnf("close connect[%s#%d] failed:%s", ip, port, err.Error())
		}
	}()

	var maxBinlogSize MySQLVariableInfo
	err = db.Raw("show variables like 'max_binlog_size'").Scan(&maxBinlogSize).Error
	if err != nil {
		log.Logger.Errorf("get mas_binlog_size failed. ip:%s, port:%d, err:%s", ip, port, err.Error())
		return err
	}

	binlogSizeMByte := maxBinlogSize.VariableValue / (1024 * 1024)
	log.Logger.Infof("the slave max_binlog_size value is %d M!", binlogSizeMByte)

	status, err := GetSlaveStatus(db)
	if err != nil {
		log.Logger.Errorf("get slave status failed. err:%s", err.Error())
		return err
	}
	log.Logger.Infof("Relay_Master_Log_File_Index:%d, Exec_Master_Log_Pos:%d",
		status.RelayMasterLogFileIndex, status.ReadMasterLogPos)

	execSlowKBytes := binlogSizeMByte*1024*uint64(status.MasterLogFileIndex-status.RelayMasterLogFileIndex) -
		status.ExecMasterLogPos/1024 + status.ReadMasterLogPos/1024

	loop := 10
	if execSlowKBytes > uint64(allowSlowBytes) {
		ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("slave delay kbytes[%d] large than allowed[%d],"+
			"try to loop wait", execSlowKBytes, allowSlowBytes))
		var i int
		for i = 0; i < loop; i++ {
			time.Sleep(3 * time.Second)
			tmpStatus, err := GetSlaveStatus(db)
			if err != nil {
				log.Logger.Errorf("get slave status failed. err:%s", err.Error())
				return err
			}
			execSlowKBytes = binlogSizeMByte*1024*
				uint64(tmpStatus.MasterLogFileIndex-tmpStatus.RelayMasterLogFileIndex) -
				tmpStatus.ExecMasterLogPos/1024 + tmpStatus.ReadMasterLogPos/1024
			if execSlowKBytes <= uint64(allowSlowBytes) {
				// todo: for GTID
				break
			}
			log.Logger.Warnf("loop[%d],slave slower too much: Execute %dK,default value is:%d",
				i, execSlowKBytes, allowSlowBytes)
		}
		if i == loop {
			return fmt.Errorf("after loop wait, slave still slower too much: Execute %dK, default value is:%d",
				execSlowKBytes, allowSlowBytes)
		}
	}
	ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("check slave[%s:%d] status success", ip, port))
	return nil
}

// GetSlaveStatus get slave status info
func GetSlaveStatus(db *gorm.DB) (BinlogStatus, error) {
	slaveStatus := SlaveStatus{}
	ret := BinlogStatus{}
	err := db.Raw("show slave status").Scan(&slaveStatus).Error
	if err != nil {
		log.Logger.Errorf("show slave status failed. err:%s", err.Error())
		return BinlogStatus{}, err
	}

	if slaveStatus.SlaveIoRunning != "Yes" || slaveStatus.SlaveSqlRunning != "Yes" {
		return BinlogStatus{}, fmt.Errorf("slave's SQL_thread[%s], IO_Thread[%s] is abnormal",
			slaveStatus.SlaveSqlRunning, slaveStatus.SlaveIoRunning)
	}

	if !strings.Contains(slaveStatus.MasterLogFile, ".") {
		log.Logger.Errorf("can't find master log file. master_log_file:%s",
			slaveStatus.MasterLogFile)
		return BinlogStatus{}, fmt.Errorf("can't find master log file")
	}

	ret.MasterLogFileIndex, err = strconv.Atoi(strings.Split(slaveStatus.MasterLogFile, ".")[1])
	if err != nil {
		log.Logger.Errorf("split master log file failed. err:%s, master_log_file:%s", err.Error(),
			slaveStatus.MasterLogFile)
	}

	if !strings.Contains(slaveStatus.RelayMasterLogFile, ".") {
		log.Logger.Errorf("can't find master log file. relay_master_log_file:%s",
			slaveStatus.RelayMasterLogFile)
		return BinlogStatus{}, fmt.Errorf("can't find master log file")
	}

	ret.RelayMasterLogFileIndex, err = strconv.Atoi(strings.Split(slaveStatus.RelayMasterLogFile, ".")[1])
	if err != nil {
		log.Logger.Errorf("split master log file failed. relay_master_log_file:%s",
			slaveStatus.RelayMasterLogFile)
		return BinlogStatus{}, err
	}

	ret.ReadMasterLogPos = slaveStatus.ReadMasterLogPos
	ret.ExecMasterLogPos = slaveStatus.ExecMasterLogPos
	// ret.RetrievedGtidSet = slaveStatus.RetrievedGtidSet
	// ret.ExecutedGtidSet = slaveStatus.ExecutedGtidSet
	// ret.MasterUuid = slaveStatus.MasterUuid
	return ret, nil
}

// MasterStatus master status struct
type MasterStatus struct {
	File            string
	Position        uint64
	BinlogDoDB      string
	BinlogIgnoreDB  string
	ExecutedGtidSet string
}

// ResetSlave do reset slave
func (ins *MySQLCommonSwitch) ResetSlave() (string, uint64, error) {
	slaveIp := ins.StandBySlave.Ip
	slavePort := ins.StandBySlave.Port
	user := ins.Config.DBConf.MySQL.User
	pass := ins.Config.DBConf.MySQL.Pass
	log.Logger.Infof("gonna RESET SLAVE on %s:%d", slaveIp, slavePort)

	connParam := fmt.Sprintf("%s:%s@(%s:%d)/%s", user, pass, slaveIp, slavePort, "infodba_schema")
	db, err := gorm.Open(mysql.Open(connParam), &gorm.Config{
		Logger: log.GormLogger,
	})
	if err != nil {
		log.Logger.Errorf("open mysql failed. ip:%s, port:%d, err:%s", slaveIp, slavePort, err.Error())
		return "", 0, err
	}

	stopSql := "stop slave"
	masterSql := "show master status"
	resetSql := "reset slave /*!50516 all */"

	err = db.Exec(stopSql).Error
	if err != nil {
		return "", 0, fmt.Errorf("stop slave failed. err:%s", err.Error())
	}
	log.Logger.Infof("execute %s success", stopSql)

	var masterStatus MasterStatus
	err = db.Raw(masterSql).Scan(&masterStatus).Error
	if err != nil {
		return "", 0, fmt.Errorf("show master status failed, err:%s", err.Error())
	}
	ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("get new master binlog info succeed. binlog_file:%s, "+
		"binlog_pos:%d", masterStatus.File, masterStatus.Position))

	err = db.Exec(resetSql).Error
	if err != nil {
		return "", 0, fmt.Errorf("reset slave failed. err:%s", err.Error())
	}
	log.Logger.Infof("executed %s on %s:%d successd", resetSql, slaveIp, slavePort)

	return masterStatus.File, masterStatus.Position, nil
}

// UpdateMetaInfo swap master, slave 's meta info in cmdb
func (ins *MySQLCommonSwitch) UpdateMetaInfo() error {
	return nil
}

// SetRoutes set switch instance's route info
// 1.set primary tdbctl(here only set the raw primary, even if it already broken-down)
// 2.set all nodes' route info
// 1). use cluster name fetch all spider-master instance, include itself(broken-down)
// 2). connect any-other tdbctl, execute 'TDBCTL GET PRIMARY' to get primary node
// TDBCTL GET PRIMARY sql return result example:
// +-------------+------------+------+----------------+
// | SERVER_NAME | HOST       | PORT | IS_THIS_SERVER |
// +-------------+------------+------+----------------+
// | TDBCTL0     | 127.0.0.1  | 3306 |              1 |
// +-------------+------------+------+----------------+
// NB: gorm's func may abnormal for some tdbctl command(its bug?), so all db operator should
// use sql.DB at present
func (ins *SpiderCommonSwitch) SetRoutes() error {
	foundPrimary := false
	dbConf := ins.Config.DBConf.MySQL
	cmdbClient := client.NewCmDBClient(&ins.Config.DBConf.CMDB, ins.Config.GetCloudId())
	rawData, err := cmdbClient.GetDBInstanceInfoByCluster(ins.ClusterName)
	if err != nil {
		return fmt.Errorf("get all cluster instance info failed:%s", err.Error())
	}

	for _, v := range rawData {
		cmdbIns := dbutil.DBInstanceInfoDetail{}
		rawIns, jsonErr := json.Marshal(v)
		if jsonErr != nil {
			return fmt.Errorf("get tdbctl primary failed:%s", jsonErr.Error())
		}
		if jsonErr = json.Unmarshal(rawIns, &cmdbIns); jsonErr != nil {
			return fmt.Errorf("get tdbctl primary failed:%s", jsonErr.Error())
		}
		//only spider-master had tdbctl node, should connect use admin port
		if !foundPrimary && cmdbIns.SpiderRole == constvar.TenDBClusterProxyMaster &&
			cmdbIns.Status != constvar.UNAVAILABLE {
			primaryTdbctl := TdbctlInfo{}
			//skip connect itself(already broken-down)
			if cmdbIns.IP == ins.Ip && cmdbIns.Port == ins.Port {
				continue
			}

			//try to connect a tdbctl node, and get primary tdbctl
			log.Logger.Debugf("try to connect tdbctl and get primary:%s#%d", cmdbIns.IP, cmdbIns.AdminPort)
			connParam := fmt.Sprintf("%s:%s@(%s:%d)/%s",
				dbConf.User, dbConf.Pass, cmdbIns.IP, cmdbIns.AdminPort, constvar.DefaultDatabase)
			if currentConn, connErr := dbutil.ConnMySQL(connParam); connErr != nil {
				log.Logger.Warnf("connect tdbctl[%s#%d] failed:%s, retry others",
					cmdbIns.IP, cmdbIns.AdminPort, connErr.Error())
				//connect failed, try another
				continue
			} else {
				//get primary tdbctl from connected tdbctl
				//TODO: gorm bug? must use sql.DB instead here
				if err = currentConn.QueryRow(GetPrimarySQL).Scan(&primaryTdbctl.ServerName,
					&primaryTdbctl.Host, &primaryTdbctl.Port, &primaryTdbctl.CurrentServer); err != nil {
					log.Logger.Warnf("execute [%s] failed:%s", GetPrimarySQL, err.Error())
					_ = currentConn.Close()
					ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("get primary tdbctl failed:%s,"+
						"try others", err.Error()))
					continue
				}

				//if primary tdbctl break-down: try to get all route from any-other(current connected) tdbctl;
				//if non-primary tdbctl broken-down:
				// 1)current connected tdbctl is primary, get all route directly
				// 2)otherwise, get all route from real primary tdbctl.
				ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("get primary tdbctl success, info:%s#%d",
					primaryTdbctl.Host, primaryTdbctl.Port))

				foundPrimary = true
				primaryConn := currentConn
				ins.PrimaryTdbctl = primaryTdbctl
				//check whether breakdown node is primary tdbctl
				if primaryTdbctl.Host == ins.Ip && primaryTdbctl.Port == cmdbIns.AdminPort {
					ins.ReportLogs(constvar.InfoResult, "primary tdbctl broken-down")
					//current break-down node is primary tdbctl
					ins.PrimaryTdbctl.CurrentServer = 1
					ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("get route from secondary tdbctl[%s#%d]",
						cmdbIns.IP, cmdbIns.AdminPort))
				} else {
					ins.ReportLogs(constvar.InfoResult, "non-primary tdbctl broken-down")
					//current break-down node is not primary
					ins.PrimaryTdbctl.CurrentServer = 0
					if primaryTdbctl.CurrentServer != 1 {
						//current connected tdbctl not primary tdbctl, close and connect to real primary
						_ = currentConn.Close()
						ins.ReportLogs(constvar.InfoResult, "try to connect real primary tdbctl and get route")
						connParam = fmt.Sprintf("%s:%s@(%s:%d)/%s",
							dbConf.User, dbConf.Pass, ins.PrimaryTdbctl.Host,
							ins.PrimaryTdbctl.Port, constvar.DefaultDatabase)
						if primaryConn, err = dbutil.ConnMySQL(connParam); err != nil {
							return fmt.Errorf("connect primary tdbctl[%s#%d] failed:%s",
								ins.PrimaryTdbctl.Host, ins.PrimaryTdbctl.Port, err.Error())
						}
					}
				}

				if ins.RouteTable, err = ins.QueryRouteInfo(primaryConn); err != nil {
					_ = primaryConn.Close()
					return fmt.Errorf("get all route info failed:%s", err.Error())
				}
				_ = primaryConn.Close()
				break
			}
		}
	}

	if !foundPrimary {
		return fmt.Errorf("no appropriate primary tdbctl found")
	}

	ins.ReportLogs(constvar.InfoResult, "found route, primary tdbctl success")

	return nil
}

// GetRouteInfo get route info from route table by ip,port
func (ins *SpiderCommonSwitch) GetRouteInfo(host string, port int) *RouteInfo {
	for _, node := range ins.RouteTable {
		if node.Host == host && node.Port == port {
			return &node
		}
	}
	return nil
}

// QueryRouteInfo query route info from mysql.servers
func (ins *SpiderCommonSwitch) QueryRouteInfo(db *sql.DB) ([]RouteInfo, error) {
	routeTable := make([]RouteInfo, 0)
	rows, err := db.Query(GetRouteSQL)
	if err != nil {
		return nil, err
	}
	for rows.Next() {
		route := RouteInfo{}
		if err := rows.Scan(&route.ServerName, &route.Host, &route.UserName,
			&route.Password, &route.Port, &route.Wrapper); err != nil {
			return nil, fmt.Errorf("query route info failed:%s", err.Error())
		}
		routeTable = append(routeTable, route)
	}
	if len(routeTable) == 0 {
		return nil, fmt.Errorf("no route info found")
	}
	ins.ReportLogs(constvar.InfoResult, "query route table success")

	return routeTable, nil
}

func (ins *SpiderCommonSwitch) ConnectPrimaryTdbctl() (*sql.DB, error) {
	mysqlConf := ins.Config.DBConf.MySQL
	connParam := fmt.Sprintf("%s:%s@(%s:%d)/%s",
		mysqlConf.User, mysqlConf.Pass, ins.PrimaryTdbctl.Host, ins.PrimaryTdbctl.Port, constvar.DefaultDatabase)
	primaryConn, err := dbutil.ConnMySQL(connParam)
	if err != nil {
		return nil, fmt.Errorf("connect primary tdbctl failed:%s", err.Error())
	}
	return primaryConn, nil
}

// RemoveNodeFromRoute connect primary node and remove input node's route
func (ins *SpiderCommonSwitch) RemoveNodeFromRoute(primaryConn *sql.DB, host string, port int) error {
	routeInfo := ins.GetRouteInfo(host, port)
	dropSQL := fmt.Sprintf(DropNodeFormat, routeInfo.ServerName)
	if result, err := primaryConn.Exec(dropSQL); err != nil {
		return fmt.Errorf("execute[%s] failed:%s", dropSQL, err.Error())
	} else {
		if rowCnt, _ := result.RowsAffected(); rowCnt != 1 {
			//TODO: current tdbctl server's rowsAffected incorrect. Next version, should return error instead
			log.Logger.Warnf("execute[%s] failed, rowsAffected num :%d", dropSQL, rowCnt)
		}
	}

	return nil
}
