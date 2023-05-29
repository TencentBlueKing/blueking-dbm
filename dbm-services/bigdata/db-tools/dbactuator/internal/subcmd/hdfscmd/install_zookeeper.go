package hdfscmd

import (
	"dbm-services/bigdata/db-tools/dbactuator/internal/subcmd"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/components/hdfs"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util"
	"dbm-services/common/go-pubpkg/logger"
	"encoding/json"
	"fmt"

	"github.com/spf13/cobra"
)

// InstallZookeeperAct TODO
type InstallZookeeperAct struct {
	*subcmd.BaseOptions
	Service hdfs.InstallZookeeperService
}

// InstallZookeeperCommand TODO
func InstallZookeeperCommand() *cobra.Command {
	act := InstallZookeeperAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "install-zookeeper",
		Short:   "hdfs 安装zookeeper",
		Example: fmt.Sprintf(`dbactuator hdfs zookeeper %s`, subcmd.CmdBaseExapmleStr),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate())
			if act.RollBack {
				util.CheckErr(act.Rollback())
				return
			}
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Validate TODO
func (d *InstallZookeeperAct) Validate() (err error) {
	return d.BaseOptions.Validate()
}

// Init TODO
func (d *InstallZookeeperAct) Init() (err error) {
	logger.Info("InstallZookeeperAct Init")
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	d.Service.InstallParams = hdfs.InitDefaultInstallParam()
	return nil
}

// Rollback TODO
// @receiver d
//
//	@return err
func (d *InstallZookeeperAct) Rollback() (err error) {
	var r rollback.RollBackObjects
	if err = d.DeserializeAndValidate(&r); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	err = r.RollBack()
	if err != nil {
		logger.Error("roll back failed %s", err.Error())
	}
	return
}

// Run TODO
func (d *InstallZookeeperAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "渲染zookeeper 配置",
			Func:    d.Service.RenderZookeeperConfig,
		},

		{
			FunName: "安装ZooKeeper",
			Func:    d.Service.InstallZookeeper,
		},
	}

	if err := steps.Run(); err != nil {
		rollbackCtxb, rerr := json.Marshal(d.Service.RollBackContext)
		if rerr != nil {
			logger.Error("json Marshal %s", err.Error())
			fmt.Printf("<ctx>Can't RollBack<ctx>\n")
		}
		fmt.Printf("<ctx>%s<ctx>\n", string(rollbackCtxb))
		return err
	}

	logger.Info("init successfully")
	return nil
}
