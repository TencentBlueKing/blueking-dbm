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

package hamysql

import (
	"fmt"

	"dbm-services/common/dbha-v2/pkg/gerrors"

	"gorm.io/driver/mysql"
	"gorm.io/gorm"
)

type DB struct {
	gdb  *gorm.DB
	opts options
}

func createDatabase(opts *options) (*gorm.DB, error) {
	gdb, err := gorm.Open(mysql.New(opts.RootDBConfig()), &gorm.Config{})
	if err != nil {
		return nil, gerrors.Newf(gerrors.ComponentFailure, "failed to connect the mysql, %v", err)
	}

	if opts.dbName == "" {
		return gdb, nil
	}

	sql := fmt.Sprintf("CREATE DATABASE IF NOT EXISTS `%s` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci", opts.dbName)
	err = gdb.Exec(sql).Error
	if err != nil {
		return nil, gerrors.Newf(gerrors.ComponentFailure, "failed to create the database(%s), %v", opts.dbName, err)
	}

	return gorm.Open(mysql.New(opts.Config()), &gorm.Config{})
}

func New(opts ...Option) (*DB, error) {
	db := &DB{
		opts: defaultOptions,
	}

	for _, opt := range opts {
		if err := opt.apply(&db.opts); err != nil {
			return nil, err
		}
	}

	gdb, err := gorm.Open(mysql.New(db.opts.Config()), &gorm.Config{})
	if err == nil {
		db.gdb = gdb
		return db, nil
	}

	gdb, err = createDatabase(&db.opts)
	if err != nil {
		if db.opts.dbName == "" {
			return nil, gerrors.NewE(gerrors.ComponentFailure, err)
		}

		return nil, gerrors.Newf(gerrors.ComponentFailure, "gorm open the db(%s) failure, %v", db.opts.dbName, err)
	}

	db.gdb = gdb
	return db, nil
}

func (db DB) DB() *gorm.DB {
	return db.gdb
}

func (db DB) Host() string {
	return db.opts.ip
}

func (db DB) Port() int {
	return db.opts.port
}
