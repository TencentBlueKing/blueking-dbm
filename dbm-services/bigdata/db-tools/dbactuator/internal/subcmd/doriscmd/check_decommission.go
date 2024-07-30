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

// CheckDecommissionAct 用于检查BE节点退役的结构体
type CheckDecommissionAct struct {
	*subcmd.BaseOptions
	Service doris.CheckDecommissionService
}

// CheckDecommissionCommand 创建检查BE节点退役的命令
func CheckDecommissionCommand() *cobra.Command {
	act := CheckDecommissionAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "check_decommission",
		Short:   "检查BE节点退役",
		Example: fmt.Sprintf(`dbactuator doris check_decommission %s`, subcmd.CmdBaseExapmleStr),
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
func (d *CheckDecommissionAct) Validate() (err error) {
	return d.BaseOptions.Validate()
}

// Init 用于初始化
func (d *CheckDecommissionAct) Init() (err error) {
	logger.Info("CheckDecommissionAct 初始化")
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate 失败, %v", err)
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	d.Service.InstallParams = doris.InitDefaultInstallParam()

	return nil
}

// Rollback 用于回滚操作
//
// @receiver d
// @return err
func (d *CheckDecommissionAct) Rollback() (err error) {
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

// Run 用于执行操作
func (d *CheckDecommissionAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "检查数据节点退役",
			Func:    d.Service.CheckDecommission,
		},
	}

	// 解析每个步骤执行返回内容的JSON
	if err := steps.Run(); err != nil {
		rollbackCtxBytes, jsonErr := json.Marshal(d.Service.RollBackContext)
		if jsonErr != nil {
			logger.Error("JSON Marshal %s", err.Error())
			fmt.Printf("<ctx>无法回滚<ctx>\n")
		}
		fmt.Printf("<ctx>%s<ctx>\n", string(rollbackCtxBytes))
		return err
	}

	logger.Info("check_decommission 执行成功")
	return nil
}
