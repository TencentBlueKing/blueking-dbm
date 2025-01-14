// Package globalmonitor monitor whether component work normal
package globalmonitor

import (
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"dbm-services/bigdata/db-tools/dbactuator/pkg/util"
	"dbm-services/common/dbha/ha-module/client"
	"dbm-services/common/dbha/ha-module/config"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/log"
	"dbm-services/common/dbha/ha-module/monitor"
	"dbm-services/common/dbha/hadb-api/model"
)

// MachineInfo instance detail info from cmdb api
type MachineInfo struct {
	IP            string `json:"ip"`
	LogicalCityID int    `json:"logical_city_id"`
	ClusterType   string `json:"cluster_type"`
	MachineType   string `json:"machine_type"`
}

// MonitorComponent global monitor work struct
type MonitorComponent struct {
	// active type list for db detect, valid type in constant.go
	ActiveClusterType []string `yaml:"active_db_type"`
	//monitor  ip
	MonIp string
	// all configure file
	Conf *config.Config
	// global monitor configure fie
	MonitorConf *config.GlobalMonitorConfig
	// API client to access cmdb metadata
	CmDBClient *client.CmDBClient
	// API client to access hadb
	HaDBClient *client.HaDBClient
	//cmdb need detect ip list
	NeedDetectMachines map[string]struct{}
	//cmdb need detect city list
	NeedDetectCities map[int]struct{}
	//HA detected ip list
	DetectedMachines map[string]struct{}
	//HA detected city list
	DetectedCities map[int]struct{}
	//HA agent list
	AgentList []model.HaStatus
	//HA gm list
	GmList []model.HaStatus
	//alert info to bk
	AlertInfo monitor.MonitorInfo
	//hash mod use to batch fetch cmdb instance
	HashMod int
	//skip statistics city list
	IgnoreCityList []int
}

// NewMonitorComponent create new global monitor component
func NewMonitorComponent(conf *config.Config) *MonitorComponent {
	return &MonitorComponent{
		ActiveClusterType:  conf.GlobalMonitorConf.ActiveClusterType,
		Conf:               conf,
		MonitorConf:        conf.GlobalMonitorConf,
		CmDBClient:         client.NewCmDBClient(&conf.DBConf.CMDB, conf.GetCloudId()),
		HaDBClient:         client.NewHaDBClient(&conf.DBConf.HADB, conf.GetCloudId()),
		MonIp:              conf.GlobalMonitorConf.LocalIP,
		NeedDetectMachines: make(map[string]struct{}),
		NeedDetectCities:   make(map[int]struct{}),
		DetectedMachines:   make(map[string]struct{}),
		DetectedCities:     make(map[int]struct{}),
		HashMod:            conf.GlobalMonitorConf.HashMod,
		IgnoreCityList:     conf.GlobalMonitorConf.IgnoreCityList,
		AlertInfo: monitor.MonitorInfo{
			EventName:       constvar.DBHAEventGlobalMonitor,
			MonitorInfoType: constvar.MonitorInfoGlobal,
			Global: monitor.GlobalMonitor{
				ServerIp:           conf.Monitor.LocalIP,
				UnCoveredInsNumber: 0,
				UnCoveredCityIDs:   nil,
				NeedDetectNumber:   0,
				HADetectedNumber:   0,
			},
		},
	}
}

// Run global monitor
func (m *MonitorComponent) Run() error {
	for {
		time.Sleep(10 * time.Second)
		log.Logger.Infof("------------------global monitor run start-----------------")
		log.Logger.Debugf("try to get all ha componentinfo")
		if err := m.getAllHaComponentInfo(); err != nil {
			log.Logger.Errorf("get all HA component info failed:%s", err.Error())
			continue
		}
		if err := m.getAllDetectedMachineInfo(); err != nil {
			log.Logger.Errorf("get all HA detected machine failed:%s", err.Error())
			continue
		}
		if err := m.getAllNeedDetectMachineInfo(); err != nil {
			log.Logger.Errorf("get all CMDB need detect machine failed:%s", err.Error())
			continue
		}

		m.checkAllCovered()
		m.checkComponentNormal()
		m.reportHeartbeat()

		log.Logger.Infof("------------------global monitor run finish-----------------")
		time.Sleep(time.Duration(m.MonitorConf.ReportInterval) * time.Second)
	}
}

// RegisterMonitorInfoToHaDB register current agent info
func (m *MonitorComponent) RegisterMonitorInfoToHaDB() error {
	err := m.HaDBClient.RegisterDBHAInfo(
		m.MonIp,
		0,
		constvar.MONITOR,
		0,
		"",
		"ALL")
	if err != nil {
		return err
	}
	return nil
}

// reporterHeartbeat send agent heartbeat to HA-DB
func (m *MonitorComponent) reportHeartbeat() {
	err := m.HaDBClient.ReporterMonitorHeartbeat(m.MonIp, strings.Join(m.ActiveClusterType, ","))
	if err != nil {
		log.Logger.Errorf("report heartbeat failed:%s", err.Error())
	}
}

// checkAllCovered check if all instances is covered
func (m *MonitorComponent) checkAllCovered() {
	//undetected instances
	unCoveredMachineMap := map[string]struct{}{}
	//undetected logical_city_ids
	unCoveredCityMap := map[int]struct{}{}
	m.AlertInfo.Global.NeedDetectNumber = len(m.NeedDetectMachines)
	m.AlertInfo.Global.HADetectedNumber = len(m.DetectedMachines)
	log.Logger.Infof("all detected city num:%d", len(m.DetectedCities))
	log.Logger.Infof("all detected machine num:%d", len(m.DetectedMachines))
	log.Logger.Infof("all need detect city num:%d", len(m.NeedDetectCities))
	log.Logger.Infof("all need detect machine num:%d", len(m.NeedDetectMachines))

	for city, _ := range m.NeedDetectCities {
		if _, ok := m.DetectedCities[city]; ok {
			continue
		} else {
			unCoveredCityMap[city] = struct{}{}
		}
	}

	for ip := range m.NeedDetectMachines {
		if _, ok := m.DetectedMachines[ip]; ok {
			continue
		} else {
			unCoveredMachineMap[ip] = struct{}{}
		}
	}

	if len(unCoveredMachineMap) > 0 {
		log.Logger.Errorf("uncovered machine list:%#v", unCoveredMachineMap)
		if err := monitor.MonitorSend(fmt.Sprintf("%d machines not covered by dbha",
			len(unCoveredMachineMap)), m.AlertInfo); err != nil {
			log.Logger.Warnf(err.Error())
		}
	}

	if len(unCoveredCityMap) > 0 {
		for k := range unCoveredCityMap {
			m.AlertInfo.Global.UnCoveredCityIDs = append(m.AlertInfo.Global.UnCoveredCityIDs, k)
		}
		log.Logger.Errorf("uncovered city list:%#v", unCoveredCityMap)
		if err := monitor.MonitorSend(fmt.Sprintf("%d logical_city_ids not covered by dbha",
			len(unCoveredCityMap)), m.AlertInfo); err != nil {
			log.Logger.Warnf(err.Error())
		}
	}

	log.Logger.Debugf("global monitor info: %#v", m.AlertInfo.Global)
}

// checkComponentNormal check if all components is work normal
func (m *MonitorComponent) checkComponentNormal() {
	for _, agent := range m.AgentList {
		if agent.ReportInterval > 20 {
			msg := fmt.Sprintf("agent:%s, cluster_type:%s detect too slow:%d",
				agent.IP, agent.DbType, agent.ReportInterval)
			log.Logger.Errorf(msg)
			if err := monitor.MonitorSend(msg, m.AlertInfo); err != nil {
				log.Logger.Warnf(err.Error())
			}
			continue
		}
	}
	for _, gm := range m.GmList {
		if gm.ReportInterval > 300 {
			msg := fmt.Sprintf("gm:%s, Campuse:%s report too slow:%d", gm.IP, gm.Campus, gm.ReportInterval)
			log.Logger.Errorf(msg)
			if err := monitor.MonitorSend(msg, m.AlertInfo); err != nil {
				log.Logger.Warnf(err.Error())
			}
			continue
		}
	}
}

// getCmDBMachineByCluster get all cmdb instance by cluster type
func (m *MonitorComponent) getCmDBMachineByCluster(clusterType string, hashMod, hashValue int) error {
	num := 0
	req := client.DBInstanceByClusterTypeRequest{
		HashCnt:      hashMod,
		HashValue:    hashValue,
		ClusterTypes: []string{clusterType},
	}

	//get all instances by cluster type
	rawInfo, err := m.CmDBClient.GetDBInstanceByClusterType(req)
	if err != nil {
		minInfo := monitor.GetApiAlertInfo(constvar.CmDBInstanceUrl, err.Error())
		if e := monitor.MonitorSend("get instances failed", minInfo); e != nil {
			log.Logger.Warnf(e.Error())
		}
		return fmt.Errorf("fetch all cmdb instance failed:%s", err.Error())
	}

	for _, v := range rawInfo {
		cmdbIns := MachineInfo{}
		rawIns, jsonErr := json.Marshal(v)
		if jsonErr != nil {
			log.Logger.Errorf("marshal db instance info failed:%s", jsonErr.Error())
			return fmt.Errorf("get cmdb instance info failed:%s", jsonErr.Error())
		}
		if jsonErr = json.Unmarshal(rawIns, &cmdbIns); jsonErr != nil {
			log.Logger.Errorf("unmarshal db instance info failed:%s", jsonErr.Error())
			return fmt.Errorf("get cmdb instance info failed:%s", jsonErr.Error())
		}

		//should ignore some city
		if util.HasElem(cmdbIns.LogicalCityID, m.IgnoreCityList) {
			continue
		}

		//some cluster type only Proxy layer need HA, so we should skip its storage layer
		//should skip PredixyRedisCluster's storage layer
		if cmdbIns.ClusterType == constvar.PredixyRedisCluster &&
			cmdbIns.MachineType == constvar.TendisCacheMetaType {
			continue
		}
		//should skip TendisplusCluster's storage layer
		if cmdbIns.ClusterType == constvar.TendisplusCluster &&
			cmdbIns.MachineType == constvar.TendisplusMetaType {
			continue
		}
		//should skip MongoShardedCluster's storage layer
		if cmdbIns.ClusterType == constvar.MongoShardedCluster &&
			(cmdbIns.MachineType == constvar.MongodbMetaType ||
				cmdbIns.MachineType == constvar.MongoConfigMetaType) {
			continue
		}

		if _, ok := m.NeedDetectMachines[cmdbIns.IP]; !ok {
			m.NeedDetectMachines[cmdbIns.IP] = struct{}{}
		}
		if _, ok := m.NeedDetectCities[cmdbIns.LogicalCityID]; !ok {
			m.NeedDetectCities[cmdbIns.LogicalCityID] = struct{}{}
			num += 1
		}
	}
	log.Logger.Debugf("cluster type:%s, hash_mod:%d, hash_value:%d, need detect machine number:%d",
		clusterType, hashMod, hashValue, num)

	return nil
}

// getAllNeedDetectMachineInfo get all need detect machine from cmdb
func (m *MonitorComponent) getAllNeedDetectMachineInfo() error {
	for _, clusterType := range m.ActiveClusterType {
		log.Logger.Infof("try to get all instances by cluster type:%s", clusterType)
		for i := 0; i < m.HashMod; i++ {
			if err := m.getCmDBMachineByCluster(clusterType, m.HashMod, i); err != nil {
				return err
			}
		}
	}
	log.Logger.Debugf("all need detect city info:%#v", m.NeedDetectCities)

	return nil
}

// getAllHaComponentInfo get all alive component from hadb
func (m *MonitorComponent) getAllHaComponentInfo() error {
	interval := m.MonitorConf.ReportInterval
	log.Logger.Infof("try to get alive agent info in latest %d second", interval)
	agentInfo, err := m.HaDBClient.GetAliveHAComponent(constvar.Agent, interval)
	if err != nil {
		return fmt.Errorf("get alive agent info failed:%s", err.Error())
	}
	m.AgentList = agentInfo
	log.Logger.Debugf("agent list:%#v", m.AgentList)
	for _, agent := range m.AgentList {
		if _, ok := m.DetectedCities[agent.CityID]; ok {
			continue
		} else {
			m.DetectedCities[agent.CityID] = struct{}{}
		}
	}
	log.Logger.Infof("all detected city list:%#v", m.DetectedCities)

	log.Logger.Infof("try to get alive gm info in latest %d second", interval)
	gmInfo, err := m.HaDBClient.GetAliveHAComponent(constvar.GM, interval)
	if err != nil {
		return fmt.Errorf("get alive agent info failed:%s", err.Error())
	}
	m.GmList = gmInfo
	log.Logger.Debugf("gm list:%#v", m.GmList)

	return nil
}

// getAllDetectedMachineInfo get all detected machine from HADB
func (m *MonitorComponent) getAllDetectedMachineInfo() error {
	log.Logger.Infof("try to get all detected instances info from hadb")
	detectInfo, err := m.HaDBClient.GetHADetectInfo()
	if err != nil {
		return err
	}
	for _, ins := range detectInfo {
		if _, ok := m.DetectedMachines[ins.IP]; ok {
			continue
		} else {
			if ins.LastTime.Before(time.Now()) && time.Since(*ins.LastTime) <= 5*time.Minute {
				m.DetectedMachines[ins.IP] = struct{}{}
			}
		}
	}
	log.Logger.Debugf("all detected machine info:%#v", m.DetectedMachines)

	return nil
}
