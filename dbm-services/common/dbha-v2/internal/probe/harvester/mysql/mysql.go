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
	"dbm-services/common/dbha-v2/internal/probe/harvester/plugin"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/proto/models"
	"encoding/json"
	"fmt"
	"net"
	"os"
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

// MySql basic structure
type MySql struct {
	// NOTE: Must include UnimplementedMethod
	plugin.UnimplementedMethod
	config  mySqlOptions // mySqlOptions includes multiple instance
	results chan *plugin.HarvestData
}

// StatusVar return all STATUS metrics
type StatusVar struct {
	Variable string `gorm:"column:Variable_name"`
	Value    string `gorm:"column:Value"`
}

// SessionInfo means single status to connect to database
type SessionInfo struct {
	ThreadID    string
	CurrentDB   string
	CurrentUser string
}

// GlobalStatus get all GLOBAL STATUS metrics
type GlobalStatus struct {
	Variable string `gorm:"column:Variable_name"`
	Value    string `gorm:"column:Value"`
}

// NewMySql create MySql instance with multiple opts
func NewMySql(opts ...Option) *MySql {
	mySqlOpts := defaultMySqlOptions

	for _, opt := range opts {
		opt.apply(&mySqlOpts)
	}

	return &MySql{
		config:  mySqlOpts,
		results: make(chan *plugin.HarvestData, 10),
	}
}

// Name return MySQL instance Name
func (m *MySql) Name() (string, error) {
	return Name, nil
}

// Version return MySQL version
func (m *MySql) Version() (string, error) {
	return Version, nil
}

// Harvest collects metrics from both the host machine and databases.
func (m *MySql) Harvest(ctx context.Context) (chan *plugin.HarvestData, error) {

	logger.Info("start the metrics collector, interval time is: %s\n", m.config.reportInterval)
	logger.Info("output file is: %s\n", m.config.outputFile)

	ticker := time.NewTicker(time.Duration(m.config.reportInterval) * time.Second)
	defer ticker.Stop()

	logger.Info(" probe start first data collection")

	for {
		select {
		case <-ticker.C:
			metrics, err := m.collectAndSaveMetrics(m.config)
			if err != nil {
				logger.Info(" failed to initialization mysql probe %s:%d. errmsg: %v", m.config.host, m.config.port, err)
				// Implement retry logic
			}
			m.results <- &plugin.HarvestData{
				Data: metrics,
			}
		case <-ctx.Done():
			logger.Info(" stop probe")
		}
	}

	return nil, nil
}

// Close MySQL harverser
func (m *MySql) Close() error {
	return nil
}

// collectAndSaveMetrics collect system&database metrics and collection
func (m *MySql) collectAndSaveMetrics(config mySqlOptions) (models.AllMetrics, error) {
	// collect system metrics
	systemMetrics, err := collectSystemMetrics()
	if err != nil {
		logger.Error(" failed to collect system metrics. errmsg: %s\n", err)
	}

	// collect multiple mysql instance metrics
	databaseMetrics := make(map[string]models.DatabaseMetrics)
	var wg sync.WaitGroup
	var mutex sync.Mutex

	if m.config.host != "" {
		wg.Add(1)
		go func() {
			defer wg.Done()
			instanceName := m.config.host
			if instanceName == "" {
				instanceName = fmt.Sprintf("%s:%d", m.config.host, m.config.host)
			}
			dbMetrics, err := collectMySQLMetrics(&m.config)
			if err != nil {
				//
				logger.Error(" failed to collect mysql instance %s. errmsg: %s \n", m.config.instanceName, err)
				// implement retry logic
				return
			}

			mutex.Lock()
			databaseMetrics[instanceName] = dbMetrics
			mutex.Unlock()
		}()
	}

	// wait for all probe goroutines to complete
	wg.Wait()

	// combine all metrics
	allMetrics := models.AllMetrics{
		Timestamp: time.Now().Unix(),
		System:    systemMetrics,
		Databases: databaseMetrics,
	}

	// metrics transfer to json
	jsonData, err := json.MarshalIndent(allMetrics, "", "  ")
	if err != nil {
		logger.Error(" failed to transfer to json. errmsg: %s\n", err)
	}

	// save json to output_file
	err = os.WriteFile(config.outputFile, jsonData, 0644)
	if err != nil {
		logger.Error(" failed to save file. errmsg: %s\n", err)
	}

	logger.Info("[%s] metrics sussessfully save to %s \n", time.Now().Format("2006-01-02 15:04:05"), m.config.outputFile)
	return allMetrics, nil
}

// collectSystemMetrics collect System Metrics
func collectSystemMetrics() (models.SystemMetrics, error) {
	metrics := models.SystemMetrics{}

	// CPU
	cpuPercents, err := cpu.Percent(time.Second, false)
	if err != nil {
		return metrics, err
	}

	cpuTimes, err := cpu.Times(false)
	if err == nil && len(cpuTimes) > 0 {
		metrics.CPUUserPercent = cpuTimes[0].User / (cpuTimes[0].Total()) * 100
		metrics.CPUSystemPercent = cpuTimes[0].System / (cpuTimes[0].Total()) * 100
		metrics.CPUIOWaitPercent = cpuTimes[0].Iowait / (cpuTimes[0].Total()) * 100
	}

	if len(cpuPercents) > 0 {
		metrics.CPUUsagePercent = cpuPercents[0]
	}

	// CPU load 1 5 15
	loadInfo, err := load.Avg()
	if err == nil {
		metrics.CPULoad1 = loadInfo.Load1
		metrics.CPULoad5 = loadInfo.Load5
		metrics.CPULoad15 = loadInfo.Load15
	}

	// Memory
	// consider tansfer function
	memInfo, err := mem.VirtualMemory()
	if err == nil {
		metrics.MemTotalMB = memInfo.Total / 1024 / 1024
		metrics.MemUsedMB = memInfo.Used / 1024 / 1024
		metrics.MemFreeMB = memInfo.Free / 1024 / 1024
		metrics.MemCacheMB = memInfo.Cached / 1024 / 1024
		metrics.MemAvailableMB = memInfo.Available / 1024 / 1024
	}

	// Swap
	swapInfo, err := mem.SwapMemory()
	if err == nil {
		metrics.SwapTotalMB = swapInfo.Total / 1024 / 1024
		metrics.SwapUsedMB = swapInfo.Used / 1024 / 1024
	}

	// Disk
	partitions, err := disk.Partitions(false)
	if err != nil {
		logger.Error(" failed to get partitions info. errmsg: %v\n", err)
	}

	// Collect disk usage
	for _, partition := range partitions {
		usageStat, err := disk.Usage(partition.Mountpoint)
		if err != nil {
			fmt.Printf(" failed to get %s info: %v\n", partition.Mountpoint, err)
			continue
		}
		metrics.DiskTotal += usageStat.Total / 1024 / 1024 / 1024
		metrics.DiskUsed += usageStat.Used / 1024 / 1024 / 1024
		metrics.DiskAvailable += usageStat.Free / 1024 / 1024 / 1024
		metrics.DiskUsagePercent += usageStat.UsedPercent / 2

		for _, opt := range partition.Opts {
			if opt == "ro" {
				metrics.DiskReadOnly = true
			}
		}
	}

	// Network

	// IP Address
	// consider tansfer function
	ipAddress := ""
	ifaces, err := net.Interfaces()
	if err == nil {
		for _, iface := range ifaces {
			// skip loopback and inactive interfaces
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
	metrics.NetIpAddress = ipAddress

	// Network usage
	networkUsage := ""
	netIOs, err := gopsutilnet.IOCounters(true)
	if err == nil {
		for _, io := range netIOs {
			networkUsage += fmt.Sprintf("%s rx=%dB, tx=%dB; ", io.Name, io.BytesRecv, io.BytesSent)
			metrics.NetBytesIn += io.BytesRecv
			metrics.NetBytesOut += io.BytesSent
		}
	}
	metrics.NetUsage = networkUsage

	// TCP connections
	connections, err := gopsutilnet.Connections("tcp")
	if err == nil {
		metrics.NetTCPConnections = len(connections)
	}

	// get Packet Loss
	metrics.NetPacketLossIn, metrics.NetPacketLossOut = getPacketLoss()

	return metrics, nil
}

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

// collect MySQL metrics
func collectMySQLMetrics(config *mySqlOptions) (models.DatabaseMetrics, error) {
	dbMetrics := models.DatabaseMetrics{}

	// MySQL DSN
	dsn := fmt.Sprintf("%s:%s@tcp(%s:%d)/%s?charset=utf8mb4&parseTime=True&loc=Local",
		config.user,
		config.password,
		config.host,
		config.port)

	// Connect to Database
	db, err := gorm.Open(mysql.Open(dsn))
	if err != nil {
		fmt.Println(" failed to connect to database. errmsg: %v\n", err)
		return dbMetrics, err
	}
	fmt.Println(" successfully connected to database.")
	_, err = db.DB()
	if err != nil {
		return dbMetrics, err
	}

	// get mysql basic status
	if err := collectMySQLStatus(db, &dbMetrics); err != nil {
		return dbMetrics, err
	}

	// get mysql performance
	if err := collectMySQLPerformance(db, &dbMetrics); err != nil {
		return dbMetrics, err
	}

	return dbMetrics, nil
}

// Collect MySQL STATUS metrics
func collectMySQLStatus(db *gorm.DB, status *models.DatabaseMetrics) error {

	err := db.Raw("SELECT VERSION() as version").Scan(&status.Version).Error
	if err != nil {
		return err
	}

	var info SessionInfo
	// NOCC:tosa/linelength(设计如此)
	err = db.Raw("SELECT CONNECTION_ID() as ThreadID, DATABASE() as CurrentDB, CURRENT_USER() as CurrentUser").Scan(&info).Error
	if err != nil {
		return err
	}

	status.ThreadID = info.ThreadID
	status.CurrentDatabase = info.CurrentDB
	status.CurrentUser = info.CurrentUser

	var statusVars []StatusVar
	// NOCC:tosa/linelength(设计如此)
	err = db.Raw("SHOW STATUS WHERE Variable_name IN ('Threads_connected', 'Open_tables', 'Slow_queries', 'Questions', 'Uptime')").Scan(&statusVars).Error
	if err != nil {
		return err
	}

	// status transfer to map
	statusMap := make(map[string]string)
	for _, v := range statusVars {
		statusMap[v.Variable] = v.Value
	}

	if val, ok := statusMap["Threads_connected"]; ok {
		status.ThreadsConnected, err = strconv.Atoi(val)
		if err != nil {
			logger.Warn("failed to convert Threads_connected to int, value(%s)", val)
		}
	}
	if val, ok := statusMap["Open_tables"]; ok {
		status.OpenTablesNow, err = strconv.Atoi(val)
		if err != nil {
			logger.Warn("failed to convert Open_tables to int, value(%s)", val)
		}
	}
	if val, ok := statusMap["Slow_queries"]; ok {
		status.SlowQueriesNow, err = strconv.Atoi(val)
		if err != nil {
			logger.Warn("failed to convert Slow_queries to int, value(%s)", val)
		}
	}
	if val, ok := statusMap["Questions"]; ok {
		status.TotalQuestions, err = strconv.Atoi(val)
		if err != nil {
			logger.Warn("failed to convert Questions to int, value(%s)", val)
		}
	}

	if val, ok := statusMap["Uptime"]; ok {
		uptime, _ := strconv.Atoi(val)
		if uptime > 0 {
			status.QueriesPerSecond = float64(status.TotalQuestions) / float64(uptime)
		}
	}

	var variables []StatusVar
	err = db.Raw("SHOW GLOBAL VARIABLES WHERE Variable_name IN ('character_set_server')").Scan(&variables).Error
	if err != nil {
		return err
	}

	for _, v := range variables {
		if v.Variable == "character_set_server" {
			status.ServerCharset = v.Value
			break
		}
	}

	var opens, flushes int
	err = db.Raw("SHOW STATUS LIKE 'Opens'").Row().Scan(nil, &opens)
	if err == nil {
		status.OpenTablesTotal = opens
	}
	err = db.Raw("SHOW STATUS LIKE 'Flush_tables'").Row().Scan(nil, &flushes)
	if err == nil {
		status.FlushTables = flushes
	}

	return nil
}

// collectMySQLPerformance collects MySQL performance metrics.
func collectMySQLPerformance(db *gorm.DB, perf *models.DatabaseMetrics) error {

	var globalStatusList []GlobalStatus
	err := db.Raw("SHOW GLOBAL STATUS").Scan(&globalStatusList).Error
	if err != nil {
		return err
	}

	// transform to map
	globalStatus := make(map[string]string)
	for _, status := range globalStatusList {
		globalStatus[status.Variable] = status.Value
	}

	// 1. connections stats
	readIntValue(globalStatus, "Threads_running", &perf.ThreadsRunning)
	readIntValue(globalStatus, "Aborted_connects", &perf.ConnectionsAborted)
	readIntValue(globalStatus, "Connections", &perf.Connections)
	readIntValue(globalStatus, "Connection_errors_accept", &perf.ConnectionsErrorsAccept)
	readIntValue(globalStatus, "Connection_errors_internal", &perf.ConnectionsErrorsInternal)
	readIntValue(globalStatus, "Connection_errors_peer_address", &perf.ConnectionsErrorsPeerAddr)

	// 2. Query stats
	readInt64Value(globalStatus, "Queries", &perf.QueryTotal)
	readInt64Value(globalStatus, "Questions", &perf.QueryQuestions)
	readInt64Value(globalStatus, "Com_select", &perf.QuerySelects)
	readInt64Value(globalStatus, "Com_insert", &perf.QueryInserts)
	readInt64Value(globalStatus, "Com_update", &perf.QueryUpdates)
	readInt64Value(globalStatus, "Com_delete", &perf.QueryDeletes)
	readInt64Value(globalStatus, "Slow_queries", &perf.QuerySlow)

	// QPS
	var uptime int64
	if val, ok := globalStatus["Uptime"]; ok {
		// consider this poiton
		uptime, _ = strconv.ParseInt(val, 10, 64)
		if uptime > 0 {
			perf.QPS = int(perf.QueryTotal / uptime)
		}
	}

	// TPS
	var commits, rollbacks int64
	readInt64Value(globalStatus, "Com_commit", &commits)
	readInt64Value(globalStatus, "Com_rollback", &rollbacks)
	if uptime > 0 {
		perf.TPS = int((commits + rollbacks) / uptime)
	}

	// 3. Query Cache
	readInt64Value(globalStatus, "Key_read_requests", &perf.KeyReadRequests)
	readInt64Value(globalStatus, "Key_reads", &perf.KeyReads)
	readInt64Value(globalStatus, "Qcache_hits", &perf.QCacheHits)
	readInt64Value(globalStatus, "Qcache_free_blocks", &perf.QCacheFreeBlocks)
	readInt64Value(globalStatus, "Qcache_free_memory", &perf.QCacheFreeMem)
	readInt64Value(globalStatus, "Qcache_inserts", &perf.QCacheInserts)
	readInt64Value(globalStatus, "Qcache_lowmem_prunes", &perf.QCachePrunes)
	readInt64Value(globalStatus, "Qcache_not_cached", &perf.QCacheNotCached)
	readInt64Value(globalStatus, "Qcache_total_blocks", &perf.QCacheTotalBlocks)

	// Hit rate
	if perf.KeyReadRequests > 0 {
		perf.KeyBufferHitRate = (1.0 - float64(perf.KeyReads)/float64(perf.KeyReadRequests)) * 100
	}

	// 4. Handler
	readInt64Value(globalStatus, "Handler_read_key", &perf.HandlerReadKey)
	readInt64Value(globalStatus, "Handler_read_rnd_next", &perf.HandlerReadRndNext)
	readInt64Value(globalStatus, "Handler_write", &perf.HandlerWrite)
	readInt64Value(globalStatus, "Handler_prepare", &perf.HandlerPrepare)
	readInt64Value(globalStatus, "Handler_commit", &perf.HandlerCommit)
	readInt64Value(globalStatus, "Handler_external_lock", &perf.HandlerExternalLock)

	// 5. InnoDB
	readInt64Value(globalStatus, "Innodb_row_lock_time", &perf.InnoDBRowLockWaitsTime)
	readInt64Value(globalStatus, "Table_locks_waited", &perf.InnoDBTableLockWaitsNum)
	readInt64Value(globalStatus, "Innodb_row_lock_waits", &perf.InnoDBRowLockWaitsNum)
	readInt64Value(globalStatus, "Innodb_background_log_sync", &perf.InnoDBBackgroundLogSync)

	readInt64Value(globalStatus, "Innodb_log_write_requests", &perf.InnoDBLogWriteRequests)
	readInt64Value(globalStatus, "Innodb_log_writes", &perf.InnoDBLogWrites)
	readInt64Value(globalStatus, "Innodb_os_log_fsyncs", &perf.InnoDBOsLogFsyncs)

	var innodbBufferPoolReads int64
	readInt64Value(globalStatus, "Innodb_buffer_pool_reads", &innodbBufferPoolReads)

	readInt64Value(globalStatus, "Innodb_buffer_pool_pages_dirty", &perf.InnoDBBufferPoolPagesDirty)
	readInt64Value(globalStatus, "Innodb_buffer_pool_pages_flushed", &perf.InnoDBBufferPoolPagesFlushed)
	readInt64Value(globalStatus, "Innodb_buffer_pool_pages_total", &perf.InnoDBBufferPoolPagesTotal)
	readInt64Value(globalStatus, "Innodb_buffer_pool_pages_free", &perf.InnoDBBufferPoolPagesFree)
	readInt64Value(globalStatus, "Innodb_buffer_pool_pages_data", &perf.InnoDBBufferPoolPagesData)
	readInt64Value(globalStatus, "Innodb_buffer_pool_bytes_data", &perf.InnoDBBufferPoolBytesData)
	readInt64Value(globalStatus, "Innodb_buffer_pool_write_requests", &perf.InnoDBBufferPoolWriteRequests)
	readInt64Value(globalStatus, "Innodb_buffer_pool_read_requests", &perf.InnoDBBufferPoolReadRequests)
	// InnoDB Cache Hit rate
	if perf.InnoDBBufferPoolReadRequests > 0 {
		perf.InnoDBBufferPoolHitRate = (1.0 - float64(innodbBufferPoolReads)/float64(perf.InnoDBBufferPoolReadRequests)) * 100
	}

	readInt64Value(globalStatus, "Innodb_rows_read", &perf.InnoDBRowsRead)
	readInt64Value(globalStatus, "Innodb_rows_inserted", &perf.InnoDBRowsInserted)
	readInt64Value(globalStatus, "Innodb_rows_updated", &perf.InnoDBRowsUpdated)
	readInt64Value(globalStatus, "Innodb_rows_deleted", &perf.InnoDBRowsDeleted)
	readInt64Value(globalStatus, "Innodb_data_writes", &perf.InnoDBDataWrites)
	readInt64Value(globalStatus, "Innodb_dblwr_writes", &perf.InnoDBDblwrPagesWritten)

	// 6. Table stats
	readInt64Value(globalStatus, "Created_tmp_tables", &perf.TableCreatedTmp)
	readInt64Value(globalStatus, "Created_tmp_disk_tables", &perf.TableCreatedTmpDisk)
	readInt64Value(globalStatus, "Created_tmp_files", &perf.FileCreatedTmp)
	readInt64Value(globalStatus, "Opened_files", &perf.FileOpen)
	readInt64Value(globalStatus, "Opened_tables", &perf.TableOpen)

	// 7. Binlog stats
	readInt64Value(globalStatus, "Binlog_cache_disk_use", &perf.BinlogCacheDiskUse)
	readInt64Value(globalStatus, "Binlog_cache_use", &perf.BinlogCacheUse)
	readInt64Value(globalStatus, "Binlog_stmt_cache_disk_use", &perf.BinlogStmtCacheDiskUse)
	readInt64Value(globalStatus, "Binlog_stmt_cache_use", &perf.BinlogStmtCacheUse)

	// 8. Performance Schema stats
	readInt64Value(globalStatus, "Performance_schema_accounts_lost", &perf.SchemaAccountsLost)
	readInt64Value(globalStatus, "Performance_schema_cond_classes_lost", &perf.SchemaCondClassesLost)
	readInt64Value(globalStatus, "Performance_schema_file_handles_lost", &perf.SchemaFileHandlesLost)
	readInt64Value(globalStatus, "Performance_schema_locker_lost", &perf.SchemaLockerLost)
	readInt64Value(globalStatus, "Performance_schema_digest_lost", &perf.SchemaDigestLost)
	readInt64Value(globalStatus, "Performance_schema_rwlock_instances_lost", &perf.SchemaRwlockInstancesLost)
	readInt64Value(globalStatus, "Performance_schema_thread_instances_lost", &perf.SchemaThreadInstancesLost)
	readInt64Value(globalStatus, "Performance_schema_table_lock_stat_lost", &perf.SchemaTableLockStatLost)

	return nil
}

// map -> int
func readIntValue(m map[string]string, key string, target *int) {
	if val, ok := m[key]; ok {
		intVal, err := strconv.Atoi(val)
		if err == nil {
			*target = intVal
		}
	}
}

// map -> int64
func readInt64Value(m map[string]string, key string, target *int64) {
	if val, ok := m[key]; ok {
		int64Val, err := strconv.ParseInt(val, 10, 64)
		if err == nil {
			*target = int64Val
		}
	}
}
