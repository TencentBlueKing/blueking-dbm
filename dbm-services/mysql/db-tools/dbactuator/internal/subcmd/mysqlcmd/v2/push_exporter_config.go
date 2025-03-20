package mysqlcmd

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/peripheraltools/v2/exporter"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"fmt"

	"github.com/spf13/cobra"
)

type PushExporterCnfAct struct {
	*subcmd.BaseOptions
	Service exporter.PushCnfComp
}

const PushExporterCnf = `push-exporter-cnf`

func NewPushExporterCnfCommand() *cobra.Command {
	act := PushExporterCnfAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   PushExporterCnf,
		Short: "push exporter cnf",
		Example: fmt.Sprintf(
			`dbactuator mysql %s %s %s`,
			PushExporterCnf,
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

func (c *PushExporterCnfAct) Validate() (err error) {
	return c.BaseOptions.Validate()
}

func (c *PushExporterCnfAct) Init() (err error) {
	if err = c.Deserialize(&c.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	c.Service.GeneralParam = subcmd.GeneralRuntimeParam
	logger.Info("extend params: %s", c.Service.Params)
	return nil
}

func (c *PushExporterCnfAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "推送配置",
			Func:    c.Service.Run,
		},
	}
	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("推送 exporter 配置完成")
	return nil
}
