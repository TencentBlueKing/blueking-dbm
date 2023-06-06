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
	"fmt"
	"regexp"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
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
	// 主从延迟检查
	SlaveDelayCheck bool `json:"slave_delay_check"`
	// 数据校验结果检查
	VerifyChecksum bool         `json:"verify_checksum"`
	SwitchParis    []SwitchUnit `json:"switch_paris" validate:"required,gt=0,dive"`
	// force: 忽略部分切换前检查
	Force bool `json:"force"`
}

// CutOverCtx TODO
type CutOverCtx struct {
	tdbCtlConn        *native.TdbctlDbWork
	spidersConn       map[string]*native.DbWorker
	ipPortServersMap  map[IPPORT]native.Server
	svrNameServersMap map[SVRNAME]native.Server
	newMasterPosInfos map[string]native.MasterStatusResp
	sysUsers          []string
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
			SlaveDelayCheck: true,
			VerifyChecksum:  true,
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
	r.spidersConn, err = ConnSpiders(servers)
	if err != nil {
		return err
	}
	logger.Info("get all sys users ...")
	r.getSysUsers(servers, append(r.GeneralParam.RuntimeExtend.MySQLSysUsers,
		r.GeneralParam.RuntimeAccountParam.GetAllSysAccount()...))
	ipPortServersMap, svrNameServersMap := transServersToMap(servers)
	r.ipPortServersMap = ipPortServersMap
	r.svrNameServersMap = svrNameServersMap
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
	return nil
}

func (r *SpiderClusterBackendSwitchComp) consistencySwitchCheck() (err error) {
	// 检查复制关系
	if err = r.checkReplicationRelation(); err != nil {
		return err
	}
	if r.Params.ClientConnCheck {
		if err := r.CheckSpiderAppProcesslist(); err != nil {
			return err
		}
	}
	// 检查数据checksum和延迟等
	var allow_delay int
	if r.Params.SlaveDelayCheck {
		allow_delay = 1
	}
	if err = replStatusCheck(r.slavesConn, r.Params.VerifyChecksum, allow_delay); err != nil {
		return err
	}
	return nil
}

// ConnSpiders TODO
func ConnSpiders(servers []native.Server) (conns map[string]*native.DbWorker, err error) {
	conns = make(map[string]*native.DbWorker)
	spider_regexp := regexp.MustCompile(native.SPIDER_PREFIX)
	for _, server := range servers {
		if spider_regexp.MatchString(server.ServerName) {
			conn, err := native.InsObject{
				Host: server.Host,
				Port: server.Port,
				User: server.Username,
				Pwd:  server.Password,
			}.Conn()
			if err != nil {
				return nil, err
			}
			key := fmt.Sprintf("%s:%d", server.Host, server.Port)
			conns[key] = conn
		}
	}
	return
}

// checkReplicationRelation TODO
// checkSlaveStatus 检查remotedb remotedr 同步关系是否正常
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

func (r *SpiderClusterBackendSwitchComp) checkReplicationStatus() (err error) {
	for _, switch_pair := range r.Params.SwitchParis {
		slaveptname, err := r.getSvrName(switch_pair.Slave.IpPort())
		if err != nil {
			return err
		}
		logger.Info("check %s replicate status ...", switch_pair.Slave.IpPort())
		err = r.tdbCtlConn.CheckSlaveReplStatus(func() (resp native.ShowSlaveStatusResp, err error) {
			return r.tdbCtlConn.ShowSlaveStatus(slaveptname)
		})
		if err != nil {
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
	var flushed bool
	logger.Info("the switching operation will be performed")
	// 更改中控路由
	logger.Info("refresh the tdbctl route")
	defer r.Unlock()
	var rollbackRouters []string
	if rollbackRouters, err = r.switchMaterSpt(); err != nil {
		return err
	}
	defer func() {
		if err != nil {
			if len(rollbackRouters) > 0 {
				logger.Info("start execute rollback router sql ... ")
				_, rerr := r.tdbCtlConn.ExecMore(rollbackRouters)
				if rerr != nil {
					logger.Error("failed to roll back tdbctl routing")
					return
				}
				logger.Info("rollback route successfully~")
				if flushed {
					ferr := r.flushrouting()
					if ferr != nil {
						return
					}
					logger.Info("flush rollback route successfully~")
				}
			}
		}
	}()
	// lock all spider write
	logger.Info("start locking the spider node")
	if err = r.LockaAllSpidersWrite(); err != nil {
		return err
	}
	// 再次检查复制状态
	if !r.Params.Force {
		if err = r.checkReplicationStatus(); err != nil {
			return err
		}
	}
	logger.Info("记录各个节点binlog的位置")
	// record the binlog position information during the handover
	if err = r.recordBinLogPos(); err != nil {
		return err
	}
	// flush 到中控生效
	logger.Info("执行:tdbctl flush routing force")
	return r.flushrouting()
}

func (r *SpiderClusterBackendSwitchComp) switchMaterSpt() (rollbackRouterSqls []string, err error) {
	for _, ins_pair := range r.realSwitchSvrPairs {
		switch_sql := ins_pair.Slave.GetAlterNodeSql(ins_pair.MptName)
		rollbackRouterSqls = append(rollbackRouterSqls, ins_pair.Master.GetAlterNodeSql(ins_pair.MptName))
		// log的时候需要隐藏密码
		logger.Info("will execute  switch sql:%s", switch_sql)
		_, err = r.tdbCtlConn.Exec(switch_sql)
		if err != nil {
			return rollbackRouterSqls, err
		}
	}
	return
}

// SwitchSlaveSpt TODO
func (r *SpiderClusterBackendSwitchComp) SwitchSlaveSpt() (err error) {
	// switch spider rout
	var rollback_switch_sqls []string
	defer func() {
		if err != nil && len(rollback_switch_sqls) > 0 {
			_, xerr := r.tdbCtlConn.ExecMore(rollback_switch_sqls)
			if xerr != nil {
				logger.Error("rollbackup tdbctl router failed %s", xerr.Error())
			}
			err = fmt.Errorf("%w,rollbackup err:%w", err, xerr)
		}
	}()

	for _, ins_pair := range r.realSwitchSvrPairs {
		switch_sql := ins_pair.Master.GetAlterNodeSql(ins_pair.SptName)
		rollback_switch_sqls = append(rollback_switch_sqls, ins_pair.Slave.GetAlterNodeSql(ins_pair.SptName))
		// log的时候需要隐藏密码
		logger.Info("will execute  switch sql:%s", switch_sql)
		_, err = r.tdbCtlConn.Exec(switch_sql)
		if err != nil {
			return err
		}
	}
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

// LockaAllSpidersWrite TODO
func (ctx *CutOverCtx) LockaAllSpidersWrite() (err error) {
	for addr, spider_conn := range ctx.spidersConn {
		_, err = spider_conn.Exec("flush table with read lock;")
		if err != nil {
			return fmt.Errorf("lock tables at %s,err:%w", addr, err)
		}
	}
	return
}

// Unlock TODO
func (ctx *CutOverCtx) Unlock() (err error) {
	for addr, spider_conn := range ctx.spidersConn {
		err = cmutil.Retry(cmutil.RetryConfig{
			Times:     3,
			DelayTime: 1 * time.Second,
		}, func() error {
			_, ierr := spider_conn.Exec("unlock tables")
			if ierr != nil {
				return ierr
			}
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
