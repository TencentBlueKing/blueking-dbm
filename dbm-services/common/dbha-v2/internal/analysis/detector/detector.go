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

// Package detector provides probe health detection and target selection for DBHA analysis.
package detector

import (
	"errors"
	"fmt"
	"strconv"
	"sync"
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/apm"
	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/haapm"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/safe"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

var (
	ErrDetectorProbeNotRunning = gerrors.Newf(gerrors.ProbeFailure, "probe is not running")
	ErrDetectorNoTarget        = gerrors.Newf(gerrors.InvalidParameter, "no detected target")
)

// DoubleCheckTask represents the double-check task.
type DoubleCheckTask struct {
	Meta   *hamodel.DbmMetadata
	DbType haprobe.DbType
}

// Response represents the response of the detector.
type Response struct {
	Id                string
	Meta              *hamodel.DbmMetadata
	DbType            haprobe.DbType
	DbEventName       haprobe.DbEventName
	DbEventNameReason haprobe.DbEventNameReason
	Err               error
	SshResp           *SshResponse

	// CheckStartTime and CheckFinishedTime are the start and end times of the instance's
	// SSH double-check detection.
	CheckStartTime    *time.Time
	CheckFinishedTime *time.Time
}

// Detector is used to detect whether the host or the probe is alive.
type Detector struct {
	wg        sync.WaitGroup
	tasks     map[string]*detectorTask
	ServiceID string
}

// Detect detects the health of the host or the probe.
func (d *Detector) Detect(dbInsts []DoubleCheckTask) error {
	if len(dbInsts) == 0 {
		return ErrDetectorNoTarget
	}

	d.tasks = map[string]*detectorTask{}

	for _, inst := range dbInsts {
		task := &detectorTask{
			meta:      inst.Meta,
			dbType:    inst.DbType,
			serviceID: d.ServiceID,
			sshCli: &Ssh{
				ip:       inst.Meta.IP,
				port:     config.Cfg.Detector.Ssh.Port,
				user:     config.Cfg.Detector.Ssh.User,
				password: config.Cfg.Detector.Ssh.Password,
				timeout:  config.Cfg.Detector.Ssh.Timeout,
			},
		}

		if _, exists := d.tasks[task.id()]; exists {
			logger.Debug("the task: %s is already in the task queue", task.id())
			continue
		}

		d.tasks[task.id()] = task

		logger.Debug("push detector task: %p task-id: %s, resp: %p task-cnt: %d",
			task, task.id(), task.resp, len(d.tasks))

		d.wg.Add(1)
		go func(task *detectorTask) {
			defer d.wg.Done()
			task.runWithGuard(config.Cfg.Detector.CheckProbeProcessCmd)
		}(task)
	}

	return nil
}

// WaitResponses waits for the responses of the detector.
func (d *Detector) WaitResponses() []*Response {
	d.wg.Wait()
	resps := []*Response{}

	for key, task := range d.tasks {
		logger.Debug("pop key: %s detector task: %p task-id: %s, resp: %p, task-cnt: %d",
			key, task, task.id(), task.resp, len(d.tasks))

		resps = append(resps, task.resp)
	}

	logger.Debug("detector task response cnt: %d, task-cnt: %d", len(resps), len(d.tasks))

	return resps
}

type detectorTask struct {
	meta      *hamodel.DbmMetadata
	dbType    haprobe.DbType
	resp      *Response
	sshCli    *Ssh
	serviceID string
}

func (d *detectorTask) id() string {
	return d.sshCli.Id()
}

// detectTaskGrace is the extra time the outer guard waits beyond the inner probe
// budget before it gives up on the task goroutine.
const detectTaskGrace = 5 * time.Second

// runWithGuard runs the detection task and returns as soon as it finishes.
// If it does not finish in time, a timeout response is produced, so that
// WaitResponses is never blocked by a task stuck outside the SSH connection.
func (d *detectorTask) runWithGuard(cmd string) {
	start := time.Now()
	timeout := d.sshCli.timeout + detectTaskGrace
	respCh := make(chan *Response, 1)

	safe.Go(func() {
		resp := d.run(cmd, start)
		respCh <- resp
		d.reportSshMetrics(start, resp)
	},
		safe.WithLabel("detectorTask.run"),
		safe.WithOnPanic(func(pi safe.PanicInfo) {
			panicErr := fmt.Errorf("detector task %s panicked: %v", d.id(), pi.Reason)
			logger.Error("detector task aborted, errmsg: %s", panicErr)

			// fill in only when no result has been handed over yet
			select {
			case respCh <- d.failureResponse(start, panicErr):
			default:
			}
		}),
	)

	timer := time.NewTimer(timeout)
	defer timer.Stop()

	select {
	case resp := <-respCh:
		d.resp = resp

	case <-timer.C:
		// last glance: the inner run may have finished at the very same moment.
		select {
		case resp := <-respCh:
			d.resp = resp
		default:
			logger.Error("detector task exceeded the outer guard timeout, task-id: %s, "+
				"inner budget: %v, timeout: %v, errmsg: %s",
				d.id(), d.sshCli.timeout, timeout, ErrDetectorSshConnectTimeout)
			d.resp = d.failureResponse(start, ErrDetectorSshConnectTimeout)
		}
	}
}

// newResponse builds a response carrying the fields shared by every outcome.
func (d *detectorTask) newResponse(start time.Time) *Response {
	return &Response{
		Id:                d.id(),
		Meta:              d.meta,
		DbType:            d.dbType,
		DbEventName:       haprobe.DbEventNameProbeOffline,
		DbEventNameReason: haprobe.DbEventNameReasonMissedProbe,
		CheckStartTime:    &start,
	}
}

// failureResponse builds the response for a task that produced no detection
// result: the outer guard timed out, or the task panicked.
func (d *detectorTask) failureResponse(start time.Time, err error) *Response {
	resp := d.newResponse(start)
	finish := time.Now()
	resp.CheckFinishedTime = &finish
	resp.Err = err

	return resp
}

// run executes the SSH detection and returns its response.
func (d *detectorTask) run(cmd string, start time.Time) *Response {
	resp := d.newResponse(start)

	sshResp, err := d.sshCli.Run(cmd)
	finish := time.Now()
	resp.CheckFinishedTime = &finish
	resp.SshResp = sshResp
	resp.Err = err

	return resp
}

// reportSshMetrics reports the metrics of a finished detection.
func (d *detectorTask) reportSshMetrics(start time.Time, resp *Response) {
	var code int
	var errMsg string
	if resp.SshResp != nil {
		code = resp.SshResp.ExitCode
		errMsg = resp.SshResp.ErrMsg
	} else {
		var gerr *gerrors.Error
		if errors.As(resp.Err, &gerr) {
			code = gerr.Code()
		}
	}

	d.reportSshTime(start, code)

	if resp.Err != nil || errMsg != "" {
		d.reportSshError(code)
	}
}

// reportSshTime reports SSH detection duration metric for a single connection.
func (d *detectorTask) reportSshTime(start time.Time, code int) {
	if reportErr := apm.DetectorSshTimeConsumingMs.ObserveWithLabels(map[string]string{
		haapm.MetricLabelServiceID:   d.serviceID,
		haapm.MetricLabelServiceName: apm.MetricServerName,
		apm.MetricLabelStatusCode:    strconv.Itoa(code),
	}, float64(time.Since(start).Milliseconds())); reportErr != nil {
		logger.Warn("failed to report detector ssh time consuming metric, errmsg: %s", reportErr)
	}
}

// reportSshError reports SSH detection error metric.
func (d *detectorTask) reportSshError(code int) {
	if reportErr := apm.DetectorSshErrorTotal.IncWithLabels(map[string]string{
		haapm.MetricLabelServiceID:   d.serviceID,
		haapm.MetricLabelServiceName: apm.MetricServerName,
		apm.MetricLabelStatusCode:    strconv.Itoa(code),
	}); reportErr != nil {
		logger.Warn("failed to report detector ssh error metric, errmsg: %s", reportErr)
	}
}
