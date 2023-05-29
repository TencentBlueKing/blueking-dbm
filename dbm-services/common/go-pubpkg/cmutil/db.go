package cmutil

import (
	"context"
	"database/sql"
	"dbm-services/common/go-pubpkg/logger"
	"fmt"
	"time"

	_ "github.com/go-sql-driver/mysql" // mysql TODO
	"github.com/jmoiron/sqlx"
)

// DbWorker TODO
type DbWorker struct {
	Dsn string
	Db  *sql.DB
}

// NewDbWorker TODO
func NewDbWorker(dsn string) (*DbWorker, error) {
	var err error
	dbw := &DbWorker{
		Dsn: dsn,
	}
	dbw.Db, err = sql.Open("mysql", dbw.Dsn)
	if err != nil {
		return nil, err
	}
	// check connect with timeout
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if err := dbw.Db.PingContext(ctx); err != nil {
		return nil, fmt.Errorf("ping context failed, err:%w", err)
	}
	if err := dbw.Db.Ping(); err != nil {
		return nil, err
	}
	return dbw, nil
}

// ShowDatabases 执行show database 获取所有的dbName
//
//	@receiver h
//	@return databases
//	@return err
func (h *DbWorker) ShowDatabases() (databases []string, err error) {
	err = h.Queryx(&databases, "show databases")
	return
}

// Queryx execute query use sqlx
func (h *DbWorker) Queryx(data interface{}, query string, args ...interface{}) error {
	logger.Info("query:%s", query)
	logger.Info("args:%v", args)
	db := sqlx.NewDb(h.Db, "mysql")
	udb := db.Unsafe()
	if err := udb.Select(data, query, args...); err != nil {
		return fmt.Errorf("sqlx select failed, err:%w", err)
	}
	return nil
}

// Queryxs execute query use sqlx return Single column
func (h *DbWorker) Queryxs(data interface{}, query string) error {
	db := sqlx.NewDb(h.Db, "mysql")
	udb := db.Unsafe()
	if err := udb.Get(data, query); err != nil {
		return err
	}
	return nil
}
