/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

package mysql

import (
	"fmt"
	"strconv"
	"strings"
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/internal/analysis/dbm"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchlogger"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"
)

// TODO: remove those variables and get them dynamically
const (
	DefaultIgnoreCheckSum     bool = false
	DefaultIgnoreSlaveDelay   bool = false
	AllowSlowBytes            int  = 0
	AllowedMaxChecksumFailCnt int  = 2
	AllowedMaxIODelay         int  = 600
	AllowedMaxHeartbeatDelay  int  = 300
)

// TODO: cancel the reliance on infodba_schema
const (
	// CheckSumSQL checksum number
	CheckSumSQL = "SELECT COUNT(DISTINCT `db`, tbl) AS total_count " +
		"FROM (" +
		"SELECT `db`, tbl " +
		"FROM infodba_schema.checksum " +
		"WHERE ts > DATE_SUB(NOW(), INTERVAL 7 DAY) " +
		"UNION " +
		"SELECT `db`, tbl " +
		"FROM infodba_schema.checksum_history " +
		"WHERE ts > DATE_SUB(NOW(), INTERVAL 7 DAY)" +
		") AS combined_results"

	// CheckSumFailSQL inconsistent checksum number
	CheckSumFailSQL = "SELECT COUNT(DISTINCT `db`, tbl, chunk) AS total_count " +
		"FROM infodba_schema.checksum " +
		"WHERE (this_crc <> master_crc OR this_cnt <> master_cnt) AND ts > DATE_SUB(NOW(), INTERVAL 7 DAY) " +
		"UNION " +
		"SELECT COUNT(DISTINCT `db`, tbl, chunk) AS total_count " +
		"FROM infodba_schema.checksum_history " +
		"WHERE (this_crc <> master_crc OR this_cnt <> master_cnt) AND ts > DATE_SUB(NOW(), INTERVAL 7 DAY)"

	// CheckDelaySQL master and slave's time delay
	CheckDelaySQL = `
		SELECT unix_timestamp(now())-unix_timestamp(master_time) as time_delay, delay_sec as slave_delay 
		FROM infodba_schema.master_slave_heartbeat 
		WHERE master_server_id = ? and slave_server_id != master_server_id
	`
)

var systemDbs = map[string]struct{}{
	"mysql":              {},
	"information_schema": {},
	"performance_schema": {},
	"test":               {},
	"infodba_schema":     {},
	"sys":                {},
}

// SlaveStatusPartialInfo contains partial slave status information for switching
type SlaveStatusPartialInfo struct {
	MasterHost              string
	MasterPort              int
	MasterLogFileIndex      int
	RelayMasterLogFileIndex int
	ReadMasterLogPos        uint64
	ExecMasterLogPos        uint64
}

// MySQLSlaveChecker is a checker for mysql slave status
type MySQLSlaveChecker struct {
	MasterIp     string
	MasterPort   int
	MasterStatus dbm.DbmMetadataStatus
	SlaveIp      string
	SlavePort    int
	SlaveStatus  dbm.DbmMetadataStatus
	ReportLogf   switchlogger.SwitchLogFunc
}

// Check is the entry function to verify if slave node satisfies switching conditions
func (checker *MySQLSlaveChecker) Check() error {
	checker.ReportLogf(switchlogger.SwitchInfo, "Start to check slave(%s:%d) status for current mysql master",
		checker.SlaveIp, checker.SlavePort)

	// TODO: get the following values dynamically
	ignoreCheckSum := DefaultIgnoreCheckSum
	ignoreSlaveDelay := DefaultIgnoreSlaveDelay
	ip := checker.SlaveIp
	port := checker.SlavePort

	slaveDB, err := hamysql.NewGormDB(
		hamysql.OptionProto(DefaultMySQLProtocol),
		hamysql.OptionIP(ip),
		hamysql.OptionPort(port),
		hamysql.OptionUser(config.Cfg.Database.Mysql.User),
		hamysql.OptionPassword(config.Cfg.Database.Mysql.Password),
	)

	if err != nil {
		return gerrors.Newf(gerrors.Failure,
			"failed to connect to mysql slave(%s:%d) when checking slave status: %s", ip, port, err.Error())
	}

	defer slaveDB.Close()

	if err := checker.CheckSqlReplicationDelay(slaveDB, ignoreSlaveDelay); err != nil {
		return err
	}

	var ioDelay, heartbeatDelay int
	if !ignoreSlaveDelay {
		if ioDelay, heartbeatDelay, err = checker.GetSlaveTimeDelay(slaveDB); err != nil {
			return err
		}
	}

	var needCheck bool
	if needCheck, err = HasUserCreatedDatabase(slaveDB, checker.ReportLogf); err != nil {
		return err
	}

	checksumCnt := 1
	checksumFailCnt := 0
	if !ignoreCheckSum {
		if checksumCnt, checksumFailCnt, err = checker.GetSlaveCheckSum(slaveDB); err != nil {
			return err
		}
	}

	if !needCheck {
		checker.ReportLogf(switchlogger.SwitchInfo,
			"no user-created database found on slave db(%s:%d), skip checksum check", ip, port)
		return nil
	}

	if checker.MasterStatus == dbm.Available { // Is this necessary? Actually the delay check is not skipped
		checksumCnt, checksumFailCnt, ioDelay, heartbeatDelay = 1, 0, 0, 0
		checker.ReportLogf(switchlogger.SwitchInfo,
			"the status of mysql master(%s:%d) is %s, skip the check of delay and checksum for its slave(%s:%d)",
			checker.MasterIp, checker.MasterPort, string(checker.MasterStatus), ip, port)
	}

	if err = checker.CheckSlaveCheckSum(ip, port, checksumCnt, checksumFailCnt); err != nil {
		return err
	}

	if err = checker.CheckSlaveTimeDelay(ip, port, ioDelay, heartbeatDelay); err != nil {
		return err
	}

	return nil
}

// CheckSqlReplicationDelay checks if slave replication is delayed
func (checker *MySQLSlaveChecker) CheckSqlReplicationDelay(slaveDB *hamysql.GormDB, ignoreDelay bool) error {
	if slaveDB == nil {
		return gerrors.New(gerrors.InvalidParameter, "get nil mysql connection when checking sql replication delay")
	}

	ip := slaveDB.Host()
	port := slaveDB.Port()
	allowSlowKBytes := AllowSlowBytes

	var varQueryRes MySQLVariableResult
	err := slaveDB.DB().Raw("show variables like 'max_binlog_size'").Scan(&varQueryRes).Error
	if err != nil {
		return gerrors.Newf(gerrors.Failure, "failed to query max_binlog_size from (%s:%d): %s", ip, port, err.Error())
	}

	maxBinlogSize, parseErr := strconv.ParseUint(varQueryRes.Value, 10, 64)
	if parseErr != nil {
		return gerrors.Newf(gerrors.Failure, "failed to parse max_binlog_size('%s') from (%s:%d): %s",
			varQueryRes.Value, ip, port, parseErr.Error())
	}
	checker.ReportLogf(switchlogger.SwitchInfo, "the max_binlog_size of slave node(%s:%d) is %dMB",
		ip, port, maxBinlogSize/1024/1024)

	slaveStatus, err := GetSlaveStatusPartialInfo(slaveDB, checker.ReportLogf)
	if err != nil {
		return gerrors.Newf(gerrors.Failure, "failed to get slave status of slave node(%s:%d): %s", ip, port, err.Error())
	}
	checker.ReportLogf(switchlogger.SwitchInfo, "successfully get slave status of slave node(%s:%d), "+
		"Relay_Master_Log_File_Index: %d, Exec_Master_Log_Pos: %d",
		ip, port, slaveStatus.RelayMasterLogFileIndex, slaveStatus.ReadMasterLogPos)

	if slaveStatus.MasterHost != checker.MasterIp || slaveStatus.MasterPort != checker.MasterPort {
		errMsg := fmt.Sprintf("the slave's master info(%s:%d) and the current master(%s:%d) are not equal",
			slaveStatus.MasterHost, slaveStatus.MasterPort, checker.MasterIp, checker.MasterPort)
		return gerrors.New(gerrors.NodeAbnormal, errMsg)
	}

	if ignoreDelay {
		checker.ReportLogf(switchlogger.SwitchInfo,
			"replication delay check was specified to skip for slave node(%s:%d)", ip, port)
		return nil
	}

	realSlowKBytes := CalSlowBytes(slaveStatus, maxBinlogSize)
	if realSlowKBytes <= uint64(allowSlowKBytes) {
		checker.ReportLogf(switchlogger.SwitchInfo, "the slave(%s:%d) was delayed for %dKB, which is less than allowed(%dKB)",
			ip, port, realSlowKBytes, allowSlowKBytes)
		return nil
	}

	checker.ReportLogf(switchlogger.SwitchInfo, "the slave(%s:%d) was delayed for %dKB, "+
		"which is larger than allowed(%dKB), try to wait in a loop", ip, port, realSlowKBytes, allowSlowKBytes)

	var i, loop int = 0, 10
	for i = 0; i < loop; i++ {
		time.Sleep(3 * time.Second)

		tmpSlaveStatus, err := GetSlaveStatusPartialInfo(slaveDB, checker.ReportLogf)
		if err != nil {
			return gerrors.Newf(gerrors.Failure, "failed to query slave status from slave(%s:%d): %s",
				ip, port, err.Error())
		}

		realSlowKBytes = CalSlowBytes(tmpSlaveStatus, maxBinlogSize)
		if realSlowKBytes <= uint64(allowSlowKBytes) {
			// TODO: for GTID
			break
		}
		checker.ReportLogf(switchlogger.SwitchInfo,
			"Loop (%d): the slave(%s:%d) was delayed for %dKB, which is larger than allowed(%dKB)",
			i, ip, port, realSlowKBytes, allowSlowKBytes)
	}

	if i == loop {
		return gerrors.Newf(gerrors.NodeAbnormal, "after waiting for %d loops, the slave(%s:%d) was still delayed too much",
			loop, ip, port)
	}

	checker.ReportLogf(switchlogger.SwitchInfo, "sql replication delay check was passed for slave node(%s:%d)", ip, port)
	return nil
}

// GetSlaveTimeDelay retrieves slave replication delay information
func (checker *MySQLSlaveChecker) GetSlaveTimeDelay(slaveDB *hamysql.GormDB) (int, int, error) {
	if slaveDB == nil {
		return 0, 0, gerrors.New(gerrors.InvalidParameter, "get nil mysql connection when getting slave time delay")
	}

	ip := slaveDB.Host()
	port := slaveDB.Port()

	slaveStatus := SlaveStatusInfo{}
	err := slaveDB.DB().Raw("show slave status").Scan(&slaveStatus).Error
	if err != nil {
		return 0, 0, gerrors.Newf(gerrors.Failure, "failed to query slave status from node(%s:%d): %s",
			ip, port, err.Error())
	}
	checker.ReportLogf(switchlogger.SwitchInfo, "successfully get Master_Server_Id of slave node(%s:%d): %d",
		ip, port, slaveStatus.MasterServerID)

	delayInfo := SlaveTimeDelayInfo{}
	err = slaveDB.DB().Raw(CheckDelaySQL, slaveStatus.MasterServerID).Scan(&delayInfo).Error
	if err != nil {
		return 0, 0, gerrors.Newf(gerrors.Failure, "failed to query slave time delay info from node(%s:%d): %s",
			ip, port, err.Error())
	}
	checker.ReportLogf(switchlogger.SwitchInfo, "successfully get slave time delay of slave node(%s:%d), "+
		"SlaveIODelay: %f, SlaveHeartbeatDelay: %f", ip, port, delayInfo.SlaveIODelay, delayInfo.SlaveHeartbeatDelay)

	return int(delayInfo.SlaveIODelay), int(delayInfo.SlaveHeartbeatDelay), nil
}

// GetSlaveCheckSum returns checksum count and failure count
func (checker *MySQLSlaveChecker) GetSlaveCheckSum(db *hamysql.GormDB) (int, int, error) {
	if db == nil {
		return 0, 0, gerrors.New(gerrors.InvalidParameter, "get nil mysql connection when getting slave checksum")
	}
	ip := db.Host()
	port := db.Port()

	var (
		checksumCnt, checksumFailCnt int
	)

	err := db.DB().Raw(CheckSumSQL).Scan(&checksumCnt).Error
	if err != nil {
		return 0, 0, gerrors.Newf(gerrors.Failure, "failed to get checksumCnt from node(%s:%d): %s",
			ip, port, err.Error())
	}

	err = db.DB().Raw(CheckSumFailSQL).Scan(&checksumFailCnt).Error
	if err != nil {
		return checksumCnt, 0, gerrors.Newf(gerrors.Failure, "failed to get checksumFailCnt from node(%s:%d): %s",
			ip, port, err.Error())
	}

	checker.ReportLogf(switchlogger.SwitchInfo,
		"successfully get checksumCnt(%d) and checksumFailCnt(%d) of slave node(%s:%d)",
		checksumCnt, checksumFailCnt, ip, port)
	return checksumCnt, checksumFailCnt, nil
}

// CheckSlaveCheckSum checks the slave checksum status
func (checker *MySQLSlaveChecker) CheckSlaveCheckSum(ip string, port int, checksumCnt int, checksumFailCnt int) error {
	if checksumCnt < 1 {
		return gerrors.Newf(gerrors.NodeAbnormal, "no checksum was done on db(%s:%d)", ip, port)
	}

	if checksumFailCnt > AllowedMaxChecksumFailCnt {
		return gerrors.Newf(gerrors.NodeAbnormal, "checksum failure count (%d) of db(%s:%d) "+
			"is larger than allowed (%d)", checksumFailCnt, ip, port, AllowedMaxChecksumFailCnt)
	}

	checker.ReportLogf(switchlogger.SwitchInfo, "checksum failure count (%d) of db(%s:%d) is in "+
		"allowed range(%d)", checksumFailCnt, ip, port, AllowedMaxChecksumFailCnt)

	return nil
}

// CheckSlaveTimeDelay checks the slave time delay
func (checker *MySQLSlaveChecker) CheckSlaveTimeDelay(ip string, port int, ioDelay int, heartbeatDelay int) error {
	if ioDelay >= AllowedMaxIODelay {
		return gerrors.Newf(gerrors.NodeAbnormal, "IO_Thread delay (%d) on slave(%s:%d) is larger than allowed (%d)",
			ioDelay, ip, port, AllowedMaxIODelay)
	}
	checker.ReportLogf(switchlogger.SwitchInfo, "IO_Thread delay (%d) on slave(%s:%d) is in allowed range(%d)",
		ioDelay, ip, port, AllowedMaxIODelay)

	if heartbeatDelay >= AllowedMaxHeartbeatDelay {
		return gerrors.Newf(gerrors.NodeAbnormal, "heartbeat delay (%d) on slave(%s:%d) is larger than allowed (%d)",
			heartbeatDelay, ip, port, AllowedMaxHeartbeatDelay)
	}
	checker.ReportLogf(switchlogger.SwitchInfo, "heartbeat delay (%d) on slave(%s:%d) is in allowed range(%d)",
		heartbeatDelay, ip, port, AllowedMaxHeartbeatDelay)

	return nil
}

// GetSlaveStatusPartialInfo retrieves partial slave status information
func GetSlaveStatusPartialInfo(slaveDB *hamysql.GormDB, reportLogf switchlogger.SwitchLogFunc) (*SlaveStatusPartialInfo, error) {
	if slaveDB == nil {
		return nil, gerrors.New(gerrors.InvalidParameter, "get nil mysql connection when getting slave status")
	}

	ip := slaveDB.Host()
	port := slaveDB.Port()
	slaveStatus, err := DoShowSlaveStatus(slaveDB, reportLogf)
	if err != nil {
		return nil, err
	}

	ret := &SlaveStatusPartialInfo{}

	if !strings.EqualFold(slaveStatus.SlaveSQLRunning, "Yes") {
		errMsg := fmt.Sprintf("slave node(%s:%d) is abnormal(Slave_SQL_Running:'%s')",
			ip, port, slaveStatus.SlaveSQLRunning)
		return nil, gerrors.New(gerrors.NodeAbnormal, errMsg)
	}

	ret.MasterLogFileIndex, err = parseMasterLogFileIndex(slaveStatus.MasterLogFile)
	if err != nil {
		errMsg := fmt.Sprintf("failed to parse the master log file of slave node(%s:%d) (Master_Log_File:'%s'): %s",
			ip, port, slaveStatus.MasterLogFile, err.Error())
		return nil, gerrors.New(gerrors.NodeAbnormal, errMsg)
	}

	ret.RelayMasterLogFileIndex, err = parseMasterLogFileIndex(slaveStatus.RelayMasterLogFile)
	if err != nil {
		errMsg := fmt.Sprintf("failed to parse the relay master log file of slave node(%s:%d) "+
			"(Relay_Master_Log_File:'%s'): %s", ip, port, slaveStatus.RelayMasterLogFile, err.Error())
		return nil, gerrors.New(gerrors.NodeAbnormal, errMsg)
	}

	ret.MasterHost = slaveStatus.MasterHost
	ret.MasterPort = slaveStatus.MasterPort
	ret.ReadMasterLogPos = slaveStatus.ReadMasterLogPos
	ret.ExecMasterLogPos = slaveStatus.ExecMasterLogPos
	return ret, nil
}

// parseMasterLogFileIndex safely parses the numeric index from MasterLogFile format like "binlog.000002"
func parseMasterLogFileIndex(masterLogFile string) (int, error) {
	if !strings.Contains(masterLogFile, ".") {
		return 0, gerrors.Newf(gerrors.Failure, "MasterLogFile does not contain dot separator: %s", masterLogFile)
	}

	parts := strings.Split(masterLogFile, ".")
	if len(parts) < 2 {
		return 0, gerrors.Newf(gerrors.Failure, "MasterLogFile has insufficient parts after splitting: %s", masterLogFile)
	}

	indexStr := parts[1]
	if indexStr == "" {
		return 0, gerrors.Newf(gerrors.Failure, "MasterLogFile index part is empty: %s", masterLogFile)
	}

	index, err := strconv.Atoi(indexStr)
	if err != nil {
		return 0, gerrors.Newf(gerrors.Failure, "failed to parse MasterLogFile index as integer: %s", indexStr)
	}

	return index, nil
}

// CalSlowBytes calculates slow bytes for slave replication
func CalSlowBytes(slaveStatus *SlaveStatusPartialInfo, maxBinlogSize uint64) uint64 {
	return uint64(slaveStatus.MasterLogFileIndex-slaveStatus.RelayMasterLogFileIndex)*(maxBinlogSize/1024) -
		(slaveStatus.ExecMasterLogPos / 1024) + (slaveStatus.ReadMasterLogPos / 1024)
}

// HasUserCreatedDatabase checks if user-created databases exist
func HasUserCreatedDatabase(db *hamysql.GormDB, reportLogf switchlogger.SwitchLogFunc) (bool, error) {
	if db == nil {
		return false, gerrors.New(gerrors.InvalidParameter, "get nil mysql connection when getting user-created database")
	}
	ip := db.Host()
	port := db.Port()

	var databases []string
	err := db.DB().Raw("show databases").Scan(&databases).Error
	if err != nil {
		return false, gerrors.Newf(gerrors.Failure, "failed to query databases from node(%s:%d): %s",
			ip, port, err.Error())
	}

	for _, database := range databases {
		if _, exists := systemDbs[database]; exists {
			continue
		}

		if reportLogf != nil {
			reportLogf(switchlogger.SwitchInfo, "found user-created database on node(%s:%d): %s", ip, port, database)
		}
		return true, nil
	}

	if reportLogf != nil {
		reportLogf(switchlogger.SwitchInfo, "no user-created database found on node(%s:%d)", ip, port)
	}
	return false, nil
}
