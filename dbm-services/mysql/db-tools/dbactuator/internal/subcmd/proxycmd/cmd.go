// Package proxycmd TODO
/*
 * @Description: proxy 相关操作的子命令集合
 */
package proxycmd

import (
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/templates"

	"github.com/spf13/cobra"
)

// NewMysqlProxyCommand TODO
func NewMysqlProxyCommand() *cobra.Command {
	cmds := &cobra.Command{
		Use:   "proxy [proxy operation]",
		Short: "MySQL Proxy Operation Command Line Interface",
		RunE:  subcmd.ValidateSubCommand(),
	}
	groups := templates.CommandGroups{
		{
			Message: "mysql_proxy",
			Commands: []*cobra.Command{
				NewDeployMySQLProxyCommand(),
				NewSetBackendsCommand(),
				NewUnInstallProxyCommand(),
				NewCloneProxyUserCommand(),
				NewRestartProxyCommand(),
				NewMySQLProxyUpgradeAct(),
				NewStandardizeProxyCommand(),
			},
		},
	}
	groups.Add(cmds)
	return cmds
}
