//go:build linux

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
	"strconv"
	"strings"
	"time"

	"dbm-services/common/dbha-v2/pkg/gerrors"
)

// userHZ is the Linux /proc clock tick rate used by starttime and related fields.
// CGO_ENABLED=0 builds cannot call sysconf(_SC_CLK_TCK); Linux /proc statistics
// are fixed at 100 Hz, matching gopsutil's hard-coded value.
const userHZ = 100

func systemUptime() (time.Duration, error) {
	content, err := os.ReadFile("/proc/uptime")
	if err != nil {
		return 0, gerrors.NewE(gerrors.Failure, err)
	}
	seconds, err := parseProcUptimeSeconds(string(content))
	if err != nil {
		return 0, err
	}
	return time.Duration(seconds * float64(time.Second)), nil
}

func selfStartedAt() (time.Time, error) {
	startTicks, err := readSelfStartTicks()
	if err != nil {
		return time.Time{}, err
	}
	bootContent, err := os.ReadFile("/proc/stat")
	if err != nil {
		return time.Time{}, gerrors.NewE(gerrors.Failure, err)
	}
	btime, err := parseProcStatBootTime(string(bootContent))
	if err != nil {
		return time.Time{}, err
	}
	startSec := float64(startTicks) / float64(userHZ)
	return time.Unix(btime, 0).Add(time.Duration(startSec * float64(time.Second))), nil
}

func selfUptime() (time.Duration, error) {
	sysUptime, err := systemUptime()
	if err != nil {
		return 0, err
	}
	startTicks, err := readSelfStartTicks()
	if err != nil {
		return 0, err
	}
	startOffset := time.Duration(float64(startTicks) / float64(userHZ) * float64(time.Second))
	uptime := sysUptime - startOffset
	if uptime < 0 {
		return 0, nil
	}
	return uptime, nil
}

func readSelfStartTicks() (uint64, error) {
	content, err := os.ReadFile("/proc/self/stat")
	if err != nil {
		return 0, gerrors.NewE(gerrors.Failure, err)
	}
	return parseSelfStatStartTicks(string(content))
}

// parseSelfStatStartTicks extracts the starttime field (field 22) from /proc/[pid]/stat.
// The comm field may contain spaces and parentheses, so parsing starts after the last ')'.
func parseSelfStatStartTicks(statContent string) (uint64, error) {
	statContent = strings.TrimSpace(statContent)
	idx := strings.LastIndex(statContent, ")")
	if idx < 0 || idx+2 >= len(statContent) {
		return 0, gerrors.Newf(gerrors.Failure, "invalid /proc/self/stat content")
	}
	fields := strings.Fields(statContent[idx+2:])
	// After ')': state is field 3 overall, so starttime (field 22) is at index 19.
	const starttimeIndex = 19
	if len(fields) <= starttimeIndex {
		return 0, gerrors.Newf(gerrors.Failure, "insufficient fields in /proc/self/stat")
	}
	ticks, err := strconv.ParseUint(fields[starttimeIndex], 10, 64)
	if err != nil {
		return 0, gerrors.Newf(gerrors.Failure, "parse starttime failed, errmsg: %s", err)
	}
	return ticks, nil
}

// parseProcUptimeSeconds extracts the first field of /proc/uptime (seconds).
func parseProcUptimeSeconds(uptimeContent string) (float64, error) {
	fields := strings.Fields(strings.TrimSpace(uptimeContent))
	if len(fields) < 1 {
		return 0, gerrors.Newf(gerrors.Failure, "invalid /proc/uptime content")
	}
	seconds, err := strconv.ParseFloat(fields[0], 64)
	if err != nil {
		return 0, gerrors.Newf(gerrors.Failure, "parse /proc/uptime failed, errmsg: %s", err)
	}
	if seconds < 0 {
		return 0, gerrors.Newf(gerrors.Failure, "negative /proc/uptime: %s", fields[0])
	}
	return seconds, nil
}

// parseProcStatBootTime extracts the btime value from /proc/stat content.
func parseProcStatBootTime(statContent string) (int64, error) {
	for _, line := range strings.Split(statContent, "\n") {
		fields := strings.Fields(line)
		if len(fields) < 2 || fields[0] != "btime" {
			continue
		}
		btime, err := strconv.ParseInt(fields[1], 10, 64)
		if err != nil {
			return 0, gerrors.Newf(gerrors.Failure, "parse btime failed, errmsg: %s", err)
		}
		return btime, nil
	}
	return 0, gerrors.Newf(gerrors.Failure, "btime not found in /proc/stat")
}
