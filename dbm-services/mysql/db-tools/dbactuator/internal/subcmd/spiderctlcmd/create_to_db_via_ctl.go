package spiderctlcmd

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/rename_dbs"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"fmt"

	"github.com/spf13/cobra"
)

type CreateToDBViaCtlAct struct {
	*subcmd.BaseOptions
	BaseService rename_dbs.ViaCtlComponent
}

func NewCreateToDBViaCtlCommand() *cobra.Command {
	act := CreateToDBViaCtlAct{
		BaseOptions: subcmd.GBaseOptions,
	}

	subCmdStr := "create-to-db-via-ctl"

	cmd := &cobra.Command{
		Use:   subCmdStr,
		Short: "中控创建目标库",
		Example: fmt.Sprintf(
			`dbactuator spiderctl %s %s %s`,
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

func (c *CreateToDBViaCtlAct) Init() error {
	logger.Info("create to db via ctl init")
	if err := c.Deserialize(&c.BaseService.Param); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}

	c.BaseService.GeneralParam = subcmd.GeneralRuntimeParam
	return nil
}

func (c *CreateToDBViaCtlAct) Run() error {
	steps := subcmd.Steps{
		{
			FunName: "Init",
			Func: func() error {
				return c.BaseService.Init(c.Uid)
			},
		},
		{
			FunName: "获取表详情",
			Func:    c.BaseService.ListTables,
		},
		{
			FunName: "新建目标库",
			Func:    c.BaseService.CreateToDB,
		},
		{
			FunName: "目标建其他对象",
			Func:    c.BaseService.CreateSchemaInToDB,
		},
	}

	if err := steps.Run(); err != nil {
		logger.Error("run create to db via ctl failed, %v", err)
		return err
	}

	logger.Info("create to db via ctl success")
	return nil
}
