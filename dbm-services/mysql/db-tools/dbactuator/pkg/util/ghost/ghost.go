/*
* TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
* Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
* Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
* You may obtain a copy of the License at https://opensource.org/licenses/MIT
* Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
* an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
* specific language governing permissions and limitations under the License.
 */

// Package ghost used for online ddl operation
package ghost

import (
	"errors"
	"fmt"
	"os"
	"os/signal"
	"runtime"
	"strings"
	"sync"
	"syscall"

	"github.com/github/gh-ost/go/base"
	"github.com/github/gh-ost/go/logic"
	"github.com/github/gh-ost/go/sql"
	"github.com/openark/golib/log"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
)

var defaultGhostConfig = struct {
	chunkSize                           int64
	dmlBatchSize                        int64
	concurrentCountTableRows            bool
	timestampOldTable                   bool
	hooksStatusIntervalSec              int64
	heartbeatIntervalMilliseconds       int64
	niceRatio                           float64
	allowedRunningOnMaster              bool
	maxLagMillisecondsThrottleThreshold int64
	defaultNumRetries                   int64
	cutoverLockTimeoutSeconds           int64
	exponentialBackoffMaxInterval       int64
	throttleHTTPIntervalMillis          int64
	throttleHTTPTimeoutMillis           int64
	storageEngine                       string
}{
	// allow-on-master
	allowedRunningOnMaster: false,
	// concurrent-rowcount
	concurrentCountTableRows: true,
	// doesn't have a gh-ost cli flag counterpart
	timestampOldTable: true,
	// hooks-status-interval
	hooksStatusIntervalSec: 60,
	// heartbeat-interval-millis
	heartbeatIntervalMilliseconds: 100,
	// nice-ratio
	niceRatio: 0,
	// chunk-size
	chunkSize: 1000,
	// dml-batch-size
	dmlBatchSize: 10,
	// max-lag-millis
	maxLagMillisecondsThrottleThreshold: 1500,
	// default-retries
	defaultNumRetries: 60,
	// cut-over-lock-timeout-seconds
	cutoverLockTimeoutSeconds: 10,
	// exponential-backoff-max-interval
	exponentialBackoffMaxInterval: 64,
	// throttle-http-interval-millis
	throttleHTTPIntervalMillis: 100,
	// throttle-http-timeout-millis
	throttleHTTPTimeoutMillis: 1000,
	storageEngine:             "innodb",
}

// UserGhostFlag TODO
type UserGhostFlag struct {
	StorageEngine                 *string  `json:"storage_engine"`
	MaxLoad                       *string  `json:"max_load"`
	NiceRatio                     *float64 `json:"nice_ratio"`
	ChunkSize                     *int64   `json:"chunk_size"`
	DmlBatchSize                  *int64   `json:"dml_batch_size"`
	DefaultRetries                *int64   `json:"default_retries"`
	CutoverLockTimeoutSeconds     *int64   `json:"cutover_lock_timeout_seconds"`
	ExponentialBackoffMaxInterval *int64   `json:"exponential_backoff_max_interval"`
	MaxLagMillis                  *int64   `json:"max_lag_millis"`
	AllowOnMaster                 *bool    `json:"allow_on_master"`
	SwitchToRBR                   *bool    `json:"switch_to_rbr"`
	AssumeRBR                     *bool    `json:"assume_rbr"`
	HeartbeatIntervalMillis       *int64   `json:"heartbeat_interval_millis"`
}

// DataSource ghost data source
type DataSource struct {
	Host     string
	Port     int
	User     string
	Password string
}

// NewMigrationContext new gh-ost migration context
// nolint
func NewMigrationContext(ds DataSource, flag UserGhostFlag, taskId uint, offset int, dbName, tbName string,
	statments []string, noop bool) (*base.MigrationContext, error) {
	migrationContext := base.NewMigrationContext()
	migrationContext.Log = transGhost2dbmLogger()
	migrationContext.Log.SetLevel(log.DEBUG)
	migrationContext.InspectorConnectionConfig.Key.Hostname = ds.Host
	port := 3306
	if ds.Port > 0 {
		port = ds.Port
	}
	migrationContext.Noop = noop
	migrationContext.InspectorConnectionConfig.Key.Port = port
	migrationContext.CliUser = ds.User
	migrationContext.CliPassword = ds.Password
	migrationContext.DatabaseName = dbName
	migrationContext.OriginalTableName = tbName
	migrationContext.AlterStatement = strings.Join(statments, " ")
	pse := sql.NewParserFromAlterStatement(migrationContext.AlterStatement)
	migrationContext.AlterStatementOptions = pse.GetAlterStatementOptions()
	migrationContext.AllowedRunningOnMaster = defaultGhostConfig.allowedRunningOnMaster
	migrationContext.ConcurrentCountTableRows = defaultGhostConfig.concurrentCountTableRows
	migrationContext.HooksStatusIntervalSec = defaultGhostConfig.hooksStatusIntervalSec
	migrationContext.CutOverType = base.CutOverAtomic
	migrationContext.ThrottleHTTPIntervalMillis = defaultGhostConfig.throttleHTTPIntervalMillis
	migrationContext.ThrottleHTTPTimeoutMillis = defaultGhostConfig.throttleHTTPTimeoutMillis
	migrationContext.TimestampOldTable = defaultGhostConfig.timestampOldTable
	migrationContext.SetHeartbeatIntervalMilliseconds(defaultGhostConfig.heartbeatIntervalMilliseconds)
	migrationContext.SetNiceRatio(defaultGhostConfig.niceRatio)
	migrationContext.SetChunkSize(defaultGhostConfig.chunkSize)
	migrationContext.SetDMLBatchSize(defaultGhostConfig.dmlBatchSize)
	migrationContext.SetMaxLagMillisecondsThrottleThreshold(defaultGhostConfig.maxLagMillisecondsThrottleThreshold)
	migrationContext.SetDefaultNumRetries(defaultGhostConfig.defaultNumRetries)
	migrationContext.ServeSocketFile = getGhostSocketFileName(taskId, offset, dbName, tbName)
	if flag.HeartbeatIntervalMillis != nil {
		migrationContext.SetHeartbeatIntervalMilliseconds(*flag.HeartbeatIntervalMillis)
	}
	migrationContext.OkToDropTable = true
	migrationContext.InitiallyDropGhostTable = true
	migrationContext.InitiallyDropOldTable = true
	migrationContext.ReplicaServerId = taskId
	storageEngine := defaultGhostConfig.storageEngine
	if flag.StorageEngine != nil {
		storageEngine = *flag.StorageEngine
	}
	if migrationContext.SwitchToRowBinlogFormat && migrationContext.AssumeRBR {
		return nil, fmt.Errorf("switchToRBR and assumeRBR are mutually exclusive")
	}
	if migrationContext.AllowedRunningOnMaster && migrationContext.TestOnReplica {
		// nolint
		migrationContext.Log.Fatal("--allow-on-master and --test-on-replica are mutually exclusive")
	}
	if migrationContext.AllowedRunningOnMaster && migrationContext.MigrateOnReplica {
		// nolint
		migrationContext.Log.Fatal("--allow-on-master and --migrate-on-replica are mutually exclusive")
	}
	if migrationContext.MigrateOnReplica && migrationContext.TestOnReplica {
		// nolint
		migrationContext.Log.Fatal("--migrate-on-replica and --test-on-replica are mutually exclusive")
	}
	if err := migrationContext.SetConnectionConfig(storageEngine); err != nil {
		return nil, err
	}
	migrationContext.ApplyCredentials()
	if flag.ChunkSize != nil {
		migrationContext.SetChunkSize(*flag.ChunkSize)
	}
	if flag.DmlBatchSize != nil {
		migrationContext.SetDMLBatchSize(*flag.DmlBatchSize)
	}
	if flag.NiceRatio != nil {
		migrationContext.SetNiceRatio(*flag.NiceRatio)
	}
	if flag.MaxLoad != nil {
		if err := migrationContext.ReadMaxLoad(*flag.MaxLoad); err != nil {
			return nil, err
		}
	}
	if flag.MaxLagMillis != nil {
		migrationContext.SetMaxLagMillisecondsThrottleThreshold(*flag.MaxLagMillis)
	}
	if flag.DefaultRetries != nil {
		migrationContext.SetDefaultNumRetries(*flag.DefaultRetries)
	}
	if flag.CutoverLockTimeoutSeconds != nil {
		migrationContext.CutOverLockTimeoutSeconds = *flag.CutoverLockTimeoutSeconds
	}
	if flag.ExponentialBackoffMaxInterval != nil {
		migrationContext.ExponentialBackoffMaxInterval = *flag.ExponentialBackoffMaxInterval
	}
	if flag.AllowOnMaster != nil {
		migrationContext.AllowedRunningOnMaster = *flag.AllowOnMaster
	}
	if flag.SwitchToRBR != nil {
		migrationContext.SwitchToRowBinlogFormat = *flag.SwitchToRBR
	}
	if flag.AssumeRBR != nil {
		migrationContext.AssumeRBR = *flag.AssumeRBR
	}
	if err := migrationContext.SetupTLS(); err != nil {
		migrationContext.Log.Fatale(err)
	}
	if err := migrationContext.SetCutOverLockTimeoutSeconds(defaultGhostConfig.cutoverLockTimeoutSeconds); err != nil {
		migrationContext.Log.Errore(err)
	}
	if err := migrationContext.SetExponentialBackoffMaxInterval(defaultGhostConfig.exponentialBackoffMaxInterval); err !=
		nil {
		migrationContext.Log.Errore(err)
	}
	acceptSignals(migrationContext)
	return migrationContext, nil
}

func getGhostSocketFileName(taskID uint, offset int, databaseName, tableName string) string {
	return fmt.Sprintf("/tmp/gh-ost.%v.%d.%v.%v.sock", taskID, offset, databaseName, tableName)
}

// BuildTaskIDWithShardID build taskID with shardId use for tendbcluster online ddl
func BuildTaskIDWithShardID(taskID, shardID uint, batchID string) string {
	return fmt.Sprintf("%d.%d.%s", taskID, shardID, batchID)
}

func acceptSignals(migrationContext *base.MigrationContext) {
	c := make(chan os.Signal, 1)

	signal.Notify(c, syscall.SIGHUP)
	go func() {
		for sig := range c {
			// nolint
			switch sig {
			case syscall.SIGHUP:
				migrationContext.Log.Infof("Received SIGHUP. Reloading configuration")
				if err := migrationContext.ReadConfigFile(); err != nil {
					log.Errore(err)
				} else {
					migrationContext.MarkPointOfInterest()
				}
			}
		}
	}()
}

func getConcurrency() int {
	n := runtime.NumCPU() / 2
	if n == 0 {
		return 1
	}
	return n
}

// RunMigratorClustershardNodes do sql on every remote node
func RunMigratorClustershardNodes(masterRemoteSvrs []native.Server, billId uint, dbName, tbName, statement string,
	flag UserGhostFlag) (err error) {
	// 使用无缓冲的 channel，配合专门的错误收集 goroutine
	errChan := make(chan error)
	wg := sync.WaitGroup{}
	ctrlChan := make(chan struct{}, getConcurrency())

	// 收集所有有效的迁移上下文
	var validMigrations []struct {
		context *base.MigrationContext
		server  native.Server
	}

	// 先验证所有的 MigrationContext，如果有错误立即返回
	for idx, svr := range masterRemoteSvrs {
		shardNum := native.GetShardNumberFromMasterServerName(svr.ServerName)
		// noop == false is execute
		mgc, err := NewMigrationContext(buildDs(svr), flag, billId, idx, BuildShardDbName(dbName, shardNum), tbName, []string{
			statement}, false)
		if err != nil {
			logger.Error("Failed to create migration context for %s: %v", svr.ServerName, err)
			return err // 立即返回错误，避免部分失败的复杂情况
		}
		validMigrations = append(validMigrations, struct {
			context *base.MigrationContext
			server  native.Server
		}{mgc, svr})
	}

	// 错误收集 goroutine
	var errs []error
	errDone := make(chan struct{})
	go func() {
		for errx := range errChan {
			errs = append(errs, errx)
		}
		close(errDone)
	}()

	// 启动所有迁移任务
	for _, migration := range validMigrations {
		wg.Add(1)
		go func(migrationContext *base.MigrationContext, svr native.Server) {
			defer wg.Done()

			// 获取并发许可
			ctrlChan <- struct{}{}
			defer func() { <-ctrlChan }() // 释放并发许可

			logger.Info("will execute sql:%s on %s", statement, svr.ServerName)
			migrator := logic.NewMigrator(migrationContext, "dbm")
			if err := migrator.Migrate(); err != nil {
				errChan <- err
			}
		}(migration.context, migration.server)
	}

	// 等待所有任务完成，然后关闭错误 channel
	go func() {
		wg.Wait()
		close(errChan)
	}()

	// 等待错误收集完成
	<-errDone

	return errors.Join(errs...)
}

func buildDs(svr native.Server) DataSource {
	return DataSource{
		Host:     svr.Host,
		Port:     svr.Port,
		User:     svr.Username,
		Password: svr.Password,
	}
}

// BuildGhostCmdEveryNodes build ghost cmd on every remote node
func BuildGhostCmdEveryNodes(masterRemoteSvrs []native.Server, billId uint, dbName, tbName, statement string,
	flag UserGhostFlag) (cmds []string) {
	for _, svr := range masterRemoteSvrs {
		shardNum := native.GetShardNumberFromMasterServerName(svr.ServerName)
		ghostCmd := buildGhostCmd(buildDs(svr), flag, billId, BuildShardDbName(dbName, shardNum), tbName, []string{statement},
			true)
		cmds = append(cmds, ghostCmd)
	}
	return cmds
}

// BuildShardDbName build shard db name
func BuildShardDbName(dbBase string, shardNum string) string {
	return fmt.Sprintf("%s_%s", dbBase, shardNum)
}

// buildGhostCmd build ghost cmd for faile on same node
func buildGhostCmd(ds DataSource, flag UserGhostFlag, taskId uint, dbName, tbName string,
	statments []string, noop bool) (ghostCmd string) {
	ghostCmd = "gh-ost"
	ghostCmd += fmt.Sprintf(" --user=%s", ds.User)
	ghostCmd += " --password=xxx "
	ghostCmd += fmt.Sprintf(" --host=%s", ds.Host)
	ghostCmd += fmt.Sprintf(" --port=%d", ds.Port)
	ghostCmd += fmt.Sprintf(" --database=\"%s\"", dbName)
	ghostCmd += fmt.Sprintf(" --table=\"%s\"", tbName)
	ghostCmd += fmt.Sprintf(" --alter=\"%s\"", strings.Join(statments, " "))
	ghostCmd += fmt.Sprintf(" --chunk-size=%d", defaultGhostConfig.chunkSize)
	if flag.ChunkSize != nil {
		ghostCmd += fmt.Sprintf(" --chunk-size=%d", *flag.ChunkSize)
	}
	if flag.StorageEngine != nil {
		ghostCmd += fmt.Sprintf(" --storage-engine=%s", *flag.StorageEngine)
	}
	if flag.AllowOnMaster != nil {
		ghostCmd += " --allow-on-master "
	}
	if !noop {
		ghostCmd += " --execute "
	}
	return
}
