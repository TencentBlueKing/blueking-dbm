/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package spiderctl

import (
	"bufio"
	"context"
	"database/sql"
	"fmt"
	"os"
	"path"
	"regexp"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil"
)

// SpiderClusterBackendSwitchComp TODO
type SpiderClusterBackendSwitchComp struct {
	GeneralParam *components.GeneralParam   `json:"general"`
	Params       *SpiderRemotedbSwitchParam `json:"extend"`
	runtimeCtx
}
type runtimeCtx struct {
	CutOverCtx
	realSwitchSvrPairs []SvrPairs
	slavesConn         map[IPPORT]*native.DbWorker
	mastesConn         map[IPPORT]*native.DbWorker
}

// SpiderRemotedbSwitchParam TODO
type SpiderRemotedbSwitchParam struct {
	Host string `json:"host" validate:"required,ip"`
	Port int    `json:"port" validate:"required,lt=65536,gte=3306"`
	// 客户端连接检查
	ClientConnCheck bool `json:"client_conn_check"`
	// 数据校验结果检查
	VerifyChecksum bool         `json:"verify_checksum"`
	SwitchParis    []SwitchUnit `json:"switch_paris" validate:"required,gt=0,dive"`
	// force: 忽略部分切换前检查
	Force bool `json:"force"`
}

// CutOverCtx TODO
type CutOverCtx struct {
	tdbCtlConn  *native.TdbctlDbWork
	spidersConn map[string]*native.DbWorker
	// 加锁解锁只能在一个连接内
	spidersLockConn          map[string]*sql.Conn
	ipPortServersMap         map[IPPORT]native.Server
	svrNameServersMap        map[SVRNAME]native.Server
	newMasterPosInfos        map[string]native.MasterStatusResp
	sysUsers                 []string
	primaryShardrollbackSqls []string
	slaveShardrollbackSqls   []string
	fd                       *os.File //  持久化回滚sql
	primaryShardSwitchSqls   []string
	slaveShardSwitchSqls     []string
}

// SvrPairs TODO
type SvrPairs struct {
	MptName string
	SptName string
	Master  *native.Server
	Slave   *native.Server
}

// SwitchUnit TODO
type SwitchUnit struct {
	Master Instance `json:"master" validate:"required"`
	Slave  Instance `json:"slave"  validate:"required"`
}

// IpPort TODO
func (i Instance) IpPort() string {
	return fmt.Sprintf("%s:%d", i.Host, i.Port)
}

// Example TODO
func (r *SpiderClusterBackendSwitchComp) Example() interface{} {
	return SpiderClusterBackendSwitchComp{
		Params: &SpiderRemotedbSwitchParam{
			Host:            "1.1.1.1",
			Port:            26000,
			ClientConnCheck: true,
			//	SlaveDelayCheck: true,
			VerifyChecksum: true,
			SwitchParis: []SwitchUnit{
				{
					Master: Instance{
						Host: "2.2.2.2",
						Port: 3306,
					},
					Slave: Instance{
						Host: "3.3.3.3",
						Port: 3306,
					},
				},
				{
					Master: Instance{
						Host: "2.2.2.2",
						Port: 3307,
					},
					Slave: Instance{
						Host: "3.3.3.3",
						Port: 3307,
					},
				},
			},
		},
	}
}

// Init TODO
func (r *SpiderClusterBackendSwitchComp) Init() (err error) {
	r.ipPortServersMap = make(map[string]native.Server)
	logger.Info("tdbctl connecting ...")
	if err = r.connTdbctl(); err != nil {
		logger.Error("Connect %d failed:%s", r.Params.Port, err.Error())
		return err
	}
	logger.Info("query tdbctl servers")
	servers, err := r.tdbCtlConn.SelectServers()
	if err != nil {
		return err
	}
	// connect spider
	logger.Info("connecting all spider ...")
	r.spidersConn, r.spidersLockConn, err = connSpiders(servers)
	if err != nil {
		return err
	}
	logger.Info("get all sys users ...")
	r.getSysUsers(servers, r.GeneralParam.GetAllSysAccount())
	ipPortServersMap, svrNameServersMap := transServersToMap(servers)
	r.ipPortServersMap = ipPortServersMap
	r.svrNameServersMap = svrNameServersMap
	// initialize rollback sql file
	if err = r.initRollbackRouteFile(); err != nil {
		return err
	}
	logger.Info("connect backend instance ...")
	r.mastesConn = make(map[string]*native.DbWorker)
	r.slavesConn = make(map[string]*native.DbWorker)
	for _, swpair := range r.Params.SwitchParis {
		masterAddr := swpair.Master.IpPort()
		slaveAddr := swpair.Slave.IpPort()
		masterSvr, ok := ipPortServersMap[masterAddr]
		if !ok {
			return fmt.Errorf("%s: servers not exist in ipPortServersMap", masterAddr)
		}
		slaveSvr, ok := ipPortServersMap[slaveAddr]
		if !ok {
			return fmt.Errorf("%s: servers not exist in ipPortServersMap", slaveAddr)
		}
		masterConn, err := masterSvr.GetConn()
		if err != nil {
			return err
		}
		r.mastesConn[masterAddr] = masterConn
		slaveConn, err := slaveSvr.GetConn()
		if err != nil {
			return err
		}
		r.slavesConn[slaveAddr] = slaveConn
	}
	return nil
}

// PreCheck TODO
func (r *SpiderClusterBackendSwitchComp) PreCheck() (err error) {
	// verify whether the instance relationship in the parameters is consistent with tdbctl servers
	logger.Info("verify whether the instance relationship in the parameters is consistent with tdbctl servers")
	if err = r.validateServers(); err != nil {
		return err
	}
	if err = r.consistencySwitchCheck(); err != nil {
		if r.Params.Force {
			logger.Warn(err.Error())
			return nil
		}
		return err
	}
	return r.getSwitchSqls()
}

func (r *SpiderClusterBackendSwitchComp) consistencySwitchCheck() (err error) {
	// 检查复制关系
	if err = r.checkReplicationRelation(); err != nil {
		return err
	}
	// 主从延迟检查
	for addr, conn := range r.slavesConn {
		if err = conn.ReplicateDelayCheck(1, 1024); err != nil {
			logger.Error("%s replicate delay abnormal %s", addr, err.Error())
			return err
		}
	}
	if r.Params.ClientConnCheck {
		if err := r.CheckSpiderAppProcesslist(); err != nil {
			return err
		}
	}
	if r.Params.VerifyChecksum {
		return validateChecksum(r.slavesConn)
	}
	return nil
}

// connSpiders TODO
func connSpiders(servers []native.Server) (conns map[string]*native.DbWorker, lockConns map[string]*sql.Conn,
	err error) {
	conns = make(map[string]*native.DbWorker)
	lockConns = make(map[string]*sql.Conn)
	spider_regexp := regexp.MustCompile(native.SPIDER_PREFIX)
	for _, server := range servers {
		if !spider_regexp.MatchString(server.ServerName) {
			continue
		}
		conn, err := native.InsObject{
			Host: server.Host,
			Port: server.Port,
			User: server.Username,
			Pwd:  server.Password,
		}.Conn()
		if err != nil {
			return nil, nil, err
		}
		key := fmt.Sprintf("%s:%d", server.Host, server.Port)
		conns[key] = conn
		sqlConn, err := conn.Db.Conn(context.Background())
		if err != nil {
			logger.Error("failed to get a persistent connection: %w", err.Error())
			return nil, nil, err
		}
		lockConns[key] = sqlConn
	}
	return
}

// checkReplicationRelation 检查remotedb remotedr 同步关系是否正常
func (r *SpiderClusterBackendSwitchComp) checkReplicationRelation() (err error) {
	for _, switch_pair := range r.Params.SwitchParis {
		slaveptname, err := r.getSvrName(switch_pair.Slave.IpPort())
		if err != nil {
			return err
		}
		slaveStaus, err := r.tdbCtlConn.ShowSlaveStatus(slaveptname)
		if err != nil {
			return err
		}
		// 检查从库实际的复制主库是否正确
		replMaster := fmt.Sprintf("%s:%d", slaveStaus.MasterHost, slaveStaus.MasterPort)
		if strings.Compare(replMaster, switch_pair.Master.IpPort()) != 0 {
			return fmt.Errorf("the %s real repl from %s,but the send param master is %s", switch_pair.Slave.IpPort(),
				replMaster, switch_pair.Master.IpPort())
		}
		err = r.tdbCtlConn.CheckSlaveReplStatus(func() (resp native.ShowSlaveStatusResp, err error) {
			return r.tdbCtlConn.ShowSlaveStatus(slaveptname)
		})
		if err != nil {
			return err
		}
	}
	return
}

// func (r *SpiderClusterBackendSwitchComp) checkReplicationStatus() (err error) {
// 	for _, switch_pair := range r.Params.SwitchParis {
// 		slaveptname, err := r.getSvrName(switch_pair.Slave.IpPort())
// 		if err != nil {
// 			return err
// 		}
// 		logger.Info("check %s replicate status ...", switch_pair.Slave.IpPort())
// 		err = r.tdbCtlConn.CheckSlaveReplStatus(func() (resp native.ShowSlaveStatusResp, err error) {
// 			return r.tdbCtlConn.ShowSlaveStatus(slaveptname)
// 		})
// 		if err != nil {
// 			return err
// 		}
// 	}
// 	return
// }

func checkReplicationStatus(conns map[IPPORT]*native.DbWorker) (err error) {
	for addr, conn := range conns {
		logger.Info("check replicate status...")
		slaveStatus, err := conn.ShowSlaveStatus()
		if err != nil {
			return err
		}
		if !slaveStatus.ReplSyncIsOk() {
			return fmt.Errorf("%s replication status is abnormal ,IO Thread: %s,SQL Thread:%s", addr,
				slaveStatus.SlaveIORunning,
				slaveStatus.SlaveSQLRunning)
		}
		err = cmutil.Retry(cmutil.RetryConfig{
			DelayTime: 1 * time.Second,
			Times:     10,
		}, func() error {
			return conn.ReplicateDelayCheck(1, 1024)
		})
		if err != nil {
			logger.Error("delay check failed %s", err.Error())
			return err
		}
	}
	return
}

func (r *SpiderClusterBackendSwitchComp) getSvrName(hostport string) (svrName string, err error) {
	if svr, ok := r.ipPortServersMap[hostport]; ok {
		return svr.ServerName, nil
	}
	return "", fmt.Errorf("get servers empty by %s", hostport)
}

// IPPORT TODO
type IPPORT = string

// SVRNAME TODO
type SVRNAME = string

func transServersToMap(servers []native.Server) (map[IPPORT]native.Server, map[SVRNAME]native.Server) {
	m := make(map[IPPORT]native.Server)
	sm := make(map[string]native.Server)
	for _, server := range servers {
		key := fmt.Sprintf("%s:%d", server.Host, server.Port)
		m[key] = server
		sm[server.ServerName] = server
	}
	return m, sm
}

func (r *SpiderClusterBackendSwitchComp) validateServers() (err error) {
	svrmap := r.ipPortServersMap
	for _, ms := range r.Params.SwitchParis {
		var mastersvr, slavesvr native.Server
		var exist bool
		mh := ms.Master.IpPort()
		if mastersvr, exist = svrmap[mh]; !exist {
			return fmt.Errorf("master %s: not found in mysql.servers", mh)
		}
		if !native.SvrNameIsMasterShard(mastersvr.ServerName) {
			return fmt.Errorf("%s in tdbctl server name:%s is not master shard", mh, mastersvr.ServerName)
		}
		sh := ms.Slave.IpPort()
		if slavesvr, exist = svrmap[sh]; !exist {
			return fmt.Errorf("slave %s: not found in mysql.servers", sh)
		}
		if !native.SvrNameIsSlaveShard(slavesvr.ServerName) {
			return fmt.Errorf("%s in tdbctl server name:%s is not slave shard", sh, slavesvr.ServerName)
		}
		masterShardNum := native.GetShardNumberFromMasterServerName(mastersvr.ServerName)
		slaveShardNum := native.GetShardNumberFromSlaveServerName(slavesvr.ServerName)
		if cmutil.IsEmpty(masterShardNum) {
			return fmt.Errorf("the master %s shard id is empty", mh)
		}
		if cmutil.IsEmpty(slaveShardNum) {
			return fmt.Errorf("the slave %s shard id is empty", sh)
		}
		if strings.Compare(masterShardNum, slaveShardNum) != 0 {
			return fmt.Errorf("master slave shard id is not equal,master shard id is %s,slave shard id  is %s",
				masterShardNum,
				slaveShardNum)
		}
		r.realSwitchSvrPairs = append(r.realSwitchSvrPairs, SvrPairs{
			MptName: mastersvr.ServerName,
			SptName: slavesvr.ServerName,
			Master:  &mastersvr,
			Slave:   &slavesvr,
		})
	}
	return nil
}

func (r *SpiderClusterBackendSwitchComp) connTdbctl() (err error) {
	// connection central control
	conn, err := native.InsObject{
		Host: r.Params.Host,
		Port: r.Params.Port,
		User: r.GeneralParam.RuntimeAccountParam.AdminUser,
		Pwd:  r.GeneralParam.RuntimeAccountParam.AdminPwd,
	}.Conn()
	r.tdbCtlConn = &native.TdbctlDbWork{DbWorker: *conn}
	return err
}

// CutOver TODO
func (r *SpiderClusterBackendSwitchComp) CutOver() (err error) {
	var tdbctlFlushed bool
	logger.Info("the switching operation will be performed")
	// 更改中控路由
	logger.Info("refresh the tdbctl route,but spider hasn t taken effect yet")
	defer func() {
		if err != nil && len(r.primaryShardrollbackSqls) > 0 {
			logger.Info("start execute rollback router sql ... ")
			if _, rerr := r.tdbCtlConn.ExecMore(r.primaryShardrollbackSqls); rerr != nil {
				logger.Error("failed to roll back tdbctl routing")
				return
			}
			logger.Info("rollback route successfully~")
			if tdbctlFlushed {
				return
			}
			if ferr := r.flushrouting(); ferr != nil {
				return
			}
			logger.Info("flush rollback route successfully~")
		}
	}()
	if _, err = r.tdbCtlConn.ExecMore(r.primaryShardSwitchSqls); err != nil {
		tdbctlFlushed = true
		return err
	}
	// lock all spider write
	defer r.Unlock()
	logger.Info("start locking the spider node")
	if err = r.lockaAllSpidersWrite(); err != nil {
		return err
	}
	// check the replication status again
	if !r.Params.Force {
		if err = checkReplicationStatus(r.slavesConn); err != nil {
			return err
		}
	}
	logger.Info("record the location of each node binlog")
	// record the binlog position information during the handover
	if err = r.recordBinLogPos(); err != nil {
		return err
	}
	// flush 到中控生效
	logger.Info("execute:tdbctl flush routing force")
	return r.flushrouting()
}

func (r *SpiderClusterBackendSwitchComp) getSwitchSqls() (err error) {
	for _, ins_pair := range r.realSwitchSvrPairs {
		primarySwitchSql := ins_pair.Slave.GetAlterNodeSql(ins_pair.MptName)
		logger.Info("primary spt switch sql:%s", mysqlutil.CleanSvrPassword(primarySwitchSql))
		r.primaryShardSwitchSqls = append(r.primaryShardSwitchSqls, primarySwitchSql)
		if !r.Params.Force {
			slaveSwitchSql := ins_pair.Master.GetAlterNodeSql(ins_pair.SptName)
			logger.Info("slave spt switch sql:%s", mysqlutil.CleanSvrPassword(slaveSwitchSql))
			r.slaveShardSwitchSqls = append(r.slaveShardSwitchSqls, slaveSwitchSql)
		}
	}
	return
}

// CutOverSlave TODO
func (r *SpiderClusterBackendSwitchComp) CutOverSlave() (err error) {
	var tdbctlFlushed bool
	// switch spider rout
	defer func() {
		if err != nil && len(r.slaveShardrollbackSqls) > 0 {
			_, xerr := r.tdbCtlConn.ExecMore(r.slaveShardrollbackSqls)
			if xerr != nil {
				logger.Error("rollbackup tdbctl router failed %s", xerr.Error())
			}
			logger.Info("rollback route successfully~")
			if tdbctlFlushed {
				return
			}
			if ferr := r.flushrouting(); ferr != nil {
				logger.Error("execute flush rollback route failed %s", err.Error())
				return
			}
			logger.Info("excute flush rollback route successfully~")
		}
	}()
	if _, err = r.tdbCtlConn.ExecMore(r.slaveShardSwitchSqls); err != nil {
		tdbctlFlushed = true
		return err
	}
	// flush 到中控生效
	logger.Info("执行:tdbctl flush routing force")
	return r.flushrouting()
}

// PersistenceRollbackFile TODO
func (r *SpiderClusterBackendSwitchComp) PersistenceRollbackFile() (err error) {
	var masterRbSqls, slaveRbSqls, w []string
	for _, ins_pair := range r.realSwitchSvrPairs {
		masterRbSqls = append(masterRbSqls, ins_pair.Master.GetAlterNodeSql(ins_pair.MptName))
		slaveRbSqls = append(slaveRbSqls, ins_pair.Slave.GetAlterNodeSql(ins_pair.SptName))
	}
	if err = r.initRollbackRouteFile(); err != nil {
		return err
	}
	w = masterRbSqls
	if !r.Params.Force {
		w = append(w, "// slave spt rollback sql text ")
		w = append(w, slaveRbSqls...)
	}
	if err = r.writeContents(w); err != nil {
		return err
	}
	if err = r.fd.Close(); err != nil {
		logger.Error("close rollback file error:%s", err.Error())
		return err
	}
	r.primaryShardrollbackSqls = masterRbSqls
	r.slaveShardrollbackSqls = slaveRbSqls
	logger.Info("rollback sql file persisted successfully")
	return
}

func (r *SpiderClusterBackendSwitchComp) recordBinLogPos() (err error) {
	r.newMasterPosInfos = make(map[string]native.MasterStatusResp)
	for _, swpair := range r.Params.SwitchParis {
		conn, ok := r.slavesConn[swpair.Slave.IpPort()]
		if !ok {
			return fmt.Errorf("get  %s conn failed", swpair.Slave.IpPort())
		}
		pos, err := conn.ShowMasterStatus()
		if err != nil {
			return err
		}
		logger.Info("%s,current pos is  binlog_file:%s,binlog_pos:%d,gitid_sets:%s", swpair.Slave.IpPort(), pos.File,
			pos.Position,
			pos.ExecutedGtidSet)
		r.newMasterPosInfos[swpair.Slave.IpPort()] = pos
	}
	return
}

// GrantReplForNewSlave TODO
func (r *SpiderClusterBackendSwitchComp) GrantReplForNewSlave() (err error) {
	for _, swpair := range r.Params.SwitchParis {
		conn, ok := r.slavesConn[swpair.Slave.IpPort()]
		if !ok {
			return fmt.Errorf("get  %s conn failed", swpair.Slave.IpPort())
		}
		if _, err = conn.ExecMore(r.grantReplSql(swpair.Master.Host)); err != nil {
			return err
		}
	}
	return nil
}

// StopRepl TODO
func (r *SpiderClusterBackendSwitchComp) StopRepl() (err error) {
	for _, swpair := range r.Params.SwitchParis {
		conn, ok := r.slavesConn[swpair.Slave.IpPort()]
		if !ok {
			return fmt.Errorf("get  %s conn failed", swpair.Slave.IpPort())
		}
		if _, err = conn.ExecMore([]string{"stop slave;", "reset slave all;"}); err != nil {
			return err
		}
	}
	return nil
}

func (r *SpiderClusterBackendSwitchComp) grantReplSql(host string) []string {
	var execSQLs []string
	repl_user := r.GeneralParam.RuntimeAccountParam.ReplUser
	repl_pwd := r.GeneralParam.RuntimeAccountParam.ReplPwd
	logger.Info("repl user:%s,repl_pwd:%s", repl_user, repl_pwd)
	execSQLs = append(execSQLs, fmt.Sprintf("CREATE USER /*!50706 IF NOT EXISTS */ `%s`@`%s` IDENTIFIED BY '%s';",
		repl_user, host, repl_pwd))
	execSQLs = append(execSQLs, fmt.Sprintf("GRANT REPLICATION SLAVE, REPLICATION CLIENT ON *.* TO `%s`@`%s`;", repl_user,
		host))
	return execSQLs
}

// ChangeMasterToNewMaster TODO
func (r *SpiderClusterBackendSwitchComp) ChangeMasterToNewMaster() (err error) {
	repl_user := r.GeneralParam.RuntimeAccountParam.ReplUser
	repl_pwd := r.GeneralParam.RuntimeAccountParam.ReplPwd
	for _, swpair := range r.Params.SwitchParis {
		conn := r.mastesConn[swpair.Master.IpPort()]
		pos := r.newMasterPosInfos[swpair.Slave.IpPort()]
		changeMastersql := fmt.Sprintf(
			`CHANGE MASTER TO MASTER_HOST='%s', 
			MASTER_USER ='%s', 
			MASTER_PASSWORD='%s',
			MASTER_PORT=%d,
			MASTER_LOG_FILE='%s',
			MASTER_LOG_POS=%d`,
			swpair.Slave.Host,
			repl_user,
			repl_pwd,
			swpair.Slave.Port,
			pos.File,
			pos.Position,
		)
		logger.Info("change master  to %s", swpair.Slave.IpPort())
		if _, err = conn.Exec(changeMastersql); err != nil {
			return err
		}
		logger.Info("start slave")
		if _, err = conn.Exec("start slave;"); err != nil {
			return err
		}
		err = cmutil.Retry(cmutil.RetryConfig{
			Times:     30,
			DelayTime: 1 * time.Second,
		}, func() error {
			ss, serr := conn.ShowSlaveStatus()
			if serr != nil {
				return serr
			}
			if ss.ReplSyncIsOk() {
				return nil
			}
			return fmt.Errorf("wating..., IOThread:%s,SQLThread:%s", ss.SlaveIORunning, ss.SlaveSQLRunning)
		})
		if err != nil {
			return err
		}
	}
	return err
}

func (c *CutOverCtx) getSysUsers(servers []native.Server, sysUsers []string) {
	for _, server := range servers {
		sysUsers = append(sysUsers, server.Username)
	}
	// get sys user
	c.sysUsers = cmutil.RemoveDuplicate(sysUsers)
	logger.Info("system user: %v", c.sysUsers)
}

func (c *CutOverCtx) getSlaveSptServers() (slaveSptServers []native.Server) {
	for svrName, server := range c.svrNameServersMap {
		if native.SvrNameIsSlaveShard(svrName) {
			slaveSptServers = append(slaveSptServers, server)
		}
	}
	return
}

func (c *CutOverCtx) getSlaveSpiderServers() (slaveSpiderServers []native.Server) {
	for svrName, server := range c.svrNameServersMap {
		if native.SvrNameIsSlaveSpiderShard(svrName) {
			slaveSpiderServers = append(slaveSpiderServers, server)
		}
	}
	return
}

// CheckSpiderAppProcesslist TODO
func (ctx *CutOverCtx) CheckSpiderAppProcesslist() (err error) {
	for addr, spider_conn := range ctx.spidersConn {
		pls, err := spider_conn.ShowApplicationProcesslist(ctx.sysUsers)
		if err != nil {
			return err
		}
		if len(pls) > 0 {
			return fmt.Errorf("spider: %s have application processlist %v", addr, pls)
		}
	}
	return
}

func (ctx *CutOverCtx) lockaAllSpidersWrite() (err error) {
	for addr, lockConn := range ctx.spidersLockConn {
		_, err = lockConn.ExecContext(context.Background(), "set lock_wait_timeout = 10;")
		if err != nil {
			return fmt.Errorf("set lock_wait_timeout at %s failed,err:%w", addr, err)
		}
		fn := func() (e error) {
			_, e = lockConn.ExecContext(context.Background(), "flush table with read lock;")
			if e != nil {
				return fmt.Errorf("lock tables at %s,err:%w", addr, e)
			}
			return e
		}
		if err = cmutil.Retry(cmutil.RetryConfig{Times: 3, DelayTime: 1 * time.Second}, fn); err != nil {
			return err
		}
	}
	return
}

// Unlock TODO
func (ctx *CutOverCtx) Unlock() (err error) {
	for addr, lockConn := range ctx.spidersLockConn {
		err = cmutil.Retry(cmutil.RetryConfig{
			Times:     3,
			DelayTime: 1 * time.Second,
		}, func() error {
			_, ierr := lockConn.ExecContext(context.Background(), "unlock tables")
			if ierr != nil {
				return ierr
			}
			// 归还连接到连接池
			lockConn.Close()
			return nil
		})
		if err != nil {
			return fmt.Errorf("addr:%s,err:%w", addr, err)
		}
	}
	return
}

func (c *CutOverCtx) flushrouting() (err error) {
	if err = cmutil.Retry(cmutil.RetryConfig{Times: 3, DelayTime: 1 * time.Second}, func() error {
		_, ferr := c.tdbCtlConn.Exec("tdbctl flush routing force")
		return ferr
	}); err != nil {
		return err
	}
	return
}

// me, ok := err.(*mysql.MySQLError)
// if !ok {
// 	return
// }
// if me.Number == 12028 {
// 	partFlushed = true
// }
// partFlushed, err

func (c *CutOverCtx) initRollbackRouteFile() (err error) {
	fileName := "rollback.sql"
	currentPath, err := os.Getwd()
	if err != nil {
		return
	}
	logger.Info("init rollback route sql file in %s", currentPath)
	if cmutil.FileExists(fileName) {
		fsInfo, err := os.Stat(fileName)
		if err != nil {
			return err
		}
		err = os.Rename(fileName, fileName+"."+fsInfo.ModTime().Format(cst.TimeLayoutDir))
		if err != nil {
			return err
		}
	}
	c.fd, err = os.OpenFile(fileName, os.O_CREATE|os.O_RDWR|os.O_APPEND, 0644)
	if err != nil {
		return err
	}
	logger.Info("create rollback sql file : %s", path.Join(currentPath, fileName))
	return
}

func (c *CutOverCtx) writeContents(contents []string) (err error) {
	write := bufio.NewWriter(c.fd)
	for _, content := range contents {
		_, err = write.WriteString(content + "\n\r")
		if err != nil {
			return err
		}
	}
	if err = write.Flush(); err != nil {
		return err
	}
	return
}
