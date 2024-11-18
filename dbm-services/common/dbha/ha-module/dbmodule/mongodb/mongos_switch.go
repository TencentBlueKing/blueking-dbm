package mongodb

import (
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/dbutil"
	"dbm-services/common/dbha/ha-module/log"
	"fmt"
)

type GwInfo struct {
	CLBFlag      bool
	DNSFlag      bool
	ServiceEntry dbutil.BindEntry
}

// MongosSwitch defined mongo switch struct
type MongosSwitch struct {
	dbutil.BaseSwitch
	ApiGw GwInfo
	Role  string
}

// # switch operation
// # step 1, check if mongos can switch
// # step 2, mark the current inst as can switch in sw_queue
// # step 3, mark the current inst to in_switch status in ha_switch_queue
// # step 5, delete the instance from that dns, print the instances number before/after switch
// # step 6, update the dns_param table to make the dns change take affect
// # step 7, return

// GetRole get mysql role type
func (ins *MongosSwitch) GetRole() string {
	return ins.Role
}

// ShowSwitchInstanceInfo show mongo instance's switch info
func (ins *MongosSwitch) ShowSwitchInstanceInfo() string {
	str := fmt.Sprintf("<%s#%d IDC:%d Role:%s Status:%s Bzid:%s ClusterType:%s MachineType:%s>",
		ins.Ip, ins.Port, ins.IdcID, ins.Role, ins.Status, ins.App, ins.ClusterType,
		ins.MetaType)
	return str
}

// CheckSwitch check before switch [Step 1]
func (ins *MongosSwitch) CheckSwitch() (bool, error) {
	if ins.Role != constvar.Mongos {
		err := fmt.Errorf("info:{%s} unknown role", ins.ShowSwitchInstanceInfo())
		ins.ReportLogs(constvar.FailResult, err.Error())
		return false, err
	}

	// check dns keep at least One.
	var err error
	if ins.ApiGw.DNSFlag && len(ins.ApiGw.ServiceEntry.Dns) >= 1 {
		for idx, bindInfo := range ins.ApiGw.ServiceEntry.Dns {
			ins.ReportLogs(constvar.InfoResult,
				fmt.Sprintf("check dns bind items %s had bindIPs:%d", bindInfo.DomainName, len(bindInfo.BindIps)))
			if len(bindInfo.BindIps) <= 1 {
				err = fmt.Errorf("%s|[%d:%s]:bind no more than one IPs:%+v",
					err.Error(), idx, bindInfo.DomainName, bindInfo.BindIps)
				ins.ReportLogs(constvar.FailResult, err.Error())
			}
		}
	}
	if err != nil {
		return false, err
	}

	return true, nil
}

// DoSwitch do switch [Step 2]
func (ins *MongosSwitch) DoSwitch() error {
	ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("handle mongos switch[%s:%d]", ins.Ip, ins.Port))
	err := ins.KickOffDns()
	cErr := ins.KickOffClb()

	if err != nil {
		err := fmt.Errorf("mongos kickoff DNS failed,[%s] err:%s", ins.ShowSwitchInstanceInfo(), err.Error())
		ins.ReportLogs(constvar.FailResult, err.Error())
		return err
	}

	if cErr != nil {
		err := fmt.Errorf("mongos kickoff CLB failed,[%s] err:%s", ins.ShowSwitchInstanceInfo(), err.Error())
		ins.ReportLogs(constvar.FailResult, err.Error())
		return cErr
	}

	succLog := fmt.Sprintf("mongos do switch success, HasDNS[%t] HasCLB[%t]", ins.ApiGw.DNSFlag, ins.ApiGw.CLBFlag)
	ins.ReportLogs(constvar.InfoResult, succLog)
	return nil
}

// UpdateMetaInfo swap master, slave 's meta info in cmdb  [Step 3]
func (ins *MongosSwitch) UpdateMetaInfo() error {
	return nil
}

// RollBack do switch rollback
func (ins *MongosSwitch) RollBack() error {
	return nil
}

// KickOffDns kick instance from dns
func (ins *MongosSwitch) KickOffDns() error {
	if !ins.ApiGw.DNSFlag {
		log.Logger.Infof("no need kickoff DNS,info:%s", ins.ShowSwitchInstanceInfo())
		return nil
	}

	// kick off instance from dns
	return ins.DeleteNameService(dbutil.BindEntry{Dns: ins.ApiGw.ServiceEntry.Dns})
}

// KickOffClb TODO
func (ins *MongosSwitch) KickOffClb() error {
	if !ins.ApiGw.CLBFlag {
		log.Logger.Infof("no need kickoff CLB,info:%s", ins.ShowSwitchInstanceInfo())
		return nil
	}

	// kick off instance from clb
	return ins.DeleteNameService(dbutil.BindEntry{Clb: ins.ApiGw.ServiceEntry.Clb})
}
