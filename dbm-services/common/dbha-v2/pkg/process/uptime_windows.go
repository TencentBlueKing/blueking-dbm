//go:build windows

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
	"sync"
	"time"

	"dbm-services/common/dbha-v2/pkg/gerrors"

	"golang.org/x/sys/windows"
)

var (
	modKernel32        = windows.NewLazySystemDLL("kernel32.dll")
	procGetTickCount64 = modKernel32.NewProc("GetTickCount64")

	selfUptimeOnce   sync.Once
	selfUptimeBase   time.Duration
	selfUptimeTickMs uint64
	selfUptimeErr    error
)

func systemUptime() (time.Duration, error) {
	ms, err := getTickCount64()
	if err != nil {
		return 0, err
	}
	return time.Duration(ms) * time.Millisecond, nil
}

func selfStartedAt() (time.Time, error) {
	var creation, exit, kernel, user windows.Filetime
	err := windows.GetProcessTimes(windows.CurrentProcess(), &creation, &exit, &kernel, &user)
	if err != nil {
		return time.Time{}, gerrors.NewE(gerrors.Failure, err)
	}
	return time.Unix(0, creation.Nanoseconds()), nil
}

func selfUptime() (time.Duration, error) {
	selfUptimeOnce.Do(func() {
		tickMs, err := getTickCount64()
		if err != nil {
			selfUptimeErr = err
			return
		}
		startedAt, err := selfStartedAt()
		if err != nil {
			selfUptimeErr = err
			return
		}
		base := time.Since(startedAt)
		if base < 0 {
			base = 0
		}
		selfUptimeBase = base
		selfUptimeTickMs = tickMs
	})
	if selfUptimeErr != nil {
		return 0, selfUptimeErr
	}
	tickMs, err := getTickCount64()
	if err != nil {
		return 0, err
	}
	elapsed := time.Duration(tickMs-selfUptimeTickMs) * time.Millisecond
	uptime := selfUptimeBase + elapsed
	if uptime < 0 {
		return 0, nil
	}
	return uptime, nil
}

func getTickCount64() (uint64, error) {
	if err := procGetTickCount64.Find(); err != nil {
		return 0, gerrors.NewE(gerrors.Failure, err)
	}
	r1, _, errno := procGetTickCount64.Call()
	if r1 == 0 && errno != windows.ERROR_SUCCESS {
		return 0, gerrors.NewE(gerrors.Failure, errno)
	}
	return uint64(r1), nil
}
