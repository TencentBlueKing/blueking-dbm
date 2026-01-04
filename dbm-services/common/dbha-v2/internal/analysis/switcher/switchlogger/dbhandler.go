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
	"fmt"

	"dbm-services/common/dbha-v2/internal/admin/migrator"
	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/internal/analysis/storage"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/hanet"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"

	"gorm.io/gorm"
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
}

type DbSwitchLogger SwitchLogger[hamodel.DbSwitchingLog]

// NewLogToDbHandler creates a LogToDbHandler by the connection information
func NewLogToDbHandler(proto string, ip string, port int, user string, passwd string) *LogToDbHandler {
	return &LogToDbHandler{
		Proto:  proto,
		Ip:     ip,
		Port:   port,
		User:   user,
		Passwd: passwd,
	}
}

// NewLogToDbHandlerFromConfig creates a LogToDbHandler from config
func NewLogToDbHandlerFromConfig() (*LogToDbHandler, error) {
	epoint, err := hanet.NewEndpoint(config.Cfg.Storage.Endpoint)
	if err != nil {
		return nil, gerrors.Newf(gerrors.InvalidConfiguration, "invalid storage configuration, %v", err)
	}

	return NewLogToDbHandler(
		epoint.Proto,
		epoint.Host,
		epoint.Port,
		config.Cfg.Storage.User,
		config.Cfg.Storage.Password,
	), nil
}

// CreateSwitchLogTable creates the table for switch log
func (hdl *LogToDbHandler) CreateSwitchLogTable() error {
	if hdl.logDb == nil {
		return gerrors.Newf(gerrors.MysqlFailure, "mysql instance for writing switch log is nil")
	}

	dbClient := hdl.logDb.DB.DB()
	sql := fmt.Sprintf(migrator.CreateDbIfNotExistSql, hamodel.DatabaseName)
	if err := dbClient.Exec(sql).Error; err != nil {
		return gerrors.Newf(gerrors.MysqlFailure, "failed to create the database(%s) on mysql(%s:%d), %v",
			hamodel.DatabaseName, hdl.Ip, hdl.Port, err)
	}

	dbhaDB := dbClient.Session(&gorm.Session{}).Exec("USE " + hamodel.DatabaseName)

	if err := dbhaDB.AutoMigrate(&hamodel.DbSwitchingLog{}); err != nil {
		return gerrors.Newf(gerrors.MysqlFailure, "failed to migrate table(%s) on mysql(%s:%d), %v",
			hamodel.DbSwitchingLogTableName, hdl.Ip, hdl.Port, err)
	}
	return nil
}

// Open opens the connection to database
func (hdl *LogToDbHandler) Open() error {
	if hdl.logDb != nil {
		return nil
	}

	db, err := hamysql.NewGormDB(
		hamysql.OptionIP(hdl.Ip),
		hamysql.OptionPort(hdl.Port),
		hamysql.OptionUser(hdl.User),
		hamysql.OptionPassword(hdl.Passwd),
	)
	if err != nil {
		errMsg := fmt.Sprintf("failed to connect mysql(%s:%d), %s", hdl.Ip, hdl.Port, err.Error())
		logger.Warn("%s", errMsg)
		return gerrors.New(gerrors.MysqlFailure, errMsg)
	}

	hdl.logDb = &storage.DbhaData{
		DB: db,
	}

	if err := hdl.CreateSwitchLogTable(); err != nil {
		hdl.Close()
		errMsg := fmt.Sprintf("failed to create switch log table, %s", err.Error())
		logger.Warn("%s", errMsg)
		return gerrors.New(gerrors.MysqlFailure, errMsg)
	}

	return nil
}

// Close closes the connection to database
func (hdl *LogToDbHandler) Close() error {
	if hdl.logDb == nil {
		return nil
	}
	con, connErr := hdl.logDb.DB.DB().DB()
	if connErr != nil {
		logger.Warn("failed to get mysql connection(%s:%d) when closing switch log, errmsg: %s",
			hdl.Ip, hdl.Port, connErr.Error())
		return connErr
	}
	if closeErr := con.Close(); closeErr != nil {
		logger.Warn("failed to close switch log mysql connection(%s:%d), errmsg: %s",
			hdl.Ip, hdl.Port, closeErr.Error())
		return closeErr
	}
	hdl.logDb = nil
	return nil
}

// Append appends a switch log record
func (hdl *LogToDbHandler) Append(record *hamodel.DbSwitchingLog) error {
	if hdl.logDb == nil {
		return gerrors.New(gerrors.Failure, "mysql instance for writing switch log is nil")
	}

	if record == nil {
		return gerrors.New(gerrors.InvalidParameter, "switch log record for db is nil")
	}
	return hdl.logDb.SaveSwitchingLog(record)
}
