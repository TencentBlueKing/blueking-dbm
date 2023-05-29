// Package dbutil TODO
package dbutil

import (
	"database/sql"

	_ "github.com/go-sql-driver/mysql"

	"dbm-services/common/dbha/ha-module/log"
)

// ConnMySQL connParam format: user:password@(ip:port)/dbName, %s:%s@(%s:%d)/%s
func ConnMySQL(connParam string) (*sql.DB, error) {
	db, err := sql.Open("mysql", connParam)
	if err != nil {
		log.Logger.Errorf("connect mysql failed. err:%s", err.Error())
		return nil, nil
	}

	return db, nil
}
