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

// WriteKeyAct TODO
type WriteKeyAct struct {
	*subcmd.BaseOptions
	Service hdfs.WriteKeyService
}

// WriteKeyCommand TODO
func WriteKeyCommand() *cobra.Command {
	act := WriteKeyAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "write-key",
		Short:   "写入key",
		Example: fmt.Sprintf(`dbactuator hdfs write-key %s`, subcmd.CmdBaseExampleStr),
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
func (d *WriteKeyAct) Validate() (err error) {
	return d.BaseOptions.Validate()
}

// Init TODO
func (d *WriteKeyAct) Init() (err error) {
	logger.Info("WriteKeyAct Init")
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
func (d *WriteKeyAct) Rollback() (err error) {
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
func (d *WriteKeyAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "写入Key",
			Func:    d.Service.WriteKey,
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

	logger.Info("Write Key successfully")
	return nil
}
