// Package cmd rootcmd
package cmd

import (
	"dbm-services/redis/db-tools/dbmon/config"
	"dbm-services/redis/db-tools/dbmon/mylog"
	"dbm-services/redis/db-tools/dbmon/pkg/consts"
	"dbm-services/redis/db-tools/dbmon/pkg/httpapi"
	"dbm-services/redis/db-tools/dbmon/pkg/keylifecycle"
	"dbm-services/redis/db-tools/dbmon/pkg/mongojob"
	"dbm-services/redis/db-tools/dbmon/pkg/redisbinlogbackup"
	"dbm-services/redis/db-tools/dbmon/pkg/redisfullbackup"
	"dbm-services/redis/db-tools/dbmon/pkg/redisheartbeat"
	"dbm-services/redis/db-tools/dbmon/pkg/redismonitor"
	"dbm-services/redis/db-tools/dbmon/pkg/report"
	"fmt"
	"log"
	"os"
	"runtime/debug"
	"time"

	"github.com/robfig/cron/v3"
	"github.com/spf13/cobra"
)

var cfgFile string
var showversion = false

// rootCmd represents the base command when called without any subcommands
var rootCmd = &cobra.Command{
	Use:   "bk-dbmon",
	Short: "redis local crontab job,include routine_backup,heartbeat etc",
	Long: `redis local crontab job,include routine_backup,heartbeat etc.
	Wait each job finish,the job result would write to local file, and other program would report the result.
	`,
	// Uncomment the following line if your bare application
	// has an action associated with it:
	Run: func(cmd *cobra.Command, args []string) {
		defer func() {
			if r := recover(); r != nil {
				_, _ = fmt.Fprintf(os.Stderr, "%s", string(debug.Stack()))
			}
		}()

		if showversion {
			_, _ = fmt.Fprintf(os.Stdout, "bk-dbmon %s\n", consts.BkDbmonVersion)
			return
		}

		config.InitConfig(cfgFile)
		mylog.InitRotateLoger()
		var entryID cron.EntryID
		var err error

		hasMongo, hasRedis, _ := getDbType(config.GlobalConf.Servers)

		if hasMongo && hasRedis {
			mylog.Logger.Fatal("dbmon not support mongo and redis at the same time")
		}

		c := cron.New(
			cron.WithLogger(mylog.AdapterLog),
		)
		if hasRedis {
			report.InitGlobalHistoryClearJob(config.GlobalConf)
			redisfullbackup.InitGlobRedisFullBackupJob(config.GlobalConf)
			redisbinlogbackup.InitGlobRedisBinlogBackupJob(config.GlobalConf)
			redisheartbeat.InitGlobRedisHeartbeatJob(config.GlobalConf)
			redismonitor.InitGlobRedisMonitorJob(config.GlobalConf)
			keylifecycle.InitRedisKeyLifeCycleJob(config.GlobalConf)
			// 默认每小时执行一次清理
			entryID, err = c.AddJob("0 1 * * *",
				cron.NewChain(cron.SkipIfStillRunning(mylog.AdapterLog)).Then(report.GlobHistoryClearJob))
			if err != nil {
				log.Panicf("reportHistoryClear addjob fail,entryID:%d,err:%v\n", entryID, err)
				return
			}
			if config.GlobalConf.RedisFullBackup.Cron != "" {
				entryID, err = c.AddJob(config.GlobalConf.RedisFullBackup.Cron,
					cron.NewChain(cron.SkipIfStillRunning(mylog.AdapterLog)).Then(redisfullbackup.GlobRedisFullBakJob))
				if err != nil {
					log.Panicf("fullbackup addjob fail,entryID:%d,err:%v\n", entryID, err)
					return
				}
			}
			if config.GlobalConf.RedisBinlogBackup.Cron != "" {
				entryID, err = c.AddJob(config.GlobalConf.RedisBinlogBackup.Cron,
					cron.NewChain(cron.SkipIfStillRunning(mylog.AdapterLog)).Then(redisbinlogbackup.GlobRedisBinlogBakJob))
				if err != nil {
					log.Panicf("binlogbackup addjob fail,entryID:%d,err:%v\n", entryID, err)
					return
				}
			}
			if config.GlobalConf.RedisHeartbeat.Cron != "" {
				entryID, err = c.AddJob(config.GlobalConf.RedisHeartbeat.Cron,
					cron.NewChain(cron.SkipIfStillRunning(mylog.AdapterLog)).Then(redisheartbeat.GlobRedisHeartbeatJob))
				if err != nil {
					fmt.Printf("heartbeat addjob fail,entryID:%d,err:%v\n", entryID, err)
					return
				}
			}
			if config.GlobalConf.RedisMonitor.Cron != "" {
				entryID, err = c.AddJob(config.GlobalConf.RedisMonitor.Cron,
					cron.NewChain(cron.SkipIfStillRunning(mylog.AdapterLog)).Then(redismonitor.GlobRedisMonitorJob))
				if err != nil {
					fmt.Printf("monitor addjob fail,entryID:%d,err:%v\n", entryID, err)
					return
				}
			}
			if config.GlobalConf.KeyLifeCycle.Cron != "" {
				entryID, err = c.AddJob(config.GlobalConf.KeyLifeCycle.Cron,
					cron.NewChain(cron.SkipIfStillRunning(mylog.AdapterLog)).Then(keylifecycle.GlobRedisKeyLifeCycleJob))
				if err != nil {
					fmt.Printf("keylifecycle addjob fail,entryID:%d,err:%v\n", entryID, err)
					return
				}
			}
		} else if hasMongo {

			// Login 登录检查和拉起
			entryID, err = c.AddJob("@every 1m",
				cron.NewChain(cron.SkipIfStillRunning(mylog.AdapterLog)).Then(
					mongojob.GetBackupJob(config.GlobalConf)))

			if err != nil {
				log.Panicf("mongo backup addjob fail,entryID:%d,err:%v\n", entryID, err)
				return
			}

			entryID, err = c.AddJob("@every 1m",
				cron.NewChain(cron.SkipIfStillRunning(mylog.AdapterLog)).Then(
					mongojob.GetCheckServiceJob(config.GlobalConf)))

		} else {
		}
		mylog.Logger.Info(fmt.Sprintf("start cron job,entryID:%d Listen:%s\n", entryID, config.GlobalConf.HttpAddress))
		c.Start()
		httpapi.StartListen(config.GlobalConf)
		for {
			time.Sleep(10 * time.Second)
		}
	},
}

// Execute adds all child commands to the root command and sets flags appropriately.
// This is called by main.main(). It only needs to happen once to the rootCmd.
func Execute() {
	err := rootCmd.Execute()
	if err != nil {
		os.Exit(1)
	}
}

func init() {
	// Here you will define your flags and configuration settings.
	// Cobra supports persistent flags, which, if defined here,
	// will be global for your application.

	rootCmd.PersistentFlags().StringVar(&cfgFile, "config", "dbmon-config.yaml",
		"required,config file (default is ./dbmon-config.yaml)")
	rootCmd.PersistentFlags().BoolVarP(&showversion, "version", "v", false, "show bk-dbmon version")

	// Cobra also supports local flags, which will only run
	// when this action is called directly.
	// rootCmd.Flags().BoolP("toggle", "t", false, "Help message for toggle")

}

// getDbType TODO
// return getDbType
func getDbType(servers []config.ConfServerItem) (hasMongo, hasRedis bool, err error) {
	for _, row := range servers {
		if consts.IsMongo(row.ClusterType) {
			hasMongo = true
		} else {
			hasRedis = true
		}
	}
	return
}
