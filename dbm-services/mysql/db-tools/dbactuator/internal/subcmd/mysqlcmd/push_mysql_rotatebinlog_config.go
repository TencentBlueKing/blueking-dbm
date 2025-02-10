package mysqlcmd

import (
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/peripheraltools/rotatebinlog"
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

type PushMySQLRotateBinlogConfigAct struct {
	*subcmd.BaseOptions
	Service rotatebinlog.MySQLRotateBinlogComp
}

const PushMySQLRotatebinlogConfig = "push-mysql-rotatebinlog-config"

func NewPushMySQLRotateBinlogConfigCommand() *cobra.Command {
	act := PushMySQLRotateBinlogConfigAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   PushMySQLRotatebinlogConfig,
		Short: "推送 mysql rotate binlog 配置",
		Example: fmt.Sprintf(
			`dbactuator mysql %s %s %s`,
			PushMySQLRotatebinlogConfig,
			subcmd.CmdBaseExampleStr,
			subcmd.ToPrettyJson(act.Service.Example()),
		),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

func (d *PushMySQLRotateBinlogConfigAct) Init() (err error) {
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return nil
}

func (d *PushMySQLRotateBinlogConfigAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "init",
			Func:    d.Service.Init,
		},
		{
			FunName: "预检查",
			Func:    d.Service.PreCheck,
		},
		{
			FunName: "渲染 config.yaml",
			Func:    d.Service.GenerateRuntimeConfig,
		},
		{
			FunName: "重载配置",
			Func:    d.Service.AddCrond,
		},
	}

	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("push new rotate_binlog config successfully")
	return nil
}
