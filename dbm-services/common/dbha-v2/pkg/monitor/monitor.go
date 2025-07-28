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

package monitor

import (
	"bytes"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
	"encoding/json"
	"fmt"
	"os/exec"
	"time"

	"golang.org/x/net/context"
)

var (
	agentEndpoint string
	accessToken   string
	bkMonitorBeat string
	dataID        uint64 = 0
	reporterType  string = "agent"
	reporterKind  string = "event"
)

// Event monitor's event
type Event struct {
	DataID      uint64       `json:"data_id"`
	AccessToken string       `json:"access_token"`
	Data        []*EventData `json:"data"`
}

type EventData struct {
	Name   string `json:"event_name"`
	Target string `json:"target"`

	// Precise to the millisecond.
	Timestamp uint64 `json:"timestamp,omitempty"`

	Content struct {
		Content string `json:"content"`
	} `json:"event"`

	Dimension struct {
		// recovery or abnormal, default is abnormal
		Type string `json:"event_type,omitempty"`
	} `json:"dimension"`
}

func SetEndpoint(epoint string) {
	agentEndpoint = epoint
}

func SetAccessToken(token string) {
	accessToken = token
}

func SetBkMonitorBeat(beatPath string) {
	bkMonitorBeat = beatPath
}

func SetDataID(id uint64) {
	dataID = id
}

func SetReportType(rtype string) {
	reporterType = rtype
}

func SetReporterKind(rkind string) {
	reporterKind = rkind
}

func PostBKMonitor(timeout time.Duration, edatas ...*EventData) error {
	if dataID == 0 {
		return gerrors.Newf(gerrors.InvalidParameter, "invalid data id(%d)", dataID)
	}

	if agentEndpoint == "" {
		return gerrors.Newf(gerrors.InvalidParameter, "invalid agent endpoint(%s)", agentEndpoint)
	}

	if timeout < 5*time.Second {
		timeout = 5 * time.Second
	}

	if len(edatas) == 0 {
		return gerrors.New(gerrors.InvalidParameter, "not set any event data")
	}

	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()

	event := &Event{
		DataID:      dataID,
		AccessToken: accessToken,
	}

	for _, data := range edatas {
		if data == nil {
			logger.Warn("invalid event data(nil), data id(%d)", dataID)
			continue
		}
		event.Data = append(event.Data, data)
	}

	if len(event.Data) == 0 {
		logger.Error("invalid event data(nil), data id(%d)", dataID)
		return gerrors.New(gerrors.InvalidParameter, "not set any event data")
	}

	datas, err := json.Marshal(event)
	if err != nil {
		return gerrors.Newf(gerrors.ComponentFailure, "marshal event data failed, %v", err)
	}

	cmd := exec.CommandContext(ctx, bkMonitorBeat, []string{
		"-report",
		"-report.type", reporterType,
		"-report.message.kind", reporterKind,
		"-report.bk_data_id", fmt.Sprintf("%d", dataID),
		"-report.agent.address", agentEndpoint,
		"-report.message.body", string(datas),
	}...)

	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	if err = cmd.Run(); err != nil {
		logger.Error("post bkmonitor event failed, stdout(%s), stderr(%s), %v", stdout.String(), stderr.String(), err)
		return gerrors.Newf(gerrors.ComponentFailure, "post bkmonitor event failed, %v", err)
	}

	return nil
}
