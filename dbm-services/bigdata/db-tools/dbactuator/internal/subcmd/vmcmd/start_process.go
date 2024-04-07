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

// StartProcessAct 是一个结构体，用于启动VictoriaMetrics进程。
type StartProcessAct struct {
	*subcmd.BaseOptions                                      // BaseOptions 是基础选项，可能包含了一些全局设置或配置。
	Service             victoriametrics.StartStopProcessComp // Service 是用于启动和停止VictoriaMetrics进程的组件。
}

// StartProcessCommand 是一个函数，返回一个cobra.Command对象，该对象定义了一个命令行命令，用于启动VictoriaMetrics进程。
func StartProcessCommand() *cobra.Command {
	act := StartProcessAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "start_process",
		Short:   "启动vm进程",
		Example: fmt.Sprintf(`dbactuator vm start_process %s`, subcmd.CmdBaseExapmleStr),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate()) // 验证参数
			if act.RollBack {             // 如果需要回滚，则执行回滚操作
				util.CheckErr(act.Rollback())
				return
			}
			util.CheckErr(act.Init()) // 初始化
			util.CheckErr(act.Run())  // 运行
		},
	}
	return cmd
}

// Validate 是 StartProcessAct 的验证函数，用于验证参数是否有效。
func (d *StartProcessAct) Validate() (err error) {
	return d.BaseOptions.Validate()
}

// Init 是 StartProcessAct 的初始化函数，用于初始化操作。
func (d *StartProcessAct) Init() (err error) {
	logger.Info("StartProcessAct Init")
	if err = d.Deserialize(&d.Service.Params); err != nil { // 反序列化参数
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam // 设置通用运行时参数
	return d.Service.Init()                             // 初始化服务
}

// Rollback 是 StartProcessAct 的回滚函数，用于在操作失败时进行回滚。
func (d *StartProcessAct) Rollback() (err error) {
	var r rollback.RollBackObjects
	if err = d.DeserializeAndValidate(&r); err != nil { // 反序列化并验证回滚对象
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	err = r.RollBack() // 执行回滚
	if err != nil {
		logger.Error("roll back failed %s", err.Error())
	}
	return
}

// Run 是 StartProcessAct 的运行函数，用于执行启动VictoriaMetrics进程的操作。
func (d *StartProcessAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "启动vm进程",
			Func:    d.Service.StartProcess, // 启动进程的函数
		},
	}

	if err := steps.Run(); err != nil { // 执行步骤
		rollbackCtxb, rerr := json.Marshal(d.Service.RollBackContext) // 序列化回滚上下文
		if rerr != nil {
			logger.Error("json Marshal %s", err.Error())
			fmt.Printf("<ctx>Can't RollBack<ctx>\n")
		}
		fmt.Printf("<ctx>%s<ctx>\n", string(rollbackCtxb))
		return err
	}

	logger.Info("start_process successfully") // 打印成功信息
	return nil
}
