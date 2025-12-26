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
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"
	"dbm-services/common/dbha-v2/tools/internal/cluster/config"
	"dbm-services/common/dbha-v2/tools/internal/cluster/dbm"
	"fmt"
	"strings"
	"time"
)

// TenDBClusterHandler provides MySQL cluster management functions
type TenDBClusterHandler struct {
	dbmClient    *dbm.Client
	mysqlHandler *MysqlClusterHandler
}

// NewTenDBClusterHandler creates a new MysqlClusterHandler
func NewTenDBClusterHandler() *TenDBClusterHandler {
	return &TenDBClusterHandler{
		dbmClient:    &dbm.Client{},
		mysqlHandler: NewMysqlClusterHandler(),
	}
}

// printOneTenDBCluster prints TenDB cluster information
func (hdl *TenDBClusterHandler) printOneTenDBCluster(cluster *config.TenDBCluster) {
	fmt.Printf("Cluster Domain: %s\n", cluster.Domain)
	fmt.Printf("Spider: %v\n", cluster.Spider)
	fmt.Printf("Spider Slaves: %v\n", cluster.SpiderSlave)
	fmt.Printf("TdbCtl Master: %s:%d\n", cluster.CtlMaster.Host, cluster.CtlMaster.Port)
	fmt.Printf("TdbCtl Slaves: %v\n", cluster.CtlSlave)
	fmt.Printf("Remote Master: %v\n", cluster.RemoteMaster)
	fmt.Printf("Remote Slaves: %v\n", cluster.RemoteSlave)
}

// getTenDBInstanceList gets TenDB instance list
func (hdl *TenDBClusterHandler) getTenDBInstanceList(cluster *config.TenDBCluster) []config.InstanceAddress {
	instanceList := []config.InstanceAddress{
		{Host: cluster.CtlMaster.Host, Port: cluster.CtlMaster.Port},
	}
	for _, spider := range cluster.Spider {
		instanceList = append(instanceList, config.InstanceAddress{Host: spider.Host, Port: spider.Port})
	}
	for _, ctl := range cluster.CtlSlave {
		instanceList = append(instanceList, config.InstanceAddress{Host: ctl.Host, Port: ctl.Port})
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
		binlogFile, binlogPos, err := hdl.mysqlHandler.stopSlaveForMaster(remote.Host, remote.Port)
		if err != nil {
			return nil, err
		}
		binlogList = append(binlogList, config.BinlogInfo{

			TenDBInfo: config.TenDBInfo{
				Host:     remote.Host,
				Port:     remote.Port,
				Username: remote.Username,
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
	for _, binlog := range binlogList {
		for _, remote := range remoteSlave {
			if remote.MasterHost == binlog.Host && remote.MasterPort == binlog.Port {
				var slaveList []config.InstanceAddress
				slaveList = append(slaveList, config.InstanceAddress{
					Host: remote.Host,
					Port: remote.Port,
				})

				if err := hdl.mysqlHandler.changeMasterForAllSlave(slaveList, binlog.Host, binlog.Port, binlog.File,
					binlog.Position); err != nil {
					return err
				}
				break
			}
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

// stopSlaveForTdbCtlMaster stops slave for tdbctl master
func (hdl *TenDBClusterHandler) stopSlaveForTdbCtlMaster(ip string, port int) error {
	masterDB, err := hamysql.NewGormDB(
		hamysql.OptionProto(MySQLProtocol),
		hamysql.OptionIP(ip),
		hamysql.OptionPort(port),
		hamysql.OptionUser(config.ClusterConfig.AuthInfo.User),
		hamysql.OptionPassword(config.ClusterConfig.AuthInfo.Password),
	)
	if err != nil {
		return gerrors.Newf(gerrors.Failure, "failed to connect to master node(%s:%d), errmsg: %s",
			ip, port, err.Error())
	}

	defer func() {
		con, _ := masterDB.DB().DB()
		if con != nil {
			con.Close()
		}
	}()

	if err = hdl.mysqlHandler.setTcAdmin(masterDB, 0); err != nil {
		return err
	}

	if err = hdl.mysqlHandler.StopSlave(masterDB); err != nil {
		return err
	}

	return hdl.mysqlHandler.ResetSlave(masterDB)
}

// changeCtlMasterForAllCtlSlave changes ctl master for all ctl slave
func (hdl *TenDBClusterHandler) changeCtlMasterForAllCtlSlave(ctlSlaveList []config.TenDBInfo, targetIp string, targetPort int) error {
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
		if err := hdl.mysqlHandler.changeMasterForSlave(slave.Host, slave.Port, changeMasterSQL, true); err != nil {
			return err
		}
	}

	// wait for slave to start
	time.Sleep(3 * time.Second)

	return hdl.mysqlHandler.checkSlaveStatus(slaveList, targetIp, targetPort)
}

// disablePrimaryForAllCtlSlave disables primary for all ctl slave
func (hdl *TenDBClusterHandler) disablePrimaryForAllCtlSlave(ctlSlaveList []config.TenDBInfo) error {
	for _, slave := range ctlSlaveList {
		slaveDB, err := hamysql.NewGormDB(
			hamysql.OptionProto(MySQLProtocol),
			hamysql.OptionIP(slave.Host),
			hamysql.OptionPort(slave.Port),
			hamysql.OptionUser(config.ClusterConfig.AuthInfo.User),
			hamysql.OptionPassword(config.ClusterConfig.AuthInfo.Password),
		)
		if err != nil {
			return gerrors.Newf(gerrors.Failure, "failed to connect to ctl slave node(%s:%d), errmsg: %s",
				slave.Host, slave.Port, err.Error())
		}

		defer func() {
			con, _ := slaveDB.DB().DB()
			if con != nil {
				con.Close()
			}
		}()

		if err = hdl.mysqlHandler.setTcAdmin(slaveDB, 1); err != nil {
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

// enablePrimaryForCtlMaster enables primary for ctl master
func (hdl *TenDBClusterHandler) enablePrimaryForCtlMaster(ctlMaster config.TenDBInfo) error {
	masterDB, err := hamysql.NewGormDB(
		hamysql.OptionProto(MySQLProtocol),
		hamysql.OptionIP(ctlMaster.Host),
		hamysql.OptionPort(ctlMaster.Port),
		hamysql.OptionUser(config.ClusterConfig.AuthInfo.User),
		hamysql.OptionPassword(config.ClusterConfig.AuthInfo.Password),
	)
	if err != nil {
		return gerrors.Newf(gerrors.Failure, "failed to connect to ctl master node(%s:%d), errmsg: %s",
			ctlMaster.Host, ctlMaster.Port, err.Error())
	}

	defer func() {
		con, _ := masterDB.DB().DB()
		if con != nil {
			con.Close()
		}
	}()

	if err = hdl.mysqlHandler.setTcAdmin(masterDB, 1); err != nil {
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

// resetMysqlServersTableForCtlMaster resets mysql.servers table for ctl master
func (hdl *TenDBClusterHandler) resetMysqlServersTableForCtlMaster(cluster *config.TenDBCluster) error {
	masterDB, err := hamysql.NewGormDB(
		hamysql.OptionProto(MySQLProtocol),
		hamysql.OptionIP(cluster.CtlMaster.Host),
		hamysql.OptionPort(cluster.CtlMaster.Port),
		hamysql.OptionUser(config.ClusterConfig.AuthInfo.User),
		hamysql.OptionPassword(config.ClusterConfig.AuthInfo.Password),
	)

	if err != nil {
		return gerrors.Newf(gerrors.Failure, "failed to connect to ctl master node(%s:%d), errmsg: %s",
			cluster.CtlMaster.Host, cluster.CtlMaster.Port, err.Error())
	}

	if err = hdl.mysqlHandler.setTcAdmin(masterDB, 0); err != nil {
		return err
	}

	if err = hdl.deleteMysqlServersTable(masterDB); err != nil {
		return err
	}

	if err = hdl.insertMysqlServersTable(cluster, masterDB); err != nil {
		return err
	}

	if err = hdl.mysqlHandler.setTcAdmin(masterDB, 1); err != nil {
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
		args = append(args, record.ServerName, record.Host, record.Username, record.Password, record.Port, record.Wrapper)
	}

	insertSQL += strings.Join(placeholders, ", ")

	if err := masterDB.DB().Exec(insertSQL, args...).Error; err != nil {
		return gerrors.Newf(gerrors.Failure,
			"failed to execute insert into mysql.servers on node(%s:%d), errmsg: %s", masterIp, masterPort, err.Error())
	}

	return nil
}

// collectServerRecords collects server records
func (hdl *TenDBClusterHandler) collectServerRecords(cluster *config.TenDBCluster) []config.TenDBInfo {
	records := make([]config.TenDBInfo, 0)

	// CtlMaster
	records = append(records, config.TenDBInfo{
		Host:       cluster.CtlMaster.Host,
		Port:       cluster.CtlMaster.Port,
		ServerName: cluster.CtlMaster.ServerName,
		Username:   cluster.CtlMaster.Username,
		Password:   cluster.CtlMaster.Password,
		Wrapper:    cluster.CtlMaster.Wrapper,
	})

	// CtlSlave
	for _, ctl := range cluster.CtlSlave {
		records = append(records, config.TenDBInfo{
			Host:       ctl.Host,
			Port:       ctl.Port,
			ServerName: ctl.ServerName,
			Username:   ctl.Username,
			Password:   ctl.Password,
			Wrapper:    ctl.Wrapper,
		})
	}

	// Spider
	for _, spider := range cluster.Spider {
		records = append(records, config.TenDBInfo{
			Host:       spider.Host,
			Port:       spider.Port,
			ServerName: spider.ServerName,
			Username:   spider.Username,
			Password:   spider.Password,
			Wrapper:    spider.Wrapper,
		})
	}

	// SpiderSlave
	for _, spider := range cluster.SpiderSlave {
		records = append(records, config.TenDBInfo{
			Host:       spider.Host,
			Port:       spider.Port,
			ServerName: spider.ServerName,
			Username:   spider.Username,
			Password:   spider.Password,
			Wrapper:    spider.Wrapper,
		})
	}

	// RemoteMaster
	for _, remote := range cluster.RemoteMaster {
		records = append(records, config.TenDBInfo{
			Host:       remote.Host,
			Port:       remote.Port,
			ServerName: remote.ServerName,
			Username:   remote.Username,
			Password:   remote.Password,
			Wrapper:    remote.Wrapper,
		})
	}

	// RemoteSlave
	for _, remote := range cluster.RemoteSlave {
		records = append(records, config.TenDBInfo{
			Host:       remote.Host,
			Port:       remote.Port,
			ServerName: remote.ServerName,
			Username:   remote.Username,
			Password:   remote.Password,
			Wrapper:    remote.Wrapper,
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

func (hdl *TenDBClusterHandler) addAllSpidersToDomain(cluster *config.TenDBCluster, domain string, bkBizId int) error {
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

	spiderList := make([]config.TenDBInfo, 0, len(cluster.Spider)+len(cluster.SpiderSlave))
	spiderList = append(spiderList, cluster.Spider...)
	spiderList = append(spiderList, cluster.SpiderSlave...)

	for _, spider := range spiderList {
		spiderHost := spider.Host
		spiderPort := spider.Port
		if !isInDomain(spiderHost, spiderPort) {
			if err := hdl.dbmClient.AddInstanceToDomain(spiderHost, spiderPort, domain, bkBizId); err != nil {
				return gerrors.Newf(gerrors.Failure, "failed to add instance(%s:%d) to domain %s, errmsg: %s",
					spiderHost, spiderPort, domain, err.Error())
			}
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
	instanceList := hdl.getTenDBInstanceList(cluster)

	if err := hdl.dbmClient.UpdateAllInstancesStatus(instanceList, dbm.StatusUnavailable); err != nil {
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

	if err := hdl.changeCtlMasterForAllCtlSlave(cluster.CtlSlave, cluster.CtlMaster.Host,
		cluster.CtlMaster.Port); err != nil {
		fmt.Printf("Failed at step 6 <change tdbctl master for all slaves>, errmsg: %s\n", err.Error())
		return err
	}
	fmt.Printf("Step 6 <change tdbctl master for all slaves> done\n")

	if err := hdl.disablePrimaryForAllCtlSlave(cluster.CtlSlave); err != nil {
		fmt.Printf("Failed at step 7 <disable primary for all ctl slaves>, errmsg: %s\n", err.Error())
		return err
	}
	fmt.Printf("Step 7 <disable primary for all ctl slaves> done\n")

	if err := hdl.enablePrimaryForCtlMaster(cluster.CtlMaster); err != nil {
		fmt.Printf("Failed at step 8 <enable primary for ctl master>, errmsg: %s\n", err.Error())
		return err
	}
	fmt.Printf("Step 8 <enable primary for ctl master> done\n")

	if err := hdl.resetMysqlServersTableForCtlMaster(cluster); err != nil {
		fmt.Printf("Failed at step 9 <reset mysql.servers table for ctl master>, errmsg: %s\n", err.Error())
		return err
	}
	fmt.Printf("Step 9 <reset mysql.servers table for ctl master> done\n")

	if err := hdl.dbmClient.UpdateAllInstancesStatus(instanceList, dbm.StatusRunning); err != nil {
		fmt.Printf("Failed at step 10 <update all instances status to running>, errmsg: %s\n", err.Error())
		return err
	}
	fmt.Printf("Step 10 <update all instances status to running> done\n")

	if err := hdl.addAllSpidersToDomain(cluster, cluster.Domain, cluster.BkBizId); err != nil {
		fmt.Printf("Failed at step 11 <add all spiders to the domain>, errmsg: %s\n", err.Error())
		return err
	}
	fmt.Printf("Step 11 <add all spiders to the domain> done\n")

	return nil
}

// ResetAllTenDBClusters resets all TenDB clusters
func (hdl *TenDBClusterHandler) ResetAllTenDBClusters() error {
	if config.ClusterConfig == nil {
		return gerrors.Newf(gerrors.Failure, "config is not loaded")
	}

	if hdl.dbmClient == nil {
		return gerrors.Newf(gerrors.Failure, "dbm client is nil")
	}

	if len(config.ClusterConfig.TenDBClusters) <= 0 {
		fmt.Println("No TenDB clusters to reset")
		return nil
	}

	failCount := 0
	fmt.Printf("=== Processing TenDB Clusters ===\n\n")
	for _, cluster := range config.ClusterConfig.TenDBClusters {
		if err := hdl.resetSingleTenDBCluster(&cluster); err != nil {
			failCount++
			fmt.Printf("Failed to reset cluster %s, errmsg: %s\n\n", cluster.Domain, err.Error())
			continue
		}
		fmt.Printf("Successfully reset cluster %s\n\n", cluster.Domain)
	}
	fmt.Printf("\n=== Resetting TenDB Clusters Done (total: %d, failed: %d, success: %d)===\n",
		len(config.ClusterConfig.TenDBClusters), failCount, len(config.ClusterConfig.TenDBClusters)-failCount)

	return nil
}
