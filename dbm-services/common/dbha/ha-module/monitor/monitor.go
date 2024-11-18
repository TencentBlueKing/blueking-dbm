// Package monitor TODO
package monitor

import (
	"encoding/json"
	"fmt"
	"strconv"

	"dbm-services/common/dbha/ha-module/client"
	"dbm-services/common/dbha/ha-module/config"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/dbutil"
	"dbm-services/common/dbha/ha-module/log"
	"dbm-services/common/dbha/ha-module/util"
)

// SwitchMonitor switch monitor information
type SwitchMonitor struct {
	ServerIp    string
	ServerPort  int
	Bzid        string
	MachineType string
	Role        string
	Status      string
	Cluster     string
	IDC         string
	//gmm double check id in ha_gm_logs
	CheckID int64
	//after MySQL switch, new master's host
	NewMasterHost string
	//after MySQL switch, new master's port
	NewMasterPort int
	//after MySQL switch, new master's binlog_file
	NewMasterBinlogFile string
	//after MySQL switch, new master's binlog_pos
	NewMasterBinlogPosition uint64
}

// DetectMonitor detect monitor information
type DetectMonitor struct {
	ServerIp    string
	ServerPort  int
	Bzid        string
	MachineType string
	Status      string
	Cluster     string
	ClusterType string
}

// GlobalMonitor HA global monitor struct
type GlobalMonitor struct {
	CloudId  int
	ServerIp string
	//not detect logical_city_ids
	UnCoveredCityIDs []int
	//not detect instances number
	UnCoveredInsNumber int
	//need detect cmdb instances number
	NeedDetectNumber int
	//HA detected instances number
	HADetectedNumber int
}

// MonitorInfo the struct of monitor information
type MonitorInfo struct {
	EventName       string
	MonitorInfoType int
	Switch          SwitchMonitor
	Detect          DetectMonitor
	//global monitor
	Global GlobalMonitor
}

// MonitorInit init monitor moudule by config
func MonitorInit(conf *config.Config) error {
	RuntimeConfigInit(
		conf.Monitor.LocalIP, conf.Monitor.BkDataId, conf.Monitor.AccessToken,
		constvar.MonitorReportType, constvar.MonitorMessageKind,
		conf.Monitor.BeatPath, conf.Monitor.AgentAddress,
	)

	return nil
}

// MonitorSendSwitch send switch monitor infomration
func MonitorSendSwitch(ins dbutil.DataBaseSwitch, content string, succ bool) {
	minfo := GetMonitorInfoBySwitch(ins, succ)
	err := MonitorSend(content, minfo)
	if err != nil {
		log.Logger.Errorf(
			"monitor send switch failed,err:%s,info:%v, content:%s", err.Error(), minfo, content,
		)
	}
}

// MonitorSendDetect send detect monitor information
func MonitorSendDetect(ins dbutil.DataBaseDetect, eventName string, content string) {
	minfo := GetMonitorInfoByDetect(ins, eventName)
	err := MonitorSend(content, minfo)
	if err != nil {
		log.Logger.Errorf(
			"monitor send detect failed,err:%s,info:%v, content:%s", err.Error(), minfo, content,
		)
	}
}

// MonitorSend send dbha monitor information
func MonitorSend(content string, info MonitorInfo) error {
	addDimension := make(map[string]interface{})
	if info.MonitorInfoType == constvar.MonitorInfoSwitch {
		// switch monitor information dimension add
		addDimension["role"] = info.Switch.Role
		addDimension["appid"] = info.Switch.Bzid
		addDimension["server_ip"] = info.Switch.ServerIp
		addDimension["server_port"] = info.Switch.ServerPort
		addDimension["status"] = info.Switch.Status
		addDimension["cluster"] = info.Switch.Cluster
		addDimension["machine_type"] = info.Switch.MachineType
		addDimension["idc"] = info.Switch.IDC
		addDimension["double_check_id"] = info.Switch.CheckID

		if info.EventName == constvar.DBHAEventMysqlSwitchSucc &&
			(info.Switch.Role == constvar.TenDBStorageMaster ||
				info.Switch.Role == constvar.TenDBClusterStorageMaster) {
			addDimension[constvar.NewMasterBinlogFile] = info.Switch.NewMasterBinlogFile
			addDimension[constvar.NewMasterBinlogPos] = info.Switch.NewMasterBinlogPosition
			addDimension[constvar.NewMasterHost] = info.Switch.NewMasterHost
			addDimension[constvar.NewMasterPort] = info.Switch.NewMasterPort
		}
	} else if info.MonitorInfoType == constvar.MonitorInfoDetect {
		// detect monitor information dimension add
		addDimension["appid"] = info.Detect.Bzid
		addDimension["server_ip"] = info.Detect.ServerIp
		addDimension["server_port"] = info.Detect.ServerPort
		addDimension["status"] = info.Detect.Status
		addDimension["cluster"] = info.Detect.Cluster
		addDimension["machine_type"] = info.Detect.MachineType
		addDimension["cluster_type"] = info.Detect.ClusterType
	} else if info.MonitorInfoType == constvar.MonitorInfoGlobal {
		addDimension["cloud_id"] = info.Global.CloudId
		addDimension["server_ip"] = info.Global.ServerIp
		addDimension["cloud_id"] = info.Global.CloudId
		addDimension["uncovered_num"] = info.Global.UnCoveredInsNumber
		addDimension["need_detect_num"] = info.Global.NeedDetectNumber
		addDimension["ha_detect__num"] = info.Global.HADetectedNumber
		addDimension["uncovered_city_ids"] = util.IntSlice2String(info.Global.UnCoveredCityIDs, ",")
	}

	return SendEvent(info.EventName, content, addDimension)
}

// GetMonitorInfoBySwitch get MonitorInfo by switch instance
func GetMonitorInfoBySwitch(ins dbutil.DataBaseSwitch, succ bool) MonitorInfo {
	var eventName string
	addr, port := ins.GetAddress()
	monInfo := MonitorInfo{
		EventName:       eventName,
		MonitorInfoType: constvar.MonitorInfoSwitch,
		Switch: SwitchMonitor{
			ServerIp:    addr,
			ServerPort:  port,
			Bzid:        ins.GetApp(),
			MachineType: ins.GetMetaType(),
			Role:        ins.GetRole(),
			Status:      ins.GetStatus(),
			Cluster:     ins.GetCluster(),
			IDC:         strconv.Itoa(ins.GetIdcID()),
			CheckID:     ins.GetDoubleCheckId(),
		},
	}

	switch ins.GetMetaType() {
	case constvar.RedisMetaType, constvar.TwemproxyMetaType,
		constvar.TendisSSDMetaType:
		if succ {
			eventName = constvar.DBHAEventRedisSwitchSucc
		} else {
			eventName = constvar.DBHAEventRedisSwitchErr
		}
	case constvar.PredixyMetaType, constvar.TendisplusMetaType:
		if succ {
			eventName = constvar.DBHAEventRedisSwitchSucc
		} else {
			eventName = constvar.DBHAEventRedisSwitchErr
		}
	case constvar.TenDBStorageType, constvar.TenDBProxyType,
		constvar.TenDBClusterStorageType, constvar.TenDBClusterProxyType:
		if succ {
			eventName = constvar.DBHAEventMysqlSwitchSucc
			if ins.GetRole() == constvar.TenDBStorageMaster ||
				ins.GetRole() == constvar.TenDBClusterStorageMaster {
				if ok, file := ins.GetInfo(constvar.NewMasterBinlogFile); ok {
					monInfo.Switch.NewMasterBinlogFile = file.(string)
				}
				if ok, pos := ins.GetInfo(constvar.NewMasterBinlogPos); ok {
					monInfo.Switch.NewMasterBinlogPosition = pos.(uint64)
				}
				if ok, masterHost := ins.GetInfo(constvar.NewMasterHost); ok {
					monInfo.Switch.NewMasterHost = masterHost.(string)
				}
				if ok, masterPort := ins.GetInfo(constvar.NewMasterPort); ok {
					monInfo.Switch.NewMasterPort = masterPort.(int)
				}
			}
		} else {
			eventName = constvar.DBHAEventMysqlSwitchErr
		}
	case constvar.Riak:
		if succ {
			eventName = constvar.DBHAEventRiakSwitchSucc
		} else {
			eventName = constvar.DBHAEventRiakSwitchErr
		}
	default:
		if succ {
			eventName = constvar.DBHAEventMysqlSwitchSucc
		} else {
			eventName = constvar.DBHAEventMysqlSwitchErr
		}
	}
	monInfo.EventName = eventName

	return monInfo
}

// GetMonitorInfoByDetect get MonitorInfo by detect instance
func GetMonitorInfoByDetect(ins dbutil.DataBaseDetect, eventName string) MonitorInfo {
	addr, port := ins.GetAddress()
	return MonitorInfo{
		EventName:       eventName,
		MonitorInfoType: constvar.MonitorInfoDetect,
		Detect: DetectMonitor{
			ServerIp:    addr,
			ServerPort:  port,
			Bzid:        ins.GetApp(),
			MachineType: string(ins.GetDBType()),
			Status:      string(ins.GetStatus()),
			Cluster:     ins.GetCluster(),
			ClusterType: ins.GetClusterType(),
		},
	}
}

// CheckHAComponent check whether HA component work normal
// 1. all need detect CMDB instances should detect
// 2. alive agent should found
func CheckHAComponent(conf *config.Config) (MonitorInfo, error) {
	cmdbClient := client.NewCmDBClient(&conf.DBConf.CMDB, conf.GetCloudId())
	hadbClient := client.NewHaDBClient(&conf.DBConf.HADB, conf.GetCloudId())
	monitorInfo := MonitorInfo{
		EventName:       constvar.DBHAEventGlobalMonitor,
		MonitorInfoType: constvar.MonitorInfoGlobal,
		Global: GlobalMonitor{
			CloudId:            conf.Monitor.CloudID,
			ServerIp:           conf.Monitor.LocalIP,
			UnCoveredInsNumber: 0,
			UnCoveredCityIDs:   nil,
			NeedDetectNumber:   0,
			HADetectedNumber:   0,
		},
	}

	//undetected instances
	unCoveredIns := map[string]struct{}{}
	//undetected logical_city_ids
	unCoveredCityIDs := map[int]struct{}{}
	//all logical_city_ids detected by agent
	allDetectCityIDs := map[int]struct{}{}

	log.Logger.Infof("try to get alive agent info latest 10 minutes")
	if agentInfo, err := hadbClient.GetAliveHAComponent(constvar.Agent, 600); err != nil {
		return monitorInfo, fmt.Errorf("get alive agent info failed:%s", err.Error())
	} else {
		log.Logger.Debugf("all agent info:%#v", agentInfo)
		for _, agent := range agentInfo {
			allDetectCityIDs[agent.CityID] = struct{}{}
		}
	}

	//2. uncovered logic_city_id
	log.Logger.Infof("try to get all need detect instances info from cmdb")
	if rawInfo, err := cmdbClient.GetAllDBInstanceInfo(); err != nil {
		return monitorInfo, fmt.Errorf("fetch all cmdb instance failed:%s", err.Error())
	} else {
		needDetectIpMap := map[string]struct{}{}
		log.Logger.Debugf("all cmdb instances number:%d", len(rawInfo))

		log.Logger.Infof("try to get all detected instances info from hadb")
		detectInfo, err := hadbClient.GetDBDetectInfo()
		if err != nil {
			return monitorInfo, fmt.Errorf("fetch all detected instances from hadb failed:%s", err.Error())
		}
		log.Logger.Debugf("HA detected instances number:%d", len(detectInfo))
		monitorInfo.Global.HADetectedNumber = len(detectInfo)

		for _, v := range rawInfo {
			found := false
			cmdbIns := dbutil.DBInstanceInfoDetail{}
			rawIns, jsonErr := json.Marshal(v)
			if jsonErr != nil {
				log.Logger.Errorf("marshal db instance info failed:%s", jsonErr.Error())
				return monitorInfo, fmt.Errorf("get cmdb instance info failed:%s", jsonErr.Error())
			}
			if jsonErr = json.Unmarshal(rawIns, &cmdbIns); jsonErr != nil {
				log.Logger.Errorf("unmarshal db instance info failed:%s", jsonErr.Error())
				return monitorInfo, fmt.Errorf("get cmdb instance info failed:%s", jsonErr.Error())
			}

			//TODO, API filter active cluster type more efficient
			if _, ok := needDetectIpMap[cmdbIns.IP]; ok ||
				!util.HasElem(cmdbIns.ClusterType, conf.Monitor.ActiveDBType) {
				continue
			} else {
				needDetectIpMap[cmdbIns.IP] = struct{}{}
			}

			for _, detectIns := range detectInfo {
				if cmdbIns.IP == detectIns.IP {
					found = true
					break
				}
			}
			if !found {
				unCoveredIns[cmdbIns.IP] = struct{}{}
				if _, ok := allDetectCityIDs[cmdbIns.LogicalCityID]; !ok {
					unCoveredCityIDs[cmdbIns.LogicalCityID] = struct{}{}
				}
			}
		}
		monitorInfo.Global.NeedDetectNumber = len(needDetectIpMap)
	}

	if len(unCoveredIns) > 0 {
		log.Logger.Errorf("uncovered instances list:%#v", unCoveredIns)
		return monitorInfo, fmt.Errorf("%d instances not covered by dbha", len(unCoveredIns))
	}

	if len(unCoveredCityIDs) > 0 {
		for k := range unCoveredCityIDs {
			monitorInfo.Global.UnCoveredCityIDs = append(monitorInfo.Global.UnCoveredCityIDs, k)
		}
		return monitorInfo, fmt.Errorf("%d logical_city_ids not covered by dbha", len(unCoveredCityIDs))
	}

	if monitorInfo.Global.HADetectedNumber != monitorInfo.Global.NeedDetectNumber {
		return monitorInfo, fmt.Errorf("need detect number:%d not equal HA detect number:%d",
			monitorInfo.Global.NeedDetectNumber, monitorInfo.Global.HADetectedNumber)
	}

	log.Logger.Debugf("global monitor info: %#v", monitorInfo)

	return monitorInfo, nil
}
