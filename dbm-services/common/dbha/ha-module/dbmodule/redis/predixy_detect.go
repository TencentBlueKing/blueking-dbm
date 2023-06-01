package redis

import (
	"encoding/json"
	"fmt"
	"strings"

	"dbm-services/common/dbha/ha-module/client"
	"dbm-services/common/dbha/ha-module/config"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/log"
	"dbm-services/common/dbha/ha-module/util"
)

// PredixyDetectInstance TODO
type PredixyDetectInstance struct {
	RedisDetectBase
}

// Detection TODO
func (ins *PredixyDetectInstance) Detection() error {
	err := ins.DoPredixyDetection()
	if err == nil && ins.Status == constvar.DBCheckSuccess {
		log.Logger.Debugf("Predixy check ok and return")
		return nil
	}

	if err != nil && ins.Status == constvar.AUTHCheckFailed {
		log.Logger.Errorf("Predixy auth failed,pass:%s,status:%s",
			ins.Pass, ins.Status)
		return err
	}

	sshErr := ins.CheckSSH()
	if sshErr != nil {
		if util.CheckSSHErrIsAuthFail(sshErr) {
			ins.Status = constvar.AUTHCheckFailed
			log.Logger.Errorf("Predixy check ssh auth failed.ip:%s,port:%d,app:%s,status:%s",
				ins.Ip, ins.Port, ins.App, ins.Status)
		} else {
			ins.Status = constvar.SSHCheckFailed
			log.Logger.Errorf("Predixy check ssh failed.ip:%s,port:%d,app:%s,status:%s",
				ins.Ip, ins.Port, ins.App, ins.Status)
		}
		return sshErr
	} else {
		log.Logger.Debugf("Predixy check ssh success. ip:%s, port:%d, app:%s",
			ins.Ip, ins.Port, ins.App)
		ins.Status = constvar.SSHCheckSuccess
		return nil
	}
}

// DoPredixyDetection do predixy detect
func (ins *PredixyDetectInstance) DoPredixyDetection() error {
	r := &client.RedisClient{}
	addr := fmt.Sprintf("%s:%d", ins.Ip, ins.Port)
	r.Init(addr, ins.Pass, ins.Timeout, 0)
	defer r.Close()

	rsp, err := r.Ping()
	if err != nil {
		predixyErr := fmt.Errorf("do predixy cmd err,err:%s", err.Error())
		if util.CheckRedisErrIsAuthFail(err) {
			ins.Status = constvar.AUTHCheckFailed
			log.Logger.Errorf("predixy detect auth failed,err:%s,status:%s",
				predixyErr.Error(), ins.Status)
		} else {
			ins.Status = constvar.DBCheckFailed
			log.Logger.Errorf("predixy detect failed,err:%s,status:%s",
				predixyErr.Error(), ins.Status)
		}
		return predixyErr
	}

	rspInfo, ok := rsp.(string)
	if !ok {
		predixyErr := fmt.Errorf("predixy ping response type is not string")
		log.Logger.Errorf(predixyErr.Error())
		ins.Status = constvar.DBCheckFailed
		return predixyErr
	}

	if strings.Contains(rspInfo, "PONG") || strings.Contains(rspInfo, "pong") {
		ins.Status = constvar.DBCheckSuccess
		return nil
	} else {
		predixyErr := fmt.Errorf("do predixy cmd err,rsp;%s", rspInfo)
		log.Logger.Errorf(predixyErr.Error())
		ins.Status = constvar.DBCheckFailed
		return predixyErr
	}
}

// Serialization TODO
func (ins *PredixyDetectInstance) Serialization() ([]byte, error) {
	response := RedisDetectResponse{
		BaseDetectDBResponse: ins.NewDBResponse(),
		Pass:                 ins.Pass,
	}

	resByte, err := json.Marshal(&response)
	if err != nil {
		log.Logger.Errorf("Predixy serialization failed. err:%s", err.Error())
		return []byte{}, err
	}
	return resByte, nil
}

// ShowDetectionInfo TODO
func (ins *PredixyDetectInstance) ShowDetectionInfo() string {
	str := fmt.Sprintf("ip:%s, port:%d, status:%s, DBType:%s",
		ins.Ip, ins.Port, ins.Status, ins.DBType)
	return str
}

// NewPredixyDetectInstance TODO
func NewPredixyDetectInstance(ins *RedisDetectInfoFromCmDB,
	conf *config.Config) *PredixyDetectInstance {
	return &PredixyDetectInstance{
		RedisDetectBase: *GetDetectBaseByInfo(ins, constvar.Predixy, conf),
	}
}

// NewPredixyDetectInstanceFromRsp TODO
func NewPredixyDetectInstanceFromRsp(ins *RedisDetectResponse,
	conf *config.Config) *PredixyDetectInstance {
	return &PredixyDetectInstance{
		RedisDetectBase: *GetDetectBaseByRsp(ins, constvar.Predixy, conf),
	}
}
