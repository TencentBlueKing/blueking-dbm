package riak

import (
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/dbutil"
	"dbm-services/common/dbha/ha-module/log"
	"fmt"
)

// RiakSwitch defined riak switch struct
type RiakSwitch struct {
	dbutil.BaseSwitch
	Role string
}

// GetRole get mysql role type
func (ins *RiakSwitch) GetRole() string {
	return ins.Role
}

// ShowSwitchInstanceInfo show mysql instance's switch info
func (ins *RiakSwitch) ShowSwitchInstanceInfo() string {
	str := fmt.Sprintf("<%s#%d IDC:%d Role:%s Status:%s Bzid:%s ClusterType:%s MachineType:%s>",
		ins.Ip, ins.Port, ins.IdcID, ins.Role, ins.Status, ins.App, ins.ClusterType,
		ins.MetaType)
	return str
}

// CheckSwitch check before switch
func (ins *RiakSwitch) CheckSwitch() (bool, error) {
	var err error
	if ins.Role == constvar.Riak {
		ins.ReportLogs(constvar.InfoResult, "instance riak, needn't check")
		return false, nil
	} else {
		err = fmt.Errorf("info:{%s} unknown role", ins.ShowSwitchInstanceInfo())
		log.Logger.Error(err)
		ins.ReportLogs(constvar.FailResult, "instance unknown role")
		return false, err
	}
}

// DoSwitch do switch
func (ins *RiakSwitch) DoSwitch() error {
	return nil
}

// RollBack do switch rollback
func (ins *RiakSwitch) RollBack() error {
	return nil
}

// UpdateMetaInfo swap master, slave 's meta info in cmdb
func (ins *RiakSwitch) UpdateMetaInfo() error {
	return nil
}
