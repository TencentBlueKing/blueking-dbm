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

package process

// Status is the type of process status.
type Status string

func (p Status) String() string {
	return string(p)
}

const (
	StatusRunning Status = "running"
	StatusStopped Status = "stopped"
)

// Probe health exit codes. The analysis detector captures these from the SSH
// session when it runs "dbha-probe health -j" on the remote host.
const (
	ExitCodeHealthDiskWriteFail = 40
	ExitCodeHealthUptimeFail    = 41
)

// ProbeHealthMarkerFile is the fixed marker file name the probe health command
// writes into each write verification dir to verify the local disk is writable.
const ProbeHealthMarkerFile = "dbhav2_probe"

// HealthInfo health information.
type HealthInfo struct {
	Pid      int32  `json:"pid"`
	ProcName string `json:"procName"`
	Status   Status `json:"status"`
	ErrMsg   string `json:"errmsg"`
}

// IsAlive reports whether the probed process is running.
func (h HealthInfo) IsAlive() bool {
	return h.Status == StatusRunning
}
