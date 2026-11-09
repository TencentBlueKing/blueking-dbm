// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package rollback

import (
	"fmt"
	"strconv"
	"strings"

	"dbm-services/redis/db-tools/dbactuator/mylog"
)

// The node log puts a prefix of about 61 characters, ending in the dest IP, before each record
// and shows about 117 in a row; a record wider than that is cut off. Every record of the rollback
// therefore keeps its first line within headWidth and the lines after it within lineWidth.
const (
	headWidth = 50
	lineWidth = 80
	// wrapIndent starts the rest of a line broken to fit.
	wrapIndent = "  "
)

const (
	levelInfo  = "info"
	levelWarn  = "warn"
	levelError = "error"
	// levelProgress is info that rollback-exercise analysis leaves out.
	levelProgress = "progress"
)

// emitLog is replaced in tests, which read the records back.
var emitLog = emit

func emit(level, msg string) {
	switch level {
	case levelWarn:
		mylog.Logger.Warn("%s", msg)
	case levelError:
		mylog.Logger.Error("%s", msg)
	case levelProgress:
		mylog.Logger.InfoNotForAi("%s", msg)
	default:
		mylog.Logger.Info("%s", msg)
	}
}

func logRecord(level, format string, args ...interface{}) {
	msg := format
	if len(args) > 0 {
		msg = fmt.Sprintf(format, args...)
	}
	emitLog(level, wrapRecord(msg))
}

func logInfo(format string, args ...interface{})  { logRecord(levelInfo, format, args...) }
func logWarn(format string, args ...interface{})  { logRecord(levelWarn, format, args...) }
func logError(format string, args ...interface{}) { logRecord(levelError, format, args...) }

// portLog prefixes every record with the port it is about, so concurrent ports stay apart in the
// node log. Shard and source are given once per port, in the opening summary.
type portLog struct {
	prefix string
}

func newPortLog(port int) portLog {
	return portLog{prefix: "[" + strconv.Itoa(port) + "] "}
}

func (l portLog) Info(format string, args ...interface{}) {
	logRecord(levelInfo, "%s", l.prefix+fmt.Sprintf(format, args...))
}

func (l portLog) Warn(format string, args ...interface{}) {
	logRecord(levelWarn, "%s", l.prefix+fmt.Sprintf(format, args...))
}

func (l portLog) Error(format string, args ...interface{}) {
	logRecord(levelError, "%s", l.prefix+fmt.Sprintf(format, args...))
}

// wrapRecord breaks the lines of msg that do not fit, at a space where there is one.
func wrapRecord(msg string) string {
	var out []string
	for i, line := range strings.Split(strings.TrimRight(msg, "\n"), "\n") {
		width := lineWidth
		if i == 0 {
			width = headWidth
		}
		out = append(out, wrapLine(line, width)...)
	}
	return strings.Join(out, "\n")
}

func wrapLine(line string, width int) []string {
	var out []string
	rest := []rune(strings.TrimRight(line, " "))
	for len(rest) > width {
		cut := width
		for j := width; j > width/2; j-- {
			if rest[j] == ' ' {
				cut = j
				break
			}
		}
		out = append(out, strings.TrimRight(string(rest[:cut]), " "))
		rest = append([]rune(wrapIndent), []rune(strings.TrimLeft(string(rest[cut:]), " "))...)
		width = lineWidth
	}
	return append(out, string(rest))
}
