package spiderctlcmd

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/spiderctl"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"fmt"

	"github.com/spf13/cobra"
)

// AddSlaveClusterRoutingAct TODO
//
//	AddSlaveClusterRoutingAct  添加spider slave集群时，添加相关路由信息
type AddSlaveClusterRoutingAct struct {
	*subcmd.BaseOptions
	Service spiderctl.AddSlaveClusterRoutingComp
}

// AddSlaveClusterRoutingCommand TODO
func AddSlaveClusterRoutingCommand() *cobra.Command {
	act := AddSlaveClusterRoutingAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   "add-slave-cluster-routing",
		Short: "添加spider-slave集群的相关路由信息",
		Example: fmt.Sprintf(`dbactuator spiderctl add-slave-cluster-routing %s %s`,
			subcmd.CmdBaseExampleStr, subcmd.ToPrettyJson(act.Service.Example())),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Init 初始化
func (d *AddSlaveClusterRoutingAct) Init() (err error) {
	logger.Info("InitCLusterRoutingAct Init")
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return
}

// Run 执行
func (d *AddSlaveClusterRoutingAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "初始化",
			Func:    d.Service.Init,
		},
		{
			FunName: "执行前检验",
			Func:    d.Service.PerCheck,
		},

		{
			FunName: "添加slave集群路由信息",
			Func:    d.Service.AddSlaveRouting,
		},
	}

	if err = steps.Run(); err != nil {
		return err
	}

	logger.Info("add slave clsuter routing relationship successfully")
	return nil
}
