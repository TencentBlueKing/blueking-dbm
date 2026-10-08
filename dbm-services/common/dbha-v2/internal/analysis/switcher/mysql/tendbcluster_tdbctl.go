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
	IP         string                        `json:"ip"`
	Port       int                           `json:"port"`
	AdminPort  int                           `json:"admin_port"`
	SpiderRole haprobe.DbmMetadataSpiderRole `json:"spider_role"`
	Status     dbm.DbmMetadataStatus         `json:"status"`
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
	ServerName  string `json:"server_name"`
	Host        string `json:"host"`
	Port        int    `json:"port"`
	ClusterRole string `json:"cluster_role"`
	Status      string `json:"status"`
	IsInvolved  bool   `json:"is_involved"`
	BinlogFile  string `json:"binlog_file"`
	BinlogPos   uint64 `json:"binlog_pos"`
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

// UnmarshalJSON decodes tdbctl REPLICATION_INFO, accepting both the legacy Master_*/Slave_*
// keys and the MySQL 8.4 Source_*/Replica_* keys; legacy keys win when both are present.
func (info *TdbctlNodeReplInfo) UnmarshalJSON(data []byte) error {
	var raw struct {
		MasterHost         string `json:"Master_Host"`
		MasterPort         int    `json:"Master_Port"`
		SlaveIORunning     string `json:"Slave_IO_Running"`
		SlaveSQLRunning    string `json:"Slave_SQL_Running"`
		RelayMasterLogFile string `json:"Relay_Master_Log_File"`
		ExecMasterLogPos   string `json:"Exec_Master_Log_Pos"`

		SourceHost         string `json:"Source_Host"`
		SourcePort         int    `json:"Source_Port"`
		ReplicaIORunning   string `json:"Replica_IO_Running"`
		ReplicaSQLRunning  string `json:"Replica_SQL_Running"`
		RelaySourceLogFile string `json:"Relay_Source_Log_File"`
		ExecSourceLogPos   string `json:"Exec_Source_Log_Pos"`
	}
	if err := json.Unmarshal(data, &raw); err != nil {
		return err
	}

	info.MasterHost = raw.MasterHost
	if info.MasterHost == "" {
		info.MasterHost = raw.SourceHost
	}
	info.MasterPort = raw.MasterPort
	if info.MasterPort == 0 {
		info.MasterPort = raw.SourcePort
	}
	info.SlaveIORunning = raw.SlaveIORunning
	if info.SlaveIORunning == "" {
		info.SlaveIORunning = raw.ReplicaIORunning
	}
	info.SlaveSQLRunning = raw.SlaveSQLRunning
	if info.SlaveSQLRunning == "" {
		info.SlaveSQLRunning = raw.ReplicaSQLRunning
	}
	info.RelayMasterLogFile = raw.RelayMasterLogFile
	if info.RelayMasterLogFile == "" {
		info.RelayMasterLogFile = raw.RelaySourceLogFile
	}
	info.ExecMasterLogPos = raw.ExecMasterLogPos
	if info.ExecMasterLogPos == "" {
		info.ExecMasterLogPos = raw.ExecSourceLogPos
	}
	return nil
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

// BrokenSpiderMasterInfo represents a broken spider master instance
type BrokenSpiderMasterInfo struct {
	BkCloudID int
	IP        string
	Port      int
	AdminPort int
}

// TdbctlOperator encapsulates tdbctl-related data and operations for TenDBCluster.
// Context fields should be set via Init before calling any method.
type TdbctlOperator struct {

	// Spider nodes info obtained from DBM during switch process
	SpiderNodes []SpiderInstanceInfo
	// Tdbctl nodes info obtained from information_schema.TDBCTL_NODES
	TdbctlNodes []TdbctlNodeInfo
	// Primary tdbctl node info
	PrimaryTdbctl *TdbctlPrimaryNodeInfo
	// Route table info obtained from mysql.servers
	TdbctlRouteTable []TdbctlRouteInfo

	// Whether primary tdbctl is changed during switch process
	PrimaryTdbctlIsChanged bool
	// Secondary tdbctl nodes that may need to change master
	SecondaryTdbctlNodes []TdbctlNodeInfo

	// Context fields set via Init
	bkCloudID           int
	cluster             string
	brokenSpiderMasters []BrokenSpiderMasterInfo
	reportLogf          switchlogger.SwitchLogFunc
}

// Init initializes the context fields for the TdbctlOperator.
// Should be called at the beginning of DoSwitch before any other method calls.
func (op *TdbctlOperator) Init(
	cluster string, bkCloudID int, brokenSpiderMasters []BrokenSpiderMasterInfo,
	reportLogf switchlogger.SwitchLogFunc,
) {
	op.bkCloudID = bkCloudID
	op.cluster = cluster
	op.brokenSpiderMasters = brokenSpiderMasters
	op.reportLogf = reportLogf
}

// SetLogFunc sets the log function for the TdbctlOperator.
func (op *TdbctlOperator) SetLogFunc(reportLogf switchlogger.SwitchLogFunc) {
	op.reportLogf = reportLogf
}

// GetLogFunc returns the log function for the TdbctlOperator.
func (op *TdbctlOperator) GetLogFunc() switchlogger.SwitchLogFunc {
	return op.reportLogf
}

// Logf logs a message using the stored reportLogf function.
func (op *TdbctlOperator) Logf(
	level switchlogger.SwitchLogLevel, format string, args ...any,
) {
	if op.reportLogf != nil {
		op.reportLogf(level, format, args...)
	}
}

// IsInvolved checks if the given host and port belong to any broken spider
func (op *TdbctlOperator) IsInvolved(host string, port int) bool {
	for _, brokenSpiderMaster := range op.brokenSpiderMasters {
		if (brokenSpiderMaster.IP == host) && (brokenSpiderMaster.AdminPort == port) {
			return true
		}
	}
	return false
}

// FindPrimaryTdbctl finds the primary tdbctl from information_schema.TDBCTL_NODES
// A tdbctl node can be considered as the primary tdbctl if it meets any of the following conditions:
//  1. The only node with CLUSTER_ROLE as "Primary" in the information_schema.TDBCTL_NODES
//  2. When there is no "Primary" node in the information_schema.TDBCTL_NODES,
//     a unique node is found that serves as the replication master for all "Secondary" nodes
func (op *TdbctlOperator) FindPrimaryTdbctl() error {
	op.PrimaryTdbctl = nil
	var masterServerName *string

	if len(op.TdbctlNodes) == 0 {
		return gerrors.New(gerrors.Failure,
			"no tdbctl node is provided to find the primary tdbctl")
	}

	for _, oneTdbctl := range op.TdbctlNodes {
		if strings.EqualFold(oneTdbctl.ClusterRole, PrimaryTdbctlRole) {
			if op.PrimaryTdbctl != nil {
				errMsg := fmt.Sprintf(
					"multiple primary tdbctl nodes(%s:%d, %s:%d) were found",
					op.PrimaryTdbctl.Host, op.PrimaryTdbctl.Port,
					oneTdbctl.Host, oneTdbctl.Port)
				op.Logf(switchlogger.SwitchWarn, "%s", errMsg)
				return gerrors.New(gerrors.Failure, errMsg)
			}

			op.PrimaryTdbctl = &TdbctlPrimaryNodeInfo{
				ServerName:  oneTdbctl.ServerName,
				Host:        oneTdbctl.Host,
				Port:        oneTdbctl.Port,
				ClusterRole: oneTdbctl.ClusterRole,
				Status:      oneTdbctl.Status,
				IsInvolved:  op.IsInvolved(oneTdbctl.Host, oneTdbctl.Port),
			}
		}

		if strings.EqualFold(oneTdbctl.ClusterRole, SecondaryTdbctlRole) {
			if (masterServerName != nil) &&
				(*masterServerName != oneTdbctl.ReplicationMaster) {
				errMsg := fmt.Sprintf(
					"multiple replication master tdbctl nodes(%s, %s) were found",
					*masterServerName, oneTdbctl.ReplicationMaster)
				op.Logf(switchlogger.SwitchWarn, "%s", errMsg)
				return gerrors.New(gerrors.Failure, errMsg)
			}

			if masterServerName == nil {
				masterServerName = &oneTdbctl.ReplicationMaster
			}
		}
	}

	if (op.PrimaryTdbctl == nil) && (masterServerName != nil) {
		op.Logf(switchlogger.SwitchInfo,
			"the primary tdbctl of cluster(%s) is missing, "+
				"but the single replication master tdbctl(%s) is found",
			op.cluster, *masterServerName)

		for _, oneTdbctl := range op.TdbctlNodes {
			if strings.EqualFold(oneTdbctl.ServerName, *masterServerName) {
				op.PrimaryTdbctl = &TdbctlPrimaryNodeInfo{
					ServerName:  oneTdbctl.ServerName,
					Host:        oneTdbctl.Host,
					Port:        oneTdbctl.Port,
					ClusterRole: oneTdbctl.ClusterRole,
					Status:      oneTdbctl.Status,
					IsInvolved:  op.IsInvolved(oneTdbctl.Host, oneTdbctl.Port),
				}
				break
			}
		}
	}

	if op.PrimaryTdbctl != nil {
		primaryTdbctlInfo := converter.ToStrIgnoreErr(*(op.PrimaryTdbctl))
		op.Logf(switchlogger.SwitchInfo,
			"successfully found the primary tdbctl node of cluster(%s): %s",
			op.cluster, primaryTdbctlInfo)
		return nil
	}

	errMsg := fmt.Sprintf(
		"no primary tdbctl node was found in cluster(%s)", op.cluster)
	op.Logf(switchlogger.SwitchWarn, "%s", errMsg)
	return gerrors.New(gerrors.Failure, errMsg)
}

// QuerySpiderNodesOfCluster query all spider nodes of current cluster from DBM
func (op *TdbctlOperator) QuerySpiderNodesOfCluster(
	dbmClient *dbm.Client,
) error {
	if dbmClient == nil {
		return gerrors.New(gerrors.Failure, "dbm client is nil when querying spider nodes")
	}

	instInfoList, err := dbmClient.QueryInstanceInfoByDomain(op.bkCloudID, op.cluster)
	if err != nil {
		op.Logf(switchlogger.SwitchWarn,
			"failed to query instance info of cluster(%s) from DBM: %s",
			op.cluster, err.Error())
		return err
	}

	op.SpiderNodes = nil
	for _, instInfo := range instInfoList {
		if instInfo.MachineType == haprobe.DbmMetadataMachineTypeSpider {
			op.SpiderNodes = append(op.SpiderNodes, SpiderInstanceInfo{
				IP:         instInfo.IP,
				Port:       instInfo.Port,
				AdminPort:  instInfo.AdminPort,
				SpiderRole: instInfo.SpiderRole,
				Status:     instInfo.Status,
			})
		}
	}

	if len(op.SpiderNodes) == 0 {
		errMsg := fmt.Sprintf(
			"found no spider instance in cluster(%s) from DBM", op.cluster)
		op.Logf(switchlogger.SwitchWarn, "%s", errMsg)
		return gerrors.New(gerrors.Failure, errMsg)
	}

	op.Logf(switchlogger.SwitchInfo,
		"successfully queried spider nodes of cluster(%s) from DBM", op.cluster)
	return nil
}

// QueryTdbctlNodesOfCluster query all tdbctl nodes of current cluster from any tdbctl node
func (op *TdbctlOperator) QueryTdbctlNodesOfCluster() error {
	for _, curSpider := range op.SpiderNodes {
		if curSpider.SpiderRole != haprobe.TenDBClusterSpiderMaster {
			op.Logf(switchlogger.SwitchWarn,
				"Not a spider master node(%s:%d), skip querying tdbctl nodes",
				curSpider.IP, curSpider.Port)
			continue
		}

		if curSpider.Status == dbm.Unavailable {
			op.Logf(switchlogger.SwitchWarn,
				"Spider master node(%s:%d) is unavailable, skip querying tdbctl nodes",
				curSpider.IP, curSpider.Port)
			continue
		}

		tdbctlDB, connErr := op.ConnectTdbctlNode(
			curSpider.IP, curSpider.AdminPort)
		if connErr != nil {
			op.Logf(switchlogger.SwitchWarn,
				"failed to connect tdbctl node(%s:%d): %s, try other nodes",
				curSpider.IP, curSpider.AdminPort, connErr.Error())
			continue
		}

		tdbctlList, queryErr := op.SelectTdbctlNodes(tdbctlDB)
		tdbctlDB.Close()

		if queryErr != nil {
			op.Logf(switchlogger.SwitchWarn,
				"failed to get tdbctl nodes info from tdbctl(%s:%d), errmsg: %s",
				curSpider.IP, curSpider.AdminPort, queryErr.Error())
			continue
		}

		op.TdbctlNodes = nil
		op.TdbctlNodes = append(op.TdbctlNodes, tdbctlList...)
		break
	}

	if len(op.TdbctlNodes) == 0 {
		return gerrors.Newf(gerrors.Failure,
			"failed to query tdbctl nodes info from all valid tdbctl nodes in cluster %s",
			op.cluster)
	}

	return nil
}

// QueryRouteInfoOfCluster query route info of current cluster from primary tdbctl node
func (op *TdbctlOperator) QueryRouteInfoOfCluster(
	primaryTdbctlDB *hamysql.GormDB,
) error {
	if primaryTdbctlDB == nil {
		return gerrors.Newf(gerrors.Failure,
			"primary tdbctl connection is nil when querying route info")
	}

	routeInfo, queryErr := op.SelectRouteInfo(primaryTdbctlDB)
	if queryErr != nil {
		op.Logf(switchlogger.SwitchWarn,
			"failed to get route info from primary tdbctl(%s:%d), errmsg: %s",
			op.PrimaryTdbctl.Host, op.PrimaryTdbctl.Port, queryErr.Error())
		return queryErr
	}
	op.TdbctlRouteTable = nil
	op.TdbctlRouteTable = append(op.TdbctlRouteTable, routeInfo...)
	return nil
}

// GetRouteInfoFromCache get route info from route table cache
func (op *TdbctlOperator) GetRouteInfoFromCache(
	host string, port int,
) (*TdbctlRouteInfo, bool) {
	for _, node := range op.TdbctlRouteTable {
		if (node.Host == host) && (node.Port == port) {
			return CopyConstructTdbctlRoute(&node), true
		}
	}
	return nil, false
}

// ConnectTdbctlNode connects to a tdbctl node using gorm
func (op *TdbctlOperator) ConnectTdbctlNode(
	tdbctlHost string, tdbctlPort int,
) (*hamysql.GormDB, error) {
	tdbctlUser := config.Cfg.Database.Mysql.User
	tdbctlPassword := config.Cfg.Database.Mysql.Password

	tdbctlDB, connErr := hamysql.NewGormDB(
		hamysql.OptionProto(DefaultMySQLProtocol),
		hamysql.OptionIP(tdbctlHost),
		hamysql.OptionPort(tdbctlPort),
		hamysql.OptionUser(tdbctlUser),
		hamysql.OptionPassword(tdbctlPassword),
		hamysql.OptionTimeout(switchcore.DbConnectTimeout()),
		hamysql.OptionSkipInitializeWithVersion(false),
		hamysql.OptionDisableDatetimePrecision(true),
		hamysql.OptionCharset(""),
	)

	if connErr != nil {
		op.Logf(switchlogger.SwitchWarn,
			"failed to connect tdbctl node(%s:%d): %s",
			tdbctlHost, tdbctlPort, connErr.Error())
		return nil, connErr
	}

	op.Logf(switchlogger.SwitchInfo,
		"successfully connected to tdbctl node(%s:%d)",
		tdbctlHost, tdbctlPort)
	return tdbctlDB, nil
}

// SelectTdbctlNodes queries tdbctl nodes info from information_schema.TDBCTL_NODES
func (op *TdbctlOperator) SelectTdbctlNodes(
	tdbctlDB *hamysql.GormDB,
) ([]TdbctlNodeInfo, error) {
	if tdbctlDB == nil {
		return nil, gerrors.New(gerrors.Failure, "tdbctl connection is nil")
	}

	var tdbctlList []TdbctlNodeInfo
	gdb, cancel := switchcore.GormWithExecSqlTimeout(tdbctlDB)
	defer cancel()

	queryErr := gdb.Raw(SelectTdbctlNodesSql).Scan(&tdbctlList).Error
	if queryErr != nil {
		return nil, gerrors.Newf(gerrors.Failure,
			"failed to execute sql(%s) on tdbctl(%s:%d), errmsg: %s",
			SelectTdbctlNodesSql, tdbctlDB.Host(), tdbctlDB.Port(),
			queryErr.Error())
	}

	if len(tdbctlList) == 0 {
		return nil, gerrors.New(gerrors.Failure, "no tdbctl node found")
	}

	nodesInfo, convertErr := converter.ToJsonStr(tdbctlList)
	if convertErr != nil {
		logger.Warn("failed to convert tdbctl nodes info to json, err: %s",
			convertErr.Error())
		nodesInfo = fmt.Sprintf("%v", tdbctlList)
	}

	op.Logf(switchlogger.SwitchInfo,
		"successfully queried all tdbctl nodes info from tdbctl node(%s:%d): %s",
		tdbctlDB.Host(), tdbctlDB.Port(), nodesInfo)

	return tdbctlList, nil
}

// SelectRouteInfo queries route info from mysql.servers
func (op *TdbctlOperator) SelectRouteInfo(
	tdbctlDB *hamysql.GormDB,
) ([]TdbctlRouteInfo, error) {
	if tdbctlDB == nil {
		return nil, gerrors.New(gerrors.Failure, "tdbctl connection is nil")
	}

	var routeInfoList []TdbctlRouteInfo
	gdb, cancel := switchcore.GormWithExecSqlTimeout(tdbctlDB)
	defer cancel()

	queryErr := gdb.Raw(SelectRouteInfoSql).Scan(&routeInfoList).Error
	if queryErr != nil {
		return nil, gerrors.Newf(gerrors.Failure,
			"failed to execute sql(%s) on tdbctl(%s:%d), errmsg: %s",
			SelectRouteInfoSql, tdbctlDB.Host(), tdbctlDB.Port(),
			queryErr.Error())
	}

	if len(routeInfoList) == 0 {
		return nil, gerrors.New(gerrors.Failure, "no server found")
	}

	routesForLog := make([]TdbctlRouteInfo, len(routeInfoList))
	for i, route := range routeInfoList {
		routesForLog[i] = route
		routesForLog[i].Password = "[secret]"
	}

	op.Logf(switchlogger.SwitchInfo,
		"successfully queried routes from tdbctl node(%s:%d): %s",
		tdbctlDB.Host(), tdbctlDB.Port(), converter.ToStrIgnoreErr(routesForLog))

	return routeInfoList, nil
}

// TdbctlDropNode drops a node from tdbctl
func (op *TdbctlOperator) TdbctlDropNode(
	tdbctlDB *hamysql.GormDB, nodeName string,
) error {
	if tdbctlDB == nil {
		return gerrors.New(gerrors.Failure, "tdbctl connection is nil")
	}

	dropNodeSql := fmt.Sprintf(TdbctlDropNodeSql, nodeName)
	gdb, cancel := switchcore.GormWithExecSqlTimeout(tdbctlDB)
	defer cancel()

	result := gdb.Exec(dropNodeSql)
	if result.Error != nil {
		return gerrors.Newf(gerrors.Failure,
			"failed to execute sql(%s) on tdbctl(%s:%d), errmsg: %s",
			dropNodeSql, tdbctlDB.Host(), tdbctlDB.Port(),
			result.Error.Error())
	}

	if result.RowsAffected != 1 {
		return gerrors.Newf(gerrors.Failure,
			"cannot ensure that the number of rows affected is 1, affected: %d",
			result.RowsAffected)
	}

	op.Logf(switchlogger.SwitchInfo,
		"successfully dropped node(%s) on tdbctl(%s:%d)",
		nodeName, tdbctlDB.Host(), tdbctlDB.Port())
	return nil
}

// TdbctlFlushRouting flushes routing on tdbctl
func (op *TdbctlOperator) TdbctlFlushRouting(
	tdbctlDB *hamysql.GormDB, force bool,
) error {
	if tdbctlDB == nil {
		return gerrors.New(gerrors.Failure, "tdbctl connection is nil")
	}

	flushRouteSql := TdbctlFlushRouteSql
	if force {
		flushRouteSql = TdbctlFlushRouteForceSql
	}

	gdb, cancel := switchcore.GormWithExecSqlTimeout(tdbctlDB)
	defer cancel()

	if result := gdb.Exec(flushRouteSql); result.Error != nil {
		errMsg := fmt.Sprintf(
			"failed to execute sql(%s) on tdbctl(%s:%d), errmsg: %s",
			flushRouteSql, tdbctlDB.Host(), tdbctlDB.Port(),
			result.Error.Error())
		op.Logf(switchlogger.SwitchWarn, errMsg)
		return gerrors.New(gerrors.Failure, errMsg)
	}

	op.Logf(switchlogger.SwitchInfo,
		"successfully flush routing on tdbctl(%s:%d)",
		tdbctlDB.Host(), tdbctlDB.Port())
	return nil
}

// execAlterNode executes the TDBCTL ALTER NODE SQL without logging
func (op *TdbctlOperator) execAlterNode(
	tdbctlDB *hamysql.GormDB,
	masterRoute *TdbctlRouteInfo, slaveRoute *TdbctlRouteInfo,
) error {
	if tdbctlDB == nil {
		return gerrors.New(gerrors.Failure, "tdbctl connection is nil")
	}

	alterNodeSQL := fmt.Sprintf(TdbctlAlterNodeSql, masterRoute.ServerName,
		slaveRoute.Host, slaveRoute.Port, slaveRoute.UserName, slaveRoute.Password)
	sqlForLog := fmt.Sprintf(TdbctlAlterNodeSql, masterRoute.ServerName,
		slaveRoute.Host, slaveRoute.Port, slaveRoute.UserName, "<secret>")

	gdb, cancel := switchcore.GormWithExecSqlTimeout(tdbctlDB)
	defer cancel()

	result := gdb.Exec(alterNodeSQL)
	if result.Error != nil {
		return gerrors.Newf(gerrors.Failure,
			"failed to execute sql(%s) on tdbctl(%s:%d), errmsg: %s",
			sqlForLog, tdbctlDB.Host(), tdbctlDB.Port(),
			result.Error.Error())
	}

	if result.RowsAffected != 1 {
		return gerrors.Newf(gerrors.Failure,
			"cannot ensure that the number of rows affected is 1, affected: %d",
			result.RowsAffected)
	}

	return nil
}

// TdbctlAlterNode alters a node's route info on tdbctl
func (op *TdbctlOperator) TdbctlAlterNode(
	tdbctlDB *hamysql.GormDB,
	masterRoute *TdbctlRouteInfo, slaveRoute *TdbctlRouteInfo,
) error {
	if err := op.execAlterNode(tdbctlDB, masterRoute, slaveRoute); err != nil {
		return err
	}

	op.Logf(switchlogger.SwitchInfo,
		"successfully altered node(%s) route to (%s:%d) on tdbctl(%s:%d)",
		masterRoute.ServerName, slaveRoute.Host, slaveRoute.Port,
		tdbctlDB.Host(), tdbctlDB.Port())
	return nil
}

// FindMasterSlavePair finds master and standby slave route info from route cache
func (op *TdbctlOperator) FindMasterSlavePair(
	masterIP string, masterPort int, slaveIP string, slavePort int,
) (*TdbctlRouteInfo, *TdbctlRouteInfo, error) {
	curMasterRoute, curMasterExists := op.GetRouteInfoFromCache(
		masterIP, masterPort)
	if !curMasterExists {
		errMsg := fmt.Sprintf(
			"failed to get route info of current remote master(%s:%d) from route cache",
			masterIP, masterPort)
		op.Logf(switchlogger.SwitchWarn,
			"when looking up route info, %s", errMsg)
		return nil, nil, gerrors.New(gerrors.Failure, errMsg)
	}

	curSlaveRoute, curSlaveExists := op.GetRouteInfoFromCache(
		slaveIP, slavePort)
	if !curSlaveExists {
		errMsg := fmt.Sprintf(
			"failed to get route info of current remote slave(%s:%d) from route cache",
			slaveIP, slavePort)
		op.Logf(switchlogger.SwitchWarn,
			"when looking up route info, %s", errMsg)
		return curMasterRoute, nil, gerrors.New(gerrors.Failure, errMsg)
	}

	op.Logf(switchlogger.SwitchInfo,
		"successfully get route info of current remote master(%s:%d) "+
			"and its remote slave(%s:%d)",
		masterIP, masterPort, slaveIP, slavePort)
	return curMasterRoute, curSlaveRoute, nil
}

// UpdateMasterRouteToSlave updates master route to slave on primary tdbctl
func (op *TdbctlOperator) UpdateMasterRouteToSlave(
	primaryTdbctlDB *hamysql.GormDB,
	masterRoute *TdbctlRouteInfo, slaveRoute *TdbctlRouteInfo,
) error {
	if err := op.execAlterNode(
		primaryTdbctlDB, masterRoute, slaveRoute,
	); err != nil {
		op.Logf(switchlogger.SwitchWarn,
			"when updating master route to slave, %s", err.Error())
		return err
	}

	op.Logf(switchlogger.SwitchInfo,
		"successfully updated master(%s) route to slave(%s) on tdbctl(%s:%d)",
		masterRoute.ServerName, slaveRoute.ServerName,
		primaryTdbctlDB.Host(), primaryTdbctlDB.Port())
	return nil
}

// ToTdbctlName convert tdbctl node to formatted name
func (op *TdbctlOperator) ToTdbctlName(node *TdbctlNodeInfo) string {
	return fmt.Sprintf("%s(%s:%d)", node.ServerName, node.Host, node.Port)
}

// ToNodeName convert node route info to formatted name
func (op *TdbctlOperator) ToNodeName(node *TdbctlRouteInfo) string {
	return fmt.Sprintf("%s(%s:%d)", node.ServerName, node.Host, node.Port)
}

// UnmarshalTdbctlReplInfo unmarshal tdbctl replication info
func (op *TdbctlOperator) UnmarshalTdbctlReplInfo(
	replicationInfo string,
) (*TdbctlNodeReplInfo, error) {
	replInfo := &TdbctlNodeReplInfo{}
	if err := json.Unmarshal([]byte(replicationInfo), replInfo); err != nil {
		return nil, err
	}

	logFileparts := strings.Split(replInfo.RelayMasterLogFile, ".")
	if len(logFileparts) < 2 {
		return replInfo, gerrors.Newf(gerrors.Failure,
			"invalid relay master log file: %s", replInfo.RelayMasterLogFile)
	}

	logFileIndex, convErr := strconv.Atoi(logFileparts[1])
	if convErr != nil {
		return replInfo, gerrors.Newf(gerrors.Failure,
			"invalid index part of relay master log file: %s",
			replInfo.RelayMasterLogFile)
	}
	replInfo.RelayMasterLogFileIndex = logFileIndex

	execPos, parseErr := strconv.ParseUint(replInfo.ExecMasterLogPos, 10, 64)
	if parseErr != nil {
		return replInfo, gerrors.Newf(gerrors.Failure,
			"invalid exec master log pos: %s", replInfo.ExecMasterLogPos)
	}
	replInfo.ExecMasterLogPosInt = execPos

	return replInfo, nil
}

// TdbctlEnablePrimary connect tdbctl and execute TDBCTL ENABLE PRIMARY [FORCE]
func (op *TdbctlOperator) TdbctlEnablePrimary(
	tdbctlHost string, tdbctlPort int, force bool,
) error {
	tdbctlDB, connErr := op.ConnectTdbctlNode(tdbctlHost, tdbctlPort)
	if connErr != nil {
		return connErr
	}
	defer tdbctlDB.Close()

	enablePimarySql := TdbctlEnablePrimarySql
	if force {
		enablePimarySql = TdbctlEnablePrimaryForceSql
	}

	gdb, cancel := switchcore.GormWithExecSqlTimeout(tdbctlDB)
	defer cancel()

	if result := gdb.Exec(enablePimarySql); result.Error != nil {
		op.Logf(switchlogger.SwitchWarn,
			"when enabling primary, failed to execute sql(%s) on tdbctl(%s:%d), errmsg: %s",
			enablePimarySql, tdbctlHost, tdbctlPort, result.Error.Error())
		return result.Error
	}

	op.Logf(switchlogger.SwitchInfo,
		"successfully enable primary on tdbctl(%s:%d)",
		tdbctlHost, tdbctlPort)
	return nil
}

// ElectNewPrimaryTdbctl elect new primary tdbctl
func (op *TdbctlOperator) ElectNewPrimaryTdbctl() (*TdbctlNodeInfo, error) {
	var electNode *TdbctlNodeInfo
	var tdbctlReplMaster *string
	maxLogFileIndex, maxExecLogPos := -1, uint64(0)

	op.Logf(switchlogger.SwitchInfo, "try to elect the new primary tdbctl of cluster(%s)", op.cluster)
	if len(op.TdbctlNodes) == 0 {
		return nil, gerrors.New(gerrors.Failure, "no tdbctl node is provided to elect the new primary tdbctl")
	}

	op.SecondaryTdbctlNodes = nil
	for nodeIndex, node := range op.TdbctlNodes {
		if (op.PrimaryTdbctl != nil) && (node.ServerName == op.PrimaryTdbctl.ServerName) {
			op.Logf(switchlogger.SwitchInfo,
				"when selecting new primary, skip current primary(%s)", op.ToTdbctlName(&node))
			continue
		}

		if strings.EqualFold(node.ClusterRole, PrimaryTdbctlRole) {
			return nil, gerrors.Newf(gerrors.Failure,
				"unexpectedly found another primary(%s)", op.ToTdbctlName(&node))
		}

		if !strings.EqualFold(node.ClusterRole, SecondaryTdbctlRole) {
			op.Logf(switchlogger.SwitchInfo,
				"when selecting new primary, skip tdbctl(%s) as it is not secondary", op.ToTdbctlName(&node))
			continue
		}

		if op.IsInvolved(node.Host, node.Port) {
			op.Logf(switchlogger.SwitchInfo,
				"when selecting new primary, skip tdbctl(%s) as it belongs to a broken spider", op.ToTdbctlName(&node))
			continue
		}

		// record secondary tdbctl nodes that are not involved in any broken spider
		op.SecondaryTdbctlNodes = append(op.SecondaryTdbctlNodes, node)

		if (tdbctlReplMaster != nil) && (node.ReplicationMaster != *tdbctlReplMaster) {
			errMsg := fmt.Sprintf("found multiple replication masters(%s, %s)", node.ReplicationMaster, *tdbctlReplMaster)
			return nil, gerrors.New(gerrors.Failure, errMsg)
		}

		if tdbctlReplMaster == nil {
			tdbctlReplMaster = &node.ReplicationMaster
		}

		replInfo, err := op.UnmarshalTdbctlReplInfo(node.ReplicationInfo)
		if err != nil {
			op.Logf(switchlogger.SwitchWarn, "when selecting new primary, "+
				"failed to parse replication info of secondary(%s): %s", op.ToTdbctlName(&node), err.Error())
			continue
		}
		op.Logf(switchlogger.SwitchInfo, "parsed replication info of tdbctl(%s): %s",
			op.ToTdbctlName(&node), converter.ToStrIgnoreErr(replInfo))

		if !strings.EqualFold(replInfo.SlaveSQLRunning, "Yes") {
			op.Logf(switchlogger.SwitchWarn, "when selecting new primary, "+
				"found Slave_SQL_Running of secondary(%s) is not Yes", op.ToTdbctlName(&node))
			continue
		}

		if (replInfo.RelayMasterLogFileIndex > maxLogFileIndex) ||
			((replInfo.RelayMasterLogFileIndex == maxLogFileIndex) && (replInfo.ExecMasterLogPosInt > maxExecLogPos)) {
			maxLogFileIndex, maxExecLogPos = replInfo.RelayMasterLogFileIndex, replInfo.ExecMasterLogPosInt
			electNode = &op.TdbctlNodes[nodeIndex]
			op.Logf(switchlogger.SwitchInfo, "when selecting new primary, "+
				"found replication delay of secondary(%s) is smaller", op.ToTdbctlName(&node))
		}
	}

	if electNode != nil {
		op.Logf(switchlogger.SwitchInfo,
			"successfully elected the new primary tdbctl in cluster(%s): %s", op.cluster, op.ToTdbctlName(electNode))
		return CopyConstructTdbctlNode(electNode), nil
	}

	return nil, gerrors.Newf(gerrors.Failure,
		"found no suitable secondary tdbctl that can be used as the new primary")
}

// HandleInvolvedPrimaryTdbctl changes the primary tdbctl if it belongs to any broken spider
func (op *TdbctlOperator) HandleInvolvedPrimaryTdbctl() error {
	if op.PrimaryTdbctl == nil {
		op.Logf(switchlogger.SwitchWarn,
			"when handling involved primary tdbctl, the primary tdbctl is nil")
		return gerrors.Newf(gerrors.Failure, "the primary tdbctl is nil")
	}

	if !op.PrimaryTdbctl.IsInvolved {
		op.Logf(switchlogger.SwitchInfo,
			"the primary tdbctl(%s:%d) does not belong to any broken spider, skip electing new primary tdbctl",
			op.PrimaryTdbctl.Host, op.PrimaryTdbctl.Port)
		return nil
	}

	op.Logf(switchlogger.SwitchInfo,
		"the primary tdbctl(%s:%d) belongs to a broken spider, try to elect new primary tdbctl",
		op.PrimaryTdbctl.Host, op.PrimaryTdbctl.Port)

	newPrimaryTdbctl, err := op.ElectNewPrimaryTdbctl()
	if err != nil {
		op.Logf(switchlogger.SwitchWarn,
			"failed to elect new primary tdbctl of cluster(%s): %s",
			op.cluster, err.Error())
		return err
	}

	binlogFile, binlogPos, resetErr := DoResetSlaveWithBinlogPos(
		newPrimaryTdbctl.Host, newPrimaryTdbctl.Port, op.reportLogf)
	if resetErr != nil {
		op.Logf(switchlogger.SwitchWarn, "failed to reset slave on new primary(%s:%d): %s",
			newPrimaryTdbctl.Host, newPrimaryTdbctl.Port, resetErr.Error())
		return resetErr
	}

	if err = op.TdbctlEnablePrimary(
		newPrimaryTdbctl.Host, newPrimaryTdbctl.Port, true,
	); err != nil {
		op.Logf(switchlogger.SwitchWarn,
			"failed to enable new primary tdbctl(%s:%d) of cluster(%s): %s",
			newPrimaryTdbctl.Host, newPrimaryTdbctl.Port,
			op.cluster, err.Error())
		return err
	}
	op.PrimaryTdbctlIsChanged = true

	op.PrimaryTdbctl = &TdbctlPrimaryNodeInfo{
		ServerName:  newPrimaryTdbctl.ServerName,
		Host:        newPrimaryTdbctl.Host,
		Port:        newPrimaryTdbctl.Port,
		ClusterRole: newPrimaryTdbctl.ClusterRole,
		Status:      newPrimaryTdbctl.Status,
		IsInvolved:  op.IsInvolved(newPrimaryTdbctl.Host, newPrimaryTdbctl.Port),
		BinlogFile:  binlogFile,
		BinlogPos:   binlogPos,
	}

	if op.PrimaryTdbctl.IsInvolved {
		errMsg := fmt.Sprintf(
			"the elected new primary tdbctl(%s:%d) still belongs to a broken spider",
			newPrimaryTdbctl.Host, newPrimaryTdbctl.Port)
		op.Logf(switchlogger.SwitchWarn, "%s", errMsg)
		return gerrors.New(gerrors.Failure, errMsg)
	}

	op.Logf(switchlogger.SwitchInfo,
		"successfully changed primary tdbctl to (%s:%d) in cluster(%s)",
		newPrimaryTdbctl.Host, newPrimaryTdbctl.Port, op.cluster)
	return nil
}

// DropBrokenSpiderRoutes remove route items of the broken spider and its tdbctl
// from the cluster route table
func (op *TdbctlOperator) DropBrokenSpiderRoutes(
	primaryTdbctlDB *hamysql.GormDB,
	spiderIP string, spiderPort int, spiderAdminPort int,
	spiderRole haprobe.DbmMetadataSpiderRole,
) error {
	curSpiderRoute, curSpiderExists := op.GetRouteInfoFromCache(
		spiderIP, spiderPort)
	if !curSpiderExists {
		errMsg := fmt.Sprintf(
			"failed to get route info of current spider(%s:%d) from route cache",
			spiderIP, spiderPort)
		op.Logf(switchlogger.SwitchWarn,
			"when dropping broken spider routes, %s", errMsg)
		return gerrors.New(gerrors.Failure, errMsg)
	}

	if primaryTdbctlDB == nil {
		errMsg := "primary tdbctl connection is nil when dropping broken spider routes"
		op.Logf(switchlogger.SwitchWarn, "%s", errMsg)
		return gerrors.Newf(gerrors.Failure, "%s", errMsg)
	}

	if err := op.TdbctlDropNode(
		primaryTdbctlDB, curSpiderRoute.ServerName,
	); err != nil {
		op.Logf(switchlogger.SwitchWarn,
			"failed to delete route item of %s on primary(%s:%d): %s",
			op.ToNodeName(curSpiderRoute),
			op.PrimaryTdbctl.Host, op.PrimaryTdbctl.Port, err.Error())
		return err
	}

	if spiderRole == haprobe.TenDBClusterSpiderSlave {
		op.Logf(switchlogger.SwitchInfo,
			"spider_slave(%s:%d) does not have corresponding tdbctl, "+
				"skip deleting tdbctl route",
			spiderIP, spiderPort)
		op.Logf(switchlogger.SwitchInfo,
			"successfully deleted route item of %s on primary(%s:%d)",
			op.ToNodeName(curSpiderRoute),
			op.PrimaryTdbctl.Host, op.PrimaryTdbctl.Port)
		return nil
	}

	curTdbctlRoute, curTdbctlExists := op.GetRouteInfoFromCache(
		spiderIP, spiderAdminPort)
	if !curTdbctlExists {
		errMsg := fmt.Sprintf(
			"failed to get route info of current tdbctl(%s:%d) from route cache",
			spiderIP, spiderAdminPort)
		op.Logf(switchlogger.SwitchWarn,
			"when dropping broken spider routes, %s", errMsg)
		return gerrors.New(gerrors.Failure, errMsg)
	}

	if err := op.TdbctlDropNode(
		primaryTdbctlDB, curTdbctlRoute.ServerName,
	); err != nil {
		op.Logf(switchlogger.SwitchWarn,
			"failed to delete route item of %s on primary(%s:%d): %s",
			op.ToNodeName(curTdbctlRoute),
			op.PrimaryTdbctl.Host, op.PrimaryTdbctl.Port, err.Error())
		return err
	}

	op.Logf(switchlogger.SwitchInfo,
		"successfully deleted two route items of %s and %s on primary(%s:%d)",
		op.ToNodeName(curSpiderRoute), op.ToNodeName(curTdbctlRoute),
		op.PrimaryTdbctl.Host, op.PrimaryTdbctl.Port)
	return nil
}

// RepairTdbctlReplication repairs tdbctl replication relationship after primary change.
// It resets slave on the new primary, then changes master on all secondary tdbctl nodes.
func (op *TdbctlOperator) RepairTdbctlReplication() error {
	if !op.PrimaryTdbctlIsChanged {
		return nil
	}

	if op.PrimaryTdbctl == nil {
		return gerrors.New(gerrors.Failure,
			"when repairing replication relationship, primary tdbctl is nil")
	}
	primaryHost := op.PrimaryTdbctl.Host
	primaryPort := op.PrimaryTdbctl.Port
	primaryBinlogFile := op.PrimaryTdbctl.BinlogFile
	primaryBinlogPos := op.PrimaryTdbctl.BinlogPos

	op.Logf(switchlogger.SwitchInfo,
		"try to repair replication relationship for tdbctl nodes, primary: %s:%d, binlog file: %s, binlog position: %d",
		primaryHost, primaryPort, primaryBinlogFile, primaryBinlogPos)

	src := hamysql.ReplSource{
		Host:         primaryHost,
		Port:         primaryPort,
		LogFile:      primaryBinlogFile,
		LogPos:       primaryBinlogPos,
		AutoPosition: hamysql.AutoPositionOff,
	}
	var succeededNodes, failedNodes []string

	for _, node := range op.SecondaryTdbctlNodes {
		if node.ServerName == op.PrimaryTdbctl.ServerName {
			continue
		}

		nodeName := op.ToTdbctlName(&node)
		if err := DoChangeMasterSteps(
			node.Host, node.Port, src, op.reportLogf,
		); err != nil {
			failedNodes = append(failedNodes, nodeName)
			op.Logf(switchlogger.SwitchWarn,
				"failed to change master to primary(%s:%d) for secondary tdbctl(%s): %s",
				primaryHost, primaryPort, nodeName, err.Error())
			continue
		}

		succeededNodes = append(succeededNodes, nodeName)
	}

	if (len(succeededNodes) == 0) && (len(failedNodes) == 0) {
		op.Logf(switchlogger.SwitchInfo,
			"no valid secondary nodes need to change master to the new primary tdbctl")
		return nil
	}

	if len(failedNodes) > 0 {
		op.Logf(switchlogger.SwitchWarn,
			"failed to change master for secondary tdbctl nodes: [%s], "+
				"succeeded nodes: [%s]",
			strings.Join(failedNodes, ", "), strings.Join(succeededNodes, ", "))
		return gerrors.Newf(gerrors.Failure,
			"failed to change master for %d secondary tdbctl nodes: [%s]",
			len(failedNodes), strings.Join(failedNodes, ", "))
	}

	op.Logf(switchlogger.SwitchInfo,
		"successfully changed master to the new primary tdbctl for all secondary nodes: [%s]",
		strings.Join(succeededNodes, ", "))
	return nil
}
