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

package mysql

import (
	"fmt"
	"math"
	"net"
	"time"

	"dbm-services/common/dbha-v2/pkg/converter"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/hanet"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"

	"github.com/shirou/gopsutil/cpu"
	"github.com/shirou/gopsutil/disk"
	"github.com/shirou/gopsutil/load"
	"github.com/shirou/gopsutil/mem"

	gopsutilnet "github.com/shirou/gopsutil/v4/net"
)

type collector struct {
	clusterType haprobe.DbmMetadataClusterType
	machineType haprobe.DbmMetadataMachineType
	accessLayer haprobe.DbmMetadataAccessLayerType
	user        string
	password    string
	endpoint    *hanet.Endpoint
	db          *hamysql.GormDB
}

func (c *collector) open() (*haprobe.DbEvent, error) {
	db, err := hamysql.NewGormDB(
		hamysql.OptionProto(c.endpoint.Proto),
		hamysql.OptionIP(c.endpoint.Host),
		hamysql.OptionPort(c.endpoint.Port),
		hamysql.OptionUser(c.user),
		hamysql.OptionPassword(c.password),
		hamysql.OptionSkipInitializeWithVersion(false),
		hamysql.OptionDisableDatetimePrecision(true),
		hamysql.OptionCharset(""),
	)

	if err != nil {
		logger.Warn("create mysql db operator failed, %v", err)
		event := &haprobe.DbEvent{
			Name:       haprobe.DbEventNameDetectFailure,
			Reason:     haprobe.DbEventNameReasonConnectionException,
			DbTypeName: haprobe.DbTypeMysql,
			Endpoint:   c.endpoint,
			Message:    err.Error(),
		}

		return event, err
	}

	sqlDb, err := db.DB().DB()

	if err != nil {
		event := &haprobe.DbEvent{
			Name:       haprobe.DbEventNameDetectFailure,
			Reason:     haprobe.DbEventNameReasonConnectionException,
			DbTypeName: haprobe.DbTypeMysql,
			Endpoint:   c.endpoint,
			Message:    err.Error(),
		}

		return event, err
	}

	sqlDb.SetMaxIdleConns(1)
	sqlDb.SetMaxOpenConns(3)
	sqlDb.SetConnMaxLifetime(time.Minute * 3)

	c.db = db
	return nil, nil
}

func (c *collector) close() {
	if c.db != nil {
		c.db.Close()
	}
}

func (c *collector) isTendbHaProxy() bool {
	return c.accessLayer == haprobe.DbmMetadataAccessLayerTypeProxy &&
		c.machineType == haprobe.DbmMetadataMachineTypeProxy &&
		c.clusterType == haprobe.DbmMetadataClusterTypeTendb
}

func (c *collector) isTendbClusterProxy() bool {
	return c.accessLayer == haprobe.DbmMetadataAccessLayerTypeProxy &&
		c.machineType == haprobe.DbmMetadataMachineTypeSpider &&
		c.clusterType == haprobe.DbmMetadataClusterTypeTendbCluster
}

func (c *collector) obtainTendbClusterProxyStatus() (*haprobe.MySqlSpiderCtlStatus, error) {
	var routes []haprobe.MySqlSpiderCtlRoute
	err := c.db.DB().Raw("select * from mysql.servers").Scan(&routes).Error

	if err != nil {
		logger.Warn("failed to get MySQL spider routes, errmsg: %s", err)
		return nil, err
	}

	var nodes []haprobe.MySqlSpiderCtlNode
	err = c.db.DB().Raw("select * from information_schema.TDBCTL_NODES").Scan(&nodes).Error

	if err != nil {
		logger.Warn("failed to get MySQL spider nodes, errmsg: %s", err)
		return nil, err
	}

	status := &haprobe.MySqlSpiderCtlStatus{
		Routes:   routes,
		CtlNodes: nodes,
	}

	return status, nil
}

func (c *collector) obtainTendbHaProxyStatus() (*haprobe.MySqlProxyStatus, error) {
	var backends []haprobe.MySqlProxyBackend
	err := c.db.DB().Raw("select * from backends").Scan(&backends).Error

	if err != nil {
		logger.Warn("failed to get MySQL proxy status, errmsg: %s", err)
		return nil, err
	}

	return &haprobe.MySqlProxyStatus{Backends: backends}, nil
}

func (c *collector) obtainGlobalStatus() (*haprobe.MySqlGlobalStatus, error) {
	var statusResults []globalStatus
	err := c.db.DB().Raw("SHOW GLOBAL STATUS").Scan(&statusResults).Error
	if err != nil {
		return nil, err
	}

	dbStatus := convertToMySqlStatus(statusResults)

	var version string
	err = c.db.DB().Raw("SELECT VERSION() as version").Scan(&version).Error
	if err != nil {
		logger.Warn("failed to get mysql version, errmsg: %s", err)
		return nil, err
	}
	dbStatus.Version = version

	var portResult globalStatus
	err = c.db.DB().Raw("SHOW VARIABLES LIKE 'port'").Scan(&portResult).Error
	if err != nil {
		logger.Warn("failed to get mysql listen port, result: %s, errmsg: %s", portResult, err)
		return nil, err
	}

	port, err := converter.ToInt(portResult.Value)
	if err != nil {
		logger.Error("failed to convert mysql listen port to int, port: %v, errmsg: %s", portResult.Value, err)
		return nil, err
	}

	logger.Debug("mysql listen port:%v", port)

	dbStatus.ListenPort = port

	// Key buffer read hit rate
	if dbStatus.KeyReadRequests != 0 {
		dbStatus.KeyBufferHitRate = float64(dbStatus.KeyReads) / float64(dbStatus.KeyReadRequests)
	}

	return dbStatus, err
}

// obtainlHostStatus obtain this host status
func (c *collector) obtainHostStatus() (*haprobe.HostMetric, error) {
	hostStatus := &haprobe.HostMetric{}

	if err := c.setCpuStatus(hostStatus); err != nil {
		logger.Warn("failed to update CPU status, errmsg: %s", err)
	}

	if err := c.setNetStatus(hostStatus); err != nil {
		logger.Warn("failed to update Net status, errmsg: %s", err)
	}

	if err := c.setStorageStatus(hostStatus); err != nil {
		logger.Warn("failed to update storage status, errmsg: %s", err)
	}

	return hostStatus, nil
}

func (c *collector) setCpuStatus(sysMetric *haprobe.HostMetric) error {

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

	sysMetric.CpuUsagePercent = cpuPercent[0]

	total := cpuTimes[0].Total()
	if math.Float64bits(total) == 0 {
		return gerrors.New(gerrors.Failure, "total CPU time is zero")
	}

	sysMetric.CpuUserPercent = cpuTimes[0].User / total * 100
	sysMetric.CpuSystemPercent = cpuTimes[0].System / total * 100
	sysMetric.CpuIOWaitPercent = cpuTimes[0].Iowait / total * 100

	load, err := load.Avg()
	if err != nil {
		return gerrors.Newf(gerrors.Failure, "failed to obtain CPU load average, %v", err)
	}

	sysMetric.CpuLoad1 = load.Load1
	sysMetric.CpuLoad5 = load.Load5
	sysMetric.CpuLoad15 = load.Load15

	return nil
}

func (c *collector) setStorageStatus(sysMetric *haprobe.HostMetric) error {
	memory, err := mem.VirtualMemory()
	if err != nil {
		return err
	}

	// convert the value from Byte to MB
	sysMetric.MemTotalMB = memory.Total / 1024 / 1024
	sysMetric.MemUsedMB = memory.Used / 1024 / 1024
	sysMetric.MemFreeMB = memory.Free / 1024 / 1024
	sysMetric.MemCacheMB = memory.Cached / 1024 / 1024
	sysMetric.MemAvailableMB = memory.Available / 1024 / 1024

	swap, err := mem.SwapMemory()
	if err != nil {
		return err
	}

	sysMetric.SwapTotalMB = swap.Total / 1024 / 1024
	sysMetric.SwapUsedMB = swap.Used / 1024 / 1024

	// Disk
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

		sysMetric.DiskUsagePercent += usageStat.UsedPercent / 2
		sysMetric.DiskTotal += usageStat.Total / 1024 / 1024
		sysMetric.DiskUsed += usageStat.Used / 1024 / 1024
		sysMetric.DiskAvailable += usageStat.Free / 1024 / 1024
	}

	return nil
}

// setNetStatus set this host net status
func (c *collector) setNetStatus(sysMetric *haprobe.HostMetric) error {
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

			sysMetric.NetIPs = append(sysMetric.NetIPs, ip.String())
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
		sysMetric.NetBytesIn += io.BytesRecv
		sysMetric.NetBytesOut += io.BytesSent
	}
	sysMetric.NetUsage = networkUsage

	// Network TCP connections
	netTCP, err := gopsutilnet.Connections("tcp")
	if err == nil {
		sysMetric.NetTCPConnections = uint(len(netTCP))
	}

	// Network packet loss
	sysMetric.NetPacketLossIn, sysMetric.NetPacketLossOut, err = c.obtainPacketLoss()
	return err
}

// obtainPacketLoss obtain the network packet loss
func (c *collector) obtainPacketLoss() (lossRateIn float64, lossRateOut float64, err error) {
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
