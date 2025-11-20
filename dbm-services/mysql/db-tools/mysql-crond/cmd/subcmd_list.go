package cmd

import (
	"fmt"
	"net/url"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"

	"github.com/jedib0t/go-pretty/v6/text"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/mysql/db-tools/mysql-crond/api"
	"dbm-services/mysql/db-tools/mysql-crond/pkg/config"

	"github.com/jedib0t/go-pretty/v6/table"
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
	if !cmutil.FileExists(configFile) {
		// 改从当前命令行所在目录查找，先获取当前 executable 路径
		exePath, _ := os.Executable()
		configFile = filepath.Join(filepath.Dir(exePath), "runtime.yaml")
	}
	if apiUrl, err = config.GetApiUrlFromConfig(configFile); err != nil {
		_, _ = fmt.Fprintln(os.Stderr, "read config error", err.Error())
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
	entries, err := manager.EntriesWithParam(queryParam)
	if err != nil {
		_, _ = fmt.Fprintln(os.Stderr, "fail to list entries", err.Error())
		os.Exit(1)
	}
	return entries
}

func printEntries(entries []*api.SimpleEntry, detail bool) {
	sort.Sort(api.SimpleEntryList(entries)) // 自定义排序展示

	tw := table.NewWriter()
	tw.SetOutputMirror(os.Stdout)
	tw.Style().Options.SeparateRows = true
	tw.Style().Format.Header = text.FormatDefault
	//tw.SortBy([]table.SortBy{{Name: "Command", Mode: table.Asc}, {Name: "Schedule", Mode: table.Asc}})
	warnColor := text.Colors{text.FgRed}
	colorTrans := text.Transformer(func(val interface{}) string {
		if val.(bool) == false {
			return warnColor.Sprintf("%t", val)
		}
		return fmt.Sprintf("%t", val)
	})
	if detail {
		tw.SetColumnConfigs([]table.ColumnConfig{
			{Number: 7, Name: "Enable", Transformer: colorTrans}, // column: Enable or not
		})
		tw.AppendHeader(table.Row{"ID", "JobName", "Schedule", "Command", "Args", "WorkDir", "Enable", "NextTime"},
			table.RowConfig{})
		for _, e := range entries {
			row := []interface{}{
				e.ID,
				e.Job.Name,
				e.Job.Schedule,
				e.Job.Command,
				strings.Join(e.Job.Args, " "),
				e.Job.WorkDir,
				*e.Job.Enable,
				e.Next.Format(time.RFC3339),
			}
			tw.AppendRow(row)
		}
	} else {
		tw.SetColumnConfigs([]table.ColumnConfig{
			{Number: 5, Name: "Enable", Transformer: colorTrans}, // column: Enable or not
		})
		tw.AppendHeader(table.Row{"ID", "JobName", "Schedule", "Command", "Enable", "NextTime"})
		for _, e := range entries {
			row := []interface{}{
				e.ID,
				e.Job.Name,
				e.Job.Schedule,
				e.Job.Command,
				*e.Job.Enable,
				e.Next.Format(time.RFC3339),
			}
			tw.AppendRow(row)
		}
	}
	tw.Render()
}
