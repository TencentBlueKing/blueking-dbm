package doriscmd

import (
	"dbm-services/bigdata/db-tools/dbactuator/pkg/components/doris"
	"encoding/json"
	"fmt"

	"dbm-services/bigdata/db-tools/dbactuator/internal/subcmd"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util"
	"dbm-services/common/go-pubpkg/logger"

	"github.com/spf13/cobra"
)

// InstallSupervisorAct TODO
type InstallSupervisorAct struct {
	*subcmd.BaseOptions
	Service doris.InstallDorisService
}

// InstallSupervisorCommand TODO
func InstallSupervisorCommand() *cobra.Command {
	act := InstallSupervisorAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "install_supervisor",
		Short:   "部署supervisor",
		Example: fmt.Sprintf(`dbactuator doris install_supervisor %s`, subcmd.CmdBaseExapmleStr),
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

// Validate 用于验证参数
func (d *InstallSupervisorAct) Validate() (err error) {
	return d.BaseOptions.Validate()
}

// Init 用于初始化
func (d *InstallSupervisorAct) Init() (err error) {
	logger.Info("InstallSupervisorAct Init")
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	d.Service.InstallParams = doris.InitDefaultInstallParam()
	return nil
}

// Rollback 用于回滚操作
//
//	@receiver d
//	@return err
func (d *InstallSupervisorAct) Rollback() (err error) {
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

// Run 用于执行
func (d *InstallSupervisorAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "部署Supervisor",
			Func:    d.Service.InstallSupervisor,
		},
	}

	// json 解析每个步骤执行返回内容
	if err := steps.Run(); err != nil {
		rollbackCtxBytes, jsonErr := json.Marshal(d.Service.RollBackContext)
		if jsonErr != nil {
			logger.Error("json Marshal %s", err.Error())
			fmt.Printf("<ctx>Can't RollBack<ctx>\n")
		}
		fmt.Printf("<ctx>%s<ctx>\n", string(rollbackCtxBytes))
		return err
	}

	logger.Info("install_supervisor successfully")
	return nil
}
