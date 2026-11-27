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
	"errors"
	"sync"
	"time"

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

// connectTrace records the boundaries of one NewGormDB or NewSqlxDB attempt.
// It lives only for that attempt and is discarded after the timings are logged.
type connectTrace struct {
	start     time.Time
	opened    time.Time
	connected time.Time
	versioned time.Time
}

func (tr connectTrace) log(opts *options, driver string, err error) {
	slow := opts.logSlowConnect
	if slow <= 0 {
		return
	}
	total := time.Since(tr.start)
	if (err == nil) && (total < slow) {
		return
	}

	errmsg := ""
	if err != nil {
		errmsg = err.Error()
	}
	openCost := durationBetween(tr.start, tr.opened)
	connectCost := durationBetween(tr.opened, tr.connected)
	versionCost := durationBetween(tr.connected, tr.versioned)
	logger.Warn(
		"mysql connect timings, driver: %s, ip: %s, port: %d, total: %s, "+
			"open: %s, connect: %s, version: %s, errmsg: %s",
		driver, opts.ip, opts.port, total, openCost, connectCost, versionCost, errmsg,
	)
}

func durationBetween(from, to time.Time) time.Duration {
	if from.IsZero() || to.IsZero() || to.Before(from) {
		return 0
	}
	return to.Sub(from)
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

	logger.Debug("dsn:%s", db.opts.SafeDSN())
	trace := connectTrace{start: time.Now()}
	opened, err := db.open(&trace)
	trace.log(&db.opts, "gorm", err)
	return opened, err
}

// NewGormDBWithTimeout creates a GormDB whose OptionTimeout covers the whole connect.
// GORM's own SELECT VERSION() is always skipped, and we run it after connect instead.
// An explicit SkipInitializeWithVersion(false) or AutoSelectVersion(false) is rejected.
func NewGormDBWithTimeout(opts ...Option) (*GormDB, error) {
	applied := defaultOptions
	// Required so OptionTimeout covers the whole connect. GORM must not run its own
	// uncancellable SELECT VERSION(), and we query the version after connect instead.
	// Caller options are applied next; flipping either value is rejected below.
	applied.skipInitializeWithVersion = true
	applied.autoSelectVersion = true
	for _, opt := range opts {
		if err := opt.apply(&applied); err != nil {
			return nil, err
		}
	}
	if !applied.skipInitializeWithVersion {
		return nil, gerrors.New(gerrors.InvalidParameter,
			"NewGormDBWithTimeout requires SkipInitializeWithVersion true")
	}
	if !applied.autoSelectVersion {
		return nil, gerrors.New(gerrors.InvalidParameter,
			"NewGormDBWithTimeout requires AutoSelectVersion true")
	}

	opts = append(opts,
		OptionSkipInitializeWithVersion(true),
		OptionAutoSelectVersion(true),
	)
	return NewGormDB(opts...)
}

// open creates a connection pool and then establishes one connection.
func (db *GormDB) open(trace *connectTrace) (*GormDB, error) {
	mysqlCfg := db.opts.Config()
	dialector := &mysql.Dialector{Config: &mysqlCfg}
	// When SkipInitializeWithVersion is false, GORM runs SELECT VERSION() here with
	// context.Background(). That query cannot be cancelled, so OptionTimeout does not
	// cover it. The dial, handshake, and SET NAMES of that same Connect are uncovered
	// as well. We trust SELECT VERSION() not to block.
	gdb, err := gorm.Open(dialector, db.gormConfig())
	trace.opened = time.Now()
	if err != nil {
		return nil, gerrors.Newf(gerrors.MysqlFailure, "failed to open the db:%s errmsg: %s", db.opts.dbName, err)
	}
	// GORM already queried the version. Reuse it so Version() does not query again.
	// The slow-connect "version" segment stays 0; this time is included in open.
	if dialector.ServerVersion != "" {
		db.version = dialector.ServerVersion
		db.versionOK = true
	}
	db.attach(gdb)

	if err = db.connect(gdb, trace); err != nil {
		db.Close()
		db.db = nil
		db.close = nil
		return nil, err
	}
	return db, nil
}

// connect checks out one connection within the timeout.
// When version initialization was skipped, this is the first dial, so the timeout
// covers the handshake and SET NAMES. Otherwise GORM already connected during Open.
func (db *GormDB) connect(gdb *gorm.DB, trace *connectTrace) error {
	ctx := context.Background()
	var cancel context.CancelFunc
	if db.opts.timeout > 0 {
		// Cancel closes the socket, so a timed-out attempt does not keep the connection.
		ctx, cancel = context.WithTimeout(ctx, db.opts.timeout)
		defer cancel()
	}

	sqlDB, err := gdb.DB()
	if err != nil {
		return buildConnectError(&db.opts, ctx, err)
	}
	conn, err := sqlDB.Conn(ctx)
	trace.connected = time.Now()
	if err != nil {
		return buildConnectError(&db.opts, ctx, err)
	}
	defer conn.Close()

	if !db.opts.skipInitializeWithVersion || !db.opts.autoSelectVersion {
		return nil
	}

	var version string
	err = conn.QueryRowContext(ctx, "SELECT VERSION()").Scan(&version)
	trace.versioned = time.Now()
	if err != nil {
		return buildConnectError(&db.opts, ctx, err)
	}
	db.version = version
	db.versionOK = true
	return nil
}

// gormConfig returns the gorm configuration for the database.
func (db *GormDB) gormConfig() *gorm.Config {
	gormCfg := &gorm.Config{
		DisableAutomaticPing: db.opts.disableAutomaticPing,
	}

	if db.opts.logger != nil {
		gormCfg.Logger = logger.NewGormLogger(db.opts.logger, &gormlogger.Config{
			SlowThreshold:             db.opts.logSlowThreshold,
			IgnoreRecordNotFoundError: db.opts.logIgnoreRecordNotFoundError,
			ParameterizedQueries:      db.opts.logParameterizedQueries,
		})
	}

	return gormCfg
}

// attach attaches the database to the GormDB instance.
func (db *GormDB) attach(gdb *gorm.DB) {
	if sqlDb, sqlErr := gdb.DB(); sqlErr == nil {
		if db.opts.maxOpenConns != 0 {
			sqlDb.SetMaxOpenConns(db.opts.maxOpenConns)
		}
		if db.opts.maxIdleConns != 0 {
			sqlDb.SetMaxIdleConns(db.opts.maxIdleConns)
		}
		if db.opts.connMaxLifetime != 0 {
			sqlDb.SetConnMaxLifetime(db.opts.connMaxLifetime)
		}
	}

	db.db = gdb
	db.close = func() {
		if sqlDb, err := db.db.DB(); err == nil {
			sqlDb.Close()
		}
	}
}

func buildConnectError(opts *options, ctx context.Context, err error) error {
	if opts.timeout > 0 && (errors.Is(err, context.DeadlineExceeded) || ctx.Err() != nil) {
		logger.Error("mysql connection establishment timed out, ip: %s, port: %d, timeout: %s",
			opts.ip, opts.port, opts.timeout.String())
		return gerrors.Newf(gerrors.MysqlFailure,
			"mysql connection establishment timed out, ip: %s, port: %d, timeout: %s",
			opts.ip, opts.port, opts.timeout.String())
	}
	return gerrors.Newf(gerrors.MysqlFailure, "mysql connection establishment failed, ip: %s, port: %d, errmsg: %s",
		opts.ip, opts.port, err.Error())
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

	logger.Debug("dsn:%s", db.opts.SafeDSN())
	trace := connectTrace{start: time.Now()}
	opened, err := db.open(&trace)
	trace.log(&db.opts, "sqlx", err)
	return opened, err
}

// open creates the pool and checks it with select version().
// sqlx.Open does not dial. There is no separate Conn step, so connect stays 0.
// The first QueryRow dials, and that time is recorded as version.
func (db *SqlxDB) open(trace *connectTrace) (*SqlxDB, error) {
	sqlDb, err := sqlx.Open("mysql", db.opts.DSN())
	trace.opened = time.Now()
	trace.connected = trace.opened
	if err != nil {
		return nil, gerrors.Newf(gerrors.MysqlFailure, "failed to open the db:%s errmsg: %s", db.opts.dbName, err)
	}

	// QueryRow releases the connection after Scan. The context covers the dial
	// inside this call; the DSN timeout alone stops at TCP connect.
	ctx := context.Background()
	var cancel context.CancelFunc
	if db.opts.timeout > 0 {
		ctx, cancel = context.WithTimeout(ctx, db.opts.timeout)
		defer cancel()
	}
	var version string
	err = sqlDb.QueryRowContext(ctx, "select version()").Scan(&version)
	trace.versioned = time.Now()
	if err != nil {
		sqlDb.Close()
		return nil, buildConnectError(&db.opts, ctx, err)
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

// Version returns the server version, preferring the value queried while opening;
// on cache miss it lazily queries and only caches successful results.
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
