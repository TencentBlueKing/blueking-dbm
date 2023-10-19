// Package cmd 根目录
/*
Copyright © 2022 NAME HERE <EMAIL ADDRESS>

*/
package cmd

import (
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobmanager"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
	"encoding/base64"
	"fmt"
	"log"
	"os"
	"strings"

	"github.com/spf13/cobra"
)

var uid string
var rootID string
var nodeID string
var versionID string
var dataDir string
var backupDir string
var payLoad string
var payLoadFormat string
var payLoadFile string
var atomJobList string
var user string
var group string
var multiProcessConcurrency int

var showSupportedAtomJobs bool

// RootCmd represents the base command when called without any subcommands
var RootCmd = &cobra.Command{
	Use:   "dbactuator_redis",
	Short: "redis原子任务合集",
	Long:  `redis原子任务合集,包含Redis 以及 RedisProxy 安装、集群创建、备份、回档等等原子任务`,
	// Uncomment the following line if your bare application
	// has an action associated with it:
	Run: func(cmd *cobra.Command, args []string) {
		var err error
		dir, _ := util.GetCurrentDirectory()

		// payLoadFile 数据构造的时候使用的
		// 解决命令行参数超限问题:./dbactuator_redis: Argument list too long 问题
		if payLoad == "" && payLoadFile != "" {
			if o, err := os.ReadFile(payLoadFile); err == nil {
				payLoad = base64.StdEncoding.EncodeToString(o)
				log.Printf("using payload file %s", payLoadFile)
			} else {
				log.Printf("using payload file %s err %v", payLoadFile, err)
			}
		}

		manager, err := jobmanager.NewJobGenericManager(uid, rootID, nodeID, versionID,
			payLoad, payLoadFormat, atomJobList, dir, multiProcessConcurrency)
		if err != nil {
			return
		}
		if showSupportedAtomJobs {
			names := manager.SupportAtomJobs()
			fmt.Printf("Support atom jobs:%s\n", strings.Join(names, "\n"))
			return
		}

		err = consts.SetRedisDataDir(dataDir)
		if err != nil {
			log.Println(err.Error())
			os.Exit(-1)
		}
		err = consts.SetRedisBakcupDir(backupDir)
		if err != nil {
			log.Println(err.Error())
			os.Exit(-1)
		}

		// 设置mongo环境变量
		err = consts.SetMongoDataDir(dataDir)
		if err != nil {
			log.Println(err.Error())
			os.Exit(-1)
		}
		err = consts.SetMongoBackupDir(backupDir)
		if err != nil {
			log.Println(err.Error())
			os.Exit(-1)
		}

		err = consts.SetProcessUser(user)
		if err != nil {
			log.Println(err.Error())
			os.Exit(-1)
		}
		err = consts.SetProcessUserGroup(group)
		if err != nil {
			log.Println(err.Error())
			os.Exit(-1)
		}

		err = manager.LoadAtomJobs()
		if err != nil {
			os.Exit(-1)
		}
		err = manager.RunAtomJobs()
		if err != nil {
			os.Exit(-1)
		}
	},
}

// Execute adds all child commands to the root command and sets flags appropriately.
// This is called by main.main(). It only needs to happen once to the rootCmd.
func Execute() {
	err := RootCmd.Execute()
	if err != nil {
		os.Exit(1)
	}
}

func init() {
	// Here you will define your flags and configuration settings.
	// Cobra supports persistent flags, which, if defined here,
	// will be global for your application.

	// Cobra also supports local flags, which will only run
	// when this action is called directly.
	RootCmd.Flags().BoolP("toggle", "t", false, "Help message for toggle")
	RootCmd.PersistentFlags().BoolVarP(&showSupportedAtomJobs, "show-supported-atomjobs", "s", false,
		"show supported atom jobs")
	RootCmd.PersistentFlags().StringVarP(&uid, "uid", "U", "", "单据id")
	RootCmd.PersistentFlags().StringVarP(&rootID, "root_id", "R", "", "流程id")
	RootCmd.PersistentFlags().StringVarP(&nodeID, "node_id", "N", "", "节点id")
	RootCmd.PersistentFlags().StringVarP(&versionID, "version_id", "V", "", "运行版本id")
	RootCmd.PersistentFlags().StringVarP(&dataDir, "data_dir", "D", "",
		"数据保存路径,亦可通过环境变量 REDIS_DATA_DIR 指定")
	RootCmd.PersistentFlags().StringVarP(&backupDir, "backup_dir", "B", "",
		"备份保存路径,亦可通过环境变量REDIS_BACKUP_DIR指定")
	RootCmd.PersistentFlags().StringVarP(&payLoad, "payload", "p", "", "原子任务参数信息,base64包裹")
	RootCmd.PersistentFlags().StringVarP(&payLoadFormat, "payload-format", "m", "",
		"command payload format, default base64, value_allowed: base64|raw")
	RootCmd.PersistentFlags().StringVarP(&atomJobList, "atom-job-list", "A", "",
		"多个原子任务名用','分割,如 redis_install,redis_replicaof")
	RootCmd.PersistentFlags().StringVarP(&payLoadFile, "payload_file", "f", "", "原子任务参数信息,json文件")
	RootCmd.PersistentFlags().StringVarP(&user, "user", "u", "", "开启进程的os用户")
	RootCmd.PersistentFlags().StringVarP(&group, "group", "g", "", "开启进程的os用户属主")
	RootCmd.PersistentFlags().IntVarP(&multiProcessConcurrency, "multi-process-concurrency", "C", 2, "多进程并发数,默认2")
}
