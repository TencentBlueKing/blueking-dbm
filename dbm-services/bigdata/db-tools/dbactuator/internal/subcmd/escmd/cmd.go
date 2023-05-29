package escmd

// Todo
import (
	. "dbm-services/bigdata/db-tools/dbactuator/internal/subcmd"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/templates"

	"github.com/spf13/cobra"
)

// NewEsCommand TODO
// Todo
func NewEsCommand() *cobra.Command {
	cmds := &cobra.Command{
		Use:   "es [es opreation]",
		Short: "ES Operation Command Line Interface",
		RunE:  ValidateSubCommand(),
	}
	groups := templates.CommandGroups{
		{
			Message: "es opreation sets",
			Commands: []*cobra.Command{
				InstallEsClientCommand(),
				InstallEsColdCommand(),
				InstallEsHotCommand(),
				InstallEsMasterCommand(),
				InstallKibanaCommand(),
				InstallSupervisorCommand(),
				InitCommand(),
				DecompressEsPkgCommand(),
				InitGrantCommand(),
				InstallTelegrafCommand(),
				InstallExporterCommand(),
				ExcludeNodeCommand(),
				CleanDataCommand(),
				StartProcessCommand(),
				StopProcessCommand(),
				RestartProcessCommand(),
				ReplaceMasterCommand(),
				CheckShardsCommand(),
				CheckConnectionsCommand(),
				CheckNodesCommand(),
				GenCerCommand(),
				PackCerCommand(),
			},
		},
	}
	groups.Add(cmds)
	return cmds
}
