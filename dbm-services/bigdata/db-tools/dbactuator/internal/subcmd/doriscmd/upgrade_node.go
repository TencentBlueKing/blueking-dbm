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

// UpgradeNodeAct 升级节点操作结构体
type UpgradeNodeAct struct {
	*subcmd.BaseOptions
	Service doris.UpgradeService
}

// UpgradeNodeCommand 创建升级节点命令
func UpgradeNodeCommand() *cobra.Command {
	act := UpgradeNodeAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "upgrade_node",
		Short:   "升级doris节点",
		Example: fmt.Sprintf(`dbactuator doris upgrade_node %s`, subcmd.CmdBaseExapmleStr),
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
func (d *UpgradeNodeAct) Validate() (err error) {
	return d.BaseOptions.Validate()
}

// Init 用于初始化
func (d *UpgradeNodeAct) Init() (err error) {
	logger.Info("UpgradeNodeAct Init")
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
func (d *UpgradeNodeAct) Rollback() (err error) {
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

// Run 用于执行升级操作
func (d *UpgradeNodeAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "升级预检查",
			Func:    d.Service.PreCheck,
		},
		{
			FunName: "停止进程",
			Func:    d.Service.StopProcess,
		},
		{
			FunName: "切换角色软链",
			Func:    d.Service.SwitchRoleLink,
		},
		{
			FunName: "切换JDK软链",
			Func:    d.Service.SwitchJdkLink,
		},
		{
			FunName: "新版本目录赋权",
			Func:    d.Service.ChownNewVersion,
		},
		{
			FunName: "启动进程",
			Func:    d.Service.StartProcess,
		},
		{
			FunName: "校验组件RUNNING",
			Func:    d.Service.CheckComponentRunning,
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

	logger.Info("upgrade_node successfully")
	return nil
}
