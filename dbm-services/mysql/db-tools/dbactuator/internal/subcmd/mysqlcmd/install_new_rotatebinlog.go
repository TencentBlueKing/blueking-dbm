package mysqlcmd

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"fmt"

	"github.com/spf13/cobra"
)

// InstallRotateBinlogAct TODO
type InstallRotateBinlogAct struct {
	*subcmd.BaseOptions
	Service mysql.InstallRotateBinlogComp
}

// CommandDeployRotatebinlog TODO
const CommandDeployRotatebinlog = "deploy-rotatebinlog"

// NewInstallRotateBinlogCommand TODO
func NewInstallRotateBinlogCommand() *cobra.Command {
	act := InstallRotateBinlogAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   CommandDeployRotatebinlog,
		Short: "部署 rotate_binlog",
		Example: fmt.Sprintf(
			`dbactuator mysql %s %s %s`, CommandDeployRotatebinlog,
			subcmd.CmdBaseExampleStr,
			subcmd.ToPrettyJson(act.Service.Example()),
		),
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

// Init TODO
func (d *InstallRotateBinlogAct) Init() (err error) {
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return nil
}

// Run TODO
func (d *InstallRotateBinlogAct) Run() (err error) {
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
			FunName: "部署二进制",
			Func:    d.Service.DeployBinary,
		},
		{
			FunName: "渲染 config.yaml",
			Func:    d.Service.GenerateBinaryConfig,
		},
		{
			FunName: "添加系统crontab",
			Func:    d.Service.InstallCrontab,
		},
	}

	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("install new rotate_binlog successfully~")
	return nil
}

// Rollback TODO
func (d *InstallRotateBinlogAct) Rollback() (err error) {
	return
}
