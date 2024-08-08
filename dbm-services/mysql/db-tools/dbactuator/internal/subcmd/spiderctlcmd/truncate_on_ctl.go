package spiderctlcmd

import (
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/truncate"
	"fmt"

	"github.com/spf13/cobra"
)

type TruncateOnCtlAct struct {
	*subcmd.BaseOptions
	BaseService truncate.ViaCtlComponent
}

func NewTruncateOnCtlCommand() *cobra.Command {
	act := TruncateOnCtlAct{
		BaseOptions: subcmd.GBaseOptions,
	}

	subCmdStr := "truncate-on-ctl"

	cmd := &cobra.Command{
		Use:   subCmdStr,
		Short: "在中控执行清档",
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

func (c *TruncateOnCtlAct) Init() error {
	logger.Info("truncate on ctl init")
	if err := c.Deserialize(&c.BaseService.Param); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}

	c.BaseService.GeneralParam = subcmd.GeneralRuntimeParam
	return nil
}

func (c *TruncateOnCtlAct) Run() error {
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
			FunName: "执行清档",
			Func:    c.BaseService.Truncate,
		},
		{
			FunName: "上报删除备份库SQL",
			Func:    c.BaseService.GenerateDropStageSQL,
		},
	}

	if err := steps.Run(); err != nil {
		logger.Error("run truncate on ctl failed, %v", err)
		return err
	}

	logger.Info("truncate on ctl success")
	return nil
}
