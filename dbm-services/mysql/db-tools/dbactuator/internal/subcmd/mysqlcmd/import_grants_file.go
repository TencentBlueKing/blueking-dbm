package mysqlcmd

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"

	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/grant/import_grants_file"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"fmt"

	"github.com/spf13/cobra"
)

const ImportGrantsFileCmd = "import-grants-file"

type ImportGrantsFileAct struct {
	*subcmd.BaseOptions
	Service import_grants_file.ImportGrantsFile
}

func NewImportGrantsFileCommand() *cobra.Command {
	act := ImportGrantsFileAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   ImportGrantsFileCmd,
		Short: "clone db grants",
		Example: fmt.Sprintf(
			`dbactuator mysql %s %s %s`,
			ImportGrantsFileCmd, subcmd.CmdBaseExampleStr, subcmd.ToPrettyJson(act.Service.Example()),
		),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

func (c *ImportGrantsFileAct) Validate() error {
	return c.BaseOptions.Validate()
}

func (c *ImportGrantsFileAct) Init() error {
	if err := c.Deserialize(&c.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	c.Service.GeneralParam = subcmd.GeneralRuntimeParam
	logger.Info("extend params: %s", c.Service.Params)
	return nil
}

func (c *ImportGrantsFileAct) Run() (err error) {
	defer util.LoggerErrorStack(logger.Error, err)
	steps := subcmd.Steps{
		{
			FunName: "初始化",
			Func:    c.Service.Init,
		},
		{
			FunName: "修改原始权限",
			Func:    c.Service.ModifyPrivs,
		},
		{
			FunName: "写入最终权限文件",
			Func:    c.Service.GenerateFinalFile,
		},
		{
			FunName: "执行导入",
			Func:    c.Service.Import,
		},
	}

	if err = steps.Run(); err != nil {
		return err
	}

	logger.Info("import grants file completed")
	return nil
}
