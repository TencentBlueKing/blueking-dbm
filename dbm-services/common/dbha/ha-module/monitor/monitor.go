// Package monitor TODO
package monitor

import (
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
}

// DetectMonitor detect monitor information
type DetectMonitor struct {
	ServerIp    string
	ServerPort  int
	Bzid        string
	MachineType string
	Status      string
	Cluster     string
}

// MonitorInfo the struct of monitor information
type MonitorInfo struct {
	EventName       string
	MonitorInfoType int
	Switch          SwitchMonitor
	Detect          DetectMonitor
}

// MonitorInit init monitor moudule by config
func MonitorInit(conf *config.Config) error {
	targetIp, err := util.GetMonIp()
	if err != nil {
		return err
	}

	RuntimeConfigInit(
		targetIp, conf.Monitor.BkDataId, conf.Monitor.AccessToken,
		conf.GetCloud(), constvar.MonitorReportType, constvar.MonitorMessageKind,
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
		addDimension["role"] = info.Switch.Role
		addDimension["bzid"] = info.Switch.Bzid
		addDimension["server_ip"] = info.Switch.ServerIp
		addDimension["server_port"] = info.Switch.ServerPort
		addDimension["status"] = info.Switch.Status
		addDimension["cluster"] = info.Switch.Cluster
		addDimension["machine_type"] = info.Switch.MachineType
		addDimension["idc"] = info.Switch.IDC
	}

	return SendEvent(info.EventName, content, addDimension)
}

// GetMonitorInfoBySwitch get MonitorInfo by switch instance
func GetMonitorInfoBySwitch(ins dbutil.DataBaseSwitch, succ bool) MonitorInfo {
	var eventName string
	switch ins.GetMetaType() {
	case constvar.RedisMetaType, constvar.TwemproxyMetaType:
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
	case constvar.MySQLMetaType, constvar.MySQLProxyMetaType:
		if succ {
			eventName = constvar.DBHAEventMysqlSwitchSucc
		} else {
			eventName = constvar.DBHAEventMysqlSwitchErr
		}
	default:
		if succ {
			eventName = constvar.DBHAEventMysqlSwitchSucc
		} else {
			eventName = constvar.DBHAEventMysqlSwitchErr
		}
	}

	addr, port := ins.GetAddress()
	return MonitorInfo{
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
			IDC:         ins.GetIDC(),
		},
	}
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
			MachineType: string(ins.GetType()),
			Status:      string(ins.GetStatus()),
			Cluster:     ins.GetCluster(),
		},
	}
}
