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

// Package switchlogger provides different implementations of database switching log
package switchlogger

import (
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
)

// SwitchLogger is the interface for database switching log
type SwitchLogger[T any] interface {
	// Open initialize the resource for logging
	Open() error
	// Close recycle the resource for logging
	Close()
	// Append append a log record. Make sure this method is thread-safe
	Append(record T) error
}

type DbSwitchLogger SwitchLogger[*hamodel.DbSwitchingLog]

type SwitchLogLevel string

// switch log level
const (
	// those log levels are used for switching steps

	SwitchInfo  SwitchLogLevel = "info"
	SwitchWarn  SwitchLogLevel = "warn"
	SwitchError SwitchLogLevel = "error"

	// those log levels are used for switching results

	SwitchFail    SwitchLogLevel = "fail"
	SwitchSuccess SwitchLogLevel = "success"
)
