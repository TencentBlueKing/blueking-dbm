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

// CheckBrokerEmptyAct 结构体定义了检查Kafka Broker是否为空的操作
type CheckBrokerEmptyAct struct {
	*subcmd.BaseOptions                       // 嵌入基础选项
	Service             kafka.DecomBrokerComp // Kafka服务组件
}

// CheckBrokerEmptyCommand 创建并返回一个cobra命令，用于检查Kafka Broker是否为空
func CheckBrokerEmptyCommand() *cobra.Command {
	act := CheckBrokerEmptyAct{
		BaseOptions: subcmd.GBaseOptions, // 初始化基础选项
	}
	cmd := &cobra.Command{
		Use:     "check_broker_empty",
		Short:   "检查Broker为空",
		Example: fmt.Sprintf(`dbactuator kafka check_broker_empty %s`, subcmd.CmdBaseExapmleStr),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate()) // 验证参数
			if act.RollBack {
				util.CheckErr(act.Rollback()) // 执行回滚操作
				return
			}
			util.CheckErr(act.Init()) // 初始化操作
			util.CheckErr(act.Run())  // 执行检查操作
		},
	}
	return cmd
}

// Validate 验证CheckBrokerEmptyAct结构体的参数
func (d *CheckBrokerEmptyAct) Validate() (err error) {
	return d.BaseOptions.Validate() // 调用基础选项的验证方法
}

// Init 初始化CheckBrokerEmptyAct结构体
func (d *CheckBrokerEmptyAct) Init() (err error) {
	logger.Info("CheckBrokerEmptyAct Init")
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam // 设置通用运行时参数
	return d.Service.Init()                             // 初始化服务组件
}

// Rollback 执行回滚操作
func (d *CheckBrokerEmptyAct) Rollback() (err error) {
	var r rollback.RollBackObjects
	if err = d.DeserializeAndValidate(&r); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	err = r.RollBack() // 调用回滚对象的回滚方法
	if err != nil {
		logger.Error("roll back failed %s", err.Error())
	}
	return
}

// Run 执行检查Kafka Broker是否为空的操作
func (d *CheckBrokerEmptyAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "检查Broker为空",
			Func:    d.Service.DoEmptyCheck, // 指定执行的函数
		},
	}

	if err := steps.Run(); err != nil {
		rollbackCtxb, rerr := json.Marshal(d.Service.RollBackContext) // 序列化回滚上下文
		if rerr != nil {
			logger.Error("json Marshal %s", err.Error())
			fmt.Printf("<ctx>Can't RollBack<ctx>\n")
		}
		fmt.Printf("<ctx>%s<ctx>\n", string(rollbackCtxb)) // 打印回滚上下文
		return err
	}

	logger.Info("check_broker_empty successfully") // 打印成功信息
	return nil
}
