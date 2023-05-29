package main

import (
	"dbm-services/redis/redis-dts/config"
	"dbm-services/redis/redis-dts/pkg/constvar"
	"dbm-services/redis/redis-dts/pkg/dtsJob"
	"dbm-services/redis/redis-dts/pkg/osPerf"
	"dbm-services/redis/redis-dts/tclog"
	"dbm-services/redis/redis-dts/util"
	"fmt"
	"log"
	"os"
	"runtime/debug"
	"sync"

	"github.com/spf13/viper"
)

func main() {
	defer func() {
		if r := recover(); r != nil {
			fmt.Fprintf(os.Stderr, "%s", string(debug.Stack()))
		}
	}()

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

func init() {
	config.InitConfig()
	tclog.InitMainlog()
	// mysql.DB.Init() //不连接MySQL
}
