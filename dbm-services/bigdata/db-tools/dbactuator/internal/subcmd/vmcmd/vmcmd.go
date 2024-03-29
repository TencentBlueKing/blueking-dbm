package vmcmd

// 引入了一些必要的包，包括内部的子命令处理包，模板工具包，以及第三方的cobra包。
import (
	. "dbm-services/bigdata/db-tools/dbactuator/internal/subcmd"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/templates"

	"github.com/spf13/cobra"
)

// VMCommand 函数返回一个处理"vm"命令的*cobra.Command。
// "vm"命令用于执行与虚拟机相关的操作。
func VMCommand() *cobra.Command {
	// 创建一个新的cobra.Command对象，设置其使用方法，简短描述，以及运行时的验证函数。
	cmds := &cobra.Command{
		Use:   "vm [vm operation]",
		Short: "VM Operation Command Line Interface",
		RunE:  ValidateSubCommand(),
	}
	// 创建一个新的命令组，包含了一些子命令，如安装vmstorage，安装vminsert等。
	groups := templates.CommandGroups{
		{
			Message: "vm operation sets",
			Commands: []*cobra.Command{
				// 安装vmstorage的命令
				InstallVMStorageCommand(),
				// 安装vminsert的命令
				InstallVMInsertCommand(),
				// 安装vmselect的命令
				InstallVMSelectCommand(),
				// 安装supervisor的命令
				InstallSupervisorCommand(),
				// 初始化命令
				InitCommand(),
				// 解压VMPkg的命令
				DecompressVMPkgCommand(),
			},
		},
	}
	// 将命令组添加到"vm"命令中。
	groups.Add(cmds)
	// 返回处理"vm"命令的*cobra.Command。
	return cmds
}
