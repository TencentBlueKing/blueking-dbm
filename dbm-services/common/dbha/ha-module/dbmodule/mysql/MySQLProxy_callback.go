package mysql

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

// NewMySQLProxyInstanceByCmDB Agent通过CMDB获取的信息来生成需要探测的实例
func NewMySQLProxyInstanceByCmDB(instances []interface{},
	conf *config.Config) ([]dbutil.DataBaseDetect, error) {
	var (
		err          error
		unmarshalIns []*MySQLDetectInstanceInfoFromCmDB
		ret          []dbutil.DataBaseDetect
	)

	unmarshalIns, err = UnMarshalMySQLInstanceByCmdb(instances, constvar.MySQLClusterType,
		constvar.MySQLProxyMetaType)

	if err != nil {
		return nil, err
	}

	for _, uIns := range unmarshalIns {
		pIns := &MySQLProxyDetectInstanceInfoFromCmDB{
			MySQLDetectInstanceInfoFromCmDB: *uIns,
		}
		ret = append(ret, NewMySQLProxyDetectInstance1(pIns, conf))
	}

	return ret, err
}

// DeserializeMySQLProxy 反序列化从Agent上报上来的故障实例
func DeserializeMySQLProxy(jsonInfo []byte, conf *config.Config) (dbutil.DataBaseDetect, error) {
	response := MySQLProxyDetectResponse{}
	err := json.Unmarshal(jsonInfo, &response)
	if err != nil {
		log.Logger.Errorf("json unmarshal failed. jsoninfo:\n%s\n, err:%s", string(jsonInfo), err.Error())
		return nil, err
	}
	var ret dbutil.DataBaseDetect
	ret = NewMySQLProxyDetectInstance2(&response, constvar.MySQLProxy, conf)
	return ret, nil
}

// NewMySQLProxySwitchInstance get instance switch info
func NewMySQLProxySwitchInstance(instances []interface{}, conf *config.Config) ([]dbutil.DataBaseSwitch, error) {
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

		inf, ok = ins["admin_port"]
		if !ok {
			err = fmt.Errorf("umarshal failed. admin_port not exist")
			log.Logger.Errorf(err.Error())
			return nil, err
		}
		adminPort := int(inf.(float64))

		inf, ok = ins["bind_entry"]
		if !ok {
			err = fmt.Errorf("umarshal failed. proxyinstance_set not exist")
			log.Logger.Errorf(err.Error())
			return nil, err
		}
		bindEntry := inf.(map[string]interface{})

		cmdbClient, err := client.NewCmDBClient(&conf.DBConf.CMDB, conf.GetCloudId())
		if err != nil {
			return nil, err
		}

		hadbClient, err := client.NewHaDBClient(&conf.DBConf.HADB, conf.GetCloudId())
		if err != nil {
			return nil, err
		}

		dnsClient, err := client.NewNameServiceClient(&conf.DNS.BindConf, conf.GetCloudId())
		if err != nil {
			return nil, err
		}

		swIns := MySQLProxySwitch{
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
			AdminPort: adminPort,
			DnsClient: dnsClient,
		}

		inf, ok = bindEntry["dns"]
		if !ok {
			err = fmt.Errorf("umarshal failed. dns not exist")
			log.Logger.Errorf(err.Error())
			return nil, err
		}
		swIns.Entry.Dns = inf.([]interface{})

		ret = append(ret, &swIns)
	}
	return ret, nil
}
