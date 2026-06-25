package kafkacmd

import (
	"fmt"

	"dbm-services/bigdata/db-tools/dbactuator/internal/subcmd"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/components/kafka"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util"
	"dbm-services/common/go-pubpkg/logger"

	"github.com/spf13/cobra"
)

// CheckBrokerConfigsAct 检查broker配置项子命令的执行结构体
type CheckBrokerConfigsAct struct {
	*subcmd.BaseOptions
	Service kafka.CheckBrokerConfigsComp
}

// CheckBrokerConfigsCommand 检查broker的server.properties中是否存在指定配置项，输出缺失的配置列表
func CheckBrokerConfigsCommand() *cobra.Command {
	act := CheckBrokerConfigsAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "check_broker_configs",
		Short:   "检查broker配置项是否存在",
		Example: fmt.Sprintf(`dbactuator kafka check_broker_configs %s`, subcmd.CmdBaseExapmleStr),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Validate 校验基础参数
func (d *CheckBrokerConfigsAct) Validate() (err error) {
	return d.BaseOptions.Validate()
}

// Init 反序列化参数并初始化组件
func (d *CheckBrokerConfigsAct) Init() (err error) {
	logger.Info("CheckBrokerConfigsAct Init")
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return d.Service.Init()
}

// Run 执行broker配置项检查，结果通过<ctx>输出
func (d *CheckBrokerConfigsAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "检查broker配置项",
			Func:    d.Service.CheckBrokerConfigs,
		},
	}

	if err := steps.Run(); err != nil {
		logger.Error("check_broker_configs failed: %v", err)
		return err
	}

	logger.Info("check_broker_configs successfully")
	return nil
}
