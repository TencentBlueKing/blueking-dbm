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

// CheckBackendsAliveAct 检查BE节点是否加入集群
type CheckBackendsAliveAct struct {
	*subcmd.BaseOptions
	Service doris.CheckBackendsAliveService
}

// CheckBackendsAliveCommand 创建检查BE节点是否加入集群的命令
func CheckBackendsAliveCommand() *cobra.Command {
	act := CheckBackendsAliveAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "check_backends_alive",
		Short:   "检查BE节点是否加入集群",
		Example: fmt.Sprintf(`dbactuator doris check_backends_alive %s`, subcmd.CmdBaseExapmleStr),
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

// Validate 验证参数
func (d *CheckBackendsAliveAct) Validate() (err error) {
	return d.BaseOptions.Validate()
}

// Init 初始化
func (d *CheckBackendsAliveAct) Init() (err error) {
	logger.Info("CheckBackendsAliveAct 初始化")
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate 失败, %v", err)
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	d.Service.InstallParams = doris.InitDefaultInstallParam()
	return nil
}

// Rollback 回滚
func (d *CheckBackendsAliveAct) Rollback() (err error) {
	var r rollback.RollBackObjects
	if err = d.DeserializeAndValidate(&r); err != nil {
		logger.Error("DeserializeAndValidate 失败, %v", err)
		return err
	}
	err = r.RollBack()
	if err != nil {
		logger.Error("回滚失败 %s", err.Error())
	}
	return
}

// Run 执行
func (d *CheckBackendsAliveAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "检查BE节点是否加入集群",
			Func:    d.Service.CheckBackendsAlive,
		},
	}
	if err := steps.Run(); err != nil {
		rollbackCtxBytes, jsonErr := json.Marshal(d.Service.RollBackContext)
		if jsonErr != nil {
			logger.Error("JSON Marshal %s", err.Error())
			fmt.Printf("<ctx>无法回滚<ctx>\n")
		}
		fmt.Printf("<ctx>%s<ctx>\n", string(rollbackCtxBytes))
		return err
	}
	logger.Info("check_backends_alive 执行成功")
	return nil
}
