package mysqlcmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// InstallMysqlRotateBinlogAct TODO
type InstallMysqlRotateBinlogAct struct {
	*subcmd.BaseOptions
	Service mysql.InstallMysqlRotateBinlogComp
}

// CommandDeployMysqlRotatebinlog TODO
const CommandDeployMysqlRotatebinlog = "deploy-mysql-rotatebinlog"

// NewInstallRotateBinlogCommand TODO
func NewInstallRotateBinlogCommand() *cobra.Command {
	act := InstallMysqlRotateBinlogAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   CommandDeployMysqlRotatebinlog,
		Short: "部署 mysql rotate binlog",
		Example: fmt.Sprintf(
			`dbactuator mysql %s %s %s`, CommandDeployMysqlRotatebinlog,
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
func (d *InstallMysqlRotateBinlogAct) Init() (err error) {
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return nil
}

// Run TODO
func (d *InstallMysqlRotateBinlogAct) Run() (err error) {
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
		{
			FunName: "迁移旧rotate_logbin",
			Func:    d.Service.RunMigrateOld,
		},
	}

	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("install new rotate_binlog successfully~")
	return nil
}

// Rollback TODO
func (d *InstallMysqlRotateBinlogAct) Rollback() (err error) {
	return
}
