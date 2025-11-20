package tools

import (
	"context"
	"dbm-services/mongodb/db-tools/dbmon/config"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/pkg/mymongo"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/toolkit/pitr"
	"errors"
	"fmt"
	osuser "os/user"
	"path/filepath"

	"github.com/gofrs/flock"
	log "github.com/sirupsen/logrus"
	"github.com/spf13/cobra"
)

/*
发起PITR备份. 该命令会在本地执行mongodump命令, 生成备份文件.
BackupType 有三种类型: full, incr, auto. full表示全备, incr表示增量备份, auto表示自动备份.
全备和增量备份的区别在于, 全备会备份所有的数据, 增量备份只会备份自上次全备以来的数据.
自动备份会根据全备和增量备份的时间间隔, 自动选择全备或增量备份.
*/
var (
	backupCmd = &cobra.Command{
		Use:   "backup",
		Short: "backup",
		Long:  `pitr backup`,
		Run: func(cmd *cobra.Command, args []string) {
			backupMain()
		},
	}
)

var sendToBackupSystem bool // 是否上传到备份系统
var fullTag string          //全备文件的Tag，表示保存天数
var incrTag string          //增量备份文件的Tag，表示保存天数
var removeOldFileFirst bool
var maxDiskUsage int
var minDiskUsage int
var reportFile string
var labelsStr string
var archive bool
var numParallelCollections int

func init() {
	backupCmd.Flags().StringVar(&host, "host", "127.0.0.1", "host")
	backupCmd.Flags().StringVar(&port, "port", "27017", "port")
	backupCmd.Flags().StringVar(&authDb, "authdb", "admin", "authdb")
	backupCmd.Flags().StringVar(&user, "user", "xxx", "xxx")
	backupCmd.Flags().StringVar(&pass, "pass", "xxx", "xxx")
	backupCmd.Flags().StringVar(&backupType, "type", "", "FULL INCR AUTO")
	backupCmd.Flags().BoolVar(&dryRun, "dryRun", false, "测试模式")
	backupCmd.Flags().Uint64Var(&fullFreq, "fullFreq", 86400, "全备时间间隔，单位秒，仅在type=auto或full时有效")
	backupCmd.Flags().Uint64Var(&incrFreq, "incrFreq", 3600, "增量备份时间间隔，单位秒，仅在type=auto或incr时有效")
	backupCmd.Flags().StringVar(&dir, "dir", ".", "")
	backupCmd.Flags().StringVar(&nodeIp, "nodeip", "", "nodeip, need in k8s")
	backupCmd.Flags().BoolVar(&gzip, "zip", false, "use mongodump -- zip. if archive is true, use zstd instead of gzip")
	backupCmd.Flags().StringVar(&addr, "addr", "127.0.0.1:6997", "用于确保只有一个mongotoolkit在运行")
	backupCmd.Flags().BoolVar(&sendToBackupSystem, "send-to-bs", false, "if send to backup system")
	backupCmd.Flags().StringVar(&fullTag, "full-tag", "MONGO_FULL_BACKUP", "full backup tag")
	backupCmd.Flags().StringVar(&incrTag, "incr-tag", "MONGO_INCR_BACKUP", "incr backup tag")
	backupCmd.Flags().BoolVar(&removeOldFileFirst, "remove-old-file-first", false, "remove old file first")
	backupCmd.Flags().IntVar(&maxDiskUsage, "max-disk-usage", 50, "max disk usage, default 50, unit: %")
	backupCmd.Flags().IntVar(&minDiskUsage, "min-disk-usage", 25, "min disk usage, default 25, unit: %")
	backupCmd.Flags().StringVar(&reportFile, "report-file", "", "report file") // 将备份文件详细信息写入到Report文件中
	backupCmd.Flags().StringVar(&labelsStr, "labels", "", "bkdbm server labels, json, allow empty")
	backupCmd.Flags().BoolVar(&archive, "archive", false,
		"use mongodump --archive. if zip is true, use zstd instead of gzip")
	backupCmd.Flags().IntVar(&numParallelCollections, "numParallelCollections", 0, "num parallel collections")
	rootCmd.AddCommand(backupCmd)
}

func backupMain() {
	initLog()
	printVersion()
	// todo Check ARgs

	connObj := mymongo.NewMongoHost(host, port, authDb, user, pass, "", host)
	db, err := connObj.Connect()
	if err != nil {
		log.Fatal(err)
	}
	prepareReportFile()
	defer db.Disconnect(context.TODO())
	isMasterOut, err := mymongo.IsMaster(db, 20)
	if err != nil {
		log.Fatal(err)
	}
	// support replica set only
	if isMasterOut.SetName == "" {
		log.Fatal("not a replica set")
	}

	connObj.Name = isMasterOut.SetName
	if fullFreq < 3600 {
		log.Warnf("fullFreq %d is too small, please set to 3600", fullFreq)
	}
	// if dir not exists, create it
	if e, _ := pitr.IsDirectory(dir); !e {
		log.Fatalf("args --dir %s is not exists or not a dir", dir)
	}
	dbmLabel, err := config.ParseBkDbmLabel(labelsStr)
	if err != nil {
		log.Fatalf("parseLabel error: %v", err)
	}

	lockHandle, err := getLock("pit_backup", port)
	if err != nil {
		log.Fatalf("get lock failed, err: %v, opType: %s, port: %s", err, "pit_backup", port)
	} else {
		log.Infof("get lock success, opType: %s, port: %s", "pit_backup", port)
	}

	var backupOpt = pitr.BackupOption{
		MongoHost:              connObj,
		BackupType:             backupType,
		Dir:                    dir,
		Zip:                    gzip,
		FullFreq:               fullFreq,
		IncrFreq:               incrFreq,
		FullTag:                fullTag,
		IncrTag:                incrTag,
		SendToBackupSystem:     sendToBackupSystem,
		RemoveOldFileFirst:     removeOldFileFirst,
		MaxDiskUsage:           maxDiskUsage,
		MinDiskUsage:           minDiskUsage,
		ReportFile:             reportFile,
		BkDbmLabel:             dbmLabel,
		DryRun:                 dryRun,
		Archive:                archive,
		NumParallelCollections: numParallelCollections,
	}
	pitr.DoJob(&backupOpt)

	err = lockHandle.Unlock()
	if err != nil {
		log.Warnf("unlock failed, err: %v, opType: %s, port: %s", err, "pit_backup", port)
	} else {
		log.Infof("unlock success, opType: %s, port: %s", "pit_backup", port)
	}
}

// getLock 获取文件锁. 如果获取失败, 则返回错误. 如果获取成功, 则返回文件锁句柄.
func getLock(opType string, port string) (lockHandle *flock.Flock, err error) {
	userName, err := osuser.Current()
	if err != nil {
		return nil, errors.New("get user name failed, err: " + err.Error())
	}
	lockDir := "/tmp"
	lockFile := fmt.Sprintf("lock.%s.%s.%s", userName.Username, opType, port)
	lockFilePath := filepath.Join(lockDir, lockFile)
	log.Infof("lockFilePath: %s", lockFilePath)

	lockHandle = flock.New(lockFilePath)
	locked, err := lockHandle.TryLock()
	log.Infof("lockPath: %s, locked: %v, err: %v", lockFilePath, locked, err)
	if err != nil {
		return nil, err
	}
	if !locked {
		return nil, errors.New("lock failed, lockFilePath: " + lockFilePath)
	}
	return lockHandle, nil
}
