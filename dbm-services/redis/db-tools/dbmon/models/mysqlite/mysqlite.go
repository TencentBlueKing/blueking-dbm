// Package mysqlite TODO
package mysqlite

import (
	"fmt"
	"os"
	"path/filepath"

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
	sqDB, err = gorm.Open(sqlite.Open(dbName), &gorm.Config{})
	if err != nil {
		err = fmt.Errorf("gorm.Open failed,err:%v,dbname:%s", err, dbName)
		mylog.Logger.Info(err.Error())
		return
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
