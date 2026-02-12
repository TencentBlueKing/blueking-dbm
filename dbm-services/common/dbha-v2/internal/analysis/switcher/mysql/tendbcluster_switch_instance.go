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
	"encoding/json"
	"fmt"
	"strconv"
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

// Commands for Tdbctl
const (
	SelectTdbctlNodesSql        = "SELECT * FROM information_schema.tdbctl_nodes"
	SelectRouteInfoSql          = "SELECT Server_name, Host, Username, Password, Port, Wrapper FROM mysql.servers"
	TdbctlEnablePrimarySql      = "TDBCTL ENABLE PRIMARY"
	TdbctlEnablePrimaryForceSql = "TDBCTL ENABLE PRIMARY FORCE"
	TdbctlDropNodeSql           = "TDBCTL DROP NODE %s"
	TdbctlFlushRouteSql         = "TDBCTL FLUSH ROUTING"
	TdbctlFlushRouteForceSql    = "TDBCTL FLUSH ROUTING FORCE"
	TdbctlChangeMasterSql       = "CHANGE MASTER TO MASTER_HOST='%s', MASTER_PORT=%d, MASTER_AUTO_POSITION=1"
	TdbctlAlterNodeSql          = "TDBCTL ALTER NODE %s OPTIONS(HOST '%s', Port %d, USER '%s', PASSWORD '%s')"
)

// Types of CLUSTER_ROLE in information_schema.TDBCTL_NODES
const (
	PrimaryTdbctlRole      = "primary"
	SecondaryTdbctlRole    = "Secondary"
	StandaloneTdbctlRole   = "Standalone"
	FalsePrimaryTdbctlRole = "FalsePrimary"
	UnknownTdbctlRole      = "Unknown"
)

// SpiderInstanceInfo represents spider node information in TenDBCluster
type SpiderInstanceInfo struct {
	IP         string                    `json:"ip"`
	Port       int                       `json:"port"`
	AdminPort  int                       `json:"admin_port"`
	SpiderRole dbm.DbmMetadataSpiderRole `json:"spider_role"`
	Status     dbm.DbmMetadataStatus     `json:"status"`
}

// TdbctlRouteInfo represents route information in mysql.servers
type TdbctlRouteInfo struct {
	ServerName string `gorm:"column:Server_name" json:"server_name"`
	Host       string `gorm:"column:Host"        json:"host"`
	UserName   string `gorm:"column:Username"    json:"username"`
	Password   string `gorm:"column:Password"    json:"password"`
	Port       int    `gorm:"column:Port"        json:"port"`
	Wrapper    string `gorm:"column:Wrapper"     json:"wrapper"`
}

// CopyConstructTdbctlRoute copies and constructs a new TdbctlRoute
func CopyConstructTdbctlRoute(node *TdbctlRouteInfo) *TdbctlRouteInfo {
	return &TdbctlRouteInfo{
		ServerName: node.ServerName,
		Host:       node.Host,
		UserName:   node.UserName,
		Password:   node.Password,
		Port:       node.Port,
		Wrapper:    node.Wrapper,
	}
}

// TdbctlPrimaryNodeInfo holds information for primary TDBCTL node
type TdbctlPrimaryNodeInfo struct {
	ServerName   string `json:"server_name"`
	Host         string `json:"host"`
	Port         int    `json:"port"`
	ClusterRole  string `json:"cluster_role"`
	Status       string `json:"status"`
	IsThisServer bool   `json:"is_this_server"`
}

// TdbctlNodeReplInfo holds replication information for TDBCTL node
type TdbctlNodeReplInfo struct {
	// information from information_schema.TDBCTL_NODES's "REPLICATION_INFO" field

	MasterHost         string `json:"Master_Host"`
	MasterPort         int    `json:"Master_Port"`
	SlaveIORunning     string `json:"Slave_IO_Running"`
	SlaveSQLRunning    string `json:"Slave_SQL_Running"`
	RelayMasterLogFile string `json:"Relay_Master_Log_File"`
	ExecMasterLogPos   string `json:"Exec_Master_Log_Pos"`

	// other information parsed from above members

	RelayMasterLogFileIndex int    `json:"Parsed_Relay_Master_Log_File_Index"`
	ExecMasterLogPosInt     uint64 `json:"Parsed_Exec_Master_Log_Pos"`
}

// TdbctlNodeInfo represents query result of information_schema.TDBCTL_NODES
type TdbctlNodeInfo struct {
	ServerName        string `gorm:"column:SERVER_NAME;not null"        json:"server_name"`
	Host              string `gorm:"column:HOST;not null"               json:"host"`
	Port              int    `gorm:"column:PORT;default:0;not null"     json:"port"`
	ReplicationMaster string `gorm:"column:REPLICATION_MASTER;not null" json:"replication_master"`
	ClusterRole       string `gorm:"column:CLUSTER_ROLE;not null"       json:"cluster_role"`
	Status            string `gorm:"column:STATUS;not null"             json:"status"`
	Message           string `gorm:"column:MESSAGE;not null"            json:"message"`
	ReplicationInfo   string `gorm:"column:REPLICATION_INFO;not null"   json:"replication_info"`
}

func (node *TdbctlNodeInfo) String() string {
	return fmt.Sprintf("ServerName: %s, Host: %s, Port: %d, ReplicationMaster: %s, ClusterRole: %s, "+
		"Status: %s, Message: %s, ReplicationInfo: %s", node.ServerName, node.Host, node.Port, node.ReplicationMaster,
		node.ClusterRole, node.Status, node.Message, node.ReplicationInfo)
}

// CopyConstructTdbctlNode copies and constructs a new TdbctlNode
func CopyConstructTdbctlNode(node *TdbctlNodeInfo) *TdbctlNodeInfo {
	return &TdbctlNodeInfo{
		ServerName:        node.ServerName,
		Host:              node.Host,
		Port:              node.Port,
		ReplicationMaster: node.ReplicationMaster,
		ClusterRole:       node.ClusterRole,
		Status:            node.Status,
		Message:           node.Message,
		ReplicationInfo:   node.ReplicationInfo,
	}
}

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
		if metadata.InstanceRole == dbm.TenDBClusterStorageMaster {
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

	// Spider nodes info obtained from DBM during switch process
	SpiderNodes []SpiderInstanceInfo

	// The following are information from TDBCTL node

	TdbctlNodes      []TdbctlNodeInfo
	PrimaryTdbctl    *TdbctlPrimaryNodeInfo
	TdbctlRouteTable []TdbctlRouteInfo
}

// ConnectTdbctlNode connect tdbctl node using gorm
func (sw *TenDBClusterBaseSwitchInstance) ConnectTdbctlNode(tdbctlHost string, tdbctlPort int) (*hamysql.GormDB, error) {
	tdbctlUser := config.Cfg.Database.Mysql.User
	tdbctlPassword := config.Cfg.Database.Mysql.Password

	tdbctlDB, connErr := hamysql.NewGormDB(
		hamysql.OptionProto(DefaultMySQLProtocol),
		hamysql.OptionIP(tdbctlHost),
		hamysql.OptionPort(tdbctlPort),
		hamysql.OptionUser(tdbctlUser),
		hamysql.OptionPassword(tdbctlPassword),
		hamysql.OptionSkipInitializeWithVersion(false),
		hamysql.OptionDisableDatetimePrecision(true),
		hamysql.OptionCharset(""),
	)

	if connErr != nil {
		sw.ReportLogf(switchlogger.SwitchWarn, "failed to connect tdbctl node(%s:%d): %s", tdbctlHost, tdbctlPort, connErr.Error())
		return nil, connErr
	}
	sw.ReportLogf(switchlogger.SwitchInfo, "successfully connected to tdbctl node(%s:%d)", tdbctlHost, tdbctlPort)
	return tdbctlDB, nil
}

// DisconnectTdbctlNode disconnect tdbctl node
func (sw *TenDBClusterBaseSwitchInstance) DisconnectTdbctlNode(tdbctlDB *hamysql.GormDB) {
	tdbctlDB.Close()
}

// SelectTdbctlNodes query tdbctl nodes info from information_schema.TDBCTL_NODES
func (sw *TenDBClusterBaseSwitchInstance) SelectTdbctlNodes(tdbctlDB *hamysql.GormDB) ([]TdbctlNodeInfo, error) {
	if tdbctlDB == nil {
		return nil, gerrors.New(gerrors.Failure, "tdbctl connection is nil")
	}

	var tdbctlList []TdbctlNodeInfo
	queryErr := tdbctlDB.DB().Raw(SelectTdbctlNodesSql).Scan(&tdbctlList).Error
	if queryErr != nil {
		return nil, gerrors.Newf(gerrors.Failure, "failed to execute sql(%s) on tdbctl(%s:%d), errmsg: %s",
			SelectTdbctlNodesSql, tdbctlDB.Host(), tdbctlDB.Port(), queryErr.Error())
	}

	if len(tdbctlList) == 0 {
		return nil, gerrors.New(gerrors.Failure, "no tdbctl node found")
	}

	nodesInfo, convertErr := converter.ToJsonStr(tdbctlList)
	if convertErr != nil {
		logger.Warn("failed to convert tdbctl nodes info to json, err: %s", convertErr.Error())
		nodesInfo = fmt.Sprintf("%v", tdbctlList)
	}
	sw.ReportLogf(switchlogger.SwitchInfo, "successfully queried all tdbctl nodes info from tdbctl node(%s:%d): %s",
		tdbctlDB.Host(), tdbctlDB.Port(), nodesInfo)

	return tdbctlList, nil
}

// SelectRouteInfo query route info from mysql.servers
func (sw *TenDBClusterBaseSwitchInstance) SelectRouteInfo(tdbctlDB *hamysql.GormDB) ([]TdbctlRouteInfo, error) {
	if tdbctlDB == nil {
		return nil, gerrors.New(gerrors.Failure, "tdbctl connection is nil")
	}

	var routeInfoList []TdbctlRouteInfo
	queryErr := tdbctlDB.DB().Raw(SelectRouteInfoSql).Scan(&routeInfoList).Error
	if queryErr != nil {
		return nil, gerrors.Newf(gerrors.Failure, "failed to execute sql(%s) on tdbctl(%s:%d), errmsg: %s",
			SelectRouteInfoSql, tdbctlDB.Host(), tdbctlDB.Port(), queryErr.Error())
	}
	sw.ReportLogf(switchlogger.SwitchInfo, "successfully executed sql(%s) on tdbctl(%s:%d)",
		SelectRouteInfoSql, tdbctlDB.Host(), tdbctlDB.Port())

	if len(routeInfoList) == 0 {
		return nil, gerrors.New(gerrors.Failure, "no server found")
	}

	routesStr, convertErr := converter.ToJsonStr(routeInfoList)
	if convertErr != nil {
		logger.Warn("failed to convert routes to json, err: %s", convertErr.Error())
		routesStr = fmt.Sprintf("%v", routeInfoList)
	}
	sw.ReportLogf(switchlogger.SwitchInfo, "successfully queried routes from tdbctl node(%s:%d): %s",
		tdbctlDB.Host(), tdbctlDB.Port(), routesStr)

	return routeInfoList, nil
}

// TdbctlDropNode drop node from tdbctl
func (sw *TenDBClusterBaseSwitchInstance) TdbctlDropNode(tdbctlDB *hamysql.GormDB, nodeName string) error {
	if tdbctlDB == nil {
		return gerrors.New(gerrors.Failure, "tdbctl connection is nil")
	}

	dropNodeSql := fmt.Sprintf(TdbctlDropNodeSql, nodeName)
	result := tdbctlDB.DB().Exec(dropNodeSql)
	if result.Error != nil {
		return gerrors.Newf(gerrors.Failure, "failed to execute sql(%s) on tdbctl(%s:%d), errmsg: %s",
			dropNodeSql, tdbctlDB.Host(), tdbctlDB.Port(), result.Error.Error())
	}
	sw.ReportLogf(switchlogger.SwitchInfo, "successfully executed sql(%s) on tdbctl(%s:%d)",
		dropNodeSql, tdbctlDB.Host(), tdbctlDB.Port())

	if result.RowsAffected != 1 {
		return gerrors.Newf(gerrors.Failure, "cannot ensure that the number of rows affected is 1, affected: %d",
			result.RowsAffected)
	}

	sw.ReportLogf(switchlogger.SwitchInfo, "successfully dropped node(%s) on tdbctl(%s:%d)", nodeName, tdbctlDB.Host(), tdbctlDB.Port())
	return nil
}

// TdbctlFlushRouting flush routing on tdbctl
func (sw *TenDBClusterBaseSwitchInstance) TdbctlFlushRouting(tdbctlDB *hamysql.GormDB, force bool) error {
	if tdbctlDB == nil {
		return gerrors.New(gerrors.Failure, "tdbctl connection is nil")
	}

	flushRouteSql := TdbctlFlushRouteSql
	if force {
		flushRouteSql = TdbctlFlushRouteForceSql
	}

	if result := tdbctlDB.DB().Exec(flushRouteSql); result.Error != nil {
		return gerrors.Newf(gerrors.Failure, "failed to execute sql(%s) on tdbctl(%s:%d), errmsg: %s",
			flushRouteSql, tdbctlDB.Host(), tdbctlDB.Port(), result.Error.Error())
	}
	sw.ReportLogf(switchlogger.SwitchInfo, "successfully executed sql(%s) on tdbctl(%s:%d)",
		flushRouteSql, tdbctlDB.Host(), tdbctlDB.Port())

	sw.ReportLogf(switchlogger.SwitchInfo, "successfully flush routing on tdbctl(%s:%d)", tdbctlDB.Host(), tdbctlDB.Port())
	return nil
}

// FindPrimaryTdbctl finds the primary tdbctl from information_schema.TDBCTL_NODES
// A tdbctl node can be considered as the primary tdbctl if it meets any of the following conditions:
//  1. The only node with CLUSTER_ROLE as "Primary" in the information_schema.TDBCTL_NODES
//  2. When there is no "Primary" node in the information_schema.TDBCTL_NODES,
//     a unique node is found that serves as the replication master for all "Secondary" nodes
func (sw *TenDBClusterBaseSwitchInstance) FindPrimaryTdbctl() error {
	sw.PrimaryTdbctl = nil
	var masterServerName *string

	if len(sw.TdbctlNodes) == 0 {
		return gerrors.New(gerrors.Failure, "no tdbctl node is provided to find the primary tdbctl")
	}

	for _, oneTdbctl := range sw.TdbctlNodes {
		if strings.EqualFold(oneTdbctl.ClusterRole, PrimaryTdbctlRole) {
			if sw.PrimaryTdbctl != nil {
				errMsg := fmt.Sprintf("multiple primary tdbctl nodes(%s:%d, %s:%d) were found",
					sw.PrimaryTdbctl.Host, sw.PrimaryTdbctl.Port, oneTdbctl.Host, oneTdbctl.Port)
				sw.ReportLogf(switchlogger.SwitchWarn, "%s", errMsg)
				return gerrors.New(gerrors.Failure, errMsg)
			}

			sw.PrimaryTdbctl = &TdbctlPrimaryNodeInfo{
				ServerName:   oneTdbctl.ServerName,
				Host:         oneTdbctl.Host,
				Port:         oneTdbctl.Port,
				ClusterRole:  oneTdbctl.ClusterRole,
				Status:       oneTdbctl.Status,
				IsThisServer: (oneTdbctl.Host == sw.IP) && (oneTdbctl.Port == sw.AdminPort),
			}
		}

		if strings.EqualFold(oneTdbctl.ClusterRole, SecondaryTdbctlRole) {
			if (masterServerName != nil) && (*masterServerName != oneTdbctl.ReplicationMaster) {
				errMsg := fmt.Sprintf("multiple replication master tdbctl nodes(%s, %s) were found",
					*masterServerName, oneTdbctl.ReplicationMaster)
				sw.ReportLogf(switchlogger.SwitchWarn, "%s", errMsg)
				return gerrors.New(gerrors.Failure, errMsg)
			}

			if masterServerName == nil {
				masterServerName = &oneTdbctl.ReplicationMaster
			}
		}
	}

	// if no primary tdbctl found, try to use the single replication master tdbctl as primary tdbctl
	if (sw.PrimaryTdbctl == nil) && (masterServerName != nil) {
		sw.ReportLogf(switchlogger.SwitchInfo, "the primary tdbctl of cluster(%s) is missing, "+
			"but the single replication master tdbctl(%s) is found", sw.Cluster, *masterServerName)

		for _, oneTdbctl := range sw.TdbctlNodes {
			if strings.EqualFold(oneTdbctl.ServerName, *masterServerName) {
				sw.PrimaryTdbctl = &TdbctlPrimaryNodeInfo{
					ServerName:   oneTdbctl.ServerName,
					Host:         oneTdbctl.Host,
					Port:         oneTdbctl.Port,
					ClusterRole:  oneTdbctl.ClusterRole,
					Status:       oneTdbctl.Status,
					IsThisServer: (oneTdbctl.Host == sw.IP) && (oneTdbctl.Port == sw.AdminPort),
				}
				break
			}
		}
	}

	if sw.PrimaryTdbctl != nil {
		primaryTdbctlInfo := converter.ToStrIgnoreErr(*(sw.PrimaryTdbctl))
		sw.ReportLogf(switchlogger.SwitchInfo, "successfully found the primary tdbctl node of cluster(%s): %s",
			sw.Cluster, primaryTdbctlInfo)
		return nil
	}

	sw.ReportLogf(switchlogger.SwitchWarn, "no primary tdbctl node was found in cluster(%s)", sw.Cluster)
	return gerrors.Newf(gerrors.Failure, "no primary tdbctl node was found in cluster(%s)", sw.Cluster)
}

// QuerySpiderNodesOfCluster query all spider nodes of current cluster from DBM
func (sw *TenDBClusterBaseSwitchInstance) QuerySpiderNodesOfCluster() error {
	instInfoList, err := sw.DbmClient.QueryInstanceInfoByDomain(sw.BkCloudID, sw.Cluster)
	if err != nil {
		sw.ReportLogf(switchlogger.SwitchWarn, "failed to query instance info of cluster(%s) from DBM: %s",
			sw.Cluster, err.Error())
		return err
	}

	sw.SpiderNodes = nil
	for _, instInfo := range instInfoList {
		if instInfo.MachineType == haprobe.DbmMetadataMachineTypeSpider {
			sw.SpiderNodes = append(sw.SpiderNodes, SpiderInstanceInfo{
				IP:         instInfo.IP,
				Port:       instInfo.Port,
				AdminPort:  instInfo.AdminPort,
				SpiderRole: instInfo.SpiderRole,
				Status:     instInfo.Status,
			})
		}
	}

	if len(sw.SpiderNodes) == 0 {
		sw.ReportLogf(switchlogger.SwitchWarn, "no spider instance of cluster %s found from DBM", sw.Cluster)
		return gerrors.Newf(gerrors.Failure, "no spider instance found in cluster %s", sw.Cluster)
	}

	sw.ReportLogf(switchlogger.SwitchInfo, "successfully queried spider nodes of cluster(%s) from DBM", sw.Cluster)
	return nil
}

// QueryTdbctlNodesOfCluster query all tdbctl nodes of current cluster from any tdbctl node
func (sw *TenDBClusterBaseSwitchInstance) QueryTdbctlNodesOfCluster() error {
	for _, curSpider := range sw.SpiderNodes {
		// only spider-master has tdbctl node
		if (curSpider.Status == dbm.Unavailable) || (curSpider.SpiderRole != dbm.TenDBClusterSpiderMaster) {
			continue
		}

		tdbctlDB, connErr := sw.ConnectTdbctlNode(curSpider.IP, curSpider.AdminPort)
		if connErr != nil {
			sw.ReportLogf(switchlogger.SwitchWarn, "failed to connect tdbctl node(%s:%d): %s, try other nodes",
				curSpider.IP, curSpider.AdminPort, connErr.Error())
			continue
		}
		defer sw.DisconnectTdbctlNode(tdbctlDB)

		tdbctlList, queryErr := sw.SelectTdbctlNodes(tdbctlDB)
		if queryErr != nil {
			sw.ReportLogf(switchlogger.SwitchWarn, "failed to get tdbctl nodes info from tdbctl(%s:%d), errmsg: %s",
				curSpider.IP, curSpider.AdminPort, queryErr.Error())
			continue
		}

		sw.TdbctlNodes = nil
		sw.TdbctlNodes = append(sw.TdbctlNodes, tdbctlList...)
		break
	}

	if len(sw.TdbctlNodes) == 0 {
		return gerrors.Newf(gerrors.Failure,
			"failed to query tdbctl nodes info from all valid tdbctl nodes in cluster %s", sw.Cluster)
	}

	return nil
}

// QueryRouteInfoOfCluster query route info of current cluster from primary tdbctl node
func (sw *TenDBClusterBaseSwitchInstance) QueryRouteInfoOfCluster(primaryTdbctlDB *hamysql.GormDB) error {
	if primaryTdbctlDB == nil {
		return gerrors.Newf(gerrors.Failure, "primary tdbctl connection is nil when querying route info")
	}

	routeInfo, queryErr := sw.SelectRouteInfo(primaryTdbctlDB)
	if queryErr != nil {
		sw.ReportLogf(switchlogger.SwitchWarn, "failed to get route info from primary tdbctl(%s:%d), errmsg: %s",
			sw.PrimaryTdbctl.Host, sw.PrimaryTdbctl.Port, queryErr.Error())
		return queryErr
	}
	sw.TdbctlRouteTable = nil
	sw.TdbctlRouteTable = append(sw.TdbctlRouteTable, routeInfo...)
	return nil
}

// GetRouteInfoFromCache get route info from route table cache
func (sw *TenDBClusterBaseSwitchInstance) GetRouteInfoFromCache(host string, port int) (*TdbctlRouteInfo, bool) {
	for _, node := range sw.TdbctlRouteTable {
		if (node.Host == host) && (node.Port == port) {
			return CopyConstructTdbctlRoute(&node), true
		}
	}
	return nil, false
}

// TenDBClusterSpiderSwitchInstance switch instance for spider
type TenDBClusterSpiderSwitchInstance struct {
	TenDBClusterBaseSwitchInstance

	// The following are instance metadata information from DBM

	SpiderRole dbm.DbmMetadataSpiderRole

	// Whether primary tdbctl is changed
	PrimaryTdbctlIsChanged bool
	// Secondary tdbctl nodes that may need to change master
	SecondaryTdbctlNodes []TdbctlNodeInfo
}

// GetInstanceRole returns the role of this instance
func (sw *TenDBClusterSpiderSwitchInstance) GetInstanceRole() dbm.DbmMetadataInstanceRole {
	return dbm.DbmMetadataInstanceRole(sw.SpiderRole)
}

// GetInstanceInfo returns instance information as string
func (sw *TenDBClusterSpiderSwitchInstance) GetInstanceInfo() string {
	infoStr := fmt.Sprintf("{bk_cloud_id:%d, ip:%s, port:%d, admin_port:%d, bk_idc_city_id:%d, "+
		"bk_biz_id:%d, status:%s, cluster:%s, cluster_id:%d, cluster_type:%s, machine_type:%s, spider_role:%s}",
		sw.BkCloudID, sw.IP, sw.Port, sw.AdminPort, sw.BkIdcCityID, sw.BkBizID, sw.Status, sw.Cluster,
		sw.ClusterID, sw.ClusterType, sw.MachineType, sw.SpiderRole)
	return infoStr
}

// ToTdbctlName convert tdbctl node to formatted name
func (sw *TenDBClusterSpiderSwitchInstance) ToTdbctlName(node *TdbctlNodeInfo) string {
	return fmt.Sprintf("%s(%s:%d)", node.ServerName, node.Host, node.Port)
}

// ToNodeName convert node route info to formatted name
func (sw *TenDBClusterSpiderSwitchInstance) ToNodeName(node *TdbctlRouteInfo) string {
	return fmt.Sprintf("%s(%s:%d)", node.ServerName, node.Host, node.Port)
}

// UnmarshalTdbctlReplInfo unmarshal tdbctl replication info
func (sw *TenDBClusterSpiderSwitchInstance) UnmarshalTdbctlReplInfo(replicationInfo string) (*TdbctlNodeReplInfo, error) {
	replInfo := &TdbctlNodeReplInfo{}
	if err := json.Unmarshal([]byte(replicationInfo), replInfo); err != nil {
		return nil, err
	}

	logFileparts := strings.Split(replInfo.RelayMasterLogFile, ".")
	if len(logFileparts) < 2 {
		return replInfo, gerrors.Newf(gerrors.Failure, "invalid relay master log file: %s", replInfo.RelayMasterLogFile)
	}

	logFileIndex, convErr := strconv.Atoi(logFileparts[1])
	if convErr != nil {
		return replInfo, gerrors.Newf(gerrors.Failure, "invalid index part of relay master log file: %s",
			replInfo.RelayMasterLogFile)
	}
	replInfo.RelayMasterLogFileIndex = logFileIndex

	execPos, parseErr := strconv.ParseUint(replInfo.ExecMasterLogPos, 10, 64)
	if parseErr != nil {
		return replInfo, gerrors.Newf(gerrors.Failure, "invalid exec master log pos: %s", replInfo.ExecMasterLogPos)
	}
	replInfo.ExecMasterLogPosInt = execPos

	return replInfo, nil
}

// CheckBeforeSwitch check slave before switch
func (sw *TenDBClusterSpiderSwitchInstance) CheckBeforeSwitch() (switchcore.SwitchCheckCode, error) {
	switch sw.SpiderRole {
	case dbm.TenDBClusterSpiderMaster:
		return switchcore.SwitchRequired, nil
	case dbm.TenDBClusterSpiderSlave:
		sw.ReportLogf(switchlogger.SwitchInfo, "this is a spider slave node, no need to check")
		return switchcore.SwitchRequired, nil
	default:
		err := gerrors.Newf(gerrors.Failure, "invalid instance role: %s", sw.SpiderRole)
		sw.ReportLogf(switchlogger.SwitchWarn, "%s", err.Error())
		return switchcore.SwitchCheckUnpass, err
	}
}

// TdbctlEnablePrimary connect tdbctl and execute TDBCTL ENABLE PRIMARY [FORCE]
func (sw *TenDBClusterSpiderSwitchInstance) TdbctlEnablePrimary(tdbctlHost string, tdbctlPort int, force bool) error {
	tdbctlDB, connErr := sw.ConnectTdbctlNode(tdbctlHost, tdbctlPort)
	if connErr != nil {
		return connErr
	}
	defer sw.DisconnectTdbctlNode(tdbctlDB)

	enablePimarySql := TdbctlEnablePrimarySql
	if force {
		enablePimarySql = TdbctlEnablePrimaryForceSql
	}

	if result := tdbctlDB.DB().Exec(enablePimarySql); result.Error != nil {
		sw.ReportLogf(switchlogger.SwitchWarn, "when enabling primary, failed to execute sql(%s) on tdbctl(%s:%d), errmsg: %s",
			enablePimarySql, tdbctlHost, tdbctlPort, result.Error.Error())
		return result.Error
	}

	sw.ReportLogf(switchlogger.SwitchInfo, "successfully enable primary on tdbctl(%s:%d)", tdbctlHost, tdbctlPort)
	return nil
}

// ElectNewPrimaryTdbctl elect new primary tdbctl
func (sw *TenDBClusterSpiderSwitchInstance) ElectNewPrimaryTdbctl() (*TdbctlNodeInfo, error) {
	var electNode *TdbctlNodeInfo
	var tdbctlReplMaster *string
	maxLogFileIndex, maxExecLogPos := -1, uint64(0)

	sw.ReportLogf(switchlogger.SwitchInfo, "try to elect the new primary tdbctl of cluster(%s)", sw.Cluster)
	if len(sw.TdbctlNodes) == 0 {
		return nil, gerrors.New(gerrors.Failure, "no tdbctl node is provided to elect the new primary tdbctl")
	}

	sw.SecondaryTdbctlNodes = nil
	for nodeIndex, node := range sw.TdbctlNodes {
		// Skip current primary
		if (sw.PrimaryTdbctl != nil) && (node.ServerName == sw.PrimaryTdbctl.ServerName) {
			sw.ReportLogf(switchlogger.SwitchInfo, "when selecting new primary, skip current primary(%s)", sw.ToTdbctlName(&node))
			continue
		}

		// Assert that there are no other primary nodes
		if strings.EqualFold(node.ClusterRole, PrimaryTdbctlRole) {
			return nil, gerrors.Newf(gerrors.Failure, "unexpectedly found another primary(%s)", sw.ToTdbctlName(&node))
		}

		// Skip node which is not secondary
		if !strings.EqualFold(node.ClusterRole, SecondaryTdbctlRole) {
			sw.ReportLogf(switchlogger.SwitchInfo, "when selecting new primary, skip tdbctl(%s) as it is not secondary",
				sw.ToTdbctlName(&node))
			continue
		}

		// Record secondary nodes. Change master for them later if the primary tdbctl is changed
		sw.SecondaryTdbctlNodes = append(sw.SecondaryTdbctlNodes, node)

		// All secondary node's REPLICATION_MASTER must be the same
		if tdbctlReplMaster == nil {
			tdbctlReplMaster = &node.ReplicationMaster
		} else if node.ReplicationMaster != *tdbctlReplMaster {
			errMsg := fmt.Sprintf("found multiple replication masters(%s, %s)", node.ReplicationMaster, *tdbctlReplMaster)
			return nil, gerrors.New(gerrors.Failure, errMsg)
		}

		// Parse replication info
		replInfo, err := sw.UnmarshalTdbctlReplInfo(node.ReplicationInfo)
		if err != nil {
			sw.ReportLogf(switchlogger.SwitchWarn, "when selecting new primary, failed to parse replication info of secondary(%s): %s",
				sw.ToTdbctlName(&node), err.Error())
			continue
		}
		sw.ReportLogf(switchlogger.SwitchInfo, "parsed replication info of tdbctl(%s): %s",
			sw.ToTdbctlName(&node), converter.ToStrIgnoreErr(replInfo))

		// Slave IO running may be broken but Slave SQL running should be Yes
		if !strings.EqualFold(replInfo.SlaveSQLRunning, "Yes") {
			sw.ReportLogf(switchlogger.SwitchWarn, "when selecting new primary, found Slave_SQL_Running of secondary(%s) is not Yes",
				sw.ToTdbctlName(&node))
			continue
		}

		// Select secondary tdbctl with smaller replication delay
		if (replInfo.RelayMasterLogFileIndex > maxLogFileIndex) ||
			((replInfo.RelayMasterLogFileIndex == maxLogFileIndex) && (replInfo.ExecMasterLogPosInt > maxExecLogPos)) {
			maxLogFileIndex, maxExecLogPos = replInfo.RelayMasterLogFileIndex, replInfo.ExecMasterLogPosInt
			electNode = &sw.TdbctlNodes[nodeIndex]
			sw.ReportLogf(switchlogger.SwitchInfo, "when selecting new primary, found replication delay of secondary(%s) is smaller",
				sw.ToTdbctlName(&node))
		}
	}

	if electNode != nil {
		sw.ReportLogf(switchlogger.SwitchInfo, "successfully elected the new primary tdbctl in cluster(%s): %s",
			sw.Cluster, sw.ToTdbctlName(electNode))
		return CopyConstructTdbctlNode(electNode), nil
	}

	return nil, gerrors.Newf(gerrors.Failure, "found no suitable secondary tdbctl that can be used as the new primary")
}

// HandleInvolvedPrimaryTdbctl changes the primary tdbctl if it belongs to the broken spider
func (sw *TenDBClusterSpiderSwitchInstance) HandleInvolvedPrimaryTdbctl() error {
	if sw.PrimaryTdbctl == nil {
		sw.ReportLogf(switchlogger.SwitchWarn, "when handling involved primary tdbctl, the primary tdbctl is nil")
		return gerrors.Newf(gerrors.Failure, "the primary tdbctl is nil")
	}

	if !sw.PrimaryTdbctl.IsThisServer {
		sw.ReportLogf(switchlogger.SwitchInfo, "the primary tdbctl(%s:%d) does not belong to current broken spider(%s:%d), "+
			"skip electing new primary tdbctl", sw.PrimaryTdbctl.Host, sw.PrimaryTdbctl.Port, sw.IP, sw.Port)
		return nil
	}

	sw.ReportLogf(switchlogger.SwitchInfo, "the primary tdbctl(%s:%d) belongs to current broken spider(%s:%d), "+
		"try to elect new primary tdbctl", sw.PrimaryTdbctl.Host, sw.PrimaryTdbctl.Port, sw.IP, sw.Port)

	newPrimaryTdbctl, err := sw.ElectNewPrimaryTdbctl()
	if err != nil {
		sw.ReportLogf(switchlogger.SwitchWarn, "failed to elect new primary tdbctl of cluster(%s): %s", sw.Cluster, err.Error())
		return err
	}

	// We defer the stop slave operation to DoFinal()
	// because it may fail and should not affect the current switch process
	if err = sw.TdbctlEnablePrimary(newPrimaryTdbctl.Host, newPrimaryTdbctl.Port, true); err != nil {
		sw.ReportLogf(switchlogger.SwitchWarn, "failed to enable new primary tdbctl(%s:%d) of cluster(%s): %s",
			newPrimaryTdbctl.Host, newPrimaryTdbctl.Port, sw.Cluster, err.Error())
		return err
	}
	sw.PrimaryTdbctlIsChanged = true

	sw.PrimaryTdbctl = &TdbctlPrimaryNodeInfo{
		ServerName:   newPrimaryTdbctl.ServerName,
		Host:         newPrimaryTdbctl.Host,
		Port:         newPrimaryTdbctl.Port,
		ClusterRole:  newPrimaryTdbctl.ClusterRole,
		Status:       newPrimaryTdbctl.Status,
		IsThisServer: (newPrimaryTdbctl.Host == sw.IP) && (newPrimaryTdbctl.Port == sw.AdminPort),
	}

	if sw.PrimaryTdbctl.IsThisServer {
		errMsg := fmt.Sprintf("the elected new primary tdbctl(%s:%d) still belongs to current broken spider(%s:%d)",
			newPrimaryTdbctl.Host, newPrimaryTdbctl.Port, sw.IP, sw.Port)
		sw.ReportLogf(switchlogger.SwitchWarn, "%s", errMsg)
		return gerrors.New(gerrors.Failure, errMsg)
	}

	sw.ReportLogf(switchlogger.SwitchInfo, "successfully changed primary tdbctl to (%s:%d) in cluster(%s)",
		newPrimaryTdbctl.Host, newPrimaryTdbctl.Port, sw.Cluster)
	return nil
}

// DeleteOwnRoutes remove route items of current broken spider (and its tdbctl if exists) from cluster route table
func (sw *TenDBClusterSpiderSwitchInstance) DeleteOwnRoutes(primaryTdbctlDB *hamysql.GormDB) error {
	curSpiderRoute, curSpiderExists := sw.GetRouteInfoFromCache(sw.IP, sw.Port)
	if !curSpiderExists {
		errMsg := fmt.Sprintf("failed to get route info of current spider(%s:%d) from route cache", sw.IP, sw.Port)
		sw.ReportLogf(switchlogger.SwitchWarn, "when deleting own routes, %s", errMsg)
		return gerrors.New(gerrors.Failure, errMsg)
	}

	if primaryTdbctlDB == nil {
		errMsg := "primary tdbctl connection is nil when dropping own routes"
		sw.ReportLogf(switchlogger.SwitchWarn, "%s", errMsg)
		return gerrors.Newf(gerrors.Failure, "%s", errMsg)
	}

	if err := sw.TdbctlDropNode(primaryTdbctlDB, curSpiderRoute.ServerName); err != nil {
		sw.ReportLogf(switchlogger.SwitchWarn, "failed to delete route item of %s on primary(%s:%d): %s",
			sw.ToNodeName(curSpiderRoute), sw.PrimaryTdbctl.Host, sw.PrimaryTdbctl.Port, err.Error())
		return err
	}

	// spider_slave nodes do not have corresponding tdbctl nodes, only spider_master nodes have tdbctl
	if sw.SpiderRole == dbm.TenDBClusterSpiderSlave {
		sw.ReportLogf(switchlogger.SwitchInfo, "spider_slave(%s:%d) does not have corresponding tdbctl, skip deleting tdbctl route",
			sw.IP, sw.Port)
		sw.ReportLogf(switchlogger.SwitchInfo, "successfully deleted route item of %s on primary(%s:%d)",
			sw.ToNodeName(curSpiderRoute), sw.PrimaryTdbctl.Host, sw.PrimaryTdbctl.Port)
		return nil
	}

	curTdbctlRoute, curTdbctlExists := sw.GetRouteInfoFromCache(sw.IP, sw.AdminPort)
	if !curTdbctlExists {
		errMsg := fmt.Sprintf("failed to get route info of current tdbctl(%s:%d) from route cache", sw.IP, sw.AdminPort)
		sw.ReportLogf(switchlogger.SwitchWarn, "when deleting own routes, %s", errMsg)
		return gerrors.New(gerrors.Failure, errMsg)
	}

	if err := sw.TdbctlDropNode(primaryTdbctlDB, curTdbctlRoute.ServerName); err != nil {
		sw.ReportLogf(switchlogger.SwitchWarn, "failed to delete route item of %s on primary(%s:%d): %s",
			sw.ToNodeName(curTdbctlRoute), sw.PrimaryTdbctl.Host, sw.PrimaryTdbctl.Port, err.Error())
		return err
	}

	sw.ReportLogf(switchlogger.SwitchInfo, "successfully deleted two route items of %s and %s on primary(%s:%d)",
		sw.ToNodeName(curSpiderRoute), sw.ToNodeName(curTdbctlRoute), sw.PrimaryTdbctl.Host, sw.PrimaryTdbctl.Port)
	return nil
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
	sw.ReportLogf(switchlogger.SwitchInfo, "switch step 1: try to delete this spider instance from all bound entries")
	if err := sw.DeleteNameService(sw.BindEntry); err != nil {
		return err
	}

	sw.ReportLogf(switchlogger.SwitchInfo, "switch step 2: try to query all spider/tdbctl nodes of this cluster from DBM")
	if err := sw.QuerySpiderNodesOfCluster(); err != nil {
		return err
	}

	sw.ReportLogf(switchlogger.SwitchInfo, "switch step 3: try to query all tdbctl nodes' status from any valid tdbctl node")
	if err := sw.QueryTdbctlNodesOfCluster(); err != nil {
		return err
	}

	sw.ReportLogf(switchlogger.SwitchInfo, "switch step 4: try to find the primary tdbctl")
	if err := sw.FindPrimaryTdbctl(); err != nil {
		return err
	}

	sw.ReportLogf(switchlogger.SwitchInfo, "switch step 5: change primary tdbctl if it belongs to current broken spider")
	if err := sw.HandleInvolvedPrimaryTdbctl(); err != nil {
		return err
	}

	sw.ReportLogf(switchlogger.SwitchInfo, "switch step 6: try to connect primary tdbctl")
	primaryTdbctlConn, connErr := sw.ConnectTdbctlNode(sw.PrimaryTdbctl.Host, sw.PrimaryTdbctl.Port)
	if connErr != nil {
		return connErr
	}
	defer sw.DisconnectTdbctlNode(primaryTdbctlConn)

	sw.ReportLogf(switchlogger.SwitchInfo, "switch step 7: try to query route info of this cluster from primary tdbctl")
	if err := sw.QueryRouteInfoOfCluster(primaryTdbctlConn); err != nil {
		return err
	}

	sw.ReportLogf(switchlogger.SwitchInfo, "switch step 8: try to delete broken-down spider and its tdbctl from cluster route table ")
	if err := sw.DeleteOwnRoutes(primaryTdbctlConn); err != nil {
		return err
	}

	sw.ReportLogf(switchlogger.SwitchInfo, "switch step 9: try to flush route table")
	if err := sw.TdbctlFlushRouting(primaryTdbctlConn, true); err != nil {
		return err
	}

	return nil
}

// DoFinal repair replication relationship if the primary tdbctl is changed
func (sw *TenDBClusterSpiderSwitchInstance) DoFinal() error {
	if sw.PrimaryTdbctlIsChanged {
		sw.ReportLog(switchlogger.SwitchInfo, "try to repair replication relationship for new primary tdbctl")

		if sw.PrimaryTdbctl == nil {
			return gerrors.New(gerrors.Failure, "when repairing replication relationship, primary tdbctl is nil")
		}
		primaryHost := sw.PrimaryTdbctl.Host
		primaryPort := sw.PrimaryTdbctl.Port

		_, _, resetSlaveErr := sw.ResetSlaveWithBinlogPos(primaryHost, primaryPort)
		if resetSlaveErr != nil {
			sw.ReportLogf(switchlogger.SwitchWarn, "failed to reset slave on new primary(%s:%d): %s",
				primaryHost, primaryPort, resetSlaveErr.Error())
			return resetSlaveErr
		}

		changeMasterSql := fmt.Sprintf(TdbctlChangeMasterSql, primaryHost, primaryPort)
		failureOccurred := false
		validSecondaryCount := 0
		for _, node := range sw.SecondaryTdbctlNodes {
			if node.ServerName == sw.PrimaryTdbctl.ServerName {
				continue
			}
			validSecondaryCount++

			if changeMasterErr := sw.ChangeMasterAuto(node.Host, node.Port, changeMasterSql); changeMasterErr != nil {
				failureOccurred = true
				sw.ReportLogf(switchlogger.SwitchWarn, "failed to change master to primary(%s:%d) for secondary tdbctl(%s): %s",
					primaryHost, primaryPort, sw.ToTdbctlName(&node), changeMasterErr.Error())
			}
		}

		if validSecondaryCount == 0 {
			sw.ReportLog(switchlogger.SwitchInfo, "no valid secondary nodes need to change master to the new primary tdbctl")
			return nil
		}
		if failureOccurred {
			errMsg := "not all secondary tdbctl successfully changed the master to the new primary tdbctl"
			sw.ReportLogf(switchlogger.SwitchWarn, "%s", errMsg)
			return gerrors.New(gerrors.Failure, errMsg)
		}
		sw.ReportLog(switchlogger.SwitchInfo, "successfully changed master to the new primary tdbctl for all valid secondary tdbctl nodes")
	}

	return nil
}

// TenDBClusterRemoteSwitchInstance switch instance for remote
type TenDBClusterRemoteSwitchInstance struct {
	TenDBClusterBaseSwitchInstance
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

	if err := sw.CheckSlaveStatus(); err != nil {
		sw.ReportLog(switchlogger.SwitchWarn, err.Error())
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
	case dbm.TenDBClusterStorageSlave:
		sw.ReportLogf(switchlogger.SwitchInfo, "this is a slave node, no need to check")
		return switchcore.SwitchNotNeeded, nil
	case dbm.TenDBClusterStorageMaster:
		return sw.CheckTenDBClusterStorageMaster()
	default:
		err := gerrors.Newf(gerrors.Failure, "invalid instance role: %s", sw.InstanceRole)
		sw.ReportLogf(switchlogger.SwitchWarn, "%s", err.Error())
		return switchcore.SwitchCheckUnpass, err
	}
}

// FindMasterSlavePair find current master and standby slave from route cache
func (sw *TenDBClusterRemoteSwitchInstance) FindMasterSlavePair() (*TdbctlRouteInfo, *TdbctlRouteInfo, error) {
	curMasterRoute, curMasterExists := sw.GetRouteInfoFromCache(sw.IP, sw.Port)
	if !curMasterExists {
		errMsg := fmt.Sprintf("failed to get route info of current remote master(%s:%d) from route cache", sw.IP, sw.Port)
		sw.ReportLogf(switchlogger.SwitchWarn, "when looking up route info, %s", errMsg)
		return nil, nil, gerrors.New(gerrors.Failure, errMsg)
	}

	curSlaveRoute, curSlaveExists := sw.GetRouteInfoFromCache(sw.StandBySlave.Ip, sw.StandBySlave.Port)
	if !curSlaveExists {
		errMsg := fmt.Sprintf("failed to get route info of current remote slave(%s:%d) from route cache", sw.IP, sw.Port)
		sw.ReportLogf(switchlogger.SwitchWarn, "when looking up route info, %s", errMsg)
		return curMasterRoute, nil, gerrors.New(gerrors.Failure, errMsg)
	}

	sw.ReportLogf(switchlogger.SwitchInfo, "successfully get route info of current remote master(%s:%d) and its remote slave(%s:%d)",
		sw.IP, sw.Port, sw.StandBySlave.Ip, sw.StandBySlave.Port)
	return curMasterRoute, curSlaveRoute, nil
}

// UpdateMasterRouteToSlave update master route to slave on primary tdbctl
func (sw *TenDBClusterRemoteSwitchInstance) UpdateMasterRouteToSlave(primaryTdbctlDB *hamysql.GormDB,
	masterRoute *TdbctlRouteInfo, slaveRoute *TdbctlRouteInfo) error {
	alterNodeSQL := fmt.Sprintf(TdbctlAlterNodeSql, masterRoute.ServerName, slaveRoute.Host, slaveRoute.Port,
		slaveRoute.UserName, slaveRoute.Password)

	result := primaryTdbctlDB.DB().Exec(alterNodeSQL)
	if result.Error != nil {
		errMsg := fmt.Sprintf("failed to execute sql(%s) on tdbctl(%s:%d), errmsg: %s",
			alterNodeSQL, primaryTdbctlDB.Host(), primaryTdbctlDB.Port(), result.Error.Error())
		sw.ReportLogf(switchlogger.SwitchWarn, "when updating master route to slave, %s", errMsg)
		return gerrors.New(gerrors.Failure, errMsg)
	}

	if result.RowsAffected != 1 {
		errMsg := fmt.Sprintf("cannot ensure that the number of rows affected is 1, affected: %d",
			result.RowsAffected)
		sw.ReportLogf(switchlogger.SwitchWarn, "when updating master route to slave, %s", errMsg)
		return gerrors.New(gerrors.Failure, errMsg)
	}

	sw.ReportLogf(switchlogger.SwitchInfo, "successfully updated master(%s) route to slave(%s) on tdbctl(%s:%d)",
		masterRoute.ServerName, slaveRoute.ServerName, primaryTdbctlDB.Host(), primaryTdbctlDB.Port())
	return nil
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
	sw.ReportLogf(switchlogger.SwitchInfo, "switch step 1: try to query all spider/tdbctl nodes of this cluster from DBM")
	if err := sw.QuerySpiderNodesOfCluster(); err != nil {
		return err
	}

	sw.ReportLogf(switchlogger.SwitchInfo, "switch step 2: try to query all tdbctl nodes' status from any valid tdbctl node")
	if err := sw.QueryTdbctlNodesOfCluster(); err != nil {
		return err
	}

	sw.ReportLogf(switchlogger.SwitchInfo, "switch step 3: try to find the primary tdbctl")
	if err := sw.FindPrimaryTdbctl(); err != nil {
		return err
	}

	sw.ReportLogf(switchlogger.SwitchInfo, "switch step 4: try to connect primary tdbctl")
	primaryTdbctlConn, connErr := sw.ConnectTdbctlNode(sw.PrimaryTdbctl.Host, sw.PrimaryTdbctl.Port)
	if connErr != nil {
		return connErr
	}
	defer sw.DisconnectTdbctlNode(primaryTdbctlConn)

	sw.ReportLogf(switchlogger.SwitchInfo, "switch step 5: try to query route info of this cluster from primary tdbctl")
	if err := sw.QueryRouteInfoOfCluster(primaryTdbctlConn); err != nil {
		return err
	}

	sw.ReportLogf(switchlogger.SwitchInfo, "switch step 6: try to find nodes info of current broken remote master and its slave")
	curMasterRoute, curSlaveRoute, notFoundErr := sw.FindMasterSlavePair()
	if notFoundErr != nil {
		return notFoundErr
	}

	sw.ReportLogf(switchlogger.SwitchInfo, "switch step 7: try to reset slave for current remote slave")
	_, _, err := sw.ResetSlaveWithBinlogPos(sw.StandBySlave.Ip, sw.StandBySlave.Port)
	if err != nil {
		err = gerrors.Newf(gerrors.Failure, "failed to reset slave status for the remote slave(%s:%d), errmsg: %s",
			sw.StandBySlave.Ip, sw.StandBySlave.Port, err.Error())
		sw.ReportLog(switchlogger.SwitchWarn, err.Error())
		return err
	}

	sw.ReportLogf(switchlogger.SwitchInfo, "switch step 8: try to update route info of current broken remote master and its slave")
	if err := sw.UpdateMasterRouteToSlave(primaryTdbctlConn, curMasterRoute, curSlaveRoute); err != nil {
		return err
	}

	sw.ReportLogf(switchlogger.SwitchInfo, "switch step 9: try to flush route table")
	if err := sw.TdbctlFlushRouting(primaryTdbctlConn, true); err != nil {
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
