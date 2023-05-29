package influxdbcmd

// Todo
import (
	. "dbm-services/bigdata/db-tools/dbactuator/internal/subcmd"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/templates"

	"github.com/spf13/cobra"
)

// NewInfluxdbCommand TODO
// Todo
func NewInfluxdbCommand() *cobra.Command {
	cmds := &cobra.Command{
		Use:   "influxdb [influxdb operation]",
		Short: "Influxdb Operation Command Line Interface",
		RunE:  ValidateSubCommand(),
	}
	groups := templates.CommandGroups{
		{
			Message: "influxdb operation sets",
			Commands: []*cobra.Command{
				InitCommand(),
				DecompressInfluxdbPkgCommand(),
				InstallSupervisorCommand(),
				InstallInfluxdbCommand(),
				InitUserCommand(),
				InstallTelegrafCommand(),
				CleanDataCommand(),
				StartProcessCommand(),
				StopProcessCommand(),
				RestartProcessCommand(),
			},
		},
	}
	groups.Add(cmds)
	return cmds
}
