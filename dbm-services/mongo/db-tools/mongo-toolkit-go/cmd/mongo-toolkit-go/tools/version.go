package tools

import (
	"fmt"
	"github.com/spf13/cobra"
)

var Version = ""
var BuildDate = ""
var CommitSha1 = ""
var BuildGolang = ""

func printVersion() {
	fmt.Printf(`Version     : %s
build_date  : %s
commit_sha1 : %s
go : %s
`, Version, BuildDate, CommitSha1, BuildGolang)
}

var versionCmd = &cobra.Command{
	Use:   "version",
	Short: "version",
	Long:  "version info",
	Run: func(cmd *cobra.Command, args []string) {
		printVersion()
	}}

func init() {
	rootCmd.AddCommand(versionCmd)
}
