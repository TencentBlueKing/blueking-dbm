package cmd

import (
	"fmt"
	"io"
	"os"
	"path"
	"sync"

	"dbm-services/mysql/db-tools/mysql-crond/pkg/config"
	"dbm-services/mysql/db-tools/mysql-crond/pkg/crond"
	"dbm-services/mysql/db-tools/mysql-crond/pkg/service"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
	"golang.org/x/exp/slog"
	"gopkg.in/natefinch/lumberjack.v2"
)

var (
	m sync.Mutex
)

var rootCmd = &cobra.Command{
	Use:   "mysql-crond",
	Short: "mysql-crond",
	RunE: func(cmd *cobra.Command, args []string) error {
		err := config.InitConfig(viper.GetString("config"))
		if err != nil {
			slog.Error("start crond", err)
			return err
		}

		initLogger()

		pidFile := path.Join(
			config.RuntimeConfig.PidPath, fmt.Sprintf("%s.pid", ExecutableName),
		)
		pf, err := os.Create(pidFile)
		if err != nil {
			slog.Error("start crond", err)
			return err
		}
		err = os.Chown(pidFile, config.JobsUserUid, config.JobsUserGid)
		if err != nil {
			slog.Error("start crond", err)
			return err
		}
		err = os.Truncate(pidFile, 0)
		if err != nil {
			slog.Error("start crond", err)
			return err
		}
		_, err = io.WriteString(pf, fmt.Sprintf("%d\n", os.Getpid()))
		if err != nil {
			slog.Error("start crond", err)
			return err
		}

		quit := make(chan struct{})

		go func() {
			<-quit
			//time.Sleep(10 * time.Second)
			//crond.Stop()
			slog.Info("quit mysql-crond")
			os.Exit(0)
		}()

		err = crond.Start()
		if err != nil {
			slog.Error("start crond", err)
			return err
		}

		err = service.Start(version, buildStamp, gitHash, quit, &m)
		if err != nil {
			slog.Error("start http server", err)
			return err
		}

		return nil
	},
}

// Execute TODO
func Execute() {
	err := rootCmd.Execute()
	if err != nil {
		slog.Error("start", err)
		os.Exit(1)
	}
}

func initLogger() {
	var ioWriters []io.Writer

	if config.RuntimeConfig.Log.Console {
		ioWriters = append(ioWriters, os.Stdout)
	}

	if config.RuntimeConfig.Log.LogFileDir != nil {
		if !path.IsAbs(*config.RuntimeConfig.Log.LogFileDir) {
			err := fmt.Errorf("log_file_dir need absolute dir")
			panic(err)
		}

		err := os.MkdirAll(*config.RuntimeConfig.Log.LogFileDir, 0755)
		if err != nil {
			panic(err)
		}
		err = os.Chown(*config.RuntimeConfig.Log.LogFileDir, config.JobsUserUid, config.JobsUserGid)
		if err != nil {
			panic(err)
		}

		logFile := path.Join(*config.RuntimeConfig.Log.LogFileDir, fmt.Sprintf("%s.log", ExecutableName))
		_, err = os.Stat(logFile)
		if err != nil {
			if os.IsNotExist(err) {
				_, err := os.Create(logFile)
				if err != nil {
					panic(err)
				}
				err = os.Chown(logFile, config.JobsUserUid, config.JobsUserGid)
				if err != nil {
					panic(err)
				}
			} else {
				panic(err)
			}
		}

		ioWriters = append(ioWriters, &lumberjack.Logger{Filename: logFile})
	}

	handleOpt := slog.HandlerOptions{
		AddSource: config.RuntimeConfig.Log.Source,
	}

	if config.RuntimeConfig.Log.Debug {
		handleOpt.Level = slog.LevelDebug
	} else {
		handleOpt.Level = slog.LevelInfo
	}

	var logger *slog.Logger
	if config.RuntimeConfig.Log.Json {
		logger = slog.New(slog.NewJSONHandler(io.MultiWriter(ioWriters...), &handleOpt))
	} else {
		logger = slog.New(slog.NewTextHandler(io.MultiWriter(ioWriters...), &handleOpt))
	}
	slog.SetDefault(logger)
}
