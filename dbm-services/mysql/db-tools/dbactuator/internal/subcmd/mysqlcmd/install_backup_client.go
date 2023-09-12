package mysqlcmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// InstallBackupClientAct TODO
type InstallBackupClientAct struct {
	*subcmd.BaseOptions
	Service mysql.InstallBackupClientComp
}

// CommandInstallBackupClient TODO
const CommandInstallBackupClient = "install-backup-client"

// InstallBackupClientCommand TODO
func InstallBackupClientCommand() *cobra.Command {
	act := InstallBackupClientAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   CommandInstallBackupClient,
		Short: "部署 backup_client",
		Example: fmt.Sprintf(
			`dbactuator mysql %s %s %s`, CommandInstallBackupClient,
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
func (d *InstallBackupClientAct) Init() (err error) {
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return nil
}

// Run TODO
func (d *InstallBackupClientAct) Run() (err error) {
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
			FunName: "渲染 config.toml",
			Func:    d.Service.GenerateBinaryConfig,
		},
		{
			FunName: "生成 cosinfo.toml",
			Func:    d.Service.GenerateBucketConfig,
		},
		{
			FunName: "添加 upload crontab",
			Func:    d.Service.InstallCrontab,
		},
	}

	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("install backup_client successfully~")
	return nil
}

// Rollback TODO
func (d *InstallBackupClientAct) Rollback() (err error) {
	return
}
