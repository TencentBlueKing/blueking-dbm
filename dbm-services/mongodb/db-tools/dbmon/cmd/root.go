// Package cmd rootcmd
package cmd

import (
	"context"
	"dbm-services/mongodb/db-tools/dbmon/cmd/backupjob"
	"dbm-services/mongodb/db-tools/dbmon/cmd/checkhealthjob"
	"dbm-services/mongodb/db-tools/dbmon/cmd/datadirjob"
	"dbm-services/mongodb/db-tools/dbmon/cmd/dbmonheartbeat"
	"dbm-services/mongodb/db-tools/dbmon/cmd/dbtablesizejob"
	"dbm-services/mongodb/db-tools/dbmon/cmd/dstatjob"
	"dbm-services/mongodb/db-tools/dbmon/cmd/logparserjob"
	"dbm-services/mongodb/db-tools/dbmon/config"
	"dbm-services/mongodb/db-tools/dbmon/mylog"
	"dbm-services/mongodb/db-tools/dbmon/pkg/consts"
	"dbm-services/mongodb/db-tools/dbmon/pkg/httpapi"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/pkg/buildinfo"
	"fmt"
	_ "net/http/pprof" // pprof TODO
	"os"
	"os/signal"
	"path"
	"runtime/debug"
	"sync"
	"syscall"
	"time"

	"github.com/pkg/errors"
	"github.com/robfig/cron/v3"
	"go.uber.org/zap"

	"github.com/spf13/cobra"
)

var cfgFile string
var clusterConfigFile string
var showVersion = false
var logLevel string
var stdout bool // file or stdout

var workDir string

const progName = "bk-dbmon"

func init() {
	rootCmd.AddCommand(configCmd)
	rootCmd.AddCommand(debugCmd)
	rootCmd.AddCommand(alarmCmd)
	rootCmd.AddCommand(metaCmd)
	rootCmd.AddCommand(versionCmd)
	rootCmd.PersistentFlags().StringVar(&cfgFile, "config", "dbmon-config.yaml",
		"required,config file (default is ./dbmon-config.yaml)")
	rootCmd.PersistentFlags().StringVar(&clusterConfigFile, "cluster-config", "cluster-config.yaml",
		"required,cluster-config.yaml file (default is $(dir of bin)/cluster-config.yaml)")
	rootCmd.PersistentFlags().StringVar(&logLevel, "logLevel", "info",
		"log level, default is info, support debug,info. use SIGUSR1 to toggle log level")
	rootCmd.PersistentFlags().BoolVar(&stdout, "stdout", false,
		"output log to stdout, default is to log file")

	rootCmd.PersistentFlags().BoolVarP(&showVersion, "version", "v", false,
		"show bk-dbmon version")
}

var versionCmd = &cobra.Command{
	Use:   "version",
	Short: "version",
	Long:  "version info",
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Printf("bk-dbmon\n%s\n", buildinfo.VersionInfo())
	},
}

// rootCmd represents the base command when called without any subcommands
var rootCmd = &cobra.Command{
	Use: progName,
	Short: fmt.Sprintf(`bk-dbmon for mongodb
%s`, buildinfo.VersionInfo()),
	Long: fmt.Sprintf(`mongodb local crontab job,include routine_backup,heartbeat etc.
Wait each job finish,the job result would write to local file, and other program would report the result.
%s`, buildinfo.VersionInfo()),
	// Uncomment the following line if your bare application
	// has an action associated with it:
	Run: main,
}

var dbmonConf *config.DbMonConfig

// preRun 初始化 日志等级、日志输出方式、配置文件。 Servers不能为空，为空则退出
func preRun(stdout bool) {
	if stdout {
		mylog.InitLoggerStdout(logLevel == "debug")
	} else {
		mylog.InitRotateLoger(logLevel == "debug")
	}
	// get executable path
	if exePath, err := os.Executable(); err != nil {
		mylog.Logger.Fatal("get executable path", zap.Error(err))
		return
	} else {
		workDir = path.Dir(exePath)
	}

	// if clusterConfigFile is not absolute path, join workDir
	if !path.IsAbs(clusterConfigFile) {
		clusterConfigFile = path.Join(workDir, clusterConfigFile)
	}
	// if cfgFile is not absolute path, join workDir
	if !path.IsAbs(cfgFile) {
		cfgFile = path.Join(workDir, cfgFile)
	}

	var err error
	dbmonConf, err = config.NewDbMonConfig(cfgFile)
	if err != nil {
		mylog.Logger.Fatal(err.Error())
	}

	err = dbmonConf.LoadAndWatchConfig(true, mylog.Logger)
	if err != nil {
		mylog.Logger.Fatal("LoadAndWatchConfig", zap.Error(err))
	}

	config.InitClusterConfigHelper(clusterConfigFile, mylog.Logger)
	if len(dbmonConf.Config.Servers) == 0 {
		mylog.Logger.Fatal("no servers in configFile", zap.String("configFile", cfgFile))
	}
}

func main(cmd *cobra.Command, args []string) {
	defer func() {
		if r := recover(); r != nil {
			_, _ = fmt.Fprintf(os.Stderr, "%s", string(debug.Stack()))
		}
	}()
	if showVersion {
		_, _ = fmt.Fprintf(os.Stdout, "%s\n%s\n", progName, buildinfo.VersionInfo())
		return
	}

	preRun(stdout)
	logger := mylog.Logger
	logger.Info("bk-dbmon start",
		zap.String("workDir", workDir),
		zap.String("version", buildinfo.VersionInfoOneLine()),
		zap.String("configFile", cfgFile),
		zap.String("clusterConfigFile", clusterConfigFile))
	defer mylog.Logger.Sync()

	var err error
	// 检查DbType，只支持Mongo
	if err = checkDbType(dbmonConf.Config.Servers); err != nil {
		fmt.Printf("%s\n", err.Error())
		logger.Fatal(err.Error())
	}

	// 只允许非root用户运行
	if username := consts.GetUsername(); username == "" || username == "root" {
		logger.Fatal(fmt.Sprintf("bad username %q", username))
	}

	// 准备备份目录
	if dirs, err := new(backupjob.BackupJob).PrepareDir(); err != nil {
		logger.Fatal(fmt.Sprintf("PrepareDir err: %q", err.Error()))
	} else {
		logger.Info(fmt.Sprintf("PrepareDir success, dir:%s", dirs))
	}
	var rootWg sync.WaitGroup

	osCtx := watchSignal()
	c := cron.New(cron.WithLogger(mylog.AdapterLog))

	// 备份任务可强制退出. todo: 如何杀掉已发起的备份任务
	job1 := backupjob.NewBackupThread(dbmonConf, mylog.Logger, "backup")
	job2 := checkhealthjob.GetCheckHealthHandle(dbmonConf, mylog.Logger, "checkhealth")
	job3 := dbmonheartbeat.GetJob(dbmonConf, mylog.Logger, "heartbeat")
	// logparserjob 任务
	job4 := logparserjob.GetJob(dbmonConf, mylog.Logger, "logparser", osCtx, &rootWg)
	job5 := dstatjob.GetJob(dbmonConf, mylog.Logger, "dstat", workDir)
	job6 := datadirjob.GetJob(dbmonConf, mylog.Logger, "datadir")
	job7 := dbtablesizejob.GetJob(dbmonConf, mylog.Logger, "dbtablesize")
	for _, row := range []struct {
		job  cron.Job
		cron string
		name string
	}{
		{job: job1, cron: "@every 1m", name: job1.Name},
		{job: job2, cron: "@every 1m", name: job2.Name},
		{job: job3, cron: "@every 1m", name: job3.Name},
		{job: job4, cron: "@every 1m", name: job4.Name},
		{job: job5, cron: "@every 2m", name: job5.Name}, // dstat 任务间隔为2分钟
		{job: job6, cron: "@every 5m", name: job6.Name},
		{job: job7, cron: "@every 10m", name: job7.Name},
	} {
		if entryID, err := c.AddJob(row.cron,
			cron.NewChain(cron.SkipIfStillRunning(mylog.AdapterLog)).Then(row.job)); err == nil {
			logger.Info("AddJob success",
				zap.String("job", row.name),
				zap.Int64("entryID", int64(entryID)))
		} else {
			logger.Panic("AddJob failed",
				zap.String("job", row.name),
				zap.Int64("entryID", int64(entryID)), zap.Error(err))
			return
		}
	}

	logger.Info(fmt.Sprintf("Listen:%s", dbmonConf.Config.HttpAddress))
	c.Start()
	rootWg.Add(1)
	go httpapi.StartListen(dbmonConf.Config, &rootWg, osCtx)
	rootWg.Wait()
	logger.Info("bk-dbmon exit")
	logger.Sync()
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

// watchSignal 监听信号
func watchSignal() context.Context {
	mylog.Logger.Info("signal.Notify SIGUSR1 SIGUSR2 SIGABRT")
	// 创建可取消的 Context
	ctx, cancel := context.WithCancel(context.Background())
	// defer cancel()
	signalCh := make(chan os.Signal, 1)
	signal.Notify(signalCh, syscall.SIGUSR1, syscall.SIGUSR2, syscall.SIGABRT)

	// 启动一个协程处理信号
	go func() {
		for {
			select {
			case sig := <-signalCh:
				mylog.Logger.Info("receive signal.", zap.String("signal", sig.String()))
				if sig == syscall.SIGUSR2 {
					// SIGUSR2 用于切换日志级别
					mylog.ToggleLogLevel()
				} else {
					// SIGUSR1 和 SIGABRT 用于取消 context
					time.Sleep(100 * time.Millisecond) // 待0.1秒再发送取消信号
					cancel()                           // 广播取消信号
				}
			case <-ctx.Done():
				return
			}
		}
	}()
	return ctx
}
