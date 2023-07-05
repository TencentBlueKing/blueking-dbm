package redis

import (
	"fmt"

	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/log"
)

// TwemproxySwitch TODO
type TwemproxySwitch struct {
	RedisProxySwitchInfo
}

// CheckSwitch TODO
func (ins *TwemproxySwitch) CheckSwitch() (bool, error) {
	return true, nil
}

// DoSwitch TODO
func (ins *TwemproxySwitch) DoSwitch() error {
	ins.ReportLogs(constvar.SwitchInfo,
		fmt.Sprintf("handle twemproxy switch[%s:%d]", ins.Ip, ins.Port))
	err := ins.KickOffDns()
	cErr := ins.KickOffClb()
	pErr := ins.KickOffPolaris()
	if err != nil {
		tpErrLog := fmt.Sprintf("Twemproxy kick dns failed,err:%s", err.Error())
		log.Logger.Errorf("%s info:%s", tpErrLog, ins.ShowSwitchInstanceInfo())
		ins.ReportLogs(constvar.SwitchFail, tpErrLog)
		return err
	}
	if cErr != nil {
		tpErrLog := fmt.Sprintf("Twemproxy kick clb failed,err:%s", cErr.Error())
		log.Logger.Errorf("%s info:%s", tpErrLog, ins.ShowSwitchInstanceInfo())
		ins.ReportLogs(constvar.SwitchFail, tpErrLog)
		return cErr
	}
	if pErr != nil {
		tpErrLog := fmt.Sprintf("Twemproxy kick polaris failed,err:%s", pErr.Error())
		log.Logger.Errorf("%s info:%s", tpErrLog, ins.ShowSwitchInstanceInfo())
		ins.ReportLogs(constvar.SwitchFail, tpErrLog)
		return pErr
	}
	succLog := fmt.Sprintf("Twemproxy do switch ok,dns[%t] clb[%t], polaris[%t]",
		ins.ApiGw.DNSFlag, ins.ApiGw.CLBFlag, ins.ApiGw.PolarisFlag)
	ins.ReportLogs(constvar.SwitchInfo, succLog)
	return nil
}

// RollBack TODO
func (ins *TwemproxySwitch) RollBack() error {
	return nil
}

// UpdateMetaInfo TODO
func (ins *TwemproxySwitch) UpdateMetaInfo() error {
	return nil
}

// ShowSwitchInstanceInfo TODO
func (ins *TwemproxySwitch) ShowSwitchInstanceInfo() string {
	format := `<%s#%d IDC:%s Status:%s App:%s ClusterType:%s MachineType:%s Cluster:%s> switch`
	str := fmt.Sprintf(
		format, ins.Ip, ins.Port, ins.IDC, ins.Status, ins.App,
		ins.ClusterType, ins.MetaType, ins.Cluster,
	)
	return str
}
