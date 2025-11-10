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

package logger

import (
	"context"
	"errors"
	"fmt"
	"time"

	"gorm.io/gorm/logger"
)

// NewGormLogger make a new logger for GORM
func NewGormLogger(l Logger, c *logger.Config) *GormLogger {
	return &GormLogger{logger: l, cfg: c}
}

// GormLogger is the logger for the GORM
type GormLogger struct {
	logger Logger
	cfg    *logger.Config
}

func (g *GormLogger) LogMode(level logger.LogLevel) logger.Interface {
	newLogger := *g
	return &newLogger
}

func (g *GormLogger) Info(ctx context.Context, msg string, data ...any) {
	if g.logger == nil {
		return
	}

	g.logger.Info(msg, data...)
}

func (g *GormLogger) Warn(ctx context.Context, msg string, data ...any) {
	if g.logger == nil {
		return
	}

	g.logger.Warn(msg, data...)
}

func (g *GormLogger) Error(ctx context.Context, msg string, data ...any) {
	if g.logger == nil {
		return
	}

	g.logger.Error(msg, data...)
}

func (g *GormLogger) Trace(ctx context.Context, begin time.Time, fc func() (string, int64), err error) {
	sql, rows := fc()

	elapsed := time.Since(begin)

	switch {
	case err != nil && (!errors.Is(err, logger.ErrRecordNotFound) || !g.cfg.IgnoreRecordNotFoundError):
		if rows == -1 {
			g.logger.Error("sql: %s, errmsg: %s", sql, err)
			return
		}

		g.logger.Error("affected rows: %d, sql: %s, errmsg: %s", rows, sql, err)

	case elapsed > g.cfg.SlowThreshold && g.cfg.SlowThreshold != 0:
		slowLog := fmt.Sprintf("SLOW SQL >= %v", g.cfg.SlowThreshold)
		if rows == -1 {
			g.logger.Error("slow: %s, sql duration: %v, sql: %s, errmsg: %s",
				rows, slowLog, elapsed, sql, err)
			return
		}

		g.logger.Error("affected rows: %d, slow: %s, duration: %v, sql: %s, errmsg: %s",
			rows, slowLog, elapsed, sql, err)

	default:
		if rows == -1 {
			g.logger.Debug("sql duration: %v, sql: %s", elapsed, sql)
			return
		}

		g.logger.Debug("affected rows: %d, sql duration: %v, sql: %s", rows, elapsed, sql)
	}
}
