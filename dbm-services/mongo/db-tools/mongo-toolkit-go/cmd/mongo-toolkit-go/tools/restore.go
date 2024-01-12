package tools

import (
	"context"
	"dbm-services/mongo/db-tools/mongo-toolkit-go/pkg/mymongo"
	"dbm-services/mongo/db-tools/mongo-toolkit-go/toolkit/logical"
	"dbm-services/mongo/db-tools/mongo-toolkit-go/toolkit/pitr"
	"path/filepath"
	"strings"

	"github.com/pkg/errors"
	log "github.com/sirupsen/logrus"
	"github.com/spf13/cobra"
)

var (
	restoreCmd = &cobra.Command{
		Use:   "restore",
		Short: "restore",
		Long:  `logical restore`,
		Run: func(cmd *cobra.Command, args []string) {
			restoreMain()
		},
	}
)

var backupFile string

func init() {
	restoreCmd.Flags().StringVar(&host, "host", "127.0.0.1", "host")
	restoreCmd.Flags().StringVar(&port, "port", "27017", "port")
	restoreCmd.Flags().StringVar(&authDb, "authdb", "admin", "authdb")
	restoreCmd.Flags().StringVar(&user, "user", "xxx", "xxx")
	restoreCmd.Flags().StringVar(&pass, "pass", "xxx", "xxx")
	restoreCmd.Flags().StringVar(&backupType, "type", "", "FULL INCR AUTO")
	restoreCmd.Flags().BoolVar(&dryRun, "dryRun", false, "测试模式")
	restoreCmd.Flags().StringVar(&dir, "dir", ".", "")
	restoreCmd.Flags().BoolVar(&gzip, "zip", false, "use mongodump -- zip")
	restoreCmd.Flags().StringVar(&addr, "addr", "127.0.0.1:6997", "用于确保只有一个mongotoolkit在运行")
	restoreCmd.Flags().StringVar(&backupFile, "file", "", "需导入的文件，.tar 或 .tar.gz 或 .tgz")
	restoreCmd.Flags().BoolVar(&removeOldFileFirst, "remove-old-file-first", false, "if remove old file first")
	restoreCmd.Flags().StringVar(&reportFile, "report-file", "", "report file") // 将备份文件详细信息写入到Report文件中. 格式是固定的.
	restoreCmd.Flags().StringVar(&mongorestoreExe, "restore-tool", "mongorestore", "mongodump exe")
	restoreCmd.Flags().BoolVar(&oplog, "oplog", false, "use mongodump --oplog ")
	restoreCmd.Flags().StringVar(&dbList, "db-list", "", "db list, like db1,db2")
	restoreCmd.Flags().StringVar(&ignoreDbList, "ignore-db-list", "", "ignore db list, like db1,db2")
	restoreCmd.Flags().StringVar(&colList, "col-list", "", "col list, like db1.col1,db2.col2")
	restoreCmd.Flags().StringVar(&ignoreColList, "ignore-col-list", "", "ignore col list, like db1.col1,db2.col2")
	rootCmd.AddCommand(restoreCmd)

}

func restoreMain() {
	initLog()
	printVersion()

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

	mongoHost.Name = isMasterOut.SetName

	// if dir not exists, create it
	if e, _ := pitr.IsDirectory(dir); !e {
		log.Fatalf("args --dir %s is not exists or not a dir", dir)
	}

	// labels = splitLabels(labelsStr)

	args := logical.RestoreArgs{
		IsPartial: false,
	}

	if dbList != "" || ignoreDbList != "" || colList != "" || ignoreColList != "" {
		args.IsPartial = true
		args.PartialArgs.DbList = strings.Split(dbList, ",")
		args.PartialArgs.IgnoreDbList = strings.Split(ignoreDbList, ",")
		args.PartialArgs.ColList = strings.Split(colList, ",")
		args.PartialArgs.IgnoreColList = strings.Split(ignoreColList, ",")
	}

	mongorestoreExePath, err := filepath.Abs(mongorestoreExe)
	if err != nil {
		log.Fatal(errors.Wrap(err, "get mongorestore path error"))
	}

	var opt = logical.RestoreOption{
		RestoreExePath: mongorestoreExePath,
		MongoHost:      mongoHost,
		BackupType:     backupType,
		Dir:            dir,
		Zip:            gzip,
		DryRun:         dryRun,
		Args:           &args,
		RestoreFile:    backupFile,
	}
	logical.Restore(&opt)
}
