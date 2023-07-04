package mysql

import (
	"fmt"

	"dbm-services/common/dbha/ha-module/client"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/dbutil"
	"dbm-services/common/dbha/ha-module/log"
)

// MySQLProxySwitch define proxy switch detail info
type MySQLProxySwitch struct {
	dbutil.BaseSwitch
	AdminPort int
	Entry     dbutil.BindEntry
	DnsClient *client.NameServiceClient
}

// CheckSwitch check whether proxy allowed swtich, always true at present
func (ins *MySQLProxySwitch) CheckSwitch() (bool, error) {
	return true, nil
}

// DoSwitch proxy do switch
//  1. get domain info
//  2. delete ip under the domain
func (ins *MySQLProxySwitch) DoSwitch() error {
	ins.ReportLogs(constvar.SwitchFail, fmt.Sprintf("get domain info by ip:%s", ins.Ip))
	dnsInfos, err := ins.DnsClient.GetDomainInfoByIp(ins.Ip)
	log.Logger.Debugf("dnsInfos:%v", dnsInfos)
	if err != nil {
		switchErrLog := fmt.Sprintf("get domain info by ip failed: %s", err.Error())
		ins.ReportLogs(constvar.SwitchFail, switchErrLog)
		return err
	}
	if len(dnsInfos) == 0 {
		switchErrLog := "mysql proxy without domain info."
		ins.ReportLogs(constvar.SwitchFail, switchErrLog)
		return fmt.Errorf("no domain info found for mysql-proxy")
	}

	ins.ReportLogs(constvar.SwitchInfo, fmt.Sprintf("start release ip[%s] from domain", ins.Ip))
	for _, dnsInfo := range dnsInfos {
		ipInfos, err := ins.DnsClient.GetDomainInfoByDomain(dnsInfo.DomainName)
		if err != nil {
			switchErrLog := fmt.Sprintf("get domain info by domain name failed. err:%s", err.Error())
			ins.ReportLogs(constvar.SwitchFail, switchErrLog)
			return err
		}
		if len(ipInfos) == 0 {
			switchErrLog := fmt.Sprintf("domain name: %s without ip.", dnsInfo.DomainName)
			ins.ReportLogs(constvar.SwitchFail, switchErrLog)
			return fmt.Errorf("domain name: %s without ip", dnsInfo.DomainName)
		}
		if len(ipInfos) == 1 {
			switchOkLog := fmt.Sprintf("domain name: %s only one ip. so we skip it.",
				dnsInfo.DomainName)
			ins.ReportLogs(constvar.SwitchInfo, switchOkLog)
		} else {
			err = ins.DnsClient.DeleteDomain(dnsInfo.DomainName, dnsInfo.App, ins.Ip, ins.Port)
			if err != nil {
				switchErrLog := fmt.Sprintf("delete domain %s failed:%s", dnsInfo.DomainName, err.Error())
				ins.ReportLogs(constvar.SwitchFail, switchErrLog)
				return err
			}
			switchOkLog := fmt.Sprintf("delete domain %s success.", dnsInfo.DomainName)
			log.Logger.Infof("%s, info:{%s}", switchOkLog, ins.ShowSwitchInstanceInfo())
			ins.ReportLogs(constvar.SwitchInfo, switchOkLog)
		}
	}
	return nil
}

// ShowSwitchInstanceInfo display switch proxy info
func (ins *MySQLProxySwitch) ShowSwitchInstanceInfo() string {
	str := fmt.Sprintf("<%s#%d IDC:%s Status:%s Bzid:%s ClusterType:%s MachineType:%s> switch",
		ins.Ip, ins.Port, ins.IDC, ins.Status, ins.App, ins.ClusterType, ins.MetaType)
	return str
}

// RollBack proxy do rollback
func (ins *MySQLProxySwitch) RollBack() error {
	return nil
}

// UpdateMetaInfo update cmdb meta info, do nothing at present
func (ins *MySQLProxySwitch) UpdateMetaInfo() error {
	return nil
}
