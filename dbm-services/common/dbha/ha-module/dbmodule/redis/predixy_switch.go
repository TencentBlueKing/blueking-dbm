package redis

import (
	"fmt"

	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/log"
)

// PredixySwitch predixy switch instance
type PredixySwitch struct {
	RedisProxySwitchInfo
}

// CheckSwitch no nothing to check
func (ins *PredixySwitch) CheckSwitch() (bool, error) {
	return true, nil
}

// DoSwitch kick predixy from gateway
func (ins *PredixySwitch) DoSwitch() error {
	ins.ReportLogs(constvar.InfoResult,
		fmt.Sprintf("handle predixy switch[%s:%d]", ins.Ip, ins.Port))
	err := ins.KickOffDns()
	cErr := ins.KickOffClb()
	pErr := ins.KickOffPolaris()
	if err != nil {
		predixyErrLog := fmt.Sprintf("Predixy kick dns failed,err:%s", err.Error())
		log.Logger.Errorf("%s info:%s", predixyErrLog, ins.ShowSwitchInstanceInfo())
		ins.ReportLogs(constvar.FailResult, predixyErrLog)
		return err
	}
	if cErr != nil {
		predixyErrLog := fmt.Sprintf("Predixy kick clb failed,err:%s", cErr.Error())
		log.Logger.Errorf("%s info:%s", predixyErrLog, ins.ShowSwitchInstanceInfo())
		ins.ReportLogs(constvar.FailResult, predixyErrLog)
		return cErr
	}
	if pErr != nil {
		predixyErrLog := fmt.Sprintf("Predixy kick polaris failed,err:%s", pErr.Error())
		log.Logger.Errorf("%s info:%s", predixyErrLog, ins.ShowSwitchInstanceInfo())
		ins.ReportLogs(constvar.FailResult, predixyErrLog)
		return pErr
	}

	succLog := fmt.Sprintf("Predixy do switch ok,dns[%t] clb[%t] polaris[%t]",
		ins.ApiGw.DNSFlag, ins.ApiGw.CLBFlag, ins.ApiGw.PolarisFlag)
	ins.ReportLogs(constvar.InfoResult, succLog)
	return nil
}

// RollBack TODO
func (ins *PredixySwitch) RollBack() error {
	return nil
}

// UpdateMetaInfo nothing to update
func (ins *PredixySwitch) UpdateMetaInfo() error {
	return nil
}

// ShowSwitchInstanceInfo show predixy switch information
func (ins *PredixySwitch) ShowSwitchInstanceInfo() string {
	format := `<%s#%d IDC:%s Status:%s App:%s ClusterType:%s MachineType:%s Cluster:%s> switch`
	str := fmt.Sprintf(
		format, ins.Ip, ins.Port, ins.IDC, ins.Status, ins.App,
		ins.ClusterType, ins.MetaType, ins.Cluster,
	)
	return str
}
