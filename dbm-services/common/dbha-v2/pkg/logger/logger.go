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

import "log"

// Logger is a universal logging interface that can be
// flexibly replaced with other logging libraies
// without interfering with the operational logic
// of business code.
type Logger interface {
	Debug(format string, args ...interface{})
	Info(format string, args ...interface{})
	Warn(format string, args ...interface{})
	Error(format string, args ...interface{})
	Fatal(format string, args ...interface{})
}

type Level string

var (
	DebugLevel Level = "debug"
	InfoLevel  Level = "info"
	WarnLevel  Level = "warn"
	ErrorLevel Level = "error"
	FatalLevel Level = "fatal"
)

// Config logger config
type Config struct {
	FileName   string
	LogLevel   Level
	MaxSizeMB  int
	MaxBackups int
	MaxAge     int
}

var dblog Logger

func SetLogger(log Logger) {
	dblog = log
}

func Log() Logger {
	return dblog
}

func Debug(format string, args ...interface{}) {
	if dblog == nil {
		log.Printf(format, args...)
		return
	}

	dblog.Debug(format, args...)
}

func Info(format string, args ...interface{}) {
	if dblog == nil {
		log.Printf(format, args...)
		return
	}

	dblog.Info(format, args...)
}

func Warn(format string, args ...interface{}) {
	if dblog == nil {
		log.Printf(format, args...)
		return
	}

	dblog.Warn(format, args...)
}

func Error(format string, args ...interface{}) {
	if dblog == nil {
		log.Printf(format, args...)
		return
	}

	dblog.Error(format, args...)
}

func Fatal(format string, args ...interface{}) {
	if dblog == nil {
		log.Fatalf(format, args...)
		return
	}

	dblog.Fatal(format, args...)
}
