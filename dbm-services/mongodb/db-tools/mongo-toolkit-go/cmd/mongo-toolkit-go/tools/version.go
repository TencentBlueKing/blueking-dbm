package tools

import (
	"fmt"

	"github.com/spf13/cobra"
)

var Version = ""
var BuildDate = ""
var CommitSha1 = ""
var BuildGolang = ""

// printVersion print version info
func printVersion() {
	fmt.Printf(`Version     : %s
build_date  : %s
commit_sha1 : %s
go : %s
`, Version, BuildDate, CommitSha1, BuildGolang)
}

// versionCmd version
var versionCmd = &cobra.Command{
	Use:   "version",
	Short: "version",
	Long:  "version info",
	Run: func(cmd *cobra.Command, args []string) {
		printVersion()
	}}

// init versionCmd
func init() {
	rootCmd.AddCommand(versionCmd)
}
