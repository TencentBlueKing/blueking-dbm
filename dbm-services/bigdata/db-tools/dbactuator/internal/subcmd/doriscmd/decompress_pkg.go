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

// DecompressDorisPkgAct 用于解压缩 Doris 包的结构体
type DecompressDorisPkgAct struct {
	*subcmd.BaseOptions
	Service doris.DecompressPkgService
}

// DecompressDorisPkgCommand 创建解压缩 Doris 包的命令
func DecompressDorisPkgCommand() *cobra.Command {
	act := DecompressDorisPkgAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "decompress_pkg",
		Short:   "解压缩",
		Example: fmt.Sprintf(`dbactuator doris decompress_pkg %s`, subcmd.CmdBaseExapmleStr),
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
func (d *DecompressDorisPkgAct) Validate() (err error) {
	return d.BaseOptions.Validate()
}

// Init 用于初始化
func (d *DecompressDorisPkgAct) Init() (err error) {
	logger.Info("DecompressDorisPkgAct 初始化")
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
func (d *DecompressDorisPkgAct) Rollback() (err error) {
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
func (d *DecompressDorisPkgAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "预检查",
			Func:    d.Service.PreCheck,
		},
		{
			FunName: "解压缩",
			Func:    d.Service.DecompressDorisPkg,
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

	logger.Info("decompress_pkg 执行成功")
	return nil
}
