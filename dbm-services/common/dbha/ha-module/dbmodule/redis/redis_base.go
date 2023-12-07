package redis

import (
	"encoding/json"
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
)

// GWInfo the gateway information
type GWInfo struct {
	PolarisFlag  bool
	CLBFlag      bool
	DNSFlag      bool
	DNSForword   bool
	ServiceEntry dbutil.BindEntry
}

// RedisSwitchInfo redis switch instance information
type RedisSwitchInfo struct {
	dbutil.BaseSwitch
	AdminPort int
	Proxy     []dbutil.ProxyInfo
	Slave     []dbutil.SlaveInfo
	Pass      string
	Role      string
	Timeout   int
}

// RedisDetectBase redis detect information
type RedisDetectBase struct {
	dbutil.BaseDetectDB
	Pass    string
	Timeout int
}

// RedisDetectResponse redis detect response
type RedisDetectResponse struct {
	dbutil.BaseDetectDBResponse
	Pass string `json:"pass"`
}

// RedisDetectInfoFromCmDB redis detect information from cmdb
type RedisDetectInfoFromCmDB struct {
	Ip          string
	Port        int
	App         string
	ClusterType string
	MetaType    string
	Pass        string
	Cluster     string
	ClusterId   int
}

// RedisProxySwitchInfo redis proxy switch information
type RedisProxySwitchInfo struct {
	dbutil.BaseSwitch
	AdminPort int
	ApiGw     GWInfo
	Pass      string
}

// CheckSSH redis do ssh check
func (ins *RedisDetectBase) CheckSSH() error {
	touchFile := fmt.Sprintf("%s_%s_%d", ins.SshInfo.Dest, "agent", ins.Port)

	touchStr := fmt.Sprintf("touch %s && if [ -d \"/data1/dbha\" ]; then touch /data1/dbha/%s ; fi "+
		"&& if [ -d \"/data/dbha\" ]; then touch /data/dbha/%s ; fi", touchFile, touchFile, touchFile)

	if err := ins.DoSSH(touchStr); err != nil {
		log.Logger.Errorf("RedisDetection do ssh failed. err:%s", err.Error())
		return err
	}
	return nil
}

// GetType return dbType
func (ins *RedisDetectBase) GetType() types.DBType {
	return ins.DBType
}

// GetDetectType return clusterType
func (ins *RedisDetectBase) GetDetectType() string {
	return ins.ClusterType
}

// GetDetectBaseByInfo get detect instance by cmdb
func GetDetectBaseByInfo(ins *RedisDetectInfoFromCmDB,
	dbType string, conf *config.Config) *RedisDetectBase {
	passwd := GetRedisMachinePasswd(conf)
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
			ClusterId:      ins.ClusterId,
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

// GetDetectBaseByRsp get detect instance by agent response
func GetDetectBaseByRsp(ins *RedisDetectResponse,
	dbType string, conf *config.Config) *RedisDetectBase {
	passwd := GetRedisMachinePasswd(conf)
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
			ClusterType:    ins.ClusterType,
			ClusterId:      ins.ClusterId,
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

// ShowSwitchInstanceInfo show instance information
func (ins *RedisProxySwitchInfo) ShowSwitchInstanceInfo() string {
	str := fmt.Sprintf("ip:%s, port:%d, IDC:%d, status:%s, app:%s, cluster_type:%s, machine_type:%s",
		ins.Ip, ins.Port, ins.IdcID, ins.Status, ins.App, ins.ClusterType, ins.MetaType)
	return str
}

// KickOffDns kick instance from dns
func (ins *RedisProxySwitchInfo) KickOffDns() error {
	if !ins.ApiGw.DNSFlag {
		log.Logger.Infof("no need kickDNS,info:%s",
			ins.ShowSwitchInstanceInfo())
		return nil
	}

	// kick off instance from dns
	return ins.DeleteNameService(dbutil.BindEntry{
		Dns: ins.ApiGw.ServiceEntry.Dns,
	})
}

// KickOffClb TODO
func (ins *RedisProxySwitchInfo) KickOffClb() error {
	if !ins.ApiGw.CLBFlag {
		log.Logger.Infof("switch proxy no need to kickoff CLB,info:%s",
			ins.ShowSwitchInstanceInfo())
		return nil
	}

	// kick off instance from clb
	return ins.DeleteNameService(dbutil.BindEntry{
		Clb: ins.ApiGw.ServiceEntry.Clb,
	})
}

// KickOffPolaris TODO
func (ins *RedisProxySwitchInfo) KickOffPolaris() error {
	if !ins.ApiGw.PolarisFlag {
		log.Logger.Infof("switch proxy no need to kickoff Polaris,info:%s",
			ins.ShowSwitchInstanceInfo())
		return nil
	}

	// kick off instance from polaris
	return ins.DeleteNameService(dbutil.BindEntry{
		Polaris: ins.ApiGw.ServiceEntry.Polaris,
	})
}

// UnMarshalRedisInstanceByCmdb parse the information from cmdb
func UnMarshalRedisInstanceByCmdb(instances []interface{},
	uClusterType string) ([]*RedisDetectInfoFromCmDB, error) {
	var (
		err error
		ret []*RedisDetectInfoFromCmDB
	)

	for _, v := range instances {
		vMap := v.(map[string]interface{})
		inf, ok := vMap["cluster_type"]
		if !ok {
			err = fmt.Errorf("umarshal failed. cluster_type not exist")
			log.Logger.Errorf(err.Error())
			return nil, err
		}
		clusterType := inf.(string)
		if clusterType != uClusterType {
			continue
		}

		ins := dbutil.DBInstanceInfoDetail{}
		rawData, err := json.Marshal(v)
		if err != nil {
			return nil, fmt.Errorf("marshal instance info failed:%s", err.Error())
		}
		if err = json.Unmarshal(rawData, &ins); err != nil {
			return nil, fmt.Errorf("unmarshal instance info failed:%s", err.Error())
		}

		detechInfo := &RedisDetectInfoFromCmDB{
			Ip:          ins.IP,
			Port:        ins.Port,
			App:         strconv.Itoa(ins.BKBizID),
			ClusterType: ins.ClusterType,
			MetaType:    ins.MachineType,
			Cluster:     ins.Cluster,
			ClusterId:   ins.ClusterId,
		}

		ret = append(ret, detechInfo)
	}
	return ret, nil
}

// GetClusterAndMetaFromIns get cluster and meta from instance
func GetClusterAndMetaFromIns(instance interface{}) (string, string, error) {
	ins := instance.(map[string]interface{})
	inf, ok := ins["cluster_type"]
	if !ok {
		err := fmt.Errorf("umarshal failed. cluster_type not exist")
		log.Logger.Errorf(err.Error())
		return "", "", err
	}
	clusterType := inf.(string)

	inf, ok = ins["machine_type"]
	if !ok {
		err := fmt.Errorf("umarshal failed. meta_type not exist")
		log.Logger.Errorf(err.Error())
		return "", "", err
	}
	metaType := inf.(string)
	return clusterType, metaType, nil
}

// CreateRedisProxySwitchInfo
func CreateRedisProxySwitchInfo(
	instance interface{}, conf *config.Config,
) (*RedisProxySwitchInfo, error) {
	var err error

	ins := dbutil.DBInstanceInfoDetail{}
	rawData, err := json.Marshal(instance)
	if err != nil {
		return nil, fmt.Errorf("marshal instance info failed:%s", err.Error())
	}
	if err = json.Unmarshal(rawData, &ins); err != nil {
		return nil, fmt.Errorf("unmarshal instance info failed:%s", err.Error())
	}

	cmdbClient := client.NewCmDBClient(&conf.DBConf.CMDB, conf.GetCloudId())
	hadbClient := client.NewHaDBClient(&conf.DBConf.HADB, conf.GetCloudId())

	swIns := RedisProxySwitchInfo{
		BaseSwitch: dbutil.BaseSwitch{
			Ip:          ins.IP,
			Port:        ins.Port,
			IdcID:       ins.BKIdcCityID,
			Status:      ins.Status,
			App:         strconv.Itoa(ins.BKBizID),
			ClusterType: ins.ClusterType,
			MetaType:    ins.MachineType,
			Cluster:     ins.Cluster,
			ClusterId:   ins.ClusterId,
			CmDBClient:  cmdbClient,
			HaDBClient:  hadbClient,
			Config:      conf,
		},
		AdminPort: ins.AdminPort,
	}

	if ins.BindEntry.Dns == nil {
		swIns.ApiGw.DNSFlag = false
	} else {
		swIns.ApiGw.DNSFlag = true
		swIns.ApiGw.ServiceEntry.Dns = ins.BindEntry.Dns
		for _, dns := range ins.BindEntry.Dns {
			if dns.ForwardEntryId != 0 {
				swIns.ApiGw.DNSForword = true
			}
		}
	}

	if ins.BindEntry.Polaris != nil && len(ins.BindEntry.Polaris) > 0 {
		swIns.ApiGw.PolarisFlag = true
		swIns.ApiGw.ServiceEntry.Polaris = ins.BindEntry.Polaris
	} else {
		swIns.ApiGw.PolarisFlag = false
	}

	if ins.BindEntry.Clb != nil && len(ins.BindEntry.Clb) > 0 {
		swIns.ApiGw.CLBFlag = true
		swIns.ApiGw.ServiceEntry.Clb = ins.BindEntry.Clb
	} else {
		swIns.ApiGw.CLBFlag = false
	}
	return &swIns, nil
}

// CreateRedisSwitchInfo create redis switch instance
func CreateRedisSwitchInfo(instance interface{}, conf *config.Config) (*RedisSwitchInfo, error) {
	var err error

	ins := dbutil.DBInstanceInfoDetail{}
	rawData, err := json.Marshal(instance)
	if err != nil {
		return nil, fmt.Errorf("marshal instance info failed:%s", err.Error())
	}
	if err = json.Unmarshal(rawData, &ins); err != nil {
		return nil, fmt.Errorf("unmarshal instance info failed:%s", err.Error())
	}

	cmdbClient := client.NewCmDBClient(&conf.DBConf.CMDB, conf.GetCloudId())
	hadbClient := client.NewHaDBClient(&conf.DBConf.HADB, conf.GetCloudId())

	swIns := RedisSwitchInfo{
		BaseSwitch: dbutil.BaseSwitch{
			Ip:          ins.IP,
			Port:        ins.Port,
			IdcID:       ins.BKIdcCityID,
			Status:      ins.Status,
			App:         strconv.Itoa(ins.BKBizID),
			ClusterType: ins.ClusterType,
			MetaType:    ins.MachineType,
			Cluster:     ins.Cluster,
			ClusterId:   ins.ClusterId,
			CmDBClient:  cmdbClient,
			HaDBClient:  hadbClient,
			Config:      conf,
		},
		Timeout: conf.DBConf.Redis.Timeout,
		Slave:   ins.Receiver,
		Proxy:   ins.ProxyInstanceSet,
		Role:    ins.InstanceRole,
	}
	return &swIns, nil
}
