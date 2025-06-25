package tools

import (
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/pkg/mymongo"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/toolkit/pitr"
	"os"

	log "github.com/sirupsen/logrus"
	"github.com/spf13/cobra"
)

// Command definition for PITR (Point-In-Time Recovery) recovery operation
var (
	recoverCmd = &cobra.Command{
		Use:   "recover",
		Short: "recover",
		Long:  `pitr recover`,
		Run: func(cmd *cobra.Command, args []string) {
			recoverMain()
		},
	}
)

/*
Recover PITR backup. This command executes mongorestore locally to restore backup files.
The recovery process follows these steps:
1. First imports the full backup
2. Then imports incremental backups in sequence
*/

// Global variables for command line flags
var src string
var recoverTimeStr string

// init initializes the command line flags for the recover command
func init() {
	recoverCmd.Flags().StringVar(&host, "host", "127.0.0.1", "host")
	recoverCmd.Flags().StringVar(&port, "port", "27017", "port")
	recoverCmd.Flags().StringVar(&authDb, "authdb", "admin", "authdb")
	recoverCmd.Flags().StringVar(&user, "user", "xxx", "xxx")
	recoverCmd.Flags().StringVar(&pass, "pass", "xxx", "xxx")
	recoverCmd.Flags().StringVar(&backupType, "type", "", "FULL INCR AUTO")
	recoverCmd.Flags().BoolVar(&dryRun, "dryRun", false, "测试模式")
	recoverCmd.Flags().StringVar(&dir, "dir", ".", "")
	recoverCmd.Flags().StringVar(&addr, "addr", "127.0.0.1:6997", "用于确保只有一个mongotoolkit在运行")
	recoverCmd.Flags().StringVar(&src, "src", "", "src mongodb instance, ip:port")
	recoverCmd.Flags().StringVar(&recoverTimeStr, "recover-time", "", "recoverTime yyyy-mm-ddTHH:MM:SS")
	recoverCmd.Flags().StringVar(&logLevel, "logLevel", "info", "logLevel")
	rootCmd.AddCommand(recoverCmd)
}

// recoverMain is the main function that orchestrates the PITR recovery process
func recoverMain() {
	//TODO check args
	initLog()
	printVersion()

	// Parse and validate recovery time
	recoverTime, err := pitr.ParseTimeStr(recoverTimeStr)
	if recoverTime == 0 || err != nil {
		pitr.ExitFailed("bad recoverTime format error (%s), require format '2006-01-02T15:04:05'", recoverTimeStr)
		os.Exit(1)
	}

	// Initialize connection to target MongoDB
	dstConn := mymongo.NewMongoHost(host, port, authDb, user, pass, "", "")
	log.Printf("TODO: check dst connect ok and dst db is empty")

	// Check for required dependencies 其它工具在mongotools目录下. 不在这里检查
	depOk := prepareDep([]string{"mongo"})
	if !depOk && !dryRun {
		pitr.ExitFailed("exit, because some dep not exists")
		os.Exit(1)
	}

	// Get MongoDB version and appropriate mongorestore binary
	version, err := pitr.GetVersion(dstConn)
	if err != nil {
		pitr.ExitFailed("get version failed, err: %v", err)
		os.Exit(1)
	}

	log.Printf("get version %v err %v", version, err)
	mongoRestoreBin, err := pitr.GetMongoRestoreBin(version)
	if err != nil {
		pitr.ExitFailed("get mongoRestoreBin failed, err: %v", err)
		os.Exit(1)
	}

	// Find and process all backup files for the source instance
	_, fileObjList, err := getFiles(dir, src)
	if err != nil {
		pitr.ExitFailed("Read Dir %s failed, error: %s", dir, err.Error())
		os.Exit(1)
	}

	// Log backup file details
	for i := 0; i < len(fileObjList); i++ {
		log.Debugf("get file: %d %s  %d [%s]",
			i, fileObjList[i].Type, fileObjList[i].V0IncrSeq, fileObjList[i].FileName)
	}

	pitr.Output("recoverTime:%s unix:%d", recoverTimeStr, recoverTime)

	// Find required backup files for recovery
	full, incrList, err := pitr.FindNeedFiles(fileObjList, recoverTime)
	if err != nil || full == nil {
		pitr.ExitFailed("FindNeedFiles Failed, err: %s", err.Error())
	}

	log.Printf("FindNeedFiles Succ")
	log.Printf("FULL: %s", full.FileName)
	for _, file := range incrList {
		log.Printf("INCR: %s", file.FileName)
	}

	// Exit if in dry run mode
	if dryRun {
		log.Printf("done, dryRun Mode, skip send recover req to backupSys")
		os.Exit(0)
	}

	lockHandle, err := getLock("pit_recover", port)
	if err != nil {
		log.Fatalf("get lock failed, err: %v, opType: %s, port: %s", err, "pit_recover", port)
	} else {
		log.Infof("get lock success, opType: %s, port: %s", "pit_recover", port)
	}

	// Execute the recovery process
	if err = pitr.DoRecover(mongoRestoreBin, dstConn, full, incrList, recoverTime, dir); err == nil {
		pitr.ExitSuccess("DoRecover Success")
	} else {
		pitr.ExitFailed("DoRecover failed, error: %s", err.Error())
	}

	err = lockHandle.Unlock()
	if err != nil {
		log.Warnf("unlock failed, err: %v, opType: %s, port: %s", err, "pit_recover", port)
	} else {
		log.Infof("unlock success, opType: %s, port: %s", "pit_recover", port)
	}
}

// getFiles retrieves all backup files from the specified directory and parses their backup information.
// It only returns files associated with the specified source instance.
// Parameters:
//   - dirPath: directory path containing backup files
//   - srcInstance: source MongoDB instance identifier (can be instance name or host:port)
//
// Returns:
//   - files: list of filenames
//   - fileObjList: list of parsed backup file objects
//   - err: error if any
func getFiles(dirPath string, srcInstance string) (files []string, fileObjList []*pitr.BackupFileName, err error) {
	entries, err := os.ReadDir(dirPath)
	if err != nil {
		return nil, nil, err
	}
	for _, fi := range entries {
		if fi.IsDir() { // 忽略 目录
			continue
		} else {
			files = append(files, fi.Name())
		}
	}
	for _, file := range files {
		fileObj, err := pitr.DecodeFilename(file)
		if err != nil {
			log.Debugf("skip file %s, err: %v", file, err)
			continue
		} else {
			log.Debugf("read fileObj %+v", fileObj)
			if srcInstance == fileObj.Name || srcInstance == fileObj.Host+":"+fileObj.Port {
				fileObjList = append(fileObjList, fileObj)
			}
		}
	}
	return files, fileObjList, nil
}

// prepareDep checks for the existence of required dependency tools in the system.
// It also ensures the tool path is properly set in the environment.
// Parameters:
//   - depList: list of required dependency tools
//
// Returns:
//   - bool: true if all dependencies exist, false otherwise
func prepareDep(depList []string) bool {
	depOk := true
	for _, dep := range depList {
		if !pitr.CommandExists(dep) {
			pitr.Output("dep tool '%s' not exists", dep)
			depOk = false
		}
	}
	return depOk
}
