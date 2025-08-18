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

package migrator

import (
	"dbm-services/common/dbha-v2/internal/admin/config"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/hanet"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"
)

var tables = []interface{}{
	&hamodel.DbhaData{},
	&hamodel.DatabaseMetric{},
	&hamodel.HostMetric{},
	&hamodel.SkipDbInstance{},
	&hamodel.DbmMetadata{},
	&hamodel.MysqlEvent{},
}

type Migrator struct {
	dbs []*hamysql.DB
}

func (m *Migrator) createDatabase(db *hamysql.DB) error {
	if err := db.DB().AutoMigrate(tables...); err != nil {
		return gerrors.Newf(gerrors.ComponentFailure, "auto migrate failed, %v", err)
	}

	return nil
}

func (m *Migrator) InitDbhaData() error {
	epoints, err := hanet.NewEndpoints(config.Cfg.Storage.Endpoint)
	if err != nil {
		return err
	}

	for _, epoint := range epoints {
		db, err := hamysql.New(
			hamysql.OptionProto(epoint.Proto),
			hamysql.OptionIP(epoint.Host),
			hamysql.OptionPort(epoint.Port),
			hamysql.OptionUser(config.Cfg.Storage.User),
			hamysql.OptionPassword(config.Cfg.Storage.Password),
			hamysql.OptionDBName(hamodel.DatabaseName),
		)

		if err != nil {
			return err
		}

		m.dbs = append(m.dbs, db)
	}

	for _, db := range m.dbs {
		if err := m.createDatabase(db); err != nil {
			return err
		}
	}

	return nil
}
