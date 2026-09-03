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
	"errors"
	"fmt"
	"math"
	"os"
	"path/filepath"
	"strings"

	"dbm-services/common/dbha-v2/pkg/constant"
	"dbm-services/common/dbha-v2/pkg/converter"
	"dbm-services/common/dbha-v2/pkg/gerrors"

	"github.com/shirou/gopsutil/v3/process"
)

const (
	InvalidPid   = -1
	NameProbe    = "probe"
	NameReceiver = "receiver"
	NameAnalysis = "analysis"
	NameAdmin    = "admin"
)

const daemonStartArg = "daemon-start"

var (
	ErrIsDir           = gerrors.Newf(gerrors.Failure, "the input PID file is a directory, not a file")
	ErrPidFileNotExist = gerrors.Newf(gerrors.NotExist, "the PID file is not exist")
	ErrInvalidFile     = gerrors.Newf(gerrors.InvalidParameter, "the input filename is invalid")
	ErrInvalidPid      = gerrors.Newf(gerrors.InvalidParameter, "the PID is invalid")
	ErrInvalidProcName = gerrors.Newf(gerrors.InvalidParameter, "the process name is invalid")
)

// IsDaemonStartGuard reports whether the process with the given PID is a guard process
// (started via daemon-start). It checks the process command line for the "daemon-start" argument.
func IsDaemonStartGuard(pid int32) (bool, error) {
	proc, err := process.NewProcess(pid)
	if err != nil {
		if errors.Is(err, process.ErrorProcessNotRunning) {
			return false, nil
		}
		return false, gerrors.NewE(gerrors.Failure, err)
	}
	cmdline, err := proc.Cmdline()
	if err != nil {
		if errors.Is(err, process.ErrorProcessNotRunning) {
			return false, nil
		}
		return false, gerrors.NewE(gerrors.Failure, err)
	}
	// Cmdline may be space or null separated; normalize to spaces then split.
	cmdline = strings.ReplaceAll(cmdline, "\x00", " ")
	for _, tok := range strings.Fields(cmdline) {
		if tok == daemonStartArg {
			return true, nil
		}
	}
	return false, nil
}

// WasRunningWithDaemonStart returns true if the process identified by pidFile and procName
// is currently running and is a daemon-start guard. Used before restart to decide whether
// to re-launch with daemon-start. Returns false when pid file is missing, process is
// not alive, or process is not the guard (e.g. plain start).
func WasRunningWithDaemonStart(pidFile, procName string) (bool, error) {
	pid, err := ReadPid(pidFile)
	if err != nil {
		if errors.Is(err, ErrPidFileNotExist) || errors.Is(err, ErrInvalidFile) {
			return false, nil
		}
		return false, err
	}
	alive, err := IsAliveWithProcessName(pid, procName)
	if err != nil || !alive {
		return false, err
	}
	return IsDaemonStartGuard(pid)
}

// BinaryName returns the base name of the current executable (e.g. dbha-admin).
// Use this for start/stop/daemon/health so the process name matches the running binary;
// when started via daemon-start, the guard process has this name.
func BinaryName() string {
	exe, err := os.Executable()
	if err != nil {
		return ""
	}
	return filepath.Base(exe)
}

// Name is used to obtain the process name.
func Name(pid int32) (string, error) {
	proc, err := process.NewProcess(pid)
	if err != nil {
		return "", gerrors.NewE(gerrors.Failure, err)
	}

	return proc.Name()
}

// SavePid is used to save the process pid into a file.
// When DBHA_UNDER_GUARD is set (child running under guard), skip writing to avoid overwriting guard's pid file.
func SavePid(filename string) error {
	if os.Getenv(EnvUnderGuard) != "" {
		return nil
	}
	if filename == "" {
		return ErrInvalidFile
	}

	filename = filepath.Clean(filename)
	parentDir := filepath.Dir(filename)

	stat, err := os.Stat(filename)

	if err != nil {
		if !os.IsNotExist(err) {
			return err
		}

		if err = os.MkdirAll(parentDir, constant.DirModePermission); err != nil {
			return gerrors.Newf(gerrors.Failure, "failed to create the dir: %s, %s", parentDir, err)
		}
	} else if stat.IsDir() {
		return ErrIsDir
	}

	pid := os.Getpid()
	data := fmt.Sprintf("%d", pid)

	if err := os.WriteFile(filename, []byte(data), constant.FileModePermission); err != nil {
		return gerrors.Newf(gerrors.Failure, "failed to create the pid file: %s, %s", filename, err)
	}

	return nil
}

// ReadPid is used to recover the PID from the file.
func ReadPid(filename string) (int32, error) {
	if filename == "" {
		return InvalidPid, ErrInvalidFile
	}

	filename = filepath.Clean(filename)

	stat, err := os.Stat(filename)
	if err != nil {
		if os.IsNotExist(err) {
			return InvalidPid, ErrPidFileNotExist
		}

		return InvalidPid, gerrors.NewE(gerrors.Failure, err)
	} else if stat.IsDir() {
		return InvalidPid, ErrPidFileNotExist
	}

	data, err := os.ReadFile(filename)
	if err != nil {
		return InvalidPid, gerrors.NewE(gerrors.Failure, err)
	}

	// Trailing whitespace is common in hand-written pid files (`echo $pid > f`),
	// while SavePid writes the number bare. Without trimming, such a file fails to
	// parse and stop / reload report an error instead of "not running".
	pid, err := converter.ToInt(strings.TrimSpace(string(data)))
	if err != nil {
		return InvalidPid, gerrors.NewE(gerrors.Failure, err)
	}

	if pid <= 0 || pid > math.MaxInt32 {
		return InvalidPid, ErrInvalidPid
	}

	return int32(pid), nil
}

// IsAlive is used to check whether the process is running.
func IsAlive(pid int32) (bool, error) {
	return process.PidExists(pid)
}

// IsAliveWithProcessName is used to check whether the process is running by the PID and name.
func IsAliveWithProcessName(pid int32, name string) (bool, error) {
	if pid <= 0 {
		return false, ErrInvalidPid
	}

	if name == "" {
		return false, ErrInvalidProcName
	}

	proc, err := process.NewProcess(pid)
	if err != nil {
		if errors.Is(err, process.ErrorProcessNotRunning) {
			return false, nil
		}
		if errors.Is(err, process.ErrorNotPermitted) {
			return false, gerrors.NewE(gerrors.Failure, err)
		}
		return false, gerrors.NewE(gerrors.Failure, err)
	}

	procName, err := proc.Name()
	if err != nil {
		if errors.Is(err, process.ErrorProcessNotRunning) {
			return false, nil
		}
		if errors.Is(err, process.ErrorNotPermitted) {
			return false, gerrors.NewE(gerrors.Failure, err)
		}
		return false, gerrors.Newf(gerrors.Failure,
			"failed to obtain the proc name by the PID: %d, errmsg: %s", pid, err)
	}

	if procName == name {
		return true, nil
	}

	return false, nil
}
