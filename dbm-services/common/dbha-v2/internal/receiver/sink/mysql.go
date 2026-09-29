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

package sink

import (
	"encoding/json"
	"path/filepath"
	"sync/atomic"
	"time"

	"dbm-services/common/dbha-v2/internal/receiver/apm"
	"dbm-services/common/dbha-v2/internal/receiver/config"
	"dbm-services/common/dbha-v2/pkg/constant"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/hanet"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"

	"gorm.io/gorm"
	"gorm.io/gorm/clause"
)

const mySQLName = "MySQL"

// Message Data message reported by probe.
type Message struct {
	Topic string
	Data  []byte
}

type mysql struct {
	dbs               []*hamysql.GormDB
	writer            chunkWriter
	batchChunkSize    int
	chunkMaxBytes     int
	writeRetryTimeout time.Duration
	closed            atomic.Bool
	// recordDuration replaces the batch-duration histogram in tests.
	recordDuration func(topic string, ms float64)
	// nowFn replaces the clock used for write-delay samples. Nil means time.Now.
	nowFn func() time.Time
	// recordStats replaces RecordWriteStats in tests.
	recordStats func(topic string, stats WriteStats)
}

func newMySql(cfg config.SinkConfig) (*mysql, error) {
	epoints, err := hanet.NewEndpoints(cfg.Endpoints)
	if err != nil {
		return nil, err
	}

	gormLogger := newMySQLGormLogger()
	timeout := cfg.SaveTimeout
	if timeout <= 0 {
		timeout = constant.DefaultSaveTimeout
	}
	msql := &mysql{
		writer:            gormChunkWriter{},
		batchChunkSize:    resolvePositiveInt(cfg.BatchChunkSize, defaultBatchChunkSize),
		chunkMaxBytes:     resolvePositiveInt(cfg.ChunkMaxBytes, defaultChunkMaxBytes),
		writeRetryTimeout: resolvePositiveDuration(cfg.WriteRetryTimeout, defaultWriteRetryTimeout),
	}

	for _, epoint := range epoints {
		db, err := hamysql.NewGormDB(buildMySQLOptions(cfg, epoint, gormLogger, timeout)...)
		if err != nil {
			return nil, err
		}
		msql.dbs = append(msql.dbs, db)
	}
	return msql, nil
}

func newMySQLGormLogger() logger.Logger {
	logBasename := filepath.Base(config.Cfg.Log.Path)
	logDir := filepath.Dir(config.Cfg.Log.Path)
	return logger.NewZapLogger(logger.Config{
		FileName:   filepath.Join(logDir, "gorm-"+logBasename),
		LogLevel:   logger.Level(config.Cfg.Log.Level),
		MaxSizeMB:  config.Cfg.Log.FileSize,
		MaxBackups: config.Cfg.Log.FileCount,
	})
}

func buildMySQLOptions(
	cfg config.SinkConfig,
	epoint *hanet.Endpoint,
	gormLogger logger.Logger,
	timeout time.Duration,
) []hamysql.Option {
	maxIdleConns := resolvePositiveInt(cfg.MaxIdleConns, defaultMaxIdleConns)
	connMaxLifetime := resolvePositiveDuration(cfg.ConnMaxLifetime, defaultConnMaxLifetime)
	opts := []hamysql.Option{
		hamysql.OptionIP(epoint.Host),
		hamysql.OptionPort(epoint.Port),
		hamysql.OptionProto(epoint.Proto),
		hamysql.OptionDBName(hamodel.DatabaseName),
		hamysql.OptionUser(cfg.User),
		hamysql.OptionPassword(cfg.Password),
		hamysql.OptionLogger(gormLogger),
		hamysql.OptionReadTimeout(timeout),
		hamysql.OptionWriteTimeout(timeout),
		hamysql.OptionMaxIdleConns(maxIdleConns),
		hamysql.OptionConnMaxLifetime(connMaxLifetime),
	}
	if cfg.MaxOpenConns != 0 {
		opts = append(opts, hamysql.OptionMaxOpenConns(cfg.MaxOpenConns))
	}
	interpolate := true
	if cfg.InterpolateParams != nil {
		interpolate = *cfg.InterpolateParams
	}
	if interpolate {
		opts = append(opts,
			hamysql.OptionInterpolateParams(true),
			hamysql.OptionAutoMaxAllowedPacket(true),
		)
	}
	return opts
}

func resolvePositiveInt(v, def int) int {
	if v <= 0 {
		return def
	}
	return v
}

func resolvePositiveDuration(v, def time.Duration) time.Duration {
	if v <= 0 {
		return def
	}
	return v
}

func (s *mysql) currentTime() time.Time {
	if s.nowFn != nil {
		return s.nowFn()
	}
	return time.Now()
}

func (s *mysql) emitStats(topic string, stats WriteStats) {
	if s.recordStats != nil {
		s.recordStats(topic, stats)
		return
	}
	RecordWriteStats(topic, stats)
}

func (s *mysql) Save(msg *Message) error {
	startTime := time.Now()
	defer func() {
		err := apm.MySqlWriteDurationMs.ObserveWithLabels(map[string]string{
			apm.MetricLabelMysql: msg.Topic,
		}, float64(time.Since(startTime).Milliseconds()))
		if err != nil {
			logger.Warn("update mysql write duration metric failed, errmsg: %s", err)
		}
	}()

	err, stats := s.saveOne(msg)
	s.emitStats(msg.Topic, stats)
	return err
}

func (s *mysql) saveOne(msg *Message) (error, WriteStats) {
	var stats WriteStats
	dbStatus := &haprobe.HarvestData{}
	if err := json.Unmarshal(msg.Data, dbStatus); err != nil {
		s.countReadError(msg.Topic)
		stats.AddDrop("", ReasonInvalidJSON, 1)
		return gerrors.Newf(
			gerrors.InvalidJson,
			"unmarshal a mysql metric message failed, topic(%s), %v",
			msg.Topic, err,
		), stats
	}

	logger.Debug("outputter(mysql) save msg: %s, raw: %s", msg.Data, dbStatus.RawValue)

	data := hamodel.NewDbhaData(dbStatus)
	if !data.HarvestType.IsKnown() {
		stats.AddDrop(string(data.DbTypeName), ReasonUnknownType, 1)
		return gerrors.Newf(gerrors.InvalidParameter,
			"unknown harvest_type, topic: %s, db: %s:%d, harvest_type: %s",
			msg.Topic, data.DbIp, data.DbPort, data.HarvestType), stats
	}

	s.writeSaveEndpoints(msg, data, &stats)
	s.countSaveVolume(msg)
	return nil, stats
}

func (s *mysql) writeSaveEndpoints(msg *Message, data *hamodel.DbhaDataStatus, stats *WriteStats) {
	dbType := string(data.DbTypeName)
	var firstOK time.Time
	okN, dataFails, otherFails := 0, 0, 0
	for _, db := range s.dbs {
		err := db.DB().Session(&gorm.Session{FullSaveAssociations: true}).
			Clauses(clause.OnConflict{UpdateAll: true}).
			Create(data).Error
		if err != nil {
			s.noteSaveEndpointError(msg.Topic, err, &dataFails, &otherFails)
			continue
		}
		if okN == 0 {
			firstOK = s.currentTime()
		}
		okN++
	}
	if okN > 0 {
		stats.Written = 1
		if ms, ok := DelayMillis(firstOK, data.ReportTimestamp); ok {
			stats.Samples = append(stats.Samples, DelaySample{DbType: dbType, Ms: ms})
		}
		return
	}
	reason := ReasonWriteError
	if len(s.dbs) > 0 && otherFails == 0 && dataFails == len(s.dbs) {
		reason = ReasonDataError
	}
	stats.AddDrop(dbType, reason, 1)
}

func (s *mysql) noteSaveEndpointError(topic string, err error, dataFails, otherFails *int) {
	logger.Warn("save the mysql metric failed, errmsg: %s", err)
	if classifyMySQLError(err) == mysqlErrData {
		*dataFails++
	} else {
		*otherFails++
	}
	if metricErr := apm.MySqlWriteErrorsTotal.IncWithLabels(map[string]string{
		apm.MetricLabelMysql: topic,
	}); metricErr != nil {
		logger.Warn("update mysql write errors metric failed, errmsg: %s", metricErr)
	}
}

func (s *mysql) countReadError(topic string) {
	if metricErr := apm.MySqlReadErrorsTotal.IncWithLabels(map[string]string{
		apm.MetricLabelMysql: topic,
	}); metricErr != nil {
		logger.Warn("update mysql read errors metric failed, errmsg: %s", metricErr)
	}
}

func (s *mysql) countSaveVolume(msg *Message) {
	if err := apm.MySqlWriteMessagesTotal.IncWithLabels(map[string]string{
		apm.MetricLabelMysql: msg.Topic,
	}); err != nil {
		logger.Warn("update mysql write messages metric failed, errmsg: %s", err)
	}
	if err := apm.MySqlWriteBytesTotal.AddWithLabels(map[string]string{
		apm.MetricLabelMysql: msg.Topic,
	}, float64(len(msg.Data))); err != nil {
		logger.Warn("update mysql write bytes metric failed, errmsg: %s", err)
	}
}

func (s *mysql) Close() {
	s.closed.Store(true)
	for _, db := range s.dbs {
		db.Close()
	}
}
