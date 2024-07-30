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

// InitSystemConfigAct TODO
type InitSystemConfigAct struct {
	*subcmd.BaseOptions
	Service doris.InitSystemConfigService
}

// InitSystemConfigCommand TODO
func InitSystemConfigCommand() *cobra.Command {
	act := InitSystemConfigAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "init",
		Short:   "doris 初始化系统配置",
		Example: fmt.Sprintf(`dbactuator doris init %s`, subcmd.CmdBaseExampleStr),
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
func (d *InitSystemConfigAct) Validate() (err error) {
	return d.BaseOptions.Validate()
}

// Init 用于初始化
func (d *InitSystemConfigAct) Init() (err error) {
	logger.Info("InitSystemConfigAct Init")
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return nil
}

// Rollback 用于回滚操作
// @receiver d
//
//	@return err
func (d *InitSystemConfigAct) Rollback() (err error) {
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
// 1. 创建执行用户 e.g. mysql
// 2. 初始化安装目录 e.g. /data/dorisenv
// 3. 修改Doris 推荐的系统配置
// 4. Doris, Java 等环境变量写入profile
func (d *InitSystemConfigAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "创建执行用户",
			Func:    d.Service.CreateExecuteUser,
		},
		{
			FunName: "初始化安装及数据目录",
			Func:    d.Service.InitInstallDir,
		},
		{
			FunName: "修改系统配置",
			Func:    d.Service.UpdateSystemConfig,
		},
		{
			FunName: "写入profile",
			Func:    d.Service.WriteProfile,
		},
	}

	if err := steps.Run(); err != nil {
		rollbackCtxBytes, jsonErr := json.Marshal(d.Service.RollBackContext)
		if jsonErr != nil {
			logger.Error("json Marshal %s", err.Error())
			fmt.Printf("<ctx>Can't RollBack<ctx>\n")
		}
		fmt.Printf("<ctx>%s<ctx>\n", string(rollbackCtxBytes))
		return err
	}

	logger.Info("init successfully")
	return nil
}
