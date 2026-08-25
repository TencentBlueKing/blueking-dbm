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
	"context"
	"fmt"
	"sort"
	"strings"
	"time"

	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
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

// MasterStatusInfo represents MySQL master status information.
type MasterStatusInfo = hamysql.MasterStatusInfo

// SlaveStatusInfo represents MySQL slave status information.
type SlaveStatusInfo = hamysql.ReplicationStatus

// MysqlBaseHandler is a base handler for mysql
type MysqlBaseHandler struct {
	dbmClient *dbm.Client
}

// replStatements resolves the replication statements accepted by the target db.
func (hdl *MysqlBaseHandler) replStatements(db *hamysql.GormDB) (*hamysql.ReplStatements, error) {
	stmts, err := db.ReplStatements(context.Background())
	if err != nil {
		return nil, gerrors.Newf(gerrors.Failure,
			"failed to detect the server version on node(%s:%d), errmsg: %s", db.Host(), db.Port(), err.Error())
	}
	return stmts, nil
}

// StopSlave stops slave replication
func (hdl *MysqlBaseHandler) StopSlave(slaveDB *hamysql.GormDB) error {
	if slaveDB == nil {
		return gerrors.New(gerrors.InvalidParameter, "ResetSlave got nil slaveDB")
	}
	slaveIp := slaveDB.Host()
	slavePort := slaveDB.Port()

	stmts, err := hdl.replStatements(slaveDB)
	if err != nil {
		return err
	}

	if err := slaveDB.DB().Exec(stmts.StopSlave).Error; err != nil {
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

	stmts, err := hdl.replStatements(slaveDB)
	if err != nil {
		return err
	}

	if err := slaveDB.DB().Exec(stmts.StartSlave).Error; err != nil {
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

	stmts, err := hdl.replStatements(db)
	if err != nil {
		return nil, err
	}

	masterStatus := &MasterStatusInfo{}
	if err := db.DB().Raw(stmts.ShowMasterStatus).Scan(masterStatus).Error; err != nil {
		return nil, gerrors.Newf(gerrors.Failure,
			"failed to get master status on node(%s:%d), errmsg: %s", slaveIp, slavePort, err.Error())
	}
	if masterStatus.File == "" {
		return nil, gerrors.Newf(gerrors.Failure,
			"empty binlog file in the result of '%s' on node(%s:%d)", stmts.ShowMasterStatus, slaveIp, slavePort)
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

	stmts, err := hdl.replStatements(slaveDB)
	if err != nil {
		return nil, err
	}

	slaveStatus := &SlaveStatusInfo{}
	if err := slaveDB.DB().Raw(stmts.ShowSlaveStatus).Scan(slaveStatus).Error; err != nil {
		return nil, gerrors.Newf(gerrors.Failure,
			"failed to get slave status on node(%s:%d), errmsg: %s", slaveIp, slavePort, err.Error())
	}
	slaveStatus.Normalize()

	return slaveStatus, nil
}

// ResetSlave resets slave replication settings
func (hdl *MysqlBaseHandler) ResetSlave(slaveDB *hamysql.GormDB) error {
	if slaveDB == nil {
		return gerrors.New(gerrors.InvalidParameter, "ResetSlave got nil slaveDB")
	}
	slaveIp := slaveDB.Host()
	slavePort := slaveDB.Port()

	stmts, err := hdl.replStatements(slaveDB)
	if err != nil {
		return err
	}

	if err := slaveDB.DB().Exec(stmts.ResetSlaveAll).Error; err != nil {
		return gerrors.Newf(gerrors.Failure,
			"failed to reset slave on node(%s:%d), errmsg: %s", slaveIp, slavePort, err.Error())
	}

	return nil
}

// stopSlaveForMaster stops slave for master
func (hdl *MysqlBaseHandler) stopSlaveForMaster(ip string, port int) (string, uint64, error) {
	masterDB, err := newToolGormDB(
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

// changeMasterForAllSlave changes master for all slave; the statement is generated per
// target node since instances may run different server versions during a rolling upgrade.
func (hdl *MysqlBaseHandler) changeMasterForAllSlave(slaveList []config.InstanceAddress, targetIp string, targetPort int,
	binlogFile string, binlogPos uint64) error {
	src := hamysql.ReplSource{
		Host:         targetIp,
		Port:         targetPort,
		User:         config.ClusterConfig.AuthInfo.ReplUser,
		Password:     config.ClusterConfig.AuthInfo.ReplPassword,
		LogFile:      binlogFile,
		LogPos:       binlogPos,
		AutoPosition: hamysql.AutoPositionOmit,
	}

	for _, slave := range slaveList {
		if err := hdl.changeMasterForSlave(slave.Host, slave.Port, src); err != nil {
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
		slaveDB, err := newToolGormDB(
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
func (hdl *MysqlBaseHandler) changeMasterForSlave(slaveIp string, slavePort int, src hamysql.ReplSource) error {
	slaveDB, err := newToolGormDB(
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

	if _, err = slaveDB.ChangeReplicationTo(context.Background(), src); err != nil {
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
	targetRole haprobe.DbmMetadataInstanceRole) (string, int, error) {
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

	if masterRole != haprobe.MySQLStorageMaster {
		curMasterHost, curMasterPort, err := hdl.findSlaveOfTargetRole(cluster.Slave, haprobe.MySQLStorageMaster)
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

		if slaveRole != haprobe.MySQLStorageSlave {
			return gerrors.Newf(gerrors.Failure, "slave(%s:%d) role is not %s",
				slave.Host, slave.Port, haprobe.MySQLStorageSlave)
		}
	}

	return nil
}

func clbInstanceToIPPort(host string, port int) string {
	return fmt.Sprintf("%s:%d", host, port)
}

func clbInstancesToIPPorts(instances []config.InstanceAddress) []string {
	ips := make([]string, 0, len(instances))
	for _, inst := range instances {
		ips = append(ips, clbInstanceToIPPort(inst.Host, inst.Port))
	}
	return ips
}

func diffClbIPPortSets(desired, current []string) (missing, extra []string) {
	desiredSet := make(map[string]struct{}, len(desired))
	currentSet := make(map[string]struct{}, len(current))

	for _, ip := range desired {
		desiredSet[ip] = struct{}{}
	}
	for _, ip := range current {
		currentSet[ip] = struct{}{}
	}

	for ip := range desiredSet {
		if _, ok := currentSet[ip]; !ok {
			missing = append(missing, ip)
		}
	}
	for ip := range currentSet {
		if _, ok := desiredSet[ip]; !ok {
			extra = append(extra, ip)
		}
	}

	sort.Strings(missing)
	sort.Strings(extra)
	return missing, extra
}

func validateClbConfig(clb *config.ClbConfig) error {
	if clb.Region == "" {
		return gerrors.New(gerrors.InvalidParameter, "clb.region is empty, please configure it in cluster.yaml")
	}
	if clb.ListenerID == "" {
		return gerrors.New(gerrors.InvalidParameter, "clb.listenerId is empty, please configure it in cluster.yaml")
	}
	if clb.LoadBalancerID == "" {
		return gerrors.New(gerrors.InvalidParameter,
			"clb.loadbalancerId is empty, please configure it in cluster.yaml")
	}
	return nil
}

func (hdl *MysqlBaseHandler) syncClbBinding(clb *config.ClbConfig) error {
	if err := validateClbConfig(clb); err != nil {
		return err
	}

	currentIPs, err := hdl.dbmClient.GetClbTargetPrivateIps(clb)
	if err != nil {
		return gerrors.Newf(gerrors.Failure,
			"failed to get clb target private ips (region=%s, listenerId=%s), errmsg: %s",
			clb.Region, clb.ListenerID, err.Error())
	}

	desiredIPs := clbInstancesToIPPorts(clb.Instances)
	missing, extra := diffClbIPPortSets(desiredIPs, currentIPs)

	if err := hdl.dbmClient.RegisterClbPartTarget(clb, missing); err != nil {
		return gerrors.Newf(gerrors.Failure,
			"failed to register clb targets (region=%s, listenerId=%s), errmsg: %s",
			clb.Region, clb.ListenerID, err.Error())
	}

	if err := hdl.dbmClient.DeregisterClbPartTarget(clb, extra); err != nil {
		return gerrors.Newf(gerrors.Failure,
			"failed to deregister clb targets (region=%s, listenerId=%s), errmsg: %s",
			clb.Region, clb.ListenerID, err.Error())
	}

	return nil
}

func (hdl *MysqlBaseHandler) resetAllClbBindings(clbList []config.ClbConfig) error {
	for i := range clbList {
		if err := hdl.syncClbBinding(&clbList[i]); err != nil {
			return err
		}
	}
	return nil
}

func (hdl *MysqlBaseHandler) queryClbBinding(clb *config.ClbConfig) (ClbBindingInfo, error) {
	if err := validateClbConfig(clb); err != nil {
		return ClbBindingInfo{}, err
	}

	instanceList, err := hdl.dbmClient.GetClbTargetPrivateIps(clb)
	if err != nil {
		return ClbBindingInfo{}, err
	}
	if instanceList == nil {
		instanceList = make([]string, 0)
	}

	return ClbBindingInfo{
		ClbID:        clb.LoadBalancerID,
		ListenerID:   clb.ListenerID,
		Region:       clb.Region,
		InstanceList: instanceList,
	}, nil
}

func (hdl *MysqlBaseHandler) buildClusterClbInfo(domain string, clbConfigs []config.ClbConfig) (ClusterClbInfo, error) {
	clbList := make([]ClbBindingInfo, 0, len(clbConfigs))
	for i := range clbConfigs {
		binding, err := hdl.queryClbBinding(&clbConfigs[i])
		if err != nil {
			return ClusterClbInfo{}, gerrors.Newf(gerrors.Failure,
				"failed to get clb info for cluster(%s), errmsg: %s", domain, err.Error())
		}
		clbList = append(clbList, binding)
	}

	return ClusterClbInfo{
		Cluster: domain,
		ClbList: clbList,
	}, nil
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
// Step 9: reset clb binding (optional; skip when clb is omitted or empty)
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

	if len(cluster.Clb) > 0 {
		if err := hdl.resetAllClbBindings(cluster.Clb); err != nil {
			fmt.Printf("Failed at step 9 <reset clb binding>, errmsg: %s\n", err.Error())
			return err
		}
		fmt.Printf("Step 9 <reset clb binding> done\n")
	}

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

// ShowAllMysqlClustersClb shows CLB binding information for all MySQL clusters
func (hdl *MysqlClusterHandler) ShowAllMysqlClustersClb() error {
	if config.ClusterConfig == nil {
		return printErrorResponse("config is not loaded")
	}

	if hdl.dbmClient == nil {
		return printErrorResponse("dbm client is nil")
	}

	clusterClbInfoList := make([]ClusterClbInfo, 0)

	for _, cluster := range config.ClusterConfig.MysqlClusters {
		if len(cluster.Clb) == 0 {
			continue
		}
		info, err := hdl.buildClusterClbInfo(cluster.Domain, cluster.Clb)
		if err != nil {
			return printErrorResponse(err.Error())
		}
		clusterClbInfoList = append(clusterClbInfoList, info)
	}

	return printJSON(clusterClbInfoList)
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
			// metadata is queried by host ip, so skip instances of other clusters co-located on the same host
			if meta.Cluster != cluster.Domain {
				continue
			}
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
	db, err := newToolGormDB(
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
