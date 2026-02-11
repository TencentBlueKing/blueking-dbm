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
 * OUT OF IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

package handler

import (
	"fmt"
	"strings"
	"time"

	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"
	"dbm-services/common/dbha-v2/tools/internal/cluster/config"
	"dbm-services/common/dbha-v2/tools/internal/cluster/dbm"
)

const (
	MySQLProtocol string = "tcp"
)

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

// MasterStatusInfo represents MySQL master status information
type MasterStatusInfo struct {
	File            string
	Position        uint64
	BinlogDoDB      string
	BinlogIgnoreDB  string
	ExecutedGtidSet string
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

// MysqlBaseHandler is a base handler for mysql
type MysqlBaseHandler struct {
	dbmClient *dbm.Client
}

// StopSlave stops slave replication
func (hdl *MysqlBaseHandler) StopSlave(slaveDB *hamysql.GormDB) error {
	if slaveDB == nil {
		return gerrors.New(gerrors.InvalidParameter, "ResetSlave got nil slaveDB")
	}
	slaveIp := slaveDB.Host()
	slavePort := slaveDB.Port()
	stopSlaveSQL := "stop slave"

	if err := slaveDB.DB().Exec(stopSlaveSQL).Error; err != nil {
		return gerrors.Newf(gerrors.Failure,
			"failed to stop slave on node(%s:%d), errmsg: %s", slaveIp, slavePort, err.Error())
	}
	return nil
}

// StartSlave starts slave replication
func (hdl *MysqlBaseHandler) StartSlave(slaveDB *hamysql.GormDB) error {
	if slaveDB == nil {
		return gerrors.New(gerrors.InvalidParameter, "StartSlave got nil slaveDB")
	}
	slaveIp := slaveDB.Host()
	slavePort := slaveDB.Port()
	startSlaveSQL := "start slave"

	if err := slaveDB.DB().Exec(startSlaveSQL).Error; err != nil {
		return gerrors.Newf(gerrors.Failure,
			"failed to start slave on node(%s:%d), errmsg: %s", slaveIp, slavePort, err.Error())
	}
	return nil
}

// ShowMasterStatus retrieves master status information
func (hdl *MysqlBaseHandler) ShowMasterStatus(db *hamysql.GormDB) (*MasterStatusInfo, error) {
	if db == nil {
		return nil, gerrors.New(gerrors.InvalidParameter, "ShowMasterStatus got nil db")
	}
	slaveIp := db.Host()
	slavePort := db.Port()
	showMasterSQL := "show master status"

	masterStatus := &MasterStatusInfo{}
	if err := db.DB().Raw(showMasterSQL).Scan(masterStatus).Error; err != nil {
		return nil, gerrors.Newf(gerrors.Failure,
			"failed to get master status on node(%s:%d), errmsg: %s", slaveIp, slavePort, err.Error())
	}

	return masterStatus, nil
}

// ShowSlaveStatus retrieves slave status information
func (hdl *MysqlBaseHandler) ShowSlaveStatus(slaveDB *hamysql.GormDB) (*SlaveStatusInfo, error) {
	if slaveDB == nil {
		return nil, gerrors.New(gerrors.InvalidParameter, "ShowSlaveStatus got nil slaveDB")
	}
	slaveIp := slaveDB.Host()
	slavePort := slaveDB.Port()
	showSlaveSQL := "show slave status"

	slaveStatus := &SlaveStatusInfo{}
	if err := slaveDB.DB().Raw(showSlaveSQL).Scan(slaveStatus).Error; err != nil {
		return nil, gerrors.Newf(gerrors.Failure,
			"failed to get slave status on node(%s:%d), errmsg: %s", slaveIp, slavePort, err.Error())
	}

	return slaveStatus, nil
}

// ResetSlave resets slave replication settings
func (hdl *MysqlBaseHandler) ResetSlave(slaveDB *hamysql.GormDB) error {
	if slaveDB == nil {
		return gerrors.New(gerrors.InvalidParameter, "ResetSlave got nil slaveDB")
	}
	slaveIp := slaveDB.Host()
	slavePort := slaveDB.Port()
	resetSlaveSQL := "reset slave /*!50516 all */"

	if err := slaveDB.DB().Exec(resetSlaveSQL).Error; err != nil {
		return gerrors.Newf(gerrors.Failure,
			"failed to reset slave on node(%s:%d), errmsg: %s", slaveIp, slavePort, err.Error())
	}

	return nil
}

// stopSlaveForMaster stops slave for master
func (hdl *MysqlBaseHandler) stopSlaveForMaster(ip string, port int) (string, uint64, error) {
	masterDB, err := hamysql.NewGormDB(
		hamysql.OptionProto(MySQLProtocol),
		hamysql.OptionIP(ip),
		hamysql.OptionPort(port),
		hamysql.OptionUser(config.ClusterConfig.AuthInfo.User),
		hamysql.OptionPassword(config.ClusterConfig.AuthInfo.Password),
	)
	if err != nil {
		return "", 0, gerrors.Newf(gerrors.Failure, "failed to connect to master node(%s:%d), errmsg: %s",
			ip, port, err.Error())
	}

	defer masterDB.Close()

	if err = hdl.StopSlave(masterDB); err != nil {
		return "", 0, err
	}

	masterStatus := &MasterStatusInfo{}
	if masterStatus, err = hdl.ShowMasterStatus(masterDB); err != nil {
		return "", 0, err
	}

	if err = hdl.ResetSlave(masterDB); err != nil {
		return masterStatus.File, masterStatus.Position, err
	}

	return masterStatus.File, masterStatus.Position, nil
}

// changeMasterForAllSlave changes master for all slave
func (hdl *MysqlBaseHandler) changeMasterForAllSlave(slaveList []config.InstanceAddress, targetIp string, targetPort int,
	binlogFile string, binlogPos uint64) error {
	changeMasterSQL := fmt.Sprintf("CHANGE MASTER TO "+
		"MASTER_HOST = '%s', "+
		"MASTER_PORT = %d, "+
		"MASTER_USER = '%s', "+
		"MASTER_PASSWORD = '%s', "+
		"MASTER_LOG_FILE = '%s', "+
		"MASTER_LOG_POS = %d",
		targetIp, targetPort,
		config.ClusterConfig.AuthInfo.ReplUser, config.ClusterConfig.AuthInfo.ReplPassword,
		binlogFile, binlogPos)

	for _, slave := range slaveList {
		if err := hdl.changeMasterForSlave(slave.Host, slave.Port, changeMasterSQL); err != nil {
			return err
		}
	}

	// wait for slave to start
	time.Sleep(3 * time.Second)

	if err := hdl.checkSlaveStatus(slaveList, targetIp, targetPort); err != nil {
		return err
	}

	return nil
}

// checkSlaveStatus checks slave status
func (hdl *MysqlBaseHandler) checkSlaveStatus(slaveList []config.InstanceAddress, targetIp string, targetPort int) error {
	for _, slave := range slaveList {
		slaveDB, err := hamysql.NewGormDB(
			hamysql.OptionProto(MySQLProtocol),
			hamysql.OptionIP(slave.Host),
			hamysql.OptionPort(slave.Port),
			hamysql.OptionUser(config.ClusterConfig.AuthInfo.User),
			hamysql.OptionPassword(config.ClusterConfig.AuthInfo.Password),
		)
		if err != nil {
			return gerrors.Newf(gerrors.Failure, "failed to connect to slave node(%s:%d), errmsg: %s",
				slave.Host, slave.Port, err.Error())
		}

		defer slaveDB.Close()

		slaveStatus, err := hdl.ShowSlaveStatus(slaveDB)
		if err != nil {
			return gerrors.Newf(gerrors.Failure, "failed to check slave status of node(%s:%d), errmsg: %s",
				slave.Host, slave.Port, err.Error())
		}

		if slaveStatus.SlaveIORunning != "Yes" || slaveStatus.SlaveSQLRunning != "Yes" ||
			slaveStatus.MasterHost != targetIp || slaveStatus.MasterPort != targetPort {
			return gerrors.Newf(gerrors.Failure, "slave status of node(%s:%d) is not correct", slave.Host, slave.Port)
		}
	}

	return nil
}

// changeMasterForSlave changes master for slave
func (hdl *MysqlBaseHandler) changeMasterForSlave(slaveIp string, slavePort int, changeMasterSQL string) error {
	slaveDB, err := hamysql.NewGormDB(
		hamysql.OptionProto(MySQLProtocol),
		hamysql.OptionIP(slaveIp),
		hamysql.OptionPort(slavePort),
		hamysql.OptionUser(config.ClusterConfig.AuthInfo.User),
		hamysql.OptionPassword(config.ClusterConfig.AuthInfo.Password),
	)
	if err != nil {
		return gerrors.Newf(gerrors.Failure, "failed to connect to slave node(%s:%d), errmsg: %s",
			slaveIp, slavePort, err.Error())
	}

	defer slaveDB.Close()

	if err := hdl.StopSlave(slaveDB); err != nil {
		return err
	}

	if err = slaveDB.DB().Exec(changeMasterSQL).Error; err != nil {
		return gerrors.Newf(gerrors.Failure, "failed to change master on node(%s:%d), errmsg: %s",
			slaveIp, slavePort, err.Error())
	}

	if err = hdl.StartSlave(slaveDB); err != nil {
		return err
	}

	return nil
}

// MysqlClusterHandler provides MySQL cluster management functions
type MysqlClusterHandler struct {
	MysqlBaseHandler
}

// NewMysqlClusterHandler creates a new MysqlClusterHandler
func NewMysqlClusterHandler() *MysqlClusterHandler {
	return &MysqlClusterHandler{
		MysqlBaseHandler: MysqlBaseHandler{dbmClient: &dbm.Client{}},
	}
}

func (hdl *MysqlClusterHandler) printOneCluster(cluster *config.MysqlCluster) {
	fmt.Printf("Cluster Domain: %s\n", cluster.Domain)
	fmt.Printf("Proxy Addresses: %v\n", cluster.Proxy)
	fmt.Printf("Master: %s:%d\n", cluster.Master.Host, cluster.Master.Port)
	fmt.Printf("Slaves: %v\n", cluster.Slave)
}

func (hdl *MysqlClusterHandler) getInstanceList(cluster *config.MysqlCluster) []config.InstanceAddress {
	instanceList := []config.InstanceAddress{
		{Host: cluster.Master.Host, Port: cluster.Master.Port},
	}
	instanceList = append(instanceList, cluster.Slave...)
	for _, proxy := range cluster.Proxy {
		instanceList = append(instanceList, config.InstanceAddress{Host: proxy.Host, Port: proxy.Port})
	}

	return instanceList
}

func (hdl *MysqlClusterHandler) switchProxyBackend(proxyIp string, proxyAdminPort int,
	targetIp string, targetPort int) error {
	proxyDB, err := hamysql.NewSqlxDB(
		hamysql.OptionIP(proxyIp),
		hamysql.OptionPort(proxyAdminPort),
		hamysql.OptionUser(config.ClusterConfig.AuthInfo.ProxyUser),
		hamysql.OptionPassword(config.ClusterConfig.AuthInfo.ProxyPassword),
		hamysql.OptionCharset(""),
	)
	if err != nil {
		return gerrors.Newf(gerrors.Failure, "failed to connect to proxy(%s:%d), errmsg: %s",
			proxyIp, proxyAdminPort, err.Error())
	}

	defer proxyDB.Close()

	switchSql := fmt.Sprintf("refresh_backends('%s:%d', 1)", targetIp, targetPort)
	querySql := "select * from backends"

	if _, err = proxyDB.DB().Exec(switchSql); err != nil {
		errMsg := fmt.Sprintf("failed to execute sql(%s), errmsg: %s", switchSql, err.Error())
		return gerrors.New(gerrors.Failure, errMsg)
	}

	var backendList []ProxyBackendInfo
	if err = proxyDB.DB().Select(&backendList, querySql); err != nil {
		errMsg := fmt.Sprintf("failed to execute sql(%s), errmsg: %s", querySql, err.Error())
		return gerrors.New(gerrors.Failure, errMsg)
	}

	targetAddress := fmt.Sprintf("%s:%d", targetIp, targetPort)
	for _, oneBackend := range backendList {
		if oneBackend.Address == targetAddress {
			return nil
		}
	}
	errMsg := fmt.Sprintf("refreshing proxy(%s:%d) backend to %s didn't work", proxyIp, proxyAdminPort, targetAddress)
	return gerrors.New(gerrors.Failure, errMsg)
}

// switchAllProxiesBackend switches all proxies' backend to targetIp:targetPort
func (hdl *MysqlClusterHandler) switchAllProxiesBackend(proxyList []config.ProxyAddress, targetIp string, targetPort int) error {
	for _, proxyIns := range proxyList {
		err := hdl.switchProxyBackend(proxyIns.Host, proxyIns.AdminPort, targetIp, targetPort)
		if err != nil {
			errMsg := fmt.Sprintf("failed to switch proxy(%s:%d) backend to %s:%d, errmsg: %s",
				proxyIns.Host, proxyIns.AdminPort, targetIp, targetPort, err.Error())
			return gerrors.New(gerrors.Failure, errMsg)
		}
	}
	return nil
}

func (hdl *MysqlClusterHandler) findSlaveOfTargetRole(slaveList []config.InstanceAddress,
	targetRole dbm.DbmMetadataInstanceRole) (string, int, error) {
	for _, slave := range slaveList {
		slaveRole, err := hdl.dbmClient.QueryInstanceRole(slave.Host, slave.Port)
		if err != nil {
			return "", 0, gerrors.Newf(gerrors.Failure, "failed to query instance role of node(%s:%d), errmsg: %s",
				slave.Host, slave.Port, err.Error())
		}

		if strings.EqualFold(string(slaveRole), string(targetRole)) {
			return slave.Host, slave.Port, nil
		}
	}

	return "", 0, gerrors.Newf(gerrors.Failure, "failed to find slave of role %s", targetRole)
}

func (hdl *MysqlClusterHandler) correctBackendRole(cluster *config.MysqlCluster) error {
	masterHost := cluster.Master.Host
	masterPort := cluster.Master.Port
	masterRole, err := hdl.dbmClient.QueryInstanceRole(masterHost, masterPort)
	if err != nil {
		return gerrors.Newf(gerrors.Failure, "failed to query instance role of node(%s:%d), errmsg: %s",
			masterHost, masterPort, err.Error())
	}

	if masterRole != dbm.MySQLStorageMaster {
		curMasterHost, curMasterPort, err := hdl.findSlaveOfTargetRole(cluster.Slave, dbm.MySQLStorageMaster)
		if err != nil {
			return gerrors.Newf(gerrors.Failure, "failed to find swap target: %s", err.Error())
		}

		if err := hdl.dbmClient.SwapMySQLRole(curMasterHost, curMasterPort, masterHost, masterPort); err != nil {
			return gerrors.Newf(gerrors.Failure, "failed to swap role of (%s:%d) and (%s:%d), errmsg: %s",
				curMasterHost, curMasterPort, masterHost, masterPort, err.Error())
		}
	}

	for _, slave := range cluster.Slave {
		slaveRole, err := hdl.dbmClient.QueryInstanceRole(slave.Host, slave.Port)
		if err != nil {
			return gerrors.Newf(gerrors.Failure, "failed to query instance role of node(%s:%d), errmsg: %s",
				slave.Host, slave.Port, err.Error())
		}

		if slaveRole != dbm.MySQLStorageSlave {
			return gerrors.Newf(gerrors.Failure, "slave(%s:%d) role is not %s", slave.Host, slave.Port, dbm.MySQLStorageSlave)
		}
	}

	return nil
}

func (hdl *MysqlClusterHandler) addNodesToDomain(instList []config.InstanceAddress, domain string, bkBizId int) error {
	instInfoList, err := hdl.dbmClient.GetAllInstancesOfDomain(domain)
	if err != nil {
		return gerrors.Newf(gerrors.Failure, "failed to get all instances of domain %s, errmsg: %s", domain, err.Error())
	}

	isInDomain := func(ip string, port int) bool {
		for _, inst := range instInfoList {
			if inst.Ip == ip && inst.Port == port {
				return true
			}
		}
		return false
	}

	for _, inst := range instList {
		instHost := inst.Host
		instPort := inst.Port
		if isInDomain(instHost, instPort) {
			continue
		}
		if err := hdl.dbmClient.AddInstanceToDomain(instHost, instPort, domain, bkBizId); err != nil {
			return gerrors.Newf(gerrors.Failure, "failed to add instance(%s:%d) to domain %s, errmsg: %s",
				instHost, instPort, domain, err.Error())
		}
	}

	return nil
}

func (hdl *MysqlClusterHandler) addAllNodesToDomain(cluster *config.MysqlCluster) error {
	poxyList := []config.InstanceAddress{}
	for _, proxy := range cluster.Proxy {
		poxyList = append(poxyList, config.InstanceAddress{
			Host: proxy.Host,
			Port: proxy.Port,
		})
	}

	if err := hdl.addNodesToDomain(poxyList, cluster.Domain, cluster.BkBizId); err != nil {
		return err
	}

	if err := hdl.addNodesToDomain(cluster.Slave, cluster.DomainSlave, cluster.BkBizId); err != nil {
		return err
	}

	return nil
}

// resetSingleMysqlCluster reset a single mysql cluster
// Step 1: update all instances status to unavailable
// Step 2: refresh all proxies' backends to 1.1.1.1
// step 3: stop slave for master backend
// step 4: change master for all slaves
// Step 5: change backend role
// Step 6: reset all proxies' backends to master backend
// Step 7: update all instances status to running
// Step 8: add nodes to corresponding domain
func (hdl *MysqlClusterHandler) resetSingleMysqlCluster(cluster *config.MysqlCluster) error {
	hdl.printOneCluster(cluster)
	fmt.Printf("Resetting cluster %s...\n", cluster.Domain)
	instanceList := hdl.getInstanceList(cluster)

	if err := hdl.dbmClient.UpdateAllInstancesStatus(instanceList, dbm.StatusUnavailable); err != nil {
		fmt.Printf("Failed at step 1 <update all instances status to unavailable>, errmsg: %s\n", err.Error())
		return err
	}
	fmt.Printf("Step 1 <update all instances status to unavailable> done\n")

	if err := hdl.switchAllProxiesBackend(cluster.Proxy, "1.1.1.1", 3306); err != nil {
		fmt.Printf("Failed at step 2 <refresh all proxies' backends to 1.1.1.1>, errmsg: %s\n", err.Error())
		return err
	}
	fmt.Printf("Step 2 <refresh all proxies' backends to 1.1.1.1> done\n")

	binlogFile, binlogPos, err := hdl.stopSlaveForMaster(cluster.Master.Host, cluster.Master.Port)
	if err != nil {
		fmt.Printf("Failed at step 3 <stop slave for master backend>, errmsg: %s\n", err.Error())
		return err
	}
	fmt.Printf("Step 3 <stop slave for master backend> done\n")

	if err := hdl.changeMasterForAllSlave(cluster.Slave, cluster.Master.Host, cluster.Master.Port,
		binlogFile, binlogPos); err != nil {
		fmt.Printf("Failed at step 4 <change master for all slaves>, errmsg: %s\n", err.Error())
		return err
	}
	fmt.Printf("Step 4 <change master for all slaves> done\n")

	if err := hdl.correctBackendRole(cluster); err != nil {
		fmt.Printf("Failed at step 5 <correct backend role>, errmsg: %s\n", err.Error())
		return err
	}
	fmt.Printf("Step 5 <correct backend role> done\n")

	if err := hdl.switchAllProxiesBackend(cluster.Proxy, cluster.Master.Host, cluster.Master.Port); err != nil {
		fmt.Printf("Failed at step 6 <refresh all proxies' backends to master backend>, errmsg: %s\n", err.Error())
		return err
	}
	fmt.Printf("Step 6 <refresh all proxies' backends to master backend> done\n")

	if err := hdl.dbmClient.UpdateAllInstancesStatus(instanceList, dbm.StatusRunning); err != nil {
		fmt.Printf("Failed at step 7 <update all instances status to running>, errmsg: %s\n", err.Error())
		return err
	}
	fmt.Printf("Step 7 <update all instances status to running> done\n")

	if err := hdl.addAllNodesToDomain(cluster); err != nil {
		fmt.Printf("Failed at step 8 <add nodes to corresponding domain>, errmsg: %s\n", err.Error())
		return err
	}
	fmt.Printf("Step 8 <add nodes to corresponding domain> done\n")

	return nil
}

// ResetAllMysqlClusters resets all MySQL clusters
func (hdl *MysqlClusterHandler) ResetAllMysqlClusters() error {
	if config.ClusterConfig == nil {
		return gerrors.Newf(gerrors.Failure, "config is not loaded")
	}

	if hdl.dbmClient == nil {
		return gerrors.Newf(gerrors.Failure, "dbm client is nil")
	}

	if len(config.ClusterConfig.MysqlClusters) <= 0 {
		fmt.Println("No MySQL clusters to reset")
		return nil
	}

	failCount := 0
	fmt.Printf("=== Processing MySQL Clusters ===\n\n")
	for _, cluster := range config.ClusterConfig.MysqlClusters {
		if err := hdl.resetSingleMysqlCluster(&cluster); err != nil {
			failCount++
			fmt.Printf("Failed to reset cluster %s, errmsg: %s\n\n", cluster.Domain, err.Error())
			continue
		}
		fmt.Printf("Successfully reset cluster %s\n\n", cluster.Domain)
	}
	fmt.Printf("\n=== Resetting MySQL Clusters Done (total: %d, failed: %d, success: %d)===\n",
		len(config.ClusterConfig.MysqlClusters), failCount, len(config.ClusterConfig.MysqlClusters)-failCount)

	return nil
}

// ShowAllMysqlClustersDomain shows domain binding information for all MySQL clusters
func (hdl *MysqlClusterHandler) ShowAllMysqlClustersDomain() error {
	if config.ClusterConfig == nil {
		return printErrorResponse("config is not loaded")
	}

	if hdl.dbmClient == nil {
		return printErrorResponse("dbm client is nil")
	}

	clusterDomainInfoList := make([]ClusterDomainInfo, 0)

	for _, cluster := range config.ClusterConfig.MysqlClusters {
		clusterDomainInfo := ClusterDomainInfo{
			Cluster: cluster.Domain,
			Domains: make([]DomainInstanceList, 0),
		}

		if cluster.Domain != "" {
			instList, err := hdl.dbmClient.GetAllInstancesOfDomain(cluster.Domain)
			if err != nil {
				return printErrorResponsef("failed to get instances of domain(%s), errmsg: %s",
					cluster.Domain, err.Error())
			}
			instanceList := make([]string, 0)
			for _, inst := range instList {
				instanceList = append(instanceList, fmt.Sprintf("%s:%d", inst.Ip, inst.Port))
			}
			clusterDomainInfo.Domains = append(clusterDomainInfo.Domains, DomainInstanceList{
				Domain:       cluster.Domain,
				InstanceList: instanceList,
			})
		}

		if cluster.DomainSlave != "" {
			instList, err := hdl.dbmClient.GetAllInstancesOfDomain(cluster.DomainSlave)
			if err != nil {
				return printErrorResponsef("failed to get instances of domain(%s), errmsg: %s",
					cluster.DomainSlave, err.Error())
			}
			instanceList := make([]string, 0)
			for _, inst := range instList {
				instanceList = append(instanceList, fmt.Sprintf("%s:%d", inst.Ip, inst.Port))
			}
			clusterDomainInfo.Domains = append(clusterDomainInfo.Domains, DomainInstanceList{
				Domain:       cluster.DomainSlave,
				InstanceList: instanceList,
			})
		}

		clusterDomainInfoList = append(clusterDomainInfoList, clusterDomainInfo)
	}

	return printJSON(clusterDomainInfoList)
}

// ShowAllMysqlClustersNodes shows all nodes status and role for all MySQL clusters
func (hdl *MysqlClusterHandler) ShowAllMysqlClustersNodes() error {
	if config.ClusterConfig == nil {
		return printErrorResponse("config is not loaded")
	}

	if hdl.dbmClient == nil {
		return printErrorResponse("dbm client is nil")
	}

	clusterNodeInfoList := make([]ClusterNodeInfo, 0)

	for _, cluster := range config.ClusterConfig.MysqlClusters {
		ipList := make([]string, 0)
		ipList = append(ipList, cluster.Master.Host)
		for _, slave := range cluster.Slave {
			ipList = append(ipList, slave.Host)
		}
		for _, proxy := range cluster.Proxy {
			ipList = append(ipList, proxy.Host)
		}

		metadataList, err := hdl.dbmClient.QueryMetadataFromDbm(0, ipList)
		if err != nil {
			return printErrorResponsef("failed to query metadata for cluster(%s), errmsg: %s",
				cluster.Domain, err.Error())
		}

		clusterNodeInfo := ClusterNodeInfo{
			Cluster: cluster.Domain,
			Nodes:   make([]NodeInfo, 0),
		}

		for _, meta := range metadataList {
			clusterNodeInfo.Nodes = append(clusterNodeInfo.Nodes, NodeInfo{
				IP:     meta.IP,
				Port:   meta.Port,
				Status: meta.Status,
				Role:   meta.GetMySQLRole(),
			})
		}

		clusterNodeInfoList = append(clusterNodeInfoList, clusterNodeInfo)
	}

	return printJSON(clusterNodeInfoList)
}

// ShowAllMysqlClustersReplication shows replication status for all MySQL clusters
// Directly connects to all backend nodes from config file to query replication status
func (hdl *MysqlClusterHandler) ShowAllMysqlClustersReplication() error {
	if config.ClusterConfig == nil {
		return printErrorResponse("config is not loaded")
	}

	clusterReplList := make([]ClusterReplicationInfo, 0)
	user := config.ClusterConfig.AuthInfo.User
	password := config.ClusterConfig.AuthInfo.Password

	for _, cluster := range config.ClusterConfig.MysqlClusters {
		clusterRepl := ClusterReplicationInfo{
			Cluster:      cluster.Domain,
			Replications: make([]ReplicationInfo, 0),
		}

		nodeList := []config.InstanceAddress{{Host: cluster.Master.Host, Port: cluster.Master.Port}}
		for _, slave := range cluster.Slave {
			nodeList = append(nodeList, config.InstanceAddress{Host: slave.Host, Port: slave.Port})
		}

		type replResult struct {
			index    int
			replInfo *ReplicationInfo
			err      error
		}
		resultCh := make(chan replResult, len(nodeList))

		for i, node := range nodeList {
			go func(idx int, host string, port int) {
				replInfo, err := hdl.getBackendNodeReplicationInfo(host, port, user, password)
				resultCh <- replResult{index: idx, replInfo: replInfo, err: err}
			}(i, node.Host, node.Port)
		}

		// Collect results
		results := make([]*ReplicationInfo, len(nodeList))
		for range nodeList {
			result := <-resultCh
			if result.err != nil {
				return printErrorResponse(result.err.Error())
			}
			results[result.index] = result.replInfo
		}

		for _, replInfo := range results {
			clusterRepl.Replications = append(clusterRepl.Replications, *replInfo)
		}

		clusterReplList = append(clusterReplList, clusterRepl)
	}

	return printJSON(clusterReplList)
}

// getBackendNodeReplicationInfo gets replication info from a backend node
func (hdl *MysqlClusterHandler) getBackendNodeReplicationInfo(host string, port int, user, password string) (*ReplicationInfo, error) {
	db, err := hamysql.NewGormDB(
		hamysql.OptionProto(MySQLProtocol),
		hamysql.OptionIP(host),
		hamysql.OptionPort(port),
		hamysql.OptionUser(user),
		hamysql.OptionPassword(password),
	)
	if err != nil {
		return nil, gerrors.Newf(gerrors.Failure, "failed to connect to backend node(%s:%d), errmsg: %s",
			host, port, err.Error())
	}
	defer db.Close()

	slaveStatus, err := hdl.ShowSlaveStatus(db)
	if err != nil {
		return nil, gerrors.Newf(gerrors.Failure, "failed to get slave status of node(%s:%d), errmsg: %s",
			host, port, err.Error())
	}

	return &ReplicationInfo{
		IP:              host,
		Port:            port,
		MasterIP:        slaveStatus.MasterHost,
		MasterPort:      slaveStatus.MasterPort,
		SlaveIORunning:  slaveStatus.SlaveIORunning,
		SlaveSQLRunning: slaveStatus.SlaveSQLRunning,
	}, nil
}

// ShowAllMysqlClustersRouting shows proxy routing (backend) information for all MySQL clusters
func (hdl *MysqlClusterHandler) ShowAllMysqlClustersRouting() error {
	if config.ClusterConfig == nil {
		return printErrorResponse("config is not loaded")
	}

	clusterRoutingList := make([]ClusterProxyRoutingInfo, 0)

	for _, cluster := range config.ClusterConfig.MysqlClusters {
		proxyIPs := make([]string, 0, len(cluster.Proxy))
		for _, proxy := range cluster.Proxy {
			proxyIPs = append(proxyIPs, proxy.Host)
		}

		metadataList, err := hdl.dbmClient.QueryMetadataFromDbm(0, proxyIPs)
		if err != nil {
			return printErrorResponsef("failed to query metadata for cluster(%s), errmsg: %s",
				cluster.Domain, err.Error())
		}

		runningProxyIPs := make(map[string]bool)
		for _, meta := range metadataList {
			if meta.Status == string(dbm.StatusRunning) {
				runningProxyIPs[meta.IP] = true
			}
		}

		clusterRouting := ClusterProxyRoutingInfo{
			Cluster: cluster.Domain,
			Proxies: make([]ProxyRoutingEntry, 0),
		}

		for _, proxy := range cluster.Proxy {
			if !runningProxyIPs[proxy.Host] {
				continue
			}

			proxyEntry, err := hdl.getProxyRoutingEntry(proxy.Host, proxy.AdminPort)
			if err != nil {
				return printErrorResponse(err.Error())
			}
			clusterRouting.Proxies = append(clusterRouting.Proxies, *proxyEntry)
		}

		clusterRoutingList = append(clusterRoutingList, clusterRouting)
	}

	return printJSON(clusterRoutingList)
}

// getProxyRoutingEntry gets routing entry from a proxy
func (hdl *MysqlClusterHandler) getProxyRoutingEntry(host string, adminPort int) (*ProxyRoutingEntry, error) {
	proxyDB, err := hamysql.NewSqlxDB(
		hamysql.OptionIP(host),
		hamysql.OptionPort(adminPort),
		hamysql.OptionUser(config.ClusterConfig.AuthInfo.ProxyUser),
		hamysql.OptionPassword(config.ClusterConfig.AuthInfo.ProxyPassword),
		hamysql.OptionCharset(""),
	)
	if err != nil {
		return nil, gerrors.Newf(gerrors.Failure, "failed to connect to proxy(%s:%d), errmsg: %s",
			host, adminPort, err.Error())
	}
	defer proxyDB.Close()

	var backendList []ProxyBackendInfo
	if err = proxyDB.DB().Select(&backendList, "select * from backends"); err != nil {
		return nil, gerrors.Newf(gerrors.Failure, "failed to query backends on proxy(%s:%d), errmsg: %s",
			host, adminPort, err.Error())
	}

	proxyEntry := ProxyRoutingEntry{
		ProxyIP:        host,
		ProxyAdminPort: adminPort,
		Backends:       make([]ProxyBackendEntry, 0),
	}

	for _, backend := range backendList {
		proxyEntry.Backends = append(proxyEntry.Backends, ProxyBackendEntry{
			BackendNdx:   backend.BackendNdx,
			BackendAddr:  backend.Address,
			BackendState: backend.State,
		})
	}

	return &proxyEntry, nil
}
