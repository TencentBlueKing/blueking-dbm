package pulsarcmd

import (
	. "dbm-services/bigdata/db-tools/dbactuator/internal/subcmd"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/templates"

	"github.com/spf13/cobra"
)

// NewPulsarCommand TODO
func NewPulsarCommand() *cobra.Command {
	cmds := &cobra.Command{
		Use:   "pulsar [pulsar operation]",
		Short: "Pulsar Operation Command Line Interface",
		RunE:  ValidateSubCommand(),
	}
	groups := templates.CommandGroups{
		{
			Message: "pulsar operation sets",
			Commands: []*cobra.Command{
				InitCommand(),
				DecompressPulsarPkgCommand(),
				InitPulsarClusterCommand(),
				InstallPulsarZookeeperCommand(),
				InstallPulsarBookkeeperCommand(),
				InstallPulsarBrokerCommand(),
				InstallSupervisorCommand(),
				// StartPulsarBrokerCommand(),
				CleanDataCommand(),
				CheckNamespaceConfigCommand(),
				CheckBrokerConfigCommand(),
				CheckUnderReplicatedCommand(),
				DecommissionBookieCommand(),
				StopProcessCommand(),
				StartProcessCommand(),
				RestartProcessCommand(),
				InstallPulsarManagerCommand(),
				AddHostsCommand(),
				ModifyHostsCommand(),
				InitPulsarManagerCommand(),
				SetBookieReadOnlyCommand(),
				UnsetBookieReadOnlyCommand(),
				CheckLedgerMetadataCommand(),
			},
		},
	}
	groups.Add(cmds)
	return cmds
}
