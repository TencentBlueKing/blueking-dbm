package kafkacmd

import (
	"encoding/json"
	"fmt"

	"dbm-services/bigdata/db-tools/dbactuator/internal/subcmd"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/components/kafka"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util"
	"dbm-services/common/go-pubpkg/logger"

	"github.com/spf13/cobra"
)

// RestartBrokerAct TODO
type RestartBrokerAct struct {
	*subcmd.BaseOptions
	Service kafka.StartStopProcessComp
}

// RestartBrokerCommand TODO
func RestartBrokerCommand() *cobra.Command {
	act := RestartBrokerAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "restart_broker",
		Short:   "重启broker进程",
		Example: fmt.Sprintf(`dbactuator kafka restart_broker %s`, subcmd.CmdBaseExapmleStr),
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
func (d *RestartBrokerAct) Validate() (err error) {
	return d.BaseOptions.Validate()
}

// Init TODO
func (d *RestartBrokerAct) Init() (err error) {
	logger.Info("RestartBrokerAct Init")
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
func (d *RestartBrokerAct) Rollback() (err error) {
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
func (d *RestartBrokerAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "重启broker进程",
			Func:    d.Service.RestartBroker,
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

	logger.Info("restart_broker successfully")
	return nil
}
