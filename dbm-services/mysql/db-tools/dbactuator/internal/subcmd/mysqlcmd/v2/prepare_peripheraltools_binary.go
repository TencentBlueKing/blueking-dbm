package mysqlcmd

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/peripheraltools/v2"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"fmt"

	"github.com/spf13/cobra"
)

type PreparePeripheralToolsBinaryAct struct {
	*subcmd.BaseOptions
	Service peripheraltools.PrepareBinary
}

const PreparePeripheralToolsBinary = `prepare-peripheraltools-binary`

func NewPreparePeripheralToolsBinaryCommand() *cobra.Command {
	act := PreparePeripheralToolsBinaryAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   PreparePeripheralToolsBinary,
		Short: "部署周边工具二进制",
		Example: fmt.Sprintf(
			`dbactuator mysql %s %s %s`,
			PreparePeripheralToolsBinary,
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

func (c *PreparePeripheralToolsBinaryAct) Validate() (err error) {
	return c.BaseOptions.Validate()
}

func (c *PreparePeripheralToolsBinaryAct) Init() (err error) {
	if err = c.Deserialize(&c.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	c.Service.GeneralParam = subcmd.GeneralRuntimeParam
	logger.Info("extend params: %s", c.Service.Params)
	return nil
}

func (c *PreparePeripheralToolsBinaryAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "准备周边工具二进制",
			Func:    c.Service.Run,
		},
	}
	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("准备周边工具二进制完成")
	return nil
}
