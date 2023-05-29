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

// StopProcessAct TODO
type StopProcessAct struct {
	*subcmd.BaseOptions
	Service hdfs.NodeOperationService
}

// StopProcessCommand TODO
func StopProcessCommand() *cobra.Command {
	act := StopProcessAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "stop-process",
		Short:   "停止所有进程",
		Example: fmt.Sprintf(`dbactuator hdfs stop-process %s`, subcmd.CmdBaseExapmleStr),
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
func (d *StopProcessAct) Validate() (err error) {
	return d.BaseOptions.Validate()
}

// Init TODO
func (d *StopProcessAct) Init() (err error) {
	logger.Info("StopProcessAct Init")
	// 获取db-flow 传进来的extend 参数
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam

	return nil
}

// Rollback TODO
//
//	@receiver d
//	@return err
func (d *StopProcessAct) Rollback() (err error) {
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
func (d *StopProcessAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "停止进程",
			Func:    d.Service.StopAllProcess,
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

	logger.Info("stop-process successfully")
	return nil
}
