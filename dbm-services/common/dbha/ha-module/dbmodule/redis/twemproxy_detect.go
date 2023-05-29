package redis

import (
	"dbm-services/common/dbha/ha-module/client"
	"dbm-services/common/dbha/ha-module/config"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/log"
	"dbm-services/common/dbha/ha-module/util"
	"encoding/json"
	"fmt"
	"strings"
)

// TwemproxyDetectInstance TODO
type TwemproxyDetectInstance struct {
	RedisDetectBase
}

// Detection TODO
func (ins *TwemproxyDetectInstance) Detection() error {
	err := ins.DoTwemproxyDetection()
	if err == nil && ins.Status == constvar.DBCheckSuccess {
		log.Logger.Debugf("Twemproxy check ok and return")
		return nil
	}

	if err != nil && ins.Status == constvar.AUTHCheckFailed {
		log.Logger.Errorf("Twemproxy auth failed,pass:%s,status:%s",
			ins.Pass, ins.Status)
		return err
	}

	sshErr := ins.CheckSSH()
	if sshErr != nil {
		if util.CheckSSHErrIsAuthFail(sshErr) {
			ins.Status = constvar.AUTHCheckFailed
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
	r.Init(addr, ins.Pass, ins.Timeout, 0)
	defer r.Close()

	rsp, err := r.Type("twemproxy_mon")
	if err != nil {
		twemproxyErr = fmt.Errorf("do twemproxy cmd err,err: %s,info;%s",
			err.Error(), ins.ShowDetectionInfo())
		if util.CheckRedisErrIsAuthFail(err) {
			ins.Status = constvar.AUTHCheckFailed
			log.Logger.Errorf("tendisplus detect auth failed,err:%s,status:%s",
				twemproxyErr.Error(), ins.Status)
		} else {
			ins.Status = constvar.DBCheckFailed
			log.Logger.Errorf("tendisplus detect failed,err:%s,status:%s",
				twemproxyErr.Error(), ins.Status)
		}
		return twemproxyErr
	}

	rspInfo, ok := rsp.(string)
	if !ok {
		twemproxyErr := fmt.Errorf("redis info response type is not string")
		log.Logger.Errorf(twemproxyErr.Error())
		ins.Status = constvar.DBCheckFailed
		return twemproxyErr
	}

	log.Logger.Infof("Twemproxy detection response:%s", rspInfo)
	if strings.Contains(rspInfo, "none") {
		ins.Status = constvar.DBCheckSuccess
		return nil
	} else {
		twemproxyErr = fmt.Errorf("twemproxy exec detection failed,rsp:%s,info:%s",
			rspInfo, ins.ShowDetectionInfo())
		log.Logger.Errorf(twemproxyErr.Error())
		ins.Status = constvar.DBCheckFailed
		return twemproxyErr
	}
}

// Serialization TODO
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

// ShowDetectionInfo TODO
func (ins *TwemproxyDetectInstance) ShowDetectionInfo() string {
	str := fmt.Sprintf("ip:%s, port:%d, status:%s, DBType:%s",
		ins.Ip, ins.Port, ins.Status, ins.DBType)
	return str
}

// NewTwemproxyDetectInstance TODO
func NewTwemproxyDetectInstance(ins *RedisDetectInfoFromCmDB,
	conf *config.Config) *TwemproxyDetectInstance {
	return &TwemproxyDetectInstance{
		RedisDetectBase: *GetDetectBaseByInfo(ins, constvar.Twemproxy, conf),
	}
}

// NewTwemproxyDetectInstanceFromRsp TODO
func NewTwemproxyDetectInstanceFromRsp(ins *RedisDetectResponse,
	conf *config.Config) *TwemproxyDetectInstance {
	return &TwemproxyDetectInstance{
		RedisDetectBase: *GetDetectBaseByRsp(ins, constvar.Twemproxy, conf),
	}
}
