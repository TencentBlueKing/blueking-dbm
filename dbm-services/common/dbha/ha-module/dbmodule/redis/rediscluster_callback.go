package redis

import (
	"encoding/json"
	"fmt"

	"dbm-services/common/dbha/ha-module/config"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/dbutil"
	"dbm-services/common/dbha/ha-module/log"
)

// RedisClusterNewIns create rediscluster and predixy detect instance
func RedisClusterNewIns(instances []interface{}, conf *config.Config) ([]dbutil.DataBaseDetect, error) {
	var (
		err          error
		unmarshalIns []*RedisDetectInfoFromCmDB
		ret          []dbutil.DataBaseDetect
	)

	unmarshalIns, err = UnMarshalRedisInstanceByCmdb(instances, constvar.PredixyRedisCluster)
	if err != nil {
		log.Logger.Errorf("RedisCluster UnMarshal failed,%s,err:%s",
			constvar.PredixyRedisCluster, err.Error())
		return nil, err
	}

	var predixyIns, redisIns []dbutil.DataBaseDetect
	for _, uIns := range unmarshalIns {
		// check the cluster_type should be PredixyRedisCluster
		if uIns.ClusterType != constvar.PredixyRedisCluster {
			redisIns = append(redisIns, NewRedisClusterDetectInstance(uIns, conf))
		}

		// create detect instance by machine_type
		if uIns.MetaType == constvar.PredixyMetaType {
			predixyIns = append(predixyIns, NewPredixyDetectInstance(uIns, conf))
		}
	}

	// get pass from config system.
	GetInstancePass(predixyIns, conf)

	ret = append(ret, redisIns...)
	ret = append(ret, predixyIns...)
	return ret, err
}

// RedisClusterDeserialize deserialize rediscluster and predixy detect instance
func RedisClusterDeserialize(jsonInfo []byte, conf *config.Config) (dbutil.DataBaseDetect, error) {
	response := RedisDetectResponse{}
	if err := json.Unmarshal(jsonInfo, &response); err != nil {
		log.Logger.Errorf("json unmarshal failed. jsoninfo:\n%s\n, err:%s", string(jsonInfo), err.Error())
		return nil, err
	}

	// cluster_type should be equal to PredixyRedisCluster
	if response.ClusterType != constvar.PredixyRedisCluster {
		unmatchErr := fmt.Errorf("cluster unmatch %s:%s", response.ClusterType, constvar.PredixyRedisCluster)
		log.Logger.Errorf("redisCluster Deserialize. %s", unmatchErr.Error())
		return nil, unmatchErr
	}

	// create detect instance by machine_type
	if response.DBType == constvar.PredixyMetaType {
		ret := NewPredixyDetectInstanceFromRsp(&response, conf)
		return ret, nil
	}
	if response.DBType == constvar.RedisMetaType {
		ret := NewRedisClusterDetectInstanceFromRsp(&response, conf)
		return ret, nil
	}
	return nil, fmt.Errorf("unexpected moudle :%s 4 cluster:%s", response.DBType, constvar.PredixyRedisCluster)
}

// RedisClusterNewSwitchIns create redis and predixy switch instance
func RedisClusterNewSwitchIns(instances []interface{}, conf *config.Config) ([]dbutil.DataBaseSwitch, error) {
	var err error
	var ret []dbutil.DataBaseSwitch

	for _, ins := range instances {
		var clusterType, metaType string
		// get cluster_type and meta type from instance information
		if clusterType, metaType, err = GetClusterAndMetaFromIns(ins); err != nil {
			log.Logger.Errorf("tendis ins lack cluster and meta info,%+v,err:%s", ins, err.Error())
			continue
		}

		// check cluster_type is equal to PredixyRedisCluster
		if clusterType != constvar.PredixyRedisCluster {
			log.Logger.Errorf("unexpected cluster type:%s, when PredixyRedisCluster handle.", clusterType)
			continue
		}

		// create instance by machine_type
		if metaType == constvar.PredixyMetaType {
			if pw, err := NewPredixySwitchIns(ins, conf); err != nil {
				log.Logger.Errorf("new predixy switch ins failed:%s", err.Error())
			} else {
				ret = append(ret, pw)
			}
			// } else if metaType == constvar.RedisMetaType {
			// 	// if pw, err := NewRedisClulsterSwitchIns(ins, conf); err != nil {
			// 	// 	log.Logger.Errorf("new redisC switch ins failed:%s", err.Error())
			// 	// } else {
			// 	// 	ret = append(ret, pw)
			// 	// }
		} else {
			log.Logger.Errorf("unexpected metaType 4 %+v::cluster:%s,dbType:%s", ins, clusterType, metaType)
		}
	}

	return ret, err
}

// NewRedisClulsterSwitchIns new redisC switch instance
func NewRedisClulsterSwitchIns(instance interface{}, conf *config.Config) (dbutil.DataBaseSwitch, error) {
	swIns, err := CreateRedisSwitchInfo(instance, conf)
	if err != nil {
		log.Logger.Errorf("parse redisC switch instance failed,err:%s", err.Error())
		return nil, err
	}

	// check machine_type is equal to redisC
	if swIns.MetaType != constvar.RedisMetaType {
		return nil, fmt.Errorf("none redis 4 switch. ins:%+v", swIns)
	}

	pw := RedisClusterSwitch{
		RedisSwitchInfo: *swIns,
	}

	// get the password of switch instance
	if passwd, err := GetInstancePassByClusterId(constvar.RedisMetaType, pw.ClusterId, conf); err != nil {
		log.Logger.Errorf("get redisC switch passwd failed,err:%s,info:%s", err.Error(), pw.ShowSwitchInstanceInfo())
	} else {
		pw.Pass = passwd
	}

	return &pw, nil
}
