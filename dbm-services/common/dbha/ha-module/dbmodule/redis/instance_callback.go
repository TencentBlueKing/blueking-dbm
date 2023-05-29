package redis

import (
	"encoding/json"
	"fmt"

	"dbm-services/common/dbha/ha-module/config"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/dbutil"
	"dbm-services/common/dbha/ha-module/log"
)

// RedisInstanceNewIns Agent通过CMDB获取的信息来生成需要探测的实例
func RedisInstanceNewIns(instances []interface{}, conf *config.Config) ([]dbutil.DataBaseDetect, error) {
	var (
		err          error
		unmarshalIns []*RedisDetectInfoFromCmDB
		redisIns     []dbutil.DataBaseDetect
	)

	// marshal 2 redis_instance struct.
	unmarshalIns, err = UnMarshalRedisInstanceByCmdb(instances, constvar.RedisInstance)
	if err != nil {
		log.Logger.Errorf("RedisInstance UnMarshal failed,%s,err:%s", constvar.RedisInstance, err.Error())
		return nil, err
	}

	for _, uIns := range unmarshalIns {
		if uIns.ClusterType != constvar.RedisInstance {
			log.Logger.Warnf("ignore 4 : instance cluster_type not redis_instance but:%+v", uIns)
			continue
		}
		redisIns = append(redisIns, NewRedisDetectInstance(uIns, constvar.RedisMetaType, conf))
	}

	// get redis instance passwd
	if len(redisIns) > 0 {
		count, _ := GetInstancePass(redisIns, conf)
		if count != len(redisIns) {
			log.Logger.Errorf("RedisInstance redis passwd part failed,succ:%d,total:%d", count, len(redisIns))
		}
	}

	return redisIns, err
}

// RedisInstanceDeserialize 反序列化从Agent上报上来的故障实例
func RedisInstanceDeserialize(jsonInfo []byte, conf *config.Config) (dbutil.DataBaseDetect, error) {
	response := RedisDetectResponse{}
	if err := json.Unmarshal(jsonInfo, &response); err != nil {
		log.Logger.Errorf("json unmarshal failed. jsoninfo:%+v, err:%s", response, err.Error())
		return nil, err
	}

	// cluster_type should be equal to RedisInstance
	if response.ClusterType != constvar.RedisInstance {
		unmatchErr := fmt.Errorf("cluster unmatch %s<>%s", response.ClusterType, constvar.RedisInstance)
		log.Logger.Errorf("redisInstance Deserialize. %s", unmatchErr.Error())
		return nil, unmatchErr
	}

	// create detect instance by machine_type
	if response.DBType == constvar.RedisMetaType {
		return NewRedisDetectInstanceFromRsp(&response, constvar.RedisMetaType, conf), nil
	}

	return nil, fmt.Errorf("redisInstance meta_type not support,%s", response.DBType)
}

// RedisInstanceNewSwitchIns create redis cluster switch ins
func RedisInstanceNewSwitchIns(instances []interface{}, conf *config.Config) ([]dbutil.DataBaseSwitch, error) {
	var err error
	var ret []dbutil.DataBaseSwitch
	for _, v := range instances {
		// get cluster_type and meta type from instance information
		clusterType, metaType, err := GetClusterAndMetaFromIns(v)
		if err != nil {
			log.Logger.Errorf("redis ins lack cluster and meta info,%v,err:%s", v, err.Error())
			continue
		}

		// check cluster_type is equal to RedisInstance
		if clusterType != constvar.RedisInstance {
			continue
		}

		// create instance by machine_type
		if metaType == constvar.RedisMetaType || metaType == constvar.TendisSSDMetaType {
			pw, err := NewInstanceSwitch(v, conf)
			if err != nil {
				log.Logger.Errorf("new redis switch ins failed:%s", err.Error())
				continue
			}
			ret = append(ret, pw)
		} else {
			log.Logger.Errorf("redis cluster[%s] not fit meta[%s]", clusterType, metaType)
			continue
		}
	}
	return ret, err
}

// NewRedisSwitchIns create redis switch instance
func NewInstanceSwitch(instance interface{}, conf *config.Config) (dbutil.DataBaseSwitch, error) {
	swIns, err := CreateRedisSwitchInfo(instance, conf)
	if err != nil {
		log.Logger.Errorf("parse redis switch instance failed,err:%s",
			err.Error())
		return nil, err
	}

	// check machine_type is equal to tendiscache
	if swIns.MetaType != constvar.RedisMetaType &&
		swIns.MetaType != constvar.TendisSSDMetaType {
		log.Logger.Errorf("create redis switch err, while the metaType[%s] != %s and %s",
			swIns.MetaType, constvar.RedisMetaType, constvar.TendisSSDMetaType)
		return nil, err
	}

	pw := RedisSwitch{
		RedisSwitchInfo: *swIns,
		Config:          conf,
		IsSkipSwitch:    false,
	}

	// get the password of redis switch instance
	passwd, err := GetInstancePassByClusterId(swIns.MetaType, pw.ClusterId, conf)
	if err != nil {
		log.Logger.Errorf("get redis switch passwd failed,err:%s,info:%s",
			err.Error(), pw.ShowSwitchInstanceInfo())
	} else {
		pw.Pass = passwd
	}

	return &pw, nil
}
