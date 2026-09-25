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
	"strings"

	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/internal/analysis/dbm"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchcore"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchlogger"
	"dbm-services/common/dbha-v2/pkg/converter"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

const (
	DefaultMySQLProtocol string = "tcp"
)

// MySQLVariableResult represents MySQL variable result
type MySQLVariableResult struct {
	VariableName string `gorm:"column:Variable_name"`
	Value        string `gorm:"column:Value"`
}

// SlaveStatusInfo represents MySQL slave status information.
type SlaveStatusInfo = hamysql.ReplicationStatus

// SlaveTimeDelayInfo contains slave replication delay information
type SlaveTimeDelayInfo struct {
	SlaveHeartbeatDelay float64 `gorm:"column:heartbeat_delay"`
}

// MasterStatusInfo represents MySQL master status information.
type MasterStatusInfo = hamysql.MasterStatusInfo

// ProxyBackendInfo contains proxy backend connection information
type ProxyBackendInfo struct {
	BackendNdx       int    `db:"backend_ndx"`
	Address          string `db:"address"`
	State            string `db:"state"`
	Type             string `db:"type"`
	UUID             string `db:"uuid"`
	ConnectedClients int    `db:"connected_clients"`
	RefreshTime      int    `db:"refresh_time"`
}

// NewMySQLSwitchInstance creates a new MySQL switch instance based on metadata
func NewMySQLSwitchInstance(metadata *dbm.DbInstMetadata) (switchcore.SwitchableInstance, error) {
	mysqlBaseInstance := MySQLBaseSwitchInstance{
		BaseSwitchInstance: switchcore.BaseSwitchInstance{
			IP:           metadata.IP,
			Port:         metadata.Port,
			Status:       metadata.Status,
			BkCloudID:    metadata.BkCloudID,
			BkIdcCityID:  metadata.BkIdcCityID,
			BkBizID:      metadata.BkBizID,
			Cluster:      metadata.Cluster,
			ClusterID:    metadata.ClusterID,
			ClusterType:  metadata.ClusterType,
			MachineType:  metadata.MachineType,
			InstanceRole: metadata.InstanceRole,
			DbmClient:    &dbm.Client{},
		},
		IsStandBy:        metadata.IsStandBy,
		AdminPort:        metadata.AdminPort,
		BindEntry:        metadata.BindEntry,
		ProxyInstanceSet: metadata.ProxyInstanceSet,
		BinlogDumperSet:  metadata.BinlogDumpers,
	}

	switch metadata.MachineType {
	case haprobe.DbmMetadataMachineTypeBackend:
		res := &MySQLStorageSwitchInstance{
			MySQLBaseSwitchInstance: mysqlBaseInstance,
		}
		if metadata.InstanceRole == haprobe.MySQLStorageMaster {
			res.SetStandbySlave(metadata.Receiver)
		}
		return res, nil

	case haprobe.DbmMetadataMachineTypeProxy:
		res := &MySQLProxySwitchInstance{
			MySQLBaseSwitchInstance: mysqlBaseInstance,
		}
		return res, nil

	default:
		logger.Error("unknown machine type(%s) for MySQL switch instance constructor", metadata.MachineType)
		return nil, gerrors.New(gerrors.InvalidParameter, "Invalid machine type")
	}
}

// MySQLBaseSwitchInstance provides base functionality for MySQL switch operations
type MySQLBaseSwitchInstance struct {
	switchcore.BaseSwitchInstance

	// The following are instance metadata information from DBM

	StandBySlave     *dbm.DbmMetadataSlaveInfo
	IsStandBy        bool
	AdminPort        int
	BindEntry        dbm.DbmMetadataBindEntry
	ProxyInstanceSet []dbm.DbmMetadataProxyInstance
	BinlogDumperSet  []dbm.DbmMetadataBinlogDumper
}

// SetStandbySlave sets the standby slave for master instance
// Only master instances can call this method.
// If no standby slave is found, it uses the first slave in the list.
func (sw *MySQLBaseSwitchInstance) SetStandbySlave(slaves []dbm.DbmMetadataSlaveInfo) {
	if len(slaves) == 0 {
		logger.Warn("no standby slave found from provided slaves for mysql master(%s:%d)", sw.IP, sw.Port)
		sw.StandBySlave = nil
		return
	}

	findIndex := 0
	for i, slave := range slaves {
		if slave.IsStandBy {
			findIndex = i
			break
		}
	}
	sw.StandBySlave = &dbm.DbmMetadataSlaveInfo{}
	*(sw.StandBySlave) = slaves[findIndex]
	logger.Debug("successfully set standby slave for mysql master(%s:%d): %s",
		sw.IP, sw.Port, converter.ToStrIgnoreErr(*(sw.StandBySlave)))
}

// StopSlave stops slave replication
func (sw *MySQLBaseSwitchInstance) StopSlave(slaveDB *hamysql.GormDB) error {
	return DoStopSlave(slaveDB, sw.ReportLogf)
}

// StartSlave starts slave replication
func (sw *MySQLBaseSwitchInstance) StartSlave(slaveDB *hamysql.GormDB) error {
	return DoStartSlave(slaveDB, sw.ReportLogf)
}

// ShowMasterStatus retrieves master status information
func (sw *MySQLBaseSwitchInstance) ShowMasterStatus(db *hamysql.GormDB) (*MasterStatusInfo, error) {
	return DoShowMasterStatus(db, sw.ReportLogf)
}

// ShowSlaveStatus retrieves slave status information
func (sw *MySQLBaseSwitchInstance) ShowSlaveStatus(slaveDB *hamysql.GormDB) (*SlaveStatusInfo, error) {
	return DoShowSlaveStatus(slaveDB, sw.ReportLogf)
}

// ResetSlave resets slave replication settings
func (sw *MySQLBaseSwitchInstance) ResetSlave(slaveDB *hamysql.GormDB) error {
	return DoResetSlave(slaveDB, sw.ReportLogf)
}

// ResetSlaveWithBinlogPos resets slave and gets consistent binlog position
func (sw *MySQLBaseSwitchInstance) ResetSlaveWithBinlogPos(slaveIp string, slavePort int) (string, uint64, error) {
	return DoResetSlaveWithBinlogPos(slaveIp, slavePort, sw.ReportLogf)
}

// ChangeMasterAuto automatically changes master configuration
func (sw *MySQLBaseSwitchInstance) ChangeMasterAuto(slaveIp string, slavePort int, src hamysql.ReplSource) error {
	return DoChangeMasterSteps(slaveIp, slavePort, src, sw.ReportLogf)
}

// MySQLStorageSwitchInstance handles MySQL storage node switching
type MySQLStorageSwitchInstance struct {
	MySQLBaseSwitchInstance

	// Information obtained during switch

	NewMasterBinlogFile string
	NewMasterBinlogPos  uint64
}

// GetInstanceInfo returns instance information as string
func (sw *MySQLStorageSwitchInstance) GetInstanceInfo() string {
	standBySlave := "nil"
	if sw.StandBySlave != nil {
		standBySlave = fmt.Sprintf("%s:%d", sw.StandBySlave.Ip, sw.StandBySlave.Port)
	}
	infoStr := fmt.Sprintf("{bk_cloud_id:%d, ip:%s, port:%d, bk_idc_city_id:%d, bk_biz_id:%d, status:%s, "+
		"cluster:%s, cluster_id:%d, cluster_type:%s, machine_type:%s, role:%s, standby_slave:%s, is_stand_by:%t}",
		sw.BkCloudID, sw.IP, sw.Port, sw.BkIdcCityID, sw.BkBizID, sw.Status, sw.Cluster,
		sw.ClusterID, sw.ClusterType, sw.MachineType, sw.InstanceRole, standBySlave, sw.IsStandBy)
	return infoStr
}

// CheckMySQLStorageMaster performs pre-switch validation checks for "backend_master" node
func (sw *MySQLStorageSwitchInstance) CheckMySQLStorageMaster() (switchcore.SwitchCheckCode, error) {
	if sw.StandBySlave == nil {
		err := gerrors.Newf(gerrors.Failure, "the standby slave is nil")
		sw.ReportLog(switchlogger.SwitchError, err.Error())
		return switchcore.SwitchCheckUnpass, err
	}
	if sw.StandBySlave.Status == dbm.Unavailable {
		err := gerrors.Newf(gerrors.Failure, "the standby slave(%s:%d) is unavailable",
			sw.StandBySlave.Ip, sw.StandBySlave.Port)
		sw.ReportLog(switchlogger.SwitchError, err.Error())
		return switchcore.SwitchCheckUnpass, err
	}

	slaveChecker := MySQLSlaveChecker{
		MasterIp:     sw.IP,
		MasterPort:   sw.Port,
		MasterStatus: sw.Status,
		SlaveIp:      sw.StandBySlave.Ip,
		SlavePort:    sw.StandBySlave.Port,
		SlaveStatus:  sw.StandBySlave.Status,
		ReportLogf:   sw.ReportLogf,
	}

	if err := slaveChecker.Check(); err != nil {
		sw.ReportLogf(switchlogger.SwitchError, "slave status check unpass: %s", err.Error())
		return switchcore.SwitchCheckUnpass, err
	}

	if len(sw.ProxyInstanceSet) == 0 {
		err := gerrors.Newf(gerrors.Failure, "no proxy instances were found for this storage node")
		sw.ReportLog(switchlogger.SwitchError, err.Error())
		return switchcore.SwitchCheckUnpass, err
	}

	return switchcore.SwitchRequired, nil
}

// CheckBeforeSwitch performs pre-switch validation checks
func (sw *MySQLStorageSwitchInstance) CheckBeforeSwitch() (switchcore.SwitchCheckCode, error) {
	switch sw.InstanceRole {
	case haprobe.MySQLStorageSlave:
		sw.ReportLogf(switchlogger.SwitchInfo, "this is a slave node, no need to check")
		return switchcore.SwitchRequired, nil
	case haprobe.MySQLStorageRepeater:
		sw.ReportLogf(switchlogger.SwitchWarn, "this is a repeater, dbha don't support")
		return switchcore.SwitchNotNeeded, nil
	case haprobe.MySQLStorageMaster:
		return sw.CheckMySQLStorageMaster()
	default:
		err := gerrors.Newf(gerrors.Failure, "invalid instance role: %s", sw.InstanceRole)
		sw.ReportLogf(switchlogger.SwitchError, "%s", err.Error())
		return switchcore.SwitchCheckUnpass, err
	}
}

// BatchRefreshProxiesBackends refreshes all available proxies' backends to the given address.
// Unavailable proxies are skipped with a warning log.
func (sw *MySQLStorageSwitchInstance) BatchRefreshProxiesBackends(
	backendIp string, backendPort int,
) error {
	proxyUser := config.Cfg.Database.Mysql.ProxyUser
	proxyPasswd := config.Cfg.Database.Mysql.ProxyPassword

	hasAvailableProxy := false
	for _, proxyIns := range sw.ProxyInstanceSet {
		if proxyIns.Status == dbm.Unavailable {
			sw.ReportLogf(switchlogger.SwitchWarn,
				"the proxy(%s:%d) is unavailable, skip updating its backends",
				proxyIns.Ip, proxyIns.AdminPort)
			continue
		}

		hasAvailableProxy = true

		if err := ProxyRefreshBackends(
			proxyIns.Ip, proxyIns.AdminPort, proxyUser, proxyPasswd,
			backendIp, backendPort, sw.ReportLogf,
		); err != nil {
			return gerrors.Newf(gerrors.Failure,
				"failed to refresh backends to (%s:%d) for the proxy(%s:%d), errmsg: %s",
				backendIp, backendPort, proxyIns.Ip, proxyIns.AdminPort, err.Error())
		}
	}

	if !hasAvailableProxy {
		return gerrors.Newf(gerrors.Failure, "no available proxies to update backends")
	}

	sw.ReportLogf(switchlogger.SwitchInfo,
		"successfully refreshed all available proxies' backends to (%s:%d)",
		backendIp, backendPort)
	return nil
}

// DoMasterSwitch performs the actual MySQL storage master switch
//  1. refresh all proxies' backends to 1.1.1.1
//  2. reset slave status for the standby slave and get its
//     consistent synchronization position(binlog file and binlog position)
//  3. refresh all proxies' backends to the alive mysql(standby slave)
func (sw *MySQLStorageSwitchInstance) DoMasterSwitch() error {
	sw.ReportLog(switchlogger.SwitchInfo, "switch step 1: update all proxies' backends to 1.1.1.1 first")
	if err := sw.BatchRefreshProxiesBackends("1.1.1.1", 3306); err != nil {
		return err
	}

	sw.ReportLog(switchlogger.SwitchInfo, "switch step 2: reset slave status for the standby slave")
	binlogFile, binlogPosition, err := sw.ResetSlaveWithBinlogPos(sw.StandBySlave.Ip, sw.StandBySlave.Port)
	if err != nil {
		err = gerrors.Newf(gerrors.Failure, "failed to reset slave status for the standby slave(%s:%d), errmsg: %s",
			sw.StandBySlave.Ip, sw.StandBySlave.Port, err.Error())
		sw.ReportLog(switchlogger.SwitchWarn, err.Error())
		return err
	}

	sw.NewMasterBinlogFile = binlogFile
	sw.NewMasterBinlogPos = binlogPosition

	sw.ReportLog(switchlogger.SwitchInfo, "switch step 3: update all proxies' backends to the new master")
	if err := sw.BatchRefreshProxiesBackends(sw.StandBySlave.Ip, sw.StandBySlave.Port); err != nil {
		return err
	}

	return nil
}

// DoSlaveSwitch performs the actual MySQL storage slave switch
func (sw *MySQLStorageSwitchInstance) DoSlaveSwitch() error {
	if sw.IsStandBy {
		sw.ReportLogf(switchlogger.SwitchInfo, "nothing to do for the standby slave")
		return nil
	}

	sw.ReportLog(switchlogger.SwitchInfo, "switch step 1: delete this slave storage instance from all bound entries")
	return sw.DeleteNameService(sw.BindEntry)
}

// DoSwitch performs the actual switch for MySQL backend nodes
func (sw *MySQLStorageSwitchInstance) DoSwitch() error {
	switch sw.InstanceRole {
	case haprobe.MySQLStorageSlave:
		return sw.DoSlaveSwitch()

	case haprobe.MySQLStorageMaster:
		return sw.DoMasterSwitch()

	default:
		return gerrors.Newf(gerrors.Failure, "the instance role(%s) is not supported when doing switch",
			sw.InstanceRole)
	}
}

// UpdateMetaInfo swaps roles of backend master and slave
func (sw *MySQLStorageSwitchInstance) UpdateMetaInfo() error {
	if sw.InstanceRole != haprobe.MySQLStorageMaster {
		sw.ReportLogf(switchlogger.SwitchInfo, "nothing to do for the instance role(%s) when updating meta info",
			sw.InstanceRole)
		return nil
	}

	err := sw.DbmClient.SwapMySQLRole(sw.BkCloudID, sw.IP, sw.Port, sw.StandBySlave.Ip, sw.StandBySlave.Port)
	if err != nil {
		errMsg := fmt.Sprintf("failed to swap roles of backend nodes(master:%s:%d, slave:%s:%d), errmsg:%s",
			sw.IP, sw.Port, sw.StandBySlave.Ip, sw.StandBySlave.Port, err.Error())
		sw.ReportLog(switchlogger.SwitchWarn, errMsg)
		return err
	}

	sw.ReportLogf(switchlogger.SwitchInfo, "successfully swap roles of backend nodes(master:%s:%d, slave:%s:%d)",
		sw.IP, sw.Port, sw.StandBySlave.Ip, sw.StandBySlave.Port)
	return nil
}

// DoFinal performs final operations after switch completion
func (sw *MySQLStorageSwitchInstance) DoFinal() error {
	sw.ReportLogf(switchlogger.SwitchInfo, "tbinlogdumpers info of current mysql: %s",
		GetBinlogDumperInfo(sw.BinlogDumperSet))

	if (sw.InstanceRole != haprobe.MySQLStorageMaster) || len(sw.BinlogDumperSet) == 0 {
		sw.ReportLogf(switchlogger.SwitchInfo, "no need to switch tbinlogdumper for current mysql")
		return nil
	}

	switchInstances := []dbm.DumperSwitchInstance{}
	for _, dumper := range sw.BinlogDumperSet {
		switchInstances = append(switchInstances, dbm.DumperSwitchInstance{
			Ip:             dumper.Ip,
			Port:           dumper.Port,
			BinlogFile:     sw.NewMasterBinlogFile,
			BinlogPosition: sw.NewMasterBinlogPos,
		})
	}

	SwitchInfos := []dbm.DumperSwitchInfo{
		{
			ClusterDomain:   sw.Cluster,
			SwitchInstances: switchInstances,
		},
	}

	err := sw.DbmClient.SwitchBinlogDumper(sw.BkCloudID, sw.GetApp(), SwitchInfos)
	if err != nil {
		errMsg := fmt.Sprintf("failed to switch all tbinlogdumpers for current mysql, errmsg: %s",
			err.Error())
		sw.ReportLog(switchlogger.SwitchWarn, errMsg)
		return gerrors.New(gerrors.Failure, errMsg)
	}
	sw.ReportLogf(switchlogger.SwitchInfo, "successfully switch all tbinlogdumpers for current mysql")

	return nil
}

// MySQLProxySwitchInstance handles MySQL proxy node switching
type MySQLProxySwitchInstance struct {
	MySQLBaseSwitchInstance
}

// DoSwitch deletes proxy instance from bound entries
func (sw *MySQLProxySwitchInstance) DoSwitch() error {
	sw.ReportLog(switchlogger.SwitchInfo, "switch step 1: delete this proxy instance from all bound entries")
	return sw.DeleteNameService(sw.BindEntry)
}

// GetInstanceInfo returns instance information as string
func (sw *MySQLProxySwitchInstance) GetInstanceInfo() string {
	infoStr := fmt.Sprintf("{bk_cloud_id:%d, ip:%s, port:%d, admin_port:%d, bk_idc_city_id:%d, "+
		"bk_biz_id:%d, status:%s, cluster:%s, cluster_id:%d, cluster_type:%s, machine_type:%s}",
		sw.BkCloudID, sw.IP, sw.Port, sw.AdminPort, sw.BkIdcCityID, sw.BkBizID, sw.Status, sw.Cluster,
		sw.ClusterID, sw.ClusterType, sw.MachineType)
	return infoStr
}

// ProxyRefreshBackends refreshes proxy backends to the new backend address
func ProxyRefreshBackends(proxyIp string, proxyAdminPort int, proxyUser string, proxyPasswd string,
	backendIp string, backendPort int, reportLogf switchlogger.SwitchLogFunc) error {
	proxyDB, err := hamysql.NewSqlxDB(
		hamysql.OptionIP(proxyIp),
		hamysql.OptionPort(proxyAdminPort),
		hamysql.OptionUser(proxyUser),
		hamysql.OptionPassword(proxyPasswd),
		hamysql.OptionCharset(""),
		hamysql.OptionTimeout(switchcore.DbConnectTimeout()),
	)
	if err != nil {
		return gerrors.Newf(gerrors.Failure, "failed to connect proxy(%s:%d): %s", proxyIp, proxyAdminPort, err.Error())
	}

	defer proxyDB.Close()

	switchSql := fmt.Sprintf("refresh_backends('%s:%d',1)", backendIp, backendPort)
	querySql := "select * from backends"

	_, err = proxyDB.DB().Exec(switchSql)
	if err != nil {
		return gerrors.Newf(gerrors.Failure, "failed to execute sql(%s) on proxy(%s:%d), errmsg: %s",
			switchSql, proxyIp, proxyAdminPort, err.Error())
	}

	var backendList []ProxyBackendInfo
	err = proxyDB.DB().Select(&backendList, querySql)
	if err != nil {
		return gerrors.Newf(gerrors.Failure, "failed to execute sql(%s) on proxy(%s:%d), errmsg: %s",
			querySql, proxyIp, proxyAdminPort, err.Error())
	}

	backendAddress := fmt.Sprintf("%s:%d", backendIp, backendPort)
	for _, oneBackend := range backendList {
		if oneBackend.Address != backendAddress {
			return gerrors.Newf(gerrors.Failure, "failed to refresh proxy(%s:%d) backends to %s, wrong backend address: %s",
				proxyIp, proxyAdminPort, backendAddress, oneBackend.Address)
		}
	}

	if reportLogf != nil {
		reportLogf(switchlogger.SwitchInfo, "successfully refresh proxy(%s:%d) backends to %s",
			proxyIp, proxyAdminPort, backendAddress)
	}
	return nil
}

// DoShowSlaveStatus executes the version-appropriate show slave status SQL and returns the result
func DoShowSlaveStatus(slaveDB *hamysql.GormDB, reportLogf switchlogger.SwitchLogFunc) (*SlaveStatusInfo, error) {
	if slaveDB == nil {
		return nil, gerrors.New(gerrors.InvalidParameter, "get nil mysql connection when trying to show slave status")
	}
	slaveIp := slaveDB.Host()
	slavePort := slaveDB.Port()

	ctx, cancel := context.WithTimeout(context.Background(), switchcore.ExecSqlTimeout())
	defer cancel()

	stmts, err := slaveDB.ReplStatements(ctx)
	if err != nil {
		return nil, gerrors.Newf(gerrors.Failure,
			"failed to detect the server version on slave(%s:%d), errmsg: %s", slaveIp, slavePort, err.Error())
	}

	slaveStatus := &SlaveStatusInfo{}
	err = slaveDB.DBWithContext(ctx).Raw(stmts.ShowSlaveStatus).Scan(slaveStatus).Error
	if err != nil {
		return nil, gerrors.Newf(gerrors.Failure,
			"failed to execute '%s' on slave(%s:%d), errmsg: %s", stmts.ShowSlaveStatus, slaveIp, slavePort, err.Error())
	}
	slaveStatus.Normalize()
	if reportLogf != nil {
		reportLogf(switchlogger.SwitchInfo, "successfully execute '%s' on slave(%s:%d)",
			stmts.ShowSlaveStatus, slaveIp, slavePort)
	}

	return slaveStatus, nil
}

// DoStopSlave stops slave replication
func DoStopSlave(slaveDB *hamysql.GormDB, reportLogf switchlogger.SwitchLogFunc) error {
	if slaveDB == nil {
		return gerrors.New(gerrors.InvalidParameter, "get nil mysql connection when trying to stop slave")
	}
	slaveIp := slaveDB.Host()
	slavePort := slaveDB.Port()

	ctx, cancel := context.WithTimeout(context.Background(), switchcore.ExecSqlTimeout())
	defer cancel()

	stmts, err := slaveDB.ReplStatements(ctx)
	if err != nil {
		return gerrors.Newf(gerrors.Failure,
			"failed to detect the server version on slave(%s:%d), errmsg: %s", slaveIp, slavePort, err.Error())
	}

	err = slaveDB.DBWithContext(ctx).Exec(stmts.StopSlave).Error
	if err != nil {
		return gerrors.Newf(gerrors.Failure,
			"failed to execute '%s' on slave(%s:%d), errmsg: %s", stmts.StopSlave, slaveIp, slavePort, err.Error())
	}
	if reportLogf != nil {
		reportLogf(switchlogger.SwitchInfo, "successfully execute '%s' on slave(%s:%d)", stmts.StopSlave, slaveIp, slavePort)
	}
	return nil
}

// DoShowMasterStatus retrieves master status information
func DoShowMasterStatus(db *hamysql.GormDB, reportLogf switchlogger.SwitchLogFunc) (*MasterStatusInfo, error) {
	if db == nil {
		return nil, gerrors.New(gerrors.InvalidParameter, "get nil mysql connection when trying to show master status")
	}
	slaveIp := db.Host()
	slavePort := db.Port()

	ctx, cancel := context.WithTimeout(context.Background(), switchcore.ExecSqlTimeout())
	defer cancel()

	stmts, err := db.ReplStatements(ctx)
	if err != nil {
		return nil, gerrors.Newf(gerrors.Failure,
			"failed to detect the server version on mysql(%s:%d), errmsg: %s", slaveIp, slavePort, err.Error())
	}

	masterStatus := &MasterStatusInfo{}
	err = db.DBWithContext(ctx).Raw(stmts.ShowMasterStatus).Scan(masterStatus).Error
	if err != nil {
		return nil, gerrors.Newf(gerrors.Failure,
			"failed to execute '%s' on mysql(%s:%d), errmsg: %s", stmts.ShowMasterStatus, slaveIp, slavePort, err.Error())
	}
	if masterStatus.File == "" {
		return nil, gerrors.Newf(gerrors.Failure,
			"empty binlog file in the result of '%s' on mysql(%s:%d)", stmts.ShowMasterStatus, slaveIp, slavePort)
	}
	if reportLogf != nil {
		reportLogf(switchlogger.SwitchInfo, "successfully execute '%s' on mysql(%s:%d)",
			stmts.ShowMasterStatus, slaveIp, slavePort)
	}

	return masterStatus, nil
}

// DoResetSlave resets slave replication settings
func DoResetSlave(slaveDB *hamysql.GormDB, reportLogf switchlogger.SwitchLogFunc) error {
	if slaveDB == nil {
		return gerrors.New(gerrors.InvalidParameter, "get nil mysql connection when trying to reset slave")
	}
	slaveIp := slaveDB.Host()
	slavePort := slaveDB.Port()

	ctx, cancel := context.WithTimeout(context.Background(), switchcore.ExecSqlTimeout())
	defer cancel()

	stmts, err := slaveDB.ReplStatements(ctx)
	if err != nil {
		return gerrors.Newf(gerrors.Failure,
			"failed to detect the server version on slave(%s:%d), errmsg: %s", slaveIp, slavePort, err.Error())
	}

	err = slaveDB.DBWithContext(ctx).Exec(stmts.ResetSlaveAll).Error
	if err != nil {
		return gerrors.Newf(gerrors.Failure,
			"failed to execute '%s' on mysql(%s:%d), errmsg: %s", stmts.ResetSlaveAll, slaveIp, slavePort, err.Error())
	}
	if reportLogf != nil {
		reportLogf(switchlogger.SwitchInfo, "successfully execute '%s' on mysql(%s:%d)",
			stmts.ResetSlaveAll, slaveIp, slavePort)
	}

	return nil
}

// DoResetSlaveWithBinlogPos resets slave and gets consistent binlog position
func DoResetSlaveWithBinlogPos(
	slaveIp string,
	slavePort int,
	reportLogf switchlogger.SwitchLogFunc,
) (string, uint64, error) {
	slaveDB, err := hamysql.NewGormDB(
		hamysql.OptionProto(DefaultMySQLProtocol),
		hamysql.OptionIP(slaveIp),
		hamysql.OptionPort(slavePort),
		hamysql.OptionUser(config.Cfg.Database.Mysql.User),
		hamysql.OptionPassword(config.Cfg.Database.Mysql.Password),
		hamysql.OptionTimeout(switchcore.DbConnectTimeout()),
	)
	if err != nil {
		return "", 0, gerrors.Newf(gerrors.Failure,
			"failed to connect mysql slave(%s:%d) when resetting slave: %s", slaveIp, slavePort, err.Error())
	}

	defer slaveDB.Close()

	err = DoStopSlave(slaveDB, reportLogf)
	if err != nil {
		return "", 0, err
	}

	masterStatus := &MasterStatusInfo{}
	masterStatus, err = DoShowMasterStatus(slaveDB, reportLogf)
	if err != nil {
		return "", 0, err
	}

	err = DoResetSlave(slaveDB, reportLogf)
	if err != nil {
		return masterStatus.File, masterStatus.Position, err
	}

	if reportLogf != nil {
		reportLogf(switchlogger.SwitchInfo, "successfully reset slave status for the slave node(%s:%d), "+
			"binlog file: \"%s\", binlog position: %d, executed_gtid_set: \"%s\"",
			slaveIp, slavePort, masterStatus.File, masterStatus.Position, masterStatus.ExecutedGtidSet)
	}

	return masterStatus.File, masterStatus.Position, nil
}

// DoStartSlave starts slave replication
func DoStartSlave(slaveDB *hamysql.GormDB, reportLogf switchlogger.SwitchLogFunc) error {
	if slaveDB == nil {
		return gerrors.New(gerrors.InvalidParameter,
			"get nil mysql connection when trying to start slave")
	}
	slaveIp := slaveDB.Host()
	slavePort := slaveDB.Port()

	ctx, cancel := context.WithTimeout(context.Background(), switchcore.ExecSqlTimeout())
	defer cancel()

	stmts, err := slaveDB.ReplStatements(ctx)
	if err != nil {
		return gerrors.Newf(gerrors.Failure,
			"failed to detect the server version on slave(%s:%d), errmsg: %s", slaveIp, slavePort, err.Error())
	}

	err = slaveDB.DBWithContext(ctx).Exec(stmts.StartSlave).Error
	if err != nil {
		return gerrors.Newf(gerrors.Failure,
			"failed to execute '%s' on slave(%s:%d), errmsg: %s",
			stmts.StartSlave, slaveIp, slavePort, err.Error())
	}
	if reportLogf != nil {
		reportLogf(switchlogger.SwitchInfo,
			"successfully execute '%s' on slave(%s:%d)",
			stmts.StartSlave, slaveIp, slavePort)
	}
	return nil
}

// DoChangeMasterSteps connects to the slave and performs stop slave, change master, start slave.
// The change-master statement is generated per the slave's own server version, falling back
// to the other naming once when the server rejects the syntax.
func DoChangeMasterSteps(
	slaveIp string, slavePort int,
	src hamysql.ReplSource,
	reportLogf switchlogger.SwitchLogFunc,
) error {
	slaveDB, err := hamysql.NewGormDB(
		hamysql.OptionProto(DefaultMySQLProtocol),
		hamysql.OptionIP(slaveIp),
		hamysql.OptionPort(slavePort),
		hamysql.OptionUser(config.Cfg.Database.Mysql.User),
		hamysql.OptionPassword(config.Cfg.Database.Mysql.Password),
		hamysql.OptionTimeout(switchcore.DbConnectTimeout()),
	)
	if err != nil {
		return gerrors.Newf(gerrors.Failure,
			"failed to connect mysql slave(%s:%d) when changing master: %s",
			slaveIp, slavePort, err.Error())
	}
	defer slaveDB.Close()

	if err = DoStopSlave(slaveDB, reportLogf); err != nil {
		return err
	}

	slaveStatus, err := DoShowSlaveStatus(slaveDB, reportLogf)
	if err != nil {
		return err
	}

	if reportLogf != nil {
		reportLogf(switchlogger.SwitchInfo,
			"before switching to the new master node, "+
				"the actual synchronization position of the slave node(%s:%d) is: [binlog_file:%s, binlog_pos:%d]",
			slaveIp, slavePort, slaveStatus.RelayMasterLogFile, slaveStatus.ExecMasterLogPos)
	}

	ctx, cancel := context.WithTimeout(context.Background(), switchcore.ExecSqlTimeout())
	defer cancel()

	changeMasterSQL, err := slaveDB.ChangeReplicationTo(ctx, src)
	if err != nil {
		return err
	}
	if reportLogf != nil {
		reportLogf(switchlogger.SwitchInfo,
			"successfully execute '%s' on node(%s:%d)",
			changeMasterSQL, slaveIp, slavePort)
	}

	if err = DoStartSlave(slaveDB, reportLogf); err != nil {
		return err
	}

	if reportLogf != nil {
		reportLogf(switchlogger.SwitchInfo,
			"successfully changed master for the slave node(%s:%d)",
			slaveIp, slavePort)
	}
	return nil
}

// GetBinlogDumperInfo returns binlog dumper information as string
func GetBinlogDumperInfo(binlogDumperSet []dbm.DbmMetadataBinlogDumper) string {
	if len(binlogDumperSet) == 0 {
		return "nil"
	}

	var dumperInfos []string
	for _, dumper := range binlogDumperSet {
		dumperInfos = append(dumperInfos, fmt.Sprintf("%s:%d", dumper.Ip, dumper.Port))
	}

	return fmt.Sprintf("(%s)", strings.Join(dumperInfos, ","))
}

// GetNewMasterInfo returns the promoted new master info. ok is true only for a master switch
// whose standby slave (the new master) is known.
func (sw *MySQLStorageSwitchInstance) GetNewMasterInfo() (*MySqlNewMasterInfo, bool) {
	if sw.InstanceRole != haprobe.MySQLStorageMaster || sw.StandBySlave == nil {
		return nil, false
	}

	return &MySqlNewMasterInfo{
		Host:       sw.StandBySlave.Ip,
		Port:       sw.StandBySlave.Port,
		BinlogFile: sw.NewMasterBinlogFile,
		BinlogPos:  sw.NewMasterBinlogPos,
	}, true
}
