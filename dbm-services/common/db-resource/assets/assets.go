/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package assets assets
package assets

import (
	"embed"
	"fmt"

	"github.com/golang-migrate/migrate/v4"
	_ "github.com/golang-migrate/migrate/v4/database/mysql" // mysql TODO
	"github.com/golang-migrate/migrate/v4/source"
	"github.com/golang-migrate/migrate/v4/source/iofs"
	"github.com/pkg/errors"

	"dbm-services/common/go-pubpkg/logger"
)

// Migrations embed migrations sqlfile

//go:embed migrations/*.sql
var fs embed.FS

// DoMigrateFromEmbed  do migrate from embed
func DoMigrateFromEmbed(user, addr, password, dbname string) (err error) {
	var mig *migrate.Migrate
	var d source.Driver
	if d, err = iofs.New(fs, "migrations"); err != nil {
		return err
	}
	dbURL := fmt.Sprintf(
		"mysql://%s:%s@tcp(%s)/%s?charset=%s&parseTime=true&loc=Local&multiStatements=true&interpolateParams=true",
		user,
		password,
		addr,
		dbname,
		"utf8",
	)
	mig, err = migrate.NewWithSourceInstance("iofs", d, dbURL)
	if err != nil {
		return errors.WithMessage(err, "migrate from embed")
	}
	defer mig.Close()
	if err = mig.Up(); err != nil {
		if err == migrate.ErrNoChange {
			logger.Info("migrate source from embed success with", "msg", err.Error())
			return nil
		}
		logger.Error("migrate source from embed failed", err)
		return err
	}
	logger.Info("migrate source from embed success")
	return nil
}
