package mysql

import (
	"fmt"
	"strconv"
	"strings"
	"time"

	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/dbutil"
	"dbm-services/common/dbha/ha-module/log"

	"gorm.io/driver/mysql"
	"gorm.io/gorm"
)

// MySQLSwitch defined mysql switch struct
type MySQLSwitch struct {
	dbutil.BaseSwitch
	Role string
	//all slaves fetched from cmdb
	Slave []MySQLSlaveInfo
	//StandbySlave standby slave which master switch to
	StandBySlave             MySQLSlaveInfo
	Proxy                    []dbutil.ProxyInfo
	Entry                    dbutil.BindEntry
	AllowedChecksumMaxOffset int
	AllowedSlaveDelayMax     int
	AllowedTimeDelayMax      int
	ExecSlowKBytes           int
	MySQLUser                string
	MySQLPass                string
	ProxyUser                string
	ProxyPass                string
	Timeout                  int
}

// MySQLSlaveInfo defined slave switch info
type MySQLSlaveInfo struct {
	Ip             string
	Port           int
	IsStandBy      bool
	BinlogFile     string
	BinlogPosition string
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

// GetRole get mysql role type
func (ins *MySQLSwitch) GetRole() string {
	return ins.Role
}

// ShowSwitchInstanceInfo show mysql instance's switch info
func (ins *MySQLSwitch) ShowSwitchInstanceInfo() string {
	str := fmt.Sprintf("<%s#%d IDC:%s Role:%s Status:%s Bzid:%s ClusterType:%s MachineType:%s>",
		ins.Ip, ins.Port, ins.IDC, ins.Role, ins.Status, ins.App, ins.ClusterType,
		ins.MetaType)
	if len(ins.Slave) > 0 {
		str = fmt.Sprintf("%s Switch from MASTER:<%s#%d> to SLAVE:<%s#%d>",
			str, ins.Ip, ins.Port, ins.StandBySlave.Ip, ins.StandBySlave.Port)
	}
	return str
}

// CheckSwitch check slave before switch
func (ins *MySQLSwitch) CheckSwitch() (bool, error) {
	var err error
	if ins.Role == constvar.MySQLSlave {
		ins.ReportLogs(constvar.CheckSwitchInfo, "instance is slave, needn't check")
		return false, nil
	} else if ins.Role == constvar.MySQLRepeater {
		ins.ReportLogs(constvar.CheckSwitchFail, "instance is repeater, dbha not support")
		return false, err
	} else if ins.Role == constvar.MySQLMaster {
		log.Logger.Infof("info:{%s} is master", ins.ShowSwitchInstanceInfo())

		log.Logger.Infof("check slave status. info{%s}", ins.ShowSwitchInstanceInfo())
		if len(ins.Slave) == 0 {
			ins.ReportLogs(constvar.CheckSwitchFail, "no slave info found")
			return false, err
		}
		ins.SetInfo(constvar.SwitchInfoSlaveIp, ins.StandBySlave.Ip)
		ins.SetInfo(constvar.SwitchInfoSlavePort, ins.StandBySlave.Port)
		err = ins.CheckSlaveStatus()
		if err != nil {
			ins.ReportLogs(constvar.CheckSwitchFail, err.Error())
			return false, err
		}

		log.Logger.Infof("start to switch. info{%s}", ins.ShowSwitchInstanceInfo())

		if len(ins.Proxy) == 0 {
			// available instance usual without proxy
			log.Logger.Infof("without proxy! info:{%s}", ins.ShowSwitchInstanceInfo())
			ins.ReportLogs(constvar.CheckSwitchInfo, "without proxy!")
			return false, nil
		}
	} else {
		err = fmt.Errorf("info:{%s} unknown role", ins.ShowSwitchInstanceInfo())
		log.Logger.Error(err)
		ins.ReportLogs(constvar.CheckSwitchFail, "instance unknown role")
		return false, err
	}

	ins.ReportLogs(constvar.CheckSwitchInfo, "mysql check switch ok")
	return true, nil
}

// DoSwitch do switch from master to slave
//  1. refresh all proxy's backend to 1.1.1.1
//  2. reset slave
//  3. get slave's consistent binlog pos
//  4. refresh backend to alive(slave) mysql
func (ins *MySQLSwitch) DoSwitch() error {
	successFlag := true
	ins.ReportLogs(constvar.SwitchInfo, "one phase:update all proxy's backend to 1.1.1.1 first")
	for _, proxyIns := range ins.Proxy {
		ins.ReportLogs(constvar.SwitchInfo, fmt.Sprintf("try to flush proxy:[%s:%d]'s backends to 1.1.1.1",
			proxyIns.Ip, proxyIns.Port))
		err := SwitchProxyBackendAddress(proxyIns.Ip, proxyIns.AdminPort, ins.ProxyUser,
			ins.ProxyPass, "1.1.1.1", 3306)
		if err != nil {
			ins.ReportLogs(constvar.SwitchFail, fmt.Sprintf("flush proxy's backend failed: %s", err.Error()))
			return fmt.Errorf("flush proxy's backend to 1.1.1.1 failed")
		}
		ins.ReportLogs(constvar.SwitchInfo, fmt.Sprintf("flush proxy:[%s:%d]'s backends to 1.1.1.1 success",
			proxyIns.Ip, proxyIns.Port))
	}
	ins.ReportLogs(constvar.SwitchInfo, "all proxy flush backends to 1.1.1.1 success")

	ins.ReportLogs(constvar.SwitchInfo, "try to reset slave")
	binlogFile, binlogPosition, err := ins.ResetSlave()
	if err != nil {
		ins.ReportLogs(constvar.SwitchFail, fmt.Sprintf("reset slave failed:%s", err.Error()))
		return fmt.Errorf("reset slave failed")
	}
	ins.ReportLogs(constvar.SwitchInfo, "reset slave success")
	ins.StandBySlave.BinlogFile = binlogFile
	ins.StandBySlave.BinlogPosition = strconv.Itoa(int(binlogPosition))

	ins.ReportLogs(constvar.SwitchInfo, "two phase: update all proxy's backend to new master")
	for _, proxyIns := range ins.Proxy {
		ins.ReportLogs(constvar.SwitchInfo, fmt.Sprintf("try to flush proxy[%s:%d]'s backend to [%s:%d]",
			proxyIns.Ip, proxyIns.Port, ins.StandBySlave.Ip, ins.StandBySlave.Port))
		err = SwitchProxyBackendAddress(proxyIns.Ip, proxyIns.AdminPort, ins.ProxyUser,
			ins.ProxyPass, ins.StandBySlave.Ip, ins.StandBySlave.Port)
		if err != nil {
			ins.ReportLogs(constvar.SwitchFail, fmt.Sprintf("flush proxy[%s:%d]'s backend to new master failed:%s",
				proxyIns.Ip, proxyIns.Port, err.Error()))
			successFlag = false
		}
		ins.ReportLogs(constvar.SwitchInfo, "flush proxy's backend to new master success")
	}

	if !successFlag {
		return fmt.Errorf("not all proxy's backend switch to new master")
	}

	ins.ReportLogs(constvar.SwitchInfo, "all proxy flush backends to new master success")
	return nil
}

// RollBack do switch rollback
func (ins *MySQLSwitch) RollBack() error {
	return nil
}

// UpdateMetaInfo swap master, slave 's meta info in cmdb
func (ins *MySQLSwitch) UpdateMetaInfo() error {
	// TODO: default 1 master 1 slave, for support multi slave, slave need to add switch_weight
	// for chose a slave to failover.
	err := ins.CmDBClient.SwapMySQLRole(ins.Ip, ins.Port,
		ins.StandBySlave.Ip, ins.StandBySlave.Port)
	if err != nil {
		updateErrLog := fmt.Sprintf("swap mysql role failed. err:%s", err.Error())
		log.Logger.Errorf("%s, info:{%s}", updateErrLog, ins.ShowSwitchInstanceInfo())
		ins.ReportLogs(constvar.UpdateMetaFail, updateErrLog)
		return err
	}
	ins.ReportLogs(constvar.UpdateMetaInfo, "update meta info success")
	return nil
}

// CheckSlaveStatus check whether slave satisfy to switch
func (ins *MySQLSwitch) CheckSlaveStatus() error {
	var (
		checksumCnt, checksumFailCnt, slaveDelay, timeDelay int
	)
	// check_slave_status
	ins.ReportLogs(constvar.CheckSwitchInfo, "try to check slave status info.")
	if err := ins.CheckSlaveSlow(); err != nil {
		return fmt.Errorf("slave delay too much. err:%s", err.Error())
	}

	needCheck, err := ins.FindUsefulDatabase()
	if err != nil {
		log.Logger.Errorf("found user-created database failed. err:%s, info:{%s}", err.Error(),
			ins.ShowSwitchInstanceInfo())
	}

	ins.ReportLogs(constvar.CheckSwitchInfo, "try to check slave checksum info.")
	checksumCnt, checksumFailCnt, err = ins.GetSlaveCheckSum()
	if err != nil {
		log.Logger.Errorf("check slave checksum info failed. err:%s, info:{%s}", err.Error(),
			ins.ShowSwitchInstanceInfo())
		return err
	}
	slaveDelay, timeDelay, err = ins.GetSlaveDelay()
	if err != nil {
		log.Logger.Errorf("check slave checksum info failed. err:%s, info:{%s}", err.Error(),
			ins.ShowSwitchInstanceInfo())
		return err
	}

	ins.ReportLogs(constvar.CheckSwitchInfo, fmt.Sprintf("checksumCnt:%d, checksumFail:%d, slaveDelay:%d, timeDelay:%d",
		checksumCnt, checksumFailCnt, slaveDelay, timeDelay))

	if needCheck {
		if ins.Status == constvar.AVAILABLE {
			checksumCnt = 1
			checksumFailCnt = 0
			slaveDelay = 0
			timeDelay = 0
			ins.ReportLogs(constvar.SwitchInfo, "instance is available, skip check delay and checksum")
		}

		if checksumCnt == 0 {
			return fmt.Errorf("none checksum done on this db")
		}

		log.Logger.Debugf("checksum have done on slave. info:{%s}", ins.ShowSwitchInstanceInfo())

		if checksumFailCnt > ins.AllowedChecksumMaxOffset {
			return fmt.Errorf("too many fail on tables checksum(%d > %d)", checksumFailCnt,
				ins.AllowedChecksumMaxOffset)
		}
		ins.ReportLogs(constvar.CheckSwitchInfo, fmt.Sprintf("checksum failedCnt[%d] in allowed range[%d]",
			checksumFailCnt, ins.AllowedChecksumMaxOffset))

	} else {
		ins.ReportLogs(constvar.CheckSwitchInfo, "none user-created database, skip check checksum")
		return nil
	}

	if slaveDelay >= ins.AllowedSlaveDelayMax {
		return fmt.Errorf("SQL_Thread delay on slave too large than allowed range(%d >= %d)", slaveDelay,
			ins.AllowedSlaveDelayMax)
	}
	ins.ReportLogs(constvar.CheckSwitchInfo, fmt.Sprintf("SQL_THread delay [%d] in allowed range[%d]",
		slaveDelay, ins.AllowedSlaveDelayMax))

	if timeDelay >= ins.AllowedTimeDelayMax {
		return fmt.Errorf("IO_Thread delay on slave too large than master(%d >= %d)", timeDelay,
			ins.AllowedTimeDelayMax)
	}
	ins.ReportLogs(constvar.CheckSwitchInfo, fmt.Sprintf("IO_Thread delay [%d] in allowed range[%d]",
		timeDelay, ins.AllowedTimeDelayMax))

	return nil
}

// GetSlaveCheckSum return value:checksumCnt, checksumFailCnt
func (ins *MySQLSwitch) GetSlaveCheckSum() (int, int, error) {
	var (
		checksumCnt, checksumFailCnt int
	)
	ip := ins.StandBySlave.Ip
	port := ins.StandBySlave.Port
	connParam := fmt.Sprintf("%s:%s@(%s:%d)/%s", ins.MySQLUser, ins.MySQLPass,
		ip, port, constvar.DefaultDatabase)
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
func (ins *MySQLSwitch) GetSlaveDelay() (int, int, error) {
	var (
		delayInfo DelayInfo
	)
	ip := ins.StandBySlave.Ip
	port := ins.StandBySlave.Port
	connParam := fmt.Sprintf("%s:%s@(%s:%d)/%s", ins.MySQLUser, ins.MySQLPass,
		ip, port, constvar.DefaultDatabase)
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
func (ins *MySQLSwitch) FindUsefulDatabase() (bool, error) {
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
	connParam := fmt.Sprintf("%s:%s@(%s:%d)/%s", ins.MySQLUser, ins.MySQLPass,
		ip, port, constvar.DefaultDatabase)
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
func (ins *MySQLSwitch) CheckSlaveSlow() error {
	ip := ins.StandBySlave.Ip
	port := ins.StandBySlave.Port
	connParam := fmt.Sprintf("%s:%s@(%s:%d)/%s", ins.MySQLUser, ins.MySQLPass, ip, port, "infodba_schema")
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
	if execSlowKBytes > uint64(ins.ExecSlowKBytes) {
		ins.ReportLogs(constvar.CheckSwitchInfo, fmt.Sprintf("slave delay kbytes[%d] large than allowed[%d],"+
			"try to loop wait", execSlowKBytes, ins.ExecSlowKBytes))
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
			if execSlowKBytes <= uint64(ins.ExecSlowKBytes) {
				// todo: for GTID
				break
			}
			log.Logger.Warnf("loop[%d],slave slower too much: Execute %dK,default value is:%d",
				i, execSlowKBytes, ins.ExecSlowKBytes)
		}
		if i == loop {
			return fmt.Errorf("after loop wait, slave still slower too much: Execute %dK, default value is:%d",
				execSlowKBytes, ins.ExecSlowKBytes)
		}
	}
	ins.ReportLogs(constvar.CheckSwitchInfo, fmt.Sprintf("check slave[%s:%d] status success", ip, port))
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
func (ins *MySQLSwitch) ResetSlave() (string, uint64, error) {
	slaveIp := ins.StandBySlave.Ip
	slavePort := ins.StandBySlave.Port
	log.Logger.Infof("gonna RESET SLAVE on %s:%d", slaveIp, slavePort)

	connParam := fmt.Sprintf("%s:%s@(%s:%d)/%s", ins.MySQLUser, ins.MySQLPass, slaveIp, slavePort, "infodba_schema")
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
	ins.ReportLogs(constvar.SwitchInfo, fmt.Sprintf("get new master binlog info succeed. binlog_file:%s, "+
		"binlog_pos:%d", masterStatus.File, masterStatus.Position))

	err = db.Exec(resetSql).Error
	if err != nil {
		return "", 0, fmt.Errorf("reset slave failed. err:%s", err.Error())
	}
	log.Logger.Infof("executed %s on %s:%d successd", resetSql, slaveIp, slavePort)

	return masterStatus.File, masterStatus.Position, nil
}
