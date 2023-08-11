package redis

import (
	"encoding/json"

	"dbm-services/common/dbha/ha-module/config"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/dbutil"
	"dbm-services/common/dbha/ha-module/log"
)

// NewTendisplusInstanceByCmdb Agent通过CMDB获取的信息来生成需要探测的实例
func NewTendisplusInstanceByCmdb(instances []interface{},
	conf *config.Config) ([]dbutil.DataBaseDetect, error) {
	var (
		err          error
		unmarshalIns []*RedisDetectInfoFromCmDB
		ret          []dbutil.DataBaseDetect
	)

	unmarshalIns, err = UnMarshalRedisInstanceByCmdb(instances,
		constvar.TendisplusCluster, constvar.TendisplusMetaType)

	if err != nil {
		return nil, err
	}

	for _, uIns := range unmarshalIns {
		ret = append(ret, NewTendisplusDetectInstance(uIns, conf))
	}

	return ret, err
}

// DeserializeTendisplus 反序列化从Agent上报上来的故障实例
func DeserializeTendisplus(jsonInfo []byte,
	conf *config.Config) (dbutil.DataBaseDetect, error) {
	response := RedisDetectResponse{}
	err := json.Unmarshal(jsonInfo, &response)
	if err != nil {
		log.Logger.Errorf("json unmarshal failed. jsoninfo:\n%s\n, err:%s",
			string(jsonInfo), err.Error())
		return nil, err
	}
	ret := NewTendisplusDetectInstanceFromRsp(&response, conf)
	return ret, nil
}

// NewTendisplusSwitchInstance TODO
func NewTendisplusSwitchInstance(instances []interface{},
	conf *config.Config) ([]dbutil.DataBaseSwitch, error) {
	var err error
	var ret []dbutil.DataBaseSwitch
	for _, v := range instances {
		swIns, err := CreateRedisSwitchInfo(v, conf)
		if err != nil {
			log.Logger.Errorf("parse tendisplus switch instance failed,err:%s",
				err.Error())
			continue
		}

		if swIns.MetaType != constvar.TendisplusMetaType {
			log.Logger.Errorf("Create tendisplus switch while the metaType[%s] != %s",
				swIns.MetaType, constvar.TendisplusMetaType)
			continue
		}

		pw := TendisplusSwitch{
			RedisSwitchInfo: *swIns,
		}

		passwd, err := GetInstancePassByCluster(
			constvar.Tendisplus, pw.Cluster, conf,
		)
		if err != nil {
			log.Logger.Errorf("get tendisplus switch passwd failed,err:%s,info:%s",
				err.Error(), pw.ShowSwitchInstanceInfo())
		} else {
			pw.Pass = passwd
		}

		ret = append(ret, &pw)
	}

	return ret, err
}
