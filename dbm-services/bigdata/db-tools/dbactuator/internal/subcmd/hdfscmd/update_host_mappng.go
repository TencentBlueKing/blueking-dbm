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

// UpdateHostMappingAct TODO
type UpdateHostMappingAct struct {
	*subcmd.BaseOptions
	Service hdfs.UpdateHostMappingService
}

// UpdateHostMappingCommand TODO
func UpdateHostMappingCommand() *cobra.Command {
	act := UpdateHostMappingAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "update-hosts",
		Short:   "hdfs 更新主机映射",
		Example: fmt.Sprintf(`dbactuator hdfs update-hosts %s`, subcmd.CmdBaseExapmleStr),
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
func (d *UpdateHostMappingAct) Validate() (err error) {
	return d.BaseOptions.Validate()
}

// Init TODO
func (d *UpdateHostMappingAct) Init() (err error) {
	logger.Info("UpdateHostMappingAct Init")
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return nil
}

// Rollback TODO
// @receiver d
//
//	@return err
func (d *UpdateHostMappingAct) Rollback() (err error) {
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
func (d *UpdateHostMappingAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "更新主机映射",
			Func:    d.Service.UpdateHostMapping,
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

	logger.Info("update host mapping successfully")
	return nil
}
