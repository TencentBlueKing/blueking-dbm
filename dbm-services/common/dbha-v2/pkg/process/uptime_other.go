//go:build !linux && !windows

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
	"os"
	"time"

	"dbm-services/common/dbha-v2/pkg/gerrors"

	"github.com/shirou/gopsutil/v3/host"
	gopsutil "github.com/shirou/gopsutil/v3/process"
)

// Non-linux/non-windows platforms have no tick-based uptime API in this package.
// These fallbacks use gopsutil wall-clock based values so macOS development builds
// still compile and tests can run. Production probe targets are linux and windows.

func systemUptime() (time.Duration, error) {
	seconds, err := host.Uptime()
	if err != nil {
		return 0, gerrors.NewE(gerrors.Failure, err)
	}
	return time.Duration(seconds) * time.Second, nil
}

func selfStartedAt() (time.Time, error) {
	p, err := gopsutil.NewProcess(int32(os.Getpid()))
	if err != nil {
		return time.Time{}, gerrors.NewE(gerrors.Failure, err)
	}
	ms, err := p.CreateTime()
	if err != nil {
		return time.Time{}, gerrors.NewE(gerrors.Failure, err)
	}
	return time.UnixMilli(ms), nil
}

func selfUptime() (time.Duration, error) {
	startedAt, err := selfStartedAt()
	if err != nil {
		return 0, err
	}
	uptime := time.Since(startedAt)
	if uptime < 0 {
		return 0, nil
	}
	return uptime, nil
}
