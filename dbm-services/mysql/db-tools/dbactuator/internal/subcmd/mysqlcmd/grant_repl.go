package mysqlcmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/grant"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// GrantReplAct 增加repl账户action
type GrantReplAct struct {
	*subcmd.BaseOptions
	Payload grant.GrantReplComp
}

// NewGrantReplCommand godoc
//
// @Summary      建立复制账号
// @Description  在目标机器新建 repl 账号
// @Tags         mysql
// @Accept       json
// @Param        body body      grant.GrantReplComp  true  "short description"
// @Router       /mysql/grant-repl [post]
func NewGrantReplCommand() *cobra.Command {
	act := GrantReplAct{
		BaseOptions: subcmd.GBaseOptions,
		Payload: grant.GrantReplComp{
			Params: &grant.GrantReplParam{},
		},
	}
	cmd := &cobra.Command{
		Use:   "grant-repl",
		Short: "新增repl账户",
		Example: fmt.Sprintf(
			`dbactuator mysql grant-repl %s %s`,
			subcmd.CmdBaseExampleStr, subcmd.ToPrettyJson(act.Payload.Example()),
		),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Init TODO
func (g *GrantReplAct) Init() (err error) {
	if err = g.Deserialize(&g.Payload.Params); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	g.Payload.GeneralParam = subcmd.GeneralRuntimeParam
	return
}

// Run TODO
func (g *GrantReplAct) Run() (err error) {
	defer util.LoggerErrorStack(logger.Error, err)
	steps := subcmd.Steps{
		{
			FunName: "初始化本地db连接",
			Func:    g.Payload.Init,
		},
		{
			FunName: "增加repl账户",
			Func:    g.Payload.GrantRepl,
		},
		{
			FunName: "获取同步位点信息",
			Func: func() error {
				postion, err := g.Payload.GetBinPosition()
				if err != nil {
					return err
				}
				g.OutputCtx(postion)
				return nil
			},
		},
	}

	if err := steps.Run(); err != nil {
		return err
	}

	logger.Info("grant repl successfully")
	return nil
}
