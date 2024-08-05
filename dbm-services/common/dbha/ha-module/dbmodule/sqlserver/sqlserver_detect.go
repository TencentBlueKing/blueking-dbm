/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package sqlserver

import (
	"encoding/json"
	"fmt"
	"math/rand"
	"sync"
	"time"

	"dbm-services/common/dbha/ha-module/config"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/dbutil"
	"dbm-services/common/dbha/ha-module/log"
	"dbm-services/common/dbha/ha-module/types"
	"dbm-services/common/dbha/ha-module/util"
)

const (
	MONITOR_DB = "Monitor"
	INSERT_SQL = `
	update [Monitor].[dbo].[CHECK_HEARTBEAT] set CHECK_TIME = GETDATE();
	if @@rowcount=0
	insert into [Monitor].[dbo].[CHECK_HEARTBEAT] values(GETDATE());`
	SSH_TOUCH_DIR = "d:\\\\dbha"
)

// SqlserverDetectResponse sqlserver instance response struct
type SqlserverDetectResponse struct {
	dbutil.BaseDetectDBResponse
}

// SqlserverLDetectInstanceInfoFromCmDB Sqlserver instance detect struct in cmdbcar
type SqlserverDetectInstanceInfoFromCmDB struct {
	Ip          string
	Port        int
	App         string
	ClusterType string
	MetaType    string
	Cluster     string
}

// SqlserverDetectInstance sqlserver instance detect struct
type SqlserverDetectInstance struct {
	dbutil.BaseDetectDB
	User    string
	Pass    string
	Timeout int
	realDB  *DbWorker
	dbMutex sync.Mutex // Mutex for protecting realDB
}

// GetDetectType return dbType
func (s *SqlserverDetectInstance) GetDetectType() string {
	return s.ClusterType
}

// Detection agent, gmm call this do lived detect
// return error:
//
//	not nil: check db failed or do ssh failed
//	nil:     check db success
func (s *SqlserverDetectInstance) Detection() error {
	recheck := 1
	var mysqlErr error
	needRecheck := true
	for i := 0; i <= recheck && needRecheck; i++ {
		// 设置缓冲为1防止没有接收者导致阻塞，即Detection已经超时返回
		errChan := make(chan error, 2)
		// 这里存在资源泄露的可能，因为不能主动kill掉协程，所以如果这个协程依然阻塞在连接CheckSqlserver，但是
		// 这个函数已经超时返回了，那么这个协程因为被阻塞一直没被释放，直到MySQL连接超时，如果阻塞的时间
		// 大于下次探测该实例的时间间隔，则创建协程频率大于释放协程频率，可能会导致oom。可以考虑在CheckSqlserver
		// 客户端连接设置超时时间来防止。
		go s.CheckSqlserver(errChan)
		select {
		case mysqlErr = <-errChan:
			if mysqlErr != nil {
				log.Logger.Warnf("check sqlserver failed. ip:%s, port:%d, app:%s", s.Ip, s.Port, s.App)
				s.Status = constvar.DBCheckFailed
				needRecheck = false
			} else {
				s.Status = constvar.DBCheckSuccess
				return nil
			}
		case <-time.After(time.Second * time.Duration(s.Timeout)):
			mysqlErr = fmt.Errorf("connect sqlserver timeout recheck:%d", recheck)
			log.Logger.Warnf(mysqlErr.Error())
			s.Status = constvar.DBCheckFailed
		}
	}

	sshErr := s.CheckSSH()
	if sshErr != nil {
		if util.CheckSSHErrIsAuthFail(sshErr) {
			s.Status = constvar.SSHAuthFailed
			log.Logger.Warnf("check ssh auth failed. ip:%s, port:%d, app:%s, status:%s",
				s.Ip, s.Port, s.App, s.Status)
		} else {
			s.Status = constvar.SSHCheckFailed
			log.Logger.Warnf("check ssh failed. ip:%s, port:%d, app:%s, status:%s",
				s.Ip, s.Port, s.App, s.Status)
		}
		return sshErr
	} else {
		log.Logger.Infof("check ssh success. ip:%s, port:%d, app:%s", s.Ip, s.Port, s.App)
		s.Status = constvar.SSHCheckSuccess
	}
	return mysqlErr
}

// Serialization serialize sqlserver instance info
func (s *SqlserverDetectInstance) Serialization() ([]byte, error) {
	response := SqlserverDetectResponse{
		BaseDetectDBResponse: s.NewDBResponse(),
	}

	resByte, err := json.Marshal(&response)

	if err != nil {
		log.Logger.Errorf("sqlserver serialization failed. err:%s", err.Error())
		return []byte{}, err
	}

	return resByte, nil
}

// CheckSqlserver check whether sqlserver alive
func (s *SqlserverDetectInstance) CheckSqlserver(errChan chan error) {
	// Lock the mutex before accessing realDB, unexpected nil may lead to core dump
	s.dbMutex.Lock()
	defer s.dbMutex.Unlock()

	if s.realDB == nil {
		db, err := NewDbWorker(s.User, s.Pass, s.Ip, s.Port, s.Timeout)
		if err != nil {
			log.Logger.Warnf("open sqlserver failed. ip:%s, port:%d, err:%s", s.Ip, s.Port, err.Error())
			errChan <- err
			return
		}
		s.realDB = db
	}
	// defer close db session
	defer func() {
		if s.realDB != nil {
			if err := s.realDB.Db.Close(); err != nil {
				log.Logger.Warnf("close connect[%s#%d] failed:%s", s.Ip, s.Port, err.Error())
			}
			// need set to nil, otherwise agent would cache connection
			// and may cause connection leak
			s.realDB = nil
		}
	}()

	if _, err := s.realDB.ExecMore([]string{INSERT_SQL}); err != nil {
		log.Logger.Warnf("sqlserver replace heartbeat failed. ip:%s, port:%d, err:%s", s.Ip, s.Port, err.Error())
		errChan <- err
		return
	}

	errChan <- nil
}

// CheckSSH use ssh check whether machine alived
func (s *SqlserverDetectInstance) CheckSSH() error {
	touchFile := fmt.Sprintf("%s_%s_%d", s.SshInfo.Dest, "agent", s.Port)

	touchStr := fmt.Sprintf("echo __FILE_TOUCH_DONE__ > %s ", fmt.Sprintf("%s\\\\%s", SSH_TOUCH_DIR, touchFile))
	log.Logger.Debug(touchStr)
	if err := s.DoSSHForWindows(touchStr); err != nil {
		log.Logger.Warnf("do ssh failed. err:%s", err.Error())
		return err
	}
	return nil
}

// AgentNewSqlserverDetectInstance convert CmDBInstanceUrl response info to SqlserverDetectInstance
func AgentNewSqlserverDetectInstance(ins *SqlserverDetectInstanceInfoFromCmDB, conf *config.Config) *SqlserverDetectInstance {
	return &SqlserverDetectInstance{
		BaseDetectDB: dbutil.BaseDetectDB{
			Ip:             ins.Ip,
			Port:           ins.Port,
			App:            ins.App,
			DBType:         types.DBType(ins.MetaType),
			ReporterTime:   time.Unix(0, 0),
			ReportInterval: conf.AgentConf.ReportInterval + rand.Intn(20),
			Status:         constvar.DBCheckSuccess,
			Cluster:        ins.Cluster,
			ClusterType:    ins.ClusterType,
			SshInfo: dbutil.Ssh{
				Port:    conf.SSH.Port,
				User:    conf.SSH.SqlserverSSHUser,
				Pass:    conf.SSH.SqlserverSSHPass,
				Dest:    conf.SSH.Dest,
				Timeout: conf.SSH.Timeout,
			},
		},
		User:    conf.DBConf.Sqlserver.User,
		Pass:    conf.DBConf.Sqlserver.Pass,
		Timeout: conf.DBConf.Sqlserver.Timeout,
	}
}

// GMNewSqlserverDetectInstance GDM convert agent report info into sqlserverDetectInstance
func GMNewSqlserverDetectInstance(ins *SqlserverDetectResponse, conf *config.Config) *SqlserverDetectInstance {
	return &SqlserverDetectInstance{
		BaseDetectDB: dbutil.BaseDetectDB{
			Ip:             ins.DBIp,
			Port:           ins.DBPort,
			App:            ins.App,
			DBType:         types.DBType(ins.DBType),
			ReporterTime:   time.Unix(0, 0),
			ReportInterval: conf.AgentConf.ReportInterval + rand.Intn(20),
			Status:         types.CheckStatus(ins.Status),
			Cluster:        ins.Cluster,
			ClusterType:    ins.ClusterType,
			SshInfo: dbutil.Ssh{
				Port:    conf.SSH.Port,
				User:    conf.SSH.SqlserverSSHUser,
				Pass:    conf.SSH.SqlserverSSHPass,
				Dest:    conf.SSH.Dest,
				Timeout: conf.SSH.Timeout,
			},
		},
		User:    conf.DBConf.Sqlserver.User,
		Pass:    conf.DBConf.Sqlserver.Pass,
		Timeout: conf.DBConf.Sqlserver.Timeout,
	}
}
