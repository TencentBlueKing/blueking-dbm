package influxdbcmd

import (
	"encoding/json"
	"fmt"

	"dbm-services/bigdata/db-tools/dbactuator/internal/subcmd"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/components/influxdb"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util"
	"dbm-services/common/go-pubpkg/logger"

	"github.com/spf13/cobra"
)

// DecompressInfluxdbPkgAct TODO
type DecompressInfluxdbPkgAct struct {
	*subcmd.BaseOptions
	Service influxdb.InstallInfluxdbComp
}

// DecompressInfluxdbPkgCommand TODO
func DecompressInfluxdbPkgCommand() *cobra.Command {
	act := DecompressInfluxdbPkgAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "decompress_pkg",
		Short:   "解压缩",
		Example: fmt.Sprintf(`dbactuator influxdb decompress_pkg %s`, subcmd.CmdBaseExapmleStr),
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
func (d *DecompressInfluxdbPkgAct) Validate() (err error) {
	return d.BaseOptions.Validate()
}

// Init TODO
func (d *DecompressInfluxdbPkgAct) Init() (err error) {
	logger.Info("DecompressInfluxdbPkgAct Init")
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
func (d *DecompressInfluxdbPkgAct) Rollback() (err error) {
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
func (d *DecompressInfluxdbPkgAct) Run() (err error) {
	steps := subcmd.Steps{
		/* Todo
		{
			FunName: "预检查",
			Func:    d.Service.PreCheck,
		},
		*/
		{
			FunName: "解压缩",
			Func:    d.Service.DecompressInfluxdbPkg,
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
