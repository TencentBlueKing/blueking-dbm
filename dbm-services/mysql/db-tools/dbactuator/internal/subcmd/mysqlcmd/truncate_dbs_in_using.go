package mysqlcmd

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/truncate"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"fmt"

	"github.com/spf13/cobra"
)

type TruncateDBsInUsingAct struct {
	*subcmd.BaseOptions
	BaseService truncate.IsDBsInUsingComponent
}

func NewTruncateDBsInUsingCommand() *cobra.Command {
	act := TruncateDBsInUsingAct{
		BaseOptions: subcmd.GBaseOptions,
	}

	subCmdStr := "truncate-dbs-in-using"

	cmd := &cobra.Command{
		Use:   subCmdStr,
		Short: "检查库表是否在用",
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

func (c *TruncateDBsInUsingAct) Init() error {
	logger.Info("create check dbs in using init")
	if err := c.Deserialize(&c.BaseService.Param); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}

	c.BaseService.GeneralParam = subcmd.GeneralRuntimeParam
	return nil
}

func (c *TruncateDBsInUsingAct) Run() error {
	steps := subcmd.Steps{
		{
			FunName: "Init",
			Func:    c.BaseService.Init,
		},
		{
			FunName: "检查库表是否在用",
			Func:    c.BaseService.IsDBsInUsing,
		},
	}

	if err := steps.Run(); err != nil {
		logger.Error("run check dbs in using failed, %v", err)
		return err
	}

	logger.Info("check dbs in using success")
	return nil
}
