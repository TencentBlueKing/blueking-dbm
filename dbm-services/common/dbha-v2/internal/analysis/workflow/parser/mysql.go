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

package parser

import (
	"encoding/json"

	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

var _ Processer = (*MySqlStatus)(nil)

var (
	ErrInvalidMySqlStatus = gerrors.Newf(gerrors.InvalidParameter, "invalid MySQL status")
)

// MySqlStatus parses MySQL probe status payloads.
type MySqlStatus struct {
}

// Process parses one MySQL raw status payload into a DB event.
func (m *MySqlStatus) Process(task json.RawMessage) (*haprobe.DbEvent, error) {
	var mySqlStatus haprobe.MySqlStatus
	if err := json.Unmarshal(task, &mySqlStatus); err != nil {
		logger.Warn("failed to unmarshal MySQL status, errmsg: %s", err)
		return nil, ErrInvalidMySqlStatus
	}

	// Note: MySqlStatus fields are pointers and may be nil; guard before dereferencing.
	logger.Debug("process MySQL status: %v, raw: %s", mySqlStatus.GlobalStatus, string(task))
	return nil, nil
}

func init() {
	Register(haprobe.DbTypeMySql, &MySqlStatus{})
}
