package main

import (
	"fmt"
	"os"
	"slow-query-parser-service/pkg/service"

	"github.com/alecthomas/kingpin/v2"
	"github.com/gin-gonic/gin"
)

var (
	version    = ""
	buildStamp = ""
	gitHash    = ""
)

var (
	root          = kingpin.New("slow-query-parser-service", "slow query parser service")
	runCmd        = root.Command("run", "start service")
	runCmdAddress = runCmd.Flag("address", "service listen address").Required().Envar("SQ_ADDRESS").TCP()
	versionCmd    = root.Command("version", "print version")
)

func main() {
	switch kingpin.MustParse(root.Parse(os.Args[1:])) {
	case runCmd.FullCommand():
		r := gin.New()
		g := r.Group("/mysql")

		g.POST("/", service.Handler)

		panic(r.Run((*runCmdAddress).String()))
	case versionCmd.FullCommand():
		fmt.Printf("Version: %s, GitHash: %s, BuildAt: %s\n", version, gitHash, buildStamp)
	}
}
