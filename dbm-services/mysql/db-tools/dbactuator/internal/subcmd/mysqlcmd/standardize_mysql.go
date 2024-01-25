package mysqlcmd

import (
	"fmt"

	"github.com/spf13/cobra"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
)

type StandardizeMySQLAct struct {
	*subcmd.BaseOptions
	Payload mysql.StandardizeMySQLComp
}

const (
	StandardizeMySQLInstance = "standardize-mysql"
)

func NewStandardizeMySQLCommand() *cobra.Command {
	act := StandardizeMySQLAct{
		BaseOptions: subcmd.GBaseOptions,
	}

	cmd := &cobra.Command{
		Use:   StandardizeMySQLInstance,
		Short: "接管 MySQL 实例",
		Example: fmt.Sprintf(
			`dbactuator mysql %s %s %s`,
			StandardizeMySQLInstance, subcmd.CmdBaseExampleStr, subcmd.ToPrettyJson(act.Payload.Example())),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}

	return cmd
}

func (c *StandardizeMySQLAct) Validate() (err error) {
	return c.BaseOptions.Validate()
}

func (c *StandardizeMySQLAct) Init() (err error) {
	if err = c.Deserialize(&c.Payload.Params); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	c.Payload.GeneralParam = subcmd.GeneralRuntimeParam
	logger.Info("extend params: %s", c.Payload.Params)
	return nil
}

func (c *StandardizeMySQLAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "初始化",
			Func:    c.Payload.Init,
		},
		{
			FunName: "清理旧系统crontab",
			Func:    c.Payload.ClearOldCrontab,
		},
		{
			FunName: "清理旧系统帐号",
			Func:    c.Payload.DropOldAccounts,
		},
		{
			FunName: "初始化帐号库表",
			Func:    c.Payload.InitDefaultPrivAndSchema,
		},
	}
	if err := steps.Run(); err != nil {
		logger.Error("run adopt scr tendbha storage failed: %s", err.Error())
		return err
	}
	logger.Info("接管 MySQL 实例完成")
	return nil
}
