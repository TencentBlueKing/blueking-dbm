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
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"

	"gorm.io/gorm"
)

var tables = []any{
	&hamodel.DbhaDataStatus{},
	&hamodel.SkipDbInstance{},
	&hamodel.DbmMetadata{},
	&hamodel.DbSwitchingLog{},
	&hamodel.DbSwitchingStrategy{},
}

const (
	CreateDbIfNotExistSql string = "CREATE DATABASE IF NOT EXISTS `%s` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
)

// Migrator implements database migration
type Migrator struct {
	dbs []*hamysql.GormDB
}

// InitDbhaData initializes the database
func (m *Migrator) InitDbhaData() error {
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

func (m *Migrator) createOrUseDatabase(db *hamysql.GormDB) error {
	sql := fmt.Sprintf(CreateDbIfNotExistSql, hamodel.DatabaseName)
	err := db.DB().Exec(sql).Error
	if err != nil {
		return gerrors.Newf(gerrors.MysqlFailure, "failed to create the database(%s), %v", hamodel.DatabaseName, err)
	}

	gdb := m.switchDatabase(db.DB(), hamodel.DatabaseName)

	if err := gdb.AutoMigrate(tables...); err != nil {
		return gerrors.Newf(gerrors.MysqlFailure, "auto migrate failed, %v", err)
	}

	return nil
}
