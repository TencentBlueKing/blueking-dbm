package mysqlcmd

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/peripheraltools/backup_client"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"fmt"

	"github.com/spf13/cobra"
)

type PushBackupClientConfigAct struct {
	*subcmd.BaseOptions
	Service backup_client.BackupClientComp
}

const CommandPushBackupClientConfig = `push-backup-client-config`

func NewPushBackupClientConfigCommand() *cobra.Command {
	act := PushBackupClientConfigAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   CommandPushBackupClientConfig,
		Short: "推送 backup_client 配置",
		Example: fmt.Sprintf(
			`dbactuator mysql %s %s %s`, CommandPushBackupClientConfig,
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

func (d *PushBackupClientConfigAct) Init() (err error) {
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return nil
}

func (d *PushBackupClientConfigAct) Run() (err error) {
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
			FunName: "渲染 config.toml",
			Func:    d.Service.GenerateBinaryConfig,
		},
		{
			FunName: "生成 cosinfo.toml",
			Func:    d.Service.GenerateBucketConfig,
		},
	}

	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("push backup_client config successfully")
	return nil
}
