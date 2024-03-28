package redis

import (
	"encoding/json"
	"fmt"

	"dbm-services/common/dbha/ha-module/config"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/dbutil"
	"dbm-services/common/dbha/ha-module/log"
)

// TendisssdClusterNewIns Agent通过CMDB获取的信息来生成需要探测的实例
func TendisssdClusterNewIns(instances []interface{},
	conf *config.Config) ([]dbutil.DataBaseDetect, error) {

	var (
		err          error
		unmarshalIns []*RedisDetectInfoFromCmDB
		ret          []dbutil.DataBaseDetect
	)

	unmarshalIns, err = UnMarshalRedisInstanceByCmdb(instances, constvar.TendisSSDCluster)
	if err != nil {
		log.Logger.Errorf("TendisSSDCluster UnMarshal failed,%s,err:%s",
			constvar.RedisCluster, err.Error())
		return nil, err
	}

	var redisIns, twemIns []dbutil.DataBaseDetect
	for _, uIns := range unmarshalIns {
		// check the cluster_type should be TwemproxyRedisInstance
		if uIns.ClusterType != constvar.TendisSSDCluster {
			continue
		}

		// create detect instance by machine_type
		if uIns.MetaType == constvar.TendisSSDMetaType {
			redisIns = append(redisIns, NewRedisDetectInstance(
				uIns, constvar.TendisSSDMetaType, conf,
			))
		} else if uIns.MetaType == constvar.TwemproxyMetaType {
			twemIns = append(twemIns, NewTwemproxyDetectInstance(uIns, conf))
		} else {
			log.Logger.Errorf("TendisssdCluster cluster is %s but meta type is invalid",
				constvar.TendisSSDCluster)
		}
	}

	// get redis instance passwd
	if len(redisIns) > 0 {
		count, _ := GetInstancePass(redisIns, conf)
		if count != len(redisIns) {
			log.Logger.Errorf("RedisCluster redis passwd part failed,succ:%d,total:%d",
				count, len(redisIns))
		}
	}

	// get twemproxy instance passwd
	if len(twemIns) > 0 {
		count, _ := GetInstancePass(twemIns, conf)
		if count != len(twemIns) {
			log.Logger.Errorf("RedisCluster twemproxy passwd part failed,succ:%d,total:%d",
				count, len(twemIns))
		}
	}

	ret = append(ret, redisIns...)
	ret = append(ret, twemIns...)
	return ret, err
}

// TendisssdClusterDeserialize 反序列化从Agent上报上来的故障实例
func TendisssdClusterDeserialize(jsonInfo []byte,
	conf *config.Config) (dbutil.DataBaseDetect, error) {
	response := RedisDetectResponse{}
	err := json.Unmarshal(jsonInfo, &response)
	if err != nil {
		log.Logger.Errorf("json unmarshal failed. jsoninfo:\n%s\n, err:%s",
			string(jsonInfo), err.Error())
		return nil, err
	}

	// cluster_type should be equal to TwemproxyRedisInstance
	if response.ClusterType != constvar.TendisSSDCluster {
		unmatchErr := fmt.Errorf("cluster unmatch %s:%s",
			response.ClusterType, constvar.TendisSSDCluster)
		log.Logger.Errorf("TendisSSDCluster Deserialize. %s", unmatchErr.Error())
		return nil, unmatchErr
	}

	// create detect instance by machine_type
	if response.DBType == constvar.TendisSSDMetaType {
		ret := NewRedisDetectInstanceFromRsp(
			&response, constvar.TendisSSDMetaType, conf,
		)
		return ret, nil
	} else if response.DBType == constvar.TwemproxyMetaType {
		ret := NewTwemproxyDetectInstanceFromRsp(&response, conf)
		return ret, nil
	} else {
		unmatchErr := fmt.Errorf("TendisSSDCluster meta_type not exist,%s",
			response.DBType)
		log.Logger.Errorf("deserialize failed,%s", unmatchErr.Error())
		return nil, err
	}
}

// TendisssdClusterNewSwitchIns create redis cluster switch ins
func TendisssdClusterNewSwitchIns(instances []interface{},
	conf *config.Config) ([]dbutil.DataBaseSwitch, error) {
	var err error
	var ret []dbutil.DataBaseSwitch
	for _, v := range instances {
		// get cluster_type and meta type from instance information
		clusterType, metaType, err := GetClusterAndMetaFromIns(v)
		if err != nil {
			log.Logger.Errorf("tendisssd ins lack cluster and meta info,%v,err:%s",
				v, err.Error())
			continue
		}

		// check cluster_type is equal to TendisSSDCluster
		if clusterType != constvar.TendisSSDCluster {
			continue
		}

		// create instance by machine_type
		if metaType == constvar.TendisSSDMetaType {
			pw, err := NewRedisSwitchIns(v, conf)
			if err != nil {
				log.Logger.Errorf("new tendisssd switch ins failed:%s", err.Error())
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
