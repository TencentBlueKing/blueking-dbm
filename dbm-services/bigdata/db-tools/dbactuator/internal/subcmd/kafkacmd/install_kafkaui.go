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

// Package kafkacmd 提供与 Kafka 相关的命令行子命令实现。
// 本文件定义了安装 Kafka UI 的命令及其执行流程。

// InstallKafkaUIAct 表示“安装 Kafka UI”动作的封装对象，
// 包含通用基础参数与具体的 Kafka 组件执行实现。
type InstallKafkaUIAct struct {
	// BaseOptions 为通用基础参数（由框架注入/初始化），
	// 提供入参反序列化、校验、以及回滚标记等能力。
	*subcmd.BaseOptions

	// Service 为安装 Kafka UI 的具体组件实现，
	// 负责参数校验、默认值初始化及实际安装过程。
	Service kafka.InstallKafkaComp
}

// InstallKafkaUICommand 构造“install_kafkaui”子命令。
// 该命令的执行流程：
// 1. Validate 校验基础参数
// 2. 若指定 --rollback，则只执行回滚逻辑
// 3. Init 初始化业务参数（反序列化、默认值注入）
// 4. Run 执行安装步骤
func InstallKafkaUICommand() *cobra.Command {
	act := InstallKafkaUIAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "install_kafkaui",
		Short:   "部署kafkaui",
		Example: fmt.Sprintf(`dbactuator kafka install_kafkaui %s`, subcmd.CmdBaseExapmleStr),
		Run: func(cmd *cobra.Command, args []string) {
			// 1. 校验基础参数（如 JSON 输入、运行模式等）
			util.CheckErr(act.Validate())
			// 2. 回滚优先：如果传入 --rollback 则执行回滚并退出
			if act.RollBack {
				util.CheckErr(act.Rollback())
				return
			}
			// 3. 初始化：反序列化业务参数、注入通用运行参数、设置默认值
			util.CheckErr(act.Init())
			// 4. 执行安装流程
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Validate 校验基础参数（由 BaseOptions 提供具体实现）。
func (d *InstallKafkaUIAct) Validate() (err error) {
	return d.BaseOptions.Validate()
}

// Init 初始化安装动作：
// - 反序列化传入参数到 Service.Params（通常来自标准输入或参数文件的 JSON）
// - 注入通用运行时参数（GeneralRuntimeParam）
// - 通过组件设置默认参数
func (d *InstallKafkaUIAct) Init() (err error) {
	logger.Info("InstallKafkaUIAct Init")
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return d.Service.InitDefaultParam()
}

// Rollback 执行回滚：
// - 从输入反序列化回滚上下文（RollBackObjects）
// - 调用 RollBack 执行回滚动作
func (d *InstallKafkaUIAct) Rollback() (err error) {
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

// Run 执行安装步骤：
// - 构建步骤列表（目前仅包含“部署kafkaui”一个步骤）
// - 若执行失败，则输出可用于后续回滚的上下文（<ctx>...<ctx> 包裹的 JSON）
// - 成功则记录日志并返回
func (d *InstallKafkaUIAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			// 步骤名称（用于日志/打印）
			FunName: "部署kafkaui",
			// 实际执行的函数
			Func: d.Service.InstallKafkaUI,
		},
	}

	// 执行步骤
	if err := steps.Run(); err != nil {
		// 将回滚上下文序列化输出，供上层调度器在需要时进行回滚
		rollbackCtxb, rerr := json.Marshal(d.Service.RollBackContext)
		if rerr != nil {
			logger.Error("json Marshal %s", err.Error())
			// 无法生成回滚上下文时，明确告知无法回滚
			fmt.Printf("<ctx>Can't RollBack<ctx>\n")
		}
		// 输出回滚上下文，外层根据 <ctx> 标签解析
		fmt.Printf("<ctx>%s<ctx>\n", string(rollbackCtxb))
		return err
	}

	logger.Info("install_kafkaui successfully")
	return nil
}
