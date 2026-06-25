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

package snapshotlogger

import (
	"context"
	"fmt"
	"sync"
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/internal/analysis/dbm"
	"dbm-services/common/dbha-v2/internal/analysis/storage"
	"dbm-services/common/dbha-v2/internal/analysis/switcher"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/hanet"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"

	"gorm.io/gorm"
)

const (
	// SwitchSnapshotLogDefaultDbConnectTimeout is the default timeout for connecting to the switch log database.
	// TCP dial deadline in DSN (go-sql-driver "timeout"; does not cap handshake/read alone).
	SwitchSnapshotLogDefaultDbConnectTimeout = 3 * time.Second

	// SwitchSnapshotLogDefaultDbOpenCheckTimeout is the default timeout for
	// checking if the switch log table exists during Open.
	// Bound for schema/table checks executed during Open (information_schema + USE + HasTable).
	SwitchSnapshotLogDefaultDbOpenCheckTimeout = 10 * time.Second

	// SwitchSnapshotLogDefaultDbWriteTimeout is the default timeout for writing switch snapshot log to database.
	SwitchSnapshotLogDefaultDbWriteTimeout = 1 * time.Second
)

// DbSnapshotHandler writes switching snapshot log to database.
// It implements the SwitchLogger[*SwitchingSnapshotData] interface.
type DbSnapshotHandler struct {
	// the connection information of the switch log database
	Proto  string
	Ip     string
	Port   int
	User   string
	Passwd string

	// the mysql instance for writing switch snapshot log
	logDb *storage.DbhaData
	// the mutex for concurrent write to database
	mu sync.Mutex

	// the timeout for writing switch snapshot log to database
	writeTimeout time.Duration
	// the timeout for connecting to the switch log database
	connectTimeout time.Duration
	// the timeout for checking if the switch log table exists
	openCheckTimeout time.Duration

	// recordID holds the ID of the created record after the first Append call.
	// It is used for updating the same record in subsequent Append calls.
	recordID uint
}

// NewDbSnapshotHandler creates a DbSnapshotHandler by the connection information.
func NewDbSnapshotHandler(
	proto string,
	ip string,
	port int,
	user string,
	passwd string,
	writeTimeout time.Duration,
	connectTimeout time.Duration,
	openCheckTimeout time.Duration,
) *DbSnapshotHandler {
	return &DbSnapshotHandler{
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

// NewDbSnapshotHandlerFromConfig creates a DbSnapshotHandler from config.
func NewDbSnapshotHandlerFromConfig() (*DbSnapshotHandler, error) {
	epoint, err := hanet.NewEndpoint(config.Cfg.Storage.Endpoint)
	if err != nil {
		return nil, gerrors.Newf(gerrors.InvalidConfiguration, "invalid storage configuration, %v", err)
	}

	hdl := &DbSnapshotHandler{
		Proto:  epoint.Proto,
		Ip:     epoint.Host,
		Port:   epoint.Port,
		User:   config.Cfg.Storage.User,
		Passwd: config.Cfg.Storage.Password,
	}

	hdl.writeTimeout = config.Cfg.Workflow.SwitchFlow.SwitchLogWriteTimeout
	if hdl.writeTimeout <= 0 {
		hdl.writeTimeout = SwitchSnapshotLogDefaultDbWriteTimeout
	}

	hdl.connectTimeout = config.Cfg.Workflow.SwitchFlow.DbConnectTimeout
	if hdl.connectTimeout <= 0 {
		hdl.connectTimeout = SwitchSnapshotLogDefaultDbConnectTimeout
	}

	hdl.openCheckTimeout = SwitchSnapshotLogDefaultDbOpenCheckTimeout

	return hdl, nil
}

// CheckSwitchSnapshotTableExists checks if the DbSwitchingSnapshotLog table exists.
func (hdl *DbSnapshotHandler) CheckSwitchSnapshotTableExists(ctx context.Context) error {
	if hdl.logDb == nil {
		return gerrors.Newf(gerrors.MysqlFailure, "mysql instance for writing switch snapshot log is nil")
	}

	dbClient := hdl.logDb.DB.DB()

	// Check if database exists
	var dbExists int
	dbCheckSQL := "SELECT 1 FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = ?"
	if err := dbClient.WithContext(ctx).Raw(dbCheckSQL, hamodel.DatabaseName).Scan(&dbExists).Error; err != nil {
		return gerrors.Newf(gerrors.MysqlFailure, "failed to check database(%s) existence on mysql(%s:%d), errmsg: %s",
			hamodel.DatabaseName, hdl.Ip, hdl.Port, err.Error())
	}

	if dbExists == 0 {
		return gerrors.Newf(gerrors.MysqlFailure, "database %s does not exist on mysql(%s:%d)",
			hamodel.DatabaseName, hdl.Ip, hdl.Port)
	}

	// Use the database
	dbhaDB := dbClient.WithContext(ctx).Session(&gorm.Session{}).Exec("USE `" + hamodel.DatabaseName + "`")
	if dbhaDB.Error != nil {
		return gerrors.Newf(gerrors.MysqlFailure,
			"failed to use database %s on mysql(%s:%d), errmsg: %s",
			hamodel.DatabaseName, hdl.Ip, hdl.Port, dbhaDB.Error.Error())
	}

	// Check if table exists
	if !dbhaDB.Migrator().HasTable(&hamodel.DbSwitchingSnapshotLog{}) {
		return gerrors.Newf(gerrors.MysqlFailure, "table %s does not exist in database %s on mysql(%s:%d)",
			hamodel.DbSwitchingSnapshotLogTableName, hamodel.DatabaseName, hdl.Ip, hdl.Port)
	}
	return nil
}

// Open opens the connection to database.
func (hdl *DbSnapshotHandler) Open() error {
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
		errMsg := fmt.Sprintf("failed to connect mysql(%s:%d), errmsg: %s", hdl.Ip, hdl.Port, err.Error())
		logger.Warn("%s", errMsg)
		return gerrors.New(gerrors.MysqlFailure, errMsg)
	}

	hdl.logDb = &storage.DbhaData{
		DB: db,
	}

	checkCtx, cancelCheck := context.WithTimeout(context.Background(), hdl.openCheckTimeout)
	defer cancelCheck()

	if err := hdl.CheckSwitchSnapshotTableExists(checkCtx); err != nil {
		// close the connection if table does not exist
		hdl.Close()

		errMsg := fmt.Sprintf("when checking switch snapshot table, errmsg: %s", err.Error())
		logger.Warn("%s", errMsg)
		return gerrors.New(gerrors.MysqlFailure, errMsg)
	}

	return nil
}

// Close closes the connection to database.
func (hdl *DbSnapshotHandler) Close() {
	if hdl.logDb == nil {
		return
	}

	if hdl.logDb.DB != nil {
		hdl.logDb.DB.Close()
	}
	hdl.logDb = nil
}

// PreSwitchLog logs a switching snapshot record to the database before the switch executes.
func (hdl *DbSnapshotHandler) PreSwitchLog(record *SwitchingSnapshotData) error {
	if record == nil {
		return gerrors.New(gerrors.InvalidParameter, "switching snapshot record for db is nil")
	}

	if hdl.logDb == nil {
		return gerrors.New(gerrors.MysqlFailure, "mysql instance for writing switch snapshot log is nil")
	}

	// avoid concurrent write to database
	hdl.mu.Lock()
	defer hdl.mu.Unlock()

	ctx, cancel := context.WithTimeout(context.Background(), hdl.writeTimeout)
	defer cancel()

	return hdl.createRecord(ctx, record)
}

// PostSwitchLog logs a switching snapshot record to the database after the switch executes.
func (hdl *DbSnapshotHandler) PostSwitchLog(record *SwitchingSnapshotData) error {
	if record == nil {
		return gerrors.New(gerrors.InvalidParameter, "switching snapshot record for db is nil")
	}

	if hdl.logDb == nil {
		return gerrors.New(gerrors.MysqlFailure, "mysql instance for writing switch snapshot log is nil")
	}

	if hdl.recordID == 0 {
		return gerrors.New(gerrors.InvalidParameter, "recordID is 0, no record to update")
	}

	// avoid concurrent write to database
	hdl.mu.Lock()
	defer hdl.mu.Unlock()

	ctx, cancel := context.WithTimeout(context.Background(), hdl.writeTimeout)
	defer cancel()

	return hdl.updateRecord(ctx, record)
}

// createRecord creates a new DbSwitchingSnapshotLog record in the database.
// After creation, GORM auto-fills the ID back into the struct,
// so we save the generated ID for subsequent updates.
func (hdl *DbSnapshotHandler) createRecord(ctx context.Context, record *SwitchingSnapshotData) error {
	dbRecord := &hamodel.DbSwitchingSnapshotLog{
		SwitchID:    record.SwitchID,
		DbType:      record.DbType,
		ActionScope: record.ActionScope,
		BkBizID:     record.BkBizID,
		BkCloudID:   record.BkCloudID,
		ClusterID:   record.ClusterID,
		ClusterName: record.ClusterName,
		Reason:      record.Reason,
		StartTime:   record.StartTime,
	}

	instances := buildInstancesListFromMetadata(record.MetadataSet, nil)
	dbRecord.SetInstances(instances)

	err := hdl.logDb.SaveSwitchingSnapshotLog(ctx, dbRecord)
	if ctx.Err() == context.DeadlineExceeded {
		return gerrors.Newf(gerrors.Failure, "switch snapshot log write timeout after %s", hdl.writeTimeout)
	}
	if err != nil {
		return err
	}

	// Save the auto-generated ID for subsequent updates
	hdl.recordID = dbRecord.ID
	return nil
}

// updateRecord updates the existing DbSwitchingSnapshotLog record identified by recordID.
func (hdl *DbSnapshotHandler) updateRecord(ctx context.Context, record *SwitchingSnapshotData) error {
	dbRecord := &hamodel.DbSwitchingSnapshotLog{
		ID:           hdl.recordID,
		FinishedTime: record.FinishedTime,
		Result:       record.Result,
	}

	instances := buildInstancesListFromMetadata(record.MetadataSet, record.Response)
	dbRecord.SetInstances(instances)

	err := hdl.logDb.UpdateSwitchingSnapshotLog(ctx, dbRecord)
	if ctx.Err() == context.DeadlineExceeded {
		return gerrors.Newf(gerrors.Failure, "switch snapshot log write timeout after %s", hdl.writeTimeout)
	}
	return err
}

// buildInstancesListFromMetadata converts DbInstMetadata list to SwitchingSnapshotInstance list for database storage.
func buildInstancesListFromMetadata(metaSet []*dbm.DbInstMetadata, response *switcher.Response) []*hamodel.SwitchingSnapshotInstance {
	if metaSet == nil {
		return nil
	}

	instances := make([]*hamodel.SwitchingSnapshotInstance, 0, len(metaSet))
	for _, meta := range metaSet {
		instanceRole := meta.InstanceRole.String()
		if instanceRole == "" && meta.SpiderRole != "" {
			instanceRole = string(meta.SpiderRole)
		}

		newMasterIP := ""
		newMasterPort := 0
		if response != nil {
			// TODO Get the latest newMasterIP and newMasterPort of the instance through response
			//instKey := switchcore.GenerateMetadataKey(meta.BkCloudID, meta.IP, meta.Port)
		}

		instances = append(instances, &hamodel.SwitchingSnapshotInstance{
			IP:            meta.IP,
			Port:          meta.Port,
			MachineType:   string(meta.MachineType),
			InstanceRole:  instanceRole,
			NewMasterIP:   newMasterIP,
			NewMasterPort: newMasterPort,
		})
	}

	return instances
}
