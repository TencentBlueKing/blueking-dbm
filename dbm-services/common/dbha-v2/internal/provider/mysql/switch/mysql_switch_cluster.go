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

package mysqlswitch

import (
	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/internal/analysis/dbm"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchcore"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchlogger"
	"dbm-services/common/dbha-v2/pkg/converter"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
	"fmt"
)

// NewMySQLSwitchCluster creates a new MySQL switch cluster
func NewMySQLSwitchCluster(clusterKey switchcore.ClusterKey, metadata []*dbm.DbInstMetadata) (switchcore.SwitchableCluster, error) {
	if len(metadata) == 0 {
		return nil, gerrors.Newf(gerrors.InvalidParameter, "empty cluster nodes metadata for key: %s", clusterKey)
	}

	switchInstances := switchcore.InstMetadataMap{}
	for _, inst := range metadata {
		if switchcore.GenerateClusterKey(inst.BkCloudID, inst.ClusterID) != clusterKey {
			return nil, gerrors.Newf(gerrors.InvalidParameter,
				"instance does not belong to the cluster key(%s), inst: %s:%d",
				clusterKey, inst.IP, inst.Port)
		}

		instKey := switchcore.GenerateMetadataKey(inst.BkCloudID, inst.IP, inst.Port)
		if _, exists := switchInstances[instKey]; exists {
			logger.Warn("found duplicate instance in cluster metadata, inst: %s", instKey)
			continue
		}

		switchInstances[instKey] = inst
	}

	base := switchcore.BaseSwitchCluster{
		BkCloudID:       metadata[0].BkCloudID,
		BkBizID:         metadata[0].BkBizID,
		Cluster:         metadata[0].Cluster,
		ClusterID:       metadata[0].ClusterID,
		ClusterType:     metadata[0].ClusterType,
		DbmClient:       &dbm.Client{},
		SwitchInstances: switchInstances,
	}

	mysqlCluster := &MySQLSwitchCluster{
		BaseSwitchCluster: base,
	}
	mysqlCluster.SetStandbySlaveMap()

	return mysqlCluster, nil
}

// MySQLSwitchCluster implements the switchcore.SwitchableCluster interface for MySQL cluster switching
type MySQLSwitchCluster struct {
	switchcore.BaseSwitchCluster

	// standby slave instances
	StandbySlaveMap map[switchcore.MetadataKey]*dbm.DbmMetadataSlaveInfo

	// backend master instances that need to be switched
	BackendMasterKeyList []switchcore.MetadataKey

	// backend slave instances that need to be switched
	BackendSlaveKeyList []switchcore.MetadataKey

	// proxy instances that need to be switched
	ProxyKeyList []switchcore.MetadataKey

	// new master binlog file
	NewMasterBinlogFile string
	// new master binlog position
	NewMasterBinlogPos uint64
}

// SetStandbySlaveMap sets the standby slave map for the cluster
func (cluster *MySQLSwitchCluster) SetStandbySlaveMap() {
	standbySlaveMap := map[switchcore.MetadataKey]*dbm.DbmMetadataSlaveInfo{}
	for instKey, instData := range cluster.SwitchInstances {
		if instData.InstanceRole != haprobe.MySQLStorageMaster {
			continue
		}

		// set standby slave for mysql master
		if len(instData.Receiver) == 0 {
			logger.Warn("no standby slave found from provided slaves for mysql master(%s:%d)", instData.IP, instData.Port)
			continue
		}

		standbySlaveMap[instKey] = &instData.Receiver[0]
		for i := range instData.Receiver {
			if instData.Receiver[i].IsStandBy {
				standbySlaveMap[instKey] = &instData.Receiver[i]
				break
			}
		}

		logger.Debug("successfully set standby slave for mysql master(%s:%d): %s",
			instData.IP, instData.Port, converter.ToStrIgnoreErr(*(standbySlaveMap[instKey])))
	}
	cluster.StandbySlaveMap = standbySlaveMap
}

// CheckMySQLStorageMaster checks if storage master node is required to be switched
func (cluster *MySQLSwitchCluster) CheckMySQLStorageMaster(instKey switchcore.MetadataKey) error {
	instData, exists := cluster.SwitchInstances[instKey]
	if !exists {
		return gerrors.Newf(gerrors.Failure, "mysql backend instance(%s) not found", instKey)
	}

	standbySlave, exists := cluster.StandbySlaveMap[instKey]
	if !exists || (standbySlave == nil) {
		err := gerrors.Newf(gerrors.Failure, "the standby slave is nil")
		cluster.ReportLogf(instKey, switchlogger.SwitchWarn, "%s", err.Error())
		return err
	}

	if standbySlave.Status == dbm.Unavailable {
		err := gerrors.Newf(gerrors.Failure, "the standby slave(%s:%d) is unavailable",
			standbySlave.Ip, standbySlave.Port)
		cluster.ReportLogf(instKey, switchlogger.SwitchWarn, "%s", err.Error())
		return err
	}

	logFunc := func(level switchlogger.SwitchLogLevel, format string, args ...any) bool {
		return cluster.ReportLogf(instKey, level, format, args...)
	}

	slaveChecker := MySQLSlaveChecker{
		MasterIp:     instData.IP,
		MasterPort:   instData.Port,
		MasterStatus: instData.Status,
		SlaveIp:      standbySlave.Ip,
		SlavePort:    standbySlave.Port,
		SlaveStatus:  standbySlave.Status,
		ReportLogf:   logFunc,
	}

	if err := slaveChecker.Check(); err != nil {
		cluster.ReportLogf(instKey, switchlogger.SwitchWarn, "slave status check unpass: %s", err.Error())
		return err
	}

	if len(instData.ProxyInstanceSet) == 0 {
		err := gerrors.Newf(gerrors.Failure, "no proxy instances were found for this storage node")
		cluster.ReportLogf(instKey, switchlogger.SwitchWarn, "%s", err.Error())
		return err
	}

	hasAvailableProxy := false
	for _, proxyInst := range instData.ProxyInstanceSet {
		proxyKey := switchcore.GenerateMetadataKey(instData.BkCloudID, proxyInst.Ip, proxyInst.Port)
		if _, exists := cluster.SwitchInstances[proxyKey]; !exists && (proxyInst.Status != dbm.Unavailable) {
			hasAvailableProxy = true
			break
		}
	}

	if !hasAvailableProxy {
		err := gerrors.Newf(gerrors.Failure, "no available proxy instances were found for this storage node")
		cluster.ReportLogf(instKey, switchlogger.SwitchWarn, "%s", err.Error())
		return err
	}

	return nil
}

// CheckMySQLBackend checks if backend node is required to be switched
func (cluster *MySQLSwitchCluster) CheckMySQLBackend(instKey switchcore.MetadataKey) error {
	instData, exists := cluster.SwitchInstances[instKey]
	if !exists {
		return gerrors.Newf(gerrors.Failure, "mysql backend instance(%s) not found", instKey)
	}

	switch instData.InstanceRole {
	case haprobe.MySQLStorageSlave:
		cluster.BackendSlaveKeyList = append(cluster.BackendSlaveKeyList, instKey)
		cluster.ReportLogf(instKey, switchlogger.SwitchInfo,
			"check result before switch: switch required, this is a slave node")
		return nil

	case haprobe.MySQLStorageRepeater:
		cluster.ReportLogf(instKey, switchlogger.SwitchWarn,
			"check result before switch: no need to switch, dbha doesn't support repeater")
		return nil

	case haprobe.MySQLStorageMaster:
		if err := cluster.CheckMySQLStorageMaster(instKey); err != nil {
			return err
		}
		cluster.BackendMasterKeyList = append(cluster.BackendMasterKeyList, instKey)
		cluster.ReportLogf(instKey, switchlogger.SwitchInfo,
			"check result before switch: switch required, this is a master node")
		return nil

	default:
		err := gerrors.Newf(gerrors.Failure, "invalid instance role: %s", instData.InstanceRole)
		cluster.ReportLogf(instKey, switchlogger.SwitchWarn, "%s", err.Error())
		return err
	}
}

// HasSwitchRequiredNode returns true if there are any nodes that are required to be switched
func (cluster *MySQLSwitchCluster) HasSwitchRequiredNode() bool {
	return (len(cluster.BackendMasterKeyList) > 0) ||
		(len(cluster.BackendSlaveKeyList) > 0) ||
		(len(cluster.ProxyKeyList) > 0)
}

// SwitchRequiredNodes returns the nodes that are required to be switched
func (cluster *MySQLSwitchCluster) SwitchRequiredNodes() []switchcore.MetadataKey {
	nodes := []switchcore.MetadataKey{}
	nodes = append(nodes, cluster.BackendMasterKeyList...)
	nodes = append(nodes, cluster.BackendSlaveKeyList...)
	nodes = append(nodes, cluster.ProxyKeyList...)
	return nodes
}

// CheckBeforeSwitch checks if the cluster is required to be switched
// Note: no per-instance parallelism here; only the backend master check is materially expensive.
func (cluster *MySQLSwitchCluster) CheckBeforeSwitch() (switchcore.SwitchCheckCode, error) {
	cluster.BackendMasterKeyList = []switchcore.MetadataKey{}
	cluster.BackendSlaveKeyList = []switchcore.MetadataKey{}
	cluster.ProxyKeyList = []switchcore.MetadataKey{}
	checkUnpassKeyList := []switchcore.MetadataKey{}

	for instKey, instData := range cluster.SwitchInstances {
		switch instData.MachineType {
		case haprobe.DbmMetadataMachineTypeProxy:
			cluster.ProxyKeyList = append(cluster.ProxyKeyList, instKey)
			cluster.ReportLogf(instKey, switchlogger.SwitchInfo,
				"check result before switch: switch required, this is a proxy node")

		case haprobe.DbmMetadataMachineTypeBackend:
			if err := cluster.CheckMySQLBackend(instKey); err != nil {
				checkUnpassKeyList = append(checkUnpassKeyList, instKey)
				cluster.ReportLogf(instKey, switchlogger.SwitchError, "check result before switch: check unpass, %s", err.Error())
			}

		default:
			checkUnpassKeyList = append(checkUnpassKeyList, instKey)
			cluster.ReportLogf(instKey, switchlogger.SwitchError,
				"check result before switch: check unpass, invalid machine type(%s)", instData.MachineType)
		}
	}

	if len(checkUnpassKeyList) > 0 {
		return switchcore.SwitchCheckUnpass, gerrors.Newf(gerrors.Failure,
			"some instances unpass the check before switch: [%s]", switchcore.JoinMetadataKeys(checkUnpassKeyList, ", "))
	}

	if !cluster.HasSwitchRequiredNode() {
		cluster.ReportClusterLogf(switchlogger.SwitchInfo, "all instances in the cluster are not required to be switched")
		return switchcore.SwitchNotNeeded, nil
	}

	cluster.ReportClusterLogf(switchlogger.SwitchInfo, "after checking, those nodes are required to be switched: "+
		"backend master: [%s], backend slave: [%s], proxy: [%s]",
		switchcore.JoinMetadataKeys(cluster.BackendMasterKeyList, ", "),
		switchcore.JoinMetadataKeys(cluster.BackendSlaveKeyList, ", "),
		switchcore.JoinMetadataKeys(cluster.ProxyKeyList, ", "))

	return switchcore.SwitchRequired, nil
}

// DeleteProxyNameService deletes the name service for the proxy instances
func (cluster *MySQLSwitchCluster) DeleteProxyNameService() error {
	if len(cluster.ProxyKeyList) == 0 {
		cluster.ReportClusterLogf(switchlogger.SwitchInfo, "no proxy instances to delete name service")
		return nil
	}

	failedProxyKeyList := []switchcore.MetadataKey{}
	for _, instKey := range cluster.ProxyKeyList {
		if err := cluster.DeleteOneInstanceNameService(instKey); err != nil {
			failedProxyKeyList = append(failedProxyKeyList, instKey)
			cluster.ReportLogf(instKey, switchlogger.SwitchWarn,
				"failed to delete name service, proxy: %s, errmsg: %s", instKey, err.Error())
		}
	}

	if len(failedProxyKeyList) > 0 {
		return gerrors.Newf(gerrors.Failure, "failed to delete name service for some proxy instances: %s",
			switchcore.JoinMetadataKeys(failedProxyKeyList, ", "))
	}

	cluster.ReportClusterLogf(switchlogger.SwitchInfo, "successfully delete name service for all proxy instances")
	return nil
}

// DeleteBackendNameService deletes the name service for the backend slave instances
func (cluster *MySQLSwitchCluster) DeleteBackendNameService() error {
	if len(cluster.BackendSlaveKeyList) == 0 {
		cluster.ReportClusterLogf(switchlogger.SwitchInfo, "no backend slave instances to delete name service")
		return nil
	}

	failedBackendKeyList := []switchcore.MetadataKey{}
	for _, instKey := range cluster.BackendSlaveKeyList {
		instData, exists := cluster.SwitchInstances[instKey]
		if !exists {
			continue
		}

		if instData.IsStandBy {
			cluster.ReportLogf(instKey, switchlogger.SwitchInfo, "skip deleting name service for the standby slave")
			continue
		}

		if err := cluster.DeleteOneInstanceNameService(instKey); err != nil {
			failedBackendKeyList = append(failedBackendKeyList, instKey)
			cluster.ReportLogf(instKey, switchlogger.SwitchWarn,
				"failed to delete name service, backend: %s, errmsg: %s", instKey, err.Error())
		}
	}

	if len(failedBackendKeyList) > 0 {
		return gerrors.Newf(gerrors.Failure, "failed to delete name service for some backend slave instances: %s",
			switchcore.JoinMetadataKeys(failedBackendKeyList, ", "))
	}

	cluster.ReportClusterLogf(switchlogger.SwitchInfo, "successfully delete name service for all backend slave instances")
	return nil
}

// GetAvailableProxies gets the available proxy instances from the first master instance
func (cluster *MySQLSwitchCluster) GetAvailableProxies(oneMasterKey switchcore.MetadataKey) (
	[]dbm.DbmMetadataProxyInstance, error) {
	masterData, exists := cluster.SwitchInstances[oneMasterKey]
	if !exists {
		retErr := gerrors.Newf(gerrors.Failure,
			"failed to get available proxies, master instance(%s) not found", oneMasterKey)
		cluster.ReportLogf(oneMasterKey, switchlogger.SwitchWarn, "%s", retErr.Error())
		return nil, retErr
	}

	if len(masterData.ProxyInstanceSet) == 0 {
		retErr := gerrors.Newf(gerrors.Failure,
			"failed to get available proxies, no proxy instances were found for master instance(%s)", oneMasterKey)
		cluster.ReportLogf(oneMasterKey, switchlogger.SwitchWarn, "%s", retErr.Error())
		return nil, retErr
	}

	availableProxies := []dbm.DbmMetadataProxyInstance{}
	availableProxyKeys := []switchcore.MetadataKey{}
	for _, proxyInst := range masterData.ProxyInstanceSet {
		proxyKey := switchcore.GenerateMetadataKey(masterData.BkCloudID, proxyInst.Ip, proxyInst.Port)
		if _, exists := cluster.SwitchInstances[proxyKey]; exists || (proxyInst.Status == dbm.Unavailable) {
			continue
		}

		availableProxies = append(availableProxies, proxyInst)
		availableProxyKeys = append(availableProxyKeys, proxyKey)
	}

	if len(availableProxies) == 0 {
		retErr := gerrors.Newf(gerrors.Failure,
			"failed to get available proxies, no available proxy instances were found for master instance(%s)", oneMasterKey)
		cluster.ReportLogf(oneMasterKey, switchlogger.SwitchWarn, "%s", retErr.Error())
		return nil, retErr
	}

	cluster.ReportLogf(oneMasterKey, switchlogger.SwitchInfo, "successfully get available proxy instances: [%s]",
		switchcore.JoinMetadataKeys(availableProxyKeys, ", "))
	return availableProxies, nil
}

// RefreshProxiesBackends refreshes the backends of the proxies to the new master
//  1. update all available proxies' backends to 1.1.1.1 first
//  2. reset slave status for the standby slave and get its
//     consistent synchronization position(binlog file and binlog position)
//  3. refresh all proxies' backends to the alive mysql(standby slave)
func (cluster *MySQLSwitchCluster) RefreshProxiesBackends() error {
	proxyUser := config.Cfg.Database.Mysql.ProxyUser
	proxyPasswd := config.Cfg.Database.Mysql.ProxyPassword

	if len(cluster.BackendMasterKeyList) == 0 {
		cluster.ReportClusterLogf(switchlogger.SwitchWarn, "no backend master instances to refresh proxies' backends")
		return nil
	}

	masterKey := cluster.BackendMasterKeyList[0]
	availableProxies, err := cluster.GetAvailableProxies(masterKey)
	if err != nil {
		return err
	}

	logFunc := func(level switchlogger.SwitchLogLevel, format string, args ...any) bool {
		return cluster.ReportLogf(masterKey, level, format, args...)
	}

	cluster.ReportLogf(masterKey, switchlogger.SwitchInfo, "update all available proxies' backends to 1.1.1.1 first")
	for _, proxyIns := range availableProxies {
		if err := ProxyRefreshBackends(proxyIns.Ip, proxyIns.AdminPort, proxyUser, proxyPasswd,
			"1.1.1.1", 3306, logFunc); err != nil {
			retErr := gerrors.Newf(gerrors.Failure,
				"failed to refresh backends to 1.1.1.1 for the proxy(%s:%d), errmsg: %s",
				proxyIns.Ip, proxyIns.AdminPort, err.Error())
			cluster.ReportLogf(masterKey, switchlogger.SwitchWarn, "%s", retErr.Error())
			return retErr
		}
	}
	cluster.ReportLogf(masterKey, switchlogger.SwitchInfo,
		"successfully update all available proxies' backends to 1.1.1.1")

	cluster.ReportLogf(masterKey, switchlogger.SwitchInfo, "reset slave status for the standby slave")
	standbySlave, exists := cluster.StandbySlaveMap[masterKey]
	if !exists || (standbySlave == nil) {
		err := gerrors.Newf(gerrors.Failure, "the standby slave is nil")
		cluster.ReportLogf(masterKey, switchlogger.SwitchWarn, "%s", err.Error())
		return err
	}

	binlogFile, binlogPosition, execErr := DoResetSlaveWithBinlogPos(standbySlave.Ip, standbySlave.Port, logFunc)
	if execErr != nil {
		retErr := gerrors.Newf(gerrors.Failure, "failed to reset slave status for the standby slave(%s:%d), errmsg: %s",
			standbySlave.Ip, standbySlave.Port, execErr.Error())
		cluster.ReportLogf(masterKey, switchlogger.SwitchWarn, "%s", retErr.Error())
		return retErr
	}

	cluster.NewMasterBinlogFile = binlogFile
	cluster.NewMasterBinlogPos = binlogPosition

	cluster.ReportLogf(masterKey, switchlogger.SwitchInfo, "update all proxies' backends to the new master")
	for _, proxyIns := range availableProxies {
		if err := ProxyRefreshBackends(proxyIns.Ip, proxyIns.AdminPort, proxyUser, proxyPasswd,
			standbySlave.Ip, standbySlave.Port, logFunc); err != nil {
			retErr := gerrors.Newf(gerrors.Failure,
				"failed to refresh backends to (%s:%d) for the proxy(%s:%d), errmsg: %s",
				standbySlave.Ip, standbySlave.Port, proxyIns.Ip, proxyIns.AdminPort, err.Error())
			cluster.ReportLogf(masterKey, switchlogger.SwitchWarn, "%s", retErr.Error())
			return retErr
		}
	}
	cluster.ReportLogf(masterKey, switchlogger.SwitchInfo,
		"successfully update all available proxies' backends to the new master")

	return nil
}

// GetNewMasterInfos returns the new master info keyed by the switched backend master instance.
func (cluster *MySQLSwitchCluster) GetNewMasterInfos() map[switchcore.MetadataKey]*switchcore.NewMasterInfo {
	res := map[switchcore.MetadataKey]*switchcore.NewMasterInfo{}
	for _, masterKey := range cluster.BackendMasterKeyList {
		standbySlave, exists := cluster.StandbySlaveMap[masterKey]
		if !exists || standbySlave == nil {
			continue
		}

		res[masterKey] = &switchcore.NewMasterInfo{
			Host:       standbySlave.Ip,
			Port:       standbySlave.Port,
			BinlogFile: cluster.NewMasterBinlogFile,
			BinlogPos:  cluster.NewMasterBinlogPos,
		}
	}

	return res
}

// DoSwitch switches the required nodes in the cluster
//  1. deletes proxy instances from all bound entries
//  2. delete non-standby slave backends from all bound entries
//  3. refresh all proxies' backends to the alive mysql(standby slave)
func (cluster *MySQLSwitchCluster) DoSwitch() error {
	cluster.ReportClusterLogf(switchlogger.SwitchInfo, "switch step 1: delete proxy instances from all bound entries")
	if err := cluster.DeleteProxyNameService(); err != nil {
		return err
	}

	cluster.ReportClusterLogf(switchlogger.SwitchInfo,
		"switch step 2: delete non-standby slave backends from all bound entries")
	if err := cluster.DeleteBackendNameService(); err != nil {
		return err
	}

	cluster.ReportClusterLogf(switchlogger.SwitchInfo, "switch step 3: refresh all proxies' backends to the new master")
	if err := cluster.RefreshProxiesBackends(); err != nil {
		return err
	}

	return nil
}

// UpdateMetaInfo updates the meta info for the backend nodes
func (cluster *MySQLSwitchCluster) UpdateMetaInfo() error {
	failedInstKeyList := []switchcore.MetadataKey{}
	switchRequiredNodes := cluster.SwitchRequiredNodes()

	for _, instKey := range switchRequiredNodes {
		instData, exists := cluster.SwitchInstances[instKey]
		if !exists {
			continue
		}

		if instData.InstanceRole != haprobe.MySQLStorageMaster {
			cluster.ReportLogf(instKey, switchlogger.SwitchInfo,
				"nothing to do for the instance role(%s) when updating meta info", instData.InstanceRole)
			continue
		}

		standbySlave, exists := cluster.StandbySlaveMap[instKey]
		if !exists || (standbySlave == nil) {
			err := gerrors.Newf(gerrors.Failure, "the standby slave is nil")
			cluster.ReportLogf(instKey, switchlogger.SwitchWarn, "%s", err.Error())
			failedInstKeyList = append(failedInstKeyList, instKey)
			continue
		}

		if err := cluster.DbmClient.SwapMySQLRole(cluster.BkCloudID, instData.IP, instData.Port,
			standbySlave.Ip, standbySlave.Port); err != nil {
			errMsg := fmt.Sprintf("failed to swap roles of backend nodes(master:%s:%d, slave:%s:%d), errmsg:%s",
				instData.IP, instData.Port, standbySlave.Ip, standbySlave.Port, err.Error())
			cluster.ReportLogf(instKey, switchlogger.SwitchWarn, "%s", errMsg)
			failedInstKeyList = append(failedInstKeyList, instKey)
			continue
		}

		cluster.ReportLogf(instKey, switchlogger.SwitchInfo,
			"successfully swap roles of backend nodes(master:%s:%d, slave:%s:%d)",
			instData.IP, instData.Port, standbySlave.Ip, standbySlave.Port)
	}

	if len(failedInstKeyList) > 0 {
		return gerrors.Newf(gerrors.Failure, "failed to update meta info for some backend nodes: %s",
			switchcore.JoinMetadataKeys(failedInstKeyList, ", "))
	}

	return nil
}

// DoFinal performs final operations after switch completion
func (cluster *MySQLSwitchCluster) DoFinal() error {
	failedInstKeyList := []switchcore.MetadataKey{}
	switchRequiredNodes := cluster.SwitchRequiredNodes()

	for _, instKey := range switchRequiredNodes {
		instData, exists := cluster.SwitchInstances[instKey]
		if !exists {
			continue
		}

		if instData.InstanceRole != haprobe.MySQLStorageMaster {
			cluster.ReportLogf(instKey, switchlogger.SwitchInfo, "nothing to do for the instance role(%s) when doing final step",
				instData.InstanceRole)
			continue
		}

		cluster.ReportLogf(instKey, switchlogger.SwitchInfo, "tbinlogdumpers info of current mysql: %s",
			GetBinlogDumperInfo(instData.BinlogDumpers))

		if len(instData.BinlogDumpers) == 0 {
			cluster.ReportLogf(instKey, switchlogger.SwitchInfo, "no need to switch tbinlogdumper for current mysql")
			continue
		}

		switchInstances := []dbm.DumperSwitchInstance{}
		for _, dumper := range instData.BinlogDumpers {
			switchInstances = append(switchInstances, dbm.DumperSwitchInstance{
				Ip:             dumper.Ip,
				Port:           dumper.Port,
				BinlogFile:     cluster.NewMasterBinlogFile,
				BinlogPosition: cluster.NewMasterBinlogPos,
			})
		}

		SwitchInfos := []dbm.DumperSwitchInfo{
			{
				ClusterDomain:   cluster.Cluster,
				SwitchInstances: switchInstances,
			},
		}

		if err := cluster.DbmClient.SwitchBinlogDumper(cluster.BkCloudID, cluster.GetApp(), SwitchInfos); err != nil {
			errMsg := fmt.Sprintf("failed to switch all tbinlogdumpers for current mysql, errmsg: %s",
				err.Error())
			cluster.ReportLogf(instKey, switchlogger.SwitchWarn, "%s", errMsg)
			failedInstKeyList = append(failedInstKeyList, instKey)
			continue
		}

		cluster.ReportLogf(instKey, switchlogger.SwitchInfo, "successfully switch all tbinlogdumpers for current mysql")
	}

	if len(failedInstKeyList) > 0 {
		return gerrors.Newf(gerrors.Failure, "failed to do final step for some broken nodes: %s",
			switchcore.JoinMetadataKeys(failedInstKeyList, ", "))
	}

	return nil
}
