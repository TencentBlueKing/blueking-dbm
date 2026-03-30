package clone_grants_from_file

import (
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/clone_grants_from_file/spider"
	"fmt"

	"github.com/spf13/cobra"
)

type CloneGrantsVerifyGrantAct struct {
	*subcmd.BaseOptions
	Service spider.ImportPrivFileComponent
}

const CloneGrantsVerifyGrantCmd = `clone-grants-verify-grant`

func NewCloneGrantsVerifyGrantCommand() *cobra.Command {
	act := &CloneGrantsVerifyGrantAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   CloneGrantsVerifyGrantCmd,
		Short: "verify grant privileges on target db after import",
		Example: fmt.Sprintf(
			`dbactuator spider %s %s %s`,
			CloneGrantsVerifyGrantCmd,
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

func (c *CloneGrantsVerifyGrantAct) Validate() error {
	return c.BaseOptions.Validate()
}

func (c *CloneGrantsVerifyGrantAct) Init() error {
	if err := c.Deserialize(&c.Service.Param); err != nil {
		logger.Error("DeserializerAndValidate err %s", err.Error())
		return err
	}
	c.Service.GeneralParam = subcmd.GeneralRuntimeParam
	logger.Info("extend params: %s", c.Service.Param)
	return nil
}

func (c *CloneGrantsVerifyGrantAct) Run() error {
	s := subcmd.Steps{
		{
			FunName: "初始化",
			Func:    c.Service.Init,
		},
		{
			FunName: "验证权限",
			Func:    c.Service.VerifyGrantPriv,
		},
	}
	if err := s.Run(); err != nil {
		logger.Error("Run err %s", err.Error())
		return err
	}

	logger.Info("验证权限完成")
	return nil
}
