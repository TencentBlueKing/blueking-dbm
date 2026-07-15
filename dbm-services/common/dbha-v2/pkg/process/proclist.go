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

import (
	"path/filepath"
	"strings"

	"github.com/shirou/gopsutil/v3/process"
)

const pingHTTPAddrFlag = "--ping-http-addr"

// ProbeProcKind classifies a dbha-probe process by its command line.
type ProbeProcKind int

const (
	ProbeProcUnknown ProbeProcKind = iota
	ProbeProcGuard
	ProbeProcWorker
	ProbeProcKeepalive
)

// ProbeProc describes one running probe binary instance.
type ProbeProc struct {
	Pid     int32
	Kind    ProbeProcKind
	Cmdline string
}

// ClassifyProbeCmdline classifies a probe process from its command line tokens.
// ensure / ensure-keepalive are management entrypoints and must not be treated as
// worker/keepalive (their argv also carries --ping-http-addr / -c).
func ClassifyProbeCmdline(cmdline string) ProbeProcKind {
	cmdline = strings.ReplaceAll(cmdline, "\x00", " ")
	for _, tok := range strings.Fields(cmdline) {
		switch tok {
		case "ensure", "ensure-keepalive":
			return ProbeProcUnknown
		}
	}
	if strings.Contains(cmdline, pingHTTPAddrFlag) {
		return ProbeProcKeepalive
	}
	for _, tok := range strings.Fields(cmdline) {
		if tok == daemonStartArg {
			return ProbeProcGuard
		}
	}
	return ProbeProcWorker
}

// ListProbeProcs returns processes whose executable path matches expectedExe
// (after EvalSymlinks/Abs when possible). Keepalive processes are included and
// tagged as ProbeProcKeepalive.
func ListProbeProcs(expectedExe string) ([]ProbeProc, error) {
	expectedExe = filepath.Clean(expectedExe)
	if resolved, err := filepath.EvalSymlinks(expectedExe); err == nil {
		expectedExe = filepath.Clean(resolved)
	}

	pids, err := process.Pids()
	if err != nil {
		return nil, err
	}
	var out []ProbeProc
	for _, pid := range pids {
		p, err := process.NewProcess(pid)
		if err != nil {
			continue
		}
		exe, err := p.Exe()
		if err != nil {
			continue
		}
		exe = filepath.Clean(exe)
		if resolved, err := filepath.EvalSymlinks(exe); err == nil {
			exe = filepath.Clean(resolved)
		}
		if !sameFilePath(exe, expectedExe) {
			continue
		}
		cmdline, err := p.Cmdline()
		if err != nil {
			continue
		}
		out = append(out, ProbeProc{
			Pid:     pid,
			Kind:    ClassifyProbeCmdline(cmdline),
			Cmdline: cmdline,
		})
	}
	return out, nil
}

func sameFilePath(a, b string) bool {
	if strings.EqualFold(a, b) {
		return true
	}
	// Compare case-folded on Windows via EqualFold above for typical paths;
	// also accept equal Clean forms.
	return a == b
}
