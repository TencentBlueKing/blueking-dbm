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

// ExecuteReassignmentAct 结构体定义了执行Kafka主题重新分配的操作
type ExecuteReassignmentAct struct {
	*subcmd.BaseOptions                         // 嵌入基础选项
	Service             kafka.TopicReassignComp // Kafka服务组件
}

// ExecuteReassignmentCommand 创建并返回一个cobra命令，用于执行Kafka主题重新分配
func ExecuteReassignmentCommand() *cobra.Command {
	act := ExecuteReassignmentAct{
		BaseOptions: subcmd.GBaseOptions, // 初始化基础选项
	}
	cmd := &cobra.Command{
		Use:     "execute_reassignment",
		Short:   "执行Kafka主题重新分配",
		Example: fmt.Sprintf(`dbactuator kafka execute_reassignment %s`, subcmd.CmdBaseExapmleStr),
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

// Validate 验证ExecuteReassignmentAct结构体的参数
func (d *ExecuteReassignmentAct) Validate() (err error) {
	return d.BaseOptions.Validate() // 调用基础选项的验证方法
}

// Init 初始化ExecuteReassignmentAct结构体
func (d *ExecuteReassignmentAct) Init() (err error) {
	logger.Info("ExecuteReassignmentAct Init")
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam // 设置通用运行时参数
	return d.Service.Init()                             // 初始化服务组件
}

// Rollback 执行回滚操作
func (d *ExecuteReassignmentAct) Rollback() (err error) {
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

// Run 执行Kafka主题重新分配的操作
func (d *ExecuteReassignmentAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "执行Kafka主题重新分配计划",
			Func:    d.Service.ExecuteReassignment,
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

	logger.Info("execute_reassignment successfully") // 打印成功信息
	return nil
}
