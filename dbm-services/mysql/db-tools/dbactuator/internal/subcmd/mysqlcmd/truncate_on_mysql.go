package mysqlcmd

import (
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/truncate"
	"fmt"

	"github.com/spf13/cobra"
)

type TruncateOnMySQLAct struct {
	*subcmd.BaseOptions
	BaseService truncate.OnMySQLComponent
}

func NewTruncateOnMySQLCommand() *cobra.Command {
	act := TruncateOnMySQLAct{
		BaseOptions: subcmd.GBaseOptions,
	}

	subCmdStr := "truncate-on-mysql"

	cmd := &cobra.Command{
		Use:   subCmdStr,
		Short: "在MySQL执行清档",
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

func (c *TruncateOnMySQLAct) Init() error {
	logger.Info("create stage on mysql init")
	if err := c.Deserialize(&c.BaseService.Param); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}

	c.BaseService.GeneralParam = subcmd.GeneralRuntimeParam
	return nil
}

func (c *TruncateOnMySQLAct) Run() error {
	steps := subcmd.Steps{
		{
			FunName: "初始化",
			Func: func() error {
				return c.BaseService.Init(c.Uid)
			},
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
		logger.Error("truncate on mysql failed, %v", err)
		return err
	}

	logger.Info("truncate on mysql success")
	return nil
}
