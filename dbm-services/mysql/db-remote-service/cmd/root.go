package cmd

import (
	"crypto/tls"
	"crypto/x509"
	"dbm-services/mysql/db-remote-service/pkg/config"
	"dbm-services/mysql/db-remote-service/pkg/service"
	"fmt"
	"io"
	"net/http"
	"os"
	"path"
	"path/filepath"

	"github.com/gin-gonic/gin"
	"github.com/spf13/cobra"
	"golang.org/x/exp/slog"
	"gopkg.in/natefinch/lumberjack.v2"
)

// rootCmd represents the base command when called without any subcommands
var rootCmd = &cobra.Command{
	Use:   "start",
	Short: "start db remote service",
	Long:  `start db remote service`,
	Run: func(cmd *cobra.Command, args []string) {
		config.InitConfig()
		initLogger()

		slog.Debug("run", slog.Any("runtime config", config.RuntimeConfig))
		slog.Debug("run", slog.Any("log config", config.LogConfig))

		r := gin.Default()
		service.RegisterRouter(r)

		if config.RuntimeConfig.TLS {
			slog.Info("run in tls mode")
			s := &http.Server{
				Addr:    fmt.Sprintf(":%d", config.RuntimeConfig.Port),
				Handler: r,
				TLSConfig: &tls.Config{
					ClientCAs: func() *x509.CertPool {
						pool := x509.NewCertPool()
						ca, err := os.ReadFile(config.RuntimeConfig.CAFile)
						if err != nil {
							slog.Error("read cer file", err)
							panic(err)
						}
						pool.AppendCertsFromPEM(ca)
						return pool
					}(),
					ClientAuth: tls.RequireAnyClientCert,
				},
			}
			if err := s.ListenAndServeTLS(config.RuntimeConfig.CertFile, config.RuntimeConfig.KeyFile); err != nil {
				slog.Error("run service", err)
				os.Exit(1)
			}
		} else {
			slog.Info("run in http mode")
			if err := r.Run(fmt.Sprintf(":%d", config.RuntimeConfig.Port)); err != nil {
				slog.Error("run service", err)
				os.Exit(1)
			}
		}
	},
}

// Execute adds all child commands to the root command and sets flags appropriately.
// This is called by main.main(). It only needs to happen once to the rootCmd.
func Execute() {
	err := rootCmd.Execute()
	if err != nil {
		slog.Error("execute cobra cmd", err)
		os.Exit(1)
	}
}

func initLogger() {
	executable, _ := os.Executable()

	var ioWriters []io.Writer

	if config.LogConfig.Console {
		ioWriters = append(ioWriters, os.Stdout)
	}

	// logFileDir := viper.GetString("log_file_dir")
	if config.LogConfig.LogFileDir != "" {
		if !path.IsAbs(config.LogConfig.LogFileDir) {
			config.LogConfig.LogFileDir = filepath.Join(filepath.Dir(executable), config.LogConfig.LogFileDir)
		}

		err := os.MkdirAll(config.LogConfig.LogFileDir, 0755)
		if err != nil {
			panic(err)
		}

		logFile := path.Join(config.LogConfig.LogFileDir, fmt.Sprintf("%s.log", filepath.Base(executable)))
		_, err = os.Stat(logFile)
		if err != nil {
			if os.IsNotExist(err) {
				_, err := os.Create(logFile)
				if err != nil {
					panic(err)
				}
			} else {
				panic(err)
			}
		}

		ioWriters = append(
			ioWriters, &lumberjack.Logger{
				Filename:   logFile,
				MaxAge:     5,
				MaxBackups: 5,
			},
		)
	}

	handleOpt := slog.HandlerOptions{
		AddSource: config.LogConfig.Source,
	}

	if config.LogConfig.Debug {
		handleOpt.Level = slog.LevelDebug
	} else {
		handleOpt.Level = slog.LevelInfo
	}

	var logger *slog.Logger
	if config.LogConfig.Json {
		logger = slog.New(handleOpt.NewJSONHandler(io.MultiWriter(ioWriters...)))
	} else {
		logger = slog.New(handleOpt.NewTextHandler(io.MultiWriter(ioWriters...)))
	}
	slog.SetDefault(logger)
}
