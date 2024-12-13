package redis

import (
	"encoding/json"
	"fmt"
	"time"

	"dbm-services/common/dbha/ha-module/client"
	"dbm-services/common/dbha/ha-module/config"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/log"
	"dbm-services/common/dbha/ha-module/util"
)

// TwemproxyDetectInstance twemproxy detect instance
type TwemproxyDetectInstance struct {
	RedisDetectBase
}

// Detection detect twemproxy instance
func (ins *TwemproxyDetectInstance) Detection() error {
	startTime := time.Now().Unix()
	err := ins.DoTwemproxyDetection()
	log.Logger.Debugf("finsh detect instance [%s#%d] ,cost: %d", ins.Ip, ins.Port, time.Now().Unix()-startTime)
	if err == nil && ins.Status == constvar.DBCheckSuccess {
		return nil
	}

	if err != nil {
		log.Logger.Errorf("Twemproxy detect failed. %s#%d|%s:%s %+v", ins.Ip, ins.Port, ins.GetDBType(), ins.Pass, err)
		if ins.Status == constvar.RedisAuthFailed {
			return err
		}
	}

	sshErr := ins.CheckSSH()
	if sshErr != nil {
		if util.CheckSSHErrIsAuthFail(sshErr) {
			ins.Status = constvar.SSHAuthFailed
			log.Logger.Errorf("Twemproxy check ssh auth failed.ip:%s,port:%d,app:%s,status:%s",
				ins.Ip, ins.Port, ins.App, ins.Status)
		} else {
			ins.Status = constvar.SSHCheckFailed
			log.Logger.Errorf("Twemproxy check ssh failed.ip:%s,port:%d,app:%s,status:%s",
				ins.Ip, ins.Port, ins.App, ins.Status)
		}
		return sshErr
	} else {
		log.Logger.Debugf("Twemproxy check ssh success. ip:%s, port:%d, app:%s",
			ins.Ip, ins.Port, ins.App)
		ins.Status = constvar.SSHCheckSuccess
		return nil
	}
}

// DoTwemproxyDetection execte detection for twemproxy instance
func (ins *TwemproxyDetectInstance) DoTwemproxyDetection() error {
	var twemproxyErr error
	r := &client.RedisClient{}
	addr := fmt.Sprintf("%s:%d", ins.Ip, ins.Port)
	if ins.Pass == "" {
		ins.Pass = GetPassByClusterID(ins.GetClusterId(), string(ins.GetDBType()))
	}
	r.Init(addr, ins.Pass, ins.Timeout, 0)
	defer r.Close()

	if _, err := r.Type("twemproxy_mon"); err != nil {
		twemproxyErr = fmt.Errorf("do twemproxy cmd failed,err: %s", err)
		if util.CheckRedisErrIsAuthFail(err) {
			ins.Status = constvar.RedisAuthFailed
		} else {
			ins.Status = constvar.DBCheckFailed
		}
		return twemproxyErr
	}

	return nil
}

// Serialization serialize detect instance
func (ins *TwemproxyDetectInstance) Serialization() ([]byte, error) {
	response := RedisDetectResponse{
		BaseDetectDBResponse: ins.NewDBResponse(),
		Pass:                 ins.Pass,
	}

	resByte, err := json.Marshal(&response)
	if err != nil {
		log.Logger.Errorf("twemproxy serialization failed. err:%s", err.Error())
		return []byte{}, err
	}
	return resByte, nil
}

// ShowDetectionInfo show detect instance information
func (ins *TwemproxyDetectInstance) ShowDetectionInfo() string {
	str := fmt.Sprintf("ip:%s, port:%d, status:%s, DBType:%s",
		ins.Ip, ins.Port, ins.Status, ins.DBType)
	return str
}

// NewTwemproxyDetectInstance create twemproxy detect ins,
//
//	used by FetchDBCallback
func NewTwemproxyDetectInstance(ins *RedisDetectInfoFromCmDB,
	conf *config.Config) *TwemproxyDetectInstance {
	return &TwemproxyDetectInstance{
		RedisDetectBase: *GetDetectBaseByInfo(ins, constvar.TwemproxyMetaType, conf),
	}
}

// NewTwemproxyDetectInstanceFromRsp create twemproxy detect ins,
//
//	used by gm/DeserializeCallback
func NewTwemproxyDetectInstanceFromRsp(ins *RedisDetectResponse,
	conf *config.Config) *TwemproxyDetectInstance {
	return &TwemproxyDetectInstance{
		RedisDetectBase: *GetDetectBaseByRsp(ins, constvar.TwemproxyMetaType, conf),
	}
}
