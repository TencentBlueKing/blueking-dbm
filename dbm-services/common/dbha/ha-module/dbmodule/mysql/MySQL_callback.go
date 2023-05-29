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

// UnMarshalMySQLInstanceByCmdb convert cmdb instance info to MySQLDetectInstanceInfoFromCmDB
func UnMarshalMySQLInstanceByCmdb(instances []interface{},
	uClusterType string, uMetaType string) ([]*MySQLDetectInstanceInfoFromCmDB, error) {
	var (
		err error
		ret []*MySQLDetectInstanceInfoFromCmDB
	)
	cache := map[string]*MySQLDetectInstanceInfoFromCmDB{}

	for _, v := range instances {
		ins := v.(map[string]interface{})
		inf, ok := ins["cluster_type"]
		if !ok {
			err = fmt.Errorf("umarshal failed. cluster_type not exist")
			log.Logger.Errorf(err.Error())
			return nil, err
		}
		clusterType := inf.(string)
		if clusterType != uClusterType {
			continue
		}
		inf, ok = ins["machine_type"]
		if !ok {
			err = fmt.Errorf("umarshal failed. machine_type not exist")
			log.Logger.Errorf(err.Error())
			return nil, err
		}
		metaType := inf.(string)
		if metaType != uMetaType {
			continue
		}
		inf, ok = ins["status"]
		if !ok {
			err = fmt.Errorf("umarshal failed. status not exist")
			log.Logger.Errorf(err.Error())
			return nil, err
		}
		status := inf.(string)
		if status != constvar.RUNNING && status != constvar.AVAILABLE {
			continue
		}
		inf, ok = ins["cluster"]
		if !ok {
			err = fmt.Errorf("umarshal failed. cluster not exist")
			log.Logger.Errorf(err.Error())
			return nil, err
		}
		cluster := inf.(string)

		inf, ok = ins["ip"]
		if !ok {
			err = fmt.Errorf("umarshal failed. ip not exist")
			log.Logger.Errorf(err.Error())
			return nil, err
		}
		ip := inf.(string)
		inf, ok = ins["port"]
		if !ok {
			err = fmt.Errorf("umarshal failed. port not exist")
			log.Logger.Errorf(err.Error())
			return nil, err
		}
		port := int(inf.(float64))
		inf, ok = ins["bk_biz_id"]
		if !ok {
			err = fmt.Errorf("umarshal failed. app not exist")
			log.Logger.Errorf(err.Error())
			return nil, err
		}
		app := strconv.Itoa(int(inf.(float64)))
		cacheIns, ok := cache[ip]
		if ok {
			if port < cacheIns.Port {
				cache[ip] = &MySQLDetectInstanceInfoFromCmDB{
					Ip:          ip,
					Port:        port,
					App:         app,
					ClusterType: clusterType,
					MetaType:    metaType,
					Cluster:     cluster,
				}
			}
		} else {
			cache[ip] = &MySQLDetectInstanceInfoFromCmDB{
				Ip:          ip,
				Port:        port,
				App:         app,
				ClusterType: clusterType,
				MetaType:    metaType,
				Cluster:     cluster,
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
	var err error
	var ret []dbutil.DataBaseSwitch
	for _, v := range instances {
		ins := v.(map[string]interface{})
		inf, ok := ins["ip"]
		if !ok {
			err = fmt.Errorf("umarshal failed. ip not exist")
			log.Logger.Errorf(err.Error())
			return nil, err
		}
		ip := inf.(string)

		inf, ok = ins["port"]
		if !ok {
			err = fmt.Errorf("umarshal failed. port not exist")
			log.Logger.Errorf(err.Error())
			return nil, err
		}
		port := int(inf.(float64))

		inf, ok = ins["bk_idc_city_id"]
		if !ok {
			err = fmt.Errorf("umarshal failed. role not exist")
			log.Logger.Errorf(err.Error())
			return nil, err
		}
		idc := strconv.Itoa(int(inf.(float64)))

		inf, ok = ins["instance_role"]
		if !ok {
			err = fmt.Errorf("umarshal failed. role not exist")
			log.Logger.Errorf(err.Error())
			return nil, err
		}
		role := inf.(string)

		inf, ok = ins["status"]
		if !ok {
			err = fmt.Errorf("umarshal failed. ip not exist")
			log.Logger.Errorf(err.Error())
			return nil, err
		}
		status := inf.(string)

		inf, ok = ins["cluster"]
		if !ok {
			err = fmt.Errorf("umarshal failed. cluster not exist")
			log.Logger.Errorf(err.Error())
			return nil, err
		}
		cluster := inf.(string)

		inf, ok = ins["bk_biz_id"]
		if !ok {
			err = fmt.Errorf("umarshal failed. app not exist")
			log.Logger.Errorf(err.Error())
			return nil, err
		}
		app := strconv.Itoa(int(inf.(float64)))

		inf, ok = ins["cluster_type"]
		if !ok {
			err = fmt.Errorf("umarshal failed. cluster_type not exist")
			log.Logger.Errorf(err.Error())
			return nil, err
		}
		clusterType := inf.(string)

		inf, ok = ins["machine_type"]
		if !ok {
			err = fmt.Errorf("umarshal failed. machine_type not exist")
			log.Logger.Errorf(err.Error())
			return nil, err
		}
		metaType := inf.(string)

		inf, ok = ins["receiver"]
		if !ok {
			err = fmt.Errorf("umarshal failed. receiver not exist")
			log.Logger.Errorf(err.Error())
			return nil, err
		}
		slave := inf.([]interface{})

		inf, ok = ins["proxyinstance_set"]
		if !ok {
			err = fmt.Errorf("umarshal failed. proxyinstance_set not exist")
			log.Logger.Errorf(err.Error())
			return nil, err
		}
		proxy := inf.([]interface{})

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
				Ip:          ip,
				Port:        port,
				IDC:         idc,
				Status:      status,
				App:         app,
				ClusterType: clusterType,
				MetaType:    metaType,
				Cluster:     cluster,
				CmDBClient:  cmdbClient,
				HaDBClient:  hadbClient,
			},
			Role:                     role,
			AllowedChecksumMaxOffset: conf.GMConf.GCM.AllowedChecksumMaxOffset,
			AllowedSlaveDelayMax:     conf.GMConf.GCM.AllowedSlaveDelayMax,
			AllowedTimeDelayMax:      conf.GMConf.GCM.AllowedTimeDelayMax,
			ExecSlowKBytes:           conf.GMConf.GCM.ExecSlowKBytes,
			MySQLUser:                conf.DBConf.MySQL.User,
			MySQLPass:                conf.DBConf.MySQL.Pass,
			ProxyUser:                conf.DBConf.MySQL.ProxyUser,
			ProxyPass:                conf.DBConf.MySQL.ProxyPass,
			Timeout:                  conf.DBConf.MySQL.Timeout,
		}

		for _, rawInfo := range slave {
			mapInfo := rawInfo.(map[string]interface{})
			inf, ok = mapInfo["ip"]
			if !ok {
				err = fmt.Errorf("umarshal failed. slave ip not exist")
				log.Logger.Errorf(err.Error())
				return nil, err
			}
			slaveIp := inf.(string)
			inf, ok = mapInfo["port"]
			if !ok {
				err = fmt.Errorf("umarshal failed. slave port not exist")
				log.Logger.Errorf(err.Error())
				return nil, err
			}
			slavePort := inf.(float64)
			swIns.Slave = append(swIns.Slave, MySQLSlaveInfo{
				Ip:   slaveIp,
				Port: int(slavePort),
			})
		}

		for _, rawInfo := range proxy {
			mapInfo := rawInfo.(map[string]interface{})
			inf, ok = mapInfo["ip"]
			if !ok {
				err = fmt.Errorf("umarshal failed. proxy ip not exist")
				log.Logger.Errorf(err.Error())
				return nil, err
			}
			proxyIp := inf.(string)
			inf, ok = mapInfo["port"]
			if !ok {
				err = fmt.Errorf("umarshal failed. proxy port not exist")
				log.Logger.Errorf(err.Error())
				return nil, err
			}
			proxyPort := inf.(float64)
			inf, ok = mapInfo["admin_port"]
			if !ok {
				err = fmt.Errorf("umarshal failed. proxy port not exist")
				log.Logger.Errorf(err.Error())
				return nil, err
			}
			proxyAdminPort := inf.(float64)
			var status string
			inf, ok = mapInfo["status"]
			if !ok {
				status = ""
			} else {
				status = inf.(string)
			}
			swIns.Proxy = append(swIns.Proxy, dbutil.ProxyInfo{
				Ip:        proxyIp,
				Port:      int(proxyPort),
				AdminPort: int(proxyAdminPort),
				Status:    status,
			})
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
