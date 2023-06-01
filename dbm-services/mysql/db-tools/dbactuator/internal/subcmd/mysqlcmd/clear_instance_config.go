package mysqlcmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// 定义mysql实例级别的配置清理过程
// 1:清理例行备份程序的实例配置
// 2:清理例行校验程序的实例配置
// 3:清理rotate_binlog的实例配置

// ClearInstanceConfig 清理实例配置
const ClearInstanceConfig = "clear-inst-config"

// ClearInstanceConfigAct 清理实例配置
type ClearInstanceConfigAct struct {
	*subcmd.BaseOptions
	Service mysql.ClearInstanceConfigComp
}

// ClearInstanceConfigCommand 清理配置子命令
// @return *cobra.Command
func ClearInstanceConfigCommand() *cobra.Command {
	act := ClearInstanceConfigAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   ClearInstanceConfig,
		Short: "清理实例级别的周边配置",
		Example: fmt.Sprintf(
			`dbactuator mysql %s %s %s`,
			ClearInstanceConfig, subcmd.CmdBaseExampleStr, subcmd.ToPrettyJson(act.Service.Example()),
		),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Init 初始化清理实例配置
func (g *ClearInstanceConfigAct) Init() (err error) {
	if err = g.Deserialize(&g.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	g.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return
}

// Run 清理实例配置执行入口
func (g *ClearInstanceConfigAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "清理目标实例初始化",
			Func:    g.Service.Init,
		},
		{
			FunName: "清理目标实例的周边配置",
			Func:    g.Service.DoClear,
		},
	}

	if err := steps.Run(); err != nil {
		return err
	}

	logger.Info("clear instance config successfully")
	return nil
}
