// Package spiderctlcmd 中控节点
/*
 * @Description: spiderctl (中控节点)相关操作的子命令集合
 */
package spiderctlcmd

import (
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/templates"

	"github.com/spf13/cobra"
)

// NewSpiderCtlCommand 中控节点
func NewSpiderCtlCommand() *cobra.Command {
	cmds := &cobra.Command{
		Use:   "spiderctl [spider-ctl operation]",
		Short: "Spiderctl Operation Command Line Interface",
		RunE:  subcmd.ValidateSubCommand(),
	}
	groups := templates.CommandGroups{
		{
			Message: "spiderctl operation sets",
			Commands: []*cobra.Command{
				NewDeploySpiderCtlCommand(),
				NewInitCLusterRoutingCommand(),
				NewAddTmpSpiderCommand(),
				AddSlaveClusterRoutingCommand(),
				NewUnInstallSpiderCtlCommand(),
				NewClusterMigrateCutOverCommand(),
				NewClusterBackendSwitchCommand(),
			},
		},
	}
	groups.Add(cmds)
	return cmds
}
