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

package haprobe

// ProbeMetric describes the probe process itself: build version, its own CPU /
// memory usage, and how long it has been running.
// CpuUsagePercent is single-core based (same semantics as top %CPU) and may exceed
// 100 on multi-core hosts; NumCPU is carried so consumers can normalize.
// StartedAt and SampledAt are unix timestamps in seconds. SampledAt is not redundant
// with HarvestBaseData.ReportTimestamp: sampling runs on its own interval, so
// ReportTimestamp minus SampledAt tells consumers how stale the snapshot is.
// UptimeSeconds is derived from OS clock ticks rather than wall-clock subtraction,
// so it stays correct across system time adjustments; StartedAt cannot offer that
// guarantee because it is an absolute time. Uptime is UptimeSeconds rendered for
// humans, e.g. "3 days 4 hours".
// Numeric fields deliberately omit the omitempty option: an idle probe can burn
// less than one clock tick within a sample interval, so 0 is a real value that must
// stay distinguishable from "not collected".
type ProbeMetric struct {
	Version         string  `json:"version,omitempty"`
	GitTag          string  `json:"git_tag,omitempty"`
	GitHash         string  `json:"git_hash,omitempty"`
	BuildTime       string  `json:"build_time,omitempty"`
	Pid             int32   `json:"pid"`
	NumCPU          int     `json:"num_cpu"`
	CpuUsagePercent float64 `json:"cpu_usage_percent"`
	MemRssMB        uint64  `json:"mem_rss_mb"`
	MemUsagePercent float64 `json:"mem_usage_percent"`
	StartedAt       uint64  `json:"started_at"`
	UptimeSeconds   uint64  `json:"uptime_seconds"`
	Uptime          string  `json:"uptime,omitempty"`
	SampledAt       uint64  `json:"sampled_at"`
}
