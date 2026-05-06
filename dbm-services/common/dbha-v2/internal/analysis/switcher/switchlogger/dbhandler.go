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

package switchlogger

import (
	"context"
	"fmt"
	"sync"
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/internal/analysis/storage"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/hanet"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"

	"gorm.io/gorm"
)

const (
	// TCP dial deadline in DSN (go-sql-driver "timeout"; does not cap handshake/read alone).
	SwitchLogDefaultDbConnectTimeout = 3 * time.Second
	// Bound for schema/table checks executed during Open (information_schema + USE + HasTable).
	SwitchLogDefaultDbOpenCheckTimeout = 10 * time.Second
	SwitchLogDefaultDbWriteTimeout     = 1 * time.Second
)

// LogToDbHandler writes switch log to database
type LogToDbHandler struct {
	// the connection information of the switch log database

	Proto  string
	Ip     string
	Port   int
	User   string
	Passwd string

	// the mysql instance for writing switch log
	logDb *storage.DbhaData
	// the mutex for concurrent write to database
	mu sync.Mutex

	// the timeout for writing switch log to database
	writeTimeout time.Duration
	// the timeout for connecting to the switch log database
	connectTimeout time.Duration
	// the timeout for checking if the switch log table exists
	openCheckTimeout time.Duration
}

// NewLogToDbHandler creates a LogToDbHandler by the connection information
func NewLogToDbHandler(
	proto string,
	ip string,
	port int,
	user string,
	passwd string,
	writeTimeout time.Duration,
	connectTimeout time.Duration,
	openCheckTimeout time.Duration,
) *LogToDbHandler {
	return &LogToDbHandler{
		Proto:            proto,
		Ip:               ip,
		Port:             port,
		User:             user,
		Passwd:           passwd,
		writeTimeout:     writeTimeout,
		connectTimeout:   connectTimeout,
		openCheckTimeout: openCheckTimeout,
	}
}

// NewLogToDbHandlerFromConfig creates a LogToDbHandler from config
func NewLogToDbHandlerFromConfig() (*LogToDbHandler, error) {
	epoint, err := hanet.NewEndpoint(config.Cfg.Storage.Endpoint)
	if err != nil {
		return nil, gerrors.Newf(gerrors.InvalidConfiguration, "invalid storage configuration, %v", err)
	}

	hdl := &LogToDbHandler{
		Proto:  epoint.Proto,
		Ip:     epoint.Host,
		Port:   epoint.Port,
		User:   config.Cfg.Storage.User,
		Passwd: config.Cfg.Storage.Password,
	}

	hdl.writeTimeout = config.Cfg.Workflow.SwitchFlow.SwitchLogWriteTimeout
	if hdl.writeTimeout <= 0 {
		hdl.writeTimeout = SwitchLogDefaultDbWriteTimeout
	}

	hdl.connectTimeout = config.Cfg.Workflow.SwitchFlow.DbConnectTimeout
	if hdl.connectTimeout <= 0 {
		hdl.connectTimeout = SwitchLogDefaultDbConnectTimeout
	}

	hdl.openCheckTimeout = SwitchLogDefaultDbOpenCheckTimeout

	return hdl, nil
}

// CheckSwitchLogTableExists checks if the switch log table exists (ctx bounds SQL execution).
func (hdl *LogToDbHandler) CheckSwitchLogTableExists(ctx context.Context) error {
	if hdl.logDb == nil {
		return gerrors.Newf(gerrors.MysqlFailure, "mysql instance for writing switch log is nil")
	}

	dbClient := hdl.logDb.DB.DB()

	// Check if database exists
	var dbExists int
	dbCheckSQL := fmt.Sprintf("SELECT 1 FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = '%s'", hamodel.DatabaseName)
	if err := dbClient.WithContext(ctx).Raw(dbCheckSQL).Scan(&dbExists).Error; err != nil {
		return gerrors.Newf(gerrors.MysqlFailure, "failed to check database(%s) existence on mysql(%s:%d), %s",
			hamodel.DatabaseName, hdl.Ip, hdl.Port, err.Error())
	}

	if dbExists == 0 {
		return gerrors.Newf(gerrors.MysqlFailure, "database %s does not exist on mysql(%s:%d)",
			hamodel.DatabaseName, hdl.Ip, hdl.Port)
	}

	// Use the database
	dbhaDB := dbClient.WithContext(ctx).Session(&gorm.Session{}).Exec("USE " + hamodel.DatabaseName)
	if dbhaDB.Error != nil {
		return gerrors.Newf(gerrors.MysqlFailure,
			"failed to use database %s on mysql(%s:%d), %s", hamodel.DatabaseName, hdl.Ip, hdl.Port, dbhaDB.Error.Error())
	}

	// Check if table exists
	migrator := dbhaDB.WithContext(ctx).Migrator()
	if !migrator.HasTable(&hamodel.DbSwitchingLog{}) {
		return gerrors.Newf(gerrors.MysqlFailure, "table %s does not exist in database %s on mysql(%s:%d)",
			hamodel.DbSwitchingLogTableName, hamodel.DatabaseName, hdl.Ip, hdl.Port)
	}
	return nil
}

// Open opens the connection to database
func (hdl *LogToDbHandler) Open() error {
	if hdl.logDb != nil {
		return nil
	}

	db, err := hamysql.NewGormDB(
		hamysql.OptionProto(hdl.Proto),
		hamysql.OptionIP(hdl.Ip),
		hamysql.OptionPort(hdl.Port),
		hamysql.OptionUser(hdl.User),
		hamysql.OptionPassword(hdl.Passwd),
		hamysql.OptionTimeout(hdl.connectTimeout),
	)
	if err != nil {
		errMsg := fmt.Sprintf("failed to connect mysql(%s:%d), %s", hdl.Ip, hdl.Port, err.Error())
		logger.Warn("%s", errMsg)
		return gerrors.New(gerrors.MysqlFailure, errMsg)
	}

	hdl.logDb = &storage.DbhaData{
		DB: db,
	}

	checkCtx, cancelCheck := context.WithTimeout(context.Background(), hdl.openCheckTimeout)
	defer cancelCheck()

	if err := hdl.CheckSwitchLogTableExists(checkCtx); err != nil {
		// close the connection if table does not exist
		hdl.Close()

		errMsg := fmt.Sprintf("when checking switch log table, %s", err.Error())
		logger.Warn("%s", errMsg)
		return gerrors.New(gerrors.MysqlFailure, errMsg)
	}

	return nil
}

// Close closes the connection to database
func (hdl *LogToDbHandler) Close() {
	if hdl.logDb == nil {
		return
	}

	if hdl.logDb.DB != nil {
		hdl.logDb.DB.Close()
	}
	hdl.logDb = nil
}

// Append appends a switch log record
func (hdl *LogToDbHandler) Append(record *hamodel.DbSwitchingLog) error {
	if hdl.logDb == nil {
		return gerrors.New(gerrors.Failure, "mysql instance for writing switch log is nil")
	}

	if record == nil {
		return gerrors.New(gerrors.InvalidParameter, "switch log record for db is nil")
	}

	// avoid concurrent write to database
	hdl.mu.Lock()
	defer hdl.mu.Unlock()

	ctx, cancel := context.WithTimeout(context.Background(), hdl.writeTimeout)
	defer cancel()

	err := hdl.logDb.SaveSwitchingLog(ctx, record)
	if ctx.Err() == context.DeadlineExceeded {
		return gerrors.Newf(gerrors.Failure, "switch log write timeout after %s", hdl.writeTimeout)
	}
	return err
}
