package redis

import (
	"encoding/json"

	"dbm-services/common/dbha/ha-module/config"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/dbutil"
	"dbm-services/common/dbha/ha-module/log"
)

// NewRedisInstanceByCmdb Agent通过CMDB获取的信息来生成需要探测的实例
func NewRedisInstanceByCmdb(instances []interface{},
	conf *config.Config) ([]dbutil.DataBaseDetect, error) {
	var (
		err          error
		unmarshalIns []*RedisDetectInfoFromCmDB
		ret          []dbutil.DataBaseDetect
	)

	unmarshalIns, err = UnMarshalRedisInstanceByCmdb(instances,
		constvar.RedisCluster, constvar.RedisMetaType)

	if err != nil {
		return nil, err
	}

	for _, uIns := range unmarshalIns {
		ret = append(ret, NewRedisDetectInstance(uIns, conf))
	}

	return ret, err
}

// DeserializeRedis 反序列化从Agent上报上来的故障实例
func DeserializeRedis(jsonInfo []byte,
	conf *config.Config) (dbutil.DataBaseDetect, error) {
	response := RedisDetectResponse{}
	err := json.Unmarshal(jsonInfo, &response)
	if err != nil {
		log.Logger.Errorf("json unmarshal failed. jsoninfo:\n%s\n, err:%s",
			string(jsonInfo), err.Error())
		return nil, err
	}
	ret := NewRedisDetectInstanceFromRsp(&response, conf)
	return ret, nil
}

// NewRedisSwitchInstance TODO
func NewRedisSwitchInstance(instances []interface{},
	conf *config.Config) ([]dbutil.DataBaseSwitch, error) {
	var err error
	var ret []dbutil.DataBaseSwitch
	for _, v := range instances {
		swIns, err := CreateRedisSwitchInfo(v, conf)
		if err != nil {
			log.Logger.Errorf("parse redis switch instance failed,err:%s",
				err.Error())
			continue
		}

		if swIns.MetaType != constvar.RedisMetaType {
			log.Logger.Errorf("Create redis switch while the metaType[%s] != %s",
				swIns.MetaType, constvar.RedisMetaType)
			continue
		}

		pw := RedisSwitch{
			RedisSwitchInfo: *swIns,
			Config:          conf,
		}

		passwd, err := GetInstancePassByCluster(
			constvar.TendisCache, pw.Cluster, conf,
		)
		if err != nil {
			log.Logger.Errorf("get redis switch passwd failed,err:%s,info:%s",
				err.Error(), pw.ShowSwitchInstanceInfo())
		} else {
			pw.Pass = passwd
		}
		ret = append(ret, &pw)
	}

	return ret, err
}
