package main

import (
	"dbm-services/mysql/slow-query-parser-service/pkg/mysql"
	"dbm-services/mysql/slow-query-parser-service/pkg/service"
	"fmt"
	"os"
	"path/filepath"

	"github.com/alecthomas/kingpin/v2"
	"golang.org/x/exp/slog"
)

var (
	version    = ""
	buildStamp = ""
	gitHash    = ""
)

var (
	root = kingpin.New("slow-query-parser-service", "slow query parser service")

	runCmd          = root.Command("run", "start service")
	runCmdAddress   = runCmd.Flag("address", "service listen address").Required().Envar("SQ_ADDRESS").TCP()
	tmysqlParsePath = runCmd.Flag("tmysqlparse-bin", "tmysqlparse bin path").Required().Envar("SQ_TMYSQLPARSER_BIN").
			ExistingFile()

	versionCmd = root.Command("version", "print version")
)

func init() {
	slog.SetDefault(
		slog.New(
			slog.HandlerOptions{
				AddSource: true,
				Level:     slog.LevelDebug,
			}.NewTextHandler(os.Stdout),
		),
	)
}

func main() {
	switch kingpin.MustParse(root.Parse(os.Args[1:])) {
	case runCmd.FullCommand():
		slog.Info("init run",
			slog.String("address", (*runCmdAddress).String()),
			slog.String("tmysqlparse-bin", *tmysqlParsePath),
		)

		if !filepath.IsAbs(*tmysqlParsePath) {
			cwd, _ := os.Getwd()
			*tmysqlParsePath = filepath.Join(cwd, *tmysqlParsePath)
			slog.Info("init run concat cwd to tmysqlparse-bin", slog.String("cwd", cwd))
		}

		mysql.ParserPath = tmysqlParsePath
		service.Start((*runCmdAddress).String())
	case versionCmd.FullCommand():
		fmt.Printf("Version: %s, GitHash: %s, BuildAt: %s\n", version, gitHash, buildStamp)
	}
}
