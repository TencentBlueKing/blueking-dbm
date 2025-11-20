package doriscmd

import (
	"dbm-services/bigdata/db-tools/dbactuator/internal/subcmd"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/components/doris"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util"
	"dbm-services/common/go-pubpkg/logger"
	"encoding/json"
	"fmt"

	"github.com/spf13/cobra"
)

// CreateResourceAct TODO
type CreateResourceAct struct {
	*subcmd.BaseOptions
	Service doris.CreateResourceService
}

// CreateResourceCommand TODO
func CreateResourceCommand() *cobra.Command {
	act := CreateResourceAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	// 生成 Doris创建资源 命令
	cmd := &cobra.Command{
		Use:     "create_resource",
		Short:   "doris 关联冷存储资源",
		Example: fmt.Sprintf(`dbactuator doris create_resource %s`, subcmd.CmdBaseExapmleStr),
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
func (d *CreateResourceAct) Validate() (err error) {
	return d.BaseOptions.Validate()
}

// Init 用于初始化
func (d *CreateResourceAct) Init() (err error) {
	logger.Info("CreateResourceAct Init")
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	// 初始化Doris安装默认参数
	d.Service.InstallParams = doris.InitDefaultInstallParam()
	return nil
}

// Rollback 用于回滚操作
// @receiver d
//
//	@return err
func (d *CreateResourceAct) Rollback() (err error) {
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
func (d *CreateResourceAct) Run() (err error) {
	// 步骤1. 创建Doris资源
	steps := subcmd.Steps{

		{
			FunName: "创建Doris冷存储资源",
			Func:    d.Service.CreateResource,
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

	logger.Info("create resource successfully")
	return nil
}
