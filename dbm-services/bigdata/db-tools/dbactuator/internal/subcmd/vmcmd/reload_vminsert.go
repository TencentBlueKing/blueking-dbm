package vmcmd

import (
	"encoding/json"
	"fmt"

	"dbm-services/bigdata/db-tools/dbactuator/internal/subcmd"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/components/victoriametrics"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util"
	"dbm-services/common/go-pubpkg/logger"

	"github.com/spf13/cobra"
)

// ReloadVMInsertAct 定义了一个结构体，用于表示部署 vmselect 实例的行为。
type ReloadVMInsertAct struct {
	*subcmd.BaseOptions                               // 嵌入了 BaseOptions 结构体，用于处理通用的命令行选项
	Service             victoriametrics.InstallVMComp // Service 是一个 VictoriaMetrics 安装组件
}

// ReloadVMInsertCommand 创建并返回一个部署 vmselect 命令的实例。
func ReloadVMInsertCommand() *cobra.Command {
	act := ReloadVMInsertAct{
		BaseOptions: subcmd.GBaseOptions, // 初始化 BaseOptions
	}
	cmd := &cobra.Command{
		Use:     "reload_vminsert",                                                         // 命令的使用方式
		Short:   "reload vminsert实例",                                                       // 命令的简短描述
		Example: fmt.Sprintf(`dbactuator vm reload_vminsert %s`, subcmd.CmdBaseExapmleStr), // 命令的示例
		Run: func(cmd *cobra.Command, args []string) { // 命令的执行函数
			util.CheckErr(act.Validate()) // 验证参数
			if act.RollBack {             // 如果需要回滚
				util.CheckErr(act.Rollback()) // 执行回滚操作
				return
			}
			util.CheckErr(act.Init()) // 初始化操作
			util.CheckErr(act.Run())  // 执行部署操作
		},
	}
	return cmd // 返回命令实例
}

// Validate 验证函数，用于验证命令行参数。
func (d *ReloadVMInsertAct) Validate() (err error) {
	return d.BaseOptions.Validate() // 调用 BaseOptions 的验证方法
}

// Init 初始化函数，用于初始化操作。
func (d *ReloadVMInsertAct) Init() (err error) {
	logger.Info("ReloadVMInsertAct Init")                   // 记录日志
	if err = d.Deserialize(&d.Service.Params); err != nil { // 反序列化参数
		logger.Error("DeserializeAndValidate failed, %v", err) // 记录错误日志
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam // 设置通用运行时参数
	return d.Service.InitDefaultParam()                 // 初始化默认参数
}

// Rollback 回滚函数，用于执行回滚操作。
func (d *ReloadVMInsertAct) Rollback() (err error) {
	var r rollback.RollBackObjects                      // 定义回滚对象
	if err = d.DeserializeAndValidate(&r); err != nil { // 反序列化并验证回滚对象
		logger.Error("DeserializeAndValidate failed, %v", err) // 记录错误日志
		return err
	}
	err = r.RollBack() // 执行回滚
	if err != nil {
		logger.Error("roll back failed %s", err.Error()) // 记录回滚失败的日志
	}
	return
}

// Run TODO
func (d *ReloadVMInsertAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "Reload vminsert",
			Func:    d.Service.ReloadVMInsert,
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

	logger.Info("reload_vminsert successfully")
	return nil
}
