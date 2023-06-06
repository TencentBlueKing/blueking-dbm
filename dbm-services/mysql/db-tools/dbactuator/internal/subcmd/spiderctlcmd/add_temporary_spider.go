// Package spiderctlcmd TODO
package spiderctlcmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/spiderctl"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// AddTmpSpiderAct  act comp param
// 用于承接act命令的参数 分为基本act参数信息和之后操作所需要的参数 内设comp承接
type AddTmpSpiderAct struct {
	*subcmd.BaseOptions
	Service spiderctl.AddTmpSpiderComp
}

// NewAddTmpSpiderCommand TODO
func NewAddTmpSpiderCommand() *cobra.Command {
	act := AddTmpSpiderAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   "add-tmp-spider",
		Short: "添加临时spider节点",
		Example: fmt.Sprintf(`dbactuator spiderctl add-tmp-spider %s %s`,
			subcmd.CmdBaseExampleStr, subcmd.ToPrettyJson(act.Service.Example()),
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
func (d *AddTmpSpiderAct) Init() (err error) {
	logger.Info("AddTmpSpiderAct Init")
	// 反序列化
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	// 初始化变量
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return nil
}

// Run TODO
func (d *AddTmpSpiderAct) Run() (err error) {
	// 是一个切片
	steps := subcmd.Steps{
		{
			FunName: "初始化",
			Func:    d.Service.Init,
		},
		{
			FunName: "中控节点配置新增spider节点信息",
			Func:    d.Service.AddTmpSpider,
		},
	}
	if err = steps.Run(); err != nil {
		return err
	}
	logger.Info("add temporary spider node successfully")
	return nil
}
