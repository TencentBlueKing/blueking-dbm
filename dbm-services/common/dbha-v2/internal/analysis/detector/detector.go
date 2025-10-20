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

package detector

import (
	"sync"

	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

var (
	ErrDetectorProbeNotRunning = gerrors.Newf(gerrors.ProbeFailure, "probe is not running")
	ErrDetectorNoTarget        = gerrors.Newf(gerrors.InvalidParameter, "no detected target")
)

const (
	CheckProbeProcessCmd = "cd ~/dbhav2/ && ./probe health -j"
)

type Response struct {
	Id                string
	Meta              *hamodel.DbmMetadata
	DbEventName       haprobe.DbEventName
	DbEventNameReason haprobe.DbEventNameReason
	Err               error
	ExitCode          int
	Data              []byte
}

// Detector is used to detect whether the host or the probe is alive.
type Detector struct {
	wg    sync.WaitGroup
	tasks map[string]*detectorTask
}

func (d *Detector) Detect(dbInsts []*hamodel.DbmMetadata) error {
	if len(dbInsts) == 0 {
		return ErrDetectorNoTarget
	}

	if d.tasks == nil {
		d.tasks = make(map[string]*detectorTask)
	}

	for _, inst := range dbInsts {
		task := &detectorTask{
			meta: inst,
			sshCli: &Ssh{
				ip:       inst.IP,
				port:     config.Cfg.Detector.Ssh.Port,
				user:     config.Cfg.Detector.Ssh.User,
				password: config.Cfg.Detector.Ssh.Password,
				timeout:  config.Cfg.Detector.Ssh.Timeout,
			},
		}

		d.tasks[task.id()] = task

		d.wg.Add(1)
		go func(task *detectorTask) {
			defer d.wg.Done()
			task.run(CheckProbeProcessCmd)
		}(task)
	}

	return nil
}

func (d *Detector) WaitResponses() []*Response {
	d.wg.Wait()
	resps := []*Response{}

	for _, task := range d.tasks {
		resps = append(resps, task.resp)
	}

	return resps
}

func (d *Detector) TryRecoverProbe() error {
	return nil
}

func (d *Detector) checkProbe() error {
	return nil
}

type detectorTask struct {
	meta   *hamodel.DbmMetadata
	resp   *Response
	sshCli *Ssh
}

func (d *detectorTask) id() string {
	return d.sshCli.Id()
}

func (d *detectorTask) run(cmd string) {
	resp := &Response{
		Meta:              d.meta,
		Id:                d.sshCli.Id(),
		DbEventName:       haprobe.DbEventNameProbeOffline,
		DbEventNameReason: haprobe.DbEventNameReasonMissedProbe,
	}

	d.resp = resp
	resp.Data, resp.Err = d.sshCli.Run(cmd)

	if err, ok := resp.Err.(*gerrors.Error); ok {
		resp.ExitCode = err.Code()
		resp.Data = []byte(err.Error())
	}
}
