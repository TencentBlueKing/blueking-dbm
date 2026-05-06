package clone_grants_from_file

import (
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/clone_grants_from_file/spider"
	"fmt"

	"github.com/spf13/cobra"
)

type CloneGrantsParsePrivFileAct struct {
	*subcmd.BaseOptions
	Service spider.ImportPrivFileComponent
}

const CloneGrantsParsePrivFileCmd = `clone-grants-parse-file`

func NewCloneGrantsParsePrivFileCommand() *cobra.Command {
	act := &CloneGrantsParsePrivFileAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   CloneGrantsParsePrivFileCmd,
		Short: "parse privilege file into create user and grant files",
		Example: fmt.Sprintf(
			`dbactuator spider %s %s %s`,
			CloneGrantsParsePrivFileCmd,
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

func (c *CloneGrantsParsePrivFileAct) Validate() error {
	return c.BaseOptions.Validate()
}

func (c *CloneGrantsParsePrivFileAct) Init() error {
	if err := c.Deserialize(&c.Service.Param); err != nil {
		logger.Error("DeserializerAndValidate err %s", err.Error())
		return err
	}
	c.Service.GeneralParam = subcmd.GeneralRuntimeParam
	logger.Info("extend params: %s", c.Service.Param)
	return nil
}

func (c *CloneGrantsParsePrivFileAct) Run() error {
	s := subcmd.Steps{
		{
			FunName: "初始化",
			Func:    c.Service.Init,
		},
		{
			FunName: "处理权限文件",
			Func:    c.Service.ParseFile,
		},
	}
	if err := s.Run(); err != nil {
		logger.Error("Run err %s", err.Error())
		return err
	}

	logger.Info("处理权限文件完成")
	return nil
}
