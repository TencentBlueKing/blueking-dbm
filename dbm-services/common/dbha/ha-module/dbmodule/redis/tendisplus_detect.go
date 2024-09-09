package redis

import (
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"dbm-services/common/dbha/ha-module/client"
	"dbm-services/common/dbha/ha-module/config"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/log"
	"dbm-services/common/dbha/ha-module/util"
)

// TendisplusDetectInstance tendisplus detect instance
type TendisplusDetectInstance struct {
	RedisDetectBase
}

// Detection detect tendisplus instance
func (ins *TendisplusDetectInstance) Detection() error {
	err := ins.DoTendisDetection()
	if err == nil && ins.Status == constvar.DBCheckSuccess {
		log.Logger.Debugf("tendisplus check ok and return ok . %s#%d", ins.Ip, ins.Port)
		return nil
	}

	if err != nil {
		log.Logger.Errorf("tendisplus detect failed. %s#%d|%s:%s %+v", ins.Ip, ins.Port, ins.GetDBType(), ins.Pass, err)
		if ins.Status == constvar.RedisAuthFailed {
			return err
		}
	}

	sshErr := ins.CheckSSH()
	if sshErr != nil {
		if util.CheckSSHErrIsAuthFail(sshErr) {
			ins.Status = constvar.SSHAuthFailed
			log.Logger.Errorf("Tendis check ssh auth failed.ip:%s,port:%d,app:%s,status:%s",
				ins.Ip, ins.Port, ins.App, ins.Status)
		} else {
			ins.Status = constvar.SSHCheckFailed
			log.Logger.Errorf("Tendis check ssh failed.ip:%s,port:%d,app:%s,status:%s",
				ins.Ip, ins.Port, ins.App, ins.Status)
		}
		return sshErr
	} else {
		log.Logger.Debugf("Tendis check ssh success. ip:%s, port:%d, app:%s",
			ins.Ip, ins.Port, ins.App)
		ins.Status = constvar.SSHCheckSuccess
		return nil
	}
}

// DoTendisDetection execute detection for tendisplus instance
func (ins *TendisplusDetectInstance) DoTendisDetection() error {
	r := &client.RedisClient{}
	addr := fmt.Sprintf("%s:%d", ins.Ip, ins.Port)
	if ins.Pass == "" {
		ins.Pass = GetPassByClusterID(ins.GetClusterId(), string(ins.GetDBType()))
	}
	r.Init(addr, ins.Pass, ins.Timeout, 0)
	defer r.Close()

	rsp, err := r.Info()
	if err != nil {
		redisErr := fmt.Errorf("tendisplus exec detection failed, err:%s", err.Error())
		if util.CheckRedisErrIsAuthFail(err) {
			ins.Status = constvar.RedisAuthFailed
		} else {
			ins.Status = constvar.DBCheckFailed
		}
		return redisErr
	}

	rspInfo, ok := rsp.(string)
	if !ok {
		redisErr := fmt.Errorf("tendisplus info response type is not string")
		log.Logger.Errorf(redisErr.Error())
		ins.Status = constvar.DBCheckFailed
		return redisErr
	}

	if !strings.Contains(rspInfo, "redis_version:") {
		redisErr := fmt.Errorf("response un-find redis_version, rsp:%s", rspInfo)
		log.Logger.Errorf(redisErr.Error())
		ins.Status = constvar.DBCheckFailed
		return redisErr
	}

	role, err := ins.GetRole(rspInfo)
	if nil != err {
		redisErr := fmt.Errorf("response un-find role, rsp:%s", rspInfo)
		log.Logger.Errorf(redisErr.Error())
		ins.Status = constvar.DBCheckFailed
		return redisErr
	}

	if role == "master" {
		return ins.DoSetCheck()
	}
	ins.Status = constvar.DBCheckSuccess
	return nil
}

// Serialization serialize tendisplus instance
func (ins *TendisplusDetectInstance) Serialization() ([]byte, error) {
	response := RedisDetectResponse{
		BaseDetectDBResponse: ins.NewDBResponse(),
		Pass:                 ins.Pass,
	}

	resByte, err := json.Marshal(&response)
	if err != nil {
		log.Logger.Errorf("Tendisplus serialization failed. err:%s", err.Error())
		return []byte{}, err
	}
	return resByte, nil
}

// GetRole get role information
func (ins *TendisplusDetectInstance) GetRole(info string) (string, error) {
	beginPos := strings.Index(info, "role:")
	if beginPos < 0 {
		roleErr := fmt.Errorf("tendisplus rsp not contains role")
		log.Logger.Errorf(roleErr.Error())
		return "", roleErr
	}

	endPos := strings.Index(info[beginPos:], "\r\n")
	if endPos < 0 {
		roleErr := fmt.Errorf("tendisplus the substr is invalid,%s",
			info[beginPos:])
		log.Logger.Errorf(roleErr.Error())
		return "", roleErr
	}

	roleInfo := info[beginPos+len("role:") : beginPos+endPos]
	return roleInfo, nil
}

// DoSetCheck check set cmd is ok or not
func (ins *TendisplusDetectInstance) DoSetCheck() error {
	r := &client.RedisClient{}
	addr := fmt.Sprintf("%s:%d", ins.Ip, ins.Port)
	if ins.Pass == "" {
		ins.Pass = GetPassByClusterID(ins.GetClusterId(), string(ins.GetDBType()))
	}
	r.InitCluster(addr, ins.Pass, ins.Timeout)
	defer r.Close()

	keyFormat := "dbha:agent:%s"
	checkKey := fmt.Sprintf(keyFormat, ins.Ip)
	checkTime := time.Now().Format("2006-01-02 15:04:05")
	cmdArgv := []string{"SET", checkKey, checkTime}

	rsp, err := r.DoCommand(cmdArgv)
	if err != nil {
		redisErr := fmt.Errorf("tendisplus set value failed,err:%s", err.Error())
		log.Logger.Errorf(redisErr.Error())
		ins.Status = constvar.DBCheckFailed
		return redisErr
	}

	rspInfo, ok := rsp.(string)
	if !ok {
		redisErr := fmt.Errorf("tendisplus info response type is not string")
		log.Logger.Errorf(redisErr.Error())
		ins.Status = constvar.DBCheckFailed
		return redisErr
	}

	if strings.Contains(rspInfo, "OK") || strings.Contains(rspInfo, "MOVED") {
		ins.Status = constvar.DBCheckSuccess
		return nil
	} else {
		redisErr := fmt.Errorf("set check failed,rsp:%s", rspInfo)
		log.Logger.Errorf(redisErr.Error())
		ins.Status = constvar.DBCheckFailed
		return redisErr
	}
}

// ShowDetectionInfo show detect instance information
func (ins *TendisplusDetectInstance) ShowDetectionInfo() string {
	str := fmt.Sprintf("ip:%s, port:%d, status:%s, DBType:%s",
		ins.Ip, ins.Port, ins.Status, ins.DBType)
	return str
}

// NewTendisplusDetectInstance create tendisplus detect ins,
//
//	used by FetchDBCallback
func NewTendisplusDetectInstance(ins *RedisDetectInfoFromCmDB,
	conf *config.Config) *TendisplusDetectInstance {
	return &TendisplusDetectInstance{
		RedisDetectBase: *GetDetectBaseByInfo(ins, constvar.TendisplusMetaType, conf),
	}
}

// NewTendisplusDetectInstanceFromRsp create tendisplus detect ins,
//
//	used by gm/DeserializeCallback
func NewTendisplusDetectInstanceFromRsp(ins *RedisDetectResponse,
	conf *config.Config) *TendisplusDetectInstance {
	return &TendisplusDetectInstance{
		RedisDetectBase: *GetDetectBaseByRsp(ins, constvar.TendisplusMetaType, conf),
	}
}
