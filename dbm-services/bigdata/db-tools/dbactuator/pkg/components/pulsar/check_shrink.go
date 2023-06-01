package pulsar

import (
	"fmt"

	"dbm-services/bigdata/db-tools/dbactuator/pkg/components"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/pulsarutil"
	"dbm-services/common/go-pubpkg/logger"
)

// CheckPulsarShrinkComp TODO
type CheckPulsarShrinkComp struct {
	GeneralParam    *components.GeneralParam
	Params          *CheckPulsarShrinkParams
	RollBackContext rollback.RollBackObjects
}

// CheckPulsarShrinkParams TODO
type CheckPulsarShrinkParams struct {
	HttpPort      int      `json:"http_port" ` // http端口
	Host          string   `json:"host" validate:"required,ip" `
	BookkeeperIp  []string `json:"bookkeeper_ip"`  // 下架的bookkeeper ip
	BookkeeperNum int      `json:"bookkeeper_num"` // 原有bookkeeper数量
}

// Init TODO
/**
 *  @description:
 *  @return
 */
func (d *CheckPulsarShrinkComp) Init() (err error) {
	logger.Info("Reduce pulsar node fake init")
	return nil
}

// CheckBrokerConf TODO
func (d *CheckPulsarShrinkComp) CheckBrokerConf() (err error) {
	return pulsarutil.CheckBrokerConf(d.Params.BookkeeperNum - len(d.Params.BookkeeperIp))
}

// CheckNamespaceEnsembleSize TODO
func (d *CheckPulsarShrinkComp) CheckNamespaceEnsembleSize() (err error) {
	return pulsarutil.CheckNamespaceEnsembleSize(d.Params.BookkeeperNum - len(d.Params.BookkeeperIp))
}

// CheckUnderReplicated TODO
func (d *CheckPulsarShrinkComp) CheckUnderReplicated() (err error) {
	return pulsarutil.CheckUnderReplicated()
}

// CheckLedgerMetadata 检查Ledger元数据
func (d *CheckPulsarShrinkComp) CheckLedgerMetadata() (err error) {
	return pulsarutil.CheckLedgerMetadata(d.Params.BookkeeperNum - len(d.Params.BookkeeperIp))
}

// DecommissionBookie TODO
func (d *CheckPulsarShrinkComp) DecommissionBookie() (err error) {
	extraCmd := fmt.Sprintf("%s/bin/bookkeeper shell decommissionbookie", cst.DefaultPulsarBkDir)
	logger.Info("下架bookkeeper, [%s]", extraCmd)
	_, err = osutil.ExecShellCommand(false, extraCmd)
	if err != nil {
		logger.Error("[%s] execute failed, %v", err)
		return err
	}
	return nil
}

// SetBookieReadonly 将bookie设置为只读状态
func (d *CheckPulsarShrinkComp) SetBookieReadonly() (err error) {
	return pulsarutil.SetBookieReadOnly()
}

// UnsetBookieReadonly 取消bookie只读状态
func (d *CheckPulsarShrinkComp) UnsetBookieReadonly() (err error) {
	return pulsarutil.UnsetBookieReadOnly()
}
