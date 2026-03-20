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
	"sort"
	"strconv"
	"strings"
	"time"

	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"
	"dbm-services/common/dbha-v2/tools/internal/cluster/config"
	"dbm-services/common/dbha-v2/tools/internal/cluster/dbm"
)

// TenDBClusterHandler provides MySQL cluster management functions
type TenDBClusterHandler struct {
	MysqlBaseHandler
}

// TdbctlPrimaryInfo represents the result of tdbctl get primary
type TdbctlPrimaryInfo struct {
	ServerName string `gorm:"column:SERVER_NAME"`
	Host       string `gorm:"column:HOST"`
	Port       int    `gorm:"column:PORT"`
}

// NewTenDBClusterHandler creates a new MysqlClusterHandler
func NewTenDBClusterHandler() *TenDBClusterHandler {
	return &TenDBClusterHandler{
		MysqlBaseHandler: MysqlBaseHandler{dbmClient: &dbm.Client{}},
	}
}

func (hdl *TenDBClusterHandler) setTcAdmin(db *hamysql.GormDB, value int64) error {
	if db == nil {
		return gerrors.New(gerrors.InvalidParameter, "setTcAdmin got nil DB")
	}
	dbIp := db.Host()
	dbPort := db.Port()
	dbSQL := fmt.Sprintf("set tc_admin = %d", value)

	if err := db.DB().Exec(dbSQL).Error; err != nil {
		return gerrors.Newf(gerrors.Failure,
			"failed to set tc_admin=%d on node(%s:%d), errmsg: %s", value, dbIp, dbPort, err.Error())
	}
	return nil
}

// printOneTenDBCluster prints TenDBCluster information
func (hdl *TenDBClusterHandler) printOneTenDBCluster(cluster *config.TenDBCluster) {
	fmt.Printf("Cluster Domain: %s\n", cluster.Domain)
	fmt.Printf("Spider: %v\n", cluster.Spider)
	fmt.Printf("Spider Slaves: %v\n", cluster.SpiderSlave)
	fmt.Printf("TdbCtl Master: %s:%d\n", cluster.CtlMaster.Host, cluster.CtlMaster.Port)
	fmt.Printf("TdbCtl Slaves: %v\n", cluster.CtlSlave)
	fmt.Printf("Remote Master: %v\n", cluster.RemoteMaster)
	fmt.Printf("Remote Slaves: %v\n", cluster.RemoteSlave)
}

func (hdl *TenDBClusterHandler) getInstanceListForDbmStatusUpdate(cluster *config.TenDBCluster) []config.InstanceAddress {
	instanceList := make([]config.InstanceAddress, 0)
	for _, spider := range cluster.Spider {
		instanceList = append(instanceList, config.InstanceAddress{Host: spider.Host, Port: spider.Port})
	}
	for _, spider := range cluster.SpiderSlave {
		instanceList = append(instanceList, config.InstanceAddress{Host: spider.Host, Port: spider.Port})
	}
	for _, remote := range cluster.RemoteMaster {
		instanceList = append(instanceList, config.InstanceAddress{Host: remote.Host, Port: remote.Port})
	}
	for _, remote := range cluster.RemoteSlave {
		instanceList = append(instanceList, config.InstanceAddress{Host: remote.Host, Port: remote.Port})
	}
	return instanceList
}

// stopSlaveForRemoteMasterAndGetBinlogList stops slave for remote master and gets binlog list
func (hdl *TenDBClusterHandler) stopSlaveForRemoteMasterAndGetBinlogList(cluster *config.TenDBCluster) ([]config.BinlogInfo, error) {
	binlogList := make([]config.BinlogInfo, 0)

	for _, remote := range cluster.RemoteMaster {
		binlogFile, binlogPos, err := hdl.stopSlaveForMaster(remote.Host, remote.Port)
		if err != nil {
			return nil, err
		}
		binlogList = append(binlogList, config.BinlogInfo{

			TenDBClusterNodeInfo: config.TenDBClusterNodeInfo{
				Host:     remote.Host,
				Port:     remote.Port,
				User:     remote.User,
				Password: remote.Password,
			},
			File:     binlogFile,
			Position: binlogPos,
		})
	}
	return binlogList, nil
}

// changeMasterForAllRemoteSlave changes master for all remote slave
func (hdl *TenDBClusterHandler) changeMasterForAllRemoteSlave(remoteSlave []config.RemoteSlaveInfo, binlogList []config.BinlogInfo) error {
	remoteSlaveMap := make(map[string]config.RemoteSlaveInfo)
	for _, remote := range remoteSlave {
		remoteSlaveMap[remote.MasterHost+":"+strconv.Itoa(remote.MasterPort)] = remote
	}

	for _, binlog := range binlogList {
		remote, ok := remoteSlaveMap[binlog.Host+":"+strconv.Itoa(binlog.Port)]
		if !ok {
			continue
		}
		var slaveList []config.InstanceAddress
		slaveList = append(slaveList, config.InstanceAddress{
			Host: remote.Host,
			Port: remote.Port,
		})

		if err := hdl.changeMasterForAllSlave(slaveList, binlog.Host, binlog.Port, binlog.File,
			binlog.Position); err != nil {
			return err
		}
	}
	return nil
}

// correctRemoteDBRole correct remote db role
func (hdl *TenDBClusterHandler) correctRemoteDBRole(cluster *config.TenDBCluster) error {
	for _, remoteSlave := range cluster.RemoteSlave {
		masterHost := remoteSlave.MasterHost
		masterPort := remoteSlave.MasterPort
		masterRole, err := hdl.dbmClient.QueryInstanceRole(masterHost, masterPort)
		if err != nil {
			return gerrors.Newf(gerrors.Failure, "failed to query instance role of node(%s:%d), errmsg: %s",
				masterHost, masterPort, err.Error())
		}

		if masterRole != dbm.TenDBClusterRemoteMaster {
			if err := hdl.dbmClient.SwapMySQLRole(remoteSlave.Host, remoteSlave.Port, masterHost, masterPort); err != nil {
				return gerrors.Newf(gerrors.Failure, "failed to swap role of (%s:%d) and (%s:%d), errmsg: %s",
					remoteSlave.Host, remoteSlave.Port, masterHost, masterPort, err.Error())
			}
		}
	}

	for _, remoteSlave := range cluster.RemoteSlave {
		slaveRole, err := hdl.dbmClient.QueryInstanceRole(remoteSlave.Host, remoteSlave.Port)
		if err != nil {
			return gerrors.Newf(gerrors.Failure, "failed to query instance role of node(%s:%d), errmsg: %s",
				remoteSlave.Host, remoteSlave.Port, err.Error())
		}

		if slaveRole != dbm.TenDBClusterRemoteSlave {
			return gerrors.Newf(gerrors.Failure, "slave(%s:%d) role is not %s", remoteSlave.Host,
				remoteSlave.Port, dbm.TenDBClusterRemoteSlave)
		}
	}

	return nil
}

// ConnectTdbctlNode connects tdbctl node using authInfo credentials
func (hdl *TenDBClusterHandler) ConnectTdbctlNode(ip string, port int) (*hamysql.GormDB, error) {
	tdbctlDB, err := hamysql.NewGormDB(
		hamysql.OptionProto(MySQLProtocol),
		hamysql.OptionIP(ip),
		hamysql.OptionPort(port),
		hamysql.OptionUser(config.ClusterConfig.AuthInfo.User),
		hamysql.OptionPassword(config.ClusterConfig.AuthInfo.Password),
		hamysql.OptionSkipInitializeWithVersion(false),
		hamysql.OptionDisableDatetimePrecision(true),
		hamysql.OptionCharset(""),
	)
	return tdbctlDB, err
}

// stopSlaveForTdbCtlMaster stops slave for tdbctl master
func (hdl *TenDBClusterHandler) stopSlaveForTdbCtlMaster(ip string, port int) error {
	masterDB, err := hdl.ConnectTdbctlNode(ip, port)
	if err != nil {
		return gerrors.Newf(gerrors.Failure, "failed to connect to tdbctl master node(%s:%d), errmsg: %s",
			ip, port, err.Error())
	}

	defer masterDB.Close()

	if err = hdl.setTcAdmin(masterDB, 0); err != nil {
		return err
	}

	if err = hdl.StopSlave(masterDB); err != nil {
		return err
	}

	return hdl.ResetSlave(masterDB)
}

// changeTdbCtlMasterForAllTdbCtlSlave changes tdbctl master for all tdbctl slave
func (hdl *TenDBClusterHandler) changeTdbCtlMasterForAllTdbCtlSlave(ctlSlaveList []config.TenDBClusterNodeInfo, targetIp string, targetPort int) error {
	var slaveList []config.InstanceAddress
	for _, slave := range ctlSlaveList {
		slaveList = append(slaveList, config.InstanceAddress{
			Host: slave.Host,
			Port: slave.Port,
		})
	}

	changeMasterSQL := fmt.Sprintf("CHANGE MASTER TO "+
		"MASTER_HOST = '%s', "+
		"MASTER_PORT = %d, "+
		"MASTER_USER = '%s', "+
		"MASTER_PASSWORD = '%s', "+
		"MASTER_AUTO_POSITION = 1",
		targetIp, targetPort,
		config.ClusterConfig.AuthInfo.ReplUser, config.ClusterConfig.AuthInfo.ReplPassword)

	for _, slave := range slaveList {
		if err := hdl.changeMasterForTdbctlSlave(slave.Host, slave.Port, changeMasterSQL); err != nil {
			return err
		}
	}

	// wait for slave to start
	time.Sleep(3 * time.Second)

	return hdl.checkSlaveStatus(slaveList, targetIp, targetPort)
}

// changeMasterForTdbctlSlave changes master for tdbctl slave
func (hdl *TenDBClusterHandler) changeMasterForTdbctlSlave(slaveIp string, slavePort int, changeMasterSQL string) error {
	slaveDB, err := hdl.ConnectTdbctlNode(slaveIp, slavePort)
	if err != nil {
		return gerrors.Newf(gerrors.Failure, "failed to connect to slave node(%s:%d), errmsg: %s",
			slaveIp, slavePort, err.Error())
	}

	defer slaveDB.Close()

	if err = hdl.setTcAdmin(slaveDB, 0); err != nil {
		return err
	}

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

// disablePrimaryForAllTdbCtlSlave disables primary for all tdbctl slave
func (hdl *TenDBClusterHandler) disablePrimaryForAllTdbCtlSlave(ctlSlaveList []config.TenDBClusterNodeInfo) error {
	for _, slave := range ctlSlaveList {
		slaveDB, err := hdl.ConnectTdbctlNode(slave.Host, slave.Port)
		if err != nil {
			return gerrors.Newf(gerrors.Failure, "failed to connect to tdbctl slave node(%s:%d), errmsg: %s",
				slave.Host, slave.Port, err.Error())
		}

		defer slaveDB.Close()

		if err = hdl.setTcAdmin(slaveDB, 1); err != nil {
			return err
		}

		slaveIp := slaveDB.Host()
		slavePort := slaveDB.Port()
		disablePrimarySQL := "tdbctl disable primary"

		if err = slaveDB.DB().Exec(disablePrimarySQL).Error; err != nil {
			return gerrors.Newf(gerrors.Failure,
				"failed to execute tdbctl disable primary on node(%s:%d), errmsg: %s", slaveIp, slavePort, err.Error())
		}
	}

	return nil
}

// enablePrimaryForTdbCtlMaster enables primary for tdbctl master
func (hdl *TenDBClusterHandler) enablePrimaryForTdbCtlMaster(ctlMaster config.TenDBClusterNodeInfo) error {
	masterDB, err := hdl.ConnectTdbctlNode(ctlMaster.Host, ctlMaster.Port)
	if err != nil {
		return gerrors.Newf(gerrors.Failure, "failed to connect to tdbctl master node(%s:%d), errmsg: %s",
			ctlMaster.Host, ctlMaster.Port, err.Error())
	}

	defer masterDB.Close()

	if err = hdl.setTcAdmin(masterDB, 1); err != nil {
		return err
	}

	slaveIp := masterDB.Host()
	slavePort := masterDB.Port()
	enablePrimarySQL := "tdbctl enable primary"

	if err = masterDB.DB().Exec(enablePrimarySQL).Error; err != nil {
		return gerrors.Newf(gerrors.Failure,
			"failed to execute tdbctl enable primary on node(%s:%d), errmsg: %s", slaveIp, slavePort, err.Error())
	}

	return nil
}

// resetMysqlServersTableForTdbCtlMaster resets mysql.servers table for tdbctl master
func (hdl *TenDBClusterHandler) resetMysqlServersTableForTdbCtlMaster(cluster *config.TenDBCluster) error {
	masterDB, err := hdl.ConnectTdbctlNode(cluster.CtlMaster.Host, cluster.CtlMaster.Port)
	if err != nil {
		return gerrors.Newf(gerrors.Failure, "failed to connect to tdbctl master node(%s:%d), errmsg: %s",
			cluster.CtlMaster.Host, cluster.CtlMaster.Port, err.Error())
	}
	defer masterDB.Close()

	if err = hdl.setTcAdmin(masterDB, 0); err != nil {
		return err
	}

	if err = hdl.deleteMysqlServersTable(masterDB); err != nil {
		return err
	}

	if err = hdl.insertMysqlServersTable(cluster, masterDB); err != nil {
		return err
	}

	if err = hdl.setTcAdmin(masterDB, 1); err != nil {
		return err
	}

	return hdl.flushRouting(masterDB)
}

// deleteMysqlServersTable deletes mysql.servers table
func (hdl *TenDBClusterHandler) deleteMysqlServersTable(masterDB *hamysql.GormDB) error {
	if masterDB == nil {
		return gerrors.New(gerrors.InvalidParameter, "deleteMysqlServersTable got nil masterDB")
	}
	masterIp := masterDB.Host()
	masterPort := masterDB.Port()
	deleteServersSQL := "DELETE FROM mysql.servers"

	if err := masterDB.DB().Exec(deleteServersSQL).Error; err != nil {
		return gerrors.Newf(gerrors.Failure,
			"failed to execute delete from mysql.servers on node(%s:%d), errmsg: %s", masterIp, masterPort, err.Error())
	}

	return nil
}

// insertMysqlServersTable inserts mysql.servers table
func (hdl *TenDBClusterHandler) insertMysqlServersTable(cluster *config.TenDBCluster, masterDB *hamysql.GormDB) error {
	if masterDB == nil {
		return gerrors.New(gerrors.InvalidParameter, "insertMysqlServersTable got nil masterDB")
	}
	masterIp := masterDB.Host()
	masterPort := masterDB.Port()

	insertSQL := `
		INSERT INTO mysql.servers (
			Server_name, Host, Username, Password, Port, Wrapper
		) VALUES
	`

	records := hdl.collectServerRecords(cluster)
	placeholders := make([]string, len(records))
	args := make([]interface{}, 0, len(records)*6)

	for i, record := range records {
		placeholders[i] = "(?, ?, ?, ?, ?, ?)"
		args = append(args, record.ServerName, record.Host, record.User, record.Password, record.Port, record.Wrapper)
	}

	insertSQL += strings.Join(placeholders, ", ")

	if err := masterDB.DB().Exec(insertSQL, args...).Error; err != nil {
		return gerrors.Newf(gerrors.Failure,
			"failed to execute insert into mysql.servers on node(%s:%d), errmsg: %s", masterIp, masterPort, err.Error())
	}

	return nil
}

// collectServerRecords collects server records
func (hdl *TenDBClusterHandler) collectServerRecords(cluster *config.TenDBCluster) []config.TenDBClusterNodeInfo {
	records := make([]config.TenDBClusterNodeInfo, 0)

	// CtlMaster
	records = append(records, config.TenDBClusterNodeInfo{
		Host:       cluster.CtlMaster.Host,
		Port:       cluster.CtlMaster.Port,
		ServerName: cluster.CtlMaster.ServerName,
		User:       cluster.CtlMaster.User,
		Password:   cluster.CtlMaster.Password,
		Wrapper:    "TDBCTL",
	})

	// CtlSlave
	for _, ctl := range cluster.CtlSlave {
		records = append(records, config.TenDBClusterNodeInfo{
			Host:       ctl.Host,
			Port:       ctl.Port,
			ServerName: ctl.ServerName,
			User:       ctl.User,
			Password:   ctl.Password,
			Wrapper:    "TDBCTL",
		})
	}

	// Spider
	for _, spider := range cluster.Spider {
		records = append(records, config.TenDBClusterNodeInfo{
			Host:       spider.Host,
			Port:       spider.Port,
			ServerName: spider.ServerName,
			User:       spider.User,
			Password:   spider.Password,
			Wrapper:    "SPIDER",
		})
	}

	// SpiderSlave
	for _, spider := range cluster.SpiderSlave {
		records = append(records, config.TenDBClusterNodeInfo{
			Host:       spider.Host,
			Port:       spider.Port,
			ServerName: spider.ServerName,
			User:       spider.User,
			Password:   spider.Password,
			Wrapper:    "SPIDER_SLAVE",
		})
	}

	// RemoteMaster
	for _, remote := range cluster.RemoteMaster {
		records = append(records, config.TenDBClusterNodeInfo{
			Host:       remote.Host,
			Port:       remote.Port,
			ServerName: remote.ServerName,
			User:       remote.User,
			Password:   remote.Password,
			Wrapper:    "mysql",
		})
	}

	// RemoteSlave
	for _, remote := range cluster.RemoteSlave {
		records = append(records, config.TenDBClusterNodeInfo{
			Host:       remote.Host,
			Port:       remote.Port,
			ServerName: remote.ServerName,
			User:       remote.User,
			Password:   remote.Password,
			Wrapper:    "mysql_slave",
		})
	}

	return records
}

// flushRouting flush routing
func (hdl *TenDBClusterHandler) flushRouting(masterDB *hamysql.GormDB) error {
	if masterDB == nil {
		return gerrors.New(gerrors.InvalidParameter, "flushRouting got nil masterDB")
	}

	flushRoutingSQL := "tdbctl flush routing"
	if err := masterDB.DB().Exec(flushRoutingSQL).Error; err != nil {
		return gerrors.Newf(gerrors.Failure,
			"failed to flush routing on node(%s:%d), errmsg: %s",
			masterDB.Host(), masterDB.Port(), err.Error())
	}

	return nil
}

func (hdl *TenDBClusterHandler) addAllSpidersToDomain(cluster *config.TenDBCluster) error {
	if cluster.Domain != "" && len(cluster.Spider) > 0 {
		if err := hdl.addSpiderNodesToDomain(cluster.Spider, cluster.Domain, cluster.BkBizId); err != nil {
			return gerrors.Newf(gerrors.Failure, "failed to add spider nodes to domain(%s), errmsg: %s",
				cluster.Domain, err.Error())
		}
	}

	if cluster.DomainSlave != "" && len(cluster.SpiderSlave) > 0 {
		if err := hdl.addSpiderNodesToDomain(cluster.SpiderSlave, cluster.DomainSlave, cluster.BkBizId); err != nil {
			return gerrors.Newf(gerrors.Failure, "failed to add spider slave nodes to domainSlave(%s), errmsg: %s",
				cluster.DomainSlave, err.Error())
		}
	}

	return nil
}

// addSpiderNodesToDomain adds spider nodes to the specified domain
func (hdl *TenDBClusterHandler) addSpiderNodesToDomain(spiderList []config.TenDBClusterNodeInfo, domain string, bkBizId int) error {
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

	for _, spider := range spiderList {
		spiderHost := spider.Host
		spiderPort := spider.Port
		if isInDomain(spiderHost, spiderPort) {
			continue
		}
		if err := hdl.dbmClient.AddInstanceToDomain(spiderHost, spiderPort, domain, bkBizId); err != nil {
			return gerrors.Newf(gerrors.Failure, "failed to add instance(%s:%d) to domain %s, errmsg: %s",
				spiderHost, spiderPort, domain, err.Error())
		}
	}

	return nil
}

// resetSingleTendbCluster reset a single mysql cluster
// Step 1: update all instances status to unavailable（ctl, spider, remote）
// Step 2: stop slave for remote master
// step 3: change master for all remote slaves
// step 4: change remote role
// Step 5: stop slave for tdbctl master
// Step 6: change master for all tdbctl slaves
// Step 7: tdbctl slaves executes disable primary
// Step 8: tdbctl master executes enable primary
// Step 9: delete and insert a new mysql.servers, flush routing
// Step 10: update all instances status to running
// Step 11: add all spiders to the domain
func (hdl *TenDBClusterHandler) resetSingleTenDBCluster(cluster *config.TenDBCluster) error {
	hdl.printOneTenDBCluster(cluster)
	fmt.Printf("Resetting cluster %s...\n", cluster.Domain)
	instanceListForDbm := hdl.getInstanceListForDbmStatusUpdate(cluster)

	if err := hdl.dbmClient.UpdateAllInstancesStatus(instanceListForDbm, dbm.StatusUnavailable); err != nil {
		fmt.Printf("Failed at step 1 <update all instances status to unavailable>, errmsg: %s\n", err.Error())
		return err
	}
	fmt.Printf("Step 1 <update all instances status to unavailable> done\n")

	binLogList, err := hdl.stopSlaveForRemoteMasterAndGetBinlogList(cluster)
	if err != nil {
		return err
	}
	fmt.Printf("Step 2 <stop slave for remote master> done\n")

	if err := hdl.changeMasterForAllRemoteSlave(cluster.RemoteSlave, binLogList); err != nil {
		fmt.Printf("Failed at step 3 <change master for all remote slaves>, errmsg: %s\n", err.Error())
		return err
	}
	fmt.Printf("Step 3 <change master for all remote slaves> done\n")

	if err := hdl.correctRemoteDBRole(cluster); err != nil {
		fmt.Printf("Failed at step 4 <correct remoteDB role>, errmsg: %s\n", err.Error())
		return err
	}
	fmt.Printf("Step 4 <correct remoteDB role> done\n")

	if err = hdl.stopSlaveForTdbCtlMaster(cluster.CtlMaster.Host, cluster.CtlMaster.Port); err != nil {
		return err
	}
	fmt.Printf("Step 5 <stop slave for tdbctl master> done\n")

	if err := hdl.changeTdbCtlMasterForAllTdbCtlSlave(cluster.CtlSlave, cluster.CtlMaster.Host,
		cluster.CtlMaster.Port); err != nil {
		fmt.Printf("Failed at step 6 <change tdbctl master for all slaves>, errmsg: %s\n", err.Error())
		return err
	}
	fmt.Printf("Step 6 <change tdbctl master for all slaves> done\n")

	if err := hdl.disablePrimaryForAllTdbCtlSlave(cluster.CtlSlave); err != nil {
		fmt.Printf("Failed at step 7 <disable primary for all tdbctl slaves>, errmsg: %s\n", err.Error())
		return err
	}
	fmt.Printf("Step 7 <disable primary for all tdbctl slaves> done\n")

	if err := hdl.enablePrimaryForTdbCtlMaster(cluster.CtlMaster); err != nil {
		fmt.Printf("Failed at step 8 <enable primary for tdbctl master>, errmsg: %s\n", err.Error())
		return err
	}
	fmt.Printf("Step 8 <enable primary for tdbctl master> done\n")

	if err := hdl.resetMysqlServersTableForTdbCtlMaster(cluster); err != nil {
		fmt.Printf("Failed at step 9 <reset mysql.servers table for tdbctl master>, errmsg: %s\n", err.Error())
		return err
	}
	fmt.Printf("Step 9 <reset mysql.servers table for tdbctl master> done\n")

	if err := hdl.dbmClient.UpdateAllInstancesStatus(instanceListForDbm, dbm.StatusRunning); err != nil {
		fmt.Printf("Failed at step 10 <update all instances status to running>, errmsg: %s\n", err.Error())
		return err
	}
	fmt.Printf("Step 10 <update all instances status to running> done\n")

	if err := hdl.addAllSpidersToDomain(cluster); err != nil {
		fmt.Printf("Failed at step 11 <add all spiders to the domain>, errmsg: %s\n", err.Error())
		return err
	}
	fmt.Printf("Step 11 <add all spiders to the domain> done\n")

	return nil
}

// ResetAllTenDBClusters resets all TenDBClusters
func (hdl *TenDBClusterHandler) ResetAllTenDBClusters() error {
	if config.ClusterConfig == nil {
		return gerrors.Newf(gerrors.Failure, "config is not loaded")
	}

	if hdl.dbmClient == nil {
		return gerrors.Newf(gerrors.Failure, "dbm client is nil")
	}

	if len(config.ClusterConfig.TenDBClusters) <= 0 {
		fmt.Println("No TenDBClusters to reset")
		return nil
	}

	failCount := 0
	fmt.Printf("=== Processing TenDBClusters ===\n\n")
	for _, cluster := range config.ClusterConfig.TenDBClusters {
		if err := hdl.resetSingleTenDBCluster(&cluster); err != nil {
			failCount++
			fmt.Printf("Failed to reset cluster %s, errmsg: %s\n\n", cluster.Domain, err.Error())
			continue
		}
		fmt.Printf("Successfully reset cluster %s\n\n", cluster.Domain)
	}
	fmt.Printf("\n=== Resetting TenDBClusters Done (total: %d, failed: %d, success: %d)===\n",
		len(config.ClusterConfig.TenDBClusters), failCount, len(config.ClusterConfig.TenDBClusters)-failCount)

	return nil
}

// ShowAllTenDBClustersDomain shows domain binding information for all TenDB clusters
func (hdl *TenDBClusterHandler) ShowAllTenDBClustersDomain() error {
	if config.ClusterConfig == nil {
		return printErrorResponse("config is not loaded")
	}

	if hdl.dbmClient == nil {
		return printErrorResponse("dbm client is nil")
	}

	clusterDomainInfoList := make([]ClusterDomainInfo, 0)

	for _, cluster := range config.ClusterConfig.TenDBClusters {
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

// ShowAllTenDBClustersNodes shows all nodes status and role for all TenDB clusters
func (hdl *TenDBClusterHandler) ShowAllTenDBClustersNodes() error {
	if config.ClusterConfig == nil {
		return printErrorResponse("config is not loaded")
	}

	if hdl.dbmClient == nil {
		return printErrorResponse("dbm client is nil")
	}

	clusterNodeInfoList := make([]ClusterNodeInfo, 0)

	for _, cluster := range config.ClusterConfig.TenDBClusters {
		serverNameMap := make(map[string]string)

		for _, spider := range cluster.Spider {
			key := fmt.Sprintf("%s:%d", spider.Host, spider.Port)
			serverNameMap[key] = spider.ServerName
		}
		for _, spider := range cluster.SpiderSlave {
			key := fmt.Sprintf("%s:%d", spider.Host, spider.Port)
			serverNameMap[key] = spider.ServerName
		}
		for _, remote := range cluster.RemoteMaster {
			key := fmt.Sprintf("%s:%d", remote.Host, remote.Port)
			serverNameMap[key] = remote.ServerName
		}
		for _, remote := range cluster.RemoteSlave {
			key := fmt.Sprintf("%s:%d", remote.Host, remote.Port)
			serverNameMap[key] = remote.ServerName
		}

		ipList := make([]string, 0)
		for _, spider := range cluster.Spider {
			ipList = append(ipList, spider.Host)
		}
		for _, spider := range cluster.SpiderSlave {
			ipList = append(ipList, spider.Host)
		}

		for _, remote := range cluster.RemoteMaster {
			ipList = append(ipList, remote.Host)
		}
		for _, remote := range cluster.RemoteSlave {
			ipList = append(ipList, remote.Host)
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
			key := fmt.Sprintf("%s:%d", meta.IP, meta.Port)
			clusterNodeInfo.Nodes = append(clusterNodeInfo.Nodes, NodeInfo{
				ServerName: serverNameMap[key],
				IP:         meta.IP,
				Port:       meta.Port,
				Status:     meta.Status,
				Role:       meta.GetTenDBClusterRole(),
			})
		}

		sort.Slice(clusterNodeInfo.Nodes, func(i, j int) bool {
			return clusterNodeInfo.Nodes[i].ServerName < clusterNodeInfo.Nodes[j].ServerName
		})

		clusterNodeInfoList = append(clusterNodeInfoList, clusterNodeInfo)
	}

	return printJSON(clusterNodeInfoList)
}

// ShowAllTenDBClustersReplication shows replication status for all TenDB clusters
// Only checks Remote nodes and tdbctl nodes (Spider nodes are stateless proxies without replication)
func (hdl *TenDBClusterHandler) ShowAllTenDBClustersReplication() error {
	if config.ClusterConfig == nil {
		return printErrorResponse("config is not loaded")
	}

	clusterReplList := make([]ClusterReplicationInfo, 0)
	user := config.ClusterConfig.AuthInfo.User
	password := config.ClusterConfig.AuthInfo.Password

	for _, cluster := range config.ClusterConfig.TenDBClusters {
		clusterRepl := ClusterReplicationInfo{
			Cluster:      cluster.Domain,
			Replications: make([]ReplicationInfo, 0),
		}

		type nodeInfo struct {
			host       string
			port       int
			serverName string
		}
		nodes := make([]nodeInfo, 0)

		for _, remote := range cluster.RemoteMaster {
			nodes = append(nodes, nodeInfo{remote.Host, remote.Port, remote.ServerName})
		}
		for _, remote := range cluster.RemoteSlave {
			nodes = append(nodes, nodeInfo{remote.Host, remote.Port, remote.ServerName})
		}
		nodes = append(nodes, nodeInfo{cluster.CtlMaster.Host, cluster.CtlMaster.Port, cluster.CtlMaster.ServerName})
		for _, ctl := range cluster.CtlSlave {
			nodes = append(nodes, nodeInfo{ctl.Host, ctl.Port, ctl.ServerName})
		}

		type replResult struct {
			index    int
			replInfo *ReplicationInfo
			err      error
		}
		resultCh := make(chan replResult, len(nodes))

		for i, node := range nodes {
			go func(idx int, n nodeInfo) {
				replInfo, err := hdl.getRemoteNodeReplicationInfo(n.host, n.port, n.serverName, user, password)
				resultCh <- replResult{index: idx, replInfo: replInfo, err: err}
			}(i, node)
		}

		results := make([]*ReplicationInfo, len(nodes))
		for range nodes {
			result := <-resultCh
			if result.err != nil {
				return printErrorResponse(result.err.Error())
			}
			results[result.index] = result.replInfo
		}

		for _, replInfo := range results {
			clusterRepl.Replications = append(clusterRepl.Replications, *replInfo)
		}

		sort.Slice(clusterRepl.Replications, func(i, j int) bool {
			return clusterRepl.Replications[i].ServerName < clusterRepl.Replications[j].ServerName
		})

		clusterReplList = append(clusterReplList, clusterRepl)
	}

	return printJSON(clusterReplList)
}

// getRemoteNodeReplicationInfo gets replication info from a node
func (hdl *TenDBClusterHandler) getRemoteNodeReplicationInfo(host string, port int, serverName string, user, password string) (*ReplicationInfo, error) {
	db, err := hamysql.NewGormDB(
		hamysql.OptionProto(MySQLProtocol),
		hamysql.OptionIP(host),
		hamysql.OptionPort(port),
		hamysql.OptionUser(user),
		hamysql.OptionPassword(password),
	)
	if err != nil {
		return nil, gerrors.Newf(gerrors.Failure, "failed to connect to node, host: %s, port: %d, errmsg: %s",
			host, port, err.Error())
	}
	defer db.Close()

	slaveStatus, err := hdl.ShowSlaveStatus(db)
	if err != nil {
		return nil, gerrors.Newf(gerrors.Failure, "failed to get slave status of node, host: %s, port: %d, errmsg: %s",
			host, port, err.Error())
	}

	return &ReplicationInfo{
		IP:              host,
		Port:            port,
		ServerName:      serverName,
		MasterIP:        slaveStatus.MasterHost,
		MasterPort:      slaveStatus.MasterPort,
		SlaveIORunning:  slaveStatus.SlaveIORunning,
		SlaveSQLRunning: slaveStatus.SlaveSQLRunning,
	}, nil
}

// connectToAvailableTdbctl connects to an available tdbctl node by querying running spiders from API
func (hdl *TenDBClusterHandler) connectToAvailableTdbctl(cluster *config.TenDBCluster) (*hamysql.GormDB, error) {
	instInfoList, err := hdl.dbmClient.GetAllInstancesOfDomain(cluster.Domain)
	if err != nil {
		return nil, gerrors.Newf(gerrors.Failure, "failed to get instances of domain(%s), errmsg: %s",
			cluster.Domain, err.Error())
	}

	spiderIPs := make([]string, 0, len(instInfoList))
	for _, inst := range instInfoList {
		spiderIPs = append(spiderIPs, inst.Ip)
	}

	metadataList, err := hdl.dbmClient.QueryMetadataFromDbm(0, spiderIPs)
	if err != nil {
		return nil, gerrors.Newf(gerrors.Failure, "failed to query metadata for spiders, cluster: %s, errmsg: %s",
			cluster.Domain, err.Error())
	}

	var errs []string
	for _, meta := range metadataList {
		if meta.Status != string(dbm.StatusRunning) {
			continue
		}
		db, connErr := hdl.ConnectTdbctlNode(meta.IP, meta.AdminPort)
		if connErr == nil {
			return db, nil
		}
		errs = append(errs, fmt.Sprintf("%s:%d - %s", meta.IP, meta.AdminPort, connErr.Error()))
	}

	if len(errs) > 0 {
		return nil, gerrors.Newf(gerrors.Failure, "failed to connect to any tdbctl node for cluster(%s), errors: [%s]",
			cluster.Domain, strings.Join(errs, "; "))
	}
	return nil, gerrors.Newf(gerrors.Failure, "no available tdbctl node found for cluster(%s)", cluster.Domain)
}

// connectToPrimaryTdbctl connects to the primary tdbctl node of a cluster
func (hdl *TenDBClusterHandler) connectToPrimaryTdbctl(cluster *config.TenDBCluster) (*hamysql.GormDB, error) {
	tdbctlDB, err := hdl.connectToAvailableTdbctl(cluster)
	if err != nil {
		return nil, err
	}
	defer tdbctlDB.Close()

	if err = hdl.setTcAdmin(tdbctlDB, 1); err != nil {
		return nil, err
	}

	var primaryInfo TdbctlPrimaryInfo
	if err = tdbctlDB.DB().Raw("tdbctl get primary").Scan(&primaryInfo).Error; err != nil {
		return nil, gerrors.Newf(gerrors.Failure, "failed to get primary tdbctl for cluster(%s), errmsg: %s",
			cluster.Domain, err.Error())
	}

	primaryDB, err := hdl.ConnectTdbctlNode(primaryInfo.Host, primaryInfo.Port)
	if err != nil {
		return nil, gerrors.Newf(gerrors.Failure, "failed to connect to primary tdbctl(%s:%d), errmsg: %s",
			primaryInfo.Host, primaryInfo.Port, err.Error())
	}

	return primaryDB, nil
}

func (hdl *TenDBClusterHandler) checkRoutingConsistencyOnPrimary(primaryDB *hamysql.GormDB) bool {
	if err := primaryDB.DB().Exec("tdbctl check routing").Error; err != nil {
		return false
	}
	return true
}

// getClusterRoutingInfo gets routing info for a TenDB cluster
func (hdl *TenDBClusterHandler) getClusterRoutingInfo(cluster *config.TenDBCluster) (*ClusterRoutingInfo, error) {
	primaryDB, err := hdl.connectToPrimaryTdbctl(cluster)
	if err != nil {
		return nil, err
	}
	defer primaryDB.Close()

	if err = hdl.setTcAdmin(primaryDB, 0); err != nil {
		return nil, err
	}

	var routingEntries []RoutingEntry
	if err = primaryDB.DB().Raw("SELECT Server_name, Host, Port, Username, Wrapper FROM mysql.servers ORDER BY Server_name").Scan(&routingEntries).Error; err != nil {
		return nil, gerrors.Newf(gerrors.Failure, "failed to query mysql.servers on primary tdbctl, errmsg: %s", err.Error())
	}

	if err = hdl.setTcAdmin(primaryDB, 1); err != nil {
		return nil, err
	}

	checkResult := "ok"
	if !hdl.checkRoutingConsistencyOnPrimary(primaryDB) {
		checkResult = "failed"
	}

	return &ClusterRoutingInfo{
		Cluster:     cluster.Domain,
		Routing:     routingEntries,
		CheckResult: checkResult,
	}, nil
}

// ShowAllTenDBClustersRouting shows routing table (mysql.servers) for all TenDB clusters
func (hdl *TenDBClusterHandler) ShowAllTenDBClustersRouting() error {
	if config.ClusterConfig == nil {
		return printErrorResponse("config is not loaded")
	}

	clusterRoutingList := make([]ClusterRoutingInfo, 0)

	for _, cluster := range config.ClusterConfig.TenDBClusters {
		routingInfo, err := hdl.getClusterRoutingInfo(&cluster)
		if err != nil {
			return printErrorResponse(err.Error())
		}
		clusterRoutingList = append(clusterRoutingList, *routingInfo)
	}

	return printJSON(clusterRoutingList)
}
