package main

import (
	"fmt"
	"os"

	"github.com/alecthomas/kingpin/v2"

	"celery-service/pkg/config"
	"celery-service/pkg/service"
)

var (
	version    = ""
	buildStamp = ""
	gitHash    = ""
)

var (
	root               = kingpin.New("celery-service", "dbm celery task service")
	externalTaskConfig = root.Flag("external-task-config", "external tasks").Required().Envar("CS_EXTERNAL_TASK").ExistingFile()
	runCmd             = root.Command("run", "start service")
	runCmdAddress      = runCmd.Flag("address", "service listen address").Required().Envar("CS_ADDRESS").TCP()
	listCmd            = root.Command("list", "list all tasks")
	versionCmd         = root.Command("version", "print version")
)

func main() {
	switch kingpin.MustParse(root.Parse(os.Args[1:])) {
	case runCmd.FullCommand():
		err := config.LoadExternalTasks(*externalTaskConfig)
		if err != nil {
			panic(err)
		}

		err = service.Start((*runCmdAddress).String())
		if err != nil {
			panic(err)
		}
	case listCmd.FullCommand():
		err := config.LoadExternalTasks(*externalTaskConfig)
		if err != nil {
			panic(err)
		}
		service.List()
	case versionCmd.FullCommand():
		fmt.Printf("Version: %s, GitHash: %s, BuildAt: %s\n", version, gitHash, buildStamp)
	}
}
