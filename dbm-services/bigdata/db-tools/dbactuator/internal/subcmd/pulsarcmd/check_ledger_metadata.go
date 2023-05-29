package pulsarcmd

import (
	"dbm-services/bigdata/db-tools/dbactuator/internal/subcmd"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/components/pulsar"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util"
	"dbm-services/common/go-pubpkg/logger"
	"encoding/json"
	"fmt"

	"github.com/spf13/cobra"
)

// CheckLedgerMetadataAct 检查ledger的metadata
type CheckLedgerMetadataAct struct {
	*subcmd.BaseOptions
	Service pulsar.CheckPulsarShrinkComp
}

// CheckLedgerMetadataCommand 检查ledger metadata的命令
func CheckLedgerMetadataCommand() *cobra.Command {
	// dbactuator pulsar check_ledger_metadata --payload xxxxx
	act := CheckLedgerMetadataAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "check_ledger_metadata",
		Short:   "检查ledger的元数据",
		Example: fmt.Sprintf(`dbactuator pulsar check_ledger_metadata %s`, subcmd.CmdBaseExapmleStr),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate())
			if act.RollBack {
				util.CheckErr(act.Rollback())
				return
			}
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Validate 校验函数
func (d *CheckLedgerMetadataAct) Validate() (err error) {
	return d.BaseOptions.Validate()
}

// Init 初始化函数
func (d *CheckLedgerMetadataAct) Init() (err error) {
	logger.Info("CheckLedgerMetadataAct Init")
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return d.Service.Init()
}

// Rollback 回滚函数
func (d *CheckLedgerMetadataAct) Rollback() (err error) {
	var r rollback.RollBackObjects
	if err = d.DeserializeAndValidate(&r); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	err = r.RollBack()
	if err != nil {
		logger.Error("roll back failed %s", err.Error())
	}
	return
}

// Run 运行函数
func (d *CheckLedgerMetadataAct) Run() (err error) {
	steps := subcmd.Steps{
		/* Todo
		{
			FunName: "预检查",
			Func:    d.Service.PreCheck,
		},
		*/
		{
			FunName: "pulsar 检查Ledger的元数据",
			Func:    d.Service.CheckLedgerMetadata,
		},
	}

	if err := steps.Run(); err != nil {
		rollbackCtxb, rerr := json.Marshal(d.Service.RollBackContext)
		if rerr != nil {
			logger.Error("json Marshal %s", err.Error())
			fmt.Printf("<ctx>Can't RollBack<ctx>\n")
		}
		fmt.Printf("<ctx>%s<ctx>\n", string(rollbackCtxb))
		return err
	}

	logger.Info("check_ledger_metadata successfully")
	return nil
}
