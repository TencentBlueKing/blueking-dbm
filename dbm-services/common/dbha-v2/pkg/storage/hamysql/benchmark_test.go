//go:build integration

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

package hamysql_test

import (
	"fmt"
	"log"
	"os"
	"strconv"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"dbm-services/common/dbha-v2/pkg/storage/hamysql"
)

var (
	testGormDB *hamysql.GormDB
	testSqlxDB *hamysql.SqlxDB
)

func TestMain(m *testing.M) {
	setup()
	code := m.Run()
	teardown()
	os.Exit(code)
}

func setup() {
	host := os.Getenv("DBHA_MYSQL_HOST")
	portStr := os.Getenv("DBHA_MYSQL_PORT")
	user := os.Getenv("DBHA_MYSQL_USER")
	password := os.Getenv("DBHA_MYSQL_PASSWORD")
	dbName := os.Getenv("DBHA_MYSQL_DBNAME")

	if host == "" || portStr == "" || user == "" {
		log.Println("MySQL environment variables not set, skipping integration tests")
		log.Println("Required: DBHA_MYSQL_HOST, DBHA_MYSQL_PORT, DBHA_MYSQL_USER, DBHA_MYSQL_PASSWORD, DBHA_MYSQL_DBNAME")
		os.Exit(0)
	}

	port, err := strconv.Atoi(portStr)
	if err != nil {
		log.Fatalf("invalid port: %s, errmsg: %v", portStr, err)
	}

	// Create GormDB
	testGormDB, err = hamysql.NewGormDB(
		hamysql.OptionProto("tcp"),
		hamysql.OptionIP(host),
		hamysql.OptionPort(port),
		hamysql.OptionUser(user),
		hamysql.OptionPassword(password),
		hamysql.OptionDBName(dbName),
	)
	if err != nil {
		log.Fatalf("failed to create GormDB, errmsg: %v", err)
	}

	// Create SqlxDB
	testSqlxDB, err = hamysql.NewSqlxDB(
		hamysql.OptionProto("tcp"),
		hamysql.OptionIP(host),
		hamysql.OptionPort(port),
		hamysql.OptionUser(user),
		hamysql.OptionPassword(password),
		hamysql.OptionDBName(dbName),
	)
	if err != nil {
		log.Fatalf("failed to create SqlxDB, errmsg: %v", err)
	}

	log.Printf("Connected to MySQL: %s:%d/%s", host, port, dbName)
}

func teardown() {
	if testGormDB != nil {
		testGormDB.Close()
	}
	if testSqlxDB != nil {
		testSqlxDB.Close()
	}
}

// ============================================================================
// Read/Write QPS tests
// ============================================================================

// TestGormReadQPS tests Gorm read QPS
func TestGormReadQPS(t *testing.T) {
	if testGormDB == nil {
		t.Skip("GormDB not initialized")
	}

	concurrencyLevels := []int{1, 10, 50, 100}
	duration := 5 * time.Second

	for _, c := range concurrencyLevels {
		var ops int64
		var errors int64
		start := time.Now()
		done := make(chan struct{})

		var wg sync.WaitGroup
		for i := 0; i < c; i++ {
			wg.Add(1)
			go func() {
				defer wg.Done()
				for {
					select {
					case <-done:
						return
					default:
						var result int
						err := testGormDB.DB().Raw("SELECT 1").Scan(&result).Error
						if err != nil {
							atomic.AddInt64(&errors, 1)
						} else {
							atomic.AddInt64(&ops, 1)
						}
					}
				}
			}()
		}

		time.Sleep(duration)
		close(done)
		wg.Wait()

		elapsed := time.Since(start)
		qps := float64(ops) / elapsed.Seconds()
		t.Logf("Gorm Read QPS: concurrency=%d, ops=%d, errors=%d, duration=%v, QPS=%.2f",
			c, ops, errors, elapsed, qps)
	}
}

// TestSqlxReadQPS tests Sqlx read QPS
func TestSqlxReadQPS(t *testing.T) {
	if testSqlxDB == nil {
		t.Skip("SqlxDB not initialized")
	}

	concurrencyLevels := []int{1, 10, 50, 100}
	duration := 5 * time.Second

	for _, c := range concurrencyLevels {
		var ops int64
		var errors int64
		start := time.Now()
		done := make(chan struct{})

		var wg sync.WaitGroup
		for i := 0; i < c; i++ {
			wg.Add(1)
			go func() {
				defer wg.Done()
				for {
					select {
					case <-done:
						return
					default:
						var result int
						err := testSqlxDB.DB().Get(&result, "SELECT 1")
						if err != nil {
							atomic.AddInt64(&errors, 1)
						} else {
							atomic.AddInt64(&ops, 1)
						}
					}
				}
			}()
		}

		time.Sleep(duration)
		close(done)
		wg.Wait()

		elapsed := time.Since(start)
		qps := float64(ops) / elapsed.Seconds()
		t.Logf("Sqlx Read QPS: concurrency=%d, ops=%d, errors=%d, duration=%v, QPS=%.2f",
			c, ops, errors, elapsed, qps)
	}
}

// TestConnectionPoolPerformance tests connection pool performance
func TestConnectionPoolPerformance(t *testing.T) {
	if testGormDB == nil {
		t.Skip("GormDB not initialized")
	}

	sqlDB, err := testGormDB.DB().DB()
	if err != nil {
		t.Fatalf("failed to get sql.DB, errmsg: %v", err)
	}

	// Test different connection pool configurations
	poolConfigs := []struct {
		maxOpen int
		maxIdle int
	}{
		{10, 5},
		{50, 25},
		{100, 50},
	}

	concurrency := 100
	duration := 5 * time.Second

	for _, cfg := range poolConfigs {
		sqlDB.SetMaxOpenConns(cfg.maxOpen)
		sqlDB.SetMaxIdleConns(cfg.maxIdle)

		var ops int64
		var errors int64
		start := time.Now()
		done := make(chan struct{})

		var wg sync.WaitGroup
		for i := 0; i < concurrency; i++ {
			wg.Add(1)
			go func() {
				defer wg.Done()
				for {
					select {
					case <-done:
						return
					default:
						var result int
						err := testGormDB.DB().Raw("SELECT 1").Scan(&result).Error
						if err != nil {
							atomic.AddInt64(&errors, 1)
						} else {
							atomic.AddInt64(&ops, 1)
						}
					}
				}
			}()
		}

		time.Sleep(duration)
		close(done)
		wg.Wait()

		elapsed := time.Since(start)
		qps := float64(ops) / elapsed.Seconds()
		stats := sqlDB.Stats()

		t.Logf("Connection Pool: maxOpen=%d, maxIdle=%d", cfg.maxOpen, cfg.maxIdle)
		t.Logf("  QPS=%.2f, ops=%d, errors=%d", qps, ops, errors)
		t.Logf("  Pool Stats: InUse=%d, Idle=%d, WaitCount=%d, WaitDuration=%v",
			stats.InUse, stats.Idle, stats.WaitCount, stats.WaitDuration)
	}
}

// ============================================================================
// MySQL reconnection tests
// ============================================================================

// TestMySQLReconnectAfterRestart tests MySQL auto-reconnection after restart
// Usage:
//  1. Run test: go test -tags=integration -run TestMySQLReconnectAfterRestart -v
//  2. During test execution (within 60 seconds), manually restart MySQL service
//  3. Observe test output to confirm reconnection success
func TestMySQLReconnectAfterRestart(t *testing.T) {
	if testGormDB == nil {
		t.Skip("GormDB not initialized")
	}

	t.Log("========================================")
	t.Log("MySQL Reconnect Test Started")
	t.Log("Please restart MySQL within 60 seconds to test reconnection")
	t.Log("========================================")

	var successCount, errorCount int64
	ticker := time.NewTicker(2 * time.Second)
	defer ticker.Stop()

	testDuration := 60 * time.Second
	endTime := time.Now().Add(testDuration)

	for time.Now().Before(endTime) {
		select {
		case <-ticker.C:
			var result int
			err := testGormDB.DB().Raw("SELECT 1").Scan(&result).Error
			if err != nil {
				atomic.AddInt64(&errorCount, 1)
				t.Logf("[%s] Query failed, errmsg: %v", time.Now().Format("15:04:05"), err)
			} else {
				atomic.AddInt64(&successCount, 1)
				t.Logf("[%s] Query success", time.Now().Format("15:04:05"))
			}
		}
	}

	t.Log("========================================")
	t.Logf("MySQL Reconnect Test Completed")
	t.Logf("Success: %d, Errors: %d", successCount, errorCount)
	t.Log("========================================")

	// If errors followed by successes, reconnection is working
	if errorCount > 0 && successCount > errorCount {
		t.Log("Reconnection appears to be working (errors followed by successes)")
	} else if errorCount > 0 && successCount == 0 {
		t.Errorf("All operations failed, reconnection may not be working")
	}
}

// TestSqlxReconnectAfterRestart tests Sqlx MySQL auto-reconnection after restart
func TestSqlxReconnectAfterRestart(t *testing.T) {
	if testSqlxDB == nil {
		t.Skip("SqlxDB not initialized")
	}

	t.Log("========================================")
	t.Log("Sqlx MySQL Reconnect Test Started")
	t.Log("Please restart MySQL within 60 seconds to test reconnection")
	t.Log("========================================")

	var successCount, errorCount int64
	ticker := time.NewTicker(2 * time.Second)
	defer ticker.Stop()

	testDuration := 60 * time.Second
	endTime := time.Now().Add(testDuration)

	for time.Now().Before(endTime) {
		select {
		case <-ticker.C:
			var result int
			err := testSqlxDB.DB().Get(&result, "SELECT 1")
			if err != nil {
				atomic.AddInt64(&errorCount, 1)
				t.Logf("[%s] Query failed, errmsg: %v", time.Now().Format("15:04:05"), err)
			} else {
				atomic.AddInt64(&successCount, 1)
				t.Logf("[%s] Query success", time.Now().Format("15:04:05"))
			}
		}
	}

	t.Log("========================================")
	t.Logf("Sqlx MySQL Reconnect Test Completed")
	t.Logf("Success: %d, Errors: %d", successCount, errorCount)
	t.Log("========================================")
}

// TestConcurrentOperationsDuringMySQLRestart tests concurrent operations during MySQL restart
func TestConcurrentOperationsDuringMySQLRestart(t *testing.T) {
	if testGormDB == nil {
		t.Skip("GormDB not initialized")
	}

	t.Log("========================================")
	t.Log("Concurrent Operations During MySQL Restart Test Started")
	t.Log("Please restart MySQL within 60 seconds")
	t.Log("========================================")

	var successCount, errorCount int64
	done := make(chan struct{})
	concurrency := 10

	var wg sync.WaitGroup
	for i := 0; i < concurrency; i++ {
		wg.Add(1)
		go func(workerID int) {
			defer wg.Done()
			for {
				select {
				case <-done:
					return
				default:
					var result int
					err := testGormDB.DB().Raw("SELECT 1").Scan(&result).Error
					if err != nil {
						atomic.AddInt64(&errorCount, 1)
					} else {
						atomic.AddInt64(&successCount, 1)
					}
					time.Sleep(100 * time.Millisecond)
				}
			}
		}(i)
	}

	// Periodically output status
	ticker := time.NewTicker(5 * time.Second)
	defer ticker.Stop()

	testDuration := 60 * time.Second
	endTime := time.Now().Add(testDuration)

	for time.Now().Before(endTime) {
		select {
		case <-ticker.C:
			t.Logf("[%s] Success: %d, Errors: %d",
				time.Now().Format("15:04:05"),
				atomic.LoadInt64(&successCount), atomic.LoadInt64(&errorCount))
		default:
			time.Sleep(1 * time.Second)
		}
	}

	close(done)
	wg.Wait()

	t.Log("========================================")
	t.Logf("Concurrent Operations Test Completed")
	t.Logf("Success: %d, Errors: %d", successCount, errorCount)
	t.Log("========================================")
}

// TestConnectionRecoveryTime tests connection recovery time
func TestConnectionRecoveryTime(t *testing.T) {
	if testGormDB == nil {
		t.Skip("GormDB not initialized")
	}

	t.Log("========================================")
	t.Log("Connection Recovery Time Test")
	t.Log("Please restart MySQL when prompted")
	t.Log("========================================")

	// First confirm connection is OK
	var result int
	err := testGormDB.DB().Raw("SELECT 1").Scan(&result).Error
	if err != nil {
		t.Fatalf("Initial connection failed, errmsg: %v", err)
	}
	t.Log("Initial connection OK")

	t.Log(">>> Please restart MySQL NOW <<<")
	t.Log("Waiting for connection to fail...")

	// Wait for connection to fail
	var failTime time.Time
	for i := 0; i < 60; i++ {
		err := testGormDB.DB().Raw("SELECT 1").Scan(&result).Error
		if err != nil {
			failTime = time.Now()
			t.Logf("[%s] Connection failed: %v", failTime.Format("15:04:05"), err)
			break
		}
		time.Sleep(1 * time.Second)
	}

	if failTime.IsZero() {
		t.Log("Connection never failed, MySQL may not have been restarted")
		return
	}

	t.Log("Waiting for connection to recover...")

	// Wait for connection to recover
	var recoverTime time.Time
	for i := 0; i < 120; i++ {
		err := testGormDB.DB().Raw("SELECT 1").Scan(&result).Error
		if err == nil {
			recoverTime = time.Now()
			t.Logf("[%s] Connection recovered!", recoverTime.Format("15:04:05"))
			break
		}
		time.Sleep(500 * time.Millisecond)
	}

	if recoverTime.IsZero() {
		t.Errorf("Connection never recovered within 60 seconds")
		return
	}

	recoveryDuration := recoverTime.Sub(failTime)
	t.Log("========================================")
	t.Logf("Connection Recovery Time: %v", recoveryDuration)
	t.Log("========================================")
}

// ============================================================================
// Stress tests
// ============================================================================

// TestHighConcurrencyStress high concurrency stress test
func TestHighConcurrencyStress(t *testing.T) {
	if testGormDB == nil {
		t.Skip("GormDB not initialized")
	}

	concurrency := 200
	duration := 30 * time.Second

	var ops int64
	var errors int64
	var maxLatency int64
	start := time.Now()
	done := make(chan struct{})

	var wg sync.WaitGroup
	for i := 0; i < concurrency; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for {
				select {
				case <-done:
					return
				default:
					opStart := time.Now()
					var result int
					err := testGormDB.DB().Raw("SELECT 1").Scan(&result).Error
					latency := time.Since(opStart).Microseconds()

					if err != nil {
						atomic.AddInt64(&errors, 1)
					} else {
						atomic.AddInt64(&ops, 1)
						// Update max latency
						for {
							old := atomic.LoadInt64(&maxLatency)
							if latency <= old || atomic.CompareAndSwapInt64(&maxLatency, old, latency) {
								break
							}
						}
					}
				}
			}
		}()
	}

	// Periodically output status
	ticker := time.NewTicker(5 * time.Second)
	go func() {
		for {
			select {
			case <-done:
				return
			case <-ticker.C:
				currentOps := atomic.LoadInt64(&ops)
				currentErrors := atomic.LoadInt64(&errors)
				elapsed := time.Since(start).Seconds()
				qps := float64(currentOps) / elapsed
				t.Logf("[%s] QPS=%.2f, ops=%d, errors=%d, max_latency=%dμs",
					time.Now().Format("15:04:05"), qps, currentOps, currentErrors, atomic.LoadInt64(&maxLatency))
			}
		}
	}()

	time.Sleep(duration)
	close(done)
	ticker.Stop()
	wg.Wait()

	elapsed := time.Since(start)
	qps := float64(ops) / elapsed.Seconds()

	t.Log("========================================")
	t.Logf("High Concurrency Stress Test Completed")
	t.Logf("Concurrency: %d", concurrency)
	t.Logf("Duration: %v", elapsed)
	t.Logf("Total Ops: %d", ops)
	t.Logf("Total Errors: %d", errors)
	t.Logf("QPS: %.2f", qps)
	t.Logf("Max Latency: %dμs (%.2fms)", maxLatency, float64(maxLatency)/1000)
	t.Log("========================================")
}

// TestLongRunningConnections long running connections stability test
func TestLongRunningConnections(t *testing.T) {
	if testGormDB == nil {
		t.Skip("GormDB not initialized")
	}

	t.Log("========================================")
	t.Log("Long Running Connections Test (5 minutes)")
	t.Log("========================================")

	duration := 5 * time.Minute
	interval := 10 * time.Second

	var successCount, errorCount int64
	var consecutiveErrors int64

	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	endTime := time.Now().Add(duration)

	for time.Now().Before(endTime) {
		select {
		case <-ticker.C:
			var result int
			err := testGormDB.DB().Raw("SELECT 1").Scan(&result).Error
			if err != nil {
				atomic.AddInt64(&errorCount, 1)
				atomic.AddInt64(&consecutiveErrors, 1)
				t.Logf("[%s] Query failed (consecutive: %d), errmsg: %v",
					time.Now().Format("15:04:05"), consecutiveErrors, err)

				if consecutiveErrors >= 5 {
					t.Errorf("Too many consecutive errors: %d", consecutiveErrors)
					return
				}
			} else {
				atomic.AddInt64(&successCount, 1)
				atomic.StoreInt64(&consecutiveErrors, 0)
				t.Logf("[%s] Query success (total: %d)",
					time.Now().Format("15:04:05"), successCount)
			}
		}
	}

	t.Log("========================================")
	t.Logf("Long Running Test Completed")
	t.Logf("Success: %d, Errors: %d", successCount, errorCount)
	t.Logf("Error Rate: %.2f%%", float64(errorCount)/float64(successCount+errorCount)*100)
	t.Log("========================================")
}

// TestTransactionUnderLoad transaction under load test
func TestTransactionUnderLoad(t *testing.T) {
	if testGormDB == nil {
		t.Skip("GormDB not initialized")
	}

	// Create test table
	err := testGormDB.DB().Exec(`
		CREATE TABLE IF NOT EXISTS benchmark_test (
			id INT AUTO_INCREMENT PRIMARY KEY,
			value VARCHAR(255),
			created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
		)
	`).Error
	if err != nil {
		t.Fatalf("failed to create test table, errmsg: %v", err)
	}
	defer testGormDB.DB().Exec("DROP TABLE IF EXISTS benchmark_test")

	concurrency := 50
	duration := 10 * time.Second

	var txSuccess, txError int64
	done := make(chan struct{})

	var wg sync.WaitGroup
	for i := 0; i < concurrency; i++ {
		wg.Add(1)
		go func(workerID int) {
			defer wg.Done()
			counter := 0
			for {
				select {
				case <-done:
					return
				default:
					tx := testGormDB.DB().Begin()
					if tx.Error != nil {
						atomic.AddInt64(&txError, 1)
						continue
					}

					// Insert
					err := tx.Exec("INSERT INTO benchmark_test (value) VALUES (?)",
						fmt.Sprintf("worker-%d-val-%d", workerID, counter)).Error
					if err != nil {
						tx.Rollback()
						atomic.AddInt64(&txError, 1)
						continue
					}

					// Query
					var count int64
					err = tx.Raw("SELECT COUNT(*) FROM benchmark_test").Scan(&count).Error
					if err != nil {
						tx.Rollback()
						atomic.AddInt64(&txError, 1)
						continue
					}

					// Commit
					if err := tx.Commit().Error; err != nil {
						atomic.AddInt64(&txError, 1)
					} else {
						atomic.AddInt64(&txSuccess, 1)
					}
					counter++
				}
			}
		}(i)
	}

	time.Sleep(duration)
	close(done)
	wg.Wait()

	t.Log("========================================")
	t.Logf("Transaction Under Load Test Completed")
	t.Logf("Successful Transactions: %d", txSuccess)
	t.Logf("Failed Transactions: %d", txError)
	t.Logf("TPS: %.2f", float64(txSuccess)/duration.Seconds())
	t.Log("========================================")
}
