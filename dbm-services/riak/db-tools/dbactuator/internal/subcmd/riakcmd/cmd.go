// Package riakcmd TODO
/*
 * @Description: proxy 相关操作的子命令集合
 */
package riakcmd

import (
	"dbm-services/riak/db-tools/dbactuator/internal/subcmd"
	"dbm-services/riak/db-tools/dbactuator/pkg/util/templates"

	"github.com/spf13/cobra"
)

// NewRiakCommand TODO
func NewRiakCommand() *cobra.Command {
	cmds := &cobra.Command{
		Use:   "riak [riak operation]",
		Short: "Riak Operation Command Line Interface",
		RunE:  subcmd.ValidateSubCommand(),
	}
	groups := templates.CommandGroups{
		{
			Message: "riak",
			Commands: []*cobra.Command{
				NewDeployRiakCommand(),
				NewJoinClusterCommand(),
				NewCommitClusterChangeCommand(),
				NewInitBucketCommand(),
				NewGetConfigCommand(),
				NewCheckConnectionsCommand(),
				NewRemoveNodeCommand(),
				NewTransferCommand(),
				NewUninstallCommand(),
			},
		},
	}
	groups.Add(cmds)
	return cmds
}
