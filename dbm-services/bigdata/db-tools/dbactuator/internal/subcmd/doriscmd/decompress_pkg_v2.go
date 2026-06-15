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

// DecompressDorisPkgV2Act 用于解压缩 Doris 包的结构体
type DecompressDorisPkgV2Act struct {
	*subcmd.BaseOptions
	Service doris.DecompressPkgService
}

// DecompressDorisPkgV2Command 创建解压缩 Doris 包的命令
func DecompressDorisPkgV2Command() *cobra.Command {
	act := DecompressDorisPkgV2Act{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "decompress_pkg_v2",
		Short:   "解压缩v2",
		Example: fmt.Sprintf(`dbactuator doris decompress_pkg_v2 %s`, subcmd.CmdBaseExapmleStr),
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
func (d *DecompressDorisPkgV2Act) Validate() (err error) {
	return d.BaseOptions.Validate()
}

// Init 用于初始化
func (d *DecompressDorisPkgV2Act) Init() (err error) {
	logger.Info("DecompressDorisPkgV2Act 初始化")
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
func (d *DecompressDorisPkgV2Act) Rollback() (err error) {
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
func (d *DecompressDorisPkgV2Act) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "预检查",
			Func:    d.Service.PreCheck,
		},
		{
			FunName: "解压缩",
			Func:    d.Service.DecompressDorisPkgV2,
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

	logger.Info("decompress_pkg_v2 执行成功")
	return nil
}
