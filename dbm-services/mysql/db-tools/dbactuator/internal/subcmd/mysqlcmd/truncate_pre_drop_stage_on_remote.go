package mysqlcmd

import (
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/truncate"
	"fmt"

	"github.com/spf13/cobra"
)

type TruncatePreDropStageOnRemoteAct struct {
	*subcmd.BaseOptions
	BaseService truncate.PreDropStageOnRemoteComponent
}

func NewTruncatePreDropStageOnRemoteCommand() *cobra.Command {
	act := TruncatePreDropStageOnRemoteAct{
		BaseOptions: subcmd.GBaseOptions,
	}

	subCmdStr := "truncate-pre-drop-stage-on-remote"

	cmd := &cobra.Command{
		Use:   subCmdStr,
		Short: "在remote预清理备份库",
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

func (c *TruncatePreDropStageOnRemoteAct) Init() error {
	logger.Info("pre drop stage via ctl init")
	if err := c.Deserialize(&c.BaseService.Param); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}

	c.BaseService.GeneralParam = subcmd.GeneralRuntimeParam
	return nil
}

func (c *TruncatePreDropStageOnRemoteAct) Run() error {
	steps := subcmd.Steps{
		{
			FunName: "Init",
			Func:    c.BaseService.Init,
		},
		{
			FunName: "执行预清理",
			Func:    c.BaseService.Do,
		},
	}

	if err := steps.Run(); err != nil {
		logger.Error("pre drop stage on remote failed, %v", err)
		return err
	}

	logger.Info("pre drop stage on remote success")
	return nil
}
