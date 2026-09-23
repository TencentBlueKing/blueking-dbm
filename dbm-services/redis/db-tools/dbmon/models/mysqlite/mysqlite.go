// Package mysqlite TODO
package mysqlite

import (
	"fmt"
	"os"
	"path/filepath"
	"time"

	"github.com/glebarez/sqlite"
	"gorm.io/gorm"

	"dbm-services/redis/db-tools/dbmon/mylog"
	"dbm-services/redis/db-tools/dbmon/util"
)

func getLocalDbName() (dbname string, err error) {
	var homeDir string
	homeDir, err = os.Executable()
	if err != nil {
		err = fmt.Errorf("os.Executable failed,err:%v", err)
		mylog.Logger.Info(err.Error())
		return
	}
	homeDir = filepath.Dir(homeDir)
	dbname = filepath.Join(homeDir, "db", "lucky_boy.db")
	return
}

// GetLocalSqDB TODO
func GetLocalSqDB() (sqDB *gorm.DB, err error) {
	dbName, err := getLocalDbName()
	if err != nil {
		return
	}
	dbDir := filepath.Dir(dbName)
	err = util.MkDirsIfNotExists([]string{dbDir})
	if err != nil {
		return
	}
	util.LocalDirChownMysql(dbDir)
	// busy_timeout: 多进程并发写时等待锁而非立即报错
	// journal_mode=WAL: 读写不互斥,崩溃后靠-wal文件自动恢复,避免rollback热日志导致的readonly(1032)错误
	sqDB, err = gorm.Open(sqlite.Open(dbName+"?_pragma=busy_timeout(10000)&_pragma=journal_mode(WAL)"), &gorm.Config{})
	if err != nil {
		err = fmt.Errorf("gorm.Open failed,err:%v,dbname:%s", err, dbName)
		mylog.Logger.Info(err.Error())
		return
	}
	return
}

const (
	// SqDBWriteRetryCount sqlite写入失败重试次数(应对多进程并发写、热日志回滚中的瞬时错误)
	SqDBWriteRetryCount = 3
	// SqDBWriteRetryInterval sqlite写入失败重试间隔
	SqDBWriteRetryInterval = 2 * time.Second
)

// RetryOnWriteErr sqlite写失败时重试,避免瞬时错误(如撞上热日志回滚)导致整个任务失败
func RetryOnWriteErr(writeFn func() error) (err error) {
	for i := 0; i < SqDBWriteRetryCount; i++ {
		if err = writeFn(); err == nil {
			return
		}
		if i < SqDBWriteRetryCount-1 {
			mylog.Logger.Warn(fmt.Sprintf("sqlite write failed,retry %d/%d after %s,err:%v",
				i+1, SqDBWriteRetryCount, SqDBWriteRetryInterval, err))
			time.Sleep(SqDBWriteRetryInterval)
		}
	}
	return
}

// CloseDB TODO
func CloseDB(sqDB *gorm.DB) {
	if sqDB != nil {
		dbInstance, _ := sqDB.DB()
		_ = dbInstance.Close()
	}
}
