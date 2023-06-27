package main

import (
	"flag"
	"fmt"
	"log"
	"os"
	"runtime/debug"
	"sync"

	"dbm-services/redis/redis-dts/config"
	"dbm-services/redis/redis-dts/pkg/constvar"
	"dbm-services/redis/redis-dts/pkg/dtsJob"
	"dbm-services/redis/redis-dts/pkg/osPerf"
	"dbm-services/redis/redis-dts/tclog"
	"dbm-services/redis/redis-dts/util"

	"github.com/spf13/viper"
)

func main() {
	defer func() {
		if r := recover(); r != nil {
			fmt.Fprintf(os.Stderr, "%s", string(debug.Stack()))
		}
	}()

	cfgFile := flag.String("config-file", "./config.yaml", "Input your config file")
	showVersion := flag.Bool("version", false, "Output version and exit.")
	showHelp := flag.Bool("help", false, "Show help message.")

	flag.Parse()

	if *showVersion {
		fmt.Println(constvar.TendisDTSVersion)
		return
	}
	if *showHelp {
		printHelp()
		return
	}
	if *cfgFile == "" {
		fmt.Println("[-config-file string] is required")
		printHelp()
		os.Exit(1)
	}

	if _, err := os.Stat(*cfgFile); err != nil {
		fmt.Printf("config file %s not exist\n", *cfgFile)
		os.Exit(1)
	}

	config.InitConfig(cfgFile)
	tclog.InitMainlog()
	// mysql.DB.Init() //连接MySQL

	debug := viper.GetBool("TENDIS_DEBUG")
	tclog.Logger.Info(fmt.Sprintf("TENDIS_DEBUG:%v", debug))

	env := viper.GetString("ENV")
	tclog.Logger.Info(fmt.Sprintf("ENV:%s", env))

	wg := &sync.WaitGroup{}
	localIP, err := util.GetLocalIP()
	if err != nil {
		log.Fatal(err)
	}

	go func() {
		osPerf.WatchDtsSvrPerf()
	}()

	jobers := make([]dtsJob.DtsJober, 0, 3)
	jobers = append(jobers, dtsJob.NewTendisSSDDtsJob(constvar.GetBkCloudID(), localIP,
		constvar.GetZoneName(), tclog.Logger, wg))
	jobers = append(jobers, dtsJob.NewTendisplusDtsJob(constvar.GetBkCloudID(), localIP,
		constvar.GetZoneName(), tclog.Logger, wg))
	jobers = append(jobers, dtsJob.NewRedisCacheDtsJob(constvar.GetBkCloudID(), localIP,
		constvar.GetZoneName(), tclog.Logger, wg))

	for _, jober := range jobers {
		jober.StartBgWorkers()
	}
	wg.Wait()
}

func printHelp() {
	fmt.Println("Usage: redis_dts_server [options]")
	fmt.Println("Options:")
	fmt.Println("  -config-file string")
	fmt.Println("        Input your config file (default \"./config.yaml\")")
	fmt.Println("  -version")
	fmt.Println("        Output version and exit.")
	fmt.Println("  -help")
	fmt.Println("        Show help message.")
}
