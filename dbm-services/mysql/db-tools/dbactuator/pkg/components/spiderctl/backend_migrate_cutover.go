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
	"errors"
	"fmt"
	"time"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/cutover"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
)

//  scene 1
//
//  spider --> master <-- slave
//  slave_spider ----------^
//
// 	after cutover
//
//  spider --> new_master <-- new_slave
//  slave_spider ----------------^

//  scene 2
//  the spider cluster not have slave
//
//  spider --> master
//
// 	after cutover
//
//  spider --> new_master

// SpiderClusterBackendMigrateCutoverComp TODO
type SpiderClusterBackendMigrateCutoverComp struct {
	GeneralParam *components.GeneralParam       `json:"general"`
	Params       *RemotedbdrMigrateCutoverParam `json:"extend"`
	ctx
}

// 迁移切换前置条件：
// 带切换的实例， dest master，dest slave 需要提前给tdbctl中控授权

// RemotedbdrMigrateCutoverParam TODO
type RemotedbdrMigrateCutoverParam struct {
	// tdbctl host port
	Host string `json:"host" validate:"required,ip"`
	Port int    `json:"port" validate:"required,lt=65536,gte=3306"`
	// 客户端连接检查
	ClientConnCheck bool `json:"client_conn_check"`
	// 主从延迟检查
	SlaveDelayCheck bool `json:"slave_delay_check"`
	// 数据校验结果检查
	VerifyChecksum      bool                 `json:"verify_checksum"`
	MigrateCutoverPairs []MigrateCutoverPair `json:"migrate_cutover_pairs"`
}

type ctx struct {
	CutOverCtx
	destMasterConn   map[IPPORT]*native.DbWorker
	destSlaveConn    map[IPPORT]*native.DbWorker
	cutOverPairs     []CutOverParis
	existRemoteSlave bool
	checkVars        []string
}

// CutOverParis TODO
type CutOverParis struct {
	MasterSvr  native.Server
	SlaveSvr   native.Server
	DestMaster CutoverUnit
	DestSlave  CutoverUnit
}

// MigrateCutoverPair TODO
type MigrateCutoverPair struct {
	Master     Instance    `json:"origin_master" validate:"required"`
	DestMaster CutoverUnit `json:"dest_master"  validate:"required"`
	DestSlave  CutoverUnit `json:"dest_slave"`
}

const (
	// DelayThreshold TODO
	//  #slave io_thread behand master time
	// my $allowed_slave_delay_max = 120;
	// #slave system time behand master time
	// my $allowed_time_delay_max = 10;
	// my $exec_delay_threshold = 1024; #kbyte
	DelayThreshold = 1024 * 10 // 10k
)

// destSlaveIsEmpty TODO
// 如果参数
func (m *MigrateCutoverPair) destSlaveIsEmpty() bool {
	return m.DestSlave == CutoverUnit{}
}

// CutoverUnit TODO
type CutoverUnit struct {
	Host string `json:"host" validate:"required,ip"`
	Port int    `json:"port" validate:"required,lt=65536,gte=3306"`
	// account password used by the tdbctl system
	User     string `json:"user"`
	Password string `json:"password"`
}

// GetAlterNodeSql TODO
func (c *CutoverUnit) GetAlterNodeSql(svrName string) string {
	return fmt.Sprintf("TDBCTL ALTER NODE %s options(user '%s', password '%s', host '%s', port %d);",
		svrName,
		c.User,
		c.Password, c.Host, c.Port)
}

// GetHostPort TODO
func (c *CutoverUnit) GetHostPort() string {
	return fmt.Sprintf("%s:%d", c.Host, c.Port)
}

// Conn TODO
func (c *CutoverUnit) Conn() (conn *native.DbWorker, err error) {
	conn, err = native.InsObject{
		Host: c.Host,
		Port: c.Port,
		User: c.User,
		Pwd:  c.Password,
	}.Conn()
	return
}

// Example TODO
func (s *SpiderClusterBackendMigrateCutoverComp) Example() interface{} {
	return SpiderClusterBackendMigrateCutoverComp{
		Params: &RemotedbdrMigrateCutoverParam{
			Host:            "1.1.1.1",
			Port:            26000,
			ClientConnCheck: true,
			SlaveDelayCheck: true,
			VerifyChecksum:  true,
			MigrateCutoverPairs: []MigrateCutoverPair{
				{
					Master: Instance{
						Host: "2.2.2.2",
						Port: 3006,
					},
					DestMaster: CutoverUnit{
						Host:     "3.3.3.3",
						Port:     3306,
						User:     "xx",
						Password: "xx",
					},
					DestSlave: CutoverUnit{
						Host:     "4.4.4.4",
						Port:     3306,
						User:     "xx",
						Password: "xx",
					},
				},
				{
					Master: Instance{
						Host: "2.2.2.2",
						Port: 3007,
					},
					DestMaster: CutoverUnit{
						Host:     "3.3.3.3",
						Port:     3307,
						User:     "xx",
						Password: "xx",
					},
					DestSlave: CutoverUnit{
						Host:     "4.4.4.4",
						Port:     3307,
						User:     "xx",
						Password: "xx",
					},
				},
			},
		},
	}
}

// Init TODO
func (s *SpiderClusterBackendMigrateCutoverComp) Init() (err error) {
	logger.Info("cutover param is %v", s.Params.MigrateCutoverPairs)
	var conn *native.DbWorker
	conn, err = native.InsObject{
		Host: s.Params.Host,
		Port: s.Params.Port,
		User: s.GeneralParam.RuntimeAccountParam.AdminUser,
		Pwd:  s.GeneralParam.RuntimeAccountParam.AdminPwd,
	}.Conn()
	if err != nil {
		return err
	}
	s.tdbCtlConn = &native.TdbctlDbWork{DbWorker: *conn}
	// 查询mysql.servers tables
	servers, err := s.tdbCtlConn.SelectServers()
	if err != nil {
		return err
	}
	// connect spider
	s.spidersConn, err = ConnSpiders(servers)
	if err != nil {
		return err
	}
	// conn dest master slave
	if err = s.connDest(); err != nil {
		return err
	}
	s.getSysUsers(servers, append(s.GeneralParam.RuntimeExtend.MySQLSysUsers,
		s.GeneralParam.RuntimeAccountParam.GetAllSysAccount()...))
	ipPortServersMap, svrNameServersMap := transServersToMap(servers)
	s.ipPortServersMap = ipPortServersMap
	s.svrNameServersMap = svrNameServersMap
	s.checkVars = []string{"character_set_server", "lower_case_table_names", "time_zone", "binlog_format",
		"log_bin_compress"}
	return nil
}

// PreCheck TODO
func (s *SpiderClusterBackendMigrateCutoverComp) PreCheck() (err error) {
	if err := s.cutOverParisParamCheck(); err != nil {
		return err
	}
	// check dest master with dest slave replicate status
	if s.existRemoteSlave {
		logger.Info("check whether the master slave synchronization status to be switched is normal")
		if err = replStatusCheck(s.destSlaveConn, s.Params.VerifyChecksum, 10); err != nil {
			return err
		}
	}
	// compare origin master with dest master variables
	if err = s.validateServers(); err != nil {
		return err
	}
	logger.Info("check whether the key variables of the source master and the target master are consistent")
	if err = s.checkPairsVariables(); err != nil {
		return err
	}
	if s.Params.ClientConnCheck {
		if err := s.CheckSpiderAppProcesslist(); err != nil {
			return err
		}
	}
	// 检查数据checksum和延迟等
	var allow_delay int
	if s.Params.SlaveDelayCheck {
		allow_delay = 1
	}
	//  check origin master with dest master replicate status
	if err = replStatusCheck(s.destMasterConn, s.Params.VerifyChecksum, allow_delay); err != nil {
		return err
	}
	return err
}

func (s *SpiderClusterBackendMigrateCutoverComp) checkPairsVariables() (err error) {
	for _, pair := range s.cutOverPairs {
		svrName := pair.MasterSvr.ServerName
		destMasterConn, ok := s.destMasterConn[pair.DestMaster.GetHostPort()]
		if !ok {
			return fmt.Errorf("get %s conn from destMasterConn map failed", pair.DestMaster.GetHostPort())
		}
		if err = s.tdbCtlConn.MySQLVarsCompare(svrName, destMasterConn, s.checkVars); err != nil {
			return err
		}
	}
	return
}

// cutOverParisParamCheck 参数中、目标的master 和目标slave 检查
// 目标slave 只能都为空、或者呀完全匹配目标master的个数
func (s *SpiderClusterBackendMigrateCutoverComp) cutOverParisParamCheck() (err error) {
	destSlaveNum := 0
	s.existRemoteSlave = false
	for _, ins := range s.Params.MigrateCutoverPairs {
		if ins.destSlaveIsEmpty() {
			if destSlaveNum > 0 {
				return fmt.Errorf("you must send slave param for master: %s", ins.DestMaster.GetHostPort())
			}
			continue
		}
		destSlaveNum++
	}
	slaveSptServers := s.getSlaveSptServers()
	slaveSpiderServers := s.getSlaveSpiderServers()
	// 如果传参中并没有待切换的slave
	// 但是在mysql.server 表中查询到了spider slave 相关信息
	// 则需要抛出异常
	if destSlaveNum == 0 && len(slaveSptServers) > 0 && len(slaveSpiderServers) > 0 {
		return errors.New(`the origin spider cluster exist spider spt and slave spider,
							but this time cutover not have waited cutover slaves`)
	}
	// 其他情况只切换spider master对应的主分片
	if destSlaveNum == len(s.Params.MigrateCutoverPairs) {
		s.existRemoteSlave = true
	}
	return nil
}

func (s *SpiderClusterBackendMigrateCutoverComp) connDest() (err error) {
	s.destMasterConn = make(map[string]*native.DbWorker)
	s.destSlaveConn = make(map[string]*native.DbWorker)
	for _, ins := range s.Params.MigrateCutoverPairs {
		destMasterAddr := ins.DestMaster.GetHostPort()
		logger.Info("connecting %s ...", destMasterAddr)
		masterConn, err := ins.DestMaster.Conn()
		if err != nil {
			return err
		}
		s.destMasterConn[destMasterAddr] = masterConn
		if !ins.destSlaveIsEmpty() {
			slaveConn, err := ins.DestMaster.Conn()
			if err != nil {
				return err
			}
			s.destSlaveConn[ins.DestSlave.GetHostPort()] = slaveConn
		}
	}
	logger.Info("dest master conn %v", s.destMasterConn)
	return
}

func replStatusCheck(conns map[string]*native.DbWorker, validateChecksum bool, allowDelayThreshold int) (err error) {
	for addr, conn := range conns {
		mscheck := &cutover.MSCheck{
			SlavedbConn:          conn,
			NeedCheckSumRd:       validateChecksum,
			NotVerifyChecksum:    !validateChecksum,
			AllowDiffCount:       10,
			AllowDelaySec:        allowDelayThreshold,
			AllowDelayBinlogByte: DelayThreshold,
		}
		if err = mscheck.Check(); err != nil {
			return fmt.Errorf("slave %s, master slave data check failed %w", addr, err)
		}
	}
	return
}

func (s *SpiderClusterBackendMigrateCutoverComp) validateServers() (err error) {
	for _, ins := range s.Params.MigrateCutoverPairs {
		var mastersvr native.Server
		var exist bool
		var pair CutOverParis
		if mastersvr, exist = s.ipPortServersMap[ins.Master.IpPort()]; !exist {
			return fmt.Errorf("master %s: not found in mysql.servers", ins.Master.IpPort())
		}
		if !native.SvrNameIsMasterShard(mastersvr.ServerName) {
			return fmt.Errorf("%s in tdbctl server name is not master shard", ins.Master.IpPort())
		}
		if s.existRemoteSlave {
			slaveSptName := native.GetSlaveShardNameByMasterShardName(mastersvr.ServerName)
			logger.Info("slave spt name is:%s", slaveSptName)
			slavesvr, exists := s.svrNameServersMap[slaveSptName]
			if !exists {
				return fmt.Errorf("the key %s,not found in svrNameServersMap ", slaveSptName)
			}
			pair.SlaveSvr = slavesvr
			pair.DestSlave = ins.DestSlave
		} else {
			pair.MasterSvr = mastersvr
			pair.DestMaster = ins.DestMaster
		}
		s.cutOverPairs = append(s.cutOverPairs, pair)
	}
	return
}

// CutOver TODO
func (s *SpiderClusterBackendMigrateCutoverComp) CutOver() (err error) {
	var flushed bool
	logger.Info("the switching operation will be performed")
	// change the central control route
	logger.Info("start refreshing the primary spt route")
	var rollbackSqls []string
	if rollbackSqls, err = s.switchSpt(); err != nil {
		return err
	}
	// release the lock until after performing the rollback routing
	defer s.Unlock()
	defer func() {
		if err != nil && len(rollbackSqls) > 0 {
			_, xerr := s.tdbCtlConn.ExecMore(rollbackSqls)
			if xerr != nil {
				logger.Error("rollbackup tdbctl router failed %s", xerr.Error())
				err = fmt.Errorf("%w,rollbackup err:%w", err, xerr)
				return
			}
			logger.Info("rollback route successfully~")
			if flushed {
				if ferr := s.flushrouting(); ferr != nil {
					err = fmt.Errorf("%w,flush rollback route err:%w", err, ferr)
					return
				}
				logger.Info("rollback route successfully~")
			}
		}
	}()
	logger.Info("update tdbctl mysql.servers successfully")
	// lock all spider write
	logger.Info("start locking the spider")
	if err = s.LockaAllSpidersWrite(); err != nil {
		return err
	}
	logger.Info("lock all spider successfully,record the location of each instance binlog")
	// record the binlog position information during the handover
	if err = s.CheckMsSyncStatusAndRecordBinlogPos(); err != nil {
		return err
	}
	logger.Info("doing tdbctl flush routing force ... ")
	return s.flushrouting()
}

// StopRepl TODO
func (s *SpiderClusterBackendMigrateCutoverComp) StopRepl() (err error) {
	for hostPort, destMasterConn := range s.destMasterConn {
		logger.Info("%s: execute stop slave,reset slave", hostPort)
		if _, err = destMasterConn.ExecMore([]string{"stop slave;", "reset slave all;"}); err != nil {
			return err
		}
	}
	return nil
}

// CheckMsSyncStatusAndRecordBinlogPos TODO
func (s *SpiderClusterBackendMigrateCutoverComp) CheckMsSyncStatusAndRecordBinlogPos() (err error) {
	for hostPort, destMasterConn := range s.destMasterConn {
		logger.Info("check replicate status...")
		slaveStatus, err := destMasterConn.ShowSlaveStatus()
		if err != nil {
			return err
		}
		if !slaveStatus.ReplSyncIsOk() {
			return fmt.Errorf("%s replication status is abnormal ,IO Thread: %s,SQL Thread:%s", hostPort,
				slaveStatus.SlaveIORunning,
				slaveStatus.SlaveSQLRunning)
		}
		cmutil.Retry(cmutil.RetryConfig{
			DelayTime: 1 * time.Second,
			Times:     10,
		}, func() error {
			delaytotalByte, err := destMasterConn.TotalDelayBinlogSize()
			if err != nil {
				return err
			}
			if delaytotalByte <= 0 || (!s.Params.SlaveDelayCheck && delaytotalByte < DelayThreshold) {
				logger.Info("synchronization delay check is normal")
			} else {
				return fmt.Errorf("slave binlog still behand master %d byte", delaytotalByte)
			}
			return nil
		})
		logger.Info("record %s master status", hostPort)
		pos, err := destMasterConn.ShowMasterStatus()
		if err != nil {
			logger.Warn("%s show master status failed %s", hostPort, err.Error())
			return nil
		}
		logger.Info("%s,current pos is  binlog_file:%s,binlog_pos:%d,gitid_sets:%s", hostPort, pos.File,
			pos.Position,
			pos.ExecutedGtidSet)
	}
	return nil
}

func (s *SpiderClusterBackendMigrateCutoverComp) switchSpt() (rollbackRouters []string, err error) {
	logger.Info("start switch master spt ...")
	var alterSqls []string
	for _, pair := range s.cutOverPairs {
		masterSvrName := pair.MasterSvr.ServerName
		rollbackRouters = append(rollbackRouters, pair.MasterSvr.GetAlterNodeSql(masterSvrName))
		alterSql := pair.DestMaster.GetAlterNodeSql(masterSvrName)
		logger.Info("will execute  master spt switch sql:%s", alterSql)
		alterSqls = append(alterSqls, alterSql)
		if s.existRemoteSlave {
			slaveSvrName := pair.SlaveSvr.ServerName
			rollbackRouters = append(rollbackRouters, pair.SlaveSvr.GetAlterNodeSql(slaveSvrName))
			alterSql := pair.SlaveSvr.GetAlterNodeSql(slaveSvrName)
			logger.Info("will execute slave spt switch sql:%s", alterSql)
		}
	}
	if _, err = s.tdbCtlConn.ExecMore(alterSqls); err != nil {
		return
	}
	return rollbackRouters, err
}
