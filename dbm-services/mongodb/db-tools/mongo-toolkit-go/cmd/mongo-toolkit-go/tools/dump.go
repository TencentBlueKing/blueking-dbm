package tools

import (
	"context"
	"dbm-services/mongodb/db-tools/dbmon/config"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/pkg/mymongo"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/pkg/report"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/toolkit/logical"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/toolkit/pitr"
	"path/filepath"
	"strings"

	"github.com/pkg/errors"
	log "github.com/sirupsen/logrus"
	"github.com/spf13/cobra"
)

var (
	dumpCmd = &cobra.Command{
		Use:   "dump",
		Short: "dump",
		Long:  `logical dump`,
		Run: func(cmd *cobra.Command, args []string) {
			dumpMain()
		},
	}
)

var backupFileTag string
var oplog bool
var dbList, ignoreDbList, colList, ignoreColList string // 逗号分隔的字符串。 MongoDB支持库表中有逗号，但此工具不支持.

var mongodumpExe string
var mongorestoreExe string

func init() {
	dumpCmd.Flags().StringVar(&host, "host", "127.0.0.1", "host")
	dumpCmd.Flags().StringVar(&port, "port", "27017", "port")
	dumpCmd.Flags().StringVar(&authDb, "authdb", "admin", "authdb")
	dumpCmd.Flags().StringVar(&user, "user", "xxx", "xxx")
	dumpCmd.Flags().StringVar(&pass, "pass", "xxx", "xxx")
	dumpCmd.Flags().StringVar(&backupType, "type", "", "FULL INCR AUTO")
	dumpCmd.Flags().BoolVar(&dryRun, "dryRun", false, "测试模式")
	dumpCmd.Flags().StringVar(&dir, "dir", ".", "")
	dumpCmd.Flags().BoolVar(&gzip, "zip", false, "use mongodump -- zip")
	dumpCmd.Flags().StringVar(&addr, "addr", "127.0.0.1:6997", "用于确保只有一个mongotoolkit在运行")
	dumpCmd.Flags().BoolVar(&sendToBackupSystem, "send-to-bs", false, "if send to backup system")
	dumpCmd.Flags().StringVar(&backupFileTag, "file-tag", "MONGO_FULL_BACKUP", "full backup tag")
	dumpCmd.Flags().BoolVar(&removeOldFileFirst, "remove-old-file-first", false, "if remove old file first")
	dumpCmd.Flags().StringVar(&reportFile, "report-file", "", "report file") // 将备份文件详细信息写入到Report文件中. 格式是固定的.
	dumpCmd.Flags().StringVar(&labelsStr, "labels", "", "bkdbm server labels, json, allow empty")
	dumpCmd.Flags().StringVar(&mongodumpExe, "dump-tool", "mongodump.100.7", "mongodump exe")
	dumpCmd.Flags().BoolVar(&oplog, "oplog", false, "use mongodump --oplog ")
	dumpCmd.Flags().StringVar(&dbList, "db-list", "", "db list, like db1,db2")
	dumpCmd.Flags().StringVar(&ignoreDbList, "ignore-db-list", "", "ignore db list, like db1,db2")
	dumpCmd.Flags().StringVar(&colList, "col-list", "", "col list, like db1.col1,db2.col2")
	dumpCmd.Flags().StringVar(&ignoreColList, "ignore-col-list", "", "ignore col list, like db1.col1,db2.col2")
	rootCmd.AddCommand(dumpCmd)

}

// dumpMain dump cmd main
func dumpMain() {
	initLog()
	printVersion()
	// todo Check ARgs
	mongoHost := mymongo.NewMongoHost(host, port, authDb, user, pass, "", host)
	db, err := mongoHost.Connect()
	if err != nil {
		log.Fatal(err)
	}
	defer db.Disconnect(context.TODO())
	isMasterOut, err := mymongo.IsMaster(db, 20)
	if err != nil {
		log.Fatal(err)
	}
	prepareReportFile()
	// 也支持在mongos上发起备份.
	mongoHost.Name = isMasterOut.SetName

	// if dir not exists, create it
	if e, _ := pitr.IsDirectory(dir); !e {
		log.Fatalf("args --dir %s is not exists or not a dir", dir)
	}

	args := logical.BakcupArgs{
		IsPartial: false,
	}

	if dbList != "" || ignoreDbList != "" || colList != "" || ignoreColList != "" {
		args.IsPartial = true
		args.PartialArgs.DbList = strings.Split(dbList, ",")
		args.PartialArgs.IgnoreDbList = strings.Split(ignoreDbList, ",")
		args.PartialArgs.ColList = strings.Split(colList, ",")
		args.PartialArgs.IgnoreColList = strings.Split(ignoreColList, ",")
	}

	args.Oplog = oplog
	// oplog 与 --db-list/--ignore-db-list/--col-list/--ignore-col-list 不能同时使用.
	if args.IsPartial && args.Oplog {
		log.Fatalf("args --oplog and --db-list/--ignore-db-list/--col-list/--ignore-col-list can not be used together")
	}

	// 如果文件中没有oplog.bson， 又指定了--oplog， 则会报错.
	mongodumpExePath, err := filepath.Abs(mongodumpExe)
	if err != nil {
		log.Fatal(errors.Wrap(err, "get mongodump path error"))
	}

	dbmLabel, err := config.ParseBkDbmLabel(labelsStr)
	if err != nil {
		log.Fatalf("parseLabel error: %v", err)
	}

	var backupOpt = logical.DumpOption{
		MongodumpExePath:   mongodumpExePath,
		MongoHost:          mongoHost,
		BackupType:         backupType,
		Dir:                dir,
		Zip:                gzip,
		Tag:                backupFileTag,
		SendToBackupSystem: sendToBackupSystem,
		RemoveOldFileFirst: removeOldFileFirst,
		ReportFile:         reportFile,
		BkDbmLabel:         dbmLabel,
		DryRun:             dryRun,
		Args:               &args,
	}
	logical.Dump(&backupOpt)
}

// prepareReportFile 准备report文件
func prepareReportFile() {
	var err error
	if reportFile == "" {
		return
	}
	reportFile, err = filepath.Abs(reportFile)
	if err != nil {
		log.Fatal(err)
	}
	if err = report.PrepareReportPath(reportFile); err != nil {
		log.Fatal(err)
	}
}
