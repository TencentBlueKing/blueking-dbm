package dbutil

import (
	"fmt"
	"time"

	"dbm-services/common/dbha/ha-module/client"
	"dbm-services/common/dbha/ha-module/config"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/log"
)

// DataBaseSwitch TODO
type DataBaseSwitch interface {
	CheckSwitch() (bool, error)
	DoSwitch() error
	ShowSwitchInstanceInfo() string
	RollBack() error
	UpdateMetaInfo() error
	DeleteNameService(entry BindEntry) error
	DoFinal() error

	GetAddress() (string, int)
	GetIdcID() int
	GetStatus() string
	GetApp() string
	GetClusterType() string
	GetMetaType() string
	GetSwitchUid() int64
	GetDoubleCheckId() int64
	GetRole() string // proxy没有role
	GetCluster() string

	SetSwitchUid(int64)
	SetDoubleCheckId(int64)
	SetInfo(infoKey string, infoValue interface{})
	GetInfo(infoKey string) (bool, interface{})
	ReportLogs(result string, comment string) bool
}

// PolarisInfo polaris detail info, response by cmdb api
type PolarisInfo struct {
	Service string `json:"polaris_name"`
	Token   string `json:"polaris_token"`
	L5      string `json:"polaris_l5"`
	// the ip list bind to clb
	BindIps  []string `json:"bind_ips"`
	BindPort int      `json:"bind_port"`
}

// ClbInfo clb detail info, response by cmdb api
type ClbInfo struct {
	Region        string `json:"clb_region"`
	LoadBalanceId string `json:"clb_id"`
	ListenId      string `json:"listener_id"`
	Ip            string `json:"clb_ip"`
	// the ip list bind to clb
	BindIps  []string `json:"bind_ips"`
	BindPort int      `json:"bind_port"`
}

// DnsInfo dns detail info, response by cmdb api
type DnsInfo struct {
	DomainName string `json:"domain"`
	//master_entry, slave_entry
	EntryRole      string   `json:"entry_role"`
	BindIps        []string `json:"bind_ips"`
	BindPort       int      `json:"bind_port"`
	ForwardEntryId int      `json:"forward_entry_id"`
}

// BindEntry TODO
type BindEntry struct {
	Dns     []DnsInfo
	Polaris []PolarisInfo
	Clb     []ClbInfo
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
	IdcID       int
	Status      string
	App         string
	ClusterType string
	//machine type in cmdb api response
	MetaType string
	//double check id
	CheckID   int64
	SwitchUid int64
	//cluster domain
	Cluster    string
	ClusterId  int
	CmDBClient *client.CmDBClient
	//if not init, gcm may report log abnormal
	HaDBClient *client.HaDBClient
	//extra info, used through SetInfo/GetInfo method
	Infos map[string]interface{}
	//config info in yaml
	Config *config.Config
}

// GetAddress TODO
func (ins *BaseSwitch) GetAddress() (string, int) {
	return ins.Ip, ins.Port
}

// GetIdcID TODO
func (ins *BaseSwitch) GetIdcID() int {
	return ins.IdcID
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
func (ins *BaseSwitch) GetSwitchUid() int64 {
	return ins.SwitchUid
}

// SetSwitchUid TODO
func (ins *BaseSwitch) SetSwitchUid(uid int64) {
	ins.SwitchUid = uid
}

// GetDoubleCheckId get gmm double check id
func (ins *BaseSwitch) GetDoubleCheckId() int64 {
	return ins.CheckID
}

// SetDoubleCheckId set gmm double check id
func (ins *BaseSwitch) SetDoubleCheckId(uid int64) {
	ins.CheckID = uid
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

// GetClusterId return the cluster id
func (ins *BaseSwitch) GetClusterId() int {
	return ins.ClusterId
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

// SingleAddressUnderDomain check whether only one address under domain
// if only one address under dns entry, return true
// if no dns entry found, return false
func (ins *BaseSwitch) SingleAddressUnderDomain(entry BindEntry) (bool, error) {
	if entry.Dns == nil {
		return false, nil
	}
	conf := ins.Config
	dnsClient := client.NewNameServiceClient(&conf.NameServices.DnsConf, conf.GetCloudId())
	for _, dns := range entry.Dns {
		number, err := dnsClient.GetAddressNumberByDomain(dns.DomainName)
		if err != nil {
			return false, err
		}
		ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("found %d address under domain %s",
			number, dns.DomainName))
		if number == 1 {
			return true, nil
		}
	}

	return false, nil
}

// DeleteNameService delete broken-down ip from entry
func (ins *BaseSwitch) DeleteNameService(entry BindEntry) error {
	//flag refer to whether release name-service success
	var (
		dnsFlag     = true
		clbFlag     = true
		polarisFlag = true
	)
	conf := ins.Config
	if entry.Dns != nil {
		ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("try to release dns entry [%s:%d]", ins.Ip, ins.Port))
		dnsClient := client.NewNameServiceClient(&conf.NameServices.DnsConf, conf.GetCloudId())
		for _, dns := range entry.Dns {
			for _, ip := range dns.BindIps {
				if ip == ins.Ip {
					if err := dnsClient.DeleteDomain(dns.DomainName, ins.GetApp(), ins.Ip, dns.BindPort); err != nil {
						ins.ReportLogs(constvar.FailResult, fmt.Sprintf("delete ip[%s] from domain[%s] failed:%s",
							ip, dns.DomainName, err.Error()))
						dnsFlag = false
					}
					break
				}
			}
		}
		if dnsFlag {
			ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("release dns entry success [%s:%d]", ins.Ip, ins.Port))
		}
	}

	if entry.Clb != nil {
		ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("try to release clb entry [%s:%d]", ins.Ip, ins.Port))
		clbClient := client.NewNameServiceClient(&conf.NameServices.ClbConf, conf.GetCloudId())
		for _, clb := range entry.Clb {
			addr := fmt.Sprintf("%s:%d", ins.Ip, clb.BindPort)
			for _, ip := range clb.BindIps {
				// the ip and port of instance should match the clb information
				if ip != ins.Ip || clb.BindPort != ins.Port {
					continue
				}

				err := clbClient.ClbDeRegister(
					clb.Region, clb.LoadBalanceId, clb.ListenId, addr,
				)
				if err != nil {
					ins.ReportLogs(constvar.FailResult,
						fmt.Sprintf("delte %s from clb[%s:%s:%s] failed:%s",
							addr, clb.Region, clb.LoadBalanceId, clb.ListenId, err.Error()))
					clbFlag = false
				}
				break
			}
		}
	}

	if entry.Polaris != nil {
		ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("try to release polaris entry [%s:%d]", ins.Ip, ins.Port))
		polarisClient := client.NewNameServiceClient(&conf.NameServices.PolarisConf, conf.GetCloudId())
		for _, pinfo := range entry.Polaris {
			addr := fmt.Sprintf("%s:%d", ins.Ip, pinfo.BindPort)
			for _, ip := range pinfo.BindIps {
				// the ip and port of instance should match the polaris information
				if ip != ins.Ip || pinfo.BindPort != ins.Port {
					continue
				}

				err := polarisClient.PolarisUnBindTarget(
					pinfo.Service, pinfo.Token, addr)
				if err != nil {
					ins.ReportLogs(constvar.FailResult,
						fmt.Sprintf("delete [%s] from polaris %s:%s failed:%s",
							addr, pinfo.Service, pinfo.Token, err.Error()))
					polarisFlag = false
				}
				break
			}
		}
	}

	if !(dnsFlag && clbFlag && polarisFlag) {
		return fmt.Errorf("release broken-down ip from all entry failed [%s:%d]", ins.Ip, ins.Port)
	}

	ins.ReportLogs(constvar.InfoResult,
		fmt.Sprintf("release all entry [dns/clb/polaris] success [%s:%d]", ins.Ip, ins.Port))
	return nil
}

// ReportLogs report switch logs to hadb
// Input param
// result: constvar.FailResult, etc. in constvar
// comment: switch detail info
func (ins *BaseSwitch) ReportLogs(result string, comment string) bool {
	log.Logger.Infof(comment)
	if nil == ins.HaDBClient {
		return false
	}

	err := ins.HaDBClient.InsertSwitchLog(
		ins.SwitchUid, ins.Ip, ins.Port, ins.App, result, comment, time.Now(),
	)
	if err != nil {
		return false
	} else {
		return true
	}
}

// DoFinal do final thing
func (ins *BaseSwitch) DoFinal() error {
	return nil
}
