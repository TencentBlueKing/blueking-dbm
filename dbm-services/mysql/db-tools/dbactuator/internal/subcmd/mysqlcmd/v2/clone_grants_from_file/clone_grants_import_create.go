package clone_grants_from_file

import (
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/clone_grants_from_file/mysql"
	"fmt"

	"github.com/spf13/cobra"
)

type CloneGrantsImportCreateAct struct {
	*subcmd.BaseOptions
	Service mysql.ImportPrivFileComponent
}

const CloneGrantsImportCreateCmd = `clone-grants-import-create`

func NewCloneGrantsImportCreateCommand() *cobra.Command {
	act := &CloneGrantsImportCreateAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   CloneGrantsImportCreateCmd,
		Short: "import create user file to target db",
		Example: fmt.Sprintf(
			`dbactuator mysql %s %s %s`,
			CloneGrantsImportCreateCmd,
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

func (c *CloneGrantsImportCreateAct) Validate() error {
	return c.BaseOptions.Validate()
}

func (c *CloneGrantsImportCreateAct) Init() error {
	if err := c.Deserialize(&c.Service.Param); err != nil {
		logger.Error("DeserializerAndValidate err %s", err.Error())
		return err
	}
	c.Service.GeneralParam = subcmd.GeneralRuntimeParam
	logger.Info("extend params: %s", c.Service.Param)
	return nil
}

func (c *CloneGrantsImportCreateAct) Run() error {
	s := subcmd.Steps{
		{
			FunName: "初始化",
			Func:    c.Service.Init,
		},
		//{
		//	FunName: "处理权限文件",
		//	Func:    c.Service.ParseFile,
		//},
		{
			FunName: "导入账号文件",
			Func:    c.Service.ImportCreateUserFile,
		},
	}
	if err := s.Run(); err != nil {
		logger.Error("Run err %s", err.Error())
		return err
	}

	logger.Info("导入账号文件完成")
	return nil
}
