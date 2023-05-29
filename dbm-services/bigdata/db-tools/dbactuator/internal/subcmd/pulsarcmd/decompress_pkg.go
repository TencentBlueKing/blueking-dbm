package pulsarcmd

import (
	"dbm-services/bigdata/db-tools/dbactuator/internal/subcmd"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/components/pulsar"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util"
	"dbm-services/common/go-pubpkg/logger"
	"encoding/json"
	"fmt"

	"github.com/spf13/cobra"
)

// DecompressPulsarPkgAct TODO
type DecompressPulsarPkgAct struct {
	*subcmd.BaseOptions
	Service pulsar.InstallPulsarComp
}

// DecompressPulsarPkgCommand TODO
func DecompressPulsarPkgCommand() *cobra.Command {
	act := DecompressPulsarPkgAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "decompress_pkg",
		Short:   "解压缩",
		Example: fmt.Sprintf(`dbactuator pulsar decompress_pkg %s`, subcmd.CmdBaseExapmleStr),
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
func (d *DecompressPulsarPkgAct) Validate() (err error) {
	return d.BaseOptions.Validate()
}

// Init TODO
func (d *DecompressPulsarPkgAct) Init() (err error) {
	logger.Info("DecompressPulsarPkgAct Init")
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return d.Service.InitDefaultParam()
}

// Rollback TODO
//
//	@receiver d
//	@return err
func (d *DecompressPulsarPkgAct) Rollback() (err error) {
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
func (d *DecompressPulsarPkgAct) Run() (err error) {
	steps := subcmd.Steps{
		/* Todo
		{
			FunName: "预检查",
			Func:    d.Service.PreCheck,
		},
		*/
		{
			FunName: "解压缩",
			Func:    d.Service.DecompressPulsarPkg,
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

	logger.Info("decompress_pkg successfully")
	return nil
}
