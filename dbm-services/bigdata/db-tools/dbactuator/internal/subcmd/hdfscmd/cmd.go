package hdfscmd

import (
	. "dbm-services/bigdata/db-tools/dbactuator/internal/subcmd"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/templates"

	"github.com/spf13/cobra"
)

// HdfsCommand TODO
func HdfsCommand() *cobra.Command {
	commands := &cobra.Command{
		Use:   "hdfs [hdfs operation]",
		Short: "HDFS Operation Command Line Interface",
		RunE:  ValidateSubCommand(),
	}
	groups := templates.CommandGroups{
		{
			Message: "hdfs operation sets",
			Commands: []*cobra.Command{
				InitSystemConfigCommand(),
				DecompressPkgCommand(),
				RenderHdfsConfigCommand(),
				InstallSupervisorCommand(),
				InstallZookeeperCommand(),
				InstallJournalNodeCommand(),
				InstallNn1Command(),
				InstallNn2Command(),
				InstallZKFCCommand(),
				InstallDataNodeCommand(),
				InstallTelegrafCommand(),
				InstallHaProxyCommand(),
				UpdateHostMappingCommand(),
				StopProcessCommand(),
				DataCleanCommand(),
				StartComponentCommand(),
				UpdateDfsHostCommand(),
				RefreshNodesCommand(),
				CheckDecommissionCommand(),
				GenerateKeyCommand(),
				WriteKeyCommand(),
				ScpDirCommand(),
				InstanceOperationCommand(),
				CheckActiveCommand(),
				UpdateZooKeeperConfigCommand(),
			},
		},
	}
	groups.Add(commands)
	return commands
}
