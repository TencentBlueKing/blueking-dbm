package cmd

import (
	"fmt"

	"github.com/spf13/cobra"
)

// versionCmd represents the version command
var subCmdVersion = &cobra.Command{
	Use:   "version",
	Short: "version information",
	Long:  `version information about buildStamp, gitHash`,
	Run: func(cmd *cobra.Command, args []string) {
		printVersion()
	},
}
var version = ""
var buildStamp = ""
var gitHash = ""

func init() {
	rootCmd.AddCommand(subCmdVersion)
}
func printVersion() {
	fmt.Printf("Version: %s, GitHash: %s, BuildAt: %s\n", version, gitHash, buildStamp)
}
