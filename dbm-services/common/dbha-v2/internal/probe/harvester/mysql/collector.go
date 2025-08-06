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
	"dbm-services/common/dbha-v2/pkg/converter"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
	"fmt"
	"math"
	"net"
	"strings"
	"time"

	"github.com/shirou/gopsutil/cpu"
	"github.com/shirou/gopsutil/disk"
	"github.com/shirou/gopsutil/load"
	"github.com/shirou/gopsutil/mem"
	"gorm.io/gorm"

	gopsutilnet "github.com/shirou/gopsutil/v4/net"
)

type globalStatus struct {
	Variable string `gorm:"column:Variable_name"`
	Value    string `gorm:"column:Value"`
}

// collectMySQLInfo collect single instance MySQL metrics.
func collectMySQLInfo(db *gorm.DB, dbMetric *haprobe.DatabaseMetric) error {
	sqlDB, err := db.DB()
	if err != nil {
		return err
	}

	if err := sqlDB.Ping(); err != nil {
		return err
	}

	var statusResults []globalStatus
	err = db.Raw("SHOW GLOBAL STATUS").Scan(&statusResults).Error
	if err != nil {
		return err
	}

	status := map[string]string{}
	for _, result := range statusResults {
		status[strings.ToLower(result.Variable)] = result.Value
	}

	obtainConnectionStatus(status, dbMetric)

	obtainQueryStatus(status, dbMetric)

	obtainQueryCache(status, dbMetric)

	obtainTableStatus(status, dbMetric)

	obtainBinlog(status, dbMetric)

	obtainPerformanceSchema(status, dbMetric)

	obtainOtherMetrics(status, dbMetric)

	var version string
	err = db.Raw("SELECT VERSION() as version").Scan(&version).Error
	if err == nil {
		dbMetric.Version = version
	}

	var portResult globalStatus
	err = db.Raw("SHOW VARIABLES LIKE 'port'").Scan(&portResult).Error
	if err != nil {
		logger.Warn("failed to get mysql listen port, %v", err)
		return err
	}

	port, err := converter.ToInt(portResult.Value)
	if err != nil {
		logger.Error("failed to parse mysql listen port, port(%v), %v", portResult.Value, err)
		return err
	}

	logger.Debug("mysql listen port:%v", port)

	dbMetric.ListenPort = port

	// Key buffer read hit rate
	if dbMetric.KeyReadRequests != 0 {
		dbMetric.KeyBufferHitRate = float64(dbMetric.KeyReads) / float64(dbMetric.KeyReadRequests)
	}

	return nil
}

// obtainCPUMetrics obtain the CPU metrics
func obtainCPUMetrics(systemMetric *haprobe.HostMetric) error {
	cpuPercent, err := cpu.Percent(1*time.Second, false)
	if err != nil {
		return gerrors.Newf(gerrors.ComponentFailure, "failed to obtain CPU percent, %v", err)
	}

	if len(cpuPercent) == 0 {
		return gerrors.New(gerrors.Failure, "failed to obtain CPU percent, empty data set")
	}

	cpuTimes, err := cpu.Times(false)
	if err != nil {
		return gerrors.Newf(gerrors.ComponentFailure, "failed to obtain CPU time, %v", err)
	}

	if len(cpuTimes) == 0 {
		return gerrors.New(gerrors.Failure, "failed to obtain CPU time, empty data set")
	}

	systemMetric.CPUUsagePercent = cpuPercent[0]

	total := cpuTimes[0].Total()
	if math.Float64bits(total) == 0 {
		return gerrors.New(gerrors.Failure, "total CPU time is zero")
	}

	systemMetric.CPUUserPercent = cpuTimes[0].User / total * 100
	systemMetric.CPUSystemPercent = cpuTimes[0].System / total * 100
	systemMetric.CPUIOWaitPercent = cpuTimes[0].Iowait / total * 100

	load, err := load.Avg()
	if err != nil {
		return gerrors.Newf(gerrors.ComponentFailure, "failed to obtain CPU load average, %v", err)
	}

	systemMetric.CPULoad1 = load.Load1
	systemMetric.CPULoad5 = load.Load5
	systemMetric.CPULoad15 = load.Load15

	return nil
}

// obtainStorageMetrics obtain the storage metrics
func obtainStorageMetrics(systemMetric *haprobe.HostMetric) error {
	memory, err := mem.VirtualMemory()
	if err != nil {
		return err
	}

	// convert the value from BYTE to MB
	systemMetric.MemTotalMB = memory.Total / 1024 / 1024
	systemMetric.MemUsedMB = memory.Used / 1024 / 1024
	systemMetric.MemFreeMB = memory.Free / 1024 / 1024
	systemMetric.MemCacheMB = memory.Cached / 1024 / 1024
	systemMetric.MemAvailableMB = memory.Available / 1024 / 1024

	swap, err := mem.SwapMemory()
	if err != nil {
		return err
	}

	systemMetric.SwapTotalMB = swap.Total / 1024 / 1024
	systemMetric.SwapUsedMB = swap.Used / 1024 / 1024

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

		systemMetric.DiskUsagePercent += usageStat.UsedPercent / 2
		systemMetric.DiskTotal += usageStat.Total / 1024 / 1024
		systemMetric.DiskUsed += usageStat.Used / 1024 / 1024
		systemMetric.DiskAvailable += usageStat.Free / 1024 / 1024
	}

	return nil
}

// obtainNetworkMetrics obtain the network metrics
func obtainNetworkMetrics(systemMetric *haprobe.HostMetric) error {
	ipAddress := ""
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

			if ipAddress != "" {
				ipAddress += ";"
			}
			ipAddress += ip.String()
		}
	}
	systemMetric.NetIpAddress = ipAddress

	// Network usage
	networkUsage := ""
	netIO, err := gopsutilnet.IOCounters(true)
	if err != nil {
		return err
	}

	for _, io := range netIO {
		networkUsage += fmt.Sprintf("%s rx=%dB, tx=%dB; ", io.Name, io.BytesRecv, io.BytesSent)
		systemMetric.NetBytesIn += io.BytesRecv
		systemMetric.NetBytesOut += io.BytesSent
	}
	systemMetric.NetUsage = networkUsage

	// Network TCP connections
	netTCP, err := gopsutilnet.Connections("tcp")
	if err == nil {
		systemMetric.NetTCPConnections = uint(len(netTCP))
	}

	// Network packet loss
	systemMetric.NetPacketLossIn, systemMetric.NetPacketLossOut, err = obtainPacketLoss()
	return err
}

// obtainPacketLoss obtain the network packet loss
func obtainPacketLoss() (lossRateIn float64, lossRateOut float64, err error) {
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

// obtainConnectionStatus obtain the connection status
func obtainConnectionStatus(globalStatus map[string]string, dbMetric *haprobe.DatabaseMetric) {
	transferToInt(globalStatus, "threads_running", &dbMetric.ThreadsRunning)
	transferToInt(globalStatus, "aborted_connects", &dbMetric.ConnectionsAborted)
	transferToInt(globalStatus, "connections", &dbMetric.Connections)
	transferToInt(globalStatus, "connection_errors_accept", &dbMetric.ConnectionsErrorsAccept)
	transferToInt(globalStatus, "connection_errors_internal", &dbMetric.ConnectionsErrorsInternal)
	transferToInt(globalStatus, "connection_errors_peer_address", &dbMetric.ConnectionsErrorsPeerAddr)
}

// obtainQueryStatus obtain the query status
func obtainQueryStatus(globalStatus map[string]string, dbMetric *haprobe.DatabaseMetric) {
	transferToUint64(globalStatus, "queries", &dbMetric.QueryTotal)
	transferToUint64(globalStatus, "questions", &dbMetric.QueryQuestions)
	transferToUint64(globalStatus, "com_select", &dbMetric.QuerySelects)
	transferToUint64(globalStatus, "com_insert", &dbMetric.QueryInserts)
	transferToUint64(globalStatus, "com_update", &dbMetric.QueryUpdates)
	transferToUint64(globalStatus, "com_delete", &dbMetric.QueryDeletes)
	transferToUint64(globalStatus, "slow_queries", &dbMetric.QuerySlow)
}

// obtainQueryCache obtain the query cache status
func obtainQueryCache(globalStatus map[string]string, dbMetric *haprobe.DatabaseMetric) {
	transferToUint64(globalStatus, "key_read_requests", &dbMetric.KeyReadRequests)
	transferToUint64(globalStatus, "key_reads", &dbMetric.KeyReads)
	transferToUint64(globalStatus, "qcache_hits", &dbMetric.QCacheHits)
	transferToUint64(globalStatus, "qcache_inserts", &dbMetric.QCacheInserts)
	transferToUint64(globalStatus, "qcache_lowmen_prunes", &dbMetric.QCachePrunes)
	transferToUint64(globalStatus, "qcache_not_cached", &dbMetric.QCacheNotCached)
	transferToUint64(globalStatus, "qcache_total_blocks", &dbMetric.QCacheTotalBlocks)
	transferToUint64(globalStatus, "qcache_free_blocks", &dbMetric.QCacheFreeBlocks)
	transferToUint64(globalStatus, "qcache_free_mem", &dbMetric.QCacheFreeMem)
}

// obtainTableStatus obtain the table status
func obtainTableStatus(globalStatus map[string]string, dbMetric *haprobe.DatabaseMetric) {
	transferToUint64(globalStatus, "created_tmp_disk_tables", &dbMetric.TableCreatedTmpDisk)
	transferToUint64(globalStatus, "created_tmp_tables", &dbMetric.TableCreatedTmp)
	transferToUint64(globalStatus, "opened_tables", &dbMetric.TableOpen)
	transferToUint64(globalStatus, "opened_files", &dbMetric.FileOpen)
	transferToUint(globalStatus, "flush_commands", &dbMetric.TableFlush)
}

// obtainBinlog obtain binlog information
func obtainBinlog(globalStatus map[string]string, dbMetric *haprobe.DatabaseMetric) {
	transferToUint64(globalStatus, "binlog_cache_disk_use", &dbMetric.BinlogCacheDiskUse)
	transferToUint64(globalStatus, "binlog_cache_use", &dbMetric.BinlogCacheUse)
	transferToUint64(globalStatus, "binlog_stmt_cache_disk_use", &dbMetric.BinlogStmtCacheDiskUse)
	transferToUint64(globalStatus, "binlog_stmt_cache_use", &dbMetric.BinlogStmtCacheUse)
}

// obtainPerformanceSchema obtain performance information
func obtainPerformanceSchema(globalStatus map[string]string, dbMetric *haprobe.DatabaseMetric) {
	transferToUint64(globalStatus, "performance_schema_accounts_lost", &dbMetric.SchemaAccountsLost)
	transferToUint64(globalStatus, "performance_schema_cond_classes_lost", &dbMetric.SchemaCondClassesLost)
	transferToUint64(globalStatus, "performance_schema_file_handles_lost", &dbMetric.SchemaFileHandlesLost)
	transferToUint64(globalStatus, "performance_schema_locker_lost", &dbMetric.SchemaLockerLost)
	transferToUint64(globalStatus, "performance_schema_digest_lost", &dbMetric.SchemaDigestLost)
	transferToUint64(globalStatus, "performance_schema_rwlock_instances_lost", &dbMetric.SchemaRwlockInstancesLost)
	transferToUint64(globalStatus, "performance_schema_thread_instances_lost", &dbMetric.SchemaThreadInstancesLost)
	transferToUint64(globalStatus, "performance_schema_table_lock_stat_lost", &dbMetric.SchemaTableLockStatLost)
}

// obtainOtherMetrics obtain the other information
func obtainOtherMetrics(globalStatus map[string]string, dbMetric *haprobe.DatabaseMetric) {
	if val, exists := globalStatus["character_set_server"]; exists {
		dbMetric.ServerCharset = val
	}

	transferToUint64(globalStatus, "com_commit", &dbMetric.QueryCommits)
	transferToUint64(globalStatus, "com_rollback", &dbMetric.QueryRollbacks)

	val, exists := globalStatus["uptime"]
	if !exists {
		logger.Warn("missed the field(uptime)")
		return
	}

	v, err := converter.ToUint64(val)
	if err != nil {
		logger.Warn("do not parse mysql status uptime, %v", v)
		return
	}

	if v == 0 {
		return
	}

	dbMetric.AvgQPS = uint(dbMetric.QueryTotal / v)
	dbMetric.AvgTPS = uint((dbMetric.QueryCommits + dbMetric.QueryRollbacks) / v)
}

// transferToInt converty the value of the key to int value
func transferToInt(m map[string]string, key string, target *int) {
	val, ok := m[key]
	if !ok {
		logger.Warn("missed the field(%s)", key)
		return
	}

	v, err := converter.ToInt(val)
	if err != nil {
		logger.Error("failed to parse the field(%s), %v", key, err)
		return
	}

	*target = v
}

// transferToUint64 convert the value of the key to uint64 value
func transferToUint64(m map[string]string, key string, target *uint64) {
	val, exists := m[key]
	if !exists {
		logger.Warn("the key(%s) does not exist", key)
		return
	}

	v, err := converter.ToUint64(val)
	if err != nil {
		logger.Warn("parse the key(%v) value failed, %v", key, err)
		return
	}

	*target = v
}

// transferToUint convert the value of the key to uint value
func transferToUint(m map[string]string, key string, target *uint) {
	val, exists := m[key]
	if !exists {
		logger.Warn("missed the field(%s)", key)
		return
	}

	v, err := converter.ToUint(val)
	if err != nil {
		logger.Warn("parse the key(%v) value failed, %v", key, err)
		return
	}

	*target = v
}
