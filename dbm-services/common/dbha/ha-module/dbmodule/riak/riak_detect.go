package riak

import (
	"encoding/json"
	"fmt"
	"math/rand"
	"strings"
	"time"

	"dbm-services/common/dbha/ha-module/config"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/dbutil"
	"dbm-services/common/dbha/ha-module/log"
	"dbm-services/common/dbha/ha-module/types"
	"dbm-services/common/dbha/ha-module/util"

	"gorm.io/gorm"
)

// RiakDetectInstance riak instance detect struct
type RiakDetectInstance struct {
	dbutil.BaseDetectDB
	User    string
	Pass    string
	Timeout int
	realDB  *gorm.DB
}

// RiakDetectResponse riak instance response struct
type RiakDetectResponse struct {
	dbutil.BaseDetectDBResponse
}

// RiakDetectInstanceInfoFromCmDB riak instance detect struct in cmdb
type RiakDetectInstanceInfoFromCmDB struct {
	Ip          string
	Port        int
	App         string
	ClusterType string
	MetaType    string
	Cluster     string
}

// NewRiakDetectInstanceForAgent convert cmdb info to detect info
func NewRiakDetectInstanceForAgent(ins *RiakDetectInstanceInfoFromCmDB, conf *config.Config) *RiakDetectInstance {
	return &RiakDetectInstance{
		BaseDetectDB: dbutil.BaseDetectDB{
			Ip:             ins.Ip,
			Port:           ins.Port,
			App:            ins.App,
			DBType:         types.DBType(ins.ClusterType),
			ReporterTime:   time.Unix(0, 0),
			ReportInterval: conf.AgentConf.ReportInterval + rand.Intn(20),
			Status:         constvar.DBCheckSuccess,
			Cluster:        ins.Cluster,
		},
		Timeout: conf.DBConf.Riak.Timeout,
	}
}

// NewRiakDetectInstanceForGdm convert api response info into detect info
func NewRiakDetectInstanceForGdm(ins *RiakDetectResponse, dbType string, conf *config.Config) *RiakDetectInstance {
	return &RiakDetectInstance{
		BaseDetectDB: dbutil.BaseDetectDB{
			Ip:             ins.DBIp,
			Port:           ins.DBPort,
			App:            ins.App,
			DBType:         types.DBType(dbType),
			ReporterTime:   time.Unix(0, 0),
			ReportInterval: conf.AgentConf.ReportInterval + rand.Intn(20),
			Status:         types.CheckStatus(ins.Status),
			Cluster:        ins.Cluster,
		},
		Timeout: conf.DBConf.Riak.Timeout,
	}
}

// Detection TODO
// return error:
//
//	not nil: check db failed or do ssh failed
//	nil:     check db success
func (m *RiakDetectInstance) Detection() error {
	recheck := 1
	var riakErr error
	for i := 0; i <= recheck; i++ {
		// 设置缓冲为1防止没有接收者导致阻塞，即Detection已经超时返回
		errChan := make(chan error, 2)
		// 这里存在资源泄露的可能，因为不能主动kill掉协程，所以如果这个协程依然阻塞在连接riak，但是
		// 这个函数已经超时返回了，那么这个协程因为被阻塞一直没被释放，直到Riak连接超时，如果阻塞的时间
		// 大于下次探测该实例的时间间隔，则创建协程频率大于释放协程频率，可能会导致oom。可以考虑在Riak
		// 客户端连接设置超时时间来防止。
		go m.CheckRiak(errChan)
		select {
		case riakErr = <-errChan:
			if riakErr != nil {
				log.Logger.Warnf("check riak failed:%s. ip:%s, port:%d, app:%s",
					riakErr.Error(), m.Ip, m.Port, m.App)
				// 公共的gmm.go的Process函数仅当SSHCheckFailed状态是才会进入gqa、gcm的切换步骤
				// 不论是riak实例访问不了还是机器访问不了，都希望gcm更改实例状态为不可用
				// 因此 m.Status = constvar.SSHCheckFailed 替代 m.Status = constvar.DBCheckFailed
				m.Status = constvar.SSHCheckFailed
			} else {
				m.Status = constvar.DBCheckSuccess
				return nil
			}
		case <-time.After(time.Second * time.Duration(m.Timeout)):
			riakErr = fmt.Errorf("connect Riak timeout recheck:%d", recheck)
			log.Logger.Warnf(riakErr.Error())
			m.Status = constvar.SSHCheckFailed
		}
	}
	return riakErr
}

// CheckRiak check whether riak alive
func (m *RiakDetectInstance) CheckRiak(errChan chan error) {
	query := fmt.Sprintf(`curl -s --connect-timeout %d -m %d http://%s:%d/types/default/buckets/test/keys/1000`,
		m.Timeout, m.Timeout, m.Ip, constvar.RiakHttpPort)
	insert := fmt.Sprintf(
		`%s -X PUT -H 'Content-Type: application/json' -d '{name: "DBATeam", members: 31}'`, query)
	_, err := util.ExecShellCommand(false, insert)
	if err != nil {
		log.Logger.Warnf("riak insert heartbeat [ %s ] failed. ip:%s, port:%d, err:%s",
			insert, m.Ip, m.Port, err.Error())
		errChan <- err
		return
	}
	stdout, err := util.ExecShellCommand(false, query)
	if err != nil {
		log.Logger.Warnf("riak query heartbeat [ %s ] failed. ip:%s, port:%d, err:%s",
			query, m.Ip, m.Port, err.Error())
		errChan <- err
		return
	} else if strings.Contains(stdout, "not found") {
		err = fmt.Errorf("riak query heartbeat [ %s ] not found", query)
		log.Logger.Warnf("riak query heartbeat [ %s ] not found. ip:%s, port:%d, err:%s",
			query, m.Ip, m.Port, err.Error())
		errChan <- err
		return
	}
	errChan <- nil
}

// Serialization serialize riak instance info
func (m *RiakDetectInstance) Serialization() ([]byte, error) {
	response := RiakDetectResponse{
		BaseDetectDBResponse: m.NewDBResponse(),
	}

	resByte, err := json.Marshal(&response)

	if err != nil {
		log.Logger.Errorf("riak serialization failed. err:%s", err.Error())
		return []byte{}, err
	}

	return resByte, nil
}
