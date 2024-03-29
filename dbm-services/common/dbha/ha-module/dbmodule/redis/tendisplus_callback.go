package redis

import (
	"encoding/json"
	"fmt"

	"dbm-services/common/dbha/ha-module/config"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/dbutil"
	"dbm-services/common/dbha/ha-module/log"
)

// TendisplusClusterNewIns create tendisplus and predixy detect instance
func TendisplusClusterNewIns(instances []interface{},
	conf *config.Config) ([]dbutil.DataBaseDetect, error) {
	var (
		err          error
		unmarshalIns []*RedisDetectInfoFromCmDB
		ret          []dbutil.DataBaseDetect
	)

	unmarshalIns, err = UnMarshalRedisInstanceByCmdb(instances, constvar.TendisplusCluster)
	if err != nil {
		log.Logger.Errorf("TendisCluster UnMarshal failed,%s,err:%s",
			constvar.TendisplusCluster, err.Error())
		return nil, err
	}

	var predixyIns []dbutil.DataBaseDetect
	for _, uIns := range unmarshalIns {
		// check the cluster_type should be PredixyTendisplusCluster
		if uIns.ClusterType != constvar.TendisplusCluster {
			continue
		}

		// create detect instance by machine_type
		if uIns.MetaType == constvar.PredixyMetaType {
			predixyIns = append(predixyIns, NewPredixyDetectInstance(uIns, conf))
		}
	}

	// get predixy passwd
	if len(predixyIns) > 0 {
		count, _ := GetInstancePass(predixyIns, conf)
		if count != len(predixyIns) {
			log.Logger.Errorf("TendisCluster predixy passwd part failed,succ:%d,total:%d",
				count, len(predixyIns))
		}
	}

	ret = append(ret, predixyIns...)
	return ret, err
}

// TendisplusClusterDeserialize deserialize tendisplus and predixy detect instance
func TendisplusClusterDeserialize(jsonInfo []byte,
	conf *config.Config) (dbutil.DataBaseDetect, error) {
	response := RedisDetectResponse{}
	err := json.Unmarshal(jsonInfo, &response)
	if err != nil {
		log.Logger.Errorf("json unmarshal failed. jsoninfo:\n%s\n, err:%s",
			string(jsonInfo), err.Error())
		return nil, err
	}

	// cluster_type should be equal to PredixyTendisplusCluster
	if response.ClusterType != constvar.TendisplusCluster {
		unmatchErr := fmt.Errorf("cluster unmatch %s:%s",
			response.ClusterType, constvar.TendisplusCluster)
		log.Logger.Errorf("TendisCluster Deserialize. %s", unmatchErr.Error())
		return nil, err
	}

	// create detect instance by machine_type
	if response.DBType == constvar.PredixyMetaType {
		ret := NewPredixyDetectInstanceFromRsp(&response, conf)
		return ret, nil
	} else {
		unmatchErr := fmt.Errorf("TendisCluster meta_type not exist,%s",
			response.DBType)
		log.Logger.Errorf("deserialize failed,%s", unmatchErr.Error())
		return nil, err
	}
}

// TendisplusClusterNewSwitchIns create tendisplus and predixy switch instance
func TendisplusClusterNewSwitchIns(instances []interface{},
	conf *config.Config) ([]dbutil.DataBaseSwitch, error) {
	var err error
	var ret []dbutil.DataBaseSwitch
	for _, v := range instances {
		// get cluster_type and meta type from instance information
		clusterType, metaType, err := GetClusterAndMetaFromIns(v)
		if err != nil {
			log.Logger.Errorf("tendis ins lack cluster and meta info,%v,err:%s",
				v, err.Error())
			continue
		}

		// check cluster_type is equal to PredixyTendisplusCluster
		if clusterType != constvar.TendisplusCluster {
			continue
		}

		// create instance by machine_type
		if metaType == constvar.PredixyMetaType {
			pw, err := NewPredixySwitchIns(v, conf)
			if err != nil {
				log.Logger.Errorf("new predixy switch ins failed:%s", err.Error())
				continue
			}
			ret = append(ret, pw)
		}
	}
	return ret, err
}

// NewTendisplusSwitchIns new tendisplus switch instance
func NewTendisplusSwitchIns(instance interface{},
	conf *config.Config) (dbutil.DataBaseSwitch, error) {
	swIns, err := CreateRedisSwitchInfo(instance, conf)
	if err != nil {
		log.Logger.Errorf("parse tendisplus switch instance failed,err:%s",
			err.Error())
		return nil, err
	}

	// check machine_type is equal to tendisplus
	if swIns.MetaType != constvar.TendisplusMetaType {
		log.Logger.Errorf("Create tendisplus switch while the metaType[%s] != %s",
			swIns.MetaType, constvar.TendisplusMetaType)
		return nil, err
	}

	pw := TendisplusSwitch{
		RedisSwitchInfo: *swIns,
	}

	// get the password of switch instance
	passwd, err := GetInstancePassByClusterId(
		constvar.TendisplusMetaType, pw.ClusterId, conf,
	)
	if err != nil {
		log.Logger.Errorf("get tendisplus switch passwd failed,err:%s,info:%s",
			err.Error(), pw.ShowSwitchInstanceInfo())
	} else {
		pw.Pass = passwd
	}

	return &pw, nil
}

// NewPredixySwitchInstance new predixy switch instance
func NewPredixySwitchIns(instance interface{},
	conf *config.Config) (dbutil.DataBaseSwitch, error) {
	swIns, err := CreateRedisProxySwitchInfo(instance, conf)
	if err != nil {
		log.Logger.Errorf("parse predixy switch instance failed,err:%s",
			err.Error())
		return nil, err
	}

	// check machine_type is equal to Predixy
	if swIns.MetaType != constvar.PredixyMetaType {
		log.Logger.Errorf("Create predixy switch while the metaType[%s] != %s",
			swIns.MetaType, constvar.PredixyMetaType)
		return nil, err
	}

	pw := PredixySwitch{
		RedisProxySwitchInfo: *swIns,
	}

	// get the password of switch instance
	passwd, err := GetInstancePassByClusterId(
		constvar.PredixyMetaType, pw.ClusterId, conf,
	)
	if err != nil {
		log.Logger.Errorf("get predixy switch passwd failed,err:%s,info:%s",
			err.Error(), pw.ShowSwitchInstanceInfo())
	} else {
		log.Logger.Infof("get predixy switch passwd[%s]", passwd)
		pw.Pass = passwd
	}
	return &pw, nil
}
