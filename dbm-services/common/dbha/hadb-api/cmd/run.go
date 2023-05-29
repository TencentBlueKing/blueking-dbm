// Package cmd TODO
/*
Copyright © 2022 NAME HERE <EMAIL ADDRESS>

*/
package cmd

import (
	"dbm-services/common/dbha/hadb-api/initc"
	"dbm-services/common/dbha/hadb-api/log"
	"dbm-services/common/dbha/hadb-api/pkg/handler"
	"dbm-services/common/dbha/hadb-api/util"

	"github.com/spf13/cobra"
	"github.com/valyala/fasthttp"
)

// runCmd represents the run command
var runCmd = &cobra.Command{
	Use:   "run",
	Short: "A brief description of your command",
	Long: `A longer description that spans multiple lines and likely contains examples
and usage of using your command. For example:

Cobra is a CLI library for Go that empowers applications.
This application is a tool to generate the needed files
to quickly create a Cobra application.`,
	Run: StartApiServer,
}

func init() {
	rootCmd.AddCommand(runCmd)

	// Here you will define your flags and configuration settings.

	// Cobra supports Persistent Flags which will work for this command
	// and all subcommands, e.g.:
	// runCmd.PersistentFlags().String("foo", "", "A help for foo")

	// Cobra supports local flags which will only run when this command
	// is called directly, e.g.:
	// runCmd.Flags().BoolP("toggle", "t", false, "Help message for toggle")
}

// StartApiServer TODO
func StartApiServer(cmd *cobra.Command, args []string) {
	log.Logger.Info("start run api server...., args:", args)
	serverPort := util.DefaultServerPort
	if len(initc.GlobalConfig.NetInfo.Port) > 0 {
		serverPort = ":" + initc.GlobalConfig.NetInfo.Port
		log.Logger.Info("Set port by config.yaml,port:%s", serverPort)
	}

	log.Logger.Info("the port of http sever ", serverPort)

	router := func(ctx *fasthttp.RequestCtx) {
		url := string(ctx.Path())
		log.Logger.Debugf("url info:%s", url)
		if _, ok := handler.AddToHandlers[url]; ok {
			handler.AddToHandlers[url](ctx)
		} else {
			ctx.Error("Not found", fasthttp.StatusNotFound)
		}
	}
	if err := fasthttp.ListenAndServe(serverPort, router); err != nil {
		log.Logger.Errorf("run api server failed:%s", err.Error())
	}
}
