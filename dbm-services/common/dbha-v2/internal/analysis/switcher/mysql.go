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

package switcher

import (
	"context"

	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/monitor"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

var _ Switcher = (*Mysql)(nil)

type Mysql struct {
}

func (m *Mysql) DbTypeName() haprobe.DbType {
	return haprobe.DbTypeMysql
}

func (m *Mysql) Switch(ctx context.Context, req *Request) *Response {
	// TODO: Need to implement the switching logic with the switching strategy.

	rsp := &Response{}

	for _, event := range req.BreakdownEvents {
		monitorEvent := &monitor.EventData{
			Name:      event.Name.String(),
			Target:    event.Endpoint,
			Timestamp: uint64(event.UpdatedAt.UnixMilli()),
		}

		monitorEvent.Content.Content = event.Message
		monitorEvent.Dimension.BkCloudID = event.BkCloudID
		monitorEvent.Dimension.IP = event.IP
		monitorEvent.Dimension.Port = event.Port
		monitorEvent.Dimension.DbTypeName = event.DbTypeName
		monitorEvent.Dimension.DbEventName = event.Name
		monitorEvent.Dimension.DbEventNameReason = event.Reason

		if err := monitor.PostBKMonitor(config.Cfg.Monitor.Timeout, monitorEvent); err != nil {
			logger.Warn("%v", err)
		}

		logger.Debug("check the business(event): %s %s", event.Endpoint, event.Message)
	}

	return rsp
}
