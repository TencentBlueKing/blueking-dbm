package cmd

import (
	"fmt"
	"os"
	"sort"
	"strings"

	"dbm-services/mysql/db-tools/mysql-crond/api"
	"dbm-services/mysql/db-tools/mysql-crond/pkg/config"

	"github.com/olekukonko/tablewriter"
	"github.com/spf13/cast"
	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

// versionCmd represents the version command
var listEntriesCmd = &cobra.Command{
	Use:   "list",
	Short: "list active crond entries",
	Long:  `list active crond entries`,
	Run: func(cmd *cobra.Command, args []string) {
		listEntries(cmd)
	},
}

func init() {
	listEntriesCmd.PersistentFlags().StringP("config", "c", "", "config file")
	_ = listEntriesCmd.MarkPersistentFlagRequired("config")
	_ = viper.BindPFlag("list-config", listEntriesCmd.PersistentFlags().Lookup("config"))

	rootCmd.AddCommand(listEntriesCmd)
}

func listEntries(cmd *cobra.Command) {
	// init config to get listen ip:port
	var err error
	apiUrl := ""
	if apiUrl, err = config.GetApiUrlFromConfig(viper.GetString("list-config")); err != nil {
		fmt.Fprintln(os.Stderr, "read config error", err.Error())
		os.Exit(1)
	}

	manager := api.NewManager(apiUrl)
	entries, err := manager.Entries()
	if err != nil {
		fmt.Fprintln(os.Stderr, "fail to list entries", err.Error())
		os.Exit(1)
	}
	sort.Sort(api.SimpleEntryList(entries)) // 自定义排序展示
	table := tablewriter.NewWriter(os.Stdout)
	table.SetAutoWrapText(true)
	table.SetRowLine(true)
	table.SetAutoFormatHeaders(false)

	table.SetHeader([]string{"ID", "JobName", "Schedule", "Command", "Args", "WorkDir", "Enable"})
	for _, e := range entries {
		table.Append([]string{
			cast.ToString(e.ID),
			e.Job.Name,
			e.Job.Schedule,
			e.Job.Command,
			strings.Join(e.Job.Args, " "),
			e.Job.WorkDir,
			cast.ToString(e.Job.Enable)})
	}

	table.Render()
}
