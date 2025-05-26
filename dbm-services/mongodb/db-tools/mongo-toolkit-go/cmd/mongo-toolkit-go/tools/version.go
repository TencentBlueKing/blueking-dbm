package tools

import (
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/pkg/buildinfo"
	"fmt"

	"github.com/spf13/cobra"
)

// printVersion print version info
func printVersion() {
	fmt.Printf("mongo-toolkit-go\n%s\n", buildinfo.VersionInfo())
}

// versionCmd version
var versionCmd = &cobra.Command{
	Use:   "version",
	Short: "version",
	Long:  "version info",
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Printf("mongo-toolkit-go\n%s\n", buildinfo.VersionInfo())
	}}

// init versionCmd
func init() {
	rootCmd.AddCommand(versionCmd)
}
