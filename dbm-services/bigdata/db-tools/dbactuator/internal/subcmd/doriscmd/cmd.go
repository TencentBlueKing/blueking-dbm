package doriscmd

// 引入了一些必要的包，包括内部的子命令处理包，模板工具包，以及第三方的cobra包。
import (
	. "dbm-services/bigdata/db-tools/dbactuator/internal/subcmd"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/templates"

	"github.com/spf13/cobra"
)

// DorisCommand 创建 Doris 命令
func DorisCommand() *cobra.Command {
	cmdList := &cobra.Command{
		Use:   "doris [doris operation]",
		Short: "Doris Operation Command Line Interface",
		RunE:  ValidateSubCommand(),
	}
	groups := templates.CommandGroups{
		{
			Message: "doris operation sets",
			Commands: []*cobra.Command{
				InitSystemConfigCommand(),
				DecompressDorisPkgCommand(),
				RenderConfigCommand(),
				FirstLaunchCommand(),
				InitGrantCommand(),
				InstallDorisCommand(),
				InstallSupervisorCommand(),
				UpdateMetadataCommand(),
				StartFeByHelperCommand(),
				StartProcessCommand(),
				StopProcessCommand(),
				RestartProcessCommand(),
				CleanDataCommand(),
				CheckDecommissionCommand(),
				CheckProcessStartCommand(),
			},
		},
	}
	groups.Add(cmdList)
	return cmdList
}
