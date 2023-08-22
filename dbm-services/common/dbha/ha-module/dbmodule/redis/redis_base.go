package redis

import (
	"fmt"
	"math/rand"
	"strconv"
	"time"

	"dbm-services/common/dbha/ha-module/client"
	"dbm-services/common/dbha/ha-module/config"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/dbutil"
	"dbm-services/common/dbha/ha-module/log"
	"dbm-services/common/dbha/ha-module/types"
	"dbm-services/common/dbha/ha-module/util"
)

// PolarisInfo TODO
type PolarisInfo struct {
	Namespace string
	Service   string
	Token     string
}

// CLBInfo TODO
type CLBInfo struct {
	Region        string
	LoadBalanceId string
	ListenId      string
}

// DNSInfo TODO
type DNSInfo struct {
	Domain string
}

// GWInfo TODO
type GWInfo struct {
	PolarisFlag bool
	Polaris     []PolarisInfo
	CLBFlag     bool
	CLB         []CLBInfo
	DNSFlag     bool
	DNS         []DNSInfo
}

// RedisSwitchInfo TODO
type RedisSwitchInfo struct {
	dbutil.BaseSwitch
	AdminPort       int
	ApiGw           GWInfo
	DnsClient       *client.NameServiceClient
	PolarisGWClient *client.NameServiceClient
	MasterConf      string
	SlaveConf       string
	Proxy           []dbutil.ProxyInfo
	Slave           []RedisSlaveInfo
	Pass            string
	Timeout         int
}

// RedisSlaveInfo TODO
type RedisSlaveInfo struct {
	Ip   string `json:"ip"`
	Port int    `json:"port"`
}

// RedisDetectBase TODO
type RedisDetectBase struct {
	dbutil.BaseDetectDB
	Pass    string
	Timeout int
}

// RedisDetectResponse TODO
type RedisDetectResponse struct {
	dbutil.BaseDetectDBResponse
	Pass string `json:"pass"`
}

// RedisDetectInfoFromCmDB TODO
type RedisDetectInfoFromCmDB struct {
	Ip          string
	Port        int
	App         string
	ClusterType string
	MetaType    string
	Pass        string
	Cluster     string
}

// RedisProxySwitchInfo TODO
type RedisProxySwitchInfo struct {
	dbutil.BaseSwitch
	AdminPort       int
	ApiGw           GWInfo
	DnsClient       *client.NameServiceClient
	PolarisGWClient *client.NameServiceClient
	Pass            string
}

// CheckSSH redis do ssh check
func (ins *RedisDetectBase) CheckSSH() error {
	touchFile := fmt.Sprintf("%s_%s_%d", ins.SshInfo.Dest, util.LocalIp, ins.Port)

	touchStr := fmt.Sprintf("touch %s && if [ -d \"/data1/dbha\" ]; then touch /data1/dbha/%s ; fi "+
		"&& if [ -d \"/data/dbha\" ]; then touch /data/dbha/%s ; fi", touchFile, touchFile, touchFile)

	if err := ins.DoSSH(touchStr); err != nil {
		log.Logger.Errorf("RedisDetection do ssh failed. err:%s", err.Error())
		return err
	}
	return nil
}

// ShowSwitchInstanceInfo TODO
func (ins *RedisProxySwitchInfo) ShowSwitchInstanceInfo() string {
	str := fmt.Sprintf("ip:%s, port:%d, IDC:%s, status:%s, app:%s, cluster_type:%s, machine_type:%s",
		ins.Ip, ins.Port, ins.IDC, ins.Status, ins.App, ins.ClusterType, ins.MetaType)
	return str
}

// KickOffDns TODO
func (ins *RedisProxySwitchInfo) KickOffDns() error {
	if !ins.ApiGw.DNSFlag {
		log.Logger.Infof("no need kickDNS,info:%s",
			ins.ShowSwitchInstanceInfo())
		return nil
	}

	for _, dnsInfo := range ins.ApiGw.DNS {
		ipInfos, err := ins.DnsClient.GetDomainInfoByDomain(dnsInfo.Domain)
		if err != nil {
			log.Logger.Errorf("get domain info by domain name failed. err:%s, info:{%s}",
				err.Error(), ins.ShowSwitchInstanceInfo())
			return err
		}

		if len(ipInfos) == 0 {
			log.Logger.Errorf("domain name: %s without ip. info:{%s}",
				dnsInfo.Domain, ins.ShowSwitchInstanceInfo())
			return fmt.Errorf("domain name: %s without ip", dnsInfo.Domain)
		} else if len(ipInfos) == 1 {
			log.Logger.Warnf("domain name: %s only one ip. so we skip it. info:{%s}",
				dnsInfo.Domain, ins.ShowSwitchInstanceInfo())
		} else {
			err = ins.DnsClient.DeleteDomain(
				dnsInfo.Domain, ins.App, ins.Ip, ins.Port,
			)
			if err != nil {
				log.Logger.Errorf("delete domain %s failed. err:%s, info:{%s}",
					dnsInfo.Domain, err.Error(), ins.ShowSwitchInstanceInfo())
				return err
			}
			log.Logger.Infof("delete domain %s success. info:{%s}",
				dnsInfo.Domain, ins.ShowSwitchInstanceInfo())
		}
	}
	return nil
}

// KickOffClb TODO
func (ins *RedisProxySwitchInfo) KickOffClb() error {
	if !ins.ApiGw.CLBFlag {
		log.Logger.Infof("switch proxy no need to kickoff CLB,info:%s",
			ins.ShowSwitchInstanceInfo())
		return nil
	}

	for _, clbInfo := range ins.ApiGw.CLB {
		ips, err := ins.PolarisGWClient.ClbGetTargets(
			clbInfo.Region, clbInfo.LoadBalanceId, clbInfo.ListenId,
		)
		if err != nil {
			log.Logger.Errorf("call ClbGetTargets failed,info:%s",
				ins.ShowSwitchInstanceInfo())
			return err
		}

		addr := fmt.Sprintf("%s:%d", ins.Ip, ins.Port)
		if len(ips) > 1 {
			err := ins.PolarisGWClient.ClbDeRegister(
				clbInfo.Region, clbInfo.LoadBalanceId, clbInfo.ListenId, addr,
			)
			if err != nil {
				log.Logger.Errorf("Kickoff %s from clb failed,info:%s",
					addr, ins.ShowSwitchInstanceInfo())
				return err
			}
		} else {
			log.Logger.Infof("CLB only left one ip, and no need to kickoff,info:%s",
				ins.ShowSwitchInstanceInfo())
		}
	}
	return nil
}

// KickOffPolaris TODO
func (ins *RedisProxySwitchInfo) KickOffPolaris() error {
	if !ins.ApiGw.PolarisFlag {
		log.Logger.Infof("switch proxy no need to kickoff Polaris,info:%s",
			ins.ShowSwitchInstanceInfo())
		return nil
	}

	for _, pinfo := range ins.ApiGw.Polaris {
		ips, err := ins.PolarisGWClient.GetPolarisTargets(pinfo.Service)
		if err != nil {
			log.Logger.Errorf("call GetPolarisTargets failed,info:%s,err:%s",
				ins.ShowSwitchInstanceInfo(), err.Error())
			return err
		}

		addr := fmt.Sprintf("%s:%d", ins.Ip, ins.Port)
		if len(ips) > 1 {
			err := ins.PolarisGWClient.PolarisUnBindTarget(
				pinfo.Service, pinfo.Token, addr)
			if err != nil {
				log.Logger.Errorf("Kickoff %s from polaris failed,info:%s,err=%s",
					addr, ins.ShowSwitchInstanceInfo(), err.Error())
				return err
			}
		} else {
			log.Logger.Infof("Polaris only left one ip, and no need to kickoff,info:%s",
				ins.ShowSwitchInstanceInfo())
		}
	}
	return nil
}

// CheckFetchEntryDetail TODO
func (ins *RedisProxySwitchInfo) CheckFetchEntryDetail() bool {
	if ins.ApiGw.PolarisFlag || ins.ApiGw.CLBFlag || ins.ApiGw.DNSFlag {
		return true
	} else {
		return false
	}
}

// GetEntryDetailInfo TODO
func (ins *RedisProxySwitchInfo) GetEntryDetailInfo() error {
	entry, err := ins.CmDBClient.GetEntryDetail(ins.Cluster)
	if err != nil {
		log.Logger.Errorf("GetEntryDetail failed, info:%s,err:%s",
			ins.ShowSwitchInstanceInfo(), err.Error())
		return err
	}

	clusterEntryInfo, ok := entry[ins.Cluster]
	if !ok {
		entryErr := fmt.Errorf("GetEntryDetail can not find [%s] in [%v]",
			ins.Cluster, entry)
		log.Logger.Errorf(entryErr.Error())
		return entryErr
	}

	entryInfo, ok := clusterEntryInfo.(map[string]interface{})
	if !ok {
		entryErr := fmt.Errorf("GetEntryDetail transfer type fail,[%v]",
			clusterEntryInfo)
		log.Logger.Errorf(entryErr.Error())
		return entryErr
	}
	err = ParseAPIGWInfo(entryInfo, &ins.ApiGw)
	if err != nil {
		log.Logger.Errorf("Parse APIGW failed, info:%s,err:%s",
			ins.ShowSwitchInstanceInfo(), err.Error())
		return err
	}
	return nil
}

// UnMarshalRedisInstanceByCmdb TODO
func UnMarshalRedisInstanceByCmdb(instances []interface{},
	uClusterType string, uMetaType string) ([]*RedisDetectInfoFromCmDB, error) {
	var (
		err error
		ret []*RedisDetectInfoFromCmDB
	)

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

		inf, ok = ins["cluster"]
		if !ok {
			err = fmt.Errorf("umarshal failed. cluster not exist")
			log.Logger.Errorf(err.Error())
			return nil, err
		}
		cluster := inf.(string)

		detechInfo := &RedisDetectInfoFromCmDB{
			Ip:          ip,
			Port:        port,
			App:         app,
			ClusterType: clusterType,
			MetaType:    metaType,
			Cluster:     cluster,
		}

		ret = append(ret, detechInfo)
	}
	return ret, nil
}

// CreateRedisProxySwitchInfo TODO
func CreateRedisProxySwitchInfo(
	instance interface{}, conf *config.Config,
) (*RedisProxySwitchInfo, error) {
	var err error

	ins := instance.(map[string]interface{})
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

	inf, ok = ins["cluster"]
	if !ok {
		err = fmt.Errorf("umarshal failed. cluster not exist")
		log.Logger.Errorf(err.Error())
		return nil, err
	}
	cluster := inf.(string)

	inf, ok = ins["admin_port"]
	if !ok {
		err = fmt.Errorf("umarshal failed. admin_port not exist")
		log.Logger.Errorf(err.Error())
		return nil, err
	}
	adminPort := int(inf.(float64))

	inf, ok = ins["bind_entry"]
	if !ok {
		err = fmt.Errorf("umarshal failed. bind_entry not exist")
		log.Logger.Errorf(err.Error())
		return nil, err
	}
	bindEntry := inf.(map[string]interface{})

	cmdbClient := client.NewCmDBClient(&conf.DBConf.CMDB, conf.GetCloudId())
	hadbClient := client.NewHaDBClient(&conf.DBConf.HADB, conf.GetCloudId())

	swIns := RedisProxySwitchInfo{
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
	}

	_, ok = bindEntry["dns"]
	if !ok {
		log.Logger.Infof("switch info not contain dns")
		swIns.ApiGw.DNSFlag = false
	} else {
		swIns.ApiGw.DNSFlag = true
		swIns.DnsClient = client.NewNameServiceClient(&conf.DNS.BindConf, conf.GetCloudId())
	}

	_, ok = bindEntry["polaris"]
	if !ok {
		log.Logger.Infof("switch info not contain polaris")
		swIns.ApiGw.PolarisFlag = false
	} else {
		swIns.ApiGw.PolarisFlag = true
	}

	_, ok = bindEntry["clb"]
	if !ok {
		log.Logger.Infof("switch info not contain clb")
		swIns.ApiGw.CLBFlag = false
	} else {
		swIns.ApiGw.CLBFlag = true
	}
	if swIns.ApiGw.CLBFlag || swIns.ApiGw.PolarisFlag {
		swIns.PolarisGWClient = client.NewNameServiceClient(&conf.DNS.PolarisConf, conf.GetCloudId())
	}

	return &swIns, nil
}

// ParseAPIGWInfo TODO
func ParseAPIGWInfo(entryDetail map[string]interface{}, apiGW *GWInfo) error {
	if nil == apiGW {
		return fmt.Errorf("input apiGW is nil")
	}

	log.Logger.Infof("input entryDetail:%v", entryDetail)
	if apiGW.PolarisFlag {
		pVal, ok := entryDetail["polaris"]
		if !ok {
			err := fmt.Errorf("have PolarisFlag ture but entryDetail lack polaris")
			log.Logger.Errorf(err.Error())
			return err
		} else {
			pArr := pVal.([]interface{})
			if nil == pArr {
				return fmt.Errorf("type trans failed while parse polaris")
			}
			for _, polaris := range pArr {
				var pIns PolarisInfo
				pInfo := polaris.(map[string]interface{})
				pname, pok := pInfo["polaris_name"]
				if pok {
					pIns.Service = pname.(string)
				}
				ptoken, pok := pInfo["polaris_token"]
				if pok {
					pIns.Token = ptoken.(string)
				}
				apiGW.Polaris = append(apiGW.Polaris, pIns)
			}
		}
	}

	if apiGW.CLBFlag {
		cVal, ok := entryDetail["clb"]
		if !ok {
			err := fmt.Errorf("have CLBFlag ture but entryDetail lack clb")
			log.Logger.Errorf(err.Error())
			return err
		} else {
			cArr := cVal.([]interface{})
			if nil == cArr {
				return fmt.Errorf("type trans failed while parse CLB")
			}
			for _, clb := range cArr {
				var cins CLBInfo
				cinfo := clb.(map[string]interface{})
				clbid, cok := cinfo["clb_id"]
				if cok {
					cins.LoadBalanceId = clbid.(string)
				}
				listenId, cok := cinfo["listener_id"]
				if cok {
					cins.ListenId = listenId.(string)
				}
				domain, cok := cinfo["clb_domain"]
				if cok {
					cins.Region = domain.(string)
				}
			}
		}
	}

	if apiGW.DNSFlag {
		dVal, ok := entryDetail["dns"]
		if !ok {
			err := fmt.Errorf("have DNSFlag ture but entryDetail lack dns")
			log.Logger.Errorf(err.Error())
			return err
		} else {
			dArr := dVal.([]interface{})
			if nil == dArr {
				return fmt.Errorf("type trans failed while parse CLB")
			}
			for _, dns := range dArr {
				var dnsIns DNSInfo
				dinfo := dns.(map[string]interface{})
				domain, dok := dinfo["domain"]
				if dok {
					dnsIns.Domain = domain.(string)
				}
				apiGW.DNS = append(apiGW.DNS, dnsIns)
			}
		}
	}

	return nil
}

// CreateRedisSwitchInfo TODO
func CreateRedisSwitchInfo(instance interface{}, conf *config.Config) (*RedisSwitchInfo, error) {
	var err error

	ins := instance.(map[string]interface{})
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

	inf, ok = ins["cluster"]
	if !ok {
		err = fmt.Errorf("umarshal failed. cluster not exist")
		log.Logger.Errorf(err.Error())
		return nil, err
	}
	cluster := inf.(string)

	_, ok = ins["bind_entry"]
	if !ok {
		err = fmt.Errorf("umarshal failed. bind_entry not exist")
		log.Logger.Errorf(err.Error())
		return nil, err
	}

	cmdbClient := client.NewCmDBClient(&conf.DBConf.CMDB, conf.GetCloudId())
	hadbClient := client.NewHaDBClient(&conf.DBConf.HADB, conf.GetCloudId())

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

	swIns := RedisSwitchInfo{
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
		Timeout: conf.DBConf.Redis.Timeout,
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
		swIns.Slave = append(swIns.Slave, RedisSlaveInfo{
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
	return &swIns, nil
}

// GetDetectBaseByInfo TODO
func GetDetectBaseByInfo(ins *RedisDetectInfoFromCmDB,
	dbType string, conf *config.Config) *RedisDetectBase {
	passwd := GetRedisMachinePasswd(ins.App, conf)
	return &RedisDetectBase{
		BaseDetectDB: dbutil.BaseDetectDB{
			Ip:             ins.Ip,
			Port:           ins.Port,
			App:            ins.App,
			DBType:         types.DBType(dbType),
			ReporterTime:   time.Unix(0, 0),
			ReportInterval: conf.AgentConf.ReportInterval + rand.Intn(20),
			Status:         constvar.DBCheckSuccess,
			Cluster:        ins.Cluster,
			ClusterType:    ins.ClusterType,
			SshInfo: dbutil.Ssh{
				Port:    conf.SSH.Port,
				User:    conf.SSH.User,
				Pass:    passwd,
				Dest:    conf.SSH.Dest,
				Timeout: conf.SSH.Timeout,
			},
		},
		Pass:    ins.Pass,
		Timeout: conf.DBConf.Redis.Timeout,
	}
}

// GetDetectBaseByRsp TODO
func GetDetectBaseByRsp(ins *RedisDetectResponse,
	dbType string, conf *config.Config) *RedisDetectBase {
	passwd := GetRedisMachinePasswd(ins.App, conf)
	return &RedisDetectBase{
		BaseDetectDB: dbutil.BaseDetectDB{
			Ip:             ins.DBIp,
			Port:           ins.DBPort,
			App:            ins.App,
			DBType:         types.DBType(dbType),
			ReporterTime:   time.Unix(0, 0),
			ReportInterval: conf.AgentConf.ReportInterval + rand.Intn(20),
			Status:         types.CheckStatus(ins.Status),
			Cluster:        ins.Cluster,
			SshInfo: dbutil.Ssh{
				Port:    conf.SSH.Port,
				User:    conf.SSH.User,
				Pass:    passwd,
				Dest:    conf.SSH.Dest,
				Timeout: conf.SSH.Timeout,
			},
		},
		Pass:    ins.Pass,
		Timeout: conf.DBConf.Redis.Timeout,
	}
}
