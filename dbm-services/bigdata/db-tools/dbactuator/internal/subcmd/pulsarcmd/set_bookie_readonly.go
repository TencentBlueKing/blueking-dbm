package pulsarcmd

import (
	"encoding/json"
	"fmt"

	"dbm-services/bigdata/db-tools/dbactuator/internal/subcmd"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/components/pulsar"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util"
	"dbm-services/common/go-pubpkg/logger"

	"github.com/spf13/cobra"
)

// SetBookieReadOnlyAct 设置bookie只读结构体
type SetBookieReadOnlyAct struct {
	*subcmd.BaseOptions
	Service pulsar.CheckPulsarShrinkComp
}

// SetBookieReadOnlyCommand 设置bookie只读命令
func SetBookieReadOnlyCommand() *cobra.Command {
	// dbactuator pulsar set_bookie_readonly --payload xxxxx
	act := SetBookieReadOnlyAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "set_bookie_readonly",
		Short:   "设置bookie只读状态",
		Example: fmt.Sprintf(`dbactuator pulsar set_bookie_readonly %s`, subcmd.CmdBaseExapmleStr),
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
func (d *SetBookieReadOnlyAct) Validate() (err error) {
	return d.BaseOptions.Validate()
}

// Init 初始化函数
func (d *SetBookieReadOnlyAct) Init() (err error) {
	logger.Info("UnsetBookieReadOnlyAct Init")
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return d.Service.Init()
}

// Rollback 回滚函数
func (d *SetBookieReadOnlyAct) Rollback() (err error) {
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
func (d *SetBookieReadOnlyAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "设置bookie只读状态",
			Func:    d.Service.SetBookieReadonly,
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

	logger.Info("set_bookie_readonly successfully")
	return nil
}
