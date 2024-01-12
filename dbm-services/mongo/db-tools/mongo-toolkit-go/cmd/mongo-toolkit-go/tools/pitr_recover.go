package tools

import (
	"dbm-services/mongo/db-tools/mongo-toolkit-go/pkg/mymongo"
	"dbm-services/mongo/db-tools/mongo-toolkit-go/toolkit/pitr"
	log "github.com/sirupsen/logrus"
	"github.com/spf13/cobra"
	"os"
	"path/filepath"
)

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

var src string
var recoverTimeStr string

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

func recoverMain() {
	//TODO check args
	initLog()
	printVersion()
	recoverTime, err := pitr.ParseTimeStr(recoverTimeStr)
	if recoverTime == 0 || err != nil {
		pitr.ExitFailed("bad recoverTime format error (%s), require format '2006-01-02T15:04:05'", recoverTimeStr)
		os.Exit(1)
	}

	dstConn := mymongo.NewMongoHost(host, port, authDb, user, pass, "", "")
	log.Printf("TODO: check dst connect ok and dst db is empty")
	// todo test dst is empty db

	// use local mongorestore mongorestore.100.7
	depList := []string{"mongorestore.100", "mongo"}
	depOk := true
	for _, dep := range depList {
		if !pitr.CommandExists(dep) {
			pitr.Output("dep tool '%s' not exists", dep)
			depOk = false
		}
	}

	if !depOk && !dryRun {
		pitr.ExitFailed("exit, because some dep not exists")
		os.Exit(1)
	}

	workdir, err := filepath.Abs(filepath.Dir(os.Args[0]))
	if err != nil {
		pitr.ExitFailed("Read Dir %s failed, error: %s", os.Args[0], err.Error())
		os.Exit(1)
	}

	pitr.BinDir = workdir
	files, err := getFiles(dir)
	if err != nil {
		pitr.ExitFailed("Read Dir %s failed, error: %s", dir, err.Error())
		os.Exit(1)
	}
	var fileObjList []*pitr.BackupFileName
	for _, file := range files {
		fileObj, err := pitr.DecodeFilename(file)
		if err != nil {
			log.Debugf("Skip file %s, err: %v", file, err)
			continue
		} else {
			log.Debugf("read fileObj %+v", fileObj)
			if src == fileObj.Name || src == fileObj.Host+":"+fileObj.Port {
				fileObjList = append(fileObjList, fileObj)
			}
		}
	}
	for i := 0; i < len(fileObjList); i++ {
		log.Debugf("get file: %d %s  %d [%s]", i, fileObjList[i].Type, fileObjList[i].V0IncrSeq, fileObjList[i].FileName)
	}
	pitr.Output("recoverTime:%s unix:%d", recoverTimeStr, recoverTime)
	full, incrList, err := pitr.FindNeedFiles(fileObjList, recoverTime)
	if err != nil || full == nil {
		pitr.ExitFailed("FindNeedFiles Failed, err: %s", err.Error())
	}
	log.Printf("FindNeedFiles Succ")
	log.Printf("FULL: %s", full.FileName)
	for _, file := range incrList {
		log.Printf("INCR: %s", file.FileName)
	}
	if dryRun {
		log.Printf("done, dryRun Mode, skip send recover req to backupSys")
		os.Exit(0)
	}
	// Do Recover
	if err := pitr.DoRecover(dstConn, full, incrList, recoverTime, dir); err == nil {
		pitr.ExitSuccess("DoRecover Success")
	} else {
		pitr.ExitFailed("DoRecover failed, error: %s", err.Error())
	}

}

func getFiles(dirPth string) (files []string, err error) {
	entries, err := os.ReadDir(dirPth)
	if err != nil {
		return nil, err
	}
	for _, fi := range entries {
		if fi.IsDir() { // 忽略 目录
			continue
		} else {
			files = append(files, fi.Name())
		}
	}
	return files, nil
}
