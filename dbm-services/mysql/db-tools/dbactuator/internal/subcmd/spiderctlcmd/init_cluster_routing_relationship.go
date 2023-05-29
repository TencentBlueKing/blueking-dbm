package spiderctlcmd

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/spiderctl"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"fmt"

	"github.com/spf13/cobra"
)

// InitCLusterRoutingAct  初始化tendb cluster 集群的路由关系
type InitCLusterRoutingAct struct {
	*subcmd.BaseOptions
	Service spiderctl.InitClusterRoutingComp
}

// NewInitCLusterRoutingCommand TODO
//
// @Summary      初始化tendb cluster 集群的路由关系
// @Description  初始化tendb cluster 集群的路由关系说明
// @Tags         spiderctl
// @Accept       json
// @Param        body body      spiderctl.InitClusterRoutingComp  true  "short description"
// @Router /mysql/init-cluster-routing [post]
func NewInitCLusterRoutingCommand() *cobra.Command {
	act := InitCLusterRoutingAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   "init-cluster-routing",
		Short: "初始化tendb cluster集群节点关系",
		Example: fmt.Sprintf(
			`dbactuator spiderctl init-cluster-routing %s %s`,
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

// Init 初始化
func (d *InitCLusterRoutingAct) Init() (err error) {
	logger.Info("InitCLusterRoutingAct Init")
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return
}

// Run 执行
func (d *InitCLusterRoutingAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "初始化",
			Func:    d.Service.Init,
		},
		{
			FunName: "配置mysql.servers表",
			Func:    d.Service.InitMySQLServers,
		},
	}

	if err = steps.Run(); err != nil {
		return err
	}

	logger.Info("init tendb cluster routing relationship successfully")
	return nil
}
