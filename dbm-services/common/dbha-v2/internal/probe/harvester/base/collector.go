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

package base

import (
	"fmt"
	"math"
	"net"
	"time"

	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"

	"github.com/shirou/gopsutil/cpu"
	"github.com/shirou/gopsutil/disk"
	"github.com/shirou/gopsutil/load"
	"github.com/shirou/gopsutil/mem"

	gopsutilnet "github.com/shirou/gopsutil/v4/net"
)

// Collector The base collector of all the harvester collectors.
type Collector struct {
}

func (c *Collector) SetCpuStatus(hostStatus *haprobe.HostMetric) error {
	cpuPercent, err := cpu.Percent(1*time.Second, false)
	if err != nil {
		return gerrors.Newf(gerrors.Failure, "failed to obtain CPU percent, %v", err)
	}

	if len(cpuPercent) == 0 {
		return gerrors.New(gerrors.Failure, "failed to obtain CPU percent, empty data set")
	}

	cpuTimes, err := cpu.Times(false)
	if err != nil {
		return gerrors.Newf(gerrors.Failure, "failed to obtain CPU time, %v", err)
	}

	if len(cpuTimes) == 0 {
		return gerrors.New(gerrors.Failure, "failed to obtain CPU time, empty data set")
	}

	hostStatus.CpuUsagePercent = cpuPercent[0]

	total := cpuTimes[0].Total()
	if math.Float64bits(total) == 0 {
		return gerrors.New(gerrors.Failure, "total CPU time is zero")
	}

	hostStatus.CpuUserPercent = cpuTimes[0].User / total * 100
	hostStatus.CpuSystemPercent = cpuTimes[0].System / total * 100
	hostStatus.CpuIOWaitPercent = cpuTimes[0].Iowait / total * 100

	load, err := load.Avg()
	if err != nil {
		return gerrors.Newf(gerrors.Failure, "failed to obtain CPU load average, %v", err)
	}

	hostStatus.CpuLoad1 = load.Load1
	hostStatus.CpuLoad5 = load.Load5
	hostStatus.CpuLoad15 = load.Load15
	return nil
}

func (c *Collector) SetMemoryStatus(hostStatus *haprobe.HostMetric) error {
	memory, err := mem.VirtualMemory()
	if err != nil {
		return err
	}

	// convert the value from Byte to MB
	hostStatus.MemTotalMB = memory.Total / 1024 / 1024
	hostStatus.MemUsedMB = memory.Used / 1024 / 1024
	hostStatus.MemFreeMB = memory.Free / 1024 / 1024
	hostStatus.MemCacheMB = memory.Cached / 1024 / 1024
	hostStatus.MemAvailableMB = memory.Available / 1024 / 1024

	swap, err := mem.SwapMemory()
	if err != nil {
		return err
	}

	hostStatus.SwapTotalMB = swap.Total / 1024 / 1024
	hostStatus.SwapUsedMB = swap.Used / 1024 / 1024

	return nil
}

// SetDiskStatus set this host disk status
func (c *Collector) SetDiskStatus(hostStatus *haprobe.HostMetric) error {
	partitions, err := disk.Partitions(false)
	if err != nil {
		logger.Error("failed to get partitions info, %v", err)
		return err
	}

	for _, partition := range partitions {
		usageStat, err := disk.Usage(partition.Mountpoint)
		if err != nil {
			logger.Error("failed to get disk usage info. errmsg: %v", err)
			continue
		}

		hostStatus.DiskUsagePercent += usageStat.UsedPercent / 2
		hostStatus.DiskTotal += usageStat.Total / 1024 / 1024
		hostStatus.DiskUsed += usageStat.Used / 1024 / 1024
		hostStatus.DiskAvailable += usageStat.Free / 1024 / 1024
	}

	return nil
}

// setNetStatus set this host net status
func (c *Collector) SetNetStatus(hostStatus *haprobe.HostMetric) error {
	ifaces, err := net.Interfaces()
	if err != nil {
		return err
	}

	for _, iface := range ifaces {
		if iface.Flags&net.FlagLoopback != 0 || iface.Flags&net.FlagUp == 0 {
			continue
		}

		addrs, err := iface.Addrs()
		if err != nil {
			continue
		}

		for _, addr := range addrs {
			var ip net.IP
			switch v := addr.(type) {
			case *net.IPNet:
				ip = v.IP

			case *net.IPAddr:
				ip = v.IP
			}

			// skip ipv6
			if ip == nil || ip.IsLoopback() || !ip.IsGlobalUnicast() {
				continue
			}

			hostStatus.NetIPs = append(hostStatus.NetIPs, ip.String())
		}
	}

	// Network usage
	networkUsage := ""
	netIO, err := gopsutilnet.IOCounters(true)
	if err != nil {
		return err
	}

	for _, io := range netIO {
		networkUsage += fmt.Sprintf("%s rx=%dB, tx=%dB; ", io.Name, io.BytesRecv, io.BytesSent)
		hostStatus.NetBytesIn += io.BytesRecv
		hostStatus.NetBytesOut += io.BytesSent
	}
	hostStatus.NetUsage = networkUsage

	// Network TCP connections
	netTCP, err := gopsutilnet.Connections("tcp")
	if err == nil {
		hostStatus.NetTCPConnections = uint(len(netTCP))
	}

	// Network packet loss
	hostStatus.NetPacketLossIn, hostStatus.NetPacketLossOut, err = c.obtainPacketLoss()
	return err
}

// obtainPacketLoss obtain the network packet loss
func (c *Collector) obtainPacketLoss() (lossRateIn float64, lossRateOut float64, err error) {
	stats1, err := gopsutilnet.IOCounters(true)
	if err != nil {
		fmt.Printf("failed to get netwokr stats: %v\n", err)
		return
	}

	time.Sleep(1 * time.Second)

	stats2, err := gopsutilnet.IOCounters(true)
	if err != nil {
		fmt.Printf("failed to get network info: %v\n", err)
		return
	}

	statsLen := len(stats1)
	for i := range stats1 {
		if stats1[i].Name != stats2[i].Name {
			continue
		}

		dropIn := stats2[i].Dropin - stats1[i].Dropin
		dropOut := stats2[i].Dropout - stats1[i].Dropout
		packetsIn := stats2[i].PacketsRecv - stats1[i].PacketsRecv
		packetsOut := stats2[i].PacketsSent - stats1[i].PacketsSent

		if packetsIn > 0 {
			lossRateIn += float64(dropIn) / float64(packetsIn) / float64(statsLen) * 100
		}

		if packetsOut > 0 {
			lossRateOut += float64(dropOut) / float64(packetsOut) / float64(statsLen) * 100
		}
	}

	return lossRateIn, lossRateOut, err
}
