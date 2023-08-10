// Package  命令
/*
 * @Description: spider 相关操作的子命令集合
 */
package tbinlogdumpercmd

import (
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/templates"

	"github.com/spf13/cobra"
)

// NewSpiderCommand tendbcluster 命令
func NewTbinlogDumperCommand() *cobra.Command {
	cmds := &cobra.Command{
		Use:   "tbinlogdumper [spider operation]",
		Short: "Tbinlogdumper Operation Command Line Interface",
		RunE:  subcmd.ValidateSubCommand(),
	}
	groups := templates.CommandGroups{
		{
			Message: "tbinlogdumper operation sets",
			Commands: []*cobra.Command{
				NewDeployTbinlogDumperCommand(),
				NewUnInstallTbinlogDumperCommand(),
			},
		},
	}
	groups.Add(cmds)
	return cmds
}
