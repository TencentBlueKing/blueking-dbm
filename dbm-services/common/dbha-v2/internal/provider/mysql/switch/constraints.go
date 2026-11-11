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

package mysqlswitch

import (
	"context"
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"

	"gorm.io/gorm"
)

const (
	defaultExecSqlTimeout      = 30 * time.Second
	defaultFlushRoutingTimeout = 30 * time.Second
)

// ExecSqlTimeout returns workflow.switchflow.mysql.execSqlTimeout, or default when unset.
func ExecSqlTimeout() time.Duration {
	d := config.Cfg.Workflow.SwitchFlow.Mysql.ExecSqlTimeout
	if d <= 0 {
		return defaultExecSqlTimeout
	}
	return d
}

// FlushRoutingTimeout returns workflow.switchflow.mysql.tdbctlFlushRoutingTimeout,
// or default when unset. It applies to TDBCTL FLUSH ROUTING [FORCE].
func FlushRoutingTimeout() time.Duration {
	d := config.Cfg.Workflow.SwitchFlow.Mysql.TdbctlFlushRoutingTimeout
	if d <= 0 {
		return defaultFlushRoutingTimeout
	}
	return d
}

// GormWithExecSqlTimeout returns db scoped to ExecSqlTimeout and the cancel func for its context deadline.
func GormWithExecSqlTimeout(db *hamysql.GormDB) (*gorm.DB, context.CancelFunc) {
	return gormWithTimeout(db, ExecSqlTimeout())
}

// GormWithFlushRoutingTimeout returns db scoped to FlushRoutingTimeout and the cancel
// func for its context deadline.
func GormWithFlushRoutingTimeout(db *hamysql.GormDB) (*gorm.DB, context.CancelFunc) {
	return gormWithTimeout(db, FlushRoutingTimeout())
}

func gormWithTimeout(db *hamysql.GormDB, timeout time.Duration) (*gorm.DB, context.CancelFunc) {
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	return db.DBWithContext(ctx), cancel
}
