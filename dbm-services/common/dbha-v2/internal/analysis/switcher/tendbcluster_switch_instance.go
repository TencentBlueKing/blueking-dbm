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

package switcher

import (
	"bk-dbconfig/pkg/core/logger"
	"encoding/json"
	"fmt"
	"strconv"
	"strings"

	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/internal/analysis/dbm"
	"dbm-services/common/dbha-v2/pkg/converter"
	"dbm-services/common/dbha-v2/pkg/gerrors"
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
	ServerName string `db:"Server_name"`
	Host       string `db:"Host"`
	UserName   string `db:"Username"`
	Password   string `db:"Password"`
	Port       int    `db:"Port"`
	Wrapper    string `db:"Wrapper"`
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
	ServerName        string `db:"SERVER_NAME;NOT NULL"        json:"server_name"`
	Host              string `db:"HOST;NOT NULL"               json:"host"`
	Port              int    `db:"PORT;default:0;NOT NULL"     json:"port"`
	ReplicationMaster string `db:"REPLICATION_MASTER;NOT NULL" json:"replication_master"`
	ClusterRole       string `db:"CLUSTER_ROLE;NOT NULL"       json:"cluster_role"`
	Status            string `db:"STATUS;NOT NULL"             json:"status"`
	Message           string `db:"MESSAGE;NOT NULL"            json:"message"`
	ReplicationInfo   string `db:"REPLICATION_INFO;NOT NULL"   json:"replication_info"`
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

// TendbClusterInstanceMetadata contains TenDBCluster instance metadata from DBM
type TendbClusterInstanceMetadata dbm.DbInstMetadata

// NewTendbClusterSwitchInstance creates a new TenDBCluster switch instance based on metadata
func NewTendbClusterSwitchInstance(metadata *TendbClusterInstanceMetadata) (SwitchableInstance, error) {
	mysqlBaseInstance := MySQLBaseSwitchInstance{
		BaseSwitchInstance: BaseSwitchInstance{
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
			dbmClient:    &dbm.Client{},
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
	// TODO
	// case hamodel.DbmMetadataMachineTypeRemote:
	// 	res := &TenDBClusterRemoteSwitchInstance{
	// 		TenDBClusterBaseSwitchInstance: tendbClusterBaseInstance,
	// 	}
	// 	return res, nil

	case haprobe.DbmMetadataMachineTypeSpider:
		res := &TenDBClusterSpiderSwitchInstance{
			TenDBClusterBaseSwitchInstance: tendbClusterBaseInstance,
			SpiderRole:                     metadata.SpiderRole,
		}
		return res, nil

	default:
		logger.Error("Unknown machine type(%s) for MySQL switch instance constructor", metadata.MachineType)
		return nil, gerrors.New(gerrors.InvalidParameter, "Invalid machine type")
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

// GetNodeRoute get route info from route table by ip,port
func (sw *TenDBClusterBaseSwitchInstance) GetNodeRoute(host string, port int) *TdbctlRouteInfo {
	// todo
	return nil
}

// ConnectTdbctlNode connect tdbctl node
func (sw *TenDBClusterBaseSwitchInstance) ConnectTdbctlNode(tdbctlHost string, tdbctlPort int) (*hamysql.SqlxDB, error) {
	sw.ReportLogf(SwitchInfo, "Try to connect tdbctl node(%s:%d)", tdbctlHost, tdbctlPort)
	tdbctlUser := config.Cfg.Database.Mysql.User
	tdbctlPassword := config.Cfg.Database.Mysql.Password

	tdbctlDB, connErr := hamysql.NewSqlxDB(
		hamysql.OptionIP(tdbctlHost),
		hamysql.OptionPort(tdbctlPort),
		hamysql.OptionUser(tdbctlUser),
		hamysql.OptionPassword(tdbctlPassword),
	)

	if connErr != nil {
		sw.ReportLogf(SwitchWarn, "Failed to connect tdbctl node(%s:%d): %s", tdbctlHost, tdbctlPort, connErr.Error())
		return nil, connErr
	}
	sw.ReportLogf(SwitchInfo, "Success to connect tdbctl node(%s:%d)", tdbctlHost, tdbctlPort)
	return tdbctlDB, nil
}

// DisconnectTdbctlNode disconnect tdbctl node
func (sw *TenDBClusterBaseSwitchInstance) DisconnectTdbctlNode(tdbctlDB *hamysql.SqlxDB) {
	con := tdbctlDB.DB()
	if err := con.Close(); err != nil {
		logger.Errorf("Failed to close tdbctl connect(%s:%d): %s",
			sw.PrimaryTdbctl.Host, sw.PrimaryTdbctl.Port, err.Error())
		sw.ReportLogf(SwitchWarn, "Failed to close tdbctl connect(%s:%d): %s",
			sw.PrimaryTdbctl.Host, sw.PrimaryTdbctl.Port, err.Error())
	}
}

// SelectTdbctlNodes query tdbctl nodes info from information_schema.TDBCTL_NODES
func (sw *TenDBClusterBaseSwitchInstance) SelectTdbctlNodes(tdbctlDB *hamysql.SqlxDB) ([]TdbctlNodeInfo, error) {
	if tdbctlDB == nil {
		return nil, gerrors.New(gerrors.Failure, "tdbctl connection is nil")
	}

	var tdbctlList []TdbctlNodeInfo
	queryErr := tdbctlDB.DB().Select(&tdbctlList, SelectTdbctlNodesSql)
	if queryErr != nil {
		return nil, gerrors.Newf(gerrors.Failure, "failed to execute sql(%s) on tdbctl(%s:%d), errmsg: %s",
			SelectTdbctlNodesSql, tdbctlDB.Host(), tdbctlDB.Port(), queryErr.Error())
	}

	if len(tdbctlList) == 0 {
		return nil, gerrors.New(gerrors.Failure, "no tdbctl node found")
	}

	nodesInfo, convertErr := converter.ToJsonStr(tdbctlList)
	if convertErr != nil {
		logger.Errorf("failed to convert tdbctl nodes info to json, err: %s", convertErr.Error())
		nodesInfo = fmt.Sprintf("%v", tdbctlList)
	}
	sw.ReportLogf(SwitchInfo, "Success to query all tdbctl nodes info from tdbctl node(%s:%d): %s",
		tdbctlDB.Host(), tdbctlDB.Port(), nodesInfo)

	return tdbctlList, nil
}

// SelectRouteInfo query route info from mysql.servers
func (sw *TenDBClusterBaseSwitchInstance) SelectRouteInfo(tdbctlDB *hamysql.SqlxDB) ([]TdbctlRouteInfo, error) {
	if tdbctlDB == nil {
		return nil, gerrors.New(gerrors.Failure, "tdbctl connection is nil")
	}

	sw.ReportLogf(SwitchInfo, "Try to execute sql(%s) on tdbctl(%s:%d)",
		SelectRouteInfoSql, tdbctlDB.Host(), tdbctlDB.Port())
	var routeInfoList []TdbctlRouteInfo
	queryErr := tdbctlDB.DB().Select(&routeInfoList, SelectRouteInfoSql)
	if queryErr != nil {
		return nil, gerrors.Newf(gerrors.Failure, "failed to execute sql(%s) on tdbctl(%s:%d), errmsg: %s",
			SelectRouteInfoSql, tdbctlDB.Host(), tdbctlDB.Port(), queryErr.Error())
	}

	if len(routeInfoList) == 0 {
		return nil, gerrors.New(gerrors.Failure, "no server found")
	}

	routesStr, convertErr := converter.ToJsonStr(routeInfoList)
	if convertErr != nil {
		logger.Errorf("failed to convert routes to json, err: %s", convertErr.Error())
		routesStr = fmt.Sprintf("%v", routeInfoList)
	}
	sw.ReportLogf(SwitchInfo, "Success to query routes from tdbctl node(%s:%d): %s",
		tdbctlDB.Host(), tdbctlDB.Port(), routesStr)

	return routeInfoList, nil
}

// TdbctlDropNode drop node from tdbctl
func (sw *TenDBClusterBaseSwitchInstance) TdbctlDropNode(tdbctlDB *hamysql.SqlxDB, nodeName string) error {
	if tdbctlDB == nil {
		return gerrors.New(gerrors.Failure, "tdbctl connection is nil")
	}

	dropNodeSql := fmt.Sprintf(TdbctlDropNodeSql, nodeName)
	sw.ReportLogf(SwitchInfo, "Try to execute sql(%s) on tdbctl(%s:%d)",
		dropNodeSql, tdbctlDB.Host(), tdbctlDB.Port())

	result, execErr := tdbctlDB.DB().Exec(dropNodeSql)
	if execErr != nil {
		return gerrors.Newf(gerrors.Failure, "failed to execute sql(%s) on tdbctl(%s:%d), errmsg: %s",
			TdbctlDropNodeSql, tdbctlDB.Host(), tdbctlDB.Port(), execErr.Error())
	}

	affected, rowErr := result.RowsAffected()
	if (rowErr != nil) || (affected != 1) {
		return gerrors.Newf(gerrors.Failure, "Cannot ensure that the number of rows affected is 1, errmsg: %s",
			rowErr.Error())
	}

	sw.ReportLogf(SwitchInfo, "Succeeded to drop node(%s) on tdbctl(%s:%d)", nodeName, tdbctlDB.Host(), tdbctlDB.Port())
	return nil
}

// TdbctlFlushRouting flush routing on tdbctl
func (sw *TenDBClusterBaseSwitchInstance) TdbctlFlushRouting(tdbctlDB *hamysql.SqlxDB, force bool) error {
	if tdbctlDB == nil {
		return gerrors.New(gerrors.Failure, "tdbctl connection is nil")
	}

	flushRouteSql := TdbctlFlushRouteSql
	if force {
		flushRouteSql = TdbctlFlushRouteForceSql
	}

	sw.ReportLogf(SwitchInfo, "Try to execute sql(%s) on tdbctl(%s:%d)",
		flushRouteSql, tdbctlDB.Host(), tdbctlDB.Port())

	if _, execErr := tdbctlDB.DB().Exec(flushRouteSql); execErr != nil {
		return gerrors.Newf(gerrors.Failure, "failed to execute sql(%s) on tdbctl(%s:%d), errmsg: %s",
			flushRouteSql, tdbctlDB.Host(), tdbctlDB.Port(), execErr.Error())
	}

	sw.ReportLogf(SwitchInfo, "Success to flush routing on tdbctl(%s:%d)", tdbctlDB.Host(), tdbctlDB.Port())
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

	sw.ReportLogf(SwitchInfo, "Try to find the primary tdbctl of cluster(%s)", sw.Cluster)

	if len(sw.TdbctlNodes) == 0 {
		return gerrors.New(gerrors.Failure, "No tdbctl node is provided to find the primary tdbctl")
	}

	for _, oneTdbctl := range sw.TdbctlNodes {
		oneTdbctlInfo := converter.ToStrIgnoreErr(oneTdbctl)
		sw.ReportLogf(SwitchInfo, "Check if node(%s) is the primary tdbctl", oneTdbctlInfo)

		if strings.EqualFold(oneTdbctl.ClusterRole, PrimaryTdbctlRole) {
			if sw.PrimaryTdbctl != nil {
				errMsg := fmt.Sprintf("Multiple primary tdbctl nodes(%s:%d, %s:%d) were found",
					sw.PrimaryTdbctl.Host, sw.PrimaryTdbctl.Port, oneTdbctl.Host, oneTdbctl.Port)
				sw.ReportLogf(SwitchWarn, "%s", errMsg)
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
				errMsg := fmt.Sprintf("Multiple replication master tdbctl nodes(%s, %s) were found",
					*masterServerName, oneTdbctl.ReplicationMaster)
				sw.ReportLogf(SwitchWarn, "%s", errMsg)
				return gerrors.New(gerrors.Failure, errMsg)
			}

			if masterServerName == nil {
				masterServerName = &oneTdbctl.ReplicationMaster
			}
		}
	}

	// if no primary tdbctl found, try to use the single replication master tdbctl as primary tdbctl
	if (sw.PrimaryTdbctl == nil) && (masterServerName != nil) {
		sw.ReportLogf(SwitchInfo, "The primary tdbctl of cluster(%s) is missing, "+
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
		sw.ReportLogf(SwitchInfo, "Successfully find the primary tdbctl node of cluster(%s): %s",
			sw.Cluster, primaryTdbctlInfo)
		return nil
	}

	sw.ReportLogf(SwitchWarn, "No primary tdbctl node was found in cluster(%s)", sw.Cluster)
	return gerrors.Newf(gerrors.Failure, "No primary tdbctl node was found in cluster(%s)", sw.Cluster)
}

// QuerySpiderNodesOfCluster query all spider nodes of current cluster from DBM
func (sw *TenDBClusterBaseSwitchInstance) QuerySpiderNodesOfCluster() error {
	sw.ReportLogf(SwitchInfo, "Try to query spider nodes of cluster(%s) from DBM", sw.Cluster)

	instInfoList, err := sw.dbmClient.QueryInstanceInfoByDomain(sw.BkCloudID, sw.Cluster)
	if err != nil {
		sw.ReportLogf(SwitchWarn, "Failed to query instance info of cluster(%s) from DBM: %s",
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
		sw.ReportLogf(SwitchWarn, "No spider instance of cluster %s found from DBM", sw.Cluster)
		return gerrors.Newf(gerrors.Failure, "no spider instance found in cluster %s", sw.Cluster)
	}

	sw.ReportLogf(SwitchInfo, "Successfully query spider nodes of cluster(%s) from DBM", sw.Cluster)
	return nil
}

// QueryTdbctlNodesOfCluster query all tdbctl nodes of current cluster from any tdbctl node
func (sw *TenDBClusterBaseSwitchInstance) QueryTdbctlNodesOfCluster() error {
	sw.ReportLogf(SwitchInfo, "Try to query tdbctl nodes of cluster(%s) from any valid tdbctl node", sw.Cluster)

	for _, curSpider := range sw.SpiderNodes {
		// only spider-master has tdbctl node
		if (curSpider.Status == dbm.Unavailable) || (curSpider.SpiderRole != dbm.TenDBClusterSpiderMaster) {
			continue
		}

		tdbctlDB, connErr := sw.ConnectTdbctlNode(curSpider.IP, curSpider.AdminPort)
		if connErr != nil {
			sw.ReportLogf(SwitchWarn, "Failed to connect tdbctl node(%s:%d): %s, try other nodes",
				curSpider.IP, curSpider.AdminPort, connErr.Error())
			continue
		}
		defer sw.DisconnectTdbctlNode(tdbctlDB)

		tdbctlList, queryErr := sw.SelectTdbctlNodes(tdbctlDB)
		if queryErr != nil {
			sw.ReportLogf(SwitchFail, "Failed to get tdbctl nodes info from tdbctl(%s:%d), errmsg: %s",
				curSpider.IP, curSpider.AdminPort, queryErr.Error())
			continue
		}

		sw.ReportLogf(SwitchInfo, "Success to get tdbctl nodes info from tdbctl(%s:%d)",
			curSpider.IP, curSpider.AdminPort)
		sw.TdbctlNodes = nil
		sw.TdbctlNodes = append(sw.TdbctlNodes, tdbctlList...)
		break
	}

	if len(sw.TdbctlNodes) == 0 {
		return gerrors.Newf(gerrors.Failure,
			"Failed to query tdbctl nodes info from all valid tdbctl nodes in cluster %s", sw.Cluster)
	}

	return nil
}

// QueryRouteInfoOfCluster query route info of current cluster from primary tdbctl node
func (sw *TenDBClusterBaseSwitchInstance) QueryRouteInfoOfCluster(primaryTdbctlDB *hamysql.SqlxDB) error {
	if primaryTdbctlDB == nil {
		return gerrors.Newf(gerrors.Failure, "primary tdbctl connection is nil when querying route info")
	}

	routeInfo, queryErr := sw.SelectRouteInfo(primaryTdbctlDB)
	if queryErr != nil {
		sw.ReportLogf(SwitchWarn, "Failed to get route info from primary tdbctl(%s:%d), errmsg: %s",
			sw.PrimaryTdbctl.Host, sw.PrimaryTdbctl.Port, queryErr.Error())
		return queryErr
	}
	sw.ReportLogf(SwitchInfo, "Success to get route info from primary tdbctl(%s:%d)",
		sw.PrimaryTdbctl.Host, sw.PrimaryTdbctl.Port)
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
		"bk_biz_id:%d, status:%s, cluster:%s, cluster_id:%d, cluster_type:%s, machine_type:%s, role:%s}",
		sw.BkCloudID, sw.IP, sw.Port, sw.AdminPort, sw.BkIdcCityID, sw.BkBizID, sw.Status, sw.Cluster,
		sw.ClusterID, sw.ClusterType, sw.MachineType, sw.InstanceRole)
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

	if _, err := tdbctlDB.DB().Exec(enablePimarySql); err != nil {
		sw.ReportLogf(SwitchWarn, "When enabling primary, failed to execute sql(%s) on tdbctl(%s:%d), errmsg: %s",
			enablePimarySql, tdbctlHost, tdbctlPort, err.Error())
		return err
	}

	sw.ReportLogf(SwitchInfo, "Successfully enable primary on tdbctl(%s:%d)", tdbctlHost, tdbctlPort)
	return nil
}

// ElectNewPrimaryTdbctl elect new primary tdbctl
func (sw *TenDBClusterSpiderSwitchInstance) ElectNewPrimaryTdbctl() (*TdbctlNodeInfo, error) {
	var electNode *TdbctlNodeInfo
	var tdbctlReplMaster *string
	maxLogFileIndex, maxExecLogPos := -1, uint64(0)

	sw.ReportLogf(SwitchInfo, "Try to elect the new primary tdbctl of cluster(%s)", sw.Cluster)
	if len(sw.TdbctlNodes) == 0 {
		return nil, gerrors.New(gerrors.Failure, "No tdbctl node is provided to elect the new primary tdbctl")
	}

	sw.SecondaryTdbctlNodes = nil
	for nodeIndex, node := range sw.TdbctlNodes {
		// Skip current primary
		if (sw.PrimaryTdbctl != nil) && (node.ServerName == sw.PrimaryTdbctl.ServerName) {
			sw.ReportLogf(SwitchInfo, "When selecting new primary, skip current primary(%s)", sw.ToTdbctlName(&node))
			continue
		}

		// Assert that there are no other primary nodes
		if strings.EqualFold(node.ClusterRole, PrimaryTdbctlRole) {
			return nil, gerrors.Newf(gerrors.Failure, "Unexpectedly found another primary(%s)", sw.ToTdbctlName(&node))
		}

		// Skip node which is not secondary
		if !strings.EqualFold(node.ClusterRole, SecondaryTdbctlRole) {
			sw.ReportLogf(SwitchInfo, "When selecting new primary, skip tdbctl(%s) as it is not secondary",
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
			sw.ReportLogf(SwitchWarn, "When selecting new primary, %s", errMsg)
			return nil, gerrors.New(gerrors.Failure, errMsg)
		}

		// Parse replication info
		replInfo, err := sw.UnmarshalTdbctlReplInfo(node.ReplicationInfo)
		if err != nil {
			sw.ReportLogf(SwitchWarn, "When selecting new primary, failed to parse replication info of secondary(%s): %s",
				sw.ToTdbctlName(&node), err.Error())
			continue
		}
		sw.ReportLogf(SwitchInfo, "Parsed replication info of tdbctl(%s): %s",
			sw.ToTdbctlName(&node), converter.ToStrIgnoreErr(replInfo))

		// Slave IO running may be broken but Slave SQL running should be Yes
		if !strings.EqualFold(replInfo.SlaveSQLRunning, "Yes") {
			sw.ReportLogf(SwitchWarn, "When selecting new primary, found Slave_SQL_Running of secondary(%s) is not Yes",
				sw.ToTdbctlName(&node))
			continue
		}

		// Select secondary tdbctl with smaller replication delay
		if (replInfo.RelayMasterLogFileIndex > maxLogFileIndex) ||
			((replInfo.RelayMasterLogFileIndex == maxLogFileIndex) && (replInfo.ExecMasterLogPosInt > maxExecLogPos)) {
			maxLogFileIndex, maxExecLogPos = replInfo.RelayMasterLogFileIndex, replInfo.ExecMasterLogPosInt
			electNode = &sw.TdbctlNodes[nodeIndex]
			sw.ReportLogf(SwitchInfo, "When selecting new primary, found replication delay of secondary(%s) is smaller",
				sw.ToTdbctlName(&node))
		}
	}

	if electNode != nil {
		sw.ReportLogf(SwitchInfo, "Success to elect the new primary in cluster(%s): %s",
			sw.Cluster, sw.ToTdbctlName(electNode))
		return CopyConstructTdbctlNode(electNode), nil
	}

	sw.ReportLogf(SwitchWarn, "Failed to elect the new primary tdbctl in cluster(%s)", sw.Cluster)
	return nil, gerrors.Newf(gerrors.Failure, "Found no suitable secondary tdbctl that can be used as the new primary")
}

// HandleInvolvedPrimaryTdbctl changes the primary tdbctl if it belongs to the broken spider
func (sw *TenDBClusterSpiderSwitchInstance) HandleInvolvedPrimaryTdbctl() error {
	if sw.PrimaryTdbctl == nil {
		sw.ReportLogf(SwitchInfo, "When handling involved primary tdbctl, the primary tdbctl is nil")
		return gerrors.Newf(gerrors.Failure, "the primary tdbctl is nil")
	}

	if !sw.PrimaryTdbctl.IsThisServer {
		sw.ReportLogf(SwitchInfo, "the primary tdbctl(%s:%d) does not belong to current broken spider(%s:%d), "+
			"skip electing new primary tdbctl", sw.PrimaryTdbctl.Host, sw.PrimaryTdbctl.Port, sw.IP, sw.Port)
		return nil
	}

	sw.ReportLogf(SwitchInfo, "the primary tdbctl(%s:%d) belongs to current broken spider(%s:%d), "+
		"try to elect new primary tdbctl", sw.PrimaryTdbctl.Host, sw.PrimaryTdbctl.Port, sw.IP, sw.Port)

	newPrimaryTdbctl, err := sw.ElectNewPrimaryTdbctl()
	if err != nil {
		sw.ReportLogf(SwitchWarn, "failed to elect new primary tdbctl of cluster(%s): %s", sw.Cluster, err.Error())
		return err
	}

	// We defer the stop slave operation to DoFinal()
	// because it may fail and should not affect the current switch process
	if err = sw.TdbctlEnablePrimary(newPrimaryTdbctl.Host, newPrimaryTdbctl.Port, true); err != nil {
		sw.ReportLogf(SwitchWarn, "failed to enable new primary tdbctl of cluster(%s): %s", sw.Cluster, err.Error())
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
		sw.ReportLogf(SwitchWarn, "%s", errMsg)
		return gerrors.New(gerrors.Failure, errMsg)
	}

	sw.ReportLogf(SwitchInfo, "Successfully change primary tdbctl to (%s:%d) in cluster(%s)",
		newPrimaryTdbctl.Host, newPrimaryTdbctl.Port, sw.Cluster)
	return nil
}

// DeleteOwnRoutes remove two route items of current broken spider and its tdbctl from cluster route table
func (sw *TenDBClusterSpiderSwitchInstance) DeleteOwnRoutes(primaryTdbctlDB *hamysql.SqlxDB) error {
	curSpiderRoute, curSpiderExists := sw.GetRouteInfoFromCache(sw.IP, sw.Port)
	if !curSpiderExists {
		errMsg := fmt.Sprintf("failed to get route info of current spider(%s:%d) from route cache", sw.IP, sw.Port)
		sw.ReportLogf(SwitchWarn, "When deleting own routes, %s", errMsg)
		return gerrors.New(gerrors.Failure, errMsg)
	}

	curTdbctlRoute, curTdbctlExists := sw.GetRouteInfoFromCache(sw.IP, sw.AdminPort)
	if !curTdbctlExists {
		errMsg := fmt.Sprintf("failed to get route info of current tdbctl(%s:%d) from route cache", sw.IP, sw.AdminPort)
		sw.ReportLogf(SwitchWarn, "When deleting own routes, %s", errMsg)
		return gerrors.New(gerrors.Failure, errMsg)
	}

	if primaryTdbctlDB == nil {
		return gerrors.Newf(gerrors.Failure, "primary tdbctl connection is nil when dropping own routes")
	}

	sw.ReportLogf(SwitchInfo, "Try to delete two route items of %s and %s on primary(%s:%d)",
		sw.ToNodeName(curSpiderRoute), sw.ToNodeName(curTdbctlRoute), sw.PrimaryTdbctl.Host, sw.PrimaryTdbctl.Port)

	if err := sw.TdbctlDropNode(primaryTdbctlDB, curSpiderRoute.ServerName); err != nil {
		sw.ReportLogf(SwitchFail, "Failed to delete route item of %s on primary(%s:%d): %s",
			sw.ToNodeName(curSpiderRoute), sw.PrimaryTdbctl.Host, sw.PrimaryTdbctl.Port, err.Error())
		return err
	}

	if err := sw.TdbctlDropNode(primaryTdbctlDB, curTdbctlRoute.ServerName); err != nil {
		sw.ReportLogf(SwitchFail, "Failed to delete route item of %s on primary(%s:%d): %s",
			sw.ToNodeName(curTdbctlRoute), sw.PrimaryTdbctl.Host, sw.PrimaryTdbctl.Port, err.Error())
		return err
	}

	sw.ReportLogf(SwitchInfo, "Success to delete two route items of %s and %s on primary(%s:%d)",
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
	sw.ReportLogf(SwitchInfo, "switch step 1: try to delete the spider instance(%s:%d) from all bound entries",
		sw.IP, sw.Port)
	if err := sw.DeleteNameService(sw.BindEntry); err != nil {
		return err
	}

	sw.ReportLogf(SwitchInfo, "switch step 2: try to query all spider/tdbctl nodes of this cluster from DBM")
	if err := sw.QuerySpiderNodesOfCluster(); err != nil {
		return err
	}

	sw.ReportLogf(SwitchInfo, "switch step 3: try to query all tdbctl nodes' status from any valid tdbctl node")
	if err := sw.QueryTdbctlNodesOfCluster(); err != nil {
		return err
	}

	sw.ReportLogf(SwitchInfo, "switch step 4: try to find the primary tdbctl")
	if err := sw.FindPrimaryTdbctl(); err != nil {
		return err
	}

	sw.ReportLogf(SwitchInfo, "switch step 5: change primary tdbctl if it belongs to current broken spider")
	if err := sw.HandleInvolvedPrimaryTdbctl(); err != nil {
		return err
	}

	sw.ReportLogf(SwitchInfo, "switch step 6: try to connect primary tdbctl")
	primaryTdbctlConn, connErr := sw.ConnectTdbctlNode(sw.PrimaryTdbctl.Host, sw.PrimaryTdbctl.Port)
	if connErr != nil {
		return connErr
	}
	defer sw.DisconnectTdbctlNode(primaryTdbctlConn)

	sw.ReportLogf(SwitchInfo, "switch step 7: try to query route info of this cluster from primary tdbctl")
	if err := sw.QueryRouteInfoOfCluster(primaryTdbctlConn); err != nil {
		return err
	}

	sw.ReportLogf(SwitchInfo, "switch step 8: try to delete broken-down spider and its tdbctl from cluster route table ")
	if err := sw.DeleteOwnRoutes(primaryTdbctlConn); err != nil {
		return err
	}

	sw.ReportLogf(SwitchInfo, "switch step 9: try to flush route table")
	if err := sw.TdbctlFlushRouting(primaryTdbctlConn, true); err != nil {
		return err
	}

	sw.ReportLogf(SwitchInfo, "switch steps of spider(%s:%d) all done", sw.IP, sw.Port)
	return nil
}

// DoFinal repair replication relationship if the primary tdbctl is changed
func (sw *TenDBClusterSpiderSwitchInstance) DoFinal() error {
	if sw.PrimaryTdbctlIsChanged {
		sw.ReportLog(SwitchInfo, "Try to repair replication relationship for new primary tdbctl")

		if sw.PrimaryTdbctl == nil {
			return gerrors.New(gerrors.Failure, "When repairing replication relationship, primary tdbctl is nil")
		}
		primaryHost := sw.PrimaryTdbctl.Host
		primaryPort := sw.PrimaryTdbctl.Port

		sw.ReportLog(SwitchInfo, "Try to reset slave on new primary tdbctl")
		_, _, resetSlaveErr := sw.ResetSlaveWithBinlogPos(primaryHost, primaryPort)
		if resetSlaveErr != nil {
			sw.ReportLogf(SwitchWarn, "Failed to reset slave on new primary(%s:%d): %s",
				primaryHost, primaryPort, resetSlaveErr.Error())
			return resetSlaveErr
		}

		sw.ReportLog(SwitchInfo, "Try to change master for all valid secondary tdbctl nodes")
		changeMasterSql := fmt.Sprintf(TdbctlChangeMasterSql, primaryHost, primaryPort)
		failureOccurred := false
		for _, node := range sw.SecondaryTdbctlNodes {
			if node.ServerName == sw.PrimaryTdbctl.ServerName {
				continue
			}

			if changeMasterErr := sw.ChangeMasterAuto(node.Host, node.Port, changeMasterSql); changeMasterErr != nil {
				failureOccurred = true
				sw.ReportLogf(SwitchWarn, "Failed to change master to primary(%s:%d) for secondary tdbctl(%s): %s",
					primaryHost, primaryPort, sw.ToTdbctlName(&node), changeMasterErr.Error())
			}
		}

		if failureOccurred {
			errMsg := "Not all secondary tdbctl successfully changed the master to the new primary tdbctl"
			sw.ReportLogf(SwitchWarn, "%s", errMsg)
			return gerrors.New(gerrors.Failure, errMsg)
		}
		sw.ReportLog(SwitchInfo, "Successfully changed master to the new primary tdbctl for all valid secondary tdbctl nodes")
	}

	return nil
}

// TenDBClusterRemoteSwitchInstance switch instance for remote
type TenDBClusterRemoteSwitchInstance struct {
	TenDBClusterBaseSwitchInstance
}

// CheckTenDBClusterStorageMaster check remote master
func (sw *TenDBClusterRemoteSwitchInstance) CheckTenDBClusterStorageMaster() (bool, error) {
	sw.ReportLogf(SwitchInfo, "Check TenDBCluster remote master: %s", sw.GetInstanceInfo())

	if sw.StandBySlave == nil {
		err := gerrors.Newf(gerrors.Failure, "The standby slave of remote master(%s:%d) is nil", sw.IP, sw.Port)
		sw.ReportLog(SwitchWarn, err.Error())
		return false, err
	}
	if sw.StandBySlave.Status == dbm.Unavailable {
		err := gerrors.Newf(gerrors.Failure, "The standby slave(%s:%d) of remote master(%s:%d) is unavailable",
			sw.StandBySlave.Ip, sw.StandBySlave.Port, sw.IP, sw.Port)
		sw.ReportLog(SwitchWarn, err.Error())
		return false, err
	}

	if err := sw.CheckSlaveStatus(); err != nil {
		sw.ReportLog(SwitchWarn, err.Error())
		return false, err
	}

	if len(sw.ProxyInstanceSet) == 0 {
		err := gerrors.Newf(gerrors.Failure,
			"No spider instances were found for remote master(%s:%d)", sw.IP, sw.Port)
		sw.ReportLog(SwitchWarn, err.Error())
		return false, err
	}

	return true, nil
}

// CheckBeforeSwitch check slave before switch
func (sw *TenDBClusterRemoteSwitchInstance) CheckBeforeSwitch() (checkPass bool, err error) {
	switch sw.InstanceRole {
	case dbm.TenDBClusterStorageSlave:
		checkPass = false
		sw.ReportLogf(SwitchInfo, "The instance(%s:%d) is a slave node, no need to check", sw.IP, sw.Port)
	case dbm.TenDBClusterStorageMaster:
		checkPass, err = sw.CheckTenDBClusterStorageMaster()
	default:
		checkPass = false
		err = gerrors.Newf(gerrors.Failure,
			"The role of the node to be switched is unknown, info{%s}", sw.GetInstanceInfo())
		sw.ReportLog(SwitchWarn, err.Error())
	}

	return
}

// FindMasterSlavePair find current master and standby slave from route cache
func (sw *TenDBClusterRemoteSwitchInstance) FindMasterSlavePair() (*TdbctlRouteInfo, *TdbctlRouteInfo, error) {
	curMasterRoute, curMasterExists := sw.GetRouteInfoFromCache(sw.IP, sw.Port)
	if !curMasterExists {
		errMsg := fmt.Sprintf("failed to get route info of current remote master(%s:%d) from route cache", sw.IP, sw.Port)
		sw.ReportLogf(SwitchWarn, "When looking up route info, %s", errMsg)
		return nil, nil, gerrors.New(gerrors.Failure, errMsg)
	}

	curSlaveRoute, curSlaveExists := sw.GetRouteInfoFromCache(sw.StandBySlave.Ip, sw.StandBySlave.Port)
	if !curSlaveExists {
		errMsg := fmt.Sprintf("failed to get route info of current remote slave(%s:%d) from route cache", sw.IP, sw.Port)
		sw.ReportLogf(SwitchWarn, "When looking up route info, %s", errMsg)
		return curMasterRoute, nil, gerrors.New(gerrors.Failure, errMsg)
	}

	return curMasterRoute, curSlaveRoute, nil
}

// UpdateMasterRouteToSlave update master route to slave on primary tdbctl
func (sw *TenDBClusterRemoteSwitchInstance) UpdateMasterRouteToSlave(primaryTdbctlDB *hamysql.SqlxDB,
	masterRoute *TdbctlRouteInfo, slaveRoute *TdbctlRouteInfo) error {
	alterNodeSQL := fmt.Sprintf(TdbctlAlterNodeSql, masterRoute.ServerName, slaveRoute.Host, slaveRoute.Port,
		slaveRoute.UserName, slaveRoute.Password)

	sw.ReportLogf(SwitchInfo, "try to execute sql(%s) on tdbctl(%s:%d)",
		alterNodeSQL, primaryTdbctlDB.Host(), primaryTdbctlDB.Port())

	result, execErr := primaryTdbctlDB.DB().Exec(alterNodeSQL)
	if execErr != nil {
		errMsg := fmt.Sprintf("failed to execute sql(%s) on tdbctl(%s:%d), errmsg: %s",
			alterNodeSQL, primaryTdbctlDB.Host(), primaryTdbctlDB.Port(), execErr.Error())
		sw.ReportLogf(SwitchWarn, "When updating master route to slave, %s", errMsg)
		return gerrors.Newf(gerrors.Failure, errMsg)
	}

	affected, rowErr := result.RowsAffected()
	if (rowErr != nil) || (affected != 1) {
		errMsg := fmt.Sprintf("cannot ensure that the number of rows affected is 1, affected: %d, errMsg: %s",
			affected, rowErr.Error())
		sw.ReportLogf(SwitchWarn, "When updating master route to slave, %s", errMsg)
		return gerrors.Newf(gerrors.Failure, errMsg)
	}

	sw.ReportLogf(SwitchInfo, "Successfully updated master(%s) route to slave(%s) on tdbctl(%s:%d)",
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
	sw.ReportLogf(SwitchInfo, "switch step 1: try to query all spider/tdbctl nodes of this cluster from DBM")
	if err := sw.QuerySpiderNodesOfCluster(); err != nil {
		return err
	}

	sw.ReportLogf(SwitchInfo, "switch step 2: try to query all tdbctl nodes' status from any valid tdbctl node")
	if err := sw.QueryTdbctlNodesOfCluster(); err != nil {
		return err
	}

	sw.ReportLogf(SwitchInfo, "switch step 3: try to find the primary tdbctl")
	if err := sw.FindPrimaryTdbctl(); err != nil {
		return err
	}

	sw.ReportLogf(SwitchInfo, "switch step 4: try to connect primary tdbctl")
	primaryTdbctlConn, connErr := sw.ConnectTdbctlNode(sw.PrimaryTdbctl.Host, sw.PrimaryTdbctl.Port)
	if connErr != nil {
		return connErr
	}
	defer sw.DisconnectTdbctlNode(primaryTdbctlConn)

	sw.ReportLogf(SwitchInfo, "switch step 5: try to query route info of this cluster from primary tdbctl")
	if err := sw.QueryRouteInfoOfCluster(primaryTdbctlConn); err != nil {
		return err
	}

	sw.ReportLogf(SwitchInfo, "switch step 6: try to find nodes info of current broken remote master and its slave")
	curMasterRoute, curSlaveRoute, notFoundErr := sw.FindMasterSlavePair()
	if notFoundErr != nil {
		return notFoundErr
	}

	sw.ReportLogf(SwitchInfo, "switch step 7: try to reset slave for current remote slave")
	_, _, err := sw.ResetSlaveWithBinlogPos(sw.StandBySlave.Ip, sw.StandBySlave.Port)
	if err != nil {
		err = gerrors.Newf(gerrors.Failure, "failed to reset slave status for the remote slave(%s:%d), errmsg: %s",
			sw.StandBySlave.Ip, sw.StandBySlave.Port, err.Error())
		sw.ReportLog(SwitchWarn, err.Error())
		return err
	}

	sw.ReportLogf(SwitchInfo, "switch step 8: try to update route info of current broken remote master and its slave")
	if err := sw.UpdateMasterRouteToSlave(primaryTdbctlConn, curMasterRoute, curSlaveRoute); err != nil {
		return err
	}

	sw.ReportLogf(SwitchInfo, "switch step 9: try to flush route table")
	if err := sw.TdbctlFlushRouting(primaryTdbctlConn, true); err != nil {
		return err
	}

	sw.ReportLogf(SwitchInfo, "switch steps of remote(%s:%d) all done", sw.IP, sw.Port)
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
	sw.ReportLog(SwitchInfo, fmt.Sprintf("try to swap roles of remote nodes(master:%s:%d, slave:%s:%d)",
		sw.IP, sw.Port, sw.StandBySlave.Ip, sw.StandBySlave.Port))

	err := sw.dbmClient.SwapMySQLRole(sw.BkCloudID, sw.IP, sw.Port, sw.StandBySlave.Ip, sw.StandBySlave.Port)
	if err != nil {
		errMsg := fmt.Sprintf("failed to swap roles of remote nodes(master:%s:%d, slave:%s:%d), errmsg:%s",
			sw.IP, sw.Port, sw.StandBySlave.Ip, sw.StandBySlave.Port, err.Error())
		sw.ReportLog(SwitchFail, errMsg)
		return err
	}

	sw.ReportLog(SwitchInfo, fmt.Sprintf("Succeeded to swap roles of remote nodes(master:%s:%d, slave:%s:%d)",
		sw.IP, sw.Port, sw.StandBySlave.Ip, sw.StandBySlave.Port))
	return nil
}
