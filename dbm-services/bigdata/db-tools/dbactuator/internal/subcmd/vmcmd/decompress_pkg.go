package vmcmd

// 导入了一系列的 Go 语言包，包括标准库的包和项目内部的包。
import (
	"encoding/json" // 用于处理 JSON 数据
	"fmt"           // 提供格式化输出函数

	// 以下是项目内部的包，用于数据库操作、VictoriaMetrics 组件、回滚操作和日志记录等。
	"dbm-services/bigdata/db-tools/dbactuator/internal/subcmd"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/components/victoriametrics"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util"
	"dbm-services/common/go-pubpkg/logger"

	"github.com/spf13/cobra" // cobra 是一个用于创建命令行应用程序的库
)

// DecompressVMPkgAct 定义了一个结构体，用于表示解压缩操作的行为。
type DecompressVMPkgAct struct {
	*subcmd.BaseOptions                               // 嵌入了 BaseOptions 结构体，用于处理通用的命令行选项
	Service             victoriametrics.InstallVMComp // Service 是一个 VictoriaMetrics 安装组件
}

// DecompressVMPkgCommand 创建并返回一个解压缩命令的实例。
func DecompressVMPkgCommand() *cobra.Command {
	act := DecompressVMPkgAct{
		BaseOptions: subcmd.GBaseOptions, // 初始化 BaseOptions
	}
	cmd := &cobra.Command{
		Use:     "decompress_pkg",                                                         // 命令的使用方式
		Short:   "解压缩",                                                                    // 命令的简短描述
		Example: fmt.Sprintf(`dbactuator vm decompress_pkg %s`, subcmd.CmdBaseExapmleStr), // 命令的示例
		Run: func(cmd *cobra.Command, args []string) { // 命令的执行函数
			util.CheckErr(act.Validate()) // 验证参数
			if act.RollBack {             // 如果需要回滚
				util.CheckErr(act.Rollback()) // 执行回滚操作
				return
			}
			util.CheckErr(act.Init()) // 初始化操作
			util.CheckErr(act.Run())  // 执行解压缩操作
		},
	}
	return cmd // 返回命令实例
}

// Validate 验证函数，用于验证命令行参数。
func (d *DecompressVMPkgAct) Validate() (err error) {
	return d.BaseOptions.Validate() // 调用 BaseOptions 的验证方法
}

// Init 初始化函数，用于初始化解压缩操作。
func (d *DecompressVMPkgAct) Init() (err error) {
	logger.Info("DecompressVMPkgAct Init")                  // 记录日志
	if err = d.Deserialize(&d.Service.Params); err != nil { // 反序列化参数
		logger.Error("DeserializeAndValidate failed, %v", err) // 记录错误日志
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam // 设置通用运行时参数
	return d.Service.InitDefaultParam()                 // 初始化默认参数
}

// Rollback 回滚函数，用于执行回滚操作。
func (d *DecompressVMPkgAct) Rollback() (err error) {
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

// Run 执行解压缩操作的函数。
func (d *DecompressVMPkgAct) Run() (err error) {
	// 定义一个步骤列表，每个步骤包含一个函数名和对应的函数指针。
	steps := subcmd.Steps{
		{
			FunName: "解压缩",                   // 步骤的名称
			Func:    d.Service.DecompressPkg, // 指向解压缩函数的指针
		},
	}

	// 运行所有步骤，如果出现错误，则执行回滚操作。
	if err := steps.Run(); err != nil {
		// 如果步骤执行出错，尝试将回滚上下文序列化为 JSON 格式。
		rollbackCtxb, rerr := json.Marshal(d.Service.RollBackContext)
		if rerr != nil {
			logger.Error("json Marshal %s", err.Error()) // 记录序列化错误日志
			fmt.Printf("<ctx>Can't RollBack<ctx>\n")     // 输出无法回滚的信息
		}
		fmt.Printf("<ctx>%s<ctx>\n", string(rollbackCtxb)) // 输出回滚上下文
		return err                                         // 返回步骤执行的错误
	}

	// 如果所有步骤都成功执行，记录解压缩成功的日志。
	logger.Info("decompress_pkg successfully")
	return nil // 返回 nil 表示成功
}
