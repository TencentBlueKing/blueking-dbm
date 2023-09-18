package redis

import (
	"encoding/json"

	"dbm-services/common/dbha/ha-module/config"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/dbutil"
	"dbm-services/common/dbha/ha-module/log"
)

// NewTwemproxyInstanceByCmdb Agent通过CMDB获取的信息来生成需要探测的实例
func NewTwemproxyInstanceByCmdb(instances []interface{},
	conf *config.Config) ([]dbutil.DataBaseDetect, error) {
	var (
		err          error
		unmarshalIns []*RedisDetectInfoFromCmDB
		ret          []dbutil.DataBaseDetect
	)

	unmarshalIns, err = UnMarshalRedisInstanceByCmdb(instances,
		constvar.RedisClusterType, constvar.TwemproxyMetaType)

	if err != nil {
		return nil, err
	}

	for _, uIns := range unmarshalIns {
		ret = append(ret, NewTwemproxyDetectInstance(uIns, conf))
	}

	return ret, err
}

// DeserializeTwemproxy 反序列化从Agent上报上来的故障实例
func DeserializeTwemproxy(jsonInfo []byte,
	conf *config.Config) (dbutil.DataBaseDetect, error) {
	response := RedisDetectResponse{}
	err := json.Unmarshal(jsonInfo, &response)
	if err != nil {
		log.Logger.Errorf("json unmarshal failed. jsoninfo:\n%s\n, err:%s",
			string(jsonInfo), err.Error())
		return nil, err
	}
	ret := NewTwemproxyDetectInstanceFromRsp(&response, conf)
	return ret, nil
}

// NewTwemproxySwitchInstance TODO
func NewTwemproxySwitchInstance(instances []interface{},
	conf *config.Config) ([]dbutil.DataBaseSwitch, error) {
	var err error
	var ret []dbutil.DataBaseSwitch
	for _, v := range instances {
		swIns, err := CreateRedisProxySwitchInfo(v, conf)
		if err != nil {
			log.Logger.Errorf("parse twemproxy switch instance failed,err:%s",
				err.Error())
			continue
		}

		if swIns.MetaType != constvar.TwemproxyMetaType {
			log.Logger.Errorf("Create Twemproxy switch while the metaType[%s] != %s",
				swIns.MetaType, constvar.TwemproxyMetaType)
			continue
		}
		if swIns.CheckFetchEntryDetail() {
			edErr := swIns.GetEntryDetailInfo()
			if edErr != nil {
				log.Logger.Errorf("GetEntryDetail failed in NewTwemproxySwitch,err:%s",
					edErr.Error())
			}
		}

		pw := TwemproxySwitch{
			RedisProxySwitchInfo: *swIns,
		}

		passwd, err := GetInstancePassByCluster(
			constvar.Twemproxy, pw.Cluster, conf,
		)
		if err != nil {
			log.Logger.Errorf("get twemproxy switch passwd failed,err:%s,info:%s",
				err.Error(), pw.ShowSwitchInstanceInfo())
		} else {
			pw.Pass = passwd
		}
		ret = append(ret, &pw)
	}

	return ret, err
}
