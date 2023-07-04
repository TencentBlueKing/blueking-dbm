package mysql

import (
	"encoding/json"
	"fmt"
	"math/rand"
	"time"

	"dbm-services/common/dbha/ha-module/config"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/dbutil"
	"dbm-services/common/dbha/ha-module/log"
	"dbm-services/common/dbha/ha-module/types"
	"dbm-services/common/dbha/ha-module/util"

	"gorm.io/driver/mysql"
	"gorm.io/gorm"
)

const (
	replaceSql = "replace into infodba_schema.check_heartbeat(uid) values(1)"
)

// MySQLDetectInstance mysql instance detect struct
type MySQLDetectInstance struct {
	dbutil.BaseDetectDB
	User    string
	Pass    string
	Timeout int
	realDB  *gorm.DB
}

// MySQLDetectResponse mysql instance response struct
type MySQLDetectResponse struct {
	dbutil.BaseDetectDBResponse
}

// MySQLDetectInstanceInfoFromCmDB mysql instance detect struct in cmdb
type MySQLDetectInstanceInfoFromCmDB struct {
	Ip          string
	Port        int
	App         string
	ClusterType string
	MetaType    string
	Cluster     string
}

// NewMySQLDetectInstance1 convert cmdb info to detect info
func NewMySQLDetectInstance1(ins *MySQLDetectInstanceInfoFromCmDB, conf *config.Config) *MySQLDetectInstance {
	return &MySQLDetectInstance{
		BaseDetectDB: dbutil.BaseDetectDB{
			Ip:             ins.Ip,
			Port:           ins.Port,
			App:            ins.App,
			DBType:         types.DBType(fmt.Sprintf("%s:%s", ins.ClusterType, ins.MetaType)),
			ReporterTime:   time.Unix(0, 0),
			ReportInterval: conf.AgentConf.ReportInterval + rand.Intn(20),
			Status:         constvar.DBCheckSuccess,
			Cluster:        ins.Cluster,
			SshInfo: dbutil.Ssh{
				Port:    conf.SSH.Port,
				User:    conf.SSH.User,
				Pass:    conf.SSH.Pass,
				Dest:    conf.SSH.Dest,
				Timeout: conf.SSH.Timeout,
			},
		},
		User:    conf.DBConf.MySQL.User,
		Pass:    conf.DBConf.MySQL.Pass,
		Timeout: conf.DBConf.MySQL.Timeout,
	}
}

// NewMySQLDetectInstance2 convert api response info into detect info
func NewMySQLDetectInstance2(ins *MySQLDetectResponse, dbType string, conf *config.Config) *MySQLDetectInstance {
	return &MySQLDetectInstance{
		BaseDetectDB: dbutil.BaseDetectDB{
			Ip:             ins.DBIp,
			Port:           ins.DBPort,
			App:            ins.App,
			DBType:         types.DBType(dbType),
			ReporterTime:   time.Unix(0, 0),
			ReportInterval: conf.AgentConf.ReportInterval + rand.Intn(20),
			Status:         types.CheckStatus(ins.Status),
			Cluster:        ins.Cluster,
			SshInfo: dbutil.Ssh{
				Port:    conf.SSH.Port,
				User:    conf.SSH.User,
				Pass:    conf.SSH.Pass,
				Dest:    conf.SSH.Dest,
				Timeout: conf.SSH.Timeout,
			},
		},
		User:    conf.DBConf.MySQL.User,
		Pass:    conf.DBConf.MySQL.Pass,
		Timeout: conf.DBConf.MySQL.Timeout,
	}
}

// Detection TODO
// return error:
//
//	not nil: check db failed or do ssh failed
//	nil:     check db success
func (m *MySQLDetectInstance) Detection() error {
	recheck := 1
	var mysqlErr error
	needRecheck := true
	for i := 0; i <= recheck && needRecheck; i++ {
		// 设置缓冲为1防止没有接收者导致阻塞，即Detection已经超时返回
		errChan := make(chan error, 2)
		// 这里存在资源泄露的可能，因为不能主动kill掉协程，所以如果这个协程依然阻塞在连接mysql，但是
		// 这个函数已经超时返回了，那么这个协程因为被阻塞一直没被释放，直到MySQL连接超时，如果阻塞的时间
		// 大于下次探测该实例的时间间隔，则创建协程频率大于释放协程频率，可能会导致oom。可以考虑在MySQL
		// 客户端连接设置超时时间来防止。
		go m.CheckMySQL(errChan)
		select {
		case mysqlErr = <-errChan:
			if mysqlErr != nil {
				log.Logger.Warnf("check mysql failed. ip:%s, port:%d, app:%s", m.Ip, m.Port, m.App)
				m.Status = constvar.DBCheckFailed
				needRecheck = false
			} else {
				m.Status = constvar.DBCheckSuccess
				return nil
			}
		case <-time.After(time.Second * time.Duration(m.Timeout)):
			mysqlErr = fmt.Errorf("connect MySQL timeout recheck:%d", recheck)
			log.Logger.Warnf(mysqlErr.Error())
			m.Status = constvar.DBCheckFailed
		}
	}

	sshErr := m.CheckSSH()
	if sshErr != nil {
		if util.CheckSSHErrIsAuthFail(sshErr) {
			m.Status = constvar.AUTHCheckFailed
			log.Logger.Warnf("check ssh auth failed. ip:%s, port:%d, app:%s, status:%s",
				m.Ip, m.Port, m.App, m.Status)
		} else {
			m.Status = constvar.SSHCheckFailed
			log.Logger.Warnf("check ssh failed. ip:%s, port:%d, app:%s, status:%s",
				m.Ip, m.Port, m.App, m.Status)
		}
		return sshErr
	} else {
		log.Logger.Infof("check ssh success. ip:%s, port:%d, app:%s", m.Ip, m.Port, m.App)
		m.Status = constvar.SSHCheckSuccess
	}
	return mysqlErr
}

// CheckMySQL check whether mysql alive
func (m *MySQLDetectInstance) CheckMySQL(errChan chan error) {
	if m.realDB == nil {
		connParam := fmt.Sprintf("%s:%s@(%s:%d)/%s", m.User, m.Pass, m.Ip, m.Port, "infodba_schema")
		db, err := gorm.Open(mysql.Open(connParam), &gorm.Config{
			Logger: log.GormLogger,
		})
		if err != nil {
			log.Logger.Warnf("open mysql failed. ip:%s, port:%d, err:%s", m.Ip, m.Port, err.Error())
			errChan <- err
			return
		}
		// set connect timeout
		db.Set("gorm:connect_timeout", m.Timeout)
		m.realDB = db
	}

	defer func() {
		if m.realDB != nil {
			db, _ := m.realDB.DB()
			if err := db.Close(); err != nil {
				log.Logger.Warnf("close connect[%s#%d] failed:%s", m.Ip, m.Port, err.Error())
			}
			// need set to nil, otherwise agent would cache connection
			// and may cause connection leak
			m.realDB = nil
		}
	}()

	err := m.realDB.Exec(replaceSql).Error
	if err != nil {
		log.Logger.Warnf("mysql replace heartbeat failed. ip:%s, port:%d, err:%s", m.Ip, m.Port, err.Error())
		errChan <- err
		return
	}

	errChan <- nil
}

// CheckSSH use ssh check whether machine alived
func (m *MySQLDetectInstance) CheckSSH() error {
	touchFile := fmt.Sprintf("%s_%s_%d", m.SshInfo.Dest, util.LocalIp, m.Port)

	touchStr := fmt.Sprintf("touch %s && if [ -d \"/data1/dbha/\" ]; then touch /data1/dbha/%s ; fi "+
		"&& if [ -d \"/data/dbha/\" ]; then touch /data/dbha/%s ; fi", touchFile, touchFile, touchFile)

	if err := m.DoSSH(touchStr); err != nil {
		log.Logger.Warnf("do ssh failed. err:%s", err.Error())
		return err
	}
	return nil
}

// Serialization serialize mysql instance info
func (m *MySQLDetectInstance) Serialization() ([]byte, error) {
	response := MySQLDetectResponse{
		BaseDetectDBResponse: m.NewDBResponse(),
	}

	resByte, err := json.Marshal(&response)

	if err != nil {
		log.Logger.Errorf("mysql serialization failed. err:%s", err.Error())
		return []byte{}, err
	}

	return resByte, nil
}
