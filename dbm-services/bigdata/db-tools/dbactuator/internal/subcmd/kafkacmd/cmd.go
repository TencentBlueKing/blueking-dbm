package kafkacmd

import (
	// 导入内部子命令包和模板工具包
	. "dbm-services/bigdata/db-tools/dbactuator/internal/subcmd"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/templates"

	"github.com/spf13/cobra"
)

// NewKafkaCommand 创建一个新的Kafka命令集
// 这个函数返回一个*cobra.Command对象，它是Kafka相关操作的根命令
func NewKafkaCommand() *cobra.Command {
	// 创建根命令"kafka"，它将包含一系列子命令
	cmds := &cobra.Command{
		Use:   "kafka [kafka operation]",                // 使用说明
		Short: "Kafka Operation Command Line Interface", // 简短描述
		RunE:  ValidateSubCommand(),                     // 当运行无子命令时，验证是否提供了子命令
	}

	// 定义一组子命令
	groups := templates.CommandGroups{
		{
			Message: "kafka operation sets", // 组描述
			Commands: []*cobra.Command{
				// 添加Kafka相关的子命令
				InitCommand(),
				DecompressKafkaPkgCommand(),
				InstallSupervisorCommand(),
				InstallZookeeperCommand(),
				InitKafkaUserCommand(),
				InstallBrokerCommand(),
				InstallManagerCommand(),
				CleanDataCommand(),
				StartProcessCommand(),
				StopProcessCommand(),
				RestartProcessCommand(),
				CheckReassignmentCommand(),
				ReduceBrokerCommand(),
				ReconfigAddCommand(),
				ReconfigRemoveCommand(),
				RestartBrokerCommand(),
				ReplaceBrokerCommand(),
				CheckBrokerEmptyCommand(),
			},
		},
	}

	// 将命令组添加到根命令
	groups.Add(cmds)

	// 返回根命令对象
	return cmds
}
