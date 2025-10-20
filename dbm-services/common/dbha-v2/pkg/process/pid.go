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
	"fmt"
	"os"
	"path/filepath"

	"dbm-services/common/dbha-v2/pkg/constant"
	"dbm-services/common/dbha-v2/pkg/converter"
	"dbm-services/common/dbha-v2/pkg/gerrors"

	"github.com/shirou/gopsutil/v3/process"
)

const (
	InvalidPid = -1
)

var (
	ErrIsDir           = gerrors.Newf(gerrors.Failure, "the input PID file is a directory, not a file")
	ErrPidFileNotExist = gerrors.Newf(gerrors.NotExist, "the PID file is not exist")
	ErrInvalidFile     = gerrors.Newf(gerrors.InvalidParameter, "the input filename is invalid")
)

// Name is used to obtain the process name.
func Name(pid int) (string, error) {
	proc, err := process.NewProcess(int32(pid))
	if err != nil {
		return "", gerrors.NewE(gerrors.Failure, err)
	}

	return proc.Name()
}

// SavePid is used to save the process pid into a file.
func SavePid(filename string) error {
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
func ReadPid(filename string) (int, error) {
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

	pid, err := converter.ToInt(string(data))
	if err != nil {
		return InvalidPid, gerrors.NewE(gerrors.Failure, err)
	}

	return pid, nil
}

// IsAlive is used to check whether the process is running.
func IsAlive(pid int) (bool, error) {
	return process.PidExists(int32(pid))
}

// IsAliveWithProcessName is used to check whether the process is running by the PID and name.
func IsAliveWithProcessName(pid int, name string) (bool, error) {
	proc, err := process.NewProcess(int32(pid))
	if err != nil {
		return false, gerrors.NewE(gerrors.Failure, err)
	}

	procName, err := proc.Name()
	if err != nil {
		return false, gerrors.Newf(gerrors.Failure,
			"failed to obtain the proc name by the PID: %d, errmsg: %s", pid, err)
	}

	if procName == name {
		return true, nil
	}

	return false, nil
}
