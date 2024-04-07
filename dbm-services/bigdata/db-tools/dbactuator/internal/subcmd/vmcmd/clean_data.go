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

// CleanDataAct 是一个结构体，用于清理VictoriaMetrics的数据目录。
type CleanDataAct struct {
	*subcmd.BaseOptions                               // BaseOptions 是基础选项，可能包含了一些全局设置或配置。
	Service             victoriametrics.CleanDataComp // Service 是用于清理数据的组件。
}

// CleanDataCommand 是一个函数，返回一个cobra.Command对象，该对象定义了一个命令行命令，用于清理VictoriaMetrics的数据目录。
func CleanDataCommand() *cobra.Command {
	act := CleanDataAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "clean_data",
		Short:   "清理vm目录",
		Example: fmt.Sprintf(`dbactuator vm clean_data %s`, subcmd.CmdBaseExapmleStr),
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

// Validate 是 CleanDataAct 的验证函数，用于验证参数是否有效。
func (d *CleanDataAct) Validate() (err error) {
	return d.BaseOptions.Validate()
}

// Init 是 CleanDataAct 的初始化函数，用于初始化操作。
func (d *CleanDataAct) Init() (err error) {
	logger.Info("CleanDataAct Init")
	if err = d.Deserialize(&d.Service.Params); err != nil { // 反序列化参数
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam // 设置通用运行时参数
	return d.Service.Init()                             // 初始化服务
}

// Rollback TODO
//
//	@receiver d
//	@return err
func (d *CleanDataAct) Rollback() (err error) {
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

// Run 是 CleanDataAct 的运行函数，用于执行清理VictoriaMetrics数据目录的操作。
func (d *CleanDataAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "清理数据目录",
			Func:    d.Service.CleanData, // 清理数据的函数
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

	logger.Info("clean_data successfully") // 打印成功信息
	return nil
}
