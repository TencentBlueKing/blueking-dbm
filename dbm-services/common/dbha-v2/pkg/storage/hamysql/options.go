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
	"strings"
	"time"

	"dbm-services/common/dbha-v2/pkg/logger"

	"gorm.io/driver/mysql"
)

type Option interface {
	apply(*options) error
}

var defaultOptions = options{
	proto:                     "tcp",
	port:                      3306,
	charset:                   "utf8mb4",
	parseTime:                 func() *bool { b := true; return &b }(),
	loc:                       "Local",
	defaultStringSize:         128,
	disableDatetimePrecision:  true,
	dontSupportRenameIndex:    true,
	dontSupportRenameColumn:   true,
	skipInitializeWithVersion: false,
	disableAutomaticPing:      true,
	logSlowThreshold:          5 * time.Second,
}

type options struct {
	user             string
	password         string
	proto            string
	ip               string
	port             int
	dbName           string
	charset          string
	parseTime        *bool
	loc              string
	timeout          time.Duration
	maxAllowedPacket int

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

	// The slow query threshold for SQL.
	logger                       logger.Logger
	logSlowThreshold             time.Duration
	logIgnoreRecordNotFoundError bool
	logParameterizedQueries      bool
	disableAutomaticPing         bool
}

func (o options) DSN() string {
	// DSN format: "user:pass@tcp(127.0.0.1:3306)/dbname?charset=utf8mb4&parseTime=True&loc=Local"

	dsnBuilder := strings.Builder{}
	dsnBuilder.WriteString(o.user + ":" + o.password + "@")
	dsnBuilder.WriteString(o.proto + "(" + o.ip + ":" + fmt.Sprintf("%d", o.port) + ")")

	if o.dbName != "" {
		dsnBuilder.WriteString("/" + o.dbName)
	} else {
		dsnBuilder.WriteString("/?")
	}

	hasOptions := false
	if o.charset != "" {
		hasOptions = true
		dsnBuilder.WriteString("charset=" + o.charset)
	}

	if o.parseTime != nil {
		if hasOptions {
			dsnBuilder.WriteString(fmt.Sprintf("&parseTime=%t", *o.parseTime))
		} else {
			hasOptions = true
			dsnBuilder.WriteString(fmt.Sprintf("parseTime=%t", *o.parseTime))
		}
	}

	if o.loc != "" {
		if hasOptions {
			dsnBuilder.WriteString("&loc=" + o.loc)
		} else {
			hasOptions = true
			dsnBuilder.WriteString("loc=" + o.loc)
		}
	}

	if o.maxAllowedPacket != 0 {
		if hasOptions {
			dsnBuilder.WriteString(fmt.Sprintf("&maxAllowedPacket=%d", o.maxAllowedPacket))
		} else {
			hasOptions = true
			dsnBuilder.WriteString(fmt.Sprintf("maxAllowedPacket=%d", o.maxAllowedPacket))
		}
	}

	if o.timeout != 0 {
		if hasOptions {
			dsnBuilder.WriteString(fmt.Sprintf("&timeout=%s", o.timeout))
		} else {
			hasOptions = true
			dsnBuilder.WriteString(fmt.Sprintf("timeout=%s", o.timeout))
		}
	}

	return dsnBuilder.String()
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
			opt.parseTime = &val
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

func OptionLogger(val logger.Logger) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.logger = val
			return nil
		},
	}
}

func OptionSkipInitializeWithVersion(val bool) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.skipInitializeWithVersion = val
			return nil
		},
	}
}

func OptionLogSlowThreshold(val time.Duration) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.logSlowThreshold = val
			return nil
		},
	}
}

func OptiionTimeout(val time.Duration) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.timeout = val
			return nil
		},
	}
}

func OptionMaxAllowedPacket(val int) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.maxAllowedPacket = val
			return nil
		},
	}
}

func OptionIgnoreRecordNotFound(val bool) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.logIgnoreRecordNotFoundError = val
			return nil
		},
	}
}

func OptionParameterizedQueries(val bool) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.logParameterizedQueries = val
			return nil
		},
	}
}

func OptionDisableDatetimePrecision(val bool) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.disableDatetimePrecision = val
			return nil
		},
	}
}
