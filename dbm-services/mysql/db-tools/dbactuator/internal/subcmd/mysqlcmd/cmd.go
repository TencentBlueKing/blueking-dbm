package mysqlcmd

import (
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/templates"

	"github.com/spf13/cobra"
)

// NewMysqlCommand mysql子命令
func NewMysqlCommand() *cobra.Command {
	cmds := &cobra.Command{
		Use:   "mysql [mysql operation]",
		Short: "MySQL Operation Command Line Interface",
		RunE:  subcmd.ValidateSubCommand(),
	}
	groups := templates.CommandGroups{
		{
			Message: "mysql operation sets",
			Commands: []*cobra.Command{
				NewDeployMySQLInstanceCommand(),
				NewStartMysqlCommand(),
				NewUnInstallMysqlCommand(),
				NewGrantReplCommand(),
				NewExecSQLFileCommand(),
				CloneClientGrantCommand(),
				NewBackupTruncateDatabaseCommand(),
				//NewBackupDatabaseTableCommand(),
				MycnfChangeCommand(),
				FindLocalBackupCommand(),
				MycnfCloneCommand(),
				NewCutOverToSlaveCommnad(),
				CleanMysqlCommand(),
				PtTableSyncCommand(),
				ParseBinlogTimeCommand(),
				FlashbackBinlogCommand(),
				NewPtTableChecksumCommand(),
				NewInstallMySQLChecksumCommand(),
				NewInstallNewDbBackupCommand(),
				//NewFullBackupCommand(),
				NewInstallRotateBinlogCommand(),
				NewInstallDBAToolkitCommand(),
				NewDeployMySQLCrondCommand(),
				ClearInstanceConfigCommand(),
				NewInstallMySQLMonitorCommand(),
				NewExecPartitionSQLCommand(),
				NewBackupDemandCommand(),
				InstallBackupClientCommand(),
				NewDropTableCommand(),
			},
		},
		{
			Message: "mysql semantic check operation sets",
			Commands: []*cobra.Command{
				NewSenmanticCheckCommand(),
				NewSenmanticDumpSchemaCommand(),
			},
		},
		{
			Message: "mysql slave operation  sets",
			Commands: []*cobra.Command{
				NewBuildMsRelatioCommand(),
				RestoreDRCommand(),
				RecoverBinlogCommand(),
			},
		},
	}
	groups.Add(cmds)
	return cmds
}
