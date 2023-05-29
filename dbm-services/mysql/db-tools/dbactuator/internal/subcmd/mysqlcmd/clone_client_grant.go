package mysqlcmd

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/grant"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"fmt"

	"github.com/spf13/cobra"
)

// CloneClineGrantAct 克隆client的权限的action
type CloneClineGrantAct struct {
	*subcmd.BaseOptions
	Service grant.CloneClentGRantComp
}

// CloneClientGrantCommand  subcommand
//
//	@return *cobra.Command
func CloneClientGrantCommand() *cobra.Command {
	act := CloneClineGrantAct{
		BaseOptions: subcmd.GBaseOptions,
		Service: grant.CloneClentGRantComp{
			Params: &grant.CloneClentGRantParam{},
		},
	}
	cmd := &cobra.Command{
		Use:     "clone-client-grant",
		Short:   "克隆客户端权限",
		Example: fmt.Sprintf(`dbactuator mysql clone-client-grant %s`, subcmd.CmdBaseExampleStr),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Init TODO
func (g *CloneClineGrantAct) Init() (err error) {
	if err = g.Deserialize(&g.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	g.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return
}

// Run TODO
func (g *CloneClineGrantAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "初始化本地db连接",
			Func:    g.Service.Init,
		},
		{
			FunName: "清理目标client残留权限",
			Func:    g.Service.ClearTargetClientPriv,
		},
		{
			FunName: "克隆client权限",
			Func:    g.Service.CloneTargetClientPriv,
		},
		{
			FunName: "回收旧client权限",
			Func:    g.Service.DropOriginClientPriv,
		},
	}

	if err := steps.Run(); err != nil {
		return err
	}

	logger.Info("clone client grant successfully")
	return nil
}
