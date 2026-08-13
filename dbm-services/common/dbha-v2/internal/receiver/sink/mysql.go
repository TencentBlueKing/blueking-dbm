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
	dbs []*hamysql.GormDB
}

func newMySql(endpoints, user, password string, timeout time.Duration) (*mysql, error) {
	epoints, err := hanet.NewEndpoints(endpoints)
	if err != nil {
		return nil, err
	}

	logBasename := filepath.Base(config.Cfg.Log.Path)
	logDir := filepath.Dir(config.Cfg.Log.Path)

	logCfg := logger.Config{
		FileName:   filepath.Join(logDir, "gorm-"+logBasename),
		LogLevel:   logger.Level(config.Cfg.Log.Level),
		MaxSizeMB:  config.Cfg.Log.FileSize,
		MaxBackups: config.Cfg.Log.FileCount,
	}

	gormLogger := logger.NewZapLogger(logCfg)

	msql := &mysql{}

	if timeout <= 0 {
		timeout = constant.DefaultSaveTimeout
	}

	for _, epoint := range epoints {
		db, err := hamysql.NewGormDB(
			hamysql.OptionIP(epoint.Host),
			hamysql.OptionPort(epoint.Port),
			hamysql.OptionProto(epoint.Proto),
			hamysql.OptionDBName(hamodel.DatabaseName),
			hamysql.OptionUser(user),
			hamysql.OptionPassword(password),
			hamysql.OptionLogger(gormLogger),
			hamysql.OptionReadTimeout(timeout),
			hamysql.OptionWriteTimeout(timeout),
		)

		if err != nil {
			return nil, err
		}

		msql.dbs = append(msql.dbs, db)
	}

	return msql, nil
}

func (s *mysql) Save(msg *Message) error {
	startTime := time.Now()
	defer func() {
		if err := apm.MySqlWriteDurationMs.ObserveWithLabels(map[string]string{
			apm.MetricLabelMysql: msg.Topic,
		}, float64(time.Since(startTime).Milliseconds())); err != nil {
			logger.Warn("update mysql write duration metric failed, errmsg: %s", err)
		}
	}()

	dbStatus := &haprobe.HarvestData{}
	if err := json.Unmarshal([]byte(msg.Data), dbStatus); err != nil {
		if metricErr := apm.MySqlReadErrorsTotal.IncWithLabels(map[string]string{
			apm.MetricLabelMysql: msg.Topic,
		}); metricErr != nil {
			logger.Warn("update mysql read errors metric failed, errmsg: %s", metricErr)
		}
		return gerrors.Newf(gerrors.InvalidJson, "unmarshal a mysql metric message failed, topic(%s), %v", msg.Topic, err)
	}

	logger.Debug("outputter(mysql) save msg: %s, raw: %s", string(msg.Data), string(dbStatus.RawValue))

	data := hamodel.NewDbhaData(dbStatus)

	// Route to a per-harvest-type table (same schema) based on HarvestType. Empty/unknown
	// falls back to the core table so no reported data is ever dropped.
	tableName, known := hamodel.GetDbhaStatusTableName(dbStatus.HarvestType)
	if !known {
		logger.Warn("unknown harvest_type, route to default table, harvest_type: %s, topic: %s, table: %s",
			dbStatus.HarvestType, msg.Topic, tableName)
	}

	for _, db := range s.dbs {
		err := db.DB().Session(&gorm.Session{FullSaveAssociations: true}).
			Table(tableName).
			Clauses(clause.OnConflict{UpdateAll: true}).
			Create(data).Error

		if err != nil {
			logger.Warn("save the mysql metric failed, errmsg: %s", err)

			if metricErr := apm.MySqlWriteErrorsTotal.IncWithLabels(map[string]string{
				apm.MetricLabelMysql: msg.Topic,
			}); metricErr != nil {
				logger.Warn("update mysql write errors metric failed, errmsg: %s", metricErr)
			}
		}
	}

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
	return nil
}

func (s *mysql) Close() {
	for _, db := range s.dbs {
		db.Close()
	}
}
