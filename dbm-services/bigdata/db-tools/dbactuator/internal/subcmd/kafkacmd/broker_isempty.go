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

// BrokerIsEmptyAct 检查Kafka Broker是否为空
type BrokerIsEmptyAct struct {
	*subcmd.BaseOptions
	Service kafka.BrokerIsEmptyComp
}

// BrokerIsEmptyCommand 创建检查Broker是否为空的命令
func BrokerIsEmptyCommand() *cobra.Command {
	act := BrokerIsEmptyAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "broker_isempty",
		Short:   "检查Broker是否为空",
		Example: fmt.Sprintf(`dbactuator kafka broker_isempty %s`, subcmd.CmdBaseExapmleStr),
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

// Validate 验证参数
func (d *BrokerIsEmptyAct) Validate() (err error) {
	return d.BaseOptions.Validate()
}

// Init 初始化
func (d *BrokerIsEmptyAct) Init() (err error) {
	logger.Info("BrokerIsEmptyAct Init")
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return d.Service.Init()
}

// Rollback 执行回滚
func (d *BrokerIsEmptyAct) Rollback() (err error) {
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

// Run 执行检查
func (d *BrokerIsEmptyAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "检查Broker是否为空",
			Func:    d.Service.BrokerIsEmpty,
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

	// 输出检查结果
	if d.Service.CheckResult != nil {
		resultJSON, _ := json.MarshalIndent(d.Service.CheckResult, "", "  ")
		fmt.Printf("\n=== 检查结果 ===\n%s\n=================\n", string(resultJSON))
	}

	logger.Info("broker_isempty successfully")
	return nil
}
