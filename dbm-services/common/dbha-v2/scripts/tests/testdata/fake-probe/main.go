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

// Command fake-probe is a test stub built as "dbha-probe" for
// scripts/tests/test-probe-start-stop-race.sh.
//
// It has to be a real compiled binary rather than a shell script: the lifecycle
// scripts validate targets via /proc/<pid>/comm and /proc/<pid>/exe, and a
// shebang script reports the interpreter (bash) for both.
//
// It reproduces only the concurrency-relevant contract of the real probe:
//   - ensure:       take pids/probe.ensure.lock non-blocking, skip if held,
//     spawn a detached daemon-start when no guard is alive
//   - daemon-start: write pids/probe.pid and idle until TERM/INT
//   - stop:         no-op, the script terminates processes itself
//
// Test-only environment switches (all off by default, production probe has none):
//
//	FAKE_PROBE_ENSURE_FAIL=1     ensure / ensure-keepalive exit 1
//	FAKE_PROBE_ENSURE_NO_SPAWN=1 ensure exits 0 without starting a process
//	FAKE_PROBE_IGNORE_TERM=1     idle processes ignore SIGTERM (SIGKILL still works)
//	FAKE_PROBE_RESPAWN_ONCE=1    on TERM, spawn one replacement then exit
//	FAKE_PROBE_RESPAWN_ALWAYS=1  on TERM, spawn a replacement that also respawns
//
// It performs no config parsing, no network and no database access, so the test
// stays deterministic.
package main

import (
	"fmt"
	"os"
	"os/exec"
	"os/signal"
	"path/filepath"
	"strconv"
	"strings"
	"syscall"
	"time"
)

func envOn(name string) bool {
	v := os.Getenv(name)
	return v == "1" || v == "true"
}

func filteredEnv(drop string) []string {
	out := make([]string, 0, len(os.Environ()))
	prefix := drop + "="
	for _, e := range os.Environ() {
		if strings.HasPrefix(e, prefix) {
			continue
		}
		out = append(out, e)
	}
	return out
}

func installRoot() string {
	exe, err := os.Executable()
	if err != nil {
		return "."
	}
	if resolved, err := filepath.EvalSymlinks(exe); err == nil {
		exe = resolved
	}
	return filepath.Clean(filepath.Join(filepath.Dir(exe), ".."))
}

func tryFileLock(path string) (*os.File, bool) {
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return nil, false
	}
	f, err := os.OpenFile(path, os.O_CREATE|os.O_RDWR, 0o600)
	if err != nil {
		return nil, false
	}
	if err := syscall.Flock(int(f.Fd()), syscall.LOCK_EX|syscall.LOCK_NB); err != nil {
		_ = f.Close()
		return nil, false
	}
	return f, true
}

// guardAlive reports whether a daemon-start process is still running, using the
// same evidence the shell side uses: liveness plus the cmdline shape.
func guardAlive(root string) bool {
	raw, err := os.ReadFile(filepath.Join(root, "pids", "probe.pid"))
	if err != nil {
		return false
	}
	pid, err := strconv.Atoi(strings.TrimSpace(string(raw)))
	if err != nil || pid <= 0 {
		return false
	}
	if err := syscall.Kill(pid, 0); err != nil {
		return false
	}
	cmdline, err := os.ReadFile(fmt.Sprintf("/proc/%d/cmdline", pid))
	if err != nil {
		return false
	}
	return strings.Contains(strings.ReplaceAll(string(cmdline), "\x00", " "), "daemon-start")
}

func maybeRespawn(dir string, args []string) {
	once := envOn("FAKE_PROBE_RESPAWN_ONCE")
	always := envOn("FAKE_PROBE_RESPAWN_ALWAYS")
	if (!once && !always) || len(args) == 0 {
		return
	}
	exe, err := os.Executable()
	if err != nil {
		return
	}
	cmd := exec.Command(exe, args...)
	cmd.Dir = dir
	cmd.SysProcAttr = &syscall.SysProcAttr{Setsid: true}
	if once && !always {
		cmd.Env = filteredEnv("FAKE_PROBE_RESPAWN_ONCE")
	}
	if err := cmd.Start(); err != nil {
		fmt.Fprintf(os.Stderr, "cannot respawn, errmsg: %s\n", err)
	}
}

func waitUntilStopped(dir string, respawnArgs []string) {
	if envOn("FAKE_PROBE_IGNORE_TERM") {
		signal.Ignore(syscall.SIGTERM)
		// Empty select{} is diagnosed as deadlock when no other goroutine exists.
		for {
			time.Sleep(time.Hour)
		}
	}
	ch := make(chan os.Signal, 1)
	signal.Notify(ch, syscall.SIGTERM, syscall.SIGINT)
	<-ch
	maybeRespawn(dir, respawnArgs)
}

func runEnsure(root string) {
	if envOn("FAKE_PROBE_ENSURE_FAIL") {
		fmt.Fprintln(os.Stderr, "ensure forced failure")
		os.Exit(1)
	}
	if envOn("FAKE_PROBE_ENSURE_NO_SPAWN") {
		fmt.Println("ensure skipped spawn")
		return
	}

	fl, held := tryFileLock(filepath.Join(root, "pids", "probe.ensure.lock"))
	if !held {
		fmt.Println("ensure already running, skip")
		return
	}
	defer func() { _ = fl.Close() }()

	if guardAlive(root) {
		fmt.Println("guard already running, keep current state")
		return
	}

	exe, err := os.Executable()
	if err != nil {
		fmt.Fprintf(os.Stderr, "cannot resolve executable, errmsg: %s\n", err)
		os.Exit(1)
	}
	cmd := exec.Command(exe, "daemon-start", "-c", "etc/probe.yaml")
	cmd.Dir = root
	// Setsid detaches the guard so it survives the ensure process exiting,
	// matching how the real probe daemonises.
	cmd.SysProcAttr = &syscall.SysProcAttr{Setsid: true}
	if err := cmd.Start(); err != nil {
		fmt.Fprintf(os.Stderr, "cannot start guard, errmsg: %s\n", err)
		os.Exit(1)
	}
	// Give the child time to publish its pid file so that a start script running
	// right after us observes the guard.
	for i := 0; i < 50; i++ {
		if guardAlive(root) {
			break
		}
		time.Sleep(20 * time.Millisecond)
	}
	fmt.Println("guard started")
}

// keepaliveRuntimeDir mirrors internal/probe/cmds/ensure.go so the stub, the
// scripts and the real binary all agree on the lock and state file locations.
func keepaliveRuntimeDir() string {
	state := os.Getenv("XDG_STATE_HOME")
	if state == "" {
		home, _ := os.UserHomeDir()
		state = filepath.Join(home, ".local", "state")
	}
	return filepath.Join(state, "dbha-v2", "runtime")
}

func keepaliveAlive(runtimeDir, addr string) bool {
	raw, err := os.ReadFile(filepath.Join(runtimeDir, "probe-keepalive.pid"))
	if err != nil {
		return false
	}
	pid, err := strconv.Atoi(strings.TrimSpace(string(raw)))
	if err != nil || pid <= 0 {
		return false
	}
	if err := syscall.Kill(pid, 0); err != nil {
		return false
	}
	cmdline, err := os.ReadFile(fmt.Sprintf("/proc/%d/cmdline", pid))
	if err != nil {
		return false
	}
	return strings.Contains(strings.ReplaceAll(string(cmdline), "\x00", " "), addr)
}

func flagValue(args []string, name string) string {
	for i, a := range args {
		if a == name && i+1 < len(args) {
			return args[i+1]
		}
		if strings.HasPrefix(a, name+"=") {
			return strings.TrimPrefix(a, name+"=")
		}
	}
	return ""
}

func runEnsureKeepalive(args []string) {
	if envOn("FAKE_PROBE_ENSURE_FAIL") {
		fmt.Fprintln(os.Stderr, "ensure-keepalive forced failure")
		os.Exit(1)
	}
	if envOn("FAKE_PROBE_ENSURE_NO_SPAWN") {
		fmt.Println("ensure-keepalive skipped spawn")
		return
	}

	addr := flagValue(args, "--ping-http-addr")
	if addr == "" {
		fmt.Fprintln(os.Stderr, "ping-http-addr is required")
		os.Exit(1)
	}

	runtimeDir := keepaliveRuntimeDir()
	if err := os.MkdirAll(runtimeDir, 0o700); err != nil {
		os.Exit(1)
	}

	fl, held := tryFileLock(filepath.Join(runtimeDir, "probe-keepalive.ensure.lock"))
	if !held {
		fmt.Println("ensure-keepalive already running, skip")
		return
	}
	defer func() { _ = fl.Close() }()

	if keepaliveAlive(runtimeDir, addr) {
		fmt.Println("keepalive already running, keep current state")
		return
	}

	exe, err := os.Executable()
	if err != nil {
		os.Exit(1)
	}
	cmd := exec.Command(exe, "--ping-http-addr", addr)
	cmd.SysProcAttr = &syscall.SysProcAttr{Setsid: true}
	if err := cmd.Start(); err != nil {
		fmt.Fprintf(os.Stderr, "cannot start keepalive, errmsg: %s\n", err)
		os.Exit(1)
	}
	_ = os.WriteFile(filepath.Join(runtimeDir, "probe-keepalive.pid"),
		[]byte(strconv.Itoa(cmd.Process.Pid)), 0o644)
	_ = os.WriteFile(filepath.Join(runtimeDir, "probe-keepalive.addr"), []byte(addr), 0o644)

	for i := 0; i < 50; i++ {
		if keepaliveAlive(runtimeDir, addr) {
			break
		}
		time.Sleep(20 * time.Millisecond)
	}
	fmt.Println("keepalive started")
}

func runDaemonStart(root string) {
	pidDir := filepath.Join(root, "pids")
	if err := os.MkdirAll(pidDir, 0o755); err != nil {
		os.Exit(1)
	}
	pidFile := filepath.Join(pidDir, "probe.pid")
	if err := os.WriteFile(pidFile, []byte(strconv.Itoa(os.Getpid())), 0o644); err != nil {
		os.Exit(1)
	}

	waitUntilStopped(root, []string{"daemon-start", "-c", "etc/probe.yaml"})
	_ = os.Remove(pidFile)
}

func runKeepaliveWorker(addr string) {
	waitUntilStopped(".", []string{"--ping-http-addr", addr})
}

func main() {
	root := installRoot()

	if len(os.Args) < 2 {
		// Worker shape (argv[0] only): idle so the classifier can see it.
		waitUntilStopped(root, nil)
		return
	}

	// Keepalive worker shape: argv carries --ping-http-addr and nothing else.
	if os.Args[1] == "--ping-http-addr" || strings.HasPrefix(os.Args[1], "--ping-http-addr=") {
		runKeepaliveWorker(flagValue(os.Args[1:], "--ping-http-addr"))
		return
	}

	switch os.Args[1] {
	case "ensure":
		runEnsure(root)
	case "ensure-keepalive":
		runEnsureKeepalive(os.Args[1:])
	case "daemon-start":
		runDaemonStart(root)
	case "stop":
		// The scripts own process termination; nothing to do here.
	case "gen-config":
		// Long-running management shape. DBM runs gen-config right before
		// start-probe.sh, so the test needs a live process of this shape to
		// prove a concurrent stop leaves it alone.
		waitUntilStopped(root, []string{"gen-config"})
	case "health":
		fmt.Println("ok")
	case "version":
		fmt.Println("fake-probe")
	default:
		// Unknown subcommands must not fail the scripts under test.
	}
}
