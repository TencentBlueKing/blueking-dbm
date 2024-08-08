package mysqlcmd

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/rename_dbs"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"fmt"

	"github.com/spf13/cobra"
)

type RenameOnMySQLAct struct {
	*subcmd.BaseOptions
	BaseService rename_dbs.OnMySQLComponent
}

func NewRenameOnMySQLCommand() *cobra.Command {
	act := RenameOnMySQLAct{
		BaseOptions: subcmd.GBaseOptions,
	}

	subCmdStr := "rename-on-mysql"

	cmd := &cobra.Command{
		Use:   subCmdStr,
		Short: "在MySQL执行DB重命名",
		Example: fmt.Sprintf(
			`dbactuator mysql %s %s %s`,
			subCmdStr,
			subcmd.CmdBaseExampleStr,
			subcmd.ToPrettyJson(act.BaseService.Example()),
		),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

func (c *RenameOnMySQLAct) Init() error {
	logger.Info("create stage via ctl init")
	if err := c.Deserialize(&c.BaseService.Param); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}

	c.BaseService.GeneralParam = subcmd.GeneralRuntimeParam
	return nil
}

func (c *RenameOnMySQLAct) Run() error {
	steps := subcmd.Steps{
		{
			FunName: "初始化",
			Func: func() error {
				return c.BaseService.Init(c.Uid)
			},
		},
		{
			FunName: "执行重命名",
			Func:    c.BaseService.Do,
		},
	}

	if err := steps.Run(); err != nil {
		logger.Error("rename on mysql failed, %v", err)
		return err
	}

	logger.Info("rename on mysql success")
	return nil
}
