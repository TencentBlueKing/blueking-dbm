package redis

import (
	"encoding/json"

	"dbm-services/common/dbha/ha-module/config"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/dbutil"
	"dbm-services/common/dbha/ha-module/log"
)

// NewPredixyInstanceByCmdb Agent通过CMDB获取的信息来生成需要探测的实例
func NewPredixyInstanceByCmdb(instances []interface{},
	conf *config.Config) ([]dbutil.DataBaseDetect, error) {
	var (
		err          error
		unmarshalIns []*RedisDetectInfoFromCmDB
		ret          []dbutil.DataBaseDetect
	)

	unmarshalIns, err = UnMarshalRedisInstanceByCmdb(
		instances, constvar.TendisplusCluster,
		constvar.PredixyMetaType)

	if err != nil {
		return nil, err
	}

	for _, uIns := range unmarshalIns {
		ret = append(ret, NewPredixyDetectInstance(uIns, conf))
	}

	return ret, err
}

// DeserializePredixy 反序列化从Agent上报上来的故障实例
func DeserializePredixy(jsonInfo []byte, conf *config.Config) (dbutil.DataBaseDetect, error) {
	response := RedisDetectResponse{}
	err := json.Unmarshal(jsonInfo, &response)
	if err != nil {
		log.Logger.Errorf("json unmarshal failed. jsoninfo:\n%s\n, err:%s",
			string(jsonInfo), err.Error())
		return nil, err
	}
	ret := NewPredixyDetectInstanceFromRsp(&response, conf)
	return ret, nil
}

// NewPredixySwitchInstance TODO
func NewPredixySwitchInstance(instances []interface{},
	conf *config.Config) ([]dbutil.DataBaseSwitch, error) {
	var err error
	var ret []dbutil.DataBaseSwitch
	for _, v := range instances {
		swIns, err := CreateRedisProxySwitchInfo(v, conf)
		if err != nil {
			log.Logger.Errorf("parse predixy switch instance failed,err:%s",
				err.Error())
			continue
		}

		if swIns.MetaType != constvar.PredixyMetaType {
			log.Logger.Errorf("Create predixy switch while the metaType[%s] != %s",
				swIns.MetaType, constvar.PredixyMetaType)
			continue
		}

		if swIns.CheckFetchEntryDetail() {
			edErr := swIns.GetEntryDetailInfo()
			if edErr != nil {
				log.Logger.Errorf("GetEntryDetail failed in NewPredixySwitch,err:%s",
					edErr.Error())
			}
		}

		pw := PredixySwitch{
			RedisProxySwitchInfo: *swIns,
		}

		passwd, err := GetInstancePassByCluster(
			constvar.Predixy, pw.Cluster, conf,
		)
		if err != nil {
			log.Logger.Errorf("get predixy switch passwd failed,err:%s,info:%s",
				err.Error(), pw.ShowSwitchInstanceInfo())
		} else {
			log.Logger.Infof("get predixy switch passwd[%s]", passwd)
			pw.Pass = passwd
		}
		ret = append(ret, &pw)
	}

	return ret, err
}
