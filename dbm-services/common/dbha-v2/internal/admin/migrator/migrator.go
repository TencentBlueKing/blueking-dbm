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

// Package migrator provides database migration functionality
package migrator

import (
	"fmt"

	"dbm-services/common/dbha-v2/internal/admin/config"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/hanet"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"

	"gorm.io/gorm"
)

const (
	// MigrateTypeSchema migrate table schema only
	MigrateTypeSchema = "schema"
	// MigrateTypeStrategy create default global strategies only
	MigrateTypeStrategy = "strategy"
	// MigrateTypeAll execute all migrations
	MigrateTypeAll = "all"
)

// defaultGlobalStrategies defines the default global strategy list
var defaultGlobalStrategies = []hamodel.DbSwitchingStrategy{
	{
		Name:                   haprobe.DbEventNameDoubleCheckSshFailureV1.String(),
		BkBizID:                0,
		Status:                 hamodel.StatusTypeEnabled,
		TriggerEventName:       haprobe.DbEventNameDoubleCheckSshFailureV1,
		TriggerEventNameReason: haprobe.DbEventNameReasonConnectionException,
		TriggerCount:           1,
		Priority:               9999,
		Scope:                  hamodel.ActionScopeTypeHost,
		Action:                 hamodel.ActionTypeSwitch,
		Description:            "",
	},
	{
		Name:                   haprobe.DbEventNameSshAuthFailure.String(),
		BkBizID:                0,
		Status:                 hamodel.StatusTypeEnabled,
		TriggerEventName:       haprobe.DbEventNameSshAuthFailure,
		TriggerEventNameReason: haprobe.DbEventNameReasonSSHAuthException,
		TriggerCount:           1,
		Priority:               9999,
		Scope:                  hamodel.ActionScopeTypeHost,
		Action:                 hamodel.ActionTypeSwitch,
		Description:            "",
	},
	{
		Name:                   haprobe.DbEventNameSshTimeout.String(),
		BkBizID:                0,
		Status:                 hamodel.StatusTypeEnabled,
		TriggerEventName:       haprobe.DbEventNameSshTimeout,
		TriggerEventNameReason: haprobe.DbEventNameReasonSshTimeout,
		TriggerCount:           1,
		Priority:               9999,
		Scope:                  hamodel.ActionScopeTypeHost,
		Action:                 hamodel.ActionTypeSwitch,
		Description:            "",
	},
	{
		Name:                   haprobe.DbEventNameDiskWriteFailure.String(),
		BkBizID:                0,
		Status:                 hamodel.StatusTypeEnabled,
		TriggerEventName:       haprobe.DbEventNameDiskWriteFailure,
		TriggerEventNameReason: haprobe.DbEventNameReasonDiskWriteException,
		TriggerCount:           1,
		Priority:               9999,
		Scope:                  hamodel.ActionScopeTypeHost,
		Action:                 hamodel.ActionTypeSwitch,
		Description:            "",
	},
	{
		Name:                   haprobe.DbEventNameUptimeFailure.String(),
		BkBizID:                0,
		Status:                 hamodel.StatusTypeEnabled,
		TriggerEventName:       haprobe.DbEventNameUptimeFailure,
		TriggerEventNameReason: haprobe.DbEventNameReasonUptimeException,
		TriggerCount:           1,
		Priority:               9999,
		Scope:                  hamodel.ActionScopeTypeHost,
		Action:                 hamodel.ActionTypeSwitch,
		Description:            "",
	},
}

var tables = []any{
	&hamodel.DbhaDataStatus{},
	&hamodel.SkipDbInstance{},
	&hamodel.DbmMetadata{},
	&hamodel.DbSwitchingLog{},
	&hamodel.DbSwitchingSnapshotLog{},
	&hamodel.DbSwitchingStrategy{},
}

const (
	CreateDbIfNotExistSql string = "CREATE DATABASE IF NOT EXISTS `%s` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
)

// Migrator implements database migration
type Migrator struct {
	dbs []*hamysql.GormDB
}

// initDbs initializes database connections
func (m *Migrator) initDbs() error {
	if len(m.dbs) > 0 {
		return nil
	}

	epoints, err := hanet.NewEndpoints(config.Cfg.Storage.Endpoint)
	if err != nil {
		return err
	}

	for _, epoint := range epoints {
		db, err := hamysql.NewGormDB(
			hamysql.OptionProto(epoint.Proto),
			hamysql.OptionIP(epoint.Host),
			hamysql.OptionPort(epoint.Port),
			hamysql.OptionUser(config.Cfg.Storage.User),
			hamysql.OptionPassword(config.Cfg.Storage.Password),
		)

		if err != nil {
			return err
		}

		m.dbs = append(m.dbs, db)
	}
	return nil
}

// MigrateSchema migrates table schema
func (m *Migrator) MigrateSchema() error {
	if err := m.initDbs(); err != nil {
		return err
	}

	for _, db := range m.dbs {
		if err := m.createAndMigrateSchema(db); err != nil {
			return err
		}
	}
	return nil
}

// MigrateStrategy creates default global strategies
func (m *Migrator) MigrateStrategy() error {
	if err := m.initDbs(); err != nil {
		return err
	}

	for _, db := range m.dbs {
		gdb := m.switchDatabase(db.DB(), hamodel.DatabaseName)
		if err := m.createDefaultGlobalStrategies(gdb); err != nil {
			return err
		}
	}
	return nil
}

// MigrateAll executes all migrations (table schema + default global strategies)
func (m *Migrator) MigrateAll() error {
	if err := m.initDbs(); err != nil {
		return err
	}

	for _, db := range m.dbs {
		if err := m.createOrUseDatabase(db); err != nil {
			return err
		}
	}
	return nil
}

func (m *Migrator) switchDatabase(db *gorm.DB, dbName string) *gorm.DB {
	return db.Session(&gorm.Session{}).Exec("USE " + dbName)
}

// createAndMigrateSchema creates database and migrates table schema only
func (m *Migrator) createAndMigrateSchema(db *hamysql.GormDB) error {
	sql := fmt.Sprintf(CreateDbIfNotExistSql, hamodel.DatabaseName)
	err := db.DB().Exec(sql).Error
	if err != nil {
		return gerrors.Newf(gerrors.MysqlFailure, "failed to create the database(%s), errmsg: %s", hamodel.DatabaseName, err)
	}

	gdb := m.switchDatabase(db.DB(), hamodel.DatabaseName)

	if err := gdb.AutoMigrate(tables...); err != nil {
		return gerrors.Newf(gerrors.MysqlFailure, "auto migrate failed, errmsg: %s", err)
	}

	return nil
}

func (m *Migrator) createOrUseDatabase(db *hamysql.GormDB) error {
	if err := m.createAndMigrateSchema(db); err != nil {
		return err
	}

	gdb := m.switchDatabase(db.DB(), hamodel.DatabaseName)

	// create default global strategies
	if err := m.createDefaultGlobalStrategies(gdb); err != nil {
		return err
	}

	return nil
}

// createDefaultGlobalStrategies creates default global strategies.
func (m *Migrator) createDefaultGlobalStrategies(db *gorm.DB) error {
	for _, strategy := range defaultGlobalStrategies {
		exists, err := m.isStrategyExists(db, &strategy)
		if err != nil {
			return err
		}
		if exists {
			logger.Info("default global strategy already exists, skip. trigger_event_name:%s",
				strategy.TriggerEventName.String())
			continue
		}

		if err := db.Model(&hamodel.DbSwitchingStrategy{}).Create(&strategy).Error; err != nil {
			return gerrors.Newf(gerrors.MysqlFailure,
				"failed to create default global strategy(%s), errmsg: %s", strategy.Name, err)
		}
		logger.Info("default global strategy created successfully. name:%s, trigger_event_name:%s",
			strategy.Name, strategy.TriggerEventName.String())
	}
	return nil
}

// isStrategyExists checks whether a strategy with the same TriggerEventName already exists.
func (m *Migrator) isStrategyExists(db *gorm.DB, strategy *hamodel.DbSwitchingStrategy) (bool, error) {
	var count int64
	err := db.Session(&gorm.Session{}).Model(&hamodel.DbSwitchingStrategy{}).
		Where(map[string]any{
			hamodel.DbSwitchingStrategyFieldBkBizID:          strategy.BkBizID,
			hamodel.DbSwitchingStrategyFieldTriggerEventName: strategy.TriggerEventName,
		}).Count(&count).Error
	if err != nil {
		return false, gerrors.Newf(gerrors.MysqlFailure,
			"failed to query default global strategy(%s), errmsg: %s", strategy.Name, err)
	}
	return count > 0, nil
}
