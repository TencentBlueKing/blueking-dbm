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
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/hanet"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

const (
	heartbeatDefaultErrMsg      = string("unknown error")
	fallbackHeartbeatDelaySec   = uint64(365 * 24 * 60 * 60)
	heartbeatSQLTimeout         = 1 * time.Second
	heartbeatWriteRetryInterval = 2 * time.Second
	heartbeatWriteMaxAttempts   = 3
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

func (c *collector) writeHeartbeatFailureEvent(err error) *haprobe.DbEvent {
	return &haprobe.DbEvent{
		Name:       haprobe.DbEventNameHeartbeatWriteFailure,
		Reason:     haprobe.DbEventNameReasonHeartbeatWriteFailure,
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

	// Each collector already owns a dedicated *sql.DB. Cap the pool at one connection so
	// sequential session settings (e.g. disable spider forwarding, sql_log_bin) and the
	// following DDL/DML stay on the same MySQL session. A timed-out query may drop that
	// connection and the next statement will reconnect; callers that depend on session
	// state must re-apply it at the start of each attempt (see writeDbhaHeartbeat).
	sqlDb.SetMaxIdleConns(1)
	sqlDb.SetMaxOpenConns(1)
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

func (c *collector) isTendbhaProxyAdminPort() bool {
	return c.isTendbHaProxy() && c.isAdmin()
}

// isTdbctl reports whether this endpoint is a tdbctl instance.
func (c *collector) isTdbctl() bool {
	return c.isTendbClusterProxy() && c.isAdmin()
}

// isPlainMysqlStorage reports whether this endpoint is a real MySQL storage backend.
func (c *collector) isPlainMysqlStorage() bool {
	return c.accessLayer == haprobe.DbmMetadataAccessLayerTypeStorage &&
		((c.machineType == haprobe.DbmMetadataMachineTypeBackend) ||
			(c.machineType == haprobe.DbmMetadataMachineTypeRemote))
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

// disableSpiderSessionForwarding disables session forwarding for spider / tdbctl.
// ctx controls the overall deadline for all SQL in this call.
func (c *collector) disableSpiderSessionForwarding(ctx context.Context) error {
	if c.machineType != haprobe.DbmMetadataMachineTypeSpider {
		return nil
	}

	// for tdbctl
	if c.isAdmin() {
		if err := c.db.DB().WithContext(ctx).Exec("SET SESSION tc_admin=OFF").Error; err != nil {
			logger.Warn("failed to set session tc_admin to OFF, errmsg: %s", err)
			return err
		}

		return nil
	}

	// for spider
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

// heartbeatExec runs one Exec with a per-statement 1s timeout nested under parent
// (the collector's overall queryCtx deadline).
func (c *collector) heartbeatExec(parent context.Context, query string, args ...any) error {
	ctx, cancel := context.WithTimeout(parent, heartbeatSQLTimeout)
	defer cancel()
	return c.db.DB().WithContext(ctx).Exec(query, args...).Error
}

// heartbeatScan runs one Raw+Scan with a per-statement 1s timeout nested under parent.
// It returns RowsAffected so callers can tell whether the result set was empty.
func (c *collector) heartbeatScan(parent context.Context, dest any, query string, args ...any) (int64, error) {
	ctx, cancel := context.WithTimeout(parent, heartbeatSQLTimeout)
	defer cancel()
	tx := c.db.DB().WithContext(ctx).Raw(query, args...).Scan(dest)
	return tx.RowsAffected, tx.Error
}

func (c *collector) obtainHeartbeatStatus(writeBinlog bool, writeMaxAttempts int) (
	*haprobe.MySqlHeartbeatStatus, error) {
	heartbeatStatus := &haprobe.MySqlHeartbeatStatus{
		WriteSuccess:       false,
		WriteFailureReason: heartbeatDefaultErrMsg,
		HeartbeatDelay:     fallbackHeartbeatDelaySec,
	}

	parentCtx, cancel := c.queryCtx()
	defer cancel()

	host := c.endpoint.Host
	port := c.endpoint.Port

	for attempt := 1; attempt <= writeMaxAttempts; attempt++ {
		c.writeDbhaHeartbeat(parentCtx, writeBinlog, host, port, heartbeatStatus)
		if heartbeatStatus.WriteSuccess {
			break
		}

		if attempt < writeMaxAttempts {
			logger.Warn("write heartbeat failed, will retry, attempt: %d, max_attempts: %d, host: %s, port: %d, errmsg: %s",
				attempt, writeMaxAttempts, host, port, heartbeatStatus.WriteFailureReason)
			select {
			case <-parentCtx.Done():
				return heartbeatStatus, gerrors.New(gerrors.Failure,
					"context done before heartbeat write success")
			case <-time.After(heartbeatWriteRetryInterval):
			}
		}
	}

	c.readDbhaHeartbeatDelay(parentCtx, host, port, heartbeatStatus)

	return heartbeatStatus, nil
}

// writeDbhaHeartbeat ensures the probe-owned heartbeat schema/table exist (DDL with
// sql_log_bin=OFF, only when the table is missing), then REPLACE a row for host:port.
// On any failure it records WriteSuccess=false but never aborts the caller — delay
// is still queried afterward.
func (c *collector) writeDbhaHeartbeat(
	parent context.Context, writeBinlog bool, host string, port int, status *haprobe.MySqlHeartbeatStatus,
) {
	markFail := func(err error) {
		status.WriteSuccess = false
		status.WriteFailureReason = err.Error()
	}

	if err := c.disableSpiderSessionForwarding(parent); err != nil {
		logger.Warn("failed to disable spider session forwarding, host: %s, port: %d, errmsg: %s",
			host, port, err)
		markFail(err)
		return
	}

	if err := c.heartbeatExec(parent, "SET SESSION sql_log_bin=OFF"); err != nil {
		logger.Warn("failed to set session sql_log_bin to OFF, errmsg: %s", err)
		markFail(err)
		return
	}

	if err := c.confirmHeartbeatTable(parent); err != nil {
		logger.Warn("failed to confirm heartbeat table, db: %s, table: %s, errmsg: %s",
			hamodel.ProbeMysqlDbName, hamodel.DbhaHeartbeatTableName, err)
		markFail(err)
		return
	}

	sqlBinLog := "OFF"
	if writeBinlog {
		sqlBinLog = "ON"
	}
	if err := c.heartbeatExec(parent, fmt.Sprintf("SET SESSION sql_log_bin=%s", sqlBinLog)); err != nil {
		logger.Warn("failed to set session sql_log_bin, value: %s, errmsg: %s", sqlBinLog, err)
		markFail(err)
		return
	}

	var serverID uint64
	if _, err := c.heartbeatScan(parent, &serverID, "SELECT @@server_id"); err != nil {
		logger.Warn("failed to get mysql server id, errmsg: %s", err)
		markFail(err)
		return
	}

	// Store SYSDATE() as a formatted string so the column type stays timezone-neutral.
	replaceSQL := fmt.Sprintf(
		"REPLACE INTO `%s`.`%s` (`host`, `port`, `server_id`, `update_time`) "+
			"VALUES (?, ?, ?, SYSDATE())",
		hamodel.ProbeMysqlDbName, hamodel.DbhaHeartbeatTableName)
	if err := c.heartbeatExec(parent, replaceSQL, host, port, serverID); err != nil {
		logger.Warn("failed to replace heartbeat, host: %s, port: %d, errmsg: %s", host, port, err)
		markFail(err)
		return
	}

	status.WriteSuccess = true
	status.WriteFailureReason = ""
}

// readDbhaHeartbeatDelay fills HeartbeatDelay from the probe-owned table. Missing row or
// query failure keeps the fallback delay so a broken path is never reported as 0 lag.
func (c *collector) readDbhaHeartbeatDelay(
	parent context.Context, host string, port int, status *haprobe.MySqlHeartbeatStatus,
) {
	var heartbeatDelay int64

	delaySQL := fmt.Sprintf(
		"SELECT GREATEST(CAST(TIMESTAMPDIFF(SECOND, update_time, SYSDATE()) AS SIGNED), 0) AS heartbeat_delay "+
			"FROM `%s`.`%s` WHERE host = ? AND port = ?",
		hamodel.ProbeMysqlDbName, hamodel.DbhaHeartbeatTableName)

	rows, err := c.heartbeatScan(parent, &heartbeatDelay, delaySQL, host, port)
	if err != nil {
		logger.Warn("failed to query heartbeat delay, host: %s, port: %d, errmsg: %s", host, port, err)
		status.HeartbeatDelay = fallbackHeartbeatDelaySec
		return
	}

	if rows == 0 {
		logger.Warn("no heartbeat row, keep fallback heartbeat delay, host: %s, port: %d", host, port)
		status.HeartbeatDelay = fallbackHeartbeatDelaySec
		return
	}

	status.HeartbeatDelay = uint64(heartbeatDelay)
}

// confirmReplHeartbeatTable disables spider session forwarding, turns sql_log_bin ON,
// and creates the probe-owned db/table for dbha_repl_heartbeat if they do not exist.
func (c *collector) confirmReplHeartbeatTable(parent context.Context) error {
	if err := c.disableSpiderSessionForwarding(parent); err != nil {
		return err
	}

	if err := c.heartbeatExec(parent, "SET SESSION sql_log_bin=ON"); err != nil {
		return err
	}

	if err := c.heartbeatExec(parent, hamodel.CreateProbeMysqlDbSQL); err != nil {
		return err
	}

	if err := c.heartbeatExec(parent, hamodel.CreateDbhaReplHeartbeatTableSQL); err != nil {
		return err
	}

	return nil
}

// confirmHeartbeatTable checks information_schema and only CREATE DATABASE/TABLE
// IF NOT EXISTS when dbha_heartbeat is missing.
func (c *collector) confirmHeartbeatTable(parent context.Context) error {
	var n int
	rows, err := c.heartbeatScan(parent, &n,
		"SELECT 1 FROM information_schema.TABLES WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ? LIMIT 1",
		hamodel.ProbeMysqlDbName, hamodel.DbhaHeartbeatTableName)

	if (err == nil) && (rows > 0) {
		return nil
	}

	// Some MySQL versions cannot query information_schema.TABLES;
	// treat failure as missing and fall through to CREATE.
	if err != nil {
		logger.Warn("failed to check heartbeat table existence, treat as missing, db: %s, table: %s, errmsg: %s",
			hamodel.ProbeMysqlDbName, hamodel.DbhaHeartbeatTableName, err)
	}

	if err := c.heartbeatExec(parent, hamodel.CreateProbeMysqlDbSQL); err != nil {
		return err
	}
	return c.heartbeatExec(parent, hamodel.CreateDbhaHeartbeatTableSQL)
}

// obtainMasterStatus writes a replication-delay heartbeat row (binlog ON, single attempt)
// into dbha_repl_heartbeat and reports delay from the newest matching row.
func (c *collector) obtainMasterStatus() (*haprobe.MySqlHeartbeatStatus, error) {
	masterStatus := &haprobe.MySqlHeartbeatStatus{
		WriteSuccess:       false,
		WriteFailureReason: heartbeatDefaultErrMsg,
		HeartbeatDelay:     fallbackHeartbeatDelaySec,
	}

	parentCtx, cancel := c.queryCtx()
	defer cancel()

	host := c.endpoint.Host
	port := c.endpoint.Port

	if err := c.confirmReplHeartbeatTable(parentCtx); err != nil {
		logger.Warn("failed to confirm repl heartbeat table, host: %s, port: %d, errmsg: %s",
			host, port, err)
		masterStatus.WriteFailureReason = err.Error()
		return masterStatus, err
	}

	serverID := c.writeReplHeartbeat(parentCtx, host, port, masterStatus)
	if !masterStatus.WriteSuccess {
		logger.Warn("write repl heartbeat failed, host: %s, port: %d, server_id: %d, errmsg: %s",
			host, port, serverID, masterStatus.WriteFailureReason)
	}
	c.readReplHeartbeatDelay(parentCtx, host, port, serverID, masterStatus)

	return masterStatus, nil
}

// writeReplHeartbeat turns sql_log_bin ON and REPLACE a row for host:port.
// Returns the server_id used for the write (0 when it could not be read).
func (c *collector) writeReplHeartbeat(
	parent context.Context, host string, port int, status *haprobe.MySqlHeartbeatStatus,
) uint64 {
	markFail := func(err error) {
		status.WriteSuccess = false
		status.WriteFailureReason = err.Error()
	}

	if err := c.heartbeatExec(parent, "SET SESSION sql_log_bin=ON"); err != nil {
		logger.Warn("failed to set session sql_log_bin, value: %s, errmsg: %s", "ON", err)
		markFail(err)
		return 0
	}

	var serverID uint64
	if _, err := c.heartbeatScan(parent, &serverID, "SELECT @@server_id"); err != nil {
		logger.Warn("failed to get mysql server id, errmsg: %s", err)
		markFail(err)
		return 0
	}

	replaceSQL := fmt.Sprintf(
		"REPLACE INTO `%s`.`%s` (`host`, `port`, `server_id`, `update_time`) VALUES (?, ?, ?, SYSDATE())",
		hamodel.ProbeMysqlDbName, hamodel.DbhaReplHeartbeatTableName)
	if err := c.heartbeatExec(parent, replaceSQL, host, port, serverID); err != nil {
		logger.Warn("failed to replace repl heartbeat, host: %s, port: %d, server_id: %d, errmsg: %s",
			host, port, serverID, err)
		markFail(err)
		return serverID
	}

	status.WriteSuccess = true
	status.WriteFailureReason = ""
	return serverID
}

// readReplHeartbeatDelay fills HeartbeatDelay from the newest dbha_repl_heartbeat row
// for (host, port, server_id). Missing row or query failure keeps the fallback delay.
func (c *collector) readReplHeartbeatDelay(
	parent context.Context, host string, port int, serverID uint64, status *haprobe.MySqlHeartbeatStatus,
) {
	if serverID == 0 {
		logger.Warn("skip repl heartbeat delay read, server_id is 0, host: %s, port: %d", host, port)
		status.HeartbeatDelay = fallbackHeartbeatDelaySec
		return
	}

	var heartbeatDelay int64
	delaySQL := fmt.Sprintf(
		"SELECT GREATEST(CAST(TIMESTAMPDIFF(SECOND, update_time, SYSDATE()) AS SIGNED), 0) AS heartbeat_delay "+
			"FROM `%s`.`%s` WHERE host = ? AND port = ? AND server_id = ? ORDER BY update_time DESC LIMIT 1",
		hamodel.ProbeMysqlDbName, hamodel.DbhaReplHeartbeatTableName)

	rows, err := c.heartbeatScan(parent, &heartbeatDelay, delaySQL, host, port, serverID)
	if err != nil {
		logger.Warn("failed to query repl heartbeat delay, host: %s, port: %d, server_id: %d, errmsg: %s",
			host, port, serverID, err)
		status.HeartbeatDelay = fallbackHeartbeatDelaySec
		return
	}

	if rows == 0 {
		logger.Warn("no repl heartbeat row, keep fallback delay, host: %s, port: %d, server_id: %d",
			host, port, serverID)
		status.HeartbeatDelay = fallbackHeartbeatDelaySec
		return
	}

	status.HeartbeatDelay = uint64(heartbeatDelay)
}

// obtainSlaveStatus reads SHOW SLAVE STATUS as a result set and fills replication delay.
// Returns (nil, nil) only when the result set is empty (not a replica / no slave channel).
// In all other cases (including query failure) the returned status is never nil.
func (c *collector) obtainSlaveStatus() (*haprobe.MySqlSlaveStatus, error) {
	ctx, cancel := c.queryCtx()
	defer cancel()

	ret := &haprobe.MySqlSlaveStatus{
		State:          mysqlCollectStateOk,
		HeartbeatDelay: fallbackHeartbeatDelaySec,
	}

	var slaveInfos []slaveStatus
	if err := c.db.DB().WithContext(ctx).Raw("SHOW SLAVE STATUS").Scan(&slaveInfos).Error; err != nil {
		logger.Warn("failed to run SHOW SLAVE STATUS, errmsg: %s", err)
		ret.State, ret.FailureReason = collectStatusResult(err)
		return ret, err
	}
	if len(slaveInfos) == 0 {
		return nil, nil
	}

	slaveInfo := slaveInfos[0]
	ret.MasterHost = slaveInfo.MasterHost
	ret.MasterPort = slaveInfo.MasterPort
	ret.SlaveIORunning = slaveInfo.SlaveIORunning
	ret.SlaveSQLRunning = slaveInfo.SlaveSQLRunning
	ret.SecondsBehindMaster = slaveInfo.SecondsBehindMaster
	ret.MasterServerId = slaveInfo.MasterServerId

	// Master_Server_Id == 0 means replication never connected (e.g. RESET SLAVE/CHANGE MASTER):
	// no heartbeat row can match, so keep the fallback delay instead of overwriting it with 0.
	if slaveInfo.MasterServerId == 0 {
		logger.Warn("slave Master_Server_Id is 0 (replication not connected), keep fallback delay")
		return ret, nil
	}

	// Delay from probe-owned dbha_repl_heartbeat replicated from master.
	var heartbeatDelay int64
	delaySQL := fmt.Sprintf(
		"SELECT GREATEST(CAST(TIMESTAMPDIFF(SECOND, update_time, SYSDATE()) AS SIGNED), 0) AS heartbeat_delay "+
			"FROM `%s`.`%s` WHERE host = ? AND port = ? AND server_id = ? ORDER BY update_time DESC LIMIT 1",
		hamodel.ProbeMysqlDbName, hamodel.DbhaReplHeartbeatTableName)
	tx := c.db.DB().WithContext(ctx).Raw(delaySQL,
		slaveInfo.MasterHost, slaveInfo.MasterPort, slaveInfo.MasterServerId).Scan(&heartbeatDelay)
	if tx.Error != nil {
		logger.Warn("failed to query slave repl heartbeat delay, current_slave: %s:%d, master: %s:%d, "+
			"master_server_id: %d, errmsg: %s",
			c.endpoint.Host, c.endpoint.Port, slaveInfo.MasterHost, slaveInfo.MasterPort,
			slaveInfo.MasterServerId, tx.Error)
		ret.State, ret.FailureReason = collectStatusResult(tx.Error)
		return ret, tx.Error
	}
	if tx.RowsAffected == 0 {
		logger.Warn("no repl heartbeat row for master, keep fallback delay, current_slave: %s:%d, master: %s:%d, "+
			"master_server_id: %d",
			c.endpoint.Host, c.endpoint.Port, slaveInfo.MasterHost, slaveInfo.MasterPort,
			slaveInfo.MasterServerId)
		return ret, nil
	}

	ret.HeartbeatDelay = uint64(heartbeatDelay)
	return ret, nil
}
