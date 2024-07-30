package doriscmd

import (
	"encoding/json"
	"fmt"

	"dbm-services/bigdata/db-tools/dbactuator/internal/subcmd"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/components/doris"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util"
	"dbm-services/common/go-pubpkg/logger"

	"github.com/spf13/cobra"
)

// RestartProcessAct TODO
type RestartProcessAct struct {
	*subcmd.BaseOptions
	Service doris.NodeOperationService
}

// RestartProcessCommand TODO
func RestartProcessCommand() *cobra.Command {
	act := RestartProcessAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "restart_process",                                                            // 命令用法
		Short:   "重启doris进程",                                                                  // 命令简短描述
		Example: fmt.Sprintf(`dbactuator doris restart_process %s`, subcmd.CmdBaseExapmleStr), // 命令示例
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
func (d *RestartProcessAct) Validate() (err error) {
	return d.BaseOptions.Validate()
}

// Init 用于初始化
func (d *RestartProcessAct) Init() (err error) {
	logger.Info("RestartProcessAct Init")
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	d.Service.InstallParams = doris.InitDefaultInstallParam()

	return nil
}

// Rollback 用于回滚操作
//
//	@receiver d
//	@return err
func (d *RestartProcessAct) Rollback() (err error) {
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
func (d *RestartProcessAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "重启doris进程",
			Func:    d.Service.StartStopComponent,
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

	logger.Info("restart_process successfully")
	return nil
}
