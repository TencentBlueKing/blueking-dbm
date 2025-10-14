package main

import (
	"encoding/json"
	"fmt"
	"os"
	"time"

	"github.com/spf13/cobra"

	binlog_parser "dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/binlog-parser"
)

var parseTimeCmd = &cobra.Command{
	Use:   "mysqlbinlog-parse-time",
	Short: "parse start or stop time for binlog",
	Long:  `parse start or stop time for binlog`,
	RunE: func(cmd *cobra.Command, args []string) error {
		output := make(map[string]interface{})
		bp, _ := binlog_parser.NewBinlogParse("mysql", 0, time.RFC3339)
		filenames, _ := cmd.Flags().GetStringSlice("filename")
		for _, filename := range filenames {
			events, err := bp.GetTime(filename, true, true)
			if err != nil {
				return err
			}
			output[filename] = events
		}
		if b, err := json.Marshal(output); err != nil {
			return err
		} else {
			fmt.Println(string(b))
			return nil
		}
	},
}

func init() {
	//命令行的flag
	parseTimeCmd.Flags().StringSliceP("filename", "f", nil, "binlog file name, comma separated")
	_ = parseTimeCmd.MarkFlagRequired("filename")
}

func main() {
	if err := parseTimeCmd.Execute(); err != nil {
		_, _ = os.Stderr.WriteString(err.Error() + "\n")
		os.Exit(1)
	}
}
