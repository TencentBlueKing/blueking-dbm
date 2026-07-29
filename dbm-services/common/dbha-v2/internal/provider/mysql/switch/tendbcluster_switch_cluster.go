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
	"fmt"
	"sync"

	"dbm-services/common/dbha-v2/internal/analysis/dbm"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchcore"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchlogger"
	"dbm-services/common/dbha-v2/pkg/converter"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// NewTenDBClusterSwitchCluster creates a new TenDBCluster switch cluster
func NewTenDBClusterSwitchCluster(
	clusterKey switchcore.ClusterKey, metadata []*dbm.DbInstMetadata,
) (switchcore.SwitchableCluster, error) {
	if len(metadata) == 0 {
		return nil, gerrors.Newf(gerrors.InvalidParameter,
			"empty cluster nodes metadata for key: %s", clusterKey)
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

	cluster := &TenDBClusterSwitchCluster{
		BaseSwitchCluster: base,
	}
	cluster.SetStandbySlaveMap()

	return cluster, nil
}

// TenDBClusterSwitchCluster implements switchcore.SwitchableCluster for TenDBCluster
type TenDBClusterSwitchCluster struct {
	switchcore.BaseSwitchCluster

	tdbctlHelper TdbctlOperator

	// standby slave instances for remote masters
	StandbySlaveMap map[switchcore.MetadataKey]*dbm.DbmMetadataSlaveInfo

	// spider instances that need to be switched
	SpiderKeyList []switchcore.MetadataKey
	// remote master instances that need to be switched
	RemoteMasterKeyList []switchcore.MetadataKey
	// remote slave instances that need to be switched
	RemoteSlaveKeyList []switchcore.MetadataKey

	// keyListMu guards concurrent appends to SpiderKeyList, RemoteMasterKeyList, and RemoteSlaveKeyList
	keyListMu sync.Mutex

	// newMasterInfoMap records the new master info keyed by the switched remote master instance
	newMasterInfoMap map[switchcore.MetadataKey]*switchcore.NewMasterInfo
	// newMasterInfoMu guards concurrent writes to newMasterInfoMap
	newMasterInfoMu sync.Mutex
}

// SetStandbySlaveMap sets the standby slave map from remote master metadata
func (cluster *TenDBClusterSwitchCluster) SetStandbySlaveMap() {
	standbySlaveMap := map[switchcore.MetadataKey]*dbm.DbmMetadataSlaveInfo{}
	for instKey, instData := range cluster.SwitchInstances {
		if instData.InstanceRole != haprobe.TenDBClusterStorageMaster {
			continue
		}

		if len(instData.Receiver) == 0 {
			logger.Warn("no standby slave found for remote master(%s:%d)",
				instData.IP, instData.Port)
			continue
		}

		standbySlaveMap[instKey] = &instData.Receiver[0]
		for i := range instData.Receiver {
			if instData.Receiver[i].IsStandBy {
				standbySlaveMap[instKey] = &instData.Receiver[i]
				break
			}
		}

		logger.Debug("successfully set standby slave for remote master(%s:%d): %s",
			instData.IP, instData.Port,
			converter.ToStrIgnoreErr(*(standbySlaveMap[instKey])))
	}
	cluster.StandbySlaveMap = standbySlaveMap
}

// HasSwitchRequiredNode returns true if there are any nodes that need switching
func (cluster *TenDBClusterSwitchCluster) HasSwitchRequiredNode() bool {
	return (len(cluster.SpiderKeyList) > 0) ||
		(len(cluster.RemoteMasterKeyList) > 0) ||
		(len(cluster.RemoteSlaveKeyList) > 0)
}

// SwitchRequiredNodes returns all node keys that need switching
func (cluster *TenDBClusterSwitchCluster) SwitchRequiredNodes() []switchcore.MetadataKey {
	nodes := []switchcore.MetadataKey{}
	nodes = append(nodes, cluster.SpiderKeyList...)
	nodes = append(nodes, cluster.RemoteMasterKeyList...)
	nodes = append(nodes, cluster.RemoteSlaveKeyList...)
	return nodes
}

// appendKey appends k to SpiderKeyList, RemoteMasterKeyList, or RemoteSlaveKeyList (caller passes slice field address).
func (cluster *TenDBClusterSwitchCluster) appendKey(slice *[]switchcore.MetadataKey, k switchcore.MetadataKey) {
	cluster.keyListMu.Lock()
	*slice = append(*slice, k)
	cluster.keyListMu.Unlock()
}

// CheckRemoteMaster checks if remote master node satisfies switching conditions
func (cluster *TenDBClusterSwitchCluster) CheckRemoteMaster(
	instKey switchcore.MetadataKey,
) error {
	instData, exists := cluster.SwitchInstances[instKey]
	if !exists {
		return gerrors.Newf(gerrors.Failure,
			"remote master instance(%s) not found", instKey)
	}

	standbySlave, exists := cluster.StandbySlaveMap[instKey]
	if !exists || (standbySlave == nil) {
		err := gerrors.Newf(gerrors.Failure, "the standby slave is nil")
		cluster.ReportLogf(instKey, switchlogger.SwitchWarn, "%s", err.Error())
		return err
	}

	if standbySlave.Status == dbm.Unavailable {
		err := gerrors.Newf(gerrors.Failure,
			"the standby slave(%s:%d) is unavailable",
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
		cluster.ReportLogf(instKey, switchlogger.SwitchWarn,
			"slave status check unpass: %s", err.Error())
		return err
	}

	if len(instData.ProxyInstanceSet) == 0 {
		err := gerrors.Newf(gerrors.Failure,
			"no spider instances were found for this remote master")
		cluster.ReportLogf(instKey, switchlogger.SwitchWarn, "%s", err.Error())
		return err
	}

	return nil
}

// checkRemoteNode classifies a remote backend node and checks if it needs switching.
// Writes to RemoteMasterKeyList use appendKey under keyListMu.
func (cluster *TenDBClusterSwitchCluster) checkRemoteNode(instKey switchcore.MetadataKey) error {
	instData, exists := cluster.SwitchInstances[instKey]
	if !exists {
		return gerrors.Newf(gerrors.Failure,
			"remote backend instance(%s) not found", instKey)
	}

	switch instData.InstanceRole {
	// Notice: remote slave node is not required to be switched
	case haprobe.TenDBClusterStorageSlave:
		// cluster.RemoteSlaveKeyList = append(cluster.RemoteSlaveKeyList, instKey)
		cluster.ReportLogf(instKey, switchlogger.SwitchInfo,
			"check result before switch: no need to switch, this is a remote slave node")
		return nil

	case haprobe.TenDBClusterStorageMaster:
		if err := cluster.CheckRemoteMaster(instKey); err != nil {
			return err
		}
		cluster.appendKey(&cluster.RemoteMasterKeyList, instKey)
		cluster.ReportLogf(instKey, switchlogger.SwitchInfo,
			"check result before switch: switch required, this is a remote master node")
		return nil

	default:
		err := gerrors.Newf(gerrors.Failure,
			"invalid instance role: %s", instData.InstanceRole)
		cluster.ReportLogf(instKey, switchlogger.SwitchWarn, "%s", err.Error())
		return err
	}
}

// CheckBeforeSwitch classifies all broken instances and validates switching conditions
func (cluster *TenDBClusterSwitchCluster) CheckBeforeSwitch() (switchcore.SwitchCheckCode, error) {
	cluster.SpiderKeyList = []switchcore.MetadataKey{}
	cluster.RemoteMasterKeyList = []switchcore.MetadataKey{}
	cluster.RemoteSlaveKeyList = []switchcore.MetadataKey{}

	var wg sync.WaitGroup
	maxInstanceConcurrency := switchcore.ClusterLevelSwitchMaxInstanceConcurrency()
	sem := make(chan struct{}, maxInstanceConcurrency)
	failCh := make(chan switchcore.MetadataKey, len(cluster.SwitchInstances))

	for instKey, instData := range cluster.SwitchInstances {
		wg.Add(1)
		go func(instKey switchcore.MetadataKey, instData *dbm.DbInstMetadata) {
			defer wg.Done()
			sem <- struct{}{}
			defer func() { <-sem }()

			switch instData.MachineType {
			case haprobe.DbmMetadataMachineTypeSpider:
				cluster.appendKey(&cluster.SpiderKeyList, instKey)
				cluster.ReportLogf(instKey, switchlogger.SwitchInfo,
					"check result before switch: switch required, this is a spider node, spider role: %s",
					instData.SpiderRole)

			case haprobe.DbmMetadataMachineTypeRemote:
				if err := cluster.checkRemoteNode(instKey); err != nil {
					failCh <- instKey
					cluster.ReportLogf(instKey, switchlogger.SwitchError,
						"check result before switch: check unpass, %s", err.Error())
					return
				}

			default:
				failCh <- instKey
				cluster.ReportLogf(instKey, switchlogger.SwitchError,
					"check result before switch: check unpass, invalid machine type(%s)",
					instData.MachineType)
			}
		}(instKey, instData)
	}
	wg.Wait()
	close(failCh)

	checkUnpassKeyList := make([]switchcore.MetadataKey, 0, len(cluster.SwitchInstances))
	for k := range failCh {
		checkUnpassKeyList = append(checkUnpassKeyList, k)
	}

	if len(checkUnpassKeyList) > 0 {
		return switchcore.SwitchCheckUnpass, gerrors.Newf(gerrors.Failure,
			"some instances unpass the check before switch: [%s]",
			switchcore.JoinMetadataKeys(checkUnpassKeyList, ", "))
	}

	if !cluster.HasSwitchRequiredNode() {
		cluster.ReportClusterLogf(switchlogger.SwitchInfo,
			"all instances in the cluster are not required to be switched")
		return switchcore.SwitchNotNeeded, nil
	}

	cluster.ReportClusterLogf(switchlogger.SwitchInfo, "after checking, those nodes are required to be switched: "+
		"spider: [%s], remote master: [%s], remote slave: [%s]",
		switchcore.JoinMetadataKeys(cluster.SpiderKeyList, ", "),
		switchcore.JoinMetadataKeys(cluster.RemoteMasterKeyList, ", "),
		switchcore.JoinMetadataKeys(cluster.RemoteSlaveKeyList, ", "))

	return switchcore.SwitchRequired, nil
}

// DeleteSpiderNameService deletes DNS/CLB/Polaris entries for broken spider instances
func (cluster *TenDBClusterSwitchCluster) DeleteSpiderNameService() error {
	if len(cluster.SpiderKeyList) == 0 {
		cluster.ReportClusterLogf(switchlogger.SwitchInfo,
			"no spider instances to delete name service")
		return nil
	}

	maxInstanceConcurrency := switchcore.ClusterLevelSwitchMaxInstanceConcurrency()
	sem := make(chan struct{}, maxInstanceConcurrency)
	failCh := make(chan switchcore.MetadataKey, len(cluster.SpiderKeyList))
	var wg sync.WaitGroup

	for _, instKey := range cluster.SpiderKeyList {
		wg.Add(1)
		go func(instKey switchcore.MetadataKey) {
			defer wg.Done()
			sem <- struct{}{}
			defer func() { <-sem }()

			if err := cluster.DeleteOneInstanceNameService(instKey); err != nil {
				failCh <- instKey
				cluster.ReportLogf(instKey, switchlogger.SwitchWarn,
					"failed to delete name service, spider: %s, errmsg: %s",
					instKey, err.Error())
			}
		}(instKey)
	}
	wg.Wait()
	close(failCh)

	failedKeyList := make([]switchcore.MetadataKey, 0, len(cluster.SpiderKeyList))
	for k := range failCh {
		failedKeyList = append(failedKeyList, k)
	}

	if len(failedKeyList) > 0 {
		return gerrors.Newf(gerrors.Failure,
			"failed to delete name service for some spider instances: %s",
			switchcore.JoinMetadataKeys(failedKeyList, ", "))
	}

	cluster.ReportClusterLogf(switchlogger.SwitchInfo,
		"successfully delete name service for all spider instances")
	return nil
}

// DoSwitch performs the actual cluster switching logic for TenDBCluster.
//  1. deletes spider/spider_slave instances from bound entries
//  2. query all spider/tdbctl nodes of this cluster from DBM
//  3. query all tdbctl nodes' status from any valid tdbctl node
//  4. found primary tdbctl
//  5. change primary tdbctl if the primary tdbctl belongs to any broken spider
//  6. connect primary tdbctl
//  7. query route table from primary tdbctl
//  8. delete broken-down spider/spider_slave/tdbctl nodes from primary-tdbctl route table
//  9. reset slaves and update route info for broken remote masters
//  10. flush route table
func (cluster *TenDBClusterSwitchCluster) DoSwitch() error {
	cluster.initTdbctlHelper()

	cluster.ReportClusterLogf(switchlogger.SwitchInfo,
		"switch step 1: delete spider/spider_slave instances from bound entries")
	if err := cluster.DeleteSpiderNameService(); err != nil {
		return err
	}

	cluster.ReportClusterLogf(switchlogger.SwitchInfo,
		"switch step 2: query all spider/tdbctl nodes of this cluster from DBM")
	if err := cluster.tdbctlHelper.QuerySpiderNodesOfCluster(cluster.DbmClient); err != nil {
		return err
	}

	cluster.ReportClusterLogf(switchlogger.SwitchInfo,
		"switch step 3: query all tdbctl nodes' status from any valid tdbctl node")
	if err := cluster.tdbctlHelper.QueryTdbctlNodesOfCluster(); err != nil {
		return err
	}

	cluster.ReportClusterLogf(switchlogger.SwitchInfo, "switch step 4: find the primary tdbctl")
	if err := cluster.tdbctlHelper.FindPrimaryTdbctl(); err != nil {
		return err
	}

	cluster.ReportClusterLogf(switchlogger.SwitchInfo,
		"switch step 5: change primary tdbctl if it belongs to any broken spider")
	if err := cluster.tdbctlHelper.HandleInvolvedPrimaryTdbctl(); err != nil {
		return err
	}

	cluster.ReportClusterLogf(switchlogger.SwitchInfo, "switch step 6: connect primary tdbctl")
	if cluster.tdbctlHelper.PrimaryTdbctl == nil {
		return gerrors.New(gerrors.Failure, "primary tdbctl is nil when connecting to primary tdbctl")
	}
	primaryTdbctlConn, connErr := cluster.tdbctlHelper.ConnectTdbctlNode(
		cluster.tdbctlHelper.PrimaryTdbctl.Host,
		cluster.tdbctlHelper.PrimaryTdbctl.Port)
	if connErr != nil {
		return connErr
	}
	defer primaryTdbctlConn.Close()

	cluster.ReportClusterLogf(switchlogger.SwitchInfo, "switch step 7: query route table from primary tdbctl")
	if err := cluster.tdbctlHelper.QueryRouteInfoOfCluster(primaryTdbctlConn); err != nil {
		return err
	}

	cluster.ReportClusterLogf(switchlogger.SwitchInfo,
		"switch step 8: delete broken spider/spider_slave/tdbctl nodes from route table")
	if err := cluster.dropAllBrokenSpiderRoutes(primaryTdbctlConn); err != nil {
		return err
	}

	cluster.ReportClusterLogf(switchlogger.SwitchInfo,
		"switch step 9: reset slaves and update route info for broken remote masters")
	if err := cluster.switchRemoteMasters(primaryTdbctlConn); err != nil {
		return err
	}

	cluster.ReportClusterLogf(switchlogger.SwitchInfo, "switch step 10: flush route table")
	if err := cluster.tdbctlHelper.TdbctlFlushRouting(primaryTdbctlConn, true); err != nil {
		return err
	}

	return nil
}

// initTdbctlHelper initializes the tdbctl helper with broken spider master info
func (cluster *TenDBClusterSwitchCluster) initTdbctlHelper() {
	brokenSpiderMasters := []BrokenSpiderMasterInfo{}
	for _, instKey := range cluster.SpiderKeyList {
		instData, exists := cluster.SwitchInstances[instKey]
		if !exists || (instData.SpiderRole != haprobe.TenDBClusterSpiderMaster) {
			continue
		}
		brokenSpiderMasters = append(brokenSpiderMasters, BrokenSpiderMasterInfo{
			BkCloudID: instData.BkCloudID,
			IP:        instData.IP,
			Port:      instData.Port,
			AdminPort: instData.AdminPort,
		})
	}
	cluster.tdbctlHelper.Init(
		cluster.Cluster, cluster.BkCloudID,
		brokenSpiderMasters, cluster.ReportClusterLogf)
}

// dropAllBrokenSpiderRoutes drops route items for all broken spider instances
func (cluster *TenDBClusterSwitchCluster) dropAllBrokenSpiderRoutes(
	primaryTdbctlConn *hamysql.GormDB,
) error {
	originalLogFunc := cluster.tdbctlHelper.GetLogFunc()
	defer cluster.tdbctlHelper.SetLogFunc(originalLogFunc)

	failedKeyList := []switchcore.MetadataKey{}

	if len(cluster.SpiderKeyList) == 0 {
		cluster.ReportClusterLogf(switchlogger.SwitchInfo,
			"no broken spider instances to drop")
		return nil
	}

	for _, instKey := range cluster.SpiderKeyList {
		instData, exists := cluster.SwitchInstances[instKey]
		if !exists {
			cluster.ReportLogf(instKey, switchlogger.SwitchWarn,
				"failed to get spider instance(%s) metadata when trying to drop it", instKey)
			failedKeyList = append(failedKeyList, instKey)
			continue
		}

		instLogFunc := func(level switchlogger.SwitchLogLevel, format string, args ...any) bool {
			return cluster.ReportLogf(instKey, level, format, args...)
		}
		cluster.tdbctlHelper.SetLogFunc(instLogFunc)

		if err := cluster.tdbctlHelper.DropBrokenSpiderRoutes(
			primaryTdbctlConn, instData.IP, instData.Port, instData.AdminPort,
			instData.SpiderRole,
		); err != nil {
			failedKeyList = append(failedKeyList, instKey)
			continue
		}
	}

	if len(failedKeyList) > 0 {
		return gerrors.Newf(gerrors.Failure,
			"failed to drop route items for some broken spider instances: [%s]",
			switchcore.JoinMetadataKeys(failedKeyList, ", "))
	}

	cluster.ReportClusterLogf(switchlogger.SwitchInfo,
		"successfully drop route items for all broken spider instances")
	return nil
}

// switchRemoteMasterWorker finds master/slave route rows, resets the standby slave,
// and updates primary tdbctl route to point at the new master.
// tdbctlMu serializes access to cluster.tdbctlHelper (shared mutable helper state);
// DoResetSlaveWithBinlogPos runs outside the lock.
func (cluster *TenDBClusterSwitchCluster) switchRemoteMasterWorker(
	primaryTdbctlConn *hamysql.GormDB,
	instKey switchcore.MetadataKey,
	instData *dbm.DbInstMetadata,
	standbySlave *dbm.DbmMetadataSlaveInfo,
	instLogFunc switchlogger.SwitchLogFunc,
	tdbctlMu *sync.Mutex,
) error {
	tdbctlMu.Lock()
	cluster.tdbctlHelper.SetLogFunc(instLogFunc)
	masterRoute, slaveRoute, findErr := cluster.tdbctlHelper.FindMasterSlavePair(
		instData.IP, instData.Port, standbySlave.Ip, standbySlave.Port)
	tdbctlMu.Unlock()
	if findErr != nil {
		return findErr
	}

	binlogFile, binlogPos, resetErr := DoResetSlaveWithBinlogPos(
		standbySlave.Ip, standbySlave.Port, instLogFunc)
	if resetErr != nil {
		errMsg := fmt.Sprintf(
			"failed to reset slave for standby slave(%s:%d), errmsg: %s",
			standbySlave.Ip, standbySlave.Port, resetErr.Error())
		cluster.ReportLogf(instKey, switchlogger.SwitchWarn, "%s", errMsg)
		return resetErr
	}

	cluster.recordNewMasterInfo(instKey, &switchcore.NewMasterInfo{
		Host:       standbySlave.Ip,
		Port:       standbySlave.Port,
		BinlogFile: binlogFile,
		BinlogPos:  binlogPos,
	})

	tdbctlMu.Lock()
	cluster.tdbctlHelper.SetLogFunc(instLogFunc)
	updateErr := cluster.tdbctlHelper.UpdateMasterRouteToSlave(
		primaryTdbctlConn, masterRoute, slaveRoute)
	tdbctlMu.Unlock()
	return updateErr
}

// recordNewMasterInfo stores the new master info of a switched remote master in a concurrency-safe way.
func (cluster *TenDBClusterSwitchCluster) recordNewMasterInfo(
	instKey switchcore.MetadataKey, info *switchcore.NewMasterInfo,
) {
	cluster.newMasterInfoMu.Lock()
	defer cluster.newMasterInfoMu.Unlock()

	if cluster.newMasterInfoMap == nil {
		cluster.newMasterInfoMap = map[switchcore.MetadataKey]*switchcore.NewMasterInfo{}
	}
	cluster.newMasterInfoMap[instKey] = info
}

// GetNewMasterInfos returns the new master info keyed by the switched remote master instance.
func (cluster *TenDBClusterSwitchCluster) GetNewMasterInfos() map[switchcore.MetadataKey]*switchcore.NewMasterInfo {
	cluster.newMasterInfoMu.Lock()
	defer cluster.newMasterInfoMu.Unlock()

	res := make(map[switchcore.MetadataKey]*switchcore.NewMasterInfo, len(cluster.newMasterInfoMap))
	for k, v := range cluster.newMasterInfoMap {
		res[k] = v
	}
	return res
}

// switchRemoteMasters resets slaves and updates route info for each broken remote master
// find master/slave pair, reset slave, and update route info
func (cluster *TenDBClusterSwitchCluster) switchRemoteMasters(
	primaryTdbctlConn *hamysql.GormDB,
) error {
	originalLogFunc := cluster.tdbctlHelper.GetLogFunc()
	defer cluster.tdbctlHelper.SetLogFunc(originalLogFunc)

	if len(cluster.RemoteMasterKeyList) == 0 {
		cluster.ReportClusterLogf(switchlogger.SwitchInfo,
			"no broken remote master instances to switch")
		return nil
	}

	var tdbctlMu sync.Mutex
	maxInstanceConcurrency := switchcore.ClusterLevelSwitchMaxInstanceConcurrency()
	sem := make(chan struct{}, maxInstanceConcurrency)
	failCh := make(chan switchcore.MetadataKey, len(cluster.RemoteMasterKeyList))
	var wg sync.WaitGroup

	for _, instKey := range cluster.RemoteMasterKeyList {
		wg.Add(1)
		go func(instKey switchcore.MetadataKey) {
			defer wg.Done()
			sem <- struct{}{}
			defer func() { <-sem }()

			instData, exists := cluster.SwitchInstances[instKey]
			if !exists {
				cluster.ReportLogf(instKey, switchlogger.SwitchWarn,
					"failed to get remote master instance(%s) metadata when trying to switch it", instKey)
				failCh <- instKey
				return
			}

			standbySlave, exists := cluster.StandbySlaveMap[instKey]
			if !exists || (standbySlave == nil) {
				cluster.ReportLogf(instKey, switchlogger.SwitchWarn,
					"failed to get standby slave for remote master(%s) when trying to switch it", instKey)
				failCh <- instKey
				return
			}

			instLogFunc := func(level switchlogger.SwitchLogLevel, format string, args ...any) bool {
				return cluster.ReportLogf(instKey, level, format, args...)
			}

			if err := cluster.switchRemoteMasterWorker(
				primaryTdbctlConn, instKey, instData, standbySlave, instLogFunc, &tdbctlMu); err != nil {
				failCh <- instKey
			}
		}(instKey)
	}
	wg.Wait()
	close(failCh)

	failedKeyList := make([]switchcore.MetadataKey, 0, len(cluster.RemoteMasterKeyList))
	for k := range failCh {
		failedKeyList = append(failedKeyList, k)
	}

	if len(failedKeyList) > 0 {
		return gerrors.Newf(gerrors.Failure,
			"failed to finish switch steps for some broken remote masters: [%s]",
			switchcore.JoinMetadataKeys(failedKeyList, ", "))
	}

	cluster.ReportClusterLogf(switchlogger.SwitchInfo,
		"successfully reset slaves and update route info for all broken remote masters")
	return nil
}

// UpdateMetaInfo swaps roles of remote masters and their standby slaves
func (cluster *TenDBClusterSwitchCluster) UpdateMetaInfo() error {
	if len(cluster.RemoteMasterKeyList) == 0 {
		cluster.ReportClusterLogf(switchlogger.SwitchInfo,
			"no remote master instances that need to swap roles")
		return nil
	}

	maxDbmAPIConcurrency := switchcore.DbmApiMaxConcurrentRequests()
	sem := make(chan struct{}, maxDbmAPIConcurrency)
	failCh := make(chan switchcore.MetadataKey, len(cluster.RemoteMasterKeyList))
	var wg sync.WaitGroup

	for _, instKey := range cluster.RemoteMasterKeyList {
		wg.Add(1)
		go func(instKey switchcore.MetadataKey) {
			defer wg.Done()
			sem <- struct{}{}
			defer func() { <-sem }()

			instData, exists := cluster.SwitchInstances[instKey]
			if !exists {
				return
			}

			standbySlave, exists := cluster.StandbySlaveMap[instKey]
			if !exists || (standbySlave == nil) {
				cluster.ReportLogf(instKey, switchlogger.SwitchWarn,
					"failed to get standby slave when trying to update meta info")
				failCh <- instKey
				return
			}

			if err := cluster.DbmClient.SwapMySQLRole(cluster.BkCloudID,
				instData.IP, instData.Port, standbySlave.Ip, standbySlave.Port); err != nil {
				cluster.ReportLogf(instKey, switchlogger.SwitchWarn,
					"failed to swap roles of remote nodes(master:%s:%d, slave:%s:%d), errmsg:%s",
					instData.IP, instData.Port, standbySlave.Ip, standbySlave.Port, err.Error())
				failCh <- instKey
				return
			}

			cluster.ReportLogf(instKey, switchlogger.SwitchInfo,
				"successfully swap roles of remote nodes(master:%s:%d, slave:%s:%d)",
				instData.IP, instData.Port, standbySlave.Ip, standbySlave.Port)
		}(instKey)
	}
	wg.Wait()
	close(failCh)

	failedInstKeyList := make([]switchcore.MetadataKey, 0, len(cluster.RemoteMasterKeyList))
	for k := range failCh {
		failedInstKeyList = append(failedInstKeyList, k)
	}

	if len(failedInstKeyList) > 0 {
		return gerrors.Newf(gerrors.Failure,
			"failed to update meta info for some remote masters: [%s]",
			switchcore.JoinMetadataKeys(failedInstKeyList, ", "))
	}

	cluster.ReportClusterLogf(switchlogger.SwitchInfo,
		"successfully update meta info for all broken remote masters")
	return nil
}

// DoFinal performs final operations after switch completion, such as
// repairing tdbctl replication relationship if the primary was changed.
func (cluster *TenDBClusterSwitchCluster) DoFinal() error {
	return cluster.tdbctlHelper.RepairTdbctlReplication()
}
