package clone_grants_from_file

import (
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/clone_grants_from_file/spider"
	"fmt"

	"github.com/spf13/cobra"
)

type CloneGrantsPrecheckCreateAct struct {
	*subcmd.BaseOptions
	Service spider.ImportPrivFileComponent
}

const CloneGrantsPrecheckCreateCmd = `clone-grants-precheck-create`

func NewCloneGrantsPrecheckCreateCommand() *cobra.Command {
	act := &CloneGrantsPrecheckCreateAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   CloneGrantsPrecheckCreateCmd,
		Short: "pre-check create user statements against target db",
		Example: fmt.Sprintf(
			`dbactuator spider %s %s %s`,
			CloneGrantsPrecheckCreateCmd,
			subcmd.CmdBaseExampleStr,
			subcmd.ToPrettyJson(act.Service.Example()),
		),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

func (c *CloneGrantsPrecheckCreateAct) Validate() error {
	return c.BaseOptions.Validate()
}

func (c *CloneGrantsPrecheckCreateAct) Init() error {
	if err := c.Deserialize(&c.Service.Param); err != nil {
		logger.Error("DeserializerAndValidate err %s", err.Error())
		return err
	}
	c.Service.GeneralParam = subcmd.GeneralRuntimeParam
	logger.Info("extend params: %s", c.Service.Param)
	return nil
}

func (c *CloneGrantsPrecheckCreateAct) Run() error {
	s := subcmd.Steps{
		{
			FunName: "初始化",
			Func:    c.Service.Init,
		},
		{
			FunName: "预检查账号",
			Func:    c.Service.PreCheckCreateUser,
		},
	}
	if err := s.Run(); err != nil {
		logger.Error("Run err %s", err.Error())
		return err
	}

	logger.Info("预检查账号完成")
	return nil
}
