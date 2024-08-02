package cmd

import (
	"fmt"
	"net/url"
	"os"
	"sort"
	"strings"
	"time"

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
		status, _ := cmd.Flags().GetString("status")
		entries := listEntries(cmd, status)
		isDetail, _ := cmd.Flags().GetBool("detail")
		printEntries(entries, isDetail)
	},
}

func init() {
	listEntriesCmd.Flags().StringP("name-match", "m", "", "regex to search name, default empty")
	_ = viper.BindPFlag("name-match", listEntriesCmd.Flags().Lookup("name-match"))

	listEntriesCmd.Flags().Bool("detail", false, "show more job column info")
	_ = viper.BindPFlag("detail", listEntriesCmd.Flags().Lookup("detail"))

	listEntriesCmd.Flags().String("status", "disabled,enabled", "list jobs only this status, all,disabled,enabled")
	_ = viper.BindPFlag("status", listEntriesCmd.Flags().Lookup("status"))

	rootCmd.AddCommand(listEntriesCmd)
}

func listEntries(cmd *cobra.Command, status string) []*api.SimpleEntry {
	// init config to get listen ip:port
	var err error
	apiUrl := ""
	configFile, _ := cmd.Flags().GetString("config")
	if apiUrl, err = config.GetApiUrlFromConfig(configFile); err != nil {
		fmt.Fprintln(os.Stderr, "read config error", err.Error())
		os.Exit(1)
	}
	queryParam := url.Values{}
	if status != "" { // all,disabled,enabled
		queryParam.Add("status", status)
	}
	if name, _ := cmd.Flags().GetString("name"); name != "" {
		queryParam.Add("name", name)
	}
	if nameMatch, _ := cmd.Flags().GetString("name-match"); nameMatch != "" {
		queryParam.Add("name-match", nameMatch)
	}
	manager := api.NewManager(apiUrl)
	entries, err := manager.Entries(queryParam)
	if err != nil {
		fmt.Fprintln(os.Stderr, "fail to list entries", err.Error())
		os.Exit(1)
	}
	return entries
}

func printEntries(entries []*api.SimpleEntry, detail bool) {
	sort.Sort(api.SimpleEntryList(entries)) // 自定义排序展示
	table := tablewriter.NewWriter(os.Stdout)
	table.SetAutoWrapText(false)
	table.SetRowLine(true)
	table.SetAutoFormatHeaders(false)

	if detail {
		table.SetHeader([]string{"ID", "JobName", "Schedule", "Command", "Args", "WorkDir", "Enable", "NextTime"})
		for _, e := range entries {
			row := []string{
				cast.ToString(e.ID),
				e.Job.Name,
				e.Job.Schedule,
				e.Job.Command,
				strings.Join(e.Job.Args, " "),
				e.Job.WorkDir,
				cast.ToString(e.Job.Enable),
				e.Next.Format(time.RFC3339),
			}
			if *(e.Job.Enable) {
				table.Append(row)
			} else {
				table.Rich(row,
					[]tablewriter.Colors{nil, nil, nil, nil, nil, nil, tablewriter.Colors{tablewriter.FgMagentaColor}, nil})
			}
		}
	} else {
		table.SetHeader([]string{"ID", "JobName", "Schedule", "Command", "Enable", "NextTime"})
		for _, e := range entries {
			row := []string{
				cast.ToString(e.ID),
				e.Job.Name,
				e.Job.Schedule,
				e.Job.Command,
				cast.ToString(e.Job.Enable),
				e.Next.Format(time.RFC3339),
			}
			if *(e.Job.Enable) {
				table.Append(row)
			} else {
				table.Rich(row,
					[]tablewriter.Colors{nil, nil, nil, nil, tablewriter.Colors{tablewriter.FgMagentaColor}, nil})
			}
		}
	}
	table.Render()
}
