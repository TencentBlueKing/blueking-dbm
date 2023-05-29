package spidercmd

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/spider"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"fmt"

	"github.com/spf13/cobra"
)

// RestartSpiderAct TODO
type RestartSpiderAct struct {
	*subcmd.BaseOptions
	Service spider.RestartSpiderComp
}

// NewRestratSpiderCommand TODO
func NewRestratSpiderCommand() *cobra.Command {
	act := RestartSpiderAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   "restart-spider",
		Short: "重启spider",
		Example: fmt.Sprintf(
			`dbactuator spider restart %s %s `,
			subcmd.CmdBaseExampleStr,
			subcmd.ToPrettyJson(act.Service.Example()),
		),
		Run: func(cmd *cobra.Command, args []string) {
			// Validate是BaseOptions绑定的方法
			util.CheckErr(act.Validate())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Init TODO
func (d *RestartSpiderAct) Init() (err error) {
	if err := d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return
}

// Run TODO
func (d *RestartSpiderAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "初始化",
			Func:    d.Service.Init,
		},
		{
			FunName: "预检查",
			Func:    d.Service.PreCheck,
		},
		{
			FunName: "重启spider",
			Func:    d.Service.RestartSpider,
		},
	}
	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("restart spider successfully")
	return nil
}
