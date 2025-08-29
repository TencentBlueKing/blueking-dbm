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

	"gorm.io/driver/mysql"
)

type Option interface {
	apply(*options) error
}

var defaultOptions = options{
	proto:                     "tcp",
	port:                      3306,
	charset:                   "utf8mb4",
	parseTime:                 true,
	loc:                       "Local",
	defaultStringSize:         128,
	disableDatetimePrecision:  true,
	dontSupportRenameIndex:    true,
	dontSupportRenameColumn:   true,
	skipInitializeWithVersion: false,
}

type options struct {
	user      string
	password  string
	proto     string
	ip        string
	port      int
	dbName    string
	charset   string
	parseTime bool
	loc       string

	// The default length of string type fields.
	defaultStringSize uint

	// Disable datetime precision. Databases prior to MySQL 5.6 do not support it.
	disableDatetimePrecision bool

	// When renaming an index, the method of deleting and creating a new one is adopted.
	// Databases prior to MySQL 5.7 and MariaDB do not support renaming indexes.
	dontSupportRenameIndex bool

	// Rename the column using 'change'.
	// MySQL version prior to 8 and MariaDB do not supporet renaming columns.
	dontSupportRenameColumn bool

	// Automatically configure based on the current MySQL version.
	skipInitializeWithVersion bool
}

func (o options) DSN() string {
	// DSN format: "user:pass@tcp(127.0.0.1:3306)/dbname?charset=utf8mb4&parseTime=True&loc=Local"
	dsn := fmt.Sprintf("%s:%s@%s(%s:%d)/%s?charset=%s&parseTime=%t&loc=%s", o.user, o.password, o.proto,
		o.ip, o.port, o.dbName, o.charset, o.parseTime, o.loc)

	return dsn
}

func (o options) RootDBDSN() string {
	// DSN format: "user:pass@tcp(127.0.0.1:3306)/dbname?charset=utf8mb4&parseTime=True&loc=Local"
	dsn := fmt.Sprintf("%s:%s@%s(%s:%d)/?charset=%s&parseTime=%t&loc=%s", o.user, o.password, o.proto,
		o.ip, o.port, o.charset, o.parseTime, o.loc)

	return dsn
}

func (o options) Config() mysql.Config {
	return mysql.Config{
		DSN:                       o.DSN(),
		DefaultStringSize:         o.defaultStringSize,
		DisableDatetimePrecision:  o.disableDatetimePrecision,
		DontSupportRenameIndex:    o.dontSupportRenameIndex,
		DontSupportRenameColumn:   o.dontSupportRenameColumn,
		SkipInitializeWithVersion: o.skipInitializeWithVersion,
	}
}

func (o options) RootDBConfig() mysql.Config {
	return mysql.Config{
		DSN:                       o.RootDBDSN(),
		DefaultStringSize:         o.defaultStringSize,
		DisableDatetimePrecision:  o.disableDatetimePrecision,
		DontSupportRenameIndex:    o.dontSupportRenameIndex,
		DontSupportRenameColumn:   o.dontSupportRenameColumn,
		SkipInitializeWithVersion: o.skipInitializeWithVersion,
	}
}

type funcOptions struct {
	f func(opt *options) error
}

func (fdo *funcOptions) apply(opt *options) error {
	return fdo.f(opt)
}

func OptionUser(val string) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.user = val
			return nil
		},
	}
}

func OptionPassword(val string) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.password = val
			return nil
		},
	}
}

func OptionProto(val string) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			if val != "" {
				opt.proto = val
			}
			return nil
		},
	}
}

func OptionIP(val string) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.ip = val
			return nil
		},
	}
}

func OptionPort(val int) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.port = val
			return nil
		},
	}
}

func OptionDBName(val string) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.dbName = val
			return nil
		},
	}
}

func OptionCharset(val string) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.charset = val
			return nil
		},
	}
}

func OptionParseTime(val bool) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.parseTime = val
			return nil
		},
	}
}

func OptionLoc(val string) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.loc = val
			return nil
		},
	}
}
