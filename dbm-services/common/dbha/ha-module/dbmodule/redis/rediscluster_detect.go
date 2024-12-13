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

// RedisClusterDetectInstance tendisplus detect instance
type RedisClusterDetectInstance struct {
	RedisDetectBase
}

// Detection detect tendisplus instance
func (ins *RedisClusterDetectInstance) Detection() error {
	startTime := time.Now().Unix()
	err := ins.DoTendisDetection()
	log.Logger.Debugf("finsh detect instance [%s#%d] ,cost: %d", ins.Ip, ins.Port, time.Now().Unix()-startTime)
	if err == nil && ins.Status == constvar.DBCheckSuccess {
		return nil
	}

	if err != nil {
		log.Logger.Errorf("redisC detect failed. %s#%d|%s:%s %+v", ins.Ip, ins.Port, ins.GetDBType(), ins.Pass, err)
		if ins.Status == constvar.RedisAuthFailed {
			return err
		}
	}

	sshErr := ins.CheckSSH()
	if sshErr != nil {
		if util.CheckSSHErrIsAuthFail(sshErr) {
			ins.Status = constvar.SSHAuthFailed
			log.Logger.Errorf("redisC check ssh auth failed.ip:%s,port:%d,app:%s,status:%s",
				ins.Ip, ins.Port, ins.App, ins.Status)
		} else {
			ins.Status = constvar.SSHCheckFailed
			log.Logger.Errorf("redisC check ssh failed.ip:%s,port:%d,app:%s,status:%s",
				ins.Ip, ins.Port, ins.App, ins.Status)
		}
		return sshErr
	} else {
		log.Logger.Debugf("redisC check ssh success. ip:%s, port:%d, app:%s",
			ins.Ip, ins.Port, ins.App)
		ins.Status = constvar.SSHCheckSuccess
		return nil
	}
}

// DoTendisDetection execute detection for tendisplus instance
func (ins *RedisClusterDetectInstance) DoTendisDetection() error {
	r := &client.RedisClient{}
	addr := fmt.Sprintf("%s:%d", ins.Ip, ins.Port)
	if ins.Pass == "" {
		ins.Pass = GetPassByClusterID(ins.GetClusterId(), string(ins.GetDBType()))
	}
	r.Init(addr, ins.Pass, ins.Timeout, 0)
	defer r.Close()

	infoMap, err := r.InfoV2("Replication")
	if err != nil {
		redisErr := fmt.Errorf("redisC exec detection failed,err:%s", err.Error())
		if util.CheckRedisErrIsAuthFail(err) {
			ins.Status = constvar.RedisAuthFailed
		} else {
			ins.Status = constvar.DBCheckFailed
		}
		return redisErr
	}

	if infoMap["role"] == "master" {
		return ins.DoSetCheck(r)
	}

	ins.Status = constvar.DBCheckSuccess
	return nil
}

// Serialization serialize tendisplus instance
func (ins *RedisClusterDetectInstance) Serialization() ([]byte, error) {
	response := RedisDetectResponse{
		BaseDetectDBResponse: ins.NewDBResponse(),
		Pass:                 ins.Pass,
	}

	resByte, err := json.Marshal(&response)
	if err != nil {
		log.Logger.Errorf("redisC serialization failed. err:%s", err.Error())
		return []byte{}, err
	}
	return resByte, nil
}

// GetRole get role information
func (ins *RedisClusterDetectInstance) GetRole(info string) (string, error) {
	beginPos := strings.Index(info, "role:")
	if beginPos < 0 {
		roleErr := fmt.Errorf("redisC rsp not contains role")
		log.Logger.Errorf(roleErr.Error())
		return "", roleErr
	}

	endPos := strings.Index(info[beginPos:], "\r\n")
	if endPos < 0 {
		roleErr := fmt.Errorf("redisC the substr is invalid,%s",
			info[beginPos:])
		log.Logger.Errorf(roleErr.Error())
		return "", roleErr
	}

	roleInfo := info[beginPos+len("role:") : beginPos+endPos]
	return roleInfo, nil
}

// DoSetCheck check set cmd is ok or not
func (ins *RedisClusterDetectInstance) DoSetCheck(r *client.RedisClient) error {
	checkKey, checkTime := fmt.Sprintf("dbha:agent:%s", ins.Ip), time.Now().Format("2006-01-02 15:04:05")
	cmdArgv := []string{"SET", checkKey, checkTime}

	rsp, err := r.DoCommand(cmdArgv)
	if err != nil {
		ins.Status = constvar.DBCheckFailed
		return fmt.Errorf("redisC set value failed,err:%s", err.Error())
	}

	rspInfo, _ := rsp.(string)
	if strings.Contains(rspInfo, "OK") || strings.Contains(rspInfo, "MOVED") {
		ins.Status = constvar.DBCheckSuccess
		return nil
	}

	ins.Status = constvar.DBCheckFailed
	return fmt.Errorf("set check failed,rsp:%s", rspInfo)
}

// ShowDetectionInfo show detect instance information
func (ins *RedisClusterDetectInstance) ShowDetectionInfo() string {
	str := fmt.Sprintf("ip:%s, port:%d, status:%s, DBType:%s", ins.Ip, ins.Port, ins.Status, ins.DBType)
	return str
}

// NewRedisClusterDetectInstance create tendisplus detect ins,	used by FetchDBCallback
func NewRedisClusterDetectInstance(ins *RedisDetectInfoFromCmDB, conf *config.Config) *RedisClusterDetectInstance {
	return &RedisClusterDetectInstance{
		RedisDetectBase: *GetDetectBaseByInfo(ins, constvar.PredixyRedisCluster, conf),
	}
}

// NewRedisClusterDetectInstanceFromRsp create tendisplus detect ins,	used by gm/DeserializeCallback
func NewRedisClusterDetectInstanceFromRsp(ins *RedisDetectResponse, conf *config.Config) *RedisClusterDetectInstance {
	return &RedisClusterDetectInstance{
		RedisDetectBase: *GetDetectBaseByRsp(ins, constvar.PredixyRedisCluster, conf),
	}
}
