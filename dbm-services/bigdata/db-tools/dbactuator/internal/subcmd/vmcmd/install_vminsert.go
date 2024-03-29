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

// InstallVMInsertAct 结构体包含了基本选项和VictoriaMetrics服务的安装组件。
type InstallVMInsertAct struct {
	*subcmd.BaseOptions
	Service victoriametrics.InstallVMComp
}

// InstallVMInsertCommand 函数返回一个处理"install_vminsert"命令的*cobra.Command。
// "install_vminsert"命令用于安装VMInsert实例。
func InstallVMInsertCommand() *cobra.Command {
	// 创建一个InstallVMInsertAct对象，包含了基本选项。
	act := InstallVMInsertAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	// 创建一个新的cobra.Command对象，设置其使用方法，简短描述，示例，以及运行时的函数。
	cmd := &cobra.Command{
		Use:     "install_vminsert",
		Short:   "部署vminsert实例",
		Example: fmt.Sprintf(`dbactuator vm install_vminsert %s`, subcmd.CmdBaseExapmleStr),
		Run: func(cmd *cobra.Command, args []string) {
			// 验证参数，初始化，运行命令或回滚。
			util.CheckErr(act.Validate())
			if act.RollBack {
				util.CheckErr(act.Rollback())
				return
			}
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	// 返回处理"install_vminsert"命令的*cobra.Command。
	return cmd
}

// Validate 方法用于验证InstallVMInsertAct的基本选项。
func (d *InstallVMInsertAct) Validate() (err error) {
	return d.BaseOptions.Validate()
}

// Init 方法用于初始化InstallVMInsertAct。
// 它首先记录初始化的信息，然后反序列化服务参数。
// 如果反序列化失败，它将记录错误并返回。
// 最后，它将通用运行时参数设置为服务的通用参数，并初始化默认参数。
func (d *InstallVMInsertAct) Init() (err error) {
	logger.Info("InstallVMInsertAct Init")
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return d.Service.InitDefaultParam()
}

// Rollback 方法用于回滚InstallVMInsertAct。
// 它首先反序列化并验证回滚对象，如果失败，它将记录错误并返回。
// 然后，它尝试回滚，如果失败，它将记录错误。
func (d *InstallVMInsertAct) Rollback() (err error) {
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
func (d *InstallVMInsertAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "部署vminsert",
			Func:    d.Service.InstallVMInsert,
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

	logger.Info("install_vminsert successfully")
	return nil
}
