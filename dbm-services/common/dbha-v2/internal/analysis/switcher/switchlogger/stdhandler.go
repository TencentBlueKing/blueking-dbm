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
	"encoding/json"

	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
)

// LogToStdHandler writes switch log to standard output
type LogToStdHandler struct {
}

// NewLogToStdHandler creates a new LogToStdHandler
func NewLogToStdHandler() *LogToStdHandler {
	return &LogToStdHandler{}
}

// Open this function does nothing, only for interface
func (hdl *LogToStdHandler) Open() error {
	return nil
}

// Close this function does nothing, only for interface
func (hdl *LogToStdHandler) Close() {
}

// Append appends a switch log record to standard output
func (hdl *LogToStdHandler) Append(record *hamodel.DbSwitchingLog) error {
	if record == nil {
		return gerrors.Newf(gerrors.InvalidParameter, "switch log record for std is nil")
	}

	logJson, marshalErr := json.Marshal(*record)
	if marshalErr != nil {
		return gerrors.Newf(gerrors.InvalidJson, "failed to marshal switch log record: %s", marshalErr.Error())
	}

	logger.Info("[SwitchLog]: %s", string(logJson))
	return nil
}
