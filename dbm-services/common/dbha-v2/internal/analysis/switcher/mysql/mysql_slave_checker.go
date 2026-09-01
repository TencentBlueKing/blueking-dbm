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
	"database/sql"
	"fmt"
	"strconv"
	"strings"
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/internal/analysis/dbm"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchcore"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchlogger"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"
)

// Slowness / heartbeat / checksum limits for slave pre-switch checks fall back inside MySQLSlaveChecker getters.
const (
	defaultAllowedSlowBytes              = 0
	defaultAllowedMaxChecksumFailCnt     = 2
	defaultAllowedMaxHeartbeatDelay      = 600
	defaultAllowedMaxSecondsBehindMaster = 600
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

	// CheckDelaySQL: probe-owned repl heartbeat delay.
	// Kept but unused: the switch no longer reads dbha_repl_heartbeat, see GetSlaveTimeDelay.
	CheckDelaySQL = "SELECT GREATEST(CAST(TIMESTAMPDIFF(SECOND, update_time, SYSDATE()) AS SIGNED), 0) " +
		"AS heartbeat_delay " +
		"FROM `" + hamodel.ProbeMysqlDbName + "`.`" + hamodel.DbhaReplHeartbeatTableName + "` " +
		"WHERE host = ? AND port = ? AND server_id = ? ORDER BY update_time DESC LIMIT 1"
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
	SecondsBehindMaster     sql.NullInt64
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

// allowedIgnoreCheckSum returns workflow.switchflow.slaveAllowedIgnoreCheckSum.
func (*MySQLSlaveChecker) allowedIgnoreCheckSum() bool {
	return config.Cfg.Workflow.SwitchFlow.AllowedIgnoreCheckSum
}

// allowedIgnoreSlaveDelay returns workflow.switchflow.slaveAllowedIgnoreSlaveDelay.
func (*MySQLSlaveChecker) allowedIgnoreSlaveDelay() bool {
	return config.Cfg.Workflow.SwitchFlow.AllowedIgnoreSlaveDelay
}

// allowedSlowBytes returns workflow.switchflow.slaveAllowedSlowBytes, or default when negative.
func (*MySQLSlaveChecker) allowedSlowBytes() int {
	v := config.Cfg.Workflow.SwitchFlow.AllowedSlowBytes
	if v < 0 {
		return defaultAllowedSlowBytes
	}
	return v
}

// allowedMaxChecksumFailCnt returns workflow.switchflow.slaveAllowedMaxChecksumFailCnt, or default when negative.
func (*MySQLSlaveChecker) allowedMaxChecksumFailCnt() int {
	v := config.Cfg.Workflow.SwitchFlow.AllowedMaxChecksumFailCnt
	if v < 0 {
		return defaultAllowedMaxChecksumFailCnt
	}
	return v
}

// allowedMaxHeartbeatDelay returns workflow.switchflow.slaveAllowedMaxHeartbeatDelay, or default when not positive.
// Kept but unused, see GetSlaveTimeDelay.
func (*MySQLSlaveChecker) allowedMaxHeartbeatDelay() int {
	v := config.Cfg.Workflow.SwitchFlow.AllowedMaxHeartbeatDelay
	if v <= 0 {
		return defaultAllowedMaxHeartbeatDelay
	}
	return v
}

// allowedMaxSecondsBehindMaster returns workflow.switchflow.slaveAllowedMaxSecondsBehindMaster,
// or default when not positive.
func (*MySQLSlaveChecker) allowedMaxSecondsBehindMaster() int {
	v := config.Cfg.Workflow.SwitchFlow.AllowedMaxSecondsBehindMaster
	if v <= 0 {
		return defaultAllowedMaxSecondsBehindMaster
	}
	return v
}

// Check is the entry function to verify if slave node satisfies switching conditions
func (checker *MySQLSlaveChecker) Check() error {
	checker.ReportLogf(switchlogger.SwitchInfo, "Start to check slave(%s:%d) status for current mysql master",
		checker.SlaveIp, checker.SlavePort)

	ignoreCheckSum := checker.allowedIgnoreCheckSum()
	ignoreSlaveDelay := checker.allowedIgnoreSlaveDelay()
	ip := checker.SlaveIp
	port := checker.SlavePort

	slaveDB, err := hamysql.NewGormDB(
		hamysql.OptionProto(DefaultMySQLProtocol),
		hamysql.OptionIP(ip),
		hamysql.OptionPort(port),
		hamysql.OptionUser(config.Cfg.Database.Mysql.User),
		hamysql.OptionPassword(config.Cfg.Database.Mysql.Password),
		hamysql.OptionTimeout(switchcore.DbConnectTimeout()),
	)

	if err != nil {
		return gerrors.Newf(gerrors.Failure,
			"failed to connect to mysql slave(%s:%d) when checking slave status: %s", ip, port, err.Error())
	}

	defer slaveDB.Close()

	// Wait for the slave to finish the remaining SQLs in its relay log.
	slaveStatus, err := checker.WaitReplPosDelay(slaveDB, ignoreSlaveDelay)
	if err != nil {
		return err
	}

	// Check the checksum status of the slave.
	if !ignoreCheckSum {
		if err := checker.runSlaveCheckSum(slaveDB, ip, port); err != nil {
			return err
		}
	}

	// Check the replication delay of the slave.
	if !ignoreSlaveDelay {
		if err := checker.runReplTimeDelay(slaveDB, ip, port, slaveStatus); err != nil {
			return err
		}
	}

	return nil
}

// runReplTimeDelay checks Seconds_Behind_Master, reusing slaveStatus when present.
// Heartbeat delay check (dbha_repl_heartbeat / GetSlaveTimeDelay) was removed.
// Lag is now judged by Seconds_Behind_Master.
func (checker *MySQLSlaveChecker) runReplTimeDelay(
	slaveDB *hamysql.GormDB, ip string, port int, slaveStatus *SlaveStatusPartialInfo,
) error {
	var behind sql.NullInt64
	if slaveStatus != nil {
		behind = slaveStatus.SecondsBehindMaster
	} else {
		var err error
		behind, err = checker.GetSecondsBehindMaster(slaveDB)
		if err != nil {
			return err
		}
	}
	return checker.CheckSecondsBehindMaster(ip, port, behind)
}

// GetSecondsBehindMaster reads Seconds_Behind_Master from SlaveStatusPartialInfo.
// Any failure to obtain the slave status is returned to the caller, which includes
// Slave_SQL_Running not being Yes. NULL is a valid result (Valid=false).
func (checker *MySQLSlaveChecker) GetSecondsBehindMaster(slaveDB *hamysql.GormDB) (sql.NullInt64, error) {
	info, err := GetSlaveStatusPartialInfo(slaveDB, checker.ReportLogf)
	if err != nil {
		return sql.NullInt64{}, err
	}
	return info.SecondsBehindMaster, nil
}

// CheckSecondsBehindMaster checks a fetched Seconds_Behind_Master value.
// NULL is not a usable lag signal and is treated as pass.
// Only a non-NULL integer at or above the allowed max fails the check.
func (checker *MySQLSlaveChecker) CheckSecondsBehindMaster(ip string, port int, behind sql.NullInt64) error {
	if !behind.Valid {
		// NULL (IO stopped / repl not connected) has no reference value; treat as pass.
		checker.ReportLogf(switchlogger.SwitchInfo,
			"seconds_behind_master is NULL, skip the check, slave: %s:%d", ip, port)
		return nil
	}

	behindSec := int(behind.Int64)
	maxBehindSec := checker.allowedMaxSecondsBehindMaster()
	if behindSec >= maxBehindSec {
		return gerrors.Newf(gerrors.NodeAbnormal, "seconds_behind_master is larger than allowed, "+
			"slave: %s:%d, seconds_behind_master: %d, allowed: %d", ip, port, behindSec, maxBehindSec)
	}

	checker.ReportLogf(switchlogger.SwitchInfo, "seconds_behind_master is in allowed range, "+
		"slave: %s:%d, seconds_behind_master: %d, allowed: %d", ip, port, behindSec, maxBehindSec)
	return nil
}

// WaitReplPosDelay checks if slave replication position is delayed.
// It returns the most recent slave status it read, so the caller can reuse it
// instead of issuing another SHOW SLAVE STATUS.
func (checker *MySQLSlaveChecker) WaitReplPosDelay(
	slaveDB *hamysql.GormDB, ignoreDelay bool,
) (latest *SlaveStatusPartialInfo, err error) {
	if slaveDB == nil {
		return nil, gerrors.New(gerrors.InvalidParameter,
			"get nil mysql connection when checking sql replication delay")
	}

	ip := slaveDB.Host()
	port := slaveDB.Port()
	allowSlowKBytes := checker.allowedSlowBytes()

	maxBinlogSize, err := queryMaxBinlogSize(slaveDB)
	if err != nil {
		return nil, err
	}
	checker.ReportLogf(switchlogger.SwitchInfo, "the max_binlog_size of slave node(%s:%d) is %dMB",
		ip, port, maxBinlogSize/1024/1024)

	slaveStatus, err := GetSlaveStatusPartialInfo(slaveDB, checker.ReportLogf)
	if err != nil {
		return nil, gerrors.Newf(gerrors.Failure,
			"failed to get slave status of slave node(%s:%d): %s", ip, port, err.Error())
	}
	latest = slaveStatus
	checker.ReportLogf(switchlogger.SwitchInfo, "successfully get slave status of slave node(%s:%d), "+
		"Relay_Master_Log_File_Index: %d, Exec_Master_Log_Pos: %d",
		ip, port, slaveStatus.RelayMasterLogFileIndex, slaveStatus.ReadMasterLogPos)

	if slaveStatus.MasterHost != checker.MasterIp || slaveStatus.MasterPort != checker.MasterPort {
		errMsg := fmt.Sprintf("the slave's master info(%s:%d) and the current master(%s:%d) are not equal",
			slaveStatus.MasterHost, slaveStatus.MasterPort, checker.MasterIp, checker.MasterPort)
		return nil, gerrors.New(gerrors.NodeAbnormal, errMsg)
	}

	if ignoreDelay {
		checker.ReportLogf(switchlogger.SwitchInfo,
			"replication delay check was specified to skip for slave node(%s:%d)", ip, port)
		return latest, nil
	}

	realSlowKBytes := CalSlowBytes(slaveStatus, maxBinlogSize)
	if realSlowKBytes <= uint64(allowSlowKBytes) {
		checker.ReportLogf(switchlogger.SwitchInfo, "the slave(%s:%d) was delayed for %dKB, which is less than allowed(%dKB)",
			ip, port, realSlowKBytes, allowSlowKBytes)
		return latest, nil
	}

	checker.ReportLogf(switchlogger.SwitchInfo, "the slave(%s:%d) was delayed for %dKB, "+
		"which is larger than allowed(%dKB), try to wait in a loop", ip, port, realSlowKBytes, allowSlowKBytes)

	var i, loop int = 0, 10
	for i = 0; i < loop; i++ {
		time.Sleep(3 * time.Second)

		tmpSlaveStatus, err := GetSlaveStatusPartialInfo(slaveDB, checker.ReportLogf)
		if err != nil {
			return nil, gerrors.Newf(gerrors.Failure, "failed to query slave status from slave(%s:%d): %s",
				ip, port, err.Error())
		}
		latest = tmpSlaveStatus

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
		return nil, gerrors.Newf(gerrors.NodeAbnormal,
			"after waiting for %d loops, the slave(%s:%d) was still delayed too much", loop, ip, port)
	}

	checker.ReportLogf(switchlogger.SwitchInfo, "sql replication delay check was passed for slave node(%s:%d)", ip, port)
	return latest, nil
}

// queryMaxBinlogSize queries the max_binlog_size from the slave database
func queryMaxBinlogSize(slaveDB *hamysql.GormDB) (uint64, error) {
	ip := slaveDB.Host()
	port := slaveDB.Port()
	var varQueryRes MySQLVariableResult
	gdb, cancel := switchcore.GormWithExecSqlTimeout(slaveDB)
	defer cancel()

	err := gdb.Raw("show variables like 'max_binlog_size'").Scan(&varQueryRes).Error
	if err != nil {
		return 0, gerrors.Newf(gerrors.Failure, "failed to query max_binlog_size from (%s:%d): %s", ip, port, err.Error())
	}

	maxBinlogSize, parseErr := strconv.ParseUint(varQueryRes.Value, 10, 64)
	if parseErr != nil {
		return 0, gerrors.Newf(gerrors.Failure, "failed to parse max_binlog_size('%s') from (%s:%d): %s",
			varQueryRes.Value, ip, port, parseErr.Error())
	}
	return maxBinlogSize, nil
}

// GetSlaveTimeDelay retrieves slave replication heartbeat delay from dbha_repl_heartbeat.
// Kept but unused: the probe no longer runs the repldelay harvest group, because ROW writes
// to dbha_repl_heartbeat can break replication on master-slave switchover. Check() judges
// the lag by Seconds_Behind_Master instead.
func (checker *MySQLSlaveChecker) GetSlaveTimeDelay(slaveDB *hamysql.GormDB) (int, error) {
	if slaveDB == nil {
		return 0, gerrors.New(gerrors.InvalidParameter, "get nil mysql connection when getting slave time delay")
	}

	ip := slaveDB.Host()
	port := slaveDB.Port()

	slaveStatus := SlaveStatusInfo{}
	gdb1, cancel1 := switchcore.GormWithExecSqlTimeout(slaveDB)
	defer cancel1()

	err := gdb1.Raw("show slave status").Scan(&slaveStatus).Error
	if err != nil {
		return 0, gerrors.Newf(gerrors.Failure,
			"failed to query slave status, slave: %s:%d, errmsg: %s", ip, port, err.Error())
	}
	checker.ReportLogf(switchlogger.SwitchInfo,
		"successfully get master identity, slave: %s:%d, master: %s:%d, master_server_id: %d",
		ip, port, slaveStatus.MasterHost, slaveStatus.MasterPort, slaveStatus.MasterServerID)

	// fallbackDelaySec is reported when repl is broken/heartbeat missing, so a broken slave isn't seen healthy.
	const fallbackDelaySec = 365 * 24 * 60 * 60

	// Master_Server_Id == 0 means replication never connected (e.g. RESET SLAVE/CHANGE MASTER):
	// no heartbeat row can match, so report the fallback delay instead of 0.
	if slaveStatus.MasterServerID == 0 {
		checker.ReportLogf(switchlogger.SwitchInfo,
			"replication not connected, use fallback delay, slave: %s:%d, master_server_id: 0", ip, port)
		return fallbackDelaySec, nil
	}

	delayInfo := SlaveTimeDelayInfo{}
	gdb2, cancel2 := switchcore.GormWithExecSqlTimeout(slaveDB)
	defer cancel2()

	tx := gdb2.Raw(CheckDelaySQL, slaveStatus.MasterHost, slaveStatus.MasterPort, slaveStatus.MasterServerID).
		Scan(&delayInfo)
	if tx.Error != nil {
		return 0, gerrors.Newf(gerrors.Failure,
			"failed to query slave time delay, slave: %s:%d, master: %s:%d, server_id: %d, errmsg: %s",
			ip, port, slaveStatus.MasterHost, slaveStatus.MasterPort, slaveStatus.MasterServerID, tx.Error.Error())
	}
	if tx.RowsAffected == 0 {
		// No matching heartbeat row (stale/ownership changed): use fallback, never report 0 for broken repl.
		checker.ReportLogf(switchlogger.SwitchInfo,
			"no repl heartbeat row, use fallback delay, slave: %s:%d, master: %s:%d, server_id: %d",
			ip, port, slaveStatus.MasterHost, slaveStatus.MasterPort, slaveStatus.MasterServerID)
		return fallbackDelaySec, nil
	}

	heartbeatDelay := int(delayInfo.SlaveHeartbeatDelay)
	checker.ReportLogf(switchlogger.SwitchInfo,
		"successfully get slave heartbeat delay, slave: %s:%d, heartbeat_delay: %d",
		ip, port, heartbeatDelay)

	return heartbeatDelay, nil
}

// runSlaveCheckSum runs checksum unless the slave has no user-created database.
// Empty instances are not covered by checksum jobs, so checksumCnt is often 0
// and would fail CheckSlaveCheckSum; skip checksum only, keep the delay check.
func (checker *MySQLSlaveChecker) runSlaveCheckSum(slaveDB *hamysql.GormDB, ip string, port int) error {
	hasBizDbs, err := HasUserCreatedDatabase(slaveDB, checker.ReportLogf)
	if err != nil {
		return err
	}
	if !hasBizDbs {
		checker.ReportLogf(switchlogger.SwitchInfo,
			"no user-created database found on slave, skip checksum check, slave: %s:%d", ip, port)
		return nil
	}

	checksumCnt, checksumFailCnt, err := checker.GetSlaveCheckSum(slaveDB)
	if err != nil {
		return err
	}
	return checker.CheckSlaveCheckSum(ip, port, checksumCnt, checksumFailCnt)
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

	gdb1, cancel1 := switchcore.GormWithExecSqlTimeout(db)
	defer cancel1()

	err := gdb1.Raw(CheckSumSQL).Scan(&checksumCnt).Error
	if err != nil {
		return 0, 0, gerrors.Newf(gerrors.Failure, "failed to get checksumCnt from node(%s:%d): %s",
			ip, port, err.Error())
	}

	gdb2, cancel2 := switchcore.GormWithExecSqlTimeout(db)
	defer cancel2()

	err = gdb2.Raw(CheckSumFailSQL).Scan(&checksumFailCnt).Error
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

	maxChecksum := checker.allowedMaxChecksumFailCnt()
	if checksumFailCnt > maxChecksum {
		return gerrors.Newf(gerrors.NodeAbnormal, "checksum failure count (%d) of db(%s:%d) "+
			"is larger than allowed (%d)", checksumFailCnt, ip, port, maxChecksum)
	}

	checker.ReportLogf(switchlogger.SwitchInfo, "checksum failure count (%d) of db(%s:%d) is in "+
		"allowed range(%d)", checksumFailCnt, ip, port, maxChecksum)

	return nil
}

// CheckSlaveTimeDelay checks the slave heartbeat delay from dbha_repl_heartbeat.
// Kept but unused, see GetSlaveTimeDelay.
func (checker *MySQLSlaveChecker) CheckSlaveTimeDelay(ip string, port int, heartbeatDelay int) error {
	maxHeartbeatDelay := checker.allowedMaxHeartbeatDelay()
	if heartbeatDelay >= maxHeartbeatDelay {
		return gerrors.Newf(gerrors.NodeAbnormal, "slave heartbeat delay is larger than allowed, "+
			"slave: %s:%d, heartbeat_delay: %d, allowed: %d", ip, port, heartbeatDelay, maxHeartbeatDelay)
	}
	checker.ReportLogf(switchlogger.SwitchInfo, "slave heartbeat delay is in allowed range, "+
		"slave: %s:%d, heartbeat_delay: %d, allowed: %d",
		ip, port, heartbeatDelay, maxHeartbeatDelay)

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
	ret.SecondsBehindMaster = slaveStatus.SecondsBehindMaster
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
	gdb, cancel := switchcore.GormWithExecSqlTimeout(db)
	defer cancel()

	err := gdb.Raw("show databases").Scan(&databases).Error
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
