/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

package hamysql

import (
	"context"
	"sync"

	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"

	"github.com/jmoiron/sqlx"
	"gorm.io/driver/mysql"
	"gorm.io/gorm"
	gormlogger "gorm.io/gorm/logger"
)

// DBType is a type constraint for supported database types (gorm.DB or sqlx.DB).
type DBType interface {
	gorm.DB | sqlx.DB
}

// Base the database base information
type Base[T DBType] struct {
	db    *T
	opts  options
	close func()
}

// GormDB wraps a GORM database connection with common base options.
type GormDB struct {
	Base[gorm.DB]

	versionMu sync.Mutex
	version   string
	versionOK bool
}

// SqlxDB wraps a sqlx database connection with common base options.
type SqlxDB struct {
	Base[sqlx.DB]
}

// NewGormDB creates a new GormDB instance with the given options.
func NewGormDB(opts ...Option) (*GormDB, error) {
	db := &GormDB{
		Base: Base[gorm.DB]{
			opts: defaultOptions,
		},
	}

	for _, opt := range opts {
		if err := opt.apply(&db.opts); err != nil {
			return nil, err
		}
	}

	gormCfg := &gorm.Config{
		DisableAutomaticPing: db.opts.disableAutomaticPing,
	}

	var gormLogger *logger.GormLogger
	if db.opts.logger != nil {
		gormLogger = logger.NewGormLogger(db.opts.logger, &gormlogger.Config{
			SlowThreshold:             db.opts.logSlowThreshold,
			IgnoreRecordNotFoundError: db.opts.logIgnoreRecordNotFoundError,
			ParameterizedQueries:      db.opts.logParameterizedQueries,
		})

		gormCfg.Logger = gormLogger
	}

	logger.Debug("dsn:%s", db.opts.SafeDSN())

	mysqlCfg := db.opts.Config()
	dialector := &mysql.Dialector{Config: &mysqlCfg}
	gdb, err := gorm.Open(dialector, gormCfg)
	if err != nil {
		return nil, gerrors.Newf(gerrors.MysqlFailure, "failed to open the db:%s errmsg: %s", db.opts.dbName, err)
	}

	// The driver already ran SELECT VERSION() during gorm.Open; reuse it as the version cache.
	// Depends on gorm.io/driver/mysql Dialector.ServerVersion (exported); if a driver upgrade
	// stops populating it, this silently degrades to the lazy path (one extra query per conn).
	if dialector.ServerVersion != "" {
		db.version = dialector.ServerVersion
		db.versionOK = true
	}

	db.db = gdb
	db.close = func() {
		if sqlDb, err := db.db.DB(); err == nil {
			sqlDb.Close()
		}
	}

	return db, nil
}

// NewSqlxDB creates a new SqlxDB instance with the given options.
func NewSqlxDB(opts ...Option) (*SqlxDB, error) {
	db := &SqlxDB{
		Base: Base[sqlx.DB]{
			opts: defaultOptions,
		},
	}

	for _, opt := range opts {
		if err := opt.apply(&db.opts); err != nil {
			return nil, err
		}
	}

	sqlDb, err := sqlx.Open("mysql", db.opts.DSN())
	if err != nil {
		return nil, gerrors.Newf(gerrors.MysqlFailure, "failed to open the db:%s errmsg: %s", db.opts.dbName, err)
	}

	if _, err = sqlDb.Queryx("select version();"); err != nil {
		return nil, gerrors.Newf(gerrors.MysqlFailure, "check that the connection to db:%s is abnormal, errmsg: %s",
			db.opts.dbName, err)
	}

	db.db = sqlDb
	db.close = func() {
		sqlDb.Close()
	}

	return db, nil
}

func (db Base[T]) DB() *T {
	return db.db
}

func (db Base[T]) Host() string {
	return db.opts.ip
}

func (db Base[T]) Port() int {
	return db.opts.port
}

func (db Base[T]) Close() {
	if db.close == nil {
		return
	}

	db.close()
}

// WithGormDB returns a GormDB view over an existing *gorm.DB.
// When onClose is non-nil it is invoked by Close(); when nil, Close is a no-op.
func WithGormDB(gdb *gorm.DB, onClose func()) *GormDB {
	return &GormDB{
		Base: Base[gorm.DB]{
			db:    gdb,
			close: onClose,
		},
	}
}

// DBWithContext returns a new gorm.DB with the given context.
func (db *GormDB) DBWithContext(ctx context.Context) *gorm.DB {
	return db.db.WithContext(ctx)
}

// Version returns the server version, preferring the value already queried by the driver
// during gorm.Open; on cache miss it lazily queries and only caches successful results.
func (db *GormDB) Version(ctx context.Context) (string, error) {
	db.versionMu.Lock()
	defer db.versionMu.Unlock()

	if db.versionOK {
		return db.version, nil
	}

	var version string
	if err := db.db.WithContext(ctx).Raw("SELECT VERSION()").Scan(&version).Error; err != nil {
		return "", gerrors.Newf(gerrors.MysqlFailure, "failed to query version on db(%s:%d), errmsg: %s",
			db.opts.ip, db.opts.port, err.Error())
	}

	db.version = version
	db.versionOK = true
	return version, nil
}

// UseReplicaNaming reports whether the connected server requires the MySQL 8.4 replica
// statement naming (SHOW REPLICA STATUS etc.).
func (db *GormDB) UseReplicaNaming(ctx context.Context) (bool, error) {
	version, err := db.Version(ctx)
	if err != nil {
		return false, err
	}
	return UseReplicaNamingByVersion(version), nil
}
