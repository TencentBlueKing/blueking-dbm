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

// ReduceBrokerAct TODO
type ReduceBrokerAct struct {
	*subcmd.BaseOptions
	Service kafka.DecomBrokerComp
}

// ReduceBrokerCommand TODO
func ReduceBrokerCommand() *cobra.Command {
	act := ReduceBrokerAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "reduce_broker",
		Short:   "broker缩容",
		Example: fmt.Sprintf(`dbactuator kafka reduce_broker %s`, subcmd.CmdBaseExapmleStr),
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
func (d *ReduceBrokerAct) Validate() (err error) {
	return d.BaseOptions.Validate()
}

// Init TODO
func (d *ReduceBrokerAct) Init() (err error) {
	logger.Info("ReduceBrokerAct Init")
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
func (d *ReduceBrokerAct) Rollback() (err error) {
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
func (d *ReduceBrokerAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "Broker缩容",
			Func:    d.Service.DoDecomBrokers,
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

	logger.Info("reduce_broker successfully")
	return nil
}
