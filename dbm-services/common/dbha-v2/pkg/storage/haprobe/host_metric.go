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

// HostMetric host metric
type HostMetric struct {
	// CPU
	CpuUsagePercent  float64 `json:"cpu_usage_percent,omitempty"`
	CpuUserPercent   float64 `json:"cpu_user_percent,omitempty"`
	CpuSystemPercent float64 `json:"cpu_system_percent,omitempty"`
	CpuIOWaitPercent float64 `json:"cpu_iowait_percent,omitempty"`
	CpuLoad1         float64 `json:"cpu_load_1,omitempty"`
	CpuLoad5         float64 `json:"cpu_load_5,omitempty"`
	CpuLoad15        float64 `json:"cpu_load_15,omitempty"`

	// Mem
	MemTotalMB     uint64 `json:"mem_total_mb,omitempty"`
	MemUsedMB      uint64 `json:"mem_used_mb,omitempty"`
	MemFreeMB      uint64 `json:"mem_free_mb,omitempty"`
	MemCacheMB     uint64 `json:"mem_cache_mb,omitempty"`
	MemAvailableMB uint64 `json:"mem_available_mb,omitempty"`
	SwapTotalMB    uint64 `json:"swap_total_mb,omitempty"`
	SwapUsedMB     uint64 `json:"swap_used_mb,omitempty"`

	// Disk
	DiskUsagePercent float64 `json:"disk_usage_percent,omitempty"`
	DiskTotal        uint64  `json:"disk_total,omitempty"`
	DiskUsed         uint64  `json:"disk_used,omitempty"`
	DiskAvailable    uint64  `json:"disk_available,omitempty"`
	DiskReadOnly     bool    `json:"disk_read_only,omitempty"`

	// Network
	NetIPs            []string `json:"network_ip_address,omitempty"`
	NetBytesIn        uint64   `json:"network_bytes_in,omitempty"`
	NetBytesOut       uint64   `json:"network_bytes_out,omitempty"`
	NetUsage          string   `json:"network_usage,omitempty"`
	NetTCPConnections uint     `json:"network_tcp_connections,omitempty"`
	NetPacketLossIn   float64  `json:"network_packet_loss_in,omitempty"`
	NetPacketLossOut  float64  `json:"network_packet_loss_out,omitempty"`
}
