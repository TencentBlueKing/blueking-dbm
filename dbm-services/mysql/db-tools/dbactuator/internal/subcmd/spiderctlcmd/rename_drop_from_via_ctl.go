package spiderctlcmd

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/rename_dbs"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"fmt"

	"github.com/spf13/cobra"
)

type RenameDropFromViaCtlAct struct {
	*subcmd.BaseOptions
	BaseService rename_dbs.ViaCtlComponent
}

func NewRenameDropFromViaCtlCommand() *cobra.Command {
	act := RenameDropFromViaCtlAct{
		BaseOptions: subcmd.GBaseOptions,
	}

	subCmdStr := "rename-drop-from-via-ctl"
	cmd := &cobra.Command{
		Use:   subCmdStr,
		Short: subCmdStr,
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

func (c *RenameDropFromViaCtlAct) Init() error {
	logger.Info("drop from db via ctl init")
	if err := c.Deserialize(&c.BaseService.Param); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}

	c.BaseService.GeneralParam = subcmd.GeneralRuntimeParam
	return nil
}

func (c *RenameDropFromViaCtlAct) Run() error {
	steps := subcmd.Steps{
		{
			FunName: "初始化",
			Func: func() error {
				return c.BaseService.Init(c.Uid)
			},
		},
		{
			FunName: "执行重命名",
			Func:    c.BaseService.DropFromDB,
		},
	}

	if err := steps.Run(); err != nil {
		logger.Error("drop from db via ctl failed, %v", err)
		return err
	}

	logger.Info("drop from db via ctl success")
	return nil
}
