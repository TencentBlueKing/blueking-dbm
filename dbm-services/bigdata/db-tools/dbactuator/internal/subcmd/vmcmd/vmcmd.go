// Package vmcmd TODO
package vmcmd

// Todo
import (
	. "dbm-services/bigdata/db-tools/dbactuator/internal/subcmd"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/templates"

	"github.com/spf13/cobra"
)

// VMCommand TODO
func VMCommand() *cobra.Command {
	cmds := &cobra.Command{
		Use:   "vm [vm opreation]",
		Short: "VM Operation Command Line Interface",
		RunE:  ValidateSubCommand(),
	}
	groups := templates.CommandGroups{
		{
			Message: "vm opreation sets",
			Commands: []*cobra.Command{
				InstallVMStorageCommand(),
				InstallVMInsertCommand(),
				InstallVMSelectCommand(),
				InstallSupervisorCommand(),
				InitCommand(),
				DecompressVMPkgCommand(),
			},
		},
	}
	groups.Add(cmds)
	return cmds
}
