package clone_grants_from_file

import (
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/clone_grants_from_file/mysql"
	"fmt"

	"github.com/spf13/cobra"
)

type CloneGrantsImportGrantAct struct {
	*subcmd.BaseOptions
	Service mysql.ImportPrivFileComponent
}

const CloneGrantsImportGrantCmd = `clone-grants-import-grant`

func NewCloneGrantsImportGrantCommand() *cobra.Command {
	act := &CloneGrantsImportGrantAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   CloneGrantsImportGrantCmd,
		Short: "import grant privilege file to target db",
		Example: fmt.Sprintf(
			`dbactuator mysql %s %s %s`,
			CloneGrantsImportGrantCmd,
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

func (c *CloneGrantsImportGrantAct) Validate() error {
	return c.BaseOptions.Validate()
}

func (c *CloneGrantsImportGrantAct) Init() error {
	if err := c.Deserialize(&c.Service.Param); err != nil {
		logger.Error("DeserializerAndValidate err %s", err.Error())
		return err
	}
	c.Service.GeneralParam = subcmd.GeneralRuntimeParam
	logger.Info("extend params: %s", c.Service.Param)
	return nil
}

func (c *CloneGrantsImportGrantAct) Run() error {
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
			FunName: "导入权限文件",
			Func:    c.Service.ImportGrantPrivFile,
		},
	}
	if err := s.Run(); err != nil {
		logger.Error("Run err %s", err.Error())
		return err
	}

	logger.Info("导入权限文件完成")
	return nil
}
