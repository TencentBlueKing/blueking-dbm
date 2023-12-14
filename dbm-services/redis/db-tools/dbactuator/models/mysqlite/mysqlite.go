// Package mysqlite TODO
package mysqlite

import (
	"fmt"
	"path/filepath"

	"github.com/glebarez/sqlite"
	"gorm.io/gorm"

	"dbm-services/redis/db-tools/dbactuator/mylog"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
)

func getLocalDbName() (dbname string, err error) {
	dbname = filepath.Join(consts.BkDbmonPath, "db", "lucky_boy.db")
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
