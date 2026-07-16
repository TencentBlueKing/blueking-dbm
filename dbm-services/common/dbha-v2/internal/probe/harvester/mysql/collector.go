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
	"context"
	"fmt"
	"time"

	"dbm-services/common/dbha-v2/internal/probe/harvester/base"
	"dbm-services/common/dbha-v2/pkg/converter"
	"dbm-services/common/dbha-v2/pkg/hanet"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

type collector struct {
	base.Collector

	clusterType  haprobe.DbmMetadataClusterType
	machineType  haprobe.DbmMetadataMachineType
	accessLayer  haprobe.DbmMetadataAccessLayerType
	instanceRole haprobe.DbmMetadataInstanceRole
	user         string
	password     string
	timeout      time.Duration
	endpoint     *hanet.Endpoint
	db           *hamysql.GormDB
	isAdminNode  bool
}

// queryCtx returns a context bounded by c.timeout; when c.timeout <= 0 it returns
// context.Background plus a no-op cancel so callers can always defer cancel().
func (c *collector) queryCtx() (context.Context, context.CancelFunc) {
	if c.timeout <= 0 {
		return context.Background(), func() {}
	}
	return context.WithTimeout(context.Background(), c.timeout)
}

func (c *collector) connectionExceptionEvent(err error) *haprobe.DbEvent {
	return &haprobe.DbEvent{
		Name:       haprobe.DbEventNameDetectFailure,
		Reason:     haprobe.DbEventNameReasonConnectionException,
		DbTypeName: haprobe.DbTypeMySql,
		Endpoint:   c.endpoint,
		Message:    hamysql.SanitizeConnectionError(err),
	}
}

func (c *collector) open() (*haprobe.DbEvent, error) {
	opts := []hamysql.Option{
		hamysql.OptionProto(c.endpoint.Proto),
		hamysql.OptionIP(c.endpoint.Host),
		hamysql.OptionPort(c.endpoint.Port),
		hamysql.OptionUser(c.user),
		hamysql.OptionPassword(c.password),
		hamysql.OptionSkipInitializeWithVersion(false),
		hamysql.OptionDisableDatetimePrecision(true),
		hamysql.OptionCharset(""),
	}
	if c.timeout > 0 {
		opts = append(opts, hamysql.OptionTimeout(c.timeout))
	}
	db, err := hamysql.NewGormDB(opts...)

	if err != nil {
		logger.Warn("create mysql db operator failed, errmsg: %s", err)
		return c.connectionExceptionEvent(err), err
	}

	return c.adoptOpenedDB(db)
}

// adoptOpenedDB configures the connection pool and assigns c.db after NewGormDB succeeds.
// On failure it closes db and returns a connection-exception DbEvent; c.db is left unset.
func (c *collector) adoptOpenedDB(db *hamysql.GormDB) (*haprobe.DbEvent, error) {
	sqlDb, err := db.DB().DB()
	if err != nil {
		db.Close()
		return c.connectionExceptionEvent(err), err
	}

	sqlDb.SetMaxIdleConns(1)
	sqlDb.SetMaxOpenConns(3)
	sqlDb.SetConnMaxLifetime(time.Minute * 3)

	c.db = db
	return nil, nil
}

func (c *collector) close() {
	if c.db == nil {
		return
	}
	c.db.Close()
	c.db = nil
}

func (c *collector) isTendbHaProxy() bool {
	return c.accessLayer == haprobe.DbmMetadataAccessLayerTypeProxy &&
		c.machineType == haprobe.DbmMetadataMachineTypeProxy &&
		c.clusterType == haprobe.DbmMetadataClusterTypeTendbha
}

func (c *collector) isTendbClusterProxy() bool {
	return c.accessLayer == haprobe.DbmMetadataAccessLayerTypeProxy &&
		c.machineType == haprobe.DbmMetadataMachineTypeSpider &&
		c.clusterType == haprobe.DbmMetadataClusterTypeTendbCluster
}

func (c *collector) isAdmin() bool {
	return c.isAdminNode
}

func (c *collector) obtainTendbClusterProxyStatus() (*haprobe.MySqlSpiderCtlStatus, error) {
	ctx, cancel := c.queryCtx()
	defer cancel()

	var routes []haprobe.MySqlSpiderCtlRoute
	err := c.db.DB().WithContext(ctx).Raw("select * from mysql.servers").Scan(&routes).Error

	if err != nil {
		logger.Warn("failed to get MySQL spider routes, errmsg: %s", err)
		return nil, err
	}

	status := &haprobe.MySqlSpiderCtlStatus{Routes: routes}

	var nodes []haprobe.MySqlSpiderCtlNode
	err = c.db.DB().WithContext(ctx).Raw("select * from information_schema.TDBCTL_NODES").Scan(&nodes).Error

	if err != nil {
		logger.Warn("failed to get MySQL spider nodes, errmsg: %s", err)
		return status, err
	}

	status.CtlNodes = nodes
	return status, nil
}

func (c *collector) obtainTendbHaProxyStatus() (*haprobe.MySqlProxyStatus, error) {
	ctx, cancel := c.queryCtx()
	defer cancel()

	var backends []haprobe.MySqlProxyBackend
	err := c.db.DB().WithContext(ctx).Raw("select * from backends").Scan(&backends).Error

	if err != nil {
		logger.Warn("failed to get MySQL proxy status, errmsg: %s", err)
		return nil, err
	}

	return &haprobe.MySqlProxyStatus{Backends: backends}, nil
}

// obtainTendbHaProxyServicePortStatus performs a lightweight reachability probe of a TendbHA
// mysql-proxy data (service) port using the probeMysql backend account. A successful SELECT 1
// is the probe verdict so reachability does not depend on gorm initialization options.
// It assumes c.db is already opened by the caller.
func (c *collector) obtainTendbHaProxyServicePortStatus() (*haprobe.MySqlProxyServicePortStatus, error) {
	ctx, cancel := c.queryCtx()
	defer cancel()

	var one int
	if err := c.db.DB().WithContext(ctx).Raw("SELECT 1").Scan(&one).Error; err != nil {
		return &haprobe.MySqlProxyServicePortStatus{
			State:         haprobe.MySqlProxyServicePortStateFailed,
			FailureReason: hamysql.SanitizeConnectionError(err),
		}, err
	}
	return &haprobe.MySqlProxyServicePortStatus{State: haprobe.MySqlProxyServicePortStateOk}, nil
}

func (c *collector) obtainGlobalStatus() (*haprobe.MySqlGlobalStatus, error) {
	ctx, cancel := c.queryCtx()
	defer cancel()

	var statusResults []globalStatus
	err := c.db.DB().WithContext(ctx).Raw("SHOW GLOBAL STATUS").Scan(&statusResults).Error
	if err != nil {
		return nil, err
	}

	dbStatus := convertToMySqlStatus(statusResults)

	var version string
	err = c.db.DB().WithContext(ctx).Raw("SELECT VERSION() as version").Scan(&version).Error
	if err != nil {
		logger.Warn("failed to get mysql version, errmsg: %s", err)
		return dbStatus, err
	}
	dbStatus.Version = version

	var portResult globalStatus
	err = c.db.DB().WithContext(ctx).Raw("SHOW VARIABLES LIKE 'port'").Scan(&portResult).Error
	if err != nil {
		logger.Warn("failed to get mysql listen port, result: %s, errmsg: %s", portResult, err)
		return dbStatus, err
	}

	port, err := converter.ToInt(portResult.Value)
	if err != nil {
		logger.Error("failed to convert mysql listen port to int, port: %v, errmsg: %s", portResult.Value, err)
		return dbStatus, err
	}

	logger.Debug("mysql listen port:%v", port)

	dbStatus.ListenPort = port

	// Key buffer read hit rate
	if dbStatus.KeyReadRequests != 0 {
		dbStatus.KeyBufferHitRate = float64(dbStatus.KeyReads) / float64(dbStatus.KeyReadRequests)
	}

	return dbStatus, err
}

// obtainlHostStatus obtain this host status
func (c *collector) obtainHostStatus() (*haprobe.HostMetric, error) {
	hostStatus := &haprobe.HostMetric{}

	if err := c.SetCpuStatus(hostStatus); err != nil {
		logger.Warn("failed to update CPU status, errmsg: %s", err)
	}

	if err := c.SetNetStatus(hostStatus); err != nil {
		logger.Warn("failed to update Net status, errmsg: %s", err)
	}

	if err := c.SetMemoryStatus(hostStatus); err != nil {
		logger.Warn("failed to update memory status, errmsg: %s", err)
	}

	if err := c.SetDiskStatus(hostStatus); err != nil {
		logger.Warn("failed to update memory status, errmsg: %s", err)
	}

	return hostStatus, nil
}

// hasSessionVariableLike reports whether SHOW SESSION VARIABLES LIKE pattern returned any rows.
// MariaDB (and some MySQL builds) do not accept bound parameters in SHOW ... LIKE, so the pattern
// is embedded as a single-quoted literal; patterns containing ' are not escaped.
func (c *collector) hasSessionVariableLike(ctx context.Context, pattern string) (bool, error) {
	var list []globalStatus
	sql := fmt.Sprintf("SHOW SESSION VARIABLES LIKE '%s'", pattern)
	if err := c.db.DB().WithContext(ctx).Raw(sql).Scan(&list).Error; err != nil {
		return false, err
	}
	return len(list) > 0, nil
}

// disableSessionForwarding disables session forwarding for the spider and tdbctl
func (c *collector) disableSpiderSessionForwarding() error {
	if c.machineType != haprobe.DbmMetadataMachineTypeSpider {
		return nil
	}

	ctx, cancel := c.queryCtx()
	defer cancel()

	if c.isAdmin() { // for tdbctl
		err := c.db.DB().WithContext(ctx).Exec("SET SESSION tc_admin=OFF").Error
		if err != nil {
			logger.Warn("failed to set session tc_admin to OFF, errmsg: %s", err)
			return err
		}
	}

	if !c.isAdmin() { // for spider
		has, err := c.hasSessionVariableLike(ctx, "ddl_execute_by_ctl")
		if err != nil {
			logger.Warn("failed to check if ddl_execute_by_ctl exists, errmsg: %s", err)
			return err
		}

		if !has {
			return nil
		}

		if err := c.db.DB().WithContext(ctx).Exec("SET SESSION ddl_execute_by_ctl=OFF").Error; err != nil {
			logger.Warn("failed to set session ddl_execute_by_ctl to OFF, errmsg: %s", err)
			return err
		}
	}

	return nil
}

// hasReplInfo return true if result set from SHOW SLAVE STATUS is not empty.
func (c *collector) hasReplInfo() (bool, error) {
	ctx, cancel := c.queryCtx()
	defer cancel()

	rows, err := c.db.DB().WithContext(ctx).Raw("SHOW SLAVE STATUS").Rows()
	if err != nil {
		logger.Warn("failed to run SHOW SLAVE STATUS, errmsg: %s", err)
		return false, err
	}
	defer rows.Close()

	// Treat as replica when SHOW SLAVE STATUS returns at least one row.
	if !rows.Next() {
		return false, rows.Err()
	}
	return true, nil
}

// isSlave returns whether the mysql instance is a slave.
func (c *collector) isSlave() bool {
	switch c.machineType {
	case haprobe.DbmMetadataMachineTypeProxy:
		return false

	case haprobe.DbmMetadataMachineTypeBackend:
		if c.instanceRole == haprobe.MySQLStorageSlave {
			return true
		}

		// Notice: backend repeater is not treated as slave
		return false

	case haprobe.DbmMetadataMachineTypeSpider:
		if c.isAdmin() {
			isSlave, _ := c.hasReplInfo()
			return isSlave
		}
		return false

	case haprobe.DbmMetadataMachineTypeRemote:
		if c.instanceRole == haprobe.TenDBClusterStorageSlave {
			return true
		}
		return false

	default:
		return false
	}
}

func (c *collector) obtainHeartbeatStatus(writeBinlog bool) (*haprobe.MySqlHeartbeatStatus, error) {
	heartbeatStatus := &haprobe.MySqlHeartbeatStatus{
		WriteSuccess:       false,
		WriteFailureReason: "unknown error",
		HeartbeatDelay:     365 * 24 * 60 * 60,
	}

	ctx, cancel := c.queryCtx()
	defer cancel()

	sqlBinLog := "OFF"
	if writeBinlog {
		sqlBinLog = "ON"
	}

	// set session sql_log_bin
	if err := c.db.DB().WithContext(ctx).Exec(
		fmt.Sprintf("SET SESSION sql_log_bin=%s", sqlBinLog)).Error; err != nil {
		logger.Warn("failed to set session sql_log_bin to %s, errmsg: %s", sqlBinLog, err)
		heartbeatStatus.WriteFailureReason = err.Error()
		return heartbeatStatus, err
	}

	// query server_id
	var serverId string
	err := c.db.DB().WithContext(ctx).Raw("SELECT @@server_id").Scan(&serverId).Error
	if err != nil {
		logger.Warn("failed to get mysql server id, errmsg: %s", err)
		heartbeatStatus.WriteFailureReason = err.Error()
		return heartbeatStatus, err
	}

	// set session transaction isolation level to repeatable read
	if err := c.db.DB().WithContext(ctx).Exec(
		"SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ").Error; err != nil {
		logger.Warn("failed to set session transaction isolation level to repeatable read, errmsg: %s", err)
		heartbeatStatus.WriteFailureReason = err.Error()
		return heartbeatStatus, err
	}

	// set session binlog format to statement
	if err := c.db.DB().WithContext(ctx).Exec(
		"SET SESSION binlog_format='STATEMENT'").Error; err != nil {
		logger.Warn("failed to set session binlog format to statement, errmsg: %s", err)
		heartbeatStatus.WriteFailureReason = err.Error()
		return heartbeatStatus, err
	}

	// insert heartbeat
	writeSuccess := true
	writeFailureReason := ""
	writeErr := c.db.DB().WithContext(ctx).Exec(`
		REPLACE INTO infodba_schema.master_slave_heartbeat
		(master_server_id, slave_server_id, master_time, slave_time, delay_sec) 
		VALUES(?, @@server_id, now(), sysdate(), timestampdiff(SECOND, now(),sysdate()))`, serverId).Error
	if writeErr != nil {
		logger.Warn("failed to insert heartbeat, errmsg: %s", writeErr)
		writeSuccess = false
		writeFailureReason = writeErr.Error()
	}
	heartbeatStatus.WriteSuccess = writeSuccess
	heartbeatStatus.WriteFailureReason = writeFailureReason

	// query heartbeat delay; GREATEST(...,0) on SIGNED avoids negative-to-UNSIGNED wraparound on clock skew.
	const fallbackHeartbeatDelay = uint64(365 * 24 * 60 * 60)
	var heartbeatDelay uint64
	tx := c.db.DB().WithContext(ctx).Raw(`
		SELECT GREATEST(CAST(UNIX_TIMESTAMP(NOW())-UNIX_TIMESTAMP(master_time) AS SIGNED), 0) as heartbeat_delay 
		FROM infodba_schema.master_slave_heartbeat 
		WHERE master_server_id = ? and slave_server_id = ?`, serverId, serverId).Scan(&heartbeatDelay)
	if tx.Error != nil {
		logger.Warn("failed to query heartbeat delay, errmsg: %s", tx.Error)
		heartbeatDelay = fallbackHeartbeatDelay
	} else if tx.RowsAffected == 0 {
		// No heartbeat row: treat as unknown/broken, never report 0 delay.
		logger.Warn("no heartbeat row for server_id=%s, keep fallback heartbeat delay", serverId)
		heartbeatDelay = fallbackHeartbeatDelay
	}
	heartbeatStatus.HeartbeatDelay = heartbeatDelay

	return heartbeatStatus, nil
}

func (c *collector) obtainSlaveStatus() (*haprobe.MySqlSlaveStatus, error) {
	ctx, cancel := c.queryCtx()
	defer cancel()

	var slaveInfo slaveStatus
	if err := c.db.DB().WithContext(ctx).Raw("SHOW SLAVE STATUS").Scan(&slaveInfo).Error; err != nil {
		logger.Warn("failed to run SHOW SLAVE STATUS, errmsg: %s", err)
		return nil, err
	}

	const fallbackDelaySec = uint64(365 * 24 * 60 * 60)
	ret := &haprobe.MySqlSlaveStatus{
		MasterHost:          slaveInfo.MasterHost,
		MasterPort:          slaveInfo.MasterPort,
		SlaveIORunning:      slaveInfo.SlaveIORunning,
		SlaveSQLRunning:     slaveInfo.SlaveSQLRunning,
		SecondsBehindMaster: slaveInfo.SecondsBehindMaster,
		MasterServerId:      slaveInfo.MasterServerId,
		HeartbeatDelay:      fallbackDelaySec,
		LastIODelay:         fallbackDelaySec,
	}

	// Optional delays from infodba_schema.master_slave_heartbeat.
	var hb struct {
		HeartbeatDelay uint64 `gorm:"column:heartbeat_delay"`
		LastIODelay    uint64 `gorm:"column:last_io_delay"`
	}

	// Master_Server_Id == 0 means replication never connected (e.g. RESET SLAVE/CHANGE MASTER):
	// no heartbeat row can match, so keep the fallback delay instead of overwriting it with 0.
	if slaveInfo.MasterServerId == 0 {
		logger.Warn("slave Master_Server_Id is 0 (replication not connected), keep fallback delay")
		return ret, nil
	}

	// Use GREATEST(..., 0) on SIGNED arithmetic to avoid negative-to-UNSIGNED wraparound.
	tx := c.db.DB().WithContext(ctx).Raw(`
		SELECT GREATEST(CAST(UNIX_TIMESTAMP(NOW()) - UNIX_TIMESTAMP(master_time) AS SIGNED), 0) AS heartbeat_delay,
		       GREATEST(CAST(IFNULL(delay_sec, 0) AS SIGNED), 0) AS last_io_delay
		FROM infodba_schema.master_slave_heartbeat
		WHERE master_server_id = ? AND slave_server_id = @@server_id`,
		slaveInfo.MasterServerId).Scan(&hb)
	if tx.Error != nil {
		logger.Warn("failed to query slave delay, errmsg: %s", tx.Error)
		return ret, nil // keep fallback
	}
	if tx.RowsAffected == 0 {
		// No matching heartbeat row (stale/ownership changed): keep fallback, never report 0 for broken repl.
		logger.Warn("no heartbeat row for master_server_id=%d, keep fallback delay", slaveInfo.MasterServerId)
		return ret, nil
	}

	ret.HeartbeatDelay = hb.HeartbeatDelay
	ret.LastIODelay = hb.LastIODelay

	return ret, nil
}
