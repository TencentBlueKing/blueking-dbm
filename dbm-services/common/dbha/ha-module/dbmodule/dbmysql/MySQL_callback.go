package dbmysql

import (
	"encoding/json"
	"fmt"
	"strconv"

	"dbm-services/common/dbha/ha-module/client"
	"dbm-services/common/dbha/ha-module/config"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/dbutil"
	"dbm-services/common/dbha/ha-module/log"
)

// UnMarshalMySQLInstanceByCmdb convert cmdb instance info to MySQLDetectInstanceInfoFromCmDB
func UnMarshalMySQLInstanceByCmdb(instances []interface{},
	clusterType string) ([]*MySQLDetectInstanceInfoFromCmDB, error) {
	var (
		ret []*MySQLDetectInstanceInfoFromCmDB
	)
	cache := map[string]*MySQLDetectInstanceInfoFromCmDB{}

	for _, v := range instances {
		ins := dbutil.DBInstanceInfoDetail{}
		rawData, err := json.Marshal(v)
		if err != nil {
			return nil, fmt.Errorf("marshal instance info failed:%s", err.Error())
		}
		if err = json.Unmarshal(rawData, &ins); err != nil {
			return nil, fmt.Errorf("unmarshal instance info failed:%s", err.Error())
		}
		if ins.ClusterType != clusterType || (ins.Status != constvar.RUNNING && ins.Status != constvar.AVAILABLE) {
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

// NewMySQLClusterByCmDB unmarshal cmdb instances to detect instance struct
// filter only TenDB cluster
func NewMySQLClusterByCmDB(instances []interface{}, conf *config.Config) ([]dbutil.DataBaseDetect, error) {
	var (
		err          error
		unmarshalIns []*MySQLDetectInstanceInfoFromCmDB
		ret          []dbutil.DataBaseDetect
	)

	unmarshalIns, err = UnMarshalMySQLInstanceByCmdb(instances, constvar.DetectTenDBHA)

	if err != nil {
		return nil, err
	}

	for _, uIns := range unmarshalIns {
		ret = append(ret, AgentNewMySQLDetectInstance(uIns, conf))
	}

	return ret, err
}

// NewSpiderClusterByCmDB unmarshal cmdb instances to detect instance struct
// filter only TenDBCluster
func NewSpiderClusterByCmDB(instances []interface{}, conf *config.Config) ([]dbutil.DataBaseDetect, error) {
	var (
		err          error
		unmarshalIns []*MySQLDetectInstanceInfoFromCmDB
		ret          []dbutil.DataBaseDetect
	)

	unmarshalIns, err = UnMarshalMySQLInstanceByCmdb(instances, constvar.DetectTenDBCluster)

	if err != nil {
		return nil, err
	}

	for _, uIns := range unmarshalIns {
		ret = append(ret, AgentNewMySQLDetectInstance(uIns, conf))
	}

	return ret, err
}

// NewMySQLSwitchInstance unmarshal cmdb instances to switch instance
// GQA call this and send to gcm switch
func NewMySQLSwitchInstance(instances []interface{}, conf *config.Config) ([]dbutil.DataBaseSwitch, error) {
	var ret []dbutil.DataBaseSwitch
	initFunc := func(ins dbutil.DBInstanceInfoDetail) (dbutil.DataBaseSwitch, error) {
		log.Logger.Debugf("mysql instance detail info:%#v", ins)
		mysqlCommon := MySQLCommonSwitch{
			BaseSwitch: dbutil.BaseSwitch{
				Ip:          ins.IP,
				Port:        ins.Port,
				IdcID:       ins.BKIdcCityID,
				Status:      ins.Status,
				App:         strconv.Itoa(ins.BKBizID),
				ClusterType: ins.ClusterType,
				MetaType:    ins.MachineType,
				Cluster:     ins.Cluster,
				Config:      conf,
				CmDBClient:  client.NewCmDBClient(&conf.DBConf.CMDB, conf.GetCloudId()),
				HaDBClient:  client.NewHaDBClient(&conf.DBConf.HADB, conf.GetCloudId()),
			},
		}

		switch ins.MachineType {
		case constvar.TenDBStorageType:
			swIns := &MySQLSwitch{
				MySQLCommonSwitch: mysqlCommon,
			}
			swIns.SetStandbySlave(ins.Receiver)
			swIns.SetInstanceRole(ins.InstanceRole)
			swIns.Proxy = ins.ProxyInstanceSet
			swIns.Dumper = ins.BinlogDumperSet
			return swIns, nil
		case constvar.TenDBProxyType:
			swIns := &MySQLProxySwitch{
				MySQLCommonSwitch: mysqlCommon,
			}
			swIns.AdminPort = ins.AdminPort
			swIns.Entry = ins.BindEntry
			return swIns, nil
		case constvar.TenDBClusterStorageType:
			swIns := &SpiderStorageSwitch{
				SpiderCommonSwitch: SpiderCommonSwitch{
					MySQLCommonSwitch: mysqlCommon,
					ClusterName:       ins.Cluster,
				},
			}
			swIns.SetStandbySlave(ins.Receiver)
			swIns.SetInstanceRole(ins.InstanceRole)
			swIns.Proxy = ins.ProxyInstanceSet
			return swIns, nil
		case constvar.TenDBClusterProxyType:
			swIns := &SpiderProxyLayerSwitch{
				SpiderCommonSwitch: SpiderCommonSwitch{
					MySQLCommonSwitch: mysqlCommon,
					ClusterName:       ins.Cluster,
				},
			}
			swIns.SetInstanceRole(ins.SpiderRole)
			swIns.AdminPort = ins.AdminPort
			swIns.Entry = ins.BindEntry
			return swIns, nil
		default:
			return nil, fmt.Errorf("unsupport MySQL meta type:%s", ins.MachineType)
		}
	}

	for _, v := range instances {
		ins := dbutil.DBInstanceInfoDetail{}
		rawData, err := json.Marshal(v)
		if err != nil {
			return nil, fmt.Errorf("marshal instance info failed:%s", err.Error())
		}
		if err = json.Unmarshal(rawData, &ins); err != nil {
			return nil, fmt.Errorf("unmarshal instance info failed:%s", err.Error())
		}
		swIns, err := initFunc(ins)
		if err != nil {
			return nil, err
		}
		ret = append(ret, swIns)
	}

	return ret, nil
}

// DeserializeMySQL gdm convert agent report info into DataBaseDetect
func DeserializeMySQL(jsonInfo []byte, conf *config.Config) (dbutil.DataBaseDetect, error) {
	response := MySQLDetectResponse{}
	err := json.Unmarshal(jsonInfo, &response)
	if err != nil {
		log.Logger.Errorf("json unmarshal failed. jsoninfo:\n%s\n, err:%s", string(jsonInfo), err.Error())
		return nil, err
	}

	ret := GMNewMySQLDetectInstance(&response, conf)
	return ret, nil
}
