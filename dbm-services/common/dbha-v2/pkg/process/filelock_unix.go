//go:build unix

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
	"os"
	"path/filepath"
	"syscall"

	"dbm-services/common/dbha-v2/pkg/constant"
	"dbm-services/common/dbha-v2/pkg/gerrors"
)

// FileLock is an exclusive advisory lock held for the process lifetime of the
// returned unlock function. TryFileLock is non-blocking: if the lock is held,
// held is false and unlock is nil.
type FileLock struct {
	f *os.File
}

// TryFileLock attempts to acquire an exclusive non-blocking flock on path.
func TryFileLock(path string) (fl *FileLock, held bool, err error) {
	if err := os.MkdirAll(filepath.Dir(path), constant.DirModePermission); err != nil {
		return nil, false, gerrors.NewE(gerrors.Failure, err)
	}
	f, err := os.OpenFile(path, os.O_CREATE|os.O_RDWR, 0o644)
	if err != nil {
		return nil, false, gerrors.NewE(gerrors.Failure, err)
	}
	if err := syscall.Flock(int(f.Fd()), syscall.LOCK_EX|syscall.LOCK_NB); err != nil {
		_ = f.Close()
		if errors.Is(err, syscall.EWOULDBLOCK) || errors.Is(err, syscall.EAGAIN) {
			return nil, false, nil
		}
		return nil, false, gerrors.NewE(gerrors.Failure, err)
	}
	return &FileLock{f: f}, true, nil
}

// Unlock releases the lock and closes the file.
func (fl *FileLock) Unlock() error {
	if fl == nil || fl.f == nil {
		return nil
	}
	_ = syscall.Flock(int(fl.f.Fd()), syscall.LOCK_UN)
	err := fl.f.Close()
	fl.f = nil
	return err
}
