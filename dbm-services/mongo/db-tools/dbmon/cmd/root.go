// Package cmd rootcmd
package cmd

import (
	"dbm-services/mongo/db-tools/dbmon/cmd/dbmonheartbeat"
	"dbm-services/mongo/db-tools/dbmon/cmd/mongojob"
	"fmt"
	"log"
	_ "net/http/pprof" // pprof TODO
	"os"
	"runtime/debug"

	"github.com/pkg/errors"
	"go.uber.org/zap/zapcore"

	"dbm-services/mongo/db-tools/dbmon/config"
	"dbm-services/mongo/db-tools/dbmon/mylog"
	"dbm-services/mongo/db-tools/dbmon/pkg/consts"
	"dbm-services/mongo/db-tools/dbmon/pkg/httpapi"

	"github.com/robfig/cron/v3"
	"github.com/spf13/cobra"
)

var cfgFile string
var showversion = false
var version string
var githash string
var buildstamp string
var goversion string

const progName = "bk-dbmon-mg"

func init() {
	rootCmd.AddCommand(debugCmd)
	rootCmd.PersistentFlags().StringVar(&cfgFile, "config", "dbmon-config.yaml",
		"required,config file (default is ./dbmon-config.yaml)")
	rootCmd.PersistentFlags().BoolVarP(&showversion, "version", "v", false, "show bk-dbmon version")

}

// rootCmd represents the base command when called without any subcommands
var rootCmd = &cobra.Command{
	Use: progName,
	Short: fmt.Sprintf(`bk-dbmon for mongodb
Version: %s
Githash: %s
Buildstamp:%s
GoVersion: %s`, version, githash, buildstamp, goversion),
	Long: fmt.Sprintf(`mongodb local crontab job,include routine_backup,heartbeat etc.
Wait each job finish,the job result would write to local file, and other program would report the result.
Version: %s
Githash: %s
Buildstamp:%s
GoVersion: %s`, version, githash, buildstamp, goversion),
	// Uncomment the following line if your bare application
	// has an action associated with it:
	Run: func(cmd *cobra.Command, args []string) {
		defer func() {
			if r := recover(); r != nil {
				_, _ = fmt.Fprintf(os.Stderr, "%s", string(debug.Stack()))
			}
		}()

		if showversion {
			_, _ = fmt.Fprintf(os.Stdout, "%s %s\n", progName, consts.BkDbmonVersion)
			return
		}

		mylog.InitRotateLoger()
		defer mylog.Logger.Sync()

		config.InitConfig(cfgFile, mylog.Logger)

		var err error
		// 检查DbType，只支持Mongo
		if err = checkDbType(config.GlobalConf.Servers); err != nil {
			mylog.Logger.Fatal(err.Error())
		}
		// 只允许非root用户运行
		if username := consts.GetUsername(); username == "" || username == "root" {
			mylog.Logger.Fatal(fmt.Sprintf("bad username %q", username))
		}
		if dirs, err := new(mongojob.BackupJob).PrepareDir(); err != nil {
			mylog.Logger.Fatal(fmt.Sprintf("PrepareDir err: %q", err.Error()))
		} else {
			mylog.Logger.Info(fmt.Sprintf("PrepareDir success, dir:%s", dirs))
		}

		var entryID cron.EntryID
		c := cron.New(cron.WithLogger(mylog.AdapterLog))
		job1 := mongojob.GetBackupJob(config.GlobalConf)
		job2 := mongojob.GetCheckHealthHandle(config.GlobalConf)
		job3 := dbmonheartbeat.GetGlobDbmonHeartbeatJob(config.GlobalConf)
		in := []struct {
			job  cron.Job
			cron string
			name string
		}{
			{job: job1, cron: "@every 1m", name: job1.Name},
			{job: job2, cron: "@every 1m", name: job2.Name},
			{job: job3, cron: "@every 1m", name: job3.Name},
		}
		for _, row := range in {
			entryID, err = c.AddJob(row.cron,
				cron.NewChain(cron.SkipIfStillRunning(mylog.AdapterLog)).Then(row.job))
			if err != nil {
				log.Panicf("addjob fail,jobName: %s entryID:%d,err:%v\n", row.name, entryID, err)
				return
			}
			mylog.Logger.Info(fmt.Sprintf("AddJob %s, entryID:%d ", row.name, entryID))
			mylog.Logger.Info("AddJob success",
				zapcore.Field{Key: "jobName", Type: zapcore.StringType, String: row.name},
				zapcore.Field{Key: "entryID", Type: zapcore.Int64Type, Integer: int64(entryID)},
			)
		}
		mylog.Logger.Info(fmt.Sprintf("start dbmon, Listen:%s\n", config.GlobalConf.HttpAddress))
		c.Start()
		// go func() {
		//	// for go tool pprof. curl http://127.0.0.1:6600/debug/pprof/heap
		//	http.ListenAndServe("127.0.0.1:6600", nil)
		// }()
		httpapi.StartListen(config.GlobalConf)
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

// checkDbType 检查DbType
func checkDbType(servers []config.ConfServerItem) (err error) {
	for _, row := range servers {
		if !consts.IsMongo(row.ClusterType) {
			return errors.Errorf("Unsupported clusterType: %q", row.ClusterType)
		}
	}
	return nil
}
