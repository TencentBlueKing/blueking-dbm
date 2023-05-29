package kafkacmd

import (
	"dbm-services/bigdata/db-tools/dbactuator/internal/subcmd"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/components/kafka"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util"
	"dbm-services/common/go-pubpkg/logger"
	"encoding/json"
	"fmt"

	"github.com/spf13/cobra"
)

// CheckReassignmentAct TODO
type CheckReassignmentAct struct {
	*subcmd.BaseOptions
	Service kafka.DecomBrokerComp
}

// CheckReassignmentCommand TODO
func CheckReassignmentCommand() *cobra.Command {
	act := CheckReassignmentAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "check_reassign",
		Short:   "检查搬迁进度",
		Example: fmt.Sprintf(`dbactuator kafka check_reassign %s`, subcmd.CmdBaseExapmleStr),
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
func (d *CheckReassignmentAct) Validate() (err error) {
	return d.BaseOptions.Validate()
}

// Init TODO
func (d *CheckReassignmentAct) Init() (err error) {
	logger.Info("CheckReassignmentAct Init")
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return d.Service.Init()
}

// Rollback TODO
//
//	@receiver d
//	@return err
func (d *CheckReassignmentAct) Rollback() (err error) {
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
func (d *CheckReassignmentAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "Broker缩容",
			Func:    d.Service.DoPartitionCheck,
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

	logger.Info("check_reassign successfully")
	return nil
}
