package mongodb

import (
	"context"
	"encoding/json"
	"fmt"
	"math/rand"
	"regexp"
	"time"

	"dbm-services/common/dbha/ha-module/config"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/dbutil"
	"dbm-services/common/dbha/ha-module/log"
	"dbm-services/common/dbha/ha-module/types"
	"dbm-services/common/dbha/ha-module/util"

	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
)

// MongosDetectInstance mongos instance detect struct
type MongosDetectInstance struct {
	dbutil.BaseDetectDB
	User    string
	Pass    string
	Timeout int
}

var mongoRegex *regexp.Regexp

func init() {
	// like 2.4.12 3.0.5 6.0.6
	mongoRegex = regexp.MustCompile(`^[0-9]+.[0-9]+.[0-9]+`)
}

// MongosDetectResponse mongos instance response struct
type MongosDetectResponse struct {
	dbutil.BaseDetectDBResponse
}

// MongosDetectInstanceInfoFromCmDB mongos instance detect struct in cmdb
type MongosDetectInstanceInfoFromCmDB struct {
	Ip          string
	Port        int
	App         string
	ClusterType string
	MetaType    string
	Cluster     string
}

// NewMongosDetectInstanceForAgent convert cmdb info to detect info
func NewMongosDetectInstanceForAgent(ins *MongosDetectInstanceInfoFromCmDB,
	conf *config.Config) *MongosDetectInstance {
	return &MongosDetectInstance{
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
		Timeout: conf.DBConf.MongoDB.Timeout,
	}
}

// NewMongosDetectInstanceForGdm convert api response info into detect info
func NewMongosDetectInstanceForGdm(ins *MongosDetectResponse,
	dbType string, conf *config.Config) *MongosDetectInstance {
	return &MongosDetectInstance{
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
		Timeout: conf.DBConf.MongoDB.Timeout,
	}
}

// Detection mongo 存活探测 PING （5s超时）
func (m *MongosDetectInstance) Detection() (err error) {
	if err = m.CheckMongo(); err != nil {
		m.Status = constvar.DBCheckFailed
		log.Logger.Debugf("mongos check instance failed . %s#%d:%+v", m.Ip, m.Port, err)

		if sshErr := m.CheckSSH(); sshErr != nil {
			if util.CheckSSHErrIsAuthFail(sshErr) {
				m.Status = constvar.SSHAuthFailed
				log.Logger.Errorf("mongos check ssh auth failed.ip:%s,port:%d,app:%s,status:%s",
					m.Ip, m.Port, m.App, m.Status)
			} else {
				m.Status = constvar.SSHCheckFailed
				log.Logger.Errorf("mongos check ssh failed.ip:%s,port:%d,app:%s,status:%s",
					m.Ip, m.Port, m.App, m.Status)
			}
			return sshErr
		}

		log.Logger.Debugf("mongos check ssh success. ip:%s, port:%d, app:%s", m.Ip, m.Port, m.App)
		m.Status = constvar.SSHCheckSuccess
		return nil
	}

	m.Status = constvar.DBCheckSuccess
	log.Logger.Infof("mongos check instance success . %s#%d", m.Ip, m.Port)
	return nil
}

// MongosDetectInstance check whether mongo alive
func (m *MongosDetectInstance) CheckMongo() error {
	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(m.Timeout)*time.Second)
	defer cancel()
	//	uri := "mongodb://user:****@localhost:27017"
	uri := fmt.Sprintf("mongodb://%s:%d", m.Ip, m.Port)
	client, err := mongo.Connect(ctx, options.Client().ApplyURI(uri))
	if err != nil {
		log.Logger.Warnf("connect mongo failed. %s#%d, err:%s", m.Ip, m.Port, err.Error())
		return err
	}
	// release connection.
	defer func() {
		if err = client.Disconnect(ctx); err != nil {
			log.Logger.Warnf("close mongo connection failed. %s#%d, err:%s", m.Ip, m.Port, err.Error())
		}
	}()

	// if err = client.Ping(ctx, readpref.Primary()); err != nil {
	// 	log.Logger.Errorf("ping mongo [ %s ] failed. ip:%s, port:%d, err:%s", m.Ip, m.Port, err.Error())
	// 	return err
	// }
	var buildInfoDoc bson.M
	if err := client.Database("dbha").RunCommand(ctx,
		bson.D{bson.E{Key: "buildInfo", Value: 1}}).Decode(&buildInfoDoc); err != nil {
		log.Logger.Errorf("failed to run buildInfo command: %s#%d, err:%+v", m.Ip, m.Port, err)
		return err
	}

	mong_version, _ := buildInfoDoc["version"].(string)
	if !mongoRegex.MatchString(mong_version) {
		return fmt.Errorf("mongos check failed:%s", mong_version)
	}

	return nil
}

// Serialization serialize mongos instance info
func (m *MongosDetectInstance) Serialization() ([]byte, error) {
	response := MongosDetectResponse{
		BaseDetectDBResponse: m.NewDBResponse(),
	}

	resByte, err := json.Marshal(&response)

	if err != nil {
		log.Logger.Errorf("mongo serialization failed. err:%s", err.Error())
		return []byte{}, err
	}

	return resByte, nil
}

// CheckSSH mongo do ssh check
func (m *MongosDetectInstance) CheckSSH() error {
	touchFile := fmt.Sprintf("%s_%s_%d", m.SshInfo.Dest, "agent", m.Port)

	touchStr := fmt.Sprintf("touch %s && if [ -d \"/data1/dbha\" ]; then touch /data1/dbha/%s ; fi "+
		"&& if [ -d \"/data/dbha\" ]; then touch /data/dbha/%s ; fi", touchFile, touchFile, touchFile)

	if err := m.DoSSH(touchStr); err != nil {
		log.Logger.Errorf("MongoDetection do ssh failed. err:%s", err.Error())
		return err
	}
	return nil
}
