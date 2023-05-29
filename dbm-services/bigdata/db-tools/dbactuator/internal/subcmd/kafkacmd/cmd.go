package kafkacmd

// Todo
import (
	. "dbm-services/bigdata/db-tools/dbactuator/internal/subcmd"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/templates"

	"github.com/spf13/cobra"
)

// NewKafkaCommand TODO
// Todo
func NewKafkaCommand() *cobra.Command {
	cmds := &cobra.Command{
		Use:   "kafka [kafka operation]",
		Short: "Kafka Operation Command Line Interface",
		RunE:  ValidateSubCommand(),
	}
	groups := templates.CommandGroups{
		{
			Message: "kafka operation sets",
			Commands: []*cobra.Command{
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
			},
		},
	}
	groups.Add(cmds)
	return cmds
}
