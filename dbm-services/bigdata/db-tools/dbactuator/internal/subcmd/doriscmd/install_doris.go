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

// InstallDorisAct TODO
type InstallDorisAct struct {
	// BaseOptions 基本参数
	*subcmd.BaseOptions
	// Service 安装DorisService方法接口层
	Service doris.InstallDorisService
}

// InstallDorisCommand TODO
func InstallDorisCommand() *cobra.Command {
	act := InstallDorisAct{
		BaseOptions: subcmd.GBaseOptions, // 初始化 InstallDorisAct 结构体
	}

	// 创建命令
	cmd := &cobra.Command{
		Use:     "install_doris",                                                            // 命令名称
		Short:   "部署doris",                                                                  // 命令简短描述
		Example: fmt.Sprintf(`dbactuator doris install_doris %s`, subcmd.CmdBaseExapmleStr), // 命令示例
		Run: func(cmd *cobra.Command, args []string) {
			// 验证参数
			util.CheckErr(act.Validate())
			// 检查是否需要回滚
			if act.RollBack {
				util.CheckErr(act.Rollback())
				return
			}
			// 执行初始化
			util.CheckErr(act.Init())
			// 执行部署操作
			util.CheckErr(act.Run())
		},
	}

	return cmd
}

// Validate 用于验证参数
func (d *InstallDorisAct) Validate() (err error) {
	return d.BaseOptions.Validate()
}

// Init 用于初始化
func (d *InstallDorisAct) Init() (err error) {
	logger.Info("InstallDorisAct Init")
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
func (d *InstallDorisAct) Rollback() (err error) {
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
func (d *InstallDorisAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "部署Doris",
			Func:    d.Service.InstallDoris,
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

	logger.Info("install_doris successfully")
	return nil
}
