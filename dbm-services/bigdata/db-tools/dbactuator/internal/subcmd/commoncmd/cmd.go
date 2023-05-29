package commoncmd

import (
	"dbm-services/bigdata/db-tools/dbactuator/internal/subcmd"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/templates"

	"github.com/spf13/cobra"
)

// NewCommonCommand TODO
// @todo 将来可以把 download 单独作为一个子命令
func NewCommonCommand() *cobra.Command {
	cmds := &cobra.Command{
		Use:   "common [common operation]",
		Short: "Common components Operation Command Line Interface",
		RunE:  subcmd.ValidateSubCommand(),
	}
	groups := templates.CommandGroups{
		{
			Message: "common operation sets",
			Commands: []*cobra.Command{
				CommandFileServer(),
				RMLargeFileCommand(),
			},
		},
	}
	groups.Add(cmds)
	return cmds
}

// NewDownloadCommand TODO
func NewDownloadCommand() *cobra.Command {
	cmds := &cobra.Command{
		Use:   "download [download operation]",
		Short: "download components Operation Command Line Interface",
	}
	groups := templates.CommandGroups{
		{
			Message: "download operation sets",
			Commands: []*cobra.Command{
				CommandDownloadScp(),
				CommandDownloadHttp(),
			},
		},
	}
	groups.Add(cmds)
	return cmds
}
