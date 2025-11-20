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

// DropResourceAct TODO
type DropResourceAct struct {
	*subcmd.BaseOptions
	Service doris.DropResourceService
}

// DropResourceCommand TODO
func DropResourceCommand() *cobra.Command {
	act := DropResourceAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	// 生成Doris删除存储资源命令
	cmd := &cobra.Command{
		Use:     "drop_resource",
		Short:   "doris 解绑冷存储资源",
		Example: fmt.Sprintf(`dbactuator doris drop_resource %s`, subcmd.CmdBaseExapmleStr),
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
func (d *DropResourceAct) Validate() (err error) {
	return d.BaseOptions.Validate()
}

// Init 用于初始化
func (d *DropResourceAct) Init() (err error) {
	logger.Info("DropResourceAct Init")
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	// 获取Doris默认安装参数
	d.Service.InstallParams = doris.InitDefaultInstallParam()
	return nil
}

// Rollback 用于回滚操作
// @receiver d
//
//	@return err
func (d *DropResourceAct) Rollback() (err error) {
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
func (d *DropResourceAct) Run() (err error) {
	// 指定metadata操作，删除Doris存储资源
	// TODO 待定增加是否判断资源有策略policy引用
	steps := subcmd.Steps{

		{
			FunName: "解绑Doris冷存储资源",
			Func:    d.Service.DropResource,
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

	logger.Info("drop resource successfully")
	return nil
}
