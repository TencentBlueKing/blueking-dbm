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

	"dbm-services/common/dbha-v2/internal/analysis/dbm"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchcore"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchlogger"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// NewTendbClusterSwitchInstance creates a new TenDBCluster switch instance based on metadata
func NewTendbClusterSwitchInstance(metadata *dbm.DbInstMetadata) (switchcore.SwitchableInstance, error) {
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
		AdminPort:        metadata.AdminPort,
		BindEntry:        metadata.BindEntry,
		ProxyInstanceSet: metadata.ProxyInstanceSet,
		BinlogDumperSet:  metadata.BinlogDumpers,
	}

	tendbClusterBaseInstance := TenDBClusterBaseSwitchInstance{
		MySQLBaseSwitchInstance: mysqlBaseInstance,
	}

	switch metadata.MachineType {
	case haprobe.DbmMetadataMachineTypeRemote:
		res := &TenDBClusterRemoteSwitchInstance{
			TenDBClusterBaseSwitchInstance: tendbClusterBaseInstance,
		}
		if metadata.InstanceRole == haprobe.TenDBClusterStorageMaster {
			res.SetStandbySlave(metadata.Receiver)
		}
		return res, nil

	case haprobe.DbmMetadataMachineTypeSpider:
		res := &TenDBClusterSpiderSwitchInstance{
			TenDBClusterBaseSwitchInstance: tendbClusterBaseInstance,
			SpiderRole:                     metadata.SpiderRole,
		}
		return res, nil

	default:
		logger.Error("found unknown machine type when constructing tendbcluster switch instance: %s",
			metadata.MachineType)
		return nil, gerrors.New(gerrors.InvalidParameter, "invalid machine type")
	}
}

// TenDBClusterBaseSwitchInstance provides base switching functionality for TenDBCluster
type TenDBClusterBaseSwitchInstance struct {
	MySQLBaseSwitchInstance

	tdbctlHelper TdbctlOperator
}

// TenDBClusterSpiderSwitchInstance switch instance for spider
type TenDBClusterSpiderSwitchInstance struct {
	TenDBClusterBaseSwitchInstance

	// The following are instance metadata information from DBM

	SpiderRole haprobe.DbmMetadataSpiderRole
}

// GetInstanceRole returns the role of this instance
func (sw *TenDBClusterSpiderSwitchInstance) GetInstanceRole() haprobe.DbmMetadataInstanceRole {
	return haprobe.DbmMetadataInstanceRole(sw.SpiderRole)
}

// GetInstanceInfo returns instance information as string
func (sw *TenDBClusterSpiderSwitchInstance) GetInstanceInfo() string {
	infoStr := fmt.Sprintf("{bk_cloud_id:%d, ip:%s, port:%d, admin_port:%d, bk_idc_city_id:%d, "+
		"bk_biz_id:%d, status:%s, cluster:%s, cluster_id:%d, cluster_type:%s, machine_type:%s, spider_role:%s}",
		sw.BkCloudID, sw.IP, sw.Port, sw.AdminPort, sw.BkIdcCityID, sw.BkBizID, sw.Status, sw.Cluster,
		sw.ClusterID, sw.ClusterType, sw.MachineType, sw.SpiderRole)
	return infoStr
}

// InitTdbctlHelper initializes the tdbctl helper
func (sw *TenDBClusterSpiderSwitchInstance) InitTdbctlHelper() error {
	brokenSpiderMasters := []BrokenSpiderMasterInfo{}
	if sw.SpiderRole == haprobe.TenDBClusterSpiderMaster {
		brokenSpiderMasters = append(brokenSpiderMasters, BrokenSpiderMasterInfo{
			BkCloudID: sw.BkCloudID,
			IP:        sw.IP,
			Port:      sw.Port,
			AdminPort: sw.AdminPort,
		})
	}
	sw.tdbctlHelper.Init(sw.Cluster, sw.BkCloudID, brokenSpiderMasters, sw.ReportLogf)
	return nil
}

// CheckBeforeSwitch check slave before switch
func (sw *TenDBClusterSpiderSwitchInstance) CheckBeforeSwitch() (switchcore.SwitchCheckCode, error) {
	switch sw.SpiderRole {
	case haprobe.TenDBClusterSpiderMaster:
		sw.ReportLogf(switchlogger.SwitchInfo, "this is a spider master node, no need to check")
		return switchcore.SwitchRequired, nil

	case haprobe.TenDBClusterSpiderSlave:
		sw.ReportLogf(switchlogger.SwitchInfo, "this is a spider slave node, no need to check")
		return switchcore.SwitchRequired, nil

	default:
		err := gerrors.Newf(gerrors.Failure, "invalid instance role: %s", sw.SpiderRole)
		sw.ReportLogf(switchlogger.SwitchWarn, "%s", err.Error())
		return switchcore.SwitchCheckUnpass, err
	}
}

// DoSwitch do spider(include tdbctl) switch
// 1. deletes spider instance from bound entries
// 2. query all spider/tdbctl nodes of this cluster from DBM
// 3. query all tdbctl nodes' status from any valid tdbctl node
// 4. found primary tdbctl
// 5. change primary tdbctl if the primary tdbctl belongs to current broken spider
// 6. connect primary tdbctl
// 7. query route table from primary tdbctl
// 8. delete broken-down spider and its corresponding tdbctl from primary-tdbctl route table
// 9. do flush routing on primary tdbctl
func (sw *TenDBClusterSpiderSwitchInstance) DoSwitch() error {
	sw.InitTdbctlHelper()

	sw.ReportLogf(switchlogger.SwitchInfo, "switch step 1: try to delete this spider instance from all bound entries")
	if err := sw.DeleteNameService(sw.BindEntry); err != nil {
		return err
	}

	sw.ReportLogf(switchlogger.SwitchInfo, "switch step 2: try to query all spider/tdbctl nodes of this cluster from DBM")
	if err := sw.tdbctlHelper.QuerySpiderNodesOfCluster(sw.DbmClient); err != nil {
		return err
	}

	sw.ReportLogf(switchlogger.SwitchInfo,
		"switch step 3: try to query all tdbctl nodes' status from any valid tdbctl node")
	if err := sw.tdbctlHelper.QueryTdbctlNodesOfCluster(); err != nil {
		return err
	}

	sw.ReportLogf(switchlogger.SwitchInfo, "switch step 4: try to find the primary tdbctl")
	if err := sw.tdbctlHelper.FindPrimaryTdbctl(); err != nil {
		return err
	}

	sw.ReportLogf(switchlogger.SwitchInfo, "switch step 5: change primary tdbctl if it belongs to current broken spider")
	if err := sw.tdbctlHelper.HandleInvolvedPrimaryTdbctl(); err != nil {
		return err
	}

	sw.ReportLogf(switchlogger.SwitchInfo, "switch step 6: try to connect primary tdbctl")
	if sw.tdbctlHelper.PrimaryTdbctl == nil {
		return gerrors.New(gerrors.Failure, "primary tdbctl is nil when connecting to primary tdbctl")
	}

	primaryTdbctlConn, connErr := sw.tdbctlHelper.ConnectTdbctlNode(
		sw.tdbctlHelper.PrimaryTdbctl.Host, sw.tdbctlHelper.PrimaryTdbctl.Port)
	if connErr != nil {
		return connErr
	}
	defer primaryTdbctlConn.Close()

	sw.ReportLogf(switchlogger.SwitchInfo, "switch step 7: try to query route info of this cluster from primary tdbctl")
	if err := sw.tdbctlHelper.QueryRouteInfoOfCluster(primaryTdbctlConn); err != nil {
		return err
	}

	sw.ReportLogf(switchlogger.SwitchInfo,
		"switch step 8: try to delete broken-down spider and its tdbctl from cluster route table")
	if err := sw.tdbctlHelper.DropBrokenSpiderRoutes(
		primaryTdbctlConn, sw.IP, sw.Port, sw.AdminPort, sw.SpiderRole,
	); err != nil {
		return err
	}

	sw.ReportLogf(switchlogger.SwitchInfo, "switch step 9: try to flush route table")
	if err := sw.tdbctlHelper.TdbctlFlushRouting(primaryTdbctlConn, true); err != nil {
		return err
	}

	return nil
}

// DoFinal repair replication relationship if the primary tdbctl is changed
func (sw *TenDBClusterSpiderSwitchInstance) DoFinal() error {
	return sw.tdbctlHelper.RepairTdbctlReplication()
}

// TenDBClusterRemoteSwitchInstance switch instance for remote
type TenDBClusterRemoteSwitchInstance struct {
	TenDBClusterBaseSwitchInstance

	// Information obtained during switch

	NewMasterBinlogFile string
	NewMasterBinlogPos  uint64
}

// GetNewMasterInfo returns the promoted new master info. ok is true only for a master switch
// whose standby slave (the new master) is known.
func (sw *TenDBClusterRemoteSwitchInstance) GetNewMasterInfo() (*switchcore.NewMasterInfo, bool) {
	if sw.InstanceRole != haprobe.TenDBClusterStorageMaster || sw.StandBySlave == nil {
		return nil, false
	}

	return &switchcore.NewMasterInfo{
		Host:       sw.StandBySlave.Ip,
		Port:       sw.StandBySlave.Port,
		BinlogFile: sw.NewMasterBinlogFile,
		BinlogPos:  sw.NewMasterBinlogPos,
	}, true
}

// CheckTenDBClusterStorageMaster check remote master
func (sw *TenDBClusterRemoteSwitchInstance) CheckTenDBClusterStorageMaster() (switchcore.SwitchCheckCode, error) {
	if sw.StandBySlave == nil {
		err := gerrors.Newf(gerrors.Failure, "the standby slave is nil")
		sw.ReportLog(switchlogger.SwitchWarn, err.Error())
		return switchcore.SwitchCheckUnpass, err
	}
	if sw.StandBySlave.Status == dbm.Unavailable {
		err := gerrors.Newf(gerrors.Failure, "the standby slave(%s:%d) is unavailable",
			sw.StandBySlave.Ip, sw.StandBySlave.Port)
		sw.ReportLog(switchlogger.SwitchWarn, err.Error())
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
		sw.ReportLogf(switchlogger.SwitchWarn, "slave status check unpass: %s", err.Error())
		return switchcore.SwitchCheckUnpass, err
	}

	if len(sw.ProxyInstanceSet) == 0 {
		err := gerrors.Newf(gerrors.Failure, "no spider instances were found for this remote master")
		sw.ReportLog(switchlogger.SwitchWarn, err.Error())
		return switchcore.SwitchCheckUnpass, err
	}

	return switchcore.SwitchRequired, nil
}

// CheckBeforeSwitch check slave before switch
func (sw *TenDBClusterRemoteSwitchInstance) CheckBeforeSwitch() (switchcore.SwitchCheckCode, error) {
	switch sw.InstanceRole {
	// Notice: remote slave node is not required to be switched
	case haprobe.TenDBClusterStorageSlave:
		sw.ReportLogf(switchlogger.SwitchInfo, "this is a slave node, no need to check")
		return switchcore.SwitchNotNeeded, nil

	case haprobe.TenDBClusterStorageMaster:
		return sw.CheckTenDBClusterStorageMaster()

	default:
		err := gerrors.Newf(gerrors.Failure, "invalid instance role: %s", sw.InstanceRole)
		sw.ReportLogf(switchlogger.SwitchWarn, "%s", err.Error())
		return switchcore.SwitchCheckUnpass, err
	}
}

// DoSwitch do switch for tendbcluster remote
//  1. query all spider/tdbctl nodes of this cluster from DBM
//  2. query all tdbctl nodes' status from any valid tdbctl node
//  3. find the primary tdbctl
//  4. connect primary tdbctl
//  5. query route info of this cluster from primary tdbctl
//  6. find nodes info of current broken remote master and its slave
//  7. reset slave for current remote slave
//  8. update route info of current broken remote master and its slave
//  9. flush route table
func (sw *TenDBClusterRemoteSwitchInstance) DoSwitch() error {
	sw.tdbctlHelper.Init(sw.Cluster, sw.BkCloudID, nil, sw.ReportLogf)

	sw.ReportLogf(switchlogger.SwitchInfo, "switch step 1: try to query all spider/tdbctl nodes of this cluster from DBM")
	if err := sw.tdbctlHelper.QuerySpiderNodesOfCluster(sw.DbmClient); err != nil {
		return err
	}

	sw.ReportLogf(switchlogger.SwitchInfo,
		"switch step 2: try to query all tdbctl nodes' status from any valid tdbctl node")
	if err := sw.tdbctlHelper.QueryTdbctlNodesOfCluster(); err != nil {
		return err
	}

	sw.ReportLogf(switchlogger.SwitchInfo, "switch step 3: try to find the primary tdbctl")
	if err := sw.tdbctlHelper.FindPrimaryTdbctl(); err != nil {
		return err
	}

	sw.ReportLogf(switchlogger.SwitchInfo, "switch step 4: try to connect primary tdbctl")
	if sw.tdbctlHelper.PrimaryTdbctl == nil {
		return gerrors.New(gerrors.Failure, "primary tdbctl is nil when connecting to primary tdbctl")
	}

	primaryTdbctlConn, connErr := sw.tdbctlHelper.ConnectTdbctlNode(
		sw.tdbctlHelper.PrimaryTdbctl.Host, sw.tdbctlHelper.PrimaryTdbctl.Port)
	if connErr != nil {
		return connErr
	}
	defer primaryTdbctlConn.Close()

	sw.ReportLogf(switchlogger.SwitchInfo, "switch step 5: try to query route info of this cluster from primary tdbctl")
	if err := sw.tdbctlHelper.QueryRouteInfoOfCluster(primaryTdbctlConn); err != nil {
		return err
	}

	sw.ReportLogf(switchlogger.SwitchInfo,
		"switch step 6: try to find nodes info of current broken remote master and its slave")
	curMasterRoute, curSlaveRoute, notFoundErr := sw.tdbctlHelper.FindMasterSlavePair(
		sw.IP, sw.Port, sw.StandBySlave.Ip, sw.StandBySlave.Port)
	if notFoundErr != nil {
		return notFoundErr
	}

	sw.ReportLogf(switchlogger.SwitchInfo, "switch step 7: try to reset slave for current remote slave")
	binlogFile, binlogPos, err := sw.ResetSlaveWithBinlogPos(sw.StandBySlave.Ip, sw.StandBySlave.Port)
	if err != nil {
		err = gerrors.Newf(gerrors.Failure, "failed to reset slave status for the remote slave(%s:%d), errmsg: %s",
			sw.StandBySlave.Ip, sw.StandBySlave.Port, err.Error())
		sw.ReportLog(switchlogger.SwitchWarn, err.Error())
		return err
	}
	sw.NewMasterBinlogFile = binlogFile
	sw.NewMasterBinlogPos = binlogPos

	sw.ReportLogf(switchlogger.SwitchInfo,
		"switch step 8: try to update route info of current broken remote master and its slave")
	if err := sw.tdbctlHelper.UpdateMasterRouteToSlave(primaryTdbctlConn, curMasterRoute, curSlaveRoute); err != nil {
		return err
	}

	sw.ReportLogf(switchlogger.SwitchInfo, "switch step 9: try to flush route table")
	if err := sw.tdbctlHelper.TdbctlFlushRouting(primaryTdbctlConn, true); err != nil {
		return err
	}

	return nil
}

// GetInstanceInfo returns formatted instance information string
func (sw *TenDBClusterRemoteSwitchInstance) GetInstanceInfo() string {
	standBySlave := "nil"
	if sw.StandBySlave != nil {
		standBySlave = fmt.Sprintf("%s:%d", sw.StandBySlave.Ip, sw.StandBySlave.Port)
	}
	infoStr := fmt.Sprintf("{bk_cloud_id:%d, ip:%s, port:%d, bk_idc_city_id:%d, bk_biz_id:%d, status:%s, "+
		"cluster:%s, cluster_id:%d, cluster_type:%s, machine_type:%s, role:%s, standby_slave:%s}",
		sw.BkCloudID, sw.IP, sw.Port, sw.BkIdcCityID, sw.BkBizID, sw.Status, sw.Cluster,
		sw.ClusterID, sw.ClusterType, sw.MachineType, sw.InstanceRole, standBySlave)
	return infoStr
}

// UpdateMetaInfo swaps roles of remote master and slave
func (sw *TenDBClusterRemoteSwitchInstance) UpdateMetaInfo() error {
	sw.ReportLogf(switchlogger.SwitchInfo, "try to swap roles of remote nodes(master:%s:%d, slave:%s:%d)",
		sw.IP, sw.Port, sw.StandBySlave.Ip, sw.StandBySlave.Port)

	err := sw.DbmClient.SwapMySQLRole(sw.BkCloudID, sw.IP, sw.Port, sw.StandBySlave.Ip, sw.StandBySlave.Port)
	if err != nil {
		errMsg := fmt.Sprintf("failed to swap roles of remote nodes(master:%s:%d, slave:%s:%d), errmsg:%s",
			sw.IP, sw.Port, sw.StandBySlave.Ip, sw.StandBySlave.Port, err.Error())
		sw.ReportLog(switchlogger.SwitchWarn, errMsg)
		return err
	}

	sw.ReportLogf(switchlogger.SwitchInfo, "successfully swapped roles of remote nodes(master:%s:%d, slave:%s:%d)",
		sw.IP, sw.Port, sw.StandBySlave.Ip, sw.StandBySlave.Port)
	return nil
}
