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
	"fmt"
	"strconv"
	"strings"
	"time"

	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"
)

// TODO: remove those variables and get them dynamically
const (
	DefaultIgnoreCheckSum     bool = false
	DefaultIgnoreSlaveDelay   bool = false
	AllowedMaxChecksumFailCnt int  = 10
	AllowedMaxSlaveDelay      int  = 1000
	AllowedMaxTimeDelay       int  = 1000

	MySQLProtocol       string = "tcp"
	MySQLUser           string = "mysql"
	MySQLPassword       string = "xxx"
	MySQLProxyUser      string = "proxy"
	MySQLProxyPassword  string = "xxx"
	MySQLDefaultDB      string = "infodba_schema"
	MySQLProxyDefaultDB string = "mysql"
	AllowSlowBytes      int    = 1024
)

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
	// CheckDelaySQL master and slave's time delay
	CheckDelaySQL = `
		SELECT unix_timestamp(now())-unix_timestamp(master_time) as time_delay, delay_sec as slave_delay 
		FROM infodba_schema.master_slave_heartbeat 
		WHERE master_server_id = ? and slave_server_id != master_server_id
	`
)

// MySQLVariableResult represents MySQL variable result
type MySQLVariableResult struct {
	VariableName string `gorm:"column:Variable_name"`
	Value        string `gorm:"column:Value"`
}

// SlaveStatusInfo represents MySQL slave status information
type SlaveStatusInfo struct {
	SlaveIOState               string `gorm:"column:Slave_IO_State"                json:"Slave_IO_State"`
	MasterHost                 string `gorm:"column:Master_Host"                   json:"Master_Host"`
	MasterUser                 string `gorm:"column:Master_User"                   json:"Master_User"`
	MasterPort                 int    `gorm:"column:Master_Port"                   json:"Master_Port"`
	ConnectRetry               int    `gorm:"column:Connect_Retry"                 json:"Connect_Retry"`
	MasterLogFile              string `gorm:"column:Master_Log_File"               json:"Master_Log_File"`
	ReadMasterLogPos           uint64 `gorm:"column:Read_Master_Log_Pos"           json:"Read_Master_Log_Pos"`
	RelayLogFile               string `gorm:"column:Relay_Log_File"                json:"Relay_Log_File"`
	RelayLogPos                uint64 `gorm:"column:Relay_Log_Pos"                 json:"Relay_Log_Pos"`
	RelayMasterLogFile         string `gorm:"column:Relay_Master_Log_File"         json:"Relay_Master_Log_File"`
	SlaveIORunning             string `gorm:"column:Slave_IO_Running"              json:"Slave_IO_Running"`
	SlaveSQLRunning            string `gorm:"column:Slave_SQL_Running"             json:"Slave_SQL_Running"`
	ReplicateDoDB              string `gorm:"column:Replicate_Do_DB"               json:"Replicate_Do_DB"`
	ReplicateIgnoreDB          string `gorm:"column:Replicate_Ignore_DB"           json:"Replicate_Ignore_DB"`
	ReplicateDoTable           string `gorm:"column:Replicate_Do_Table"            json:"Replicate_Do_Table"`
	ReplicateIgnoreTable       string `gorm:"column:Replicate_Ignore_Table"        json:"Replicate_Ignore_Table"`
	ReplicateWildDoTable       string `gorm:"column:Replicate_Wild_Do_Table"       json:"Replicate_Wild_Do_Table"`
	ReplicateWildIgnoreTable   string `gorm:"column:Replicate_Wild_Ignore_Table"   json:"Replicate_Wild_Ignore_Table"`
	LastErrno                  int    `gorm:"column:Last_Errno"                    json:"Last_Errno"`
	LastError                  string `gorm:"column:Last_Error"                    json:"Last_Error"`
	SkipCounter                int    `gorm:"column:Skip_Counter"                  json:"Skip_Counter"`
	ExecMasterLogPos           uint64 `gorm:"column:Exec_Master_Log_Pos"           json:"Exec_Master_Log_Pos"`
	RelayLogSpace              uint64 `gorm:"column:Relay_Log_Space"               json:"Relay_Log_Space"`
	UntilCondition             string `gorm:"column:Until_Condition"               json:"Until_Condition"`
	UntilLogFile               string `gorm:"column:Until_Log_File"                json:"Until_Log_File"`
	UntilLogPos                uint64 `gorm:"column:Until_Log_Pos"                 json:"Until_Log_Pos"`
	MasterSSLAllowed           string `gorm:"column:Master_SSL_Allowed"            json:"Master_SSL_Allowed"`
	MasterSSLCAFile            string `gorm:"column:Master_SSL_CA_File"            json:"Master_SSL_CA_File"`
	MasterSSLCAPath            string `gorm:"column:Master_SSL_CA_Path"            json:"Master_SSL_CA_Path"`
	MasterSSLCert              string `gorm:"column:Master_SSL_Cert"               json:"Master_SSL_Cert"`
	MasterSSLCipher            string `gorm:"column:Master_SSL_Cipher"             json:"Master_SSL_Cipher"`
	MasterSSLKey               string `gorm:"column:Master_SSL_Key"                json:"Master_SSL_Key"`
	SecondsBehindMaster        int    `gorm:"column:Seconds_Behind_Master"         json:"Seconds_Behind_Master"`
	MasterSSLVerifyServerCert  string `gorm:"column:Master_SSL_Verify_Server_Cert" json:"Master_SSL_Verify_Server_Cert"`
	LastIOErrno                int    `gorm:"column:Last_IO_Errno"                 json:"Last_IO_Errno"`
	LastIOError                string `gorm:"column:Last_IO_Error"                 json:"Last_IO_Error"`
	LastSQLErrno               int    `gorm:"column:Last_SQL_Errno"                json:"Last_SQL_Errno"`
	LastSQLError               string `gorm:"column:Last_SQL_Error"                json:"Last_SQL_Error"`
	ReplicateIgnoreServerIDs   string `gorm:"column:Replicate_Ignore_Server_Ids"   json:"Replicate_Ignore_Server_Ids"`
	MasterServerID             uint64 `gorm:"column:Master_Server_Id"              json:"Master_Server_Id"`
	MasterUUID                 string `gorm:"column:Master_UUID"                   json:"Master_UUID"`
	MasterInfoFile             string `gorm:"column:Master_Info_File"              json:"Master_Info_File"`
	SqlDelay                   uint64 `gorm:"column:SQL_Delay"                     json:"SQL_Delay"`
	SqlRemainingDelay          string `gorm:"column:SQL_Remaining_Delay"           json:"SQL_Remaining_Delay"`
	SlaveSqlRunningState       string `gorm:"column:Slave_SQL_Running_State"       json:"Slave_SQL_Running_State"`
	MasterRetryCount           int    `gorm:"column:Master_Retry_Count"            json:"Master_Retry_Count"`
	MasterBind                 string `gorm:"column:Master_Bind"                   json:"Master_Bind"`
	LastIoErrorTimestamp       string `gorm:"column:Last_IO_Error_Timestamp"       json:"Last_IO_Error_Timestamp"`
	LastSqlErrorTimestamp      string `gorm:"column:Last_SQL_Error_Timestamp"      json:"Last_SQL_Error_Timestamp"`
	MasterSSLCrl               string `gorm:"column:Master_SSL_Crl"                json:"Master_SSL_Crl"`
	MasterSSLCrlpath           string `gorm:"column:Master_SSL_Crlpath"            json:"Master_SSL_Crlpath"`
	RetrievedGtidSet           string `gorm:"column:Retrieved_Gtid_Set"            json:"Retrieved_Gtid_Set"`
	ExecutedGtidSet            string `gorm:"column:Executed_Gtid_Set"             json:"Executed_Gtid_Set"`
	AutoPosition               string `gorm:"column:Auto_Position"                 json:"Auto_Position"`
	ReplicateWildParallelTable string `gorm:"column:Replicate_Wild_Parallel_Table" json:"Replicate_Wild_Parallel_Table"`
}

// SlaveStatusPartialInfo contains partial slave status information for switching
type SlaveStatusPartialInfo struct {
	MasterHost              string
	MasterPort              int
	MasterLogFileIndex      int
	RelayMasterLogFileIndex int
	ReadMasterLogPos        uint64
	ExecMasterLogPos        uint64
}

// SlaveTimeDelayInfo contains slave replication delay information
type SlaveTimeDelayInfo struct {
	SlaveIODelay        float64 `gorm:"column:slave_delay"`
	SlaveHeartbeatDelay float64 `gorm:"column:time_delay"`
}

// MasterStatusInfo represents MySQL master status information
type MasterStatusInfo struct {
	File            string
	Position        uint64
	BinlogDoDB      string
	BinlogIgnoreDB  string
	ExecutedGtidSet string
}

// ProxyBackendInfo contains proxy backend connection information
type ProxyBackendInfo struct {
	BackendNdx       int    `gorm:"column:backend_ndx"`
	Address          string `gorm:"column:address"`
	State            string `gorm:"column:state"`
	Type             string `gorm:"column:type"`
	UUID             string `gorm:"column:uuid"`
	ConnectedClients int    `gorm:"column:connected_clients"`
	RefreshTime      int    `gorm:"column:refresh_time"`
}

// MySQLInstanceMetadata contains MySQL instance metadata from DBM
type MySQLInstanceMetadata struct {
	Ip               string                             `json:"ip"`
	Port             int                                `json:"port"`
	Status           hamodel.DbmMetadataStatus          `json:"status"`
	BkCloudID        int                                `json:"bk_cloud_id"`
	BkIdcCityID      int                                `json:"bk_idc_city_id"`
	BkBizID          int                                `json:"bk_biz_id"`
	Cluster          string                             `json:"cluster"`
	ClusterID        int                                `json:"cluster_id"`
	ClusterType      hamodel.DbmMetadataClusterType     `json:"cluster_type"`
	MachineType      hamodel.DbmMetadataMachineType     `json:"machine_type"`
	InstanceRole     hamodel.DbmMetadataInstanceRole    `json:"instance_role"`
	Receiver         []hamodel.DbmMetadataSlaveInfo     `json:"receiver"`
	AdminPort        int                                `json:"admin_port"`
	BindEntry        hamodel.DbmMetadataBindEntry       `json:"bind_entry"`
	ProxyInstanceSet []hamodel.DbmMetadataProxyInstance `json:"proxyinstance_set"`
	BinlogDumperSet  []hamodel.DbmMetadataBinlogDumper  `json:"tbinlogdumpers"`
}

// NewMySQLSwitchInstance creates a new MySQL switch instance based on metadata
func NewMySQLSwitchInstance(metadata *MySQLInstanceMetadata) (SwitchableInstance, error) {
	mysqlBaseInstance := MySQLBaseSwitchInstance{
		BaseSwitchInstance: BaseSwitchInstance{
			Ip:           metadata.Ip,
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
		},
		AdminPort:        metadata.AdminPort,
		BindEntry:        metadata.BindEntry,
		ProxyInstanceSet: metadata.ProxyInstanceSet,
		BinlogDumperSet:  metadata.BinlogDumperSet,
	}
	mysqlBaseInstance.SetStandbySlave(metadata.Receiver)

	switch metadata.MachineType {
	case hamodel.DbmMetadataMachineTypeBackend:
		res := &MySQLStorageSwitchInstance{
			MySQLBaseSwitchInstance: mysqlBaseInstance,
		}
		return res, nil
	case hamodel.DbmMetadataMachineTypeProxy:
		res := &MySQLProxySwitchInstance{
			MySQLBaseSwitchInstance: mysqlBaseInstance,
		}
		return res, nil
	default:
		logger.Error("Unknown machine type(%s) for MySQL switch instance constructor ", metadata.MachineType)
		return nil, gerrors.New(gerrors.InvalidParameter, "Invalid machine type")
	}
}

// MySQLBaseSwitchInstance provides base functionality for MySQL switch operations
type MySQLBaseSwitchInstance struct {
	BaseSwitchInstance

	// The following are instance metadata information from DBM

	StandBySlave     *hamodel.DbmMetadataSlaveInfo
	AdminPort        int
	BindEntry        hamodel.DbmMetadataBindEntry
	ProxyInstanceSet []hamodel.DbmMetadataProxyInstance
	BinlogDumperSet  []hamodel.DbmMetadataBinlogDumper
}

// GetBinlogDumperInfo returns binlog dumper information as string
func (sw *MySQLBaseSwitchInstance) GetBinlogDumperInfo() string {
	dumperInfo := "nil"
	if len(sw.BinlogDumperSet) > 0 {
		var dumperInfos []string
		for _, dumper := range sw.BinlogDumperSet {
			dumperInfos = append(dumperInfos, fmt.Sprintf("%s:%d", dumper.Ip, dumper.Port))
		}
		dumperInfo = fmt.Sprintf("(%s)", strings.Join(dumperInfos, ","))
	}
	return dumperInfo
}

// SetStandbySlave sets the standby slave for master instance
// Only master instances can call this method.
// If no standby slave is found, it uses the first slave in the list.
func (sw *MySQLBaseSwitchInstance) SetStandbySlave(slaves []hamodel.DbmMetadataSlaveInfo) {
	if len(slaves) == 0 {
		logger.Debug("No standby slave found")
		sw.StandBySlave = nil
	}

	findIndex := 0
	for i, slave := range slaves {
		if slave.IsStandBy {
			findIndex = i
			break
		}
	}
	sw.StandBySlave = &hamodel.DbmMetadataSlaveInfo{}
	*(sw.StandBySlave) = slaves[findIndex]
	logger.Debug("Success to set standby slave: %#v", sw.StandBySlave)
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

// GetSlaveStatusPartialInfo retrieves partial slave status information
func (sw *MySQLBaseSwitchInstance) GetSlaveStatusPartialInfo(slaveDB *hamysql.DB) (*SlaveStatusPartialInfo, error) {
	if slaveDB == nil {
		return nil, gerrors.New(gerrors.InvalidParameter, "GetSlaveStatusPartialInfo got nil slaveDB")
	}

	ip := slaveDB.Host()
	port := slaveDB.Port()
	slaveStatus, err := sw.ShowSlaveStatus(slaveDB)
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
	return ret, nil
}

// CheckSqlReplicationDelay checks if slave replication is delayed
func (sw *MySQLBaseSwitchInstance) CheckSqlReplicationDelay(slaveDB *hamysql.DB, ignoreDelay bool) error {
	if slaveDB == nil {
		return gerrors.New(gerrors.InvalidParameter, "CheckReplicationDelay got nil slaveDB")
	}

	ip := slaveDB.Host()
	port := slaveDB.Port()
	allowSlowKBytes := AllowSlowBytes

	var varQueryRes MySQLVariableResult
	err := slaveDB.DB().Raw("show variables like 'max_binlog_size'").Scan(&varQueryRes).Error
	if err != nil {
		logger.Error("failed to query max_binlog_size from (%s:%d). errmsg: %s", ip, port, err.Error())
		return err
	}

	maxBinlogSize, parseErr := strconv.ParseUint(varQueryRes.Value, 10, 64)
	if parseErr != nil {
		logger.Error("failed to parse max_binlog_size('%s') to uint. errmsg: %s", varQueryRes.Value, parseErr.Error())
		return parseErr
	}
	logger.Info("the slave node's max_binlog_size is %dMB!", maxBinlogSize/1024/1024)

	slaveStatus, err := sw.GetSlaveStatusPartialInfo(slaveDB)
	if err != nil {
		logger.Error("failed to query slave status. errmsg:%s", err.Error())
		return err
	}
	logger.Info("Relay_Master_Log_File_Index:%d, Exec_Master_Log_Pos:%d",
		slaveStatus.RelayMasterLogFileIndex, slaveStatus.ReadMasterLogPos)

	if slaveStatus.MasterHost != sw.Ip || slaveStatus.MasterPort != sw.Port {
		errMsg := fmt.Sprintf("the slave's master info(%s:%d) and the broken-down instance(%s:%d) are not equal",
			slaveStatus.MasterHost, slaveStatus.MasterPort, sw.Ip, sw.Port)
		return gerrors.New(gerrors.NodeAbnormal, errMsg)
	}

	if ignoreDelay {
		logger.Info("'ignoreSlaveDelay' is configured, skip check replication delay")
		return nil
	}

	realSlowKBytes := uint64(slaveStatus.MasterLogFileIndex-slaveStatus.RelayMasterLogFileIndex)*(maxBinlogSize/1024) -
		(slaveStatus.ExecMasterLogPos / 1024) + (slaveStatus.ReadMasterLogPos / 1024)

	if realSlowKBytes <= uint64(allowSlowKBytes) {
		sw.ReportLog(SwitchInfo, fmt.Sprintf("Status check of slave node (%s:%d) passed", ip, port))
		return nil
	}

	loop := 10
	sw.ReportLog(SwitchInfo, fmt.Sprintf("the slave(%s:%d) was delayed for %dKB, which is larger than allowed(%dKB)"+
		"Try to wait in a loop", ip, port, realSlowKBytes, allowSlowKBytes))
	var i int
	for i = 0; i < loop; i++ {
		time.Sleep(3 * time.Second)
		tmpSlaveStatus, err := sw.GetSlaveStatusPartialInfo(slaveDB)
		if err != nil {
			logger.Error("failed to query slave status. errmsg:%s", err.Error())
			return err
		}
		realSlowKBytes = uint64(tmpSlaveStatus.MasterLogFileIndex-tmpSlaveStatus.RelayMasterLogFileIndex)*
			(maxBinlogSize/1024) - (tmpSlaveStatus.ExecMasterLogPos / 1024) + (tmpSlaveStatus.ReadMasterLogPos / 1024)
		if realSlowKBytes <= uint64(allowSlowKBytes) {
			// TODO: for GTID
			break
		}
		logger.Warn("Loop (%d): the slave(%s:%d) was delayed for %dKB, which is larger than allowed(%dKB)",
			i, ip, port, realSlowKBytes, allowSlowKBytes)
	}
	if i == loop {
		errMsg := fmt.Sprintf("after waiting for %d loops, the slave(%s:%d) was still delayed too much",
			loop, ip, port)
		return gerrors.New(gerrors.NodeAbnormal, errMsg)
	}

	sw.ReportLog(SwitchInfo, fmt.Sprintf("Status check of slave node (%s:%d) passed", ip, port))
	return nil
}

// GetSlaveCheckSum returns checksum count and failure count
func (sw *MySQLBaseSwitchInstance) GetSlaveCheckSum(db *hamysql.DB) (int, int, error) {
	if db == nil {
		return 0, 0, gerrors.New(gerrors.InvalidParameter, "GetSlaveCheckSum got nil db")
	}
	ip := db.Host()
	port := db.Port()

	var (
		checksumCnt, checksumFailCnt int
	)

	err := db.DB().Raw(CheckSumSQL).Scan(&checksumCnt).Error
	if err != nil {
		logger.Error("failed to get checksumCnt from node(%s:%d), errmsg: %s", ip, port, err.Error())
		return 0, 0, err
	}

	err = db.DB().Raw(CheckSumFailSQL).Scan(&checksumFailCnt).Error
	if err != nil {
		logger.Error("failed to get checksumFailCnt from node(%s:%d), errmsg: %s", ip, port, err.Error())
		return checksumCnt, 0, err
	}

	return checksumCnt, checksumFailCnt, nil
}

// GetSlaveTimeDelay retrieves slave replication delay information
func (sw *MySQLBaseSwitchInstance) GetSlaveTimeDelay(slaveDB *hamysql.DB) (int, int, error) {
	if slaveDB == nil {
		return 0, 0, gerrors.New(gerrors.InvalidParameter, "GetSlaveDelay got nil db")
	}
	ip := slaveDB.Host()
	port := slaveDB.Port()

	slaveStatus := SlaveStatusInfo{}
	err := slaveDB.DB().Raw("show slave status").Scan(&slaveStatus).Error
	if err != nil {
		logger.Error("failed to query slave status of (%s:%d), errmsg: %s", ip, port, err.Error())
		return 0, 0, err
	}
	logger.Debug("slave status info: %v", slaveStatus)

	delayInfo := SlaveTimeDelayInfo{}
	err = slaveDB.DB().Raw(CheckDelaySQL, slaveStatus.MasterServerID).Scan(&delayInfo).Error
	if err != nil {
		logger.Error("failed to query slave(%s:%d) delay info, errmsg: %s", ip, port, err.Error())
		return 0, 0, err
	}

	return int(delayInfo.SlaveIODelay), int(delayInfo.SlaveHeartbeatDelay), nil
}

// HasUserCreatedDatabase checks if user-created databases exist
func (sw *MySQLBaseSwitchInstance) HasUserCreatedDatabase(db *hamysql.DB) (bool, error) {
	if db == nil {
		return false, gerrors.New(gerrors.InvalidParameter, "HasUserCreatedDatabase got nil db")
	}
	ip := db.Host()
	port := db.Port()

	var systemDbs = map[string]bool{
		"mysql":              true,
		"information_schema": true,
		"performance_schema": true,
		"test":               true,
		"infodba_schema":     true,
		"sys":                true,
	}

	var databases []string
	err := db.DB().Raw("show databases").Scan(&databases).Error
	if err != nil {
		logger.Error("failed to get all databases from node(%s:%d), errmsg: %s", ip, port, err.Error())
		return false, err
	}

	for _, database := range databases {
		if _, exists := systemDbs[database]; !exists {
			return true, nil
		}
	}

	logger.Info("no user-created database found on node(%s:%d)", ip, port)
	return false, nil
}

// CheckSlaveCheckSum checks the slave checksum status
func (sw *MySQLBaseSwitchInstance) CheckSlaveCheckSum(ip string, port int, checksumCnt int, checksumFailCnt int) error {
	if checksumCnt < 1 {
		return gerrors.Newf(gerrors.NodeAbnormal, "No checksum was done on db(%s:%d)", ip, port)
	}
	logger.Debug("Checksum was done on slave db(%s:%d)", ip, port)

	if checksumFailCnt > AllowedMaxChecksumFailCnt {
		return gerrors.Newf(gerrors.NodeAbnormal, "Checksum failure count (%d) of db(%s:%d) "+
			"is larger than allowed (%d)", checksumFailCnt, ip, port, AllowedMaxChecksumFailCnt)
	}
	sw.ReportLogf(SwitchInfo, "Checksum failure count (%d) of db(%s:%d) is in "+
		"allowed range(%d)", checksumFailCnt, ip, port, AllowedMaxChecksumFailCnt)

	return nil
}

// CheckSlaveTimeDelay checks the slave time delay
func (sw *MySQLBaseSwitchInstance) CheckSlaveTimeDelay(ip string, port int, slaveDelay int, timeDelay int) error {
	if slaveDelay >= AllowedMaxSlaveDelay {
		return gerrors.Newf(gerrors.NodeAbnormal, "IO_Thread delay (%d) on slave(%s:%d) is larger than allowed (%d)",
			slaveDelay, ip, port, AllowedMaxSlaveDelay)
	}
	sw.ReportLogf(SwitchInfo, "IO_Thread delay (%d) on slave(%s:%d) is in allowed range(%d)",
		slaveDelay, ip, port, AllowedMaxSlaveDelay)

	if timeDelay >= AllowedMaxTimeDelay {
		return gerrors.Newf(gerrors.NodeAbnormal, "heartbeat delay (%d) on slave(%s:%d) is larger than allowed (%d)",
			timeDelay, ip, port, AllowedMaxTimeDelay)
	}
	sw.ReportLogf(SwitchInfo, "heartbeat delay (%d) on slave(%s:%d) is in allowed range(%d)",
		timeDelay, ip, port, AllowedMaxTimeDelay)

	return nil
}

// CheckSlaveStatus verifies if slave node satisfies switching conditions
func (sw *MySQLBaseSwitchInstance) CheckSlaveStatus() error {
	// TODO: get the following values dynamically
	ignoreCheckSum := DefaultIgnoreCheckSum
	ignoreSlaveDelay := DefaultIgnoreSlaveDelay
	ip := sw.StandBySlave.Ip
	port := sw.StandBySlave.Port

	slaveDB, err := hamysql.New(
		hamysql.OptionProto(MySQLProtocol),
		hamysql.OptionIP(ip),
		hamysql.OptionPort(port),
		hamysql.OptionUser(MySQLUser),
		hamysql.OptionPassword(MySQLPassword),
		hamysql.OptionDBName(MySQLDefaultDB),
	)
	if err != nil {
		logger.Warn("create mysql instance(%s:%d) failed, %v", ip, port, err)
		return err
	}

	defer func() {
		con, _ := slaveDB.DB().DB()
		if err = con.Close(); err != nil {
			logger.Warn("close slave DB connect(%s:%d) failed: %s", ip, port, err.Error())
		}
	}()

	sw.ReportLog(SwitchInfo, "try to check slave status info")
	if err := sw.CheckSqlReplicationDelay(slaveDB, ignoreSlaveDelay); err != nil {
		return err
	}

	var slaveDelay, timeDelay int
	if !ignoreSlaveDelay {
		if slaveDelay, timeDelay, err = sw.GetSlaveTimeDelay(slaveDB); err != nil {
			return err
		}
	}

	var needCheck bool
	if needCheck, err = sw.HasUserCreatedDatabase(slaveDB); err != nil {
		return err
	}

	sw.ReportLog(SwitchInfo, "try to check slave checksum info.")
	checksumCnt := 1
	checksumFailCnt := 0
	if !ignoreCheckSum {
		if checksumCnt, checksumFailCnt, err = sw.GetSlaveCheckSum(slaveDB); err != nil {
			return err
		}
	}
	sw.ReportLogf(SwitchInfo, "checksumCnt:%d, checksumFail:%d, slaveDelay:%d, timeDelay:%d",
		checksumCnt, checksumFailCnt, slaveDelay, timeDelay)

	if !needCheck {
		sw.ReportLogf(SwitchInfo, "No user-created database found on db(%s:%d), skip checksum check", ip, port)
		return nil
	}

	if sw.Status == hamodel.AVAILABLE { // Is this necessary? Actually the delay check is not skipped
		checksumCnt, checksumFailCnt, slaveDelay, timeDelay = 1, 0, 0, 0
		sw.ReportLogf(SwitchInfo, "instance(%s:%d) is available, skip the check of delay and checksum", ip, port)
	}

	if err = sw.CheckSlaveCheckSum(ip, port, checksumCnt, checksumFailCnt); err != nil {
		return err
	}

	if err = sw.CheckSlaveTimeDelay(ip, port, slaveDelay, timeDelay); err != nil {
		return err
	}

	return nil
}

// StopSlave stops slave replication
func (sw *MySQLBaseSwitchInstance) StopSlave(slaveDB *hamysql.DB) error {
	if slaveDB == nil {
		return gerrors.New(gerrors.InvalidParameter, "ResetSlave got nil slaveDB")
	}
	slaveIp := slaveDB.Host()
	slavePort := slaveDB.Port()
	stopSlaveSQL := "stop slave"

	logger.Info("Try to STOP SLAVE on %s:%d", slaveIp, slavePort)
	err := slaveDB.DB().Exec(stopSlaveSQL).Error
	if err != nil {
		return gerrors.Newf(gerrors.Failure,
			"failed to stop slave on node(%s:%d), errmsg: %s", slaveIp, slavePort, err.Error())
	}
	logger.Info("execute '%s' successfully on slave(%s:%d)", stopSlaveSQL, slaveIp, slavePort)
	return nil
}

// StartSlave starts slave replication
func (sw *MySQLBaseSwitchInstance) StartSlave(slaveDB *hamysql.DB) error {
	if slaveDB == nil {
		return gerrors.New(gerrors.InvalidParameter, "StartSlave got nil slaveDB")
	}
	slaveIp := slaveDB.Host()
	slavePort := slaveDB.Port()
	startSlaveSQL := "start slave"

	logger.Info("Try to START SLAVE on %s:%d", slaveIp, slavePort)
	err := slaveDB.DB().Exec(startSlaveSQL).Error
	if err != nil {
		return gerrors.Newf(gerrors.Failure,
			"failed to start slave on node(%s:%d), errmsg: %s", slaveIp, slavePort, err.Error())
	}
	logger.Info("execute '%s' successfully on slave(%s:%d)", startSlaveSQL, slaveIp, slavePort)
	return nil
}

// ShowMasterStatus retrieves master status information
func (sw *MySQLBaseSwitchInstance) ShowMasterStatus(db *hamysql.DB) (*MasterStatusInfo, error) {
	if db == nil {
		return nil, gerrors.New(gerrors.InvalidParameter, "ShowMasterStatus got nil db")
	}
	slaveIp := db.Host()
	slavePort := db.Port()
	showMasterSQL := "show master status"

	masterStatus := &MasterStatusInfo{}
	logger.Info("Try to SHOW MASTER STATUS on %s:%d", slaveIp, slavePort)
	err := db.DB().Raw(showMasterSQL).Scan(masterStatus).Error
	if err != nil {
		return nil, gerrors.Newf(gerrors.Failure,
			"failed to get master status on node(%s:%d), errmsg: %s", slaveIp, slavePort, err.Error())
	}
	logger.Info("execute '%s' successfully on node(%s:%d)", showMasterSQL, slaveIp, slavePort)

	return masterStatus, nil
}

// ShowSlaveStatus retrieves slave status information
func (sw *MySQLBaseSwitchInstance) ShowSlaveStatus(slaveDB *hamysql.DB) (*SlaveStatusInfo, error) {
	if slaveDB == nil {
		return nil, gerrors.New(gerrors.InvalidParameter, "ShowSlaveStatus got nil slaveDB")
	}
	slaveIp := slaveDB.Host()
	slavePort := slaveDB.Port()
	showSlaveSQL := "show slave status"

	logger.Info("Try to SHOW SLAVE STATUS on %s:%d", slaveIp, slavePort)
	slaveStatus := &SlaveStatusInfo{}
	err := slaveDB.DB().Raw(showSlaveSQL).Scan(slaveStatus).Error
	if err != nil {
		return nil, gerrors.Newf(gerrors.Failure,
			"failed to get slave status on node(%s:%d), errmsg: %s", slaveIp, slavePort, err.Error())
	}
	logger.Info("execute '%s' successfully on node(%s:%d)", showSlaveSQL, slaveIp, slavePort)

	return slaveStatus, nil
}

// ResetSlave resets slave replication settings
func (sw *MySQLBaseSwitchInstance) ResetSlave(slaveDB *hamysql.DB) error {
	if slaveDB == nil {
		return gerrors.New(gerrors.InvalidParameter, "ResetSlave got nil slaveDB")
	}
	slaveIp := slaveDB.Host()
	slavePort := slaveDB.Port()
	resetSlaveSQL := "reset slave /*!50516 all */"

	logger.Info("Try to RESET SLAVE on %s:%d", slaveIp, slavePort)
	err := slaveDB.DB().Exec(resetSlaveSQL).Error
	if err != nil {
		return gerrors.Newf(gerrors.Failure,
			"failed to reset slave on node(%s:%d), errmsg: %s", slaveIp, slavePort, err.Error())
	}
	logger.Info("execute '%s' successfully on slave(%s:%d)", resetSlaveSQL, slaveIp, slavePort)

	return nil
}

// ResetSlaveWithBinlogPos resets slave and gets consistent binlog position
func (sw *MySQLBaseSwitchInstance) ResetSlaveWithBinlogPos(slaveIp string, slavePort int) (string, uint64, error) {
	slaveDB, err := hamysql.New(
		hamysql.OptionProto(MySQLProtocol),
		hamysql.OptionIP(slaveIp),
		hamysql.OptionPort(slavePort),
		hamysql.OptionUser(MySQLUser),
		hamysql.OptionPassword(MySQLPassword),
		hamysql.OptionDBName(MySQLDefaultDB),
	)
	if err != nil {
		logger.Warn("create slave mysql instance(%s:%d) failed, %v", slaveIp, slavePort, err)
		return "", 0, err
	}

	defer func() {
		con, _ := slaveDB.DB().DB()
		if err = con.Close(); err != nil {
			logger.Warn("close slave DB connect(%s:%d) failed: %s", slaveIp, slavePort, err.Error())
		}
	}()

	err = sw.StopSlave(slaveDB)
	if err != nil {
		return "", 0, err
	}

	masterStatus := &MasterStatusInfo{}
	masterStatus, err = sw.ShowMasterStatus(slaveDB)
	if err != nil {
		return "", 0, err
	}

	err = sw.ResetSlave(slaveDB)
	if err != nil {
		return masterStatus.File, masterStatus.Position, err
	}

	return masterStatus.File, masterStatus.Position, nil
}

// ChangeMasterAuto automatically changes master configuration
func (sw *MySQLBaseSwitchInstance) ChangeMasterAuto(slaveIp string, slavePort int, changeMasterSQL string) error {
	slaveDB, err := hamysql.New(
		hamysql.OptionProto(MySQLProtocol),
		hamysql.OptionIP(slaveIp),
		hamysql.OptionPort(slavePort),
		hamysql.OptionUser(MySQLUser),
		hamysql.OptionPassword(MySQLPassword),
		hamysql.OptionDBName(MySQLDefaultDB),
	)
	if err != nil {
		logger.Warn("create slave mysql instance(%s:%d) failed, %v", slaveIp, slavePort, err)
		return err
	}

	defer func() {
		con, _ := slaveDB.DB().DB()
		if err = con.Close(); err != nil {
			logger.Warn("close slave DB connect(%s:%d) failed: %s", slaveIp, slavePort, err.Error())
		}
	}()

	err = sw.StopSlave(slaveDB)
	if err != nil {
		return err
	}

	slaveStatus, err := sw.ShowSlaveStatus(slaveDB)
	if err != nil {
		return err
	}

	sw.ReportLog(SwitchInfo, fmt.Sprintf("Before switching to the new master node, "+
		"the actual synchronization position of the slave node(%s:%d) is: [binlog_file:%s, binlog_pos:%d]",
		slaveIp, slavePort, slaveStatus.RelayMasterLogFile, slaveStatus.ExecMasterLogPos))

	err = slaveDB.DB().Exec(changeMasterSQL).Error
	if err != nil {
		return gerrors.Newf(gerrors.Failure, "change master failed on node(%s:%d), errmsg: %s",
			slaveIp, slavePort, err.Error())
	}
	sw.ReportLog(SwitchInfo, fmt.Sprintf("Do CHANGE MASTER successfully on node(%s:%d)", slaveIp, slavePort))

	err = sw.StartSlave(slaveDB)
	if err != nil {
		return err
	}
	sw.ReportLog(SwitchInfo, fmt.Sprintf("Do START SLAVE successfully on node(%s:%d)", slaveIp, slavePort))

	return nil
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
		standBySlave = fmt.Sprintf("%s#%d", sw.StandBySlave.Ip, sw.StandBySlave.Port)
	}
	infoStr := fmt.Sprintf("{bk_cloud_id:%d, ip:%s, port:%d, bk_idc_city_id:%d, bk_biz_id:%d, status:%s, "+
		"cluster:%s, cluster_id:%d, cluster_type:%s, machine_type:%s, role:%s, standby_slave:%s}",
		sw.BkCloudID, sw.Ip, sw.Port, sw.BkIdcCityID, sw.BkBizID, sw.Status, sw.Cluster,
		sw.ClusterID, sw.ClusterType, sw.MachineType, sw.InstanceRole, standBySlave)
	return infoStr
}

// CheckMySQLStorageMaster performs pre-switch validation checks for "backend_master" node
func (sw *MySQLStorageSwitchInstance) CheckMySQLStorageMaster() (bool, error) {
	logger.Info("Do check before switch, info{%s}", sw.GetInstanceInfo())
	if sw.StandBySlave == nil {
		err := gerrors.Newf(gerrors.Failure, "The standby slave of master(%s:%d) is nil", sw.Ip, sw.Port)
		sw.ReportLog(SwitchFail, err.Error())
		return false, err
	}
	if sw.StandBySlave.Status == hamodel.UNAVAILABLE {
		err := gerrors.Newf(gerrors.Failure, "The standby slave(%s:%d) of master(%s:%d) is unavailable",
			sw.StandBySlave.Ip, sw.StandBySlave.Port, sw.Ip, sw.Port)
		sw.ReportLog(SwitchFail, err.Error())
		return false, err
	}

	if err := sw.CheckSlaveStatus(); err != nil {
		sw.ReportLog(SwitchFail, err.Error())
		return false, err
	}

	if len(sw.ProxyInstanceSet) == 0 {
		err := gerrors.Newf(gerrors.Failure,
			"No proxy instances were found for storage node(%s:%d)", sw.Ip, sw.Port)
		sw.ReportLog(SwitchFail, err.Error())
		return false, err
	}

	return true, nil
}

// CheckBeforeSwitch performs pre-switch validation checks
func (sw *MySQLStorageSwitchInstance) CheckBeforeSwitch() (checkPass bool, err error) {
	switch sw.InstanceRole {
	case hamodel.MySQLStorageSlave:
		checkPass = false
		sw.ReportLogf(SwitchInfo, "The instance(%s:%d) is a slave node, no need to check", sw.Ip, sw.Port)
	case hamodel.MySQLStorageRepeater:
		checkPass = false
		err = gerrors.Newf(gerrors.Failure, "The instance(%s:%d) is a repeater, dbha don't support", sw.Ip, sw.Port)
		sw.ReportLog(SwitchFail, err.Error())
	case hamodel.MySQLStorageMaster:
		checkPass, err = sw.CheckMySQLStorageMaster()
	default:
		checkPass = false
		err = gerrors.Newf(gerrors.Failure,
			"The role of the node to be switched is unknown, info{%s}", sw.GetInstanceInfo())
		sw.ReportLog(SwitchFail, err.Error())
	}

	return
}

// SwitchProxyBackendAddress switches proxy backend to new address
func SwitchProxyBackendAddress(proxyIp string, proxyAdminPort int, proxyUser string, proxyPasswd string,
	slaveIp string, slavePort int) error {
	proxyDB, err := hamysql.New(
		hamysql.OptionProto(MySQLProtocol),
		hamysql.OptionIP(proxyIp),
		hamysql.OptionPort(proxyAdminPort),
		hamysql.OptionUser(proxyUser),
		hamysql.OptionPassword(proxyPasswd),
		hamysql.OptionDBName(MySQLProxyDefaultDB),
	)
	if err != nil {
		logger.Warn("create mysql instance(%s:%d) failed, %v", proxyIp, proxyAdminPort, err)
		return err
	}

	defer func() {
		con, _ := proxyDB.DB().DB()
		if err = con.Close(); err != nil {
			logger.Warn("close proxy DB connect(%s:%d) failed: %s", proxyIp, proxyAdminPort, err.Error())
		}
	}()

	switchSql := fmt.Sprintf("refresh_backends('%s:%d',1)", slaveIp, slavePort)
	querySql := "select * from backends"

	err = proxyDB.DB().Exec(switchSql).Error
	if err != nil {
		errMsg := fmt.Sprintf("failed to execute sql(%s), errmsg: %s", switchSql, err.Error())
		logger.Error("%s", errMsg)
		return gerrors.New(gerrors.Failure, errMsg)
	}

	var backendList []ProxyBackendInfo
	err = proxyDB.DB().Raw(querySql).Scan(&backendList).Error
	if err != nil {
		errMsg := fmt.Sprintf("failed to execute sql(%s), errmsg: %s", querySql, err.Error())
		logger.Error("%s", errMsg)
		return gerrors.New(gerrors.Failure, errMsg)
	}

	slaveAddress := fmt.Sprintf("%s:%d", slaveIp, slavePort)
	for _, oneBackend := range backendList {
		if oneBackend.Address == slaveAddress {
			logger.Info("refreshing proxy(%s:%d) backend to %s worked", proxyIp, proxyAdminPort, slaveIp)
			// TODO: There are some redundant processing logics in dbha-v1 here, will modify after understanding it better
			return nil
		}
	}
	errMsg := fmt.Sprintf("refreshing proxy(%s:%d) backend to %s didn't work", proxyIp, proxyAdminPort, slaveAddress)
	logger.Error("%s", errMsg)
	return gerrors.New(gerrors.Failure, errMsg)
}

// DoSwitch performs the actual MySQL storage node switching
//  1. refresh all proxies' backends to 1.1.1.1
//  2. reset slave status for the standby slave and get its
//     consistent synchronization position(binlog file and binlog position)
//  3. refresh all proxies' backends to the alive mysql(standby slave)
func (sw *MySQLStorageSwitchInstance) DoSwitch() error {
	proxyUser := MySQLProxyUser
	proxyPasswd := MySQLProxyPassword

	sw.ReportLog(SwitchInfo, "switch step 1: update all proxies' backends to 1.1.1.1 first")
	for _, proxyIns := range sw.ProxyInstanceSet {
		sw.ReportLog(SwitchInfo, fmt.Sprintf("try to refresh backends to 1.1.1.1 for the proxy(%s:%d)",
			proxyIns.Ip, proxyIns.Port))
		err := SwitchProxyBackendAddress(proxyIns.Ip, proxyIns.AdminPort, proxyUser, proxyPasswd,
			"1.1.1.1", 3306)
		if err != nil {
			err = gerrors.Newf(gerrors.Failure,
				"failed to refresh backends to 1.1.1.1 for the proxy(%s:%d), errmsg: %s",
				proxyIns.Ip, proxyIns.Port, err.Error())
			sw.ReportLog(SwitchFail, err.Error())
			return err
		}
		sw.ReportLog(SwitchInfo, fmt.Sprintf("refresh backends to 1.1.1.1 successfully for the proxy(%s:%d)",
			proxyIns.Ip, proxyIns.Port))
	}
	sw.ReportLog(SwitchInfo, "update all proxies' backends to 1.1.1.1 successfully")

	sw.ReportLog(SwitchInfo, "switch step 2: reset slave status for the standby slave")
	binlogFile, binlogPosition, err := sw.ResetSlaveWithBinlogPos(sw.StandBySlave.Ip, sw.StandBySlave.Port)
	if err != nil {
		err = gerrors.Newf(gerrors.Failure, "failed to reset slave status for the standby slave(%s:%d), errmsg: %s",
			sw.StandBySlave.Ip, sw.StandBySlave.Port, err.Error())
		sw.ReportLog(SwitchFail, err.Error())
		return err
	}

	sw.NewMasterBinlogFile = binlogFile
	sw.NewMasterBinlogPos = binlogPosition
	sw.ReportLog(SwitchInfo, fmt.Sprintf("reset slave status successfully for the standby slave(%s:%d), "+
		"binlog info: [binlog_file:%s, binlog_pos:%d]",
		sw.StandBySlave.Ip, sw.StandBySlave.Port, binlogFile, binlogPosition))

	sw.ReportLog(SwitchInfo, "switch step 3: update all proxies' backends to the new master")
	for _, proxyIns := range sw.ProxyInstanceSet {
		sw.ReportLog(SwitchInfo, fmt.Sprintf("try to refresh backends to (%s:%d) for the proxy(%s:%d)",
			sw.StandBySlave.Ip, sw.StandBySlave.Port, proxyIns.Ip, proxyIns.Port))
		err = SwitchProxyBackendAddress(proxyIns.Ip, proxyIns.AdminPort, proxyUser,
			proxyPasswd, sw.StandBySlave.Ip, sw.StandBySlave.Port)
		if err != nil {
			err = gerrors.Newf(gerrors.Failure,
				"failed to refresh backends to (%s:%d) for the proxy(%s:%d), errmsg: %s",
				sw.StandBySlave.Ip, sw.StandBySlave.Port, proxyIns.Ip, proxyIns.Port, err.Error())
			sw.ReportLog(SwitchFail, err.Error())
		}
		sw.ReportLog(SwitchInfo, fmt.Sprintf("refresh backends to (%s:%d) successfully for the proxy(%s:%d)",
			sw.StandBySlave.Ip, sw.StandBySlave.Port, proxyIns.Ip, proxyIns.Port))
	}
	sw.ReportLog(SwitchInfo, "update all proxies' backends to the new master successfully")

	return nil
}

// UpdateMetaInfo updates metadata after switching
func (sw *MySQLStorageSwitchInstance) UpdateMetaInfo() error {
	err := sw.dbmClient.SwapMySQLRole(sw.Ip, sw.Port, sw.StandBySlave.Ip, sw.StandBySlave.Port)
	if err != nil {
		errMsg := fmt.Sprintf("swap db-mysql role [master:%s:%d, slave:%s:%d] failed. errmsg:%s",
			sw.Ip, sw.Port, sw.StandBySlave.Ip, sw.StandBySlave.Port, err.Error())
		sw.ReportLog(SwitchFail, errMsg)
		return err
	}
	sw.ReportLog(SwitchInfo, fmt.Sprintf("swap db-mysql role [master:%s:%d, slave:%s:%d] successfully",
		sw.Ip, sw.Port, sw.StandBySlave.Ip, sw.StandBySlave.Port))
	return nil
}

// DoFinal performs final operations after switch completion
func (sw *MySQLStorageSwitchInstance) DoFinal() error {
	sw.ReportLog(SwitchInfo, fmt.Sprintf("Do final things after switch for node(%s:%d)",
		sw.Ip, sw.Port))

	logger.Debug("tbinlogdumpers info of node(%s:%d): %s", sw.Ip, sw.Port, sw.GetBinlogDumperInfo())

	if (sw.InstanceRole != hamodel.MySQLStorageSlave) || len(sw.BinlogDumperSet) == 0 {
		sw.ReportLogf(SwitchInfo, "no need to switch tbinlogdumper for node(%s:%d)", sw.Ip, sw.Port)
		return nil
	}

	switchInstances := []DumperSwitchInstance{}
	for _, dumper := range sw.BinlogDumperSet {
		switchInstances = append(switchInstances, DumperSwitchInstance{
			Ip:             dumper.Ip,
			Port:           dumper.Port,
			BinlogFile:     sw.NewMasterBinlogFile,
			BinlogPosition: sw.NewMasterBinlogPos,
		})
	}

	switchInfos := []DumperSwitchInfo{
		{
			ClusterDomain:   sw.Cluster,
			SwitchInstances: switchInstances,
		},
	}

	err := sw.dbmClient.SwitchBinlogDumper(sw.GetApp(), switchInfos)
	if err != nil {
		errMsg := fmt.Sprintf("failed to switch all tbinlogdumpers for the node(%s:%d), errmsg: %s",
			sw.Ip, sw.Port, err.Error())
		sw.ReportLog(SwitchFail, errMsg)
		return gerrors.New(gerrors.Failure, errMsg)
	}
	sw.ReportLogf(SwitchInfo, "switch all tbinlogdumpers successfully for the node(%s:%d)",
		sw.Ip, sw.Port)

	return nil
}

// MySQLProxySwitchInstance handles MySQL proxy node switching
type MySQLProxySwitchInstance struct {
	MySQLBaseSwitchInstance
}

// DoSwitch deletes proxy instance from bound entries
func (sw *MySQLProxySwitchInstance) DoSwitch() error {
	sw.ReportLogf(SwitchInfo, "try to delete the proxy instance(%s:%d) from all bound entries",
		sw.Ip, sw.Port)
	return sw.DeleteNameService(sw.BindEntry)
}
