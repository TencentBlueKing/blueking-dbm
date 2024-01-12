package tools

import (
	"fmt"
	"github.com/natefinch/lumberjack"
	log "github.com/sirupsen/logrus"
	"github.com/spf13/cobra"
	"io"
	"os"
)

var (
	host, port, user, pass, authDb string
	backupType                     string
	fullFreq, incrFreq             uint64
	dir                            string
	nodeIp                         string
	gzip                           bool
	addr                           string
	dryRun                         bool
	logFile                        string
	logLevel                       string

	rootCmd = &cobra.Command{
		Use:   "mongo-toolkit-go",
		Short: "mongo-toolkit-go"}
)

func init() {
	rootCmd.PersistentFlags().StringVar(&logFile, "logFile", "", "log file, default stdout ")
	rootCmd.PersistentFlags().StringVar(&logLevel, "logLevel", "info", "log level, debug, info, warn, error, fatal, panic")
	log.SetFormatter(&log.JSONFormatter{})
}

func initLog() {
	// logFile := path.Join(logFile)
	if logLevel == "debug" {
		log.SetLevel(log.DebugLevel)
	} else if logLevel == "info" {
		log.SetLevel(log.InfoLevel)
	} else if logLevel == "warn" {
		log.SetLevel(log.WarnLevel)
	} else if logLevel == "error" {
		log.SetLevel(log.ErrorLevel)
	} else if logLevel == "fatal" {
		log.SetLevel(log.FatalLevel)
	} else if logLevel == "panic" {
		log.SetLevel(log.PanicLevel)
	}

	if logFile != "" {
		fmt.Printf("save log to %s, logLevel %s\n", logFile, logLevel)
		log.SetOutput(
			io.MultiWriter(
				&lumberjack.Logger{
					Filename:   logFile,
					MaxSize:    10,
					MaxBackups: 3,
					MaxAge:     7,
					Compress:   false,
				},
			))
	} else {
		log.SetReportCaller(true)
		log.SetOutput(
			io.MultiWriter(
				os.Stdout,
			))
		fmt.Printf("save log to %s, logLevel %s\n", "stdout", logLevel)
	}

}

// Execute rootCmd Main
func Execute(version, buildDate, commitSha1, goVersion string) {
	Version = version
	BuildDate = buildDate
	CommitSha1 = commitSha1
	BuildGolang = goVersion
	rootCmd.ParseFlags(os.Args)
	if err := rootCmd.Execute(); err != nil {
		fmt.Println(err)
	}
}
