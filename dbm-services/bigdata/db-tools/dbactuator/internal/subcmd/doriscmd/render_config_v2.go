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

// RenderConfigV2Act 用于渲染配置的V2版本结构体
type RenderConfigV2Act struct {
	*subcmd.BaseOptions
	Service doris.InstallDorisService
}

// RenderConfigV2Command 创建渲染配置V2版本的命令
func RenderConfigV2Command() *cobra.Command {
	act := RenderConfigV2Act{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "render_config_v2",
		Short:   "doris 渲染集群配置v2",
		Example: fmt.Sprintf(`dbactuator doris render_config_v2 %s`, subcmd.CmdBaseExapmleStr),
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
func (d *RenderConfigV2Act) Validate() (err error) {
	return d.BaseOptions.Validate()
}

// Init 用于初始化
func (d *RenderConfigV2Act) Init() (err error) {
	logger.Info("RenderConfigV2Act Init")
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
func (d *RenderConfigV2Act) Rollback() (err error) {
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
func (d *RenderConfigV2Act) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "渲染Doris配置V2",
			Func:    d.Service.RenderConfigV2,
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

	logger.Info("render_config_v2 successfully")
	return nil
}
