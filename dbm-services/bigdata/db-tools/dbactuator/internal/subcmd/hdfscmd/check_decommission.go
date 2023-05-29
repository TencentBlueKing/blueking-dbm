package hdfscmd

import (
	"encoding/json"
	"fmt"

	"dbm-services/bigdata/db-tools/dbactuator/internal/subcmd"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/components/hdfs"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util"
	"dbm-services/common/go-pubpkg/logger"

	"github.com/spf13/cobra"
)

// CheckDecommissionAct TODO
type CheckDecommissionAct struct {
	*subcmd.BaseOptions
	Service hdfs.CheckDecommissionService
}

// CheckDecommissionCommand TODO
func CheckDecommissionCommand() *cobra.Command {
	act := CheckDecommissionAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "check-decommission",
		Short:   "检查退役节点",
		Example: fmt.Sprintf(`dbactuator hdfs check-decommission %s`, subcmd.CmdBaseExampleStr),
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
func (d *CheckDecommissionAct) Validate() (err error) {
	return d.BaseOptions.Validate()
}

// Init TODO
func (d *CheckDecommissionAct) Init() (err error) {
	logger.Info("CheckDecommissionAct Init")
	// 获取db-flow 传进来的extend 参数
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	// 获取HDFS集群 安装配置，e.g. 安装目录，安装JDK版本，安装haproxy文件等
	d.Service.InstallParams = hdfs.InitDefaultInstallParam()
	return nil
}

// Rollback TODO
//
//	@receiver d
//	@return err
func (d *CheckDecommissionAct) Rollback() (err error) {
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
func (d *CheckDecommissionAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "检查DN节点是否退役",
			Func:    d.Service.CheckDatanodeDecommission,
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

	logger.Info("Check Decommission successfully")
	return nil
}
