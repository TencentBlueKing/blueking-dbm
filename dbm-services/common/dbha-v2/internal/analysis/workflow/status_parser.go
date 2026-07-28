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

package workflow

import (
	"dbm-services/common/dbha-v2/internal/analysis/parser"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

var (
	ErrUnknownDbType = gerrors.Newf(gerrors.InvalidParameter, "unknown DB type")
)

// StatusParser used to parse all DB statuses.
type StatusParser struct{}

// ParseDbStatus Parse the DB status
func (s *StatusParser) ParseDbStatus(dbStatus []parser.DBTyperWrapper) ([]*haprobe.DbEvent, error) {
	var dbEvents []*haprobe.DbEvent

	for _, v := range dbStatus {
		logger.Debug("parse DB status, DB type: %v", v.DbTypeName)

		processer, ok := parser.Lookup(v.DbTypeName)
		if !ok {
			logger.Warn("no processer for DB type: %v", v.DbTypeName)
			continue
		}

		event, err := processer.Process(v.Value)
		if err != nil {
			logger.Warn("failed to parse DB status, DB type: %s, errmsg: %s", v.DbTypeName, err)
			continue
		}

		if event != nil {
			dbEvents = append(dbEvents, event)
		}

	}

	return dbEvents, nil
}

// ParseHostStatus Parse the host status
func (s *StatusParser) ParseHostStatus(dbStatus []*haprobe.HostMetric) ([]*haprobe.DbEvent, error) {
	// TODO:
	return nil, nil
}
