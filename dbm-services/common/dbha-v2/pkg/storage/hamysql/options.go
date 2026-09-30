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

// Option applies configuration to MySQL client options.
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
	user                 string
	password             string
	proto                string
	ip                   string
	port                 int
	dbName               string
	charset              string
	parseTime            *bool
	loc                  string
	timeout              time.Duration
	readTimeout          time.Duration
	writeTimeout         time.Duration
	maxAllowedPacket     int
	autoMaxAllowedPacket bool
	interpolateParams    bool
	maxOpenConns         int
	maxIdleConns         int
	connMaxLifetime      time.Duration

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

func (o options) BuildDSNString(coverPassword bool) string {
	// DSN format: "user:pass@tcp(127.0.0.1:3306)/dbname?charset=utf8mb4&parseTime=True&loc=Local"

	dsnBuilder := strings.Builder{}

	if coverPassword {
		dsnBuilder.WriteString(o.user + ":" + "<secret>" + "@")
	} else {
		dsnBuilder.WriteString(o.user + ":" + o.password + "@")
	}

	dsnBuilder.WriteString(o.proto + "(" + o.ip + ":" + fmt.Sprintf("%d", o.port) + ")")

	if o.dbName != "" {
		dsnBuilder.WriteString("/" + o.dbName + "?")
	} else {
		dsnBuilder.WriteString("/?")
	}

	hasOptions := false
	appendOpt := func(kv string) {
		if hasOptions {
			dsnBuilder.WriteString("&")
		}
		hasOptions = true
		dsnBuilder.WriteString(kv)
	}

	if o.charset != "" {
		appendOpt("charset=" + o.charset)
	}

	if o.parseTime != nil {
		appendOpt(fmt.Sprintf("parseTime=%t", *o.parseTime))
	}

	if o.loc != "" {
		appendOpt("loc=" + o.loc)
	}

	// OptionAutoMaxAllowedPacket takes precedence over OptionMaxAllowedPacket.
	if o.autoMaxAllowedPacket {
		appendOpt("maxAllowedPacket=0")
	} else if o.maxAllowedPacket != 0 {
		appendOpt(fmt.Sprintf("maxAllowedPacket=%d", o.maxAllowedPacket))
	}

	if o.timeout != 0 {
		appendOpt(fmt.Sprintf("timeout=%s", o.timeout))
	}

	if o.readTimeout != 0 {
		appendOpt(fmt.Sprintf("readTimeout=%s", o.readTimeout))
	}

	if o.writeTimeout != 0 {
		appendOpt(fmt.Sprintf("writeTimeout=%s", o.writeTimeout))
	}

	if o.interpolateParams {
		appendOpt("interpolateParams=true")
	}

	return dsnBuilder.String()
}

func (o options) DSN() string {
	return o.BuildDSNString(false)
}

func (o options) SafeDSN() string {
	return o.BuildDSNString(true)
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

// OptionUser sets the mysql username.
func OptionUser(val string) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.user = val
			return nil
		},
	}
}

// OptionPassword sets the mysql password.
func OptionPassword(val string) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.password = val
			return nil
		},
	}
}

// OptionProto sets the mysql connection protocol, such as tcp.
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

// OptionIP sets the mysql server IP address.
func OptionIP(val string) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.ip = val
			return nil
		},
	}
}

// OptionPort sets the mysql server port.
func OptionPort(val int) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.port = val
			return nil
		},
	}
}

// OptionDBName sets the mysql database name.
func OptionDBName(val string) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.dbName = val
			return nil
		},
	}
}

// OptionCharset sets the mysql charset in DSN.
func OptionCharset(val string) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.charset = val
			return nil
		},
	}
}

// OptionParseTime sets whether to parse time values.
func OptionParseTime(val bool) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.parseTime = &val
			return nil
		},
	}
}

// OptionLoc sets location for time parsing.
func OptionLoc(val string) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.loc = val
			return nil
		},
	}
}

// OptionLogger sets the logger used by mysql storage layer.
func OptionLogger(val logger.Logger) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.logger = val
			return nil
		},
	}
}

// OptionSkipInitializeWithVersion controls whether to skip version-based auto config.
func OptionSkipInitializeWithVersion(val bool) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.skipInitializeWithVersion = val
			return nil
		},
	}
}

// OptionLogSlowThreshold sets slow SQL logging threshold.
func OptionLogSlowThreshold(val time.Duration) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.logSlowThreshold = val
			return nil
		},
	}
}

// OptionTimeout sets mysql connection timeout in DSN.
func OptionTimeout(val time.Duration) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.timeout = val
			return nil
		},
	}
}

// OptionReadTimeout sets readTimeout in DSN.
func OptionReadTimeout(val time.Duration) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.readTimeout = val
			return nil
		},
	}
}

// OptionWriteTimeout sets writeTimeout in DSN.
func OptionWriteTimeout(val time.Duration) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.writeTimeout = val
			return nil
		},
	}
}

// OptionMaxAllowedPacket sets maxAllowedPacket in DSN.
// Ignored when OptionAutoMaxAllowedPacket(true) is also set.
func OptionMaxAllowedPacket(val int) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.maxAllowedPacket = val
			return nil
		},
	}
}

// OptionAutoMaxAllowedPacket writes maxAllowedPacket=0 into the DSN so the
// driver queries the server limit on each new connection. Takes precedence
// over OptionMaxAllowedPacket. Intended for standard MySQL with interpolateParams.
func OptionAutoMaxAllowedPacket(val bool) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.autoMaxAllowedPacket = val
			return nil
		},
	}
}

// OptionInterpolateParams enables client-side parameter interpolation in DSN.
// Only for standard MySQL with a driver-recognized safe charset (e.g. utf8mb4).
// Do not use for proxy/tdbctl management ports.
func OptionInterpolateParams(val bool) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.interpolateParams = val
			return nil
		},
	}
}

// OptionMaxOpenConns sets sql.DB MaxOpenConns. Applied only by NewGormDB when
// non-zero. Zero leaves the database/sql default unchanged.
func OptionMaxOpenConns(val int) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.maxOpenConns = val
			return nil
		},
	}
}

// OptionMaxIdleConns sets sql.DB MaxIdleConns. Applied only by NewGormDB when
// non-zero. Zero leaves the database/sql default unchanged.
func OptionMaxIdleConns(val int) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.maxIdleConns = val
			return nil
		},
	}
}

// OptionConnMaxLifetime sets sql.DB ConnMaxLifetime. Applied only by NewGormDB when
// non-zero. Zero leaves the database/sql default unchanged.
func OptionConnMaxLifetime(val time.Duration) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.connMaxLifetime = val
			return nil
		},
	}
}

// OptionIgnoreRecordNotFound sets whether to ignore record-not-found logs.
func OptionIgnoreRecordNotFound(val bool) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.logIgnoreRecordNotFoundError = val
			return nil
		},
	}
}

// OptionParameterizedQueries sets whether to parameterize SQL logs.
func OptionParameterizedQueries(val bool) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.logParameterizedQueries = val
			return nil
		},
	}
}

// OptionDisableDatetimePrecision sets whether datetime precision is disabled.
func OptionDisableDatetimePrecision(val bool) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.disableDatetimePrecision = val
			return nil
		},
	}
}
