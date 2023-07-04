package mysql

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

type DBInstanceInfoDetail struct {
	IP               string             `json:"ip"`
	Port             int                `json:"port"`
	BKIdcCityID      int                `json:"bk_idc_city_id"`
	InstanceRole     string             `json:"instance_role"`
	Status           string             `json:"status"`
	Cluster          string             `json:"cluster"`
	BKBizID          int                `json:"bk_biz_id"`
	ClusterType      string             `json:"cluster_type"`
	MachineType      string             `json:"machine_type"`
	Receiver         []MySQLSlaveInfo   `json:"receiver"`
	ProxyInstanceSet []dbutil.ProxyInfo `json:"proxyinstance_set"`
}

// UnMarshalMySQLInstanceByCmdb convert cmdb instance info to MySQLDetectInstanceInfoFromCmDB
func UnMarshalMySQLInstanceByCmdb(instances []interface{},
	uClusterType string, uMetaType string) ([]*MySQLDetectInstanceInfoFromCmDB, error) {
	var (
		ret []*MySQLDetectInstanceInfoFromCmDB
	)
	cache := map[string]*MySQLDetectInstanceInfoFromCmDB{}

	for _, v := range instances {
		ins := DBInstanceInfoDetail{}
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
			cache[ins.IP] = &MySQLDetectInstanceInfoFromCmDB{
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

// NewMySQLInstanceByCmDB unmarshal cmdb instances to detect instance struct
func NewMySQLInstanceByCmDB(instances []interface{}, Conf *config.Config) ([]dbutil.DataBaseDetect, error) {
	var (
		err          error
		unmarshalIns []*MySQLDetectInstanceInfoFromCmDB
		ret          []dbutil.DataBaseDetect
	)

	unmarshalIns, err = UnMarshalMySQLInstanceByCmdb(instances, constvar.MySQLClusterType,
		constvar.MySQLMetaType)

	if err != nil {
		return nil, err
	}

	for _, uIns := range unmarshalIns {
		ret = append(ret, NewMySQLDetectInstance1(uIns, Conf))
	}

	return ret, err
}

// NewMySQLSwitchInstance unmarshal cmdb instances to switch instance struct
func NewMySQLSwitchInstance(instances []interface{}, conf *config.Config) ([]dbutil.DataBaseSwitch, error) {
	var ret []dbutil.DataBaseSwitch
	for _, v := range instances {
		ins := DBInstanceInfoDetail{}
		rawData, err := json.Marshal(v)
		if err != nil {
			return nil, fmt.Errorf("marshal instance info failed:%s", err.Error())
		}
		if err = json.Unmarshal(rawData, &ins); err != nil {
			return nil, fmt.Errorf("unmarshal instance info failed:%s", err.Error())
		}

		cmdbClient, err := client.NewCmDBClient(&conf.DBConf.CMDB, conf.GetCloudId())
		if err != nil {
			return nil, err
		}

		hadbClient, err := client.NewHaDBClient(&conf.DBConf.HADB, conf.GetCloudId())
		if err != nil {
			return nil, err
		}

		swIns := MySQLSwitch{
			BaseSwitch: dbutil.BaseSwitch{
				Ip:          ins.IP,
				Port:        ins.Port,
				IDC:         strconv.Itoa(ins.BKIdcCityID),
				Status:      ins.Status,
				App:         strconv.Itoa(ins.BKBizID),
				ClusterType: ins.ClusterType,
				MetaType:    ins.MachineType,
				Cluster:     ins.Cluster,
				CmDBClient:  cmdbClient,
				HaDBClient:  hadbClient,
			},
			Role:                     ins.InstanceRole,
			AllowedChecksumMaxOffset: conf.GMConf.GCM.AllowedChecksumMaxOffset,
			AllowedSlaveDelayMax:     conf.GMConf.GCM.AllowedSlaveDelayMax,
			AllowedTimeDelayMax:      conf.GMConf.GCM.AllowedTimeDelayMax,
			ExecSlowKBytes:           conf.GMConf.GCM.ExecSlowKBytes,
			MySQLUser:                conf.DBConf.MySQL.User,
			MySQLPass:                conf.DBConf.MySQL.Pass,
			ProxyUser:                conf.DBConf.MySQL.ProxyUser,
			ProxyPass:                conf.DBConf.MySQL.ProxyPass,
			Timeout:                  conf.DBConf.MySQL.Timeout,
			Slave:                    ins.Receiver,
			Proxy:                    ins.ProxyInstanceSet,
		}

		// always use standbySlave, if no standby attribute slave found, use
		// the first slave
		if ins.InstanceRole == constvar.MySQLMaster && len(ins.Receiver) > 0 {
			swIns.StandBySlave = ins.Receiver[0]
		}
		for _, slave := range ins.Receiver {
			if slave.IsStandBy {
				swIns.StandBySlave = slave
				break
			}
		}
		ret = append(ret, &swIns)
	}
	return ret, nil
}

// DeserializeMySQL convert response info to detect info
func DeserializeMySQL(jsonInfo []byte, Conf *config.Config) (dbutil.DataBaseDetect, error) {
	response := MySQLDetectResponse{}
	err := json.Unmarshal(jsonInfo, &response)
	if err != nil {
		log.Logger.Errorf("json unmarshal failed. jsoninfo:\n%s\n, err:%s", string(jsonInfo), err.Error())
		return nil, err
	}

	ret := NewMySQLDetectInstance2(&response, constvar.MySQL, Conf)
	return ret, nil
}
