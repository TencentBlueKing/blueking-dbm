package riak

import (
	"dbm-services/common/dbha/ha-module/client"
	"dbm-services/common/dbha/ha-module/config"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/dbutil"
	"dbm-services/common/dbha/ha-module/log"
	"encoding/json"
	"fmt"
	"strconv"
)

// RiakInstanceInfoDetail 实例信息
type RiakInstanceInfoDetail struct {
	IP           string `json:"ip"`
	Port         int    `json:"port"`
	BKIdcCityID  int    `json:"bk_idc_city_id"`
	InstanceRole string `json:"instance_role"`
	Status       string `json:"status"`
	Cluster      string `json:"cluster"`
	BKBizID      int    `json:"bk_biz_id"`
	ClusterType  string `json:"cluster_type"`
	MachineType  string `json:"machine_type"`
}

// NewRiakInstanceByCmDB unmarshal cmdb instances to agent detect instance struct
func NewRiakInstanceByCmDB(instances []interface{}, Conf *config.Config) ([]dbutil.DataBaseDetect, error) {
	var (
		err          error
		unmarshalIns []*RiakDetectInstanceInfoFromCmDB
		ret          []dbutil.DataBaseDetect
	)

	unmarshalIns, err = UnMarshalRiakInstanceByCmdb(instances, constvar.Riak, constvar.Riak)

	if err != nil {
		return nil, err
	}

	// cmdb的数据结构转换为agent用来探测的数据结构
	for _, uIns := range unmarshalIns {
		ret = append(ret, NewRiakDetectInstanceForAgent(uIns, Conf))
	}

	return ret, err
}

// DeserializeRiak 反序列化从Agent上报上来的故障实例
func DeserializeRiak(jsonInfo []byte, conf *config.Config) (dbutil.DataBaseDetect, error) {
	response := RiakDetectResponse{}
	err := json.Unmarshal(jsonInfo, &response)
	if err != nil {
		log.Logger.Errorf("json unmarshal failed. jsoninfo:\n%s\n, err:%s", string(jsonInfo), err.Error())
		return nil, err
	}
	var ret dbutil.DataBaseDetect
	// gm将agent上报的数据结构转换为gdm通道接收的数据结构
	ret = NewRiakDetectInstanceForGdm(&response, constvar.Riak, conf)
	return ret, nil
}

// NewRiakSwitchInstance unmarshal cmdb instances to switch instance struct
func NewRiakSwitchInstance(instances []interface{}, conf *config.Config) ([]dbutil.DataBaseSwitch, error) {
	var ret []dbutil.DataBaseSwitch
	for _, v := range instances {
		ins := RiakInstanceInfoDetail{}
		rawData, err := json.Marshal(v)
		if err != nil {
			return nil, fmt.Errorf("marshal instance info failed:%s", err.Error())
		}
		if err = json.Unmarshal(rawData, &ins); err != nil {
			return nil, fmt.Errorf("unmarshal instance info failed:%s", err.Error())
		}

		// 用于切换的实例信息
		swIns := RiakSwitch{
			BaseSwitch: dbutil.BaseSwitch{
				Ip:          ins.IP,
				Port:        ins.Port,
				IdcID:       ins.BKIdcCityID,
				Status:      ins.Status,
				App:         strconv.Itoa(ins.BKBizID),
				ClusterType: ins.ClusterType,
				MetaType:    ins.MachineType,
				Cluster:     ins.Cluster,
				CmDBClient:  client.NewCmDBClient(&conf.DBConf.CMDB, conf.GetCloudId()),
				HaDBClient:  client.NewHaDBClient(&conf.DBConf.HADB, conf.GetCloudId()),
			},
			Role: ins.InstanceRole,
		}
		ret = append(ret, &swIns)
	}
	return ret, nil
}

// UnMarshalRiakInstanceByCmdb convert cmdb instance info to RiakDetectInstanceInfoFromCmDB
func UnMarshalRiakInstanceByCmdb(instances []interface{},
	uClusterType string, uMetaType string) ([]*RiakDetectInstanceInfoFromCmDB, error) {
	var (
		ret []*RiakDetectInstanceInfoFromCmDB
	)
	cache := map[string]*RiakDetectInstanceInfoFromCmDB{}

	for _, v := range instances {
		ins := RiakInstanceInfoDetail{}
		rawData, err := json.Marshal(v)
		if err != nil {
			return nil, fmt.Errorf("marshal instance info failed:%s", err.Error())
		}
		if err = json.Unmarshal(rawData, &ins); err != nil {
			return nil, fmt.Errorf("unmarshal instance info failed:%s", err.Error())
		}
		if ins.ClusterType != uClusterType || ins.MachineType != uMetaType ||
			(ins.Status != constvar.RUNNING && ins.Status != constvar.AVAILABLE) {
			continue
		}
		cacheIns, ok := cache[ins.IP]
		//only need detect the minimum port instance
		if !ok || ok && ins.Port < cacheIns.Port {
			cache[ins.IP] = &RiakDetectInstanceInfoFromCmDB{
				Ip:          ins.IP,
				Port:        ins.Port,
				App:         strconv.Itoa(ins.BKBizID),
				ClusterType: ins.ClusterType,
				MetaType:    ins.MachineType,
				Cluster:     ins.Cluster,
			}
		}
	}

	for _, cacheIns := range cache {
		ret = append(ret, cacheIns)
	}

	return ret, nil
}
