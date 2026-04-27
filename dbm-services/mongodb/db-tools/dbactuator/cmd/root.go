// Package cmd 根目录
/*
Copyright © 2022 NAME HERE <EMAIL ADDRESS>

*/
package cmd

import (
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/pkg/buildinfo"
	"encoding/base64"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strings"

	"github.com/pkg/errors"

	"dbm-services/mongodb/db-tools/dbactuator/mylog"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/common"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/consts"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/jobmanager"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

var uid string
var rootID string
var nodeID string
var versionID string
var dataDir string
var backupDir string
var binDir string
var payLoad string
var payLoadFormat string
var payLoadFile string
var atomJobList string
var user string
var group string
var printParamJson string
var listJob bool
var debugPs bool

// debugGetPidByPort <= 0 means flag not used (default -1).
var debugGetPidByPort int = -1

// debugStepDownPort <= 0 means flag not used (default -1).
var debugStepDownPort int = -1
var debugStepDownIP string = "127.0.0.1"
var debugStepDownUser string
var debugStepDownPass string

func exitWithError(err error) {
	log.Println("err:", err)
	fmt.Println(buildinfo.VersionInfoOneLine())
	os.Exit(-1)
}

func initEnv() error {
	var err error
	// 设置mongo环境变量
	err = consts.SetMongoDataDir(dataDir)
	if err != nil {
		return errors.Wrap(err, "SetMongoDataDir")
	}
	err = consts.SetMongoBackupDir(backupDir)
	if err != nil {
		return errors.Wrap(err, "SetMongoBackupDir")
	}
	err = consts.SetMongoBinDir(binDir)
	if err != nil {
		return errors.Wrap(err, "SetMongoBinDir")
	}

	err = consts.SetProcessUser(user)
	if err != nil {
		return errors.Wrap(err, "SetProcessUser")
	}
	err = consts.SetProcessUserGroup(group)
	if err != nil {
		return errors.Wrap(err, "SetProcessUserGroup")
	}
	return nil
}

// RootCmd represents the base command when called without any subcommands
var RootCmd = &cobra.Command{
	Use:   "mongo-dbactuator",
	Short: "mongo原子任务合集",
	Long:  `mongo原子任务合集,包含mongo复制集、cluster的创建，备份，回档等等原子任务。`,
	// Uncomment the following line if your bare application
	// has an action associated with it:
	Run: func(cmd *cobra.Command, args []string) {
		var err error
		dir, _ := util.GetCurrentDirectory()

		// 优先使用payLoad
		if payLoad == "" && payLoadFile != "" {
			if o, err := os.ReadFile(payLoadFile); err == nil {
				payLoad = base64.StdEncoding.EncodeToString(o)
				log.Printf("using payload file %s", payLoadFile)
			} else {
				log.Printf("using payload file %s err %v", payLoadFile, err)
			}
		}
		// 设置mongo环境
		if err = initEnv(); err != nil {
			exitWithError(err)
		}
		manager, err := jobmanager.NewJobGenericManager(uid, rootID, nodeID, versionID,
			payLoad, payLoadFormat, atomJobList, dir)
		if err != nil {
			exitWithError(err)
		}
		manager.PrintVersion(buildinfo.VersionInfoOneLine()) // 打印版本信息
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

var debugCmd = &cobra.Command{
	Use:   "debug",
	Short: "debug",
	Long:  `debug`,
	Run: func(cmd *cobra.Command, args []string) {
		if listJob {
			dir, _ := util.GetCurrentDirectory()
			if manager, err := jobmanager.NewJobGenericManager(uid, rootID, nodeID, versionID,
				payLoad, payLoadFormat, atomJobList, dir); err != nil {
				panic(err)
			} else {
				manager.RegisterAtomJob()
				for _, r := range manager.GetJobNameList() {
					fmt.Printf("%s\n", r)
				}
			}
			os.Exit(0)
		} else if debugPs {
			if p, err := util.ListProcess(); err != nil {
				fmt.Printf("err %s\n", err.Error())
			} else {
				for _, r := range p {
					fmt.Printf("%+v\n", r)
				}
			}
			os.Exit(0)
		} else if debugGetPidByPort > 0 {
			pid, comm, err := common.GetMongoPidAndNameByPort(debugGetPidByPort)
			if err != nil {
				fmt.Fprintf(os.Stderr, "GetMongoPidAndNameByPort(%d) error: %v\n", debugGetPidByPort, err)
				os.Exit(1)
			}
			if pid == 0 {
				fmt.Printf("port=%d: no TCP LISTEN (GetMongoPidAndNameByPort returned pid=0)\n", debugGetPidByPort)
			} else {
				fmt.Printf("port=%d pid=%d comm=%q\n", debugGetPidByPort, pid, comm)
			}
			os.Exit(0)
		} else if debugStepDownPort > 0 {
			// stepDown path uses util.RunBashCmd -> util.RunLocalCmd -> mylog.Logger.*.
			// Debug mode does not create jobruntime logger, so initialize a lightweight default logger here.
			if mylog.Logger == nil {
				mylog.UnitTestInitLog()
			}
			if (debugStepDownUser == "" && debugStepDownPass != "") ||
				(debugStepDownUser != "" && debugStepDownPass == "") {
				fmt.Fprintln(os.Stderr, "debug --stepdown requires both --stepdown-user and --stepdown-pass, or neither")
				os.Exit(1)
			}
			mongoBinRoot := binDir
			if mongoBinRoot == "" {
				mongoBinRoot = consts.GetMongoBinDir()
			}
			mongoBin := filepath.Join(mongoBinRoot, "mongodb", "bin", "mongo")
			var (
				ok  bool
				err error
			)
			if debugStepDownUser != "" {
				ok, err = common.AuthRsStepDown(mongoBin, debugStepDownIP, debugStepDownPort, debugStepDownUser, debugStepDownPass)
			} else {
				ok, err = common.NoAuthRsStepDown(mongoBin, debugStepDownIP, debugStepDownPort)
			}
			if err != nil {
				if strings.Contains(err.Error(), "get primary info timeout") {
					fmt.Printf(
						"stepDown command sent: ip=%s port=%d, primary verify timeout (%v)\n",
						debugStepDownIP, debugStepDownPort, err)
					os.Exit(0)
				}
				fmt.Fprintf(os.Stderr, "stepDown failed: ip=%s port=%d err=%v\n", debugStepDownIP, debugStepDownPort, err)
				os.Exit(1)
			}
			if ok {
				fmt.Printf("stepDown success: ip=%s port=%d, primary switched\n", debugStepDownIP, debugStepDownPort)
			} else {
				fmt.Printf("stepDown executed: ip=%s port=%d, node still primary\n", debugStepDownIP, debugStepDownPort)
			}
			os.Exit(0)
		} else if printParamJson != "" {
			doPrintParamJson()
		} else {
			fmt.Printf("%s", buildinfo.VersionInfo())
			cmd.Help()
		}
	},
}

func init() {
	// Here you will define your flags and configuration settings.
	// Cobra supports persistent flags, which, if defined here,
	// will be global for your application.

	// Cobra also supports local flags, which will only run
	// when this action is called directly.
	RootCmd.Flags().BoolP("toggle", "t", false, "Help message for toggle")
	RootCmd.PersistentFlags().StringVarP(&uid, "uid", "U", "", "单据id")
	RootCmd.PersistentFlags().StringVarP(&rootID, "root_id", "R", "", "流程id")
	RootCmd.PersistentFlags().StringVarP(&nodeID, "node_id", "N", "", "节点id")
	RootCmd.PersistentFlags().StringVarP(&versionID, "version_id", "V", "", "运行版本id")
	RootCmd.PersistentFlags().StringVarP(&dataDir, "data_dir", "D", "",
		"数据保存路径,亦可通过环境变量 REDIS_DATA_DIR 指定")
	RootCmd.PersistentFlags().StringVarP(&backupDir, "backup_dir", "B", "",
		"备份保存路径,亦可通过环境变量REDIS_BACKUP_DIR指定")
	RootCmd.PersistentFlags().StringVar(&binDir, "bin_dir", "",
		"Mongo二进制安装根路径,亦可通过环境变量 MONGO_BIN_DIR 指定,默认 /usr/local")
	RootCmd.PersistentFlags().StringVarP(&payLoad, "payload", "p", "", "原子任务参数信息,base64包裹")
	RootCmd.PersistentFlags().StringVarP(&payLoadFormat, "payload-format", "m", "",
		"command payload format, default base64, value_allowed: base64|raw")
	RootCmd.PersistentFlags().StringVarP(&atomJobList, "atom-job-list", "A", "",
		"多个原子任务名用','分割,如 redis_install,redis_replicaof")
	RootCmd.PersistentFlags().StringVarP(&payLoadFile, "payload_file", "f", "", "原子任务参数信息,json文件")
	RootCmd.PersistentFlags().StringVarP(&user, "user", "u", "", "开启进程的os用户")
	RootCmd.PersistentFlags().StringVarP(&group, "group", "g", "", "开启进程的os用户属主")
	debugCmd.PersistentFlags().StringVarP(&printParamJson, "param", "P", "", "print atom job param")
	debugCmd.PersistentFlags().BoolVarP(&listJob, "list", "L", false, "list atom jobs")
	debugCmd.PersistentFlags().BoolVarP(&debugPs, "ps", "S", false, "list process")
	debugCmd.PersistentFlags().IntVar(&debugGetPidByPort, "get-pid-by-port", -1,
		"test common.GetMongoPidAndNameByPort for this TCP port (e.g. 27017)")
	debugCmd.PersistentFlags().IntVar(&debugStepDownPort, "stepdown", -1,
		"debug rs.stepDown on this mongo port (e.g. 27017)")
	debugCmd.PersistentFlags().StringVar(&debugStepDownIP, "stepdown-ip", "127.0.0.1",
		"ip used by debug --stepdown")
	debugCmd.PersistentFlags().StringVar(&debugStepDownUser, "stepdown-user", "",
		"admin username used by debug --stepdown (optional)")
	debugCmd.PersistentFlags().StringVar(&debugStepDownPass, "stepdown-pass", "",
		"admin password used by debug --stepdown (optional)")

	RootCmd.AddCommand(debugCmd)

}

func doPrintParamJson() {
	dir, _ := util.GetCurrentDirectory()
	if manager, err := jobmanager.NewJobGenericManager(uid, rootID, nodeID, versionID,
		payLoad, payLoadFormat, printParamJson, dir); err != nil {
		panic(err)
	} else {
		err = manager.LoadAtomJobs()
		if err != nil {
			fmt.Printf("err %s\n", err.Error())
			os.Exit(1)
		}
		r := manager.GetAtomJobInstance(printParamJson)
		fmt.Printf("%s\n", r.Param())
	}
	os.Exit(0)
}

// Execute adds all child commands to the root command and sets flags appropriately.
// This is called by main.main(). It only needs to happen once to the rootCmd.
func Execute() {
	err := RootCmd.Execute()
	if err != nil {
		os.Exit(1)
	}
}
