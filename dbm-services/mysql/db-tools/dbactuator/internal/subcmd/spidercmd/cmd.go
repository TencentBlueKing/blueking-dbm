// Package spidercmd tendbcluster 命令
/*
 * @Description: spider 相关操作的子命令集合
 */
package spidercmd

import (
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd/spidercmd/clone_grants_from_file"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/templates"

	"github.com/spf13/cobra"
)

// NewSpiderCommand tendbcluster 命令
func NewSpiderCommand() *cobra.Command {
	cmds := &cobra.Command{
		Use:   "spider [spider operation]",
		Short: "Spider Operation Command Line Interface",
		RunE:  subcmd.ValidateSubCommand(),
	}
	groups := templates.CommandGroups{
		{
			Message: "spider operation sets",
			Commands: []*cobra.Command{
				NewDeploySpiderCommand(),
				NewUnInstallSpiderCommand(),
				NewRestratSpiderCommand(),
				NewUpgradeSpiderCommand(),
				clone_grants_from_file.NewCloneGrantsDumpPrivCommand(),
				clone_grants_from_file.NewCloneGrantsParsePrivFileCommand(),
				clone_grants_from_file.NewCloneGrantsPrecheckCreateCommand(),
				clone_grants_from_file.NewCloneGrantsImportCreateCommand(),
				clone_grants_from_file.NewCloneGrantsVerifyCreateCommand(),
				clone_grants_from_file.NewCloneGrantsImportGrantCommand(),
				clone_grants_from_file.NewCloneGrantsVerifyGrantCommand(),
			},
		},
	}
	groups.Add(cmds)
	return cmds
}
