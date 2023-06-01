package dbutil

import (
	"time"

	"dbm-services/common/dbha/ha-module/client"
	"dbm-services/common/dbha/ha-module/log"
)

// DataBaseSwitch TODO
type DataBaseSwitch interface {
	CheckSwitch() (bool, error)
	DoSwitch() error
	ShowSwitchInstanceInfo() string
	RollBack() error
	UpdateMetaInfo() error

	GetAddress() (string, int)
	GetIDC() string
	GetStatus() string
	GetApp() string
	GetClusterType() string
	GetMetaType() string
	GetSwitchUid() uint
	GetRole() string // proxy没有role
	GetCluster() string

	SetSwitchUid(uint)
	SetInfo(infoKey string, infoValue interface{})
	GetInfo(infoKey string) (bool, interface{})
	ReportLogs(result string, comment string) bool
}

// BindEntry TODO
type BindEntry struct {
	Dns     []interface{}
	Polaris []interface{}
	CLB     []interface{}
}

// ProxyInfo TODO
type ProxyInfo struct {
	Ip        string `json:"ip"`
	Port      int    `json:"port"`
	AdminPort int    `json:"admin_port"`
	Status    string `json:"status"`
}

// BaseSwitch TODO
type BaseSwitch struct {
	Ip          string
	Port        int
	IDC         string
	Status      string
	App         string
	ClusterType string
	MetaType    string
	SwitchUid   uint
	Cluster     string
	CmDBClient  *client.CmDBClient
	HaDBClient  *client.HaDBClient
	Infos       map[string]interface{}
}

// GetAddress TODO
func (ins *BaseSwitch) GetAddress() (string, int) {
	return ins.Ip, ins.Port
}

// GetIDC TODO
func (ins *BaseSwitch) GetIDC() string {
	return ins.IDC
}

// GetStatus TODO
func (ins *BaseSwitch) GetStatus() string {
	return ins.Status
}

// GetApp TODO
func (ins *BaseSwitch) GetApp() string {
	return ins.App
}

// GetClusterType TODO
func (ins *BaseSwitch) GetClusterType() string {
	return ins.ClusterType
}

// GetMetaType TODO
func (ins *BaseSwitch) GetMetaType() string {
	return ins.MetaType
}

// GetSwitchUid TODO
func (ins *BaseSwitch) GetSwitchUid() uint {
	return ins.SwitchUid
}

// SetSwitchUid TODO
func (ins *BaseSwitch) SetSwitchUid(uid uint) {
	ins.SwitchUid = uid
}

// GetRole TODO
// override if needed
func (ins *BaseSwitch) GetRole() string {
	return "N/A"
}

// GetCluster return the cluster info
func (ins *BaseSwitch) GetCluster() string {
	return ins.Cluster
}

// SetInfo set information to switch instance
func (ins *BaseSwitch) SetInfo(infoKey string, infoValue interface{}) {
	if nil == ins.Infos {
		ins.Infos = make(map[string]interface{})
	}

	ins.Infos[infoKey] = infoValue
}

// GetInfo get information by key from switch instance
func (ins *BaseSwitch) GetInfo(infoKey string) (bool, interface{}) {
	if nil == ins.Infos {
		return false, nil
	}

	v, ok := ins.Infos[infoKey]
	if ok {
		return true, v
	} else {
		return false, nil
	}
}

// ReportLogs TODO
func (ins *BaseSwitch) ReportLogs(result string, comment string) bool {
	log.Logger.Infof(comment)
	if nil == ins.HaDBClient {
		return false
	}

	err := ins.HaDBClient.InsertSwitchLog(
		ins.SwitchUid, ins.Ip, ins.Port, result, comment, time.Now(),
	)
	if err != nil {
		return false
	} else {
		return true
	}
}
