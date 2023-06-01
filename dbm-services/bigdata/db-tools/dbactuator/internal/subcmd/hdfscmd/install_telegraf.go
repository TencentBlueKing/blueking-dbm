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

// InstallTelegrafAct TODO
type InstallTelegrafAct struct {
	*subcmd.BaseOptions
	Service hdfs.InstallHdfsService
}

// InstallTelegrafCommand TODO
func InstallTelegrafCommand() *cobra.Command {
	act := InstallTelegrafAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "install-telegraf",
		Short:   "hdfs 安装telegraf",
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
func (d *InstallTelegrafAct) Validate() (err error) {
	return d.BaseOptions.Validate()
}

// Init TODO
func (d *InstallTelegrafAct) Init() (err error) {
	logger.Info("InstallTelegrafAct Init")
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
func (d *InstallTelegrafAct) Rollback() (err error) {
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
func (d *InstallTelegrafAct) Run() (err error) {
	steps := subcmd.Steps{

		// {
		//	FunName: "预检查",
		//	Func:    d.Service.PreCheck,
		// },
		{
			FunName: "安装HaProxy",
			Func:    d.Service.InstallHaProxy,
		},
		{
			FunName: "渲染HaProxy配置",
			Func:    d.Service.RenderHaProxyConfig,
		},
		{
			FunName: "启动HaProxy",
			Func:    d.Service.StartHaProxy,
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
