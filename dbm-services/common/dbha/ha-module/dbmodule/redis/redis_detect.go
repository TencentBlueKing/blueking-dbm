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

// RedisDetectInstance redis detect instance
type RedisDetectInstance struct {
	RedisDetectBase
}

// Detection detection api
func (ins *RedisDetectInstance) Detection() error {
	err := ins.DoRedisDetection()
	if err == nil && ins.Status == constvar.DBCheckSuccess {
		log.Logger.Debugf("redis check ok and return ok . %s#%d", ins.Ip, ins.Port)
		return nil
	}

	if err != nil && ins.Status == constvar.AUTHCheckFailed {
		log.Logger.Debugf("redis check auth failed.%s#%d|%s:%s %+v",
			ins.Ip, ins.Port, ins.GetType(), ins.Pass, err)
		return err
	}

	sshErr := ins.CheckSSH()
	if sshErr != nil {
		if util.CheckSSHErrIsAuthFail(sshErr) {
			ins.Status = constvar.AUTHCheckFailed
			log.Logger.Errorf("Redis check ssh auth failed.ip:%s,port:%d,app:%s,status:%s",
				ins.Ip, ins.Port, ins.App, ins.Status)
		} else {
			ins.Status = constvar.SSHCheckFailed
			log.Logger.Errorf("Redis check ssh failed.ip:%s,port:%d,app:%s,status:%s",
				ins.Ip, ins.Port, ins.App, ins.Status)
		}
		return sshErr
	} else {
		log.Logger.Debugf("Redis check ssh success. ip:%s, port:%d, app:%s",
			ins.Ip, ins.Port, ins.App)
		ins.Status = constvar.SSHCheckSuccess
		return nil
	}
}

// DoRedisDetection do detect action
func (ins *RedisDetectInstance) DoRedisDetection() error {
	r := &client.RedisClient{}
	addr := fmt.Sprintf("%s:%d", ins.Ip, ins.Port)
	if ins.Pass == "" {
		ins.Pass = GetPassByClusterID(ins.GetClusterId(), string(ins.GetType()))
	}
	r.Init(addr, ins.Pass, ins.Timeout, 0)
	defer r.Close()

	rsp, err := r.InfoV2("Replication")
	if err != nil {
		redisErr := fmt.Errorf("redis do cmd err,err: %s", err.Error())
		if util.CheckRedisErrIsAuthFail(err) {
			ins.Status = constvar.AUTHCheckFailed
		} else {
			ins.Status = constvar.DBCheckFailed
		}
		return redisErr
	}

	if _, ok := rsp["role"]; !ok {
		redisErr := fmt.Errorf("response un-find role, rsp %s:%+v", addr, rsp)
		ins.Status = constvar.DBCheckFailed
		return redisErr
	}

	if rsp["role"] == "master" {
		return ins.DoSetCheck(r)
	}

	ins.Status = constvar.DBCheckSuccess
	return nil
}

// Serialization do serialize
func (ins *RedisDetectInstance) Serialization() ([]byte, error) {
	response := RedisDetectResponse{
		BaseDetectDBResponse: ins.NewDBResponse(),
		Pass:                 ins.Pass,
	}

	resByte, err := json.Marshal(&response)
	if err != nil {
		log.Logger.Errorf("redis serialization failed. err:%s", err.Error())
		return []byte{}, err
	}
	return resByte, nil
}

// GetRole get role of instance
func (ins *RedisDetectInstance) GetRole(info string) (string, error) {
	beginPos := strings.Index(info, "role:")
	if beginPos < 0 {
		roleErr := fmt.Errorf("RedisCache rsp not contains role")
		log.Logger.Errorf(roleErr.Error())
		return "", roleErr
	}

	endPos := strings.Index(info[beginPos:], "\r\n")
	if endPos < 0 {
		roleErr := fmt.Errorf("RedisCache the substr is invalid,%s",
			info[beginPos:])
		log.Logger.Errorf(roleErr.Error())
		return "", roleErr
	}

	roleInfo := info[beginPos+len("role:") : beginPos+endPos]
	return roleInfo, nil
}

// DoSetCheck check redis set response
func (ins *RedisDetectInstance) DoSetCheck(r *client.RedisClient) error {
	keyFormat := "dbha:agent:%s"
	checkKey := fmt.Sprintf(keyFormat, ins.Ip)
	checkTime := time.Now().Format("2006-01-02 15:04:05")

	selectCmd := []string{"select", "0"}
	if ins.GetDetectType() == constvar.RedisCluster ||
		ins.GetDetectType() == constvar.TendisSSDCluster ||
		ins.GetDetectType() == constvar.RedisInstance {
		selectCmd = []string{"select", "1"}
	}
	selRsp, serr := r.DoCommand(selectCmd)
	if serr != nil {
		log.Logger.Warnf("do select failed %+v ,%s:%s#%d", serr, ins.Cluster, ins.Ip, ins.Port)
		return serr
	}

	selInfo, ok := selRsp.(string)
	if !ok {
		redisErr := fmt.Errorf("redis select rsp type is not string")
		log.Logger.Errorf(redisErr.Error())
		ins.Status = constvar.DBCheckFailed
		return redisErr
	}

	if !strings.Contains(selInfo, "OK") {
		redisErr := fmt.Errorf("redis select rsp[%s] type is not ok", selInfo)
		log.Logger.Errorf(redisErr.Error())
		ins.Status = constvar.DBCheckFailed
		return redisErr
	}

	cmdArgv := []string{"SET", checkKey, checkTime}
	rsp, err := r.DoCommand(cmdArgv)
	if err != nil {
		redisErr := fmt.Errorf("response un-find role, rsp:%s", rsp)
		log.Logger.Errorf(redisErr.Error())
		ins.Status = constvar.DBCheckFailed
		return redisErr
	}

	rspInfo, ok := rsp.(string)
	if !ok {
		redisErr := fmt.Errorf("redis info response type is not string")
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
func (ins *RedisDetectInstance) ShowDetectionInfo() string {
	str := fmt.Sprintf("ip:%s, port:%d, status:%s, DBType:%s",
		ins.Ip, ins.Port, ins.Status, ins.DBType)
	return str
}

// NewRedisDetectInstance create Redis detect ins,
//
//	used by FetchDBCallback
func NewRedisDetectInstance(ins *RedisDetectInfoFromCmDB,
	metaType string, conf *config.Config) *RedisDetectInstance {
	return &RedisDetectInstance{
		RedisDetectBase: *GetDetectBaseByInfo(ins, metaType, conf),
	}
}

// NewRedisDetectInstanceFromRsp create Redis detect ins,
//
//	used by gm/DeserializeCallback
func NewRedisDetectInstanceFromRsp(ins *RedisDetectResponse,
	metaType string, conf *config.Config) *RedisDetectInstance {
	return &RedisDetectInstance{
		RedisDetectBase: *GetDetectBaseByRsp(ins, metaType, conf),
	}
}
