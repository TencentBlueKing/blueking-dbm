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

// GenerateKeyAct TODO
type GenerateKeyAct struct {
	*subcmd.BaseOptions
	Service hdfs.GenerateKeyService
}

// GenerateKeyCommand TODO
func GenerateKeyCommand() *cobra.Command {
	act := GenerateKeyAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "generate-key",
		Short:   "生成免密key",
		Example: fmt.Sprintf(`dbactuator hdfs generate-key %s`, subcmd.CmdBaseExampleStr),
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
func (d *GenerateKeyAct) Validate() (err error) {
	return d.BaseOptions.Validate()
}

// Init TODO
func (d *GenerateKeyAct) Init() (err error) {
	logger.Info("GenerateKeyAct Init")
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
func (d *GenerateKeyAct) Rollback() (err error) {
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
func (d *GenerateKeyAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "生成Key",
			Func:    d.Service.GenerateKey,
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

	logger.Info("Generate Key successfully")
	return nil
}
