package cmd

import (
	"fmt"
	"log"
	"os"
	"runtime/debug"

	"dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/rotate"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

// Execute TODO
func Execute() {
	defer func() {
		if err := recover(); err != nil {
			fmt.Println(err)
			log.Println("panic goroutine inner error", err, string(debug.Stack()))
			os.Exit(1)
			return
		}
	}()
	err := rootCmd.Execute()
	if err != nil {
		os.Exit(1)
	}
}

var rootCmd = &cobra.Command{
	Use:   "rotate_binlog",
	Short: "rotate binlog and backup them to remote",
	Long: `rotate binlog files and backup them to remote
                backup system`,
	SilenceUsage: true,
	RunE: func(cmd *cobra.Command, args []string) error {
		comp := rotate.RotateBinlogComp{Config: viper.GetString("config")}
		if removeConfigs, err := cmd.PersistentFlags().GetStringSlice("removeConfig"); err != nil {
			return err
		} else if len(removeConfigs) > 0 {
			return comp.RemoveConfig(removeConfigs)
		}
		addSchedule, _ := cmd.PersistentFlags().GetBool("addSchedule")
		delSchedule, _ := cmd.PersistentFlags().GetBool("delSchedule")
		if isSchedule, err := comp.HandleScheduler(addSchedule, delSchedule); err != nil {
			return err
		} else if isSchedule {
			return nil
		}

		return comp.Start()
	},
	PreRun: func(cmd *cobra.Command, args []string) {
		// subcmd.SetLogger(nil, &subcmd.BaseOptions{Uid: "rotate_binlog", NodeId: "0"})
	},
}

func init() {
	var Config string
	rootCmd.PersistentFlags().StringVarP(&Config, "config", "c", "config.yaml", "config file")
	rootCmd.PersistentFlags().StringSlice("removeConfig", nil, "remove binlog instance rotate config from config file")
	rootCmd.PersistentFlags().Bool("addSchedule", false, "add schedule to crond")
	rootCmd.PersistentFlags().Bool("delSchedule", false, "del schedule from crond")
	viper.BindPFlag("config", rootCmd.PersistentFlags().Lookup("config"))
}
