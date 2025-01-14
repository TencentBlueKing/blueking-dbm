// Package monitor TODO
package monitor

import (
	"strconv"

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
	ServerIp string
	//not detect logical_city_ids
	UnCoveredCityIDs []int
	//not detect instances number
	UnCoveredInsNumber int
	//need detect cmdb instances number
	NeedDetectNumber int
	//HA detected instances number
	HADetectedNumber int
	Content          string
}

// APIMonitor api monitor struct
type APIMonitor struct {
	ApiName string
	Message string
}

// MonitorInfo the struct of monitor information
type MonitorInfo struct {
	EventName       string
	MonitorInfoType int
	Switch          SwitchMonitor
	Detect          DetectMonitor
	//global monitor
	Global  GlobalMonitor
	ApiInfo APIMonitor
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
	switch info.MonitorInfoType {
	case constvar.MonitorInfoSwitch:
		// switch monitor information dimension add
		addDimension["instance_role"] = info.Switch.Role
		addDimension["appid"] = info.Switch.Bzid
		addDimension["server_ip"] = info.Switch.ServerIp
		addDimension["server_port"] = info.Switch.ServerPort
		addDimension["status"] = info.Switch.Status
		addDimension["cluster_domain"] = info.Switch.Cluster
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
	case constvar.MonitorInfoDetect:
		// detect monitor information dimension add
		addDimension["appid"] = info.Detect.Bzid
		addDimension["server_ip"] = info.Detect.ServerIp
		addDimension["server_port"] = info.Detect.ServerPort
		addDimension["status"] = info.Detect.Status
		addDimension["cluster_domain"] = info.Detect.Cluster
		addDimension["machine_type"] = info.Detect.MachineType
		addDimension["cluster_type"] = info.Detect.ClusterType
	case constvar.MonitorInfoGlobal:
		addDimension["server_ip"] = info.Global.ServerIp
		addDimension["uncovered_ins_num"] = info.Global.UnCoveredInsNumber
		addDimension["need_detect_num"] = info.Global.NeedDetectNumber
		addDimension["ha_detect_num"] = info.Global.HADetectedNumber
		addDimension["uncovered_city_ids"] = util.IntSlice2String(info.Global.UnCoveredCityIDs, ",")
	case constvar.MonitorInfoAPI:
		addDimension["api_name"] = info.ApiInfo.ApiName
		addDimension["api_message"] = info.ApiInfo.Message
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
	case constvar.SqlserverHA:
		if succ {
			eventName = constvar.DBHAEventSQLserverSwitchSucc
		} else {
			eventName = constvar.DBHAEventSQLserverSwitchErr
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

func GetApiAlertInfo(apiName, message string) MonitorInfo {
	return MonitorInfo{
		EventName:       constvar.DBHAEventApiFailed,
		MonitorInfoType: constvar.MonitorInfoAPI,
		ApiInfo: APIMonitor{
			ApiName: apiName,
			Message: message,
		},
	}
}
