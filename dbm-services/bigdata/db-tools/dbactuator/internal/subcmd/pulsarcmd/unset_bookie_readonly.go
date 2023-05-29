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

// UnsetBookieReadOnlyAct 取消bookie只读结构体
type UnsetBookieReadOnlyAct struct {
	*subcmd.BaseOptions
	Service pulsar.CheckPulsarShrinkComp
}

// UnsetBookieReadOnlyCommand 取消bookie只读命令
func UnsetBookieReadOnlyCommand() *cobra.Command {
	// dbactuator pulsar unset_bookie_readonly --payload xxxxx
	act := UnsetBookieReadOnlyAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "unset_bookie_readonly",
		Short:   "取消bookie只读状态",
		Example: fmt.Sprintf(`dbactuator pulsar unset_bookie_readonly %s`, subcmd.CmdBaseExapmleStr),
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
func (d *UnsetBookieReadOnlyAct) Validate() (err error) {
	return d.BaseOptions.Validate()
}

// Init 初始化函数
func (d *UnsetBookieReadOnlyAct) Init() (err error) {
	logger.Info("UnsetBookieReadOnlyAct Init")
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return d.Service.Init()
}

// Rollback 回滚函数
func (d *UnsetBookieReadOnlyAct) Rollback() (err error) {
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
func (d *UnsetBookieReadOnlyAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "取消bookie只读状态",
			Func:    d.Service.UnsetBookieReadonly,
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

	logger.Info("unset_bookie_readonly successfully")
	return nil
}
