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
	"context"
	"dbm-services/common/dbha-v2/internal/probe/config"
	"dbm-services/common/dbha-v2/internal/probe/harvester/plugin"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
	"fmt"
	"net"
	"strconv"
	"sync"
	"time"

	"github.com/shirou/gopsutil/v4/cpu"
	"github.com/shirou/gopsutil/v4/disk"
	"github.com/shirou/gopsutil/v4/load"
	"github.com/shirou/gopsutil/v4/mem"
	gopsutilnet "github.com/shirou/gopsutil/v4/net"
	"gorm.io/driver/mysql"
	"gorm.io/gorm"
)

const (
	Name    = "mysql"
	Version = "v1.0.0"
)

// MySql mysql harvester
type MySql struct {
	// NOTE: Must include UnimplementedMethod
	plugin.UnimplementedMethod
	config mySqlOptions
	wg     sync.WaitGroup
	// historyMetrics is a map for calculatring realtime QPS
	historyMetrics map[string]*haprobe.DatabaseMetric
	historyMutex   sync.RWMutex
}

// GlobalStatus is a struct for mysql global status
type GlobalStatus struct {
	Variable string `gorm:"column:Variable_name"`
	Value    string `gorm:"column:Value"`
}

// NewMySql constructor
func NewMySql(opts ...Option) *MySql {
	mySqlOpts := defaultMySqlOptions

	for _, opt := range opts {
		opt.apply(&mySqlOpts)
	}

	return &MySql{
		config:         mySqlOpts,
		historyMetrics: make(map[string]*haprobe.DatabaseMetric),
	}
}

// Name returns the name of the plugin.
func (m *MySql) Name() (string, error) {
	return Name, nil
}

// Version returns the version of the plugin.
func (m *MySql) Version() (string, error) {
	return Version, nil
}

// Close closes the plugin.
func (m *MySql) Close() error {
	// wait for all goroutines to finish
	m.wg.Wait()

	// add a lock to clean up history metrics
	m.historyMutex.Lock()
	defer m.historyMutex.Unlock()

	// clean up history metrics
	for k := range m.historyMetrics {
		delete(m.historyMetrics, k)
	}

	logger.Info("MySQL harvester plugin closed successfully")
	return nil
}

// Harvest harvests data from the target instance.
func (m *MySql) Harvest(ctx context.Context) (chan *plugin.HarvestData, error) {
	logger.Info("start mysql harvest, interval time is: %v", m.config.reportInterval)

	dataC := make(chan *plugin.HarvestData, 1024)

	m.wg.Add(1)
	go func(ctx context.Context) {
		defer m.wg.Done()
		defer close(dataC)

		ticker := time.NewTicker(time.Duration(m.config.reportInterval) * time.Second)
		defer ticker.Stop()
		for {
			select {
			case <-ctx.Done():
				logger.Info(" exit mysql harvest plugin")
				return

			case <-ticker.C:
				// collect data from the target instance.
				metrics, err := m.collectAndSaveMetrics()
				if err != nil {
					logger.Error("failed to collect mysql metrics: %v", err)
					// Retry next instance if failed to maintain availability
					continue
				}
				dataC <- &plugin.HarvestData{
					Data: metrics,
				}
			}
		}
	}(ctx)

	return dataC, nil
}

// collectAndSaveMetrics collects and saves metrics.
func (m *MySql) collectAndSaveMetrics() (*haprobe.MySQLMetric, error) {
	// 1. collect metrics from system
	systemMetric, err := m.collectSystemMetrics()
	if err != nil {
		return nil, err
	}

	// 2. collect metrics from mysql instances
	mysqlMetrics, err := m.collectMysqlMetrics()
	if err != nil {
		return nil, err
	}

	// 3. combine metrics
	metrics := &haprobe.MySQLMetric{
		SequenceID:      0,
		MachineID:       "",
		MessageID:       "",
		ServiceID:       "",
		ReportTimestamp: 0,
		Host:            systemMetric,
		Databases:       mysqlMetrics, // slice,mysql instance metrics
	}

	return metrics, nil
}

// collectSystemMetrics collects system metrics.
func (m *MySql) collectSystemMetrics() (*haprobe.HostMetric, error) {

	systemMetric := &haprobe.HostMetric{}
	if err := getCPUMetrics(systemMetric); err != nil {
		logger.Info(" failed to harvest CPU info. errmsg: %v", err)
		return systemMetric, err
	}

	if err := getStorageMetrics(systemMetric); err != nil {
		logger.Info(" failed to harvest Swap/Memory/Disk info. errmsg: %v", err)
		return systemMetric, err
	}

	if err := getNetworkMetrics(systemMetric); err != nil {
		logger.Info(" failed to harvest Network info. errmsg: %v", err)
		return systemMetric, err
	}

	return systemMetric, nil
}

func getCPUMetrics(systemMetric *haprobe.HostMetric) error {
	// CPU
	cpuPercent, err := cpu.Percent(1*time.Second, false)
	if err != nil {
		return err
	}

	cpuTimes, err := cpu.Times(false)
	if err == nil && len(cpuTimes) > 0 {
		systemMetric.CPUUserPercent = cpuTimes[0].User / cpuTimes[0].Total() * 100
		systemMetric.CPUSystemPercent = cpuTimes[0].System / cpuTimes[0].Total() * 100
		systemMetric.CPUIOWaitPercent = cpuTimes[0].Iowait / cpuTimes[0].Total() * 100
	}

	if len(cpuPercent) > 0 {
		systemMetric.CPUUsagePercent = cpuPercent[0]
	}
	// CPU load
	load, err := load.Avg()
	if err == nil {
		systemMetric.CPULoad1 = load.Load1
		systemMetric.CPULoad5 = load.Load5
		systemMetric.CPULoad15 = load.Load15
	}
	return nil
}

func getStorageMetrics(systemMetric *haprobe.HostMetric) error {
	// Memory
	memory, err := mem.VirtualMemory()
	if err == nil {
		systemMetric.MemTotalMB = memory.Total / 1024 / 1024
		systemMetric.MemUsedMB = memory.Used / 1024 / 1024
		systemMetric.MemFreeMB = memory.Free / 1024 / 1024
		systemMetric.MemCacheMB = memory.Cached / 1024 / 1024
		systemMetric.MemAvailableMB = memory.Available / 1024 / 1024
	}

	// Swap
	swap, err := mem.SwapMemory()
	if err == nil {
		systemMetric.SwapTotalMB = swap.Total / 1024 / 1024
		systemMetric.SwapUsedMB = swap.Used / 1024 / 1024
	}

	// Disk
	partitions, err := disk.Partitions(false)
	if err != nil {
		logger.Error(" failed to get partitions info. errmsg: %v", err)
		return err
	}

	for _, partition := range partitions {
		usageStat, err := disk.Usage(partition.Mountpoint)
		if err != nil {
			logger.Error(" failed to get disk usage info. errmsg: %v", err)
			continue
		}

		systemMetric.DiskUsagePercent += usageStat.UsedPercent / 2
		systemMetric.DiskTotal += usageStat.Total / 1024 / 1024
		systemMetric.DiskUsed += usageStat.Used / 1024 / 1024
		systemMetric.DiskAvailable += usageStat.Free / 1024 / 1024

		for _, opt := range partition.Opts {
			if opt == "ro" {
				systemMetric.DiskReadOnly = true
			}
		}
	}
	return nil
}

func getNetworkMetrics(systemMetric *haprobe.HostMetric) error {
	// Network
	ipAddress := ""
	ifaces, err := net.Interfaces()
	if err == nil {
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
					ipAddress += ", "
				}
				ipAddress += ip.String()
			}
		}
	}
	systemMetric.NetIpAddress = ipAddress

	// Network usage
	networkUsage := ""
	netIO, err := gopsutilnet.IOCounters(true)
	if err == nil {
		for _, io := range netIO {
			networkUsage += fmt.Sprintf("%s rx=%dB, tx=%dB; ", io.Name, io.BytesRecv, io.BytesSent)
			systemMetric.NetBytesIn += io.BytesRecv
			systemMetric.NetBytesOut += io.BytesSent
		}
	}
	systemMetric.NetUsage = networkUsage

	// Network TCP connections
	netTCP, err := gopsutilnet.Connections("tcp")
	if err == nil {
		systemMetric.NetTCPConnections = uint(len(netTCP))
	}

	// Network packet loss
	systemMetric.NetPacketLossIn, systemMetric.NetPacketLossOut = getPacketLoss()
	return nil
}

// getPacketLoss get network packet loss rate
func getPacketLoss() (lossRateIn float64, lossRateOut float64) {

	stats1, err := gopsutilnet.IOCounters(true)
	if err != nil {
		fmt.Printf("failed to get netwokr stats: %v\n", err)
		return
	}

	time.Sleep(1 * time.Second)

	stats2, err := gopsutilnet.IOCounters(true)
	if err != nil {
		fmt.Printf(" failed to get network info: %v\n", err)
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
	return lossRateIn, lossRateOut
}

// collectMySQLInfo collect all instances MySQL metrics.
func (m *MySql) collectMysqlMetrics() ([]*haprobe.DatabaseMetric, error) {
	var allDbMetrics []*haprobe.DatabaseMetric

	// Use default config if no instances configured (backward compatibility)
	if len(m.config.instances) == 0 {
		// Validate default configuration
		if m.config.host == "" || m.config.port <= 0 || m.config.user == "" {
			return nil, fmt.Errorf("missing required default configuration: host=%s, port=%d, user=%s",
				m.config.host, m.config.port, m.config.user)
		}

		// Use single default instance
		instance := config.InstanceConfig{
			Host:     m.config.host,
			Port:     m.config.port,
			User:     m.config.user,
			Password: m.config.password,
			Name:     fmt.Sprintf("%s:%d", m.config.host, m.config.port),
		}
		m.config.instances = []config.InstanceConfig{instance}
	}

	// Iterate over configured instances
	for _, instance := range m.config.instances {
		logger.Info("collecting metrics for MySQL instance: %s", instance.Name)

		// MySQL DSN
		dsn := fmt.Sprintf("%s:%s@tcp(%s:%d)/?charset=utf8mb4&parseTime=True&loc=Local",
			instance.User,
			instance.Password,
			instance.Host,
			instance.Port,
		)

		// Connect to MySQL
		db, err := gorm.Open(mysql.Open(dsn))
		if err != nil {
			logger.Error("failed to connect to mysql instance %s. errmsg: %v", instance.Name, err)
			// continue with other instances even if one fails
			continue
		}

		// create a DatabaseMetric to store instance metrics
		instanceDbMetrics := haprobe.DatabaseMetric{}

		if err := collectMySQLInfo(db, &instanceDbMetrics, instance.Name); err != nil {
			logger.Error("failed to collect mysql info for instance %s. errmsg: %v", instance.Name, err)
			if conn, err := db.DB(); err == nil {
				conn.Close()
			}
			continue
		}

		// realtime QPS
		m.calculateRealTimeQPS(instance.Name, &instanceDbMetrics)

		if conn, err := db.DB(); err == nil {
			conn.Close()
		}
		instanceDbMetrics.ListenPort = instance.Port
		// add single instance metrics to all metrics
		allDbMetrics = append(allDbMetrics, &instanceDbMetrics)

		logger.Info("successfully collected metrics for MySQL instance: %s", instance.Name)
	}

	if len(allDbMetrics) == 0 {
		return nil, fmt.Errorf("no MySQL instances were successfully connected")
	}

	return allDbMetrics, nil
}

// collectMySQLInfo collect single instance MySQL metrics.
func collectMySQLInfo(db *gorm.DB, dbMetric *haprobe.DatabaseMetric, instanceName string) error {
	// valide database connection
	if db == nil {
		return fmt.Errorf("database connection is nil for instance: %s", instanceName)
	}
	sqlDB, err := db.DB()
	if err != nil {
		return fmt.Errorf("failed to get underlying sql.DB for instance %s: %v", instanceName, err)
	}
	if err := sqlDB.Ping(); err != nil {
		return fmt.Errorf("failed to ping database for instance %s: %v", instanceName, err)
	}

	var globalStatusList []GlobalStatus
	err = db.Raw("SHOW GLOBAL STATUS").Scan(&globalStatusList).Error
	if err != nil {
		return fmt.Errorf("failed to execute SHOW GLOBAL STATUS for instance %s: %v", instanceName, err)
	}

	globalStatus := make(map[string]string)
	for _, status := range globalStatusList {
		globalStatus[status.Variable] = status.Value
	}

	// Connection status
	getConnectionStatus(globalStatus, dbMetric)

	// Query status
	getQueryStatus(globalStatus, dbMetric)

	// Average QPS/TPS

	// Query cache
	getQueryCache(globalStatus, dbMetric)

	// Table Status
	getTableStatus(globalStatus, dbMetric)

	// BinLog
	getBinlog(globalStatus, dbMetric)
	// performance Schema
	getPerformanceSchema(globalStatus, dbMetric)
	// Others
	getOtherMetrics(globalStatus, dbMetric)

	var version string
	err = db.Raw("SELECT VERSION() as version").Scan(&version).Error
	if err == nil {
		dbMetric.Version = version
	}

	var portResult GlobalStatus
	err = db.Raw("SHOW VARIABLES LIKE 'port'").Scan(&portResult).Error
	if err == nil {
		if port, err := strconv.Atoi(portResult.Value); err == nil {
			dbMetric.ListenPort = port
		}
	}

	// Key buffer read hit rate
	dbMetric.KeyBufferHitRate = float64(dbMetric.KeyReads) / float64(dbMetric.KeyReadRequests)
	return nil
}

// calculateRealTimeQPS to calculate realtime QPS
func (m *MySql) calculateRealTimeQPS(instanceName string, currentMetric *haprobe.DatabaseMetric) {
	if instanceName == "" {
		logger.Error("real time qps: instance name is empty")
		return
	}

	if currentMetric == nil {
		logger.Error("real time qps: current metric is nil for instance: %s", instanceName)
		return
	}

	m.historyMutex.Lock()
	defer m.historyMutex.Unlock()

	// get history metric
	previousMetric, exists := m.historyMetrics[instanceName]
	if !exists {
		// fisrt time to collect, not to calculate
		m.historyMetrics[instanceName] = currentMetric
		return
	}

	// calculate difference between current and previous metric
	queryDiff := currentMetric.QueryTotal - previousMetric.QueryTotal
	if queryDiff > 0 {
		interval := float64(m.config.reportInterval)
		realTimeQPS := float64(queryDiff) / interval
		currentMetric.QPS = uint(realTimeQPS)
	}

	// Realtime TPS
	commitDiff := currentMetric.QueryCommits - previousMetric.QueryCommits
	rollbackDiff := currentMetric.QueryRollbacks - previousMetric.QueryRollbacks
	totalDiff := commitDiff + rollbackDiff
	if totalDiff > 0 {
		interval := float64(m.config.reportInterval)
		realTimeTPS := float64(totalDiff) / interval
		currentMetric.TPS = uint(realTimeTPS)
	}

	m.historyMetrics[instanceName] = currentMetric
}

// Connection status
func getConnectionStatus(globalStatus map[string]string, dbMetric *haprobe.DatabaseMetric) {
	transferToInt(globalStatus, "Threads_running", &dbMetric.ThreadsRunning)
	transferToInt(globalStatus, "Aborted_connects", &dbMetric.ConnectionsAborted)
	transferToInt(globalStatus, "Connections", &dbMetric.Connections)
	transferToInt(globalStatus, "Connection_errors_accept", &dbMetric.ConnectionsErrorsAccept)
	transferToInt(globalStatus, "Connection_errors_internal", &dbMetric.ConnectionsErrorsInternal)
	transferToInt(globalStatus, "Connection_errors_peer_address", &dbMetric.ConnectionsErrorsPeerAddr)
}

// Query status
func getQueryStatus(globalStatus map[string]string, dbMetric *haprobe.DatabaseMetric) {
	transferToUint64(globalStatus, "Queries", &dbMetric.QueryTotal)
	transferToUint64(globalStatus, "Questions", &dbMetric.QueryQuestions)
	transferToUint64(globalStatus, "Com_select", &dbMetric.QuerySelects)
	transferToUint64(globalStatus, "Com_insert", &dbMetric.QueryInserts)
	transferToUint64(globalStatus, "Com_update", &dbMetric.QueryUpdates)
	transferToUint64(globalStatus, "Com_delete", &dbMetric.QueryDeletes)
	transferToUint64(globalStatus, "Slow_queries", &dbMetric.QuerySlow)
}

// Query cache
func getQueryCache(globalStatus map[string]string, dbMetric *haprobe.DatabaseMetric) {
	transferToUint64(globalStatus, "Key_read_requests", &dbMetric.KeyReadRequests)
	transferToUint64(globalStatus, "Key_reads", &dbMetric.KeyReads)
	transferToUint64(globalStatus, "Qcache_hits", &dbMetric.QCacheHits)
	transferToUint64(globalStatus, "Qcache_inserts", &dbMetric.QCacheInserts)
	transferToUint64(globalStatus, "Qcache_lowmen_prunes", &dbMetric.QCachePrunes)
	transferToUint64(globalStatus, "Qcache_not_cached", &dbMetric.QCacheNotCached)
	transferToUint64(globalStatus, "Qcache_total_blocks", &dbMetric.QCacheTotalBlocks)
	transferToUint64(globalStatus, "Qcache_free_blocks", &dbMetric.QCacheFreeBlocks)
	transferToUint64(globalStatus, "Qcache_free_mem", &dbMetric.QCacheFreeMem)
}

// Table Status
func getTableStatus(globalStatus map[string]string, dbMetric *haprobe.DatabaseMetric) {
	transferToUint64(globalStatus, "Created_tmp_disk_tables", &dbMetric.TableCreatedTmpDisk)
	transferToUint64(globalStatus, "Created_tmp_tables", &dbMetric.TableCreatedTmp)
	transferToUint64(globalStatus, "Opened_tables", &dbMetric.TableOpen)
	transferToUint64(globalStatus, "Opened_files", &dbMetric.FileOpen)
	transferToUint(globalStatus, "Flush_commands", &dbMetric.TableFlush)
}

// BinLog
func getBinlog(globalStatus map[string]string, dbMetric *haprobe.DatabaseMetric) {
	transferToUint64(globalStatus, "Binlog_cache_disk_use", &dbMetric.BinlogCacheDiskUse)
	transferToUint64(globalStatus, "Binlog_cache_use", &dbMetric.BinlogCacheUse)
	transferToUint64(globalStatus, "Binlog_stmt_cache_disk_use", &dbMetric.BinlogStmtCacheDiskUse)
	transferToUint64(globalStatus, "Binlog_stmt_cache_use", &dbMetric.BinlogStmtCacheUse)
}

// performance Schema
func getPerformanceSchema(globalStatus map[string]string, dbMetric *haprobe.DatabaseMetric) {
	transferToUint64(globalStatus, "Performance_schema_accounts_lost", &dbMetric.SchemaAccountsLost)
	transferToUint64(globalStatus, "Performance_schema_cond_classes_lost", &dbMetric.SchemaCondClassesLost)
	transferToUint64(globalStatus, "Performance_schema_file_handles_lost", &dbMetric.SchemaFileHandlesLost)
	transferToUint64(globalStatus, "Performance_schema_locker_lost", &dbMetric.SchemaLockerLost)
	transferToUint64(globalStatus, "Performance_schema_digest_lost", &dbMetric.SchemaDigestLost)
	transferToUint64(globalStatus, "Performance_schema_rwlock_instances_lost", &dbMetric.SchemaRwlockInstancesLost)
	transferToUint64(globalStatus, "Performance_schema_thread_instances_lost", &dbMetric.SchemaThreadInstancesLost)
	transferToUint64(globalStatus, "Performance_schema_table_lock_stat_lost", &dbMetric.SchemaTableLockStatLost)
}

// Others
func getOtherMetrics(globalStatus map[string]string, dbMetric *haprobe.DatabaseMetric) {
	// character_set_server
	if val, ok := globalStatus["character_set_server"]; ok {
		dbMetric.ServerCharset = val
	}
	// Threads_connected
	transferToUint64(globalStatus, "Com_commit", &dbMetric.QueryCommits)
	transferToUint64(globalStatus, "Com_rollback", &dbMetric.QueryRollbacks)

	// AvgQPS/AvgTPS
	if val, err := strconv.ParseUint(globalStatus["Uptime"], 10, 64); err == nil {
		dbMetric.AvgQPS = uint(dbMetric.QueryTotal / val)
		dbMetric.AvgTPS = uint((dbMetric.QueryCommits + dbMetric.QueryRollbacks) / val)
	}

}

// map[string]string -> int
func transferToInt(m map[string]string, key string, target *int) {
	if val, ok := m[key]; ok {
		intVal, err := strconv.Atoi(val)
		if err == nil {
			*target = intVal
		}
	}
}

// map -> uint64
func transferToUint64(m map[string]string, key string, target *uint64) {
	if val, ok := m[key]; ok {
		uint64Val, err := strconv.ParseUint(val, 10, 64)
		if err == nil {
			*target = uint64Val
		}
	}
}

// map[string]string -> uint
func transferToUint(m map[string]string, key string, target *uint) {
	if val, ok := m[key]; ok {
		if u, err := strconv.ParseUint(val, 10, 32); err == nil {
			*target = uint(u)
		}
	}
}
