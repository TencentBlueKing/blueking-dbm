package mysqlcmd

import (
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/peripheraltools/dbbackup"
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

type PushNewDbBackupConfigAct struct {
	*subcmd.BaseOptions
	Service dbbackup.NewDbBackupComp
}

const PushNewDbBackupConfig = `push-new-db-backup-config`

func NewPushNewDbBackupConfigCommand() *cobra.Command {
	act := PushNewDbBackupConfigAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   PushNewDbBackupConfig,
		Short: "推送GO版本备份配置",
		Example: fmt.Sprintf(
			`dbactuator mysql %s %s %s`,
			PushNewDbBackupConfig,
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

func (d *PushNewDbBackupConfigAct) Init() (err error) {
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return nil
}

func (d *PushNewDbBackupConfigAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "init",
			Func:    d.Service.Init,
		},
		{
			FunName: "初始化待渲染配置",
			Func:    d.Service.InitRenderData,
		},

		{
			FunName: "生成配置",
			Func:    d.Service.GenerateRuntimeConfig,
		},
		{
			FunName: "重载配置",
			Func:    d.Service.AddCrontab,
		},
	}

	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("push new dbbackup config successfully")
	return nil
}
