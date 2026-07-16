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

package cmds

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"time"

	"dbm-services/common/dbha-v2/internal/probe/config"
	"dbm-services/common/dbha-v2/pkg/process"

	"github.com/spf13/cobra"
)

const (
	probeEnsureLockRel     = "pids/probe.ensure.lock"
	keepaliveEnsureLockRel = "probe-keepalive.ensure.lock"
	pingHTTPAddrFlag       = "--ping-http-addr"
)

// FromCron is set when ensure is invoked by schtasks/crontab (no task registration).
var FromCron bool

// EnsureCmdRunE ensures probe runs as guard+worker (daemon-start shape).
func EnsureCmdRunE(cmd *cobra.Command, args []string) error {
	if _, err := process.ChdirInstallRoot(); err != nil {
		return err
	}

	fl, held, err := process.TryFileLock(probeEnsureLockRel)
	if err != nil {
		return err
	}
	if !held {
		fmt.Fprintln(cmd.OutOrStdout(), "ensure already running, skip")
		return nil
	}
	defer fl.Unlock()

	configPath, _ := cmd.Root().PersistentFlags().GetString("config")
	if configPath == "" {
		configPath = "./etc/probe.yaml"
	}
	if err := config.Load(configPath); err != nil {
		return err
	}

	exe, err := os.Executable()
	if err != nil {
		return err
	}
	procs, err := process.ListProbeProcs(exe)
	if err != nil {
		return err
	}
	procs = excludeSelf(procs)

	guards, workers := splitGuardWorker(procs)
	if len(guards) > 0 {
		fmt.Fprintln(cmd.OutOrStdout(), "guard already running, keep current state")
		return nil
	}
	if len(workers) > 0 {
		fmt.Fprintln(cmd.OutOrStdout(), "worker without guard detected, recovering to daemon-start")
		if err := stopProbeWorkers(cmd, workers); err != nil {
			return err
		}
	}
	return DaemonStartCmdRunE(cmd, args)
}

// EnsureKeepaliveCmdRunE ensures a keepalive ping process is running for KeepalivePingAddr.
func EnsureKeepaliveCmdRunE(cmd *cobra.Command, _ []string) error {
	root, err := process.ChdirInstallRoot()
	if err != nil {
		return err
	}

	addr, _ := cmd.Flags().GetString("ping-http-addr")
	if addr == "" {
		addr, _ = cmd.Root().PersistentFlags().GetString("ping-http-addr")
	}
	addr = strings.TrimSpace(addr)
	if addr == "" {
		return fmt.Errorf("ping-http-addr is required")
	}

	runtimeDir := keepaliveRuntimeDir(root)
	if err := os.MkdirAll(runtimeDir, 0o700); err != nil {
		return err
	}
	lockPath := filepath.Join(runtimeDir, keepaliveEnsureLockRel)
	fl, held, err := process.TryFileLock(lockPath)
	if err != nil {
		return err
	}
	if !held {
		fmt.Fprintln(cmd.OutOrStdout(), "ensure-keepalive already running, skip")
		return nil
	}
	defer fl.Unlock()

	exe, err := os.Executable()
	if err != nil {
		return err
	}
	procs, err := process.ListProbeProcs(exe)
	if err != nil {
		return err
	}
	running := filterKeepaliveByAddr(excludeSelf(procs), addr)

	pidFile := filepath.Join(runtimeDir, "probe-keepalive.pid")
	addrFile := filepath.Join(runtimeDir, "probe-keepalive.addr")

	if len(running) > 0 {
		if FromCron {
			fmt.Fprintln(cmd.OutOrStdout(), "keepalive already running, skip restart in cron")
			return nil
		}
		fmt.Fprintln(cmd.OutOrStdout(), "existing keepalive detected, stopping before restart")
		if err := stopKeepaliveProcs(running, addr); err != nil {
			return err
		}
	}

	child, err := process.StartDaemon(process.DaemonOptions{
		Executable: exe,
		Args:       []string{pingHTTPAddrFlag, addr},
	})
	if err != nil {
		return err
	}
	if err := os.WriteFile(pidFile, []byte(fmt.Sprintf("%d\n", child.Pid)), 0o644); err != nil {
		return err
	}
	if err := os.WriteFile(addrFile, []byte(addr+"\n"), 0o644); err != nil {
		return err
	}

	time.Sleep(500 * time.Millisecond)
	alive, _ := process.IsAlive(int32(child.Pid))
	if !alive {
		_ = os.Remove(pidFile)
		_ = os.Remove(addrFile)
		return fmt.Errorf("keepalive startup check failed, pid: %d", child.Pid)
	}
	fmt.Fprintf(cmd.OutOrStdout(), "keepalive started, pid: %d, addr: %s\n", child.Pid, addr)
	return nil
}

func keepaliveRuntimeDir(installRoot string) string {
	if runtime.GOOS == "windows" {
		return filepath.Join(installRoot, "runtime")
	}
	state := os.Getenv("XDG_STATE_HOME")
	if state == "" {
		home, _ := os.UserHomeDir()
		state = filepath.Join(home, ".local", "state")
	}
	return filepath.Join(state, "dbha-v2", "runtime")
}

func excludeSelf(procs []process.ProbeProc) []process.ProbeProc {
	self := int32(os.Getpid())
	var out []process.ProbeProc
	for _, p := range procs {
		if p.Pid == self {
			continue
		}
		out = append(out, p)
	}
	return out
}

func splitGuardWorker(procs []process.ProbeProc) (guards, workers []process.ProbeProc) {
	for _, p := range procs {
		switch p.Kind {
		case process.ProbeProcGuard:
			guards = append(guards, p)
		case process.ProbeProcWorker:
			workers = append(workers, p)
		}
	}
	return guards, workers
}

func stopProbeWorkers(cmd *cobra.Command, workers []process.ProbeProc) error {
	prevForce := ForceStop
	ForceStop = true
	_ = StopCmdRunE(cmd, nil)
	ForceStop = prevForce
	time.Sleep(time.Second)
	for _, w := range workers {
		alive, _ := process.IsAlive(w.Pid)
		if !alive {
			continue
		}
		p, err := os.FindProcess(int(w.Pid))
		if err != nil {
			continue
		}
		_ = p.Kill()
	}
	time.Sleep(500 * time.Millisecond)
	return nil
}

func filterKeepaliveByAddr(procs []process.ProbeProc, addr string) []process.ProbeProc {
	var out []process.ProbeProc
	for _, p := range procs {
		if p.Kind != process.ProbeProcKeepalive {
			continue
		}
		if strings.Contains(p.Cmdline, addr) {
			out = append(out, p)
		}
	}
	return out
}

func stopKeepaliveProcs(procs []process.ProbeProc, addr string) error {
	if err := process.SignalKeepaliveStop(addr); err != nil && !errors.Is(err, process.ErrProcessNotRunning) {
		return err
	}
	for _, p := range procs {
		proc, err := os.FindProcess(int(p.Pid))
		if err != nil {
			continue
		}
		_ = process.TermKeepaliveProc(proc)
	}
	time.Sleep(time.Second)
	for _, p := range procs {
		alive, _ := process.IsAlive(p.Pid)
		if !alive {
			continue
		}
		proc, err := os.FindProcess(int(p.Pid))
		if err != nil {
			continue
		}
		_ = proc.Kill()
	}
	return nil
}
