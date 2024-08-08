package mysqlcmd

import (
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/rename_dbs"
	"fmt"

	"github.com/spf13/cobra"
)

type RenamePreDropToOnRemoteAct struct {
	*subcmd.BaseOptions
	BaseService rename_dbs.PreDropToOnRemoteComponent
}

func NewRenamePreDropToOnRemoteCommand() *cobra.Command {
	act := RenamePreDropToOnRemoteAct{
		BaseOptions: subcmd.GBaseOptions,
	}

	subCmdStr := "rename-pre-drop-to-on-remote"

	cmd := &cobra.Command{
		Use:   subCmdStr,
		Short: "在remote与清理目标库",
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

func (c *RenamePreDropToOnRemoteAct) Init() error {
	logger.Info("pre drop to via ctl init")
	if err := c.Deserialize(&c.BaseService.Param); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}

	c.BaseService.GeneralParam = subcmd.GeneralRuntimeParam
	return nil
}

func (c *RenamePreDropToOnRemoteAct) Run() error {
	steps := subcmd.Steps{
		{
			FunName: "执行预清理",
			Func:    c.BaseService.Do,
		},
	}

	if err := steps.Run(); err != nil {
		logger.Error("pre drop to on remote failed, %v", err)
		return err
	}

	logger.Info("pre drop to on remote success")
	return nil
}
