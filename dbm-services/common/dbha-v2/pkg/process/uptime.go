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

// Package process provides process lifecycle helpers and OS tick based uptime APIs.
package process

import "time"

// SystemUptime returns how long the operating system has been running.
// The value is derived from OS clock ticks (Linux /proc/uptime, Windows
// GetTickCount64), so it is unaffected by system time adjustments.
func SystemUptime() (time.Duration, error) {
	return systemUptime()
}

// SelfStartedAt returns the start time of the current process.
// The returned absolute time may shift when the system wall clock is adjusted
// (for example Linux btime changes); only SelfUptime is tick-immune.
func SelfStartedAt() (time.Time, error) {
	return selfStartedAt()
}

// SelfUptime returns how long the current process has been running. Like
// SystemUptime it is derived from OS clock ticks instead of subtracting the
// process start time from the current wall clock.
func SelfUptime() (time.Duration, error) {
	return selfUptime()
}
