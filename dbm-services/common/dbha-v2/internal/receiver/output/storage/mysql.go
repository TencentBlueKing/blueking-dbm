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

package storage

import (
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"

	"gorm.io/driver/mysql"
	"gorm.io/gorm"
)

const NameMySQL = "MySQL"

func NewMySQL(endpoint, user, password string, opts ...MySQLOption) (*MySQL, error) {

	mydb := &MySQL{opts: &mysqlOptions{
		endpoint: endpoint,
		user:     user,
		password: password,
	}}

	for _, opt := range opts {
		opt.apply(mydb.opts)
	}

	dsn := mydb.opts.buildDSN()
	db, err := gorm.Open(mysql.Open(dsn), &gorm.Config{})
	if err != nil {
		return nil, gerrors.Newf(gerrors.ComponentFailure, "open the db(%s) failed, errmsg(%v)", dsn, err)
	}
	mydb.db = db

	return mydb, nil
}

type MySQL struct {
	topics map[string]struct{}
	db     *gorm.DB
	opts   *mysqlOptions
}

func (m *MySQL) migrate(topic string) error {
	_ = topic
	return nil
}

func (m *MySQL) Save(msg *Message) error {

	logger.Debug("mysql save:%v", *msg)
	return nil
}

func (m *MySQL) Close() {

}
