package spiderctlcmd

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/truncate"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"fmt"

	"github.com/spf13/cobra"
)

type CreateStageViaCtlAct struct {
	*subcmd.BaseOptions
	BaseService truncate.ViaCtlComponent
}

func NewCreateStageViaCtlCommand() *cobra.Command {
	act := CreateStageViaCtlAct{
		BaseOptions: subcmd.GBaseOptions,
	}

	subCmdStr := "create-stage-via-ctl"

	cmd := &cobra.Command{
		Use:   subCmdStr,
		Short: "中控创建清档备份库表",
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

func (c *CreateStageViaCtlAct) Init() error {
	logger.Info("create stage via ctl init")
	if err := c.Deserialize(&c.BaseService.Param); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}

	c.BaseService.GeneralParam = subcmd.GeneralRuntimeParam
	return nil
}

func (c *CreateStageViaCtlAct) Run() error {
	steps := subcmd.Steps{
		{
			FunName: "Init",
			Func:    c.BaseService.Init,
		},
		{
			FunName: "获取清档目标",
			Func:    c.BaseService.GetTarget,
		},
		{
			FunName: "创建备份库",
			Func:    c.BaseService.CreateStageDBs,
		},
		{
			FunName: "创建备份库表",
			Func:    c.BaseService.CreateStageTables,
		},
	}

	if err := steps.Run(); err != nil {
		logger.Error("run create stage via ctl failed, %v", err)
		return err
	}

	logger.Info("create stage via ctl success")
	return nil
}
