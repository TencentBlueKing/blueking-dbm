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

package switchlogger

import (
	"sync"

	"dbm-services/common/dbha-v2/pkg/gerrors"
)

// NewSwitchLoggers creates the default switch logger set (stdout + db) and a release function.
// Callers should defer the returned release to close logger resources.
// On partial failure the stdout logger is still returned so switching can continue to record logs.
func NewSwitchLoggers() (loggers []DbSwitchLogger, release func(), err error) {
	loggers = []DbSwitchLogger{
		NewLogToStdHandler(),
	}
	loggers[0].Open()
	release = newSwitchLoggersRelease(loggers)

	dbHdl, newDbHdlErr := NewLogToDbHandlerFromConfig()
	if newDbHdlErr != nil {
		return loggers, release, gerrors.Newf(gerrors.Failure, "failed to create db switch logger: %s",
			newDbHdlErr.Error())
	}

	if openErr := dbHdl.Open(); openErr != nil {
		return loggers, release, gerrors.Newf(gerrors.Failure, "failed to open db switch logger: %s", openErr.Error())
	}

	loggers = append(loggers, dbHdl)
	release = newSwitchLoggersRelease(loggers)
	return loggers, release, nil
}

func newSwitchLoggersRelease(loggers []DbSwitchLogger) func() {
	var once sync.Once
	return func() {
		once.Do(func() {
			for _, switchLogger := range loggers {
				if switchLogger == nil {
					continue
				}
				switchLogger.Close()
			}
		})
	}
}
