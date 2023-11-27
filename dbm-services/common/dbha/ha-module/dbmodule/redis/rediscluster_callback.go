package redis

import (
	"encoding/json"
	"fmt"

	"dbm-services/common/dbha/ha-module/config"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/dbutil"
	"dbm-services/common/dbha/ha-module/log"
)

// RedisClusterNewIns Agent通过CMDB获取的信息来生成需要探测的实例
func RedisClusterNewIns(instances []interface{},
	conf *config.Config) ([]dbutil.DataBaseDetect, error) {

	var (
		err          error
		unmarshalIns []*RedisDetectInfoFromCmDB
		ret          []dbutil.DataBaseDetect
	)

	unmarshalIns, err = UnMarshalRedisInstanceByCmdb(instances, constvar.RedisCluster)
	if err != nil {
		log.Logger.Errorf("RedisCluster UnMarshal failed,%s,err:%s",
			constvar.RedisCluster, err.Error())
		return nil, err
	}

	var redisIns, twemIns []dbutil.DataBaseDetect
	for _, uIns := range unmarshalIns {
		// check the cluster_type should be TwemproxyRedisInstance
		if uIns.ClusterType != constvar.RedisCluster {
			continue
		}

		// create detect instance by machine_type
		if uIns.MetaType == constvar.RedisMetaType {
			redisIns = append(redisIns, NewRedisDetectInstance(uIns, conf))
			count, _ := GetInstancePass(constvar.RedisMetaType, redisIns, conf)
			if count != len(redisIns) {
				log.Logger.Errorf("RedisCluster redis passwd part failed,succ:%d,total:%d",
					count, len(redisIns))
			}
		} else if uIns.MetaType == constvar.TwemproxyMetaType {
			twemIns = append(twemIns, NewTwemproxyDetectInstance(uIns, conf))
			count, _ := GetInstancePass(constvar.TwemproxyMetaType, twemIns, conf)
			if count != len(twemIns) {
				log.Logger.Errorf("RedisCluster twemproxy passwd part failed,succ:%d,total:%d",
					count, len(twemIns))
			}
		} else {
			log.Logger.Errorf("RedisCluster cluster is %s but meta type is invalid",
				constvar.RedisCluster)
		}
	}

	ret = append(ret, redisIns...)
	ret = append(ret, twemIns...)
	return ret, err
}

// RedisClusterDeserialize 反序列化从Agent上报上来的故障实例
func RedisClusterDeserialize(jsonInfo []byte,
	conf *config.Config) (dbutil.DataBaseDetect, error) {
	response := RedisDetectResponse{}
	err := json.Unmarshal(jsonInfo, &response)
	if err != nil {
		log.Logger.Errorf("json unmarshal failed. jsoninfo:\n%s\n, err:%s",
			string(jsonInfo), err.Error())
		return nil, err
	}

	// cluster_type should be equal to TwemproxyRedisInstance
	if response.ClusterType != constvar.RedisCluster {
		unmatchErr := fmt.Errorf("cluster unmatch %s:%s",
			response.ClusterType, constvar.RedisCluster)
		log.Logger.Errorf("RedisCluster Deserialize. %s", unmatchErr.Error())
		return nil, unmatchErr
	}

	// create detect instance by machine_type
	if response.DBType == constvar.RedisMetaType {
		ret := NewRedisDetectInstanceFromRsp(&response, conf)
		return ret, nil
	} else if response.DBType == constvar.TwemproxyMetaType {
		ret := NewTwemproxyDetectInstanceFromRsp(&response, conf)
		return ret, nil
	} else {
		unmatchErr := fmt.Errorf("RedisCluster meta_type not exist,%s",
			response.DBType)
		log.Logger.Errorf("deserialize failed,%s", unmatchErr.Error())
		return nil, err
	}
}

// RedisClusterNewSwitchIns create redis cluster switch ins
func RedisClusterNewSwitchIns(instances []interface{},
	conf *config.Config) ([]dbutil.DataBaseSwitch, error) {
	var err error
	var ret []dbutil.DataBaseSwitch
	for _, v := range instances {
		// get cluster_type and meta type from instance information
		clusterType, metaType, err := GetClusterAndMetaFromIns(v)
		if err != nil {
			log.Logger.Errorf("redis ins lack cluster and meta info,%v,err:%s",
				v, err.Error())
			continue
		}

		// check cluster_type is equal to TwemproxyRedisInstance
		if clusterType != constvar.RedisCluster {
			continue
		}

		// create instance by machine_type
		if metaType == constvar.RedisMetaType {
			pw, err := NewRedisSwitchIns(v, conf)
			if err != nil {
				log.Logger.Errorf("new redis switch ins failed:%s", err.Error())
				continue
			}
			ret = append(ret, pw)
		} else if metaType == constvar.TwemproxyMetaType {
			pw, err := NewTwemproxySwitchIns(v, conf)
			if err != nil {
				log.Logger.Errorf("new twemproxy switch ins failed:%s", err.Error())
				continue
			}
			ret = append(ret, pw)
		} else {
			log.Logger.Errorf("redis cluster[%s] not fit meta[%s]",
				clusterType, metaType)
			continue
		}
	}
	return ret, err
}

// NewRedisSwitchIns create redis switch instance
func NewRedisSwitchIns(instance interface{},
	conf *config.Config) (dbutil.DataBaseSwitch, error) {
	swIns, err := CreateRedisSwitchInfo(instance, conf)
	if err != nil {
		//stuff err
		log.Logger.Errorf("parse redis switch instance failed,err:%s",
			err.Error())
		return nil, err
	}

	// check machine_type is equal to tendiscache
	if swIns.MetaType != constvar.RedisMetaType {
		log.Logger.Errorf("Create redis switch while the metaType[%s] != %s",
			swIns.MetaType, constvar.RedisMetaType)
		return nil, err
	}

	pw := RedisSwitch{
		RedisSwitchInfo: *swIns,
		Config:          conf,
		NoNeed:          false,
	}

	// get the password of redis switch instance
	passwd, err := GetInstancePassByCluster(
		constvar.RedisMetaType, pw.Cluster, conf,
	)
	if err != nil {
		log.Logger.Errorf("get redis switch passwd failed,err:%s,info:%s",
			err.Error(), pw.ShowSwitchInstanceInfo())
	} else {
		pw.Pass = passwd
	}

	return &pw, nil
}

// NewTwemproxySwitchIns create twemproxy switch instance
func NewTwemproxySwitchIns(instance interface{},
	conf *config.Config) (dbutil.DataBaseSwitch, error) {
	swIns, err := CreateRedisProxySwitchInfo(instance, conf)
	if err != nil {
		log.Logger.Errorf("parse twemproxy switch instance failed,err:%s",
			err.Error())
		return nil, err
	}

	// check machine_type is equal to twemproxy
	if swIns.MetaType != constvar.TwemproxyMetaType {
		log.Logger.Errorf("Create Twemproxy switch while the metaType[%s] != %s",
			swIns.MetaType, constvar.TwemproxyMetaType)
		return nil, err
	}

	pw := TwemproxySwitch{
		RedisProxySwitchInfo: *swIns,
	}

	// get the password of twemproxy switch instance
	passwd, err := GetInstancePassByCluster(
		constvar.TwemproxyMetaType, pw.Cluster, conf,
	)
	if err != nil {
		log.Logger.Errorf("get twemproxy switch passwd failed,err:%s,info:%s",
			err.Error(), pw.ShowSwitchInstanceInfo())
	} else {
		pw.Pass = passwd
	}
	return &pw, nil
}
