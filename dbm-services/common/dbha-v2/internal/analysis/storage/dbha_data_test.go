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

package storage

import (
	"context"
	"fmt"
	"os"
	"strconv"
	"testing"
	"time"

	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"

	"gorm.io/driver/mysql"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

// newTestDbhaData creates a DbhaData backed by SQLite in-memory database for in-package testing.
func newTestDbhaData(t *testing.T) *DbhaData {
	t.Helper()

	gormDB, err := gorm.Open(sqlite.Open(":memory:"), &gorm.Config{})
	if err != nil {
		t.Fatalf("failed to open sqlite in-memory database: %v", err)
	}

	if err := gormDB.AutoMigrate(&hamodel.DbSwitchingStrategy{}); err != nil {
		t.Fatalf("failed to auto migrate: %v", err)
	}

	t.Cleanup(func() {
		sqlDB, _ := gormDB.DB()
		if sqlDB != nil {
			sqlDB.Close()
		}
	})

	return &DbhaData{DB: hamysql.WithGormDB(gormDB, nil)}
}

// insertStrategies inserts strategy records in batch.
func insertStrategies(t *testing.T, ha *DbhaData, strategies ...*hamodel.DbSwitchingStrategy) {
	t.Helper()
	for _, s := range strategies {
		if err := ha.DB.DB().Create(s).Error; err != nil {
			t.Fatalf("failed to insert strategy: %v", err)
		}
	}
}

// ============================================================
// ReadSwitchingStrategyWithBkBizId tests
// ============================================================

func TestReadSwitchingStrategy_OnlyReturnsEnabled(t *testing.T) {
	ha := newTestDbhaData(t)

	insertStrategies(t, ha,
		&hamodel.DbSwitchingStrategy{
			Name:             "enabled-one",
			BkBizID:          100,
			Status:           hamodel.StatusTypeEnabled,
			TriggerEventName: haprobe.DbEventNameDetectFailure,
			TriggerCount:     1,
			Priority:         1,
		},
		&hamodel.DbSwitchingStrategy{
			Name:             "disabled-one",
			BkBizID:          100,
			Status:           hamodel.StatusTypeDisabled,
			TriggerEventName: haprobe.DbEventNameDetectFailure,
			TriggerCount:     1,
			Priority:         2,
		},
		&hamodel.DbSwitchingStrategy{
			Name:             "deleted-one",
			BkBizID:          100,
			Status:           hamodel.StatusTypeDeleted,
			TriggerEventName: haprobe.DbEventNameDetectFailure,
			TriggerCount:     1,
			Priority:         3,
		},
	)

	strategies, err := ha.ReadSwitchingStrategyWithBkBizId(context.Background(), 100)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if len(strategies) != 1 {
		t.Fatalf("expected 1 strategy, got %d", len(strategies))
	}
	if strategies[0].Name != "enabled-one" {
		t.Errorf("expected 'enabled-one', got %q", strategies[0].Name)
	}
}

func TestReadSwitchingStrategy_BizAndGlobalReturned(t *testing.T) {
	ha := newTestDbhaData(t)

	insertStrategies(t, ha,
		// biz-level strategy
		&hamodel.DbSwitchingStrategy{
			Name:             "biz-strategy",
			BkBizID:          100,
			Status:           hamodel.StatusTypeEnabled,
			TriggerEventName: haprobe.DbEventNameDetectFailure,
			TriggerCount:     1,
			Priority:         1,
		},
		// global strategy
		&hamodel.DbSwitchingStrategy{
			Name:             "global-strategy",
			BkBizID:          0,
			Status:           hamodel.StatusTypeEnabled,
			TriggerEventName: haprobe.DbEventNameDetectFailure,
			TriggerCount:     1,
			Priority:         1,
		},
	)

	strategies, err := ha.ReadSwitchingStrategyWithBkBizId(context.Background(), 100)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if len(strategies) != 2 {
		t.Fatalf("expected 2 strategies (biz + global), got %d", len(strategies))
	}

	names := map[string]bool{}
	for _, s := range strategies {
		names[s.Name] = true
	}
	if !names["biz-strategy"] || !names["global-strategy"] {
		t.Errorf("expected both biz and global strategies, got names: %v", names)
	}
}

func TestReadSwitchingStrategy_OtherBizNotReturned(t *testing.T) {
	ha := newTestDbhaData(t)

	insertStrategies(t, ha,
		// strategy belonging to bizId=200
		&hamodel.DbSwitchingStrategy{
			Name:             "other-biz",
			BkBizID:          200,
			Status:           hamodel.StatusTypeEnabled,
			TriggerEventName: haprobe.DbEventNameDetectFailure,
			TriggerCount:     1,
			Priority:         1,
		},
	)

	strategies, err := ha.ReadSwitchingStrategyWithBkBizId(context.Background(), 100)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if len(strategies) != 0 {
		t.Errorf("expected 0 strategies for bizId=100, got %d", len(strategies))
	}
}

func TestReadSwitchingStrategy_EmptyTable(t *testing.T) {
	ha := newTestDbhaData(t)

	strategies, err := ha.ReadSwitchingStrategyWithBkBizId(context.Background(), 100)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if len(strategies) != 0 {
		t.Errorf("expected 0 strategies for empty table, got %d", len(strategies))
	}
}

// ============================================================
// DbhaDataStatus statistics tests
// ============================================================

// These statistics queries rely on MySQL-only SQL: COUNT(DISTINCT col1, col2, ...) over several
// columns, which SQLite rejects with "wrong number of arguments to function count()". They are
// therefore exercised against a real MySQL server configured through the DB_TEST_* environment
// variables; the tests skip when no server is reachable, so `make test` stays self-contained.

// database connection configuration with environment variable support
var statsTestConfig = struct {
	IP     string
	Port   int
	User   string
	Passwd string
	DBName string
}{
	IP:     getEnvWithDefault("DB_TEST_IP", "127.0.0.1"),
	Port:   getEnvAsIntWithDefault("DB_TEST_PORT", 3306),
	User:   getEnvWithDefault("DB_TEST_USER", "test_user"),
	Passwd: getEnvWithDefault("DB_TEST_PASSWD", "test_password"),
	DBName: getEnvWithDefault("DB_TEST_DB", "dbha_data"),
}

// Helper function to get environment variable with default value
func getEnvWithDefault(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

// Helper function to get environment variable as integer with default value
func getEnvAsIntWithDefault(key string, defaultValue int) int {
	if value := os.Getenv(key); value != "" {
		if intValue, err := strconv.Atoi(value); err == nil {
			return intValue
		}
	}
	return defaultValue
}

// newStatsTestDb opens a real MySQL server and rebuilds the DbhaDataStatus table in it so the
// statistics queries run against a known fixture.
func newStatsTestDb(t *testing.T) (*DbhaData, *gorm.DB) {
	t.Helper()

	if os.Getenv("DB_TEST_SKIP_MYSQL") != "" {
		t.Skip("DB_TEST_SKIP_MYSQL is set")
	}

	cfg := statsTestConfig
	addr := fmt.Sprintf("%s:%d", cfg.IP, cfg.Port)

	// Connect without a database first so the schema can be created on demand.
	rootDSN := fmt.Sprintf("%s:%s@tcp(%s)/?charset=utf8mb4&parseTime=True&loc=Local", cfg.User, cfg.Passwd, addr)
	rootDB, err := gorm.Open(mysql.Open(rootDSN), &gorm.Config{})
	if err != nil {
		t.Skipf("no MySQL available, skipping statistics query test: %v", err)
	}
	if sqlDB, e := rootDB.DB(); e == nil {
		defer sqlDB.Close()
	}
	if err := rootDB.Exec(fmt.Sprintf("CREATE DATABASE IF NOT EXISTS %s", cfg.DBName)).Error; err != nil {
		t.Skipf("cannot create test database, skipping statistics query test: %v", err)
	}

	dsn := fmt.Sprintf("%s:%s@tcp(%s)/%s?charset=utf8mb4&parseTime=True&loc=Local",
		cfg.User, cfg.Passwd, addr, cfg.DBName)
	gdb, err := gorm.Open(mysql.Open(dsn), &gorm.Config{})
	if err != nil {
		t.Skipf("no MySQL available, skipping statistics query test: %v", err)
	}

	if err := gdb.Migrator().DropTable(&hamodel.DbhaDataStatus{}); err != nil {
		t.Fatalf("failed to drop test table: %v", err)
	}
	if err := gdb.AutoMigrate(&hamodel.DbhaDataStatus{}); err != nil {
		t.Fatalf("failed to auto migrate DbhaDataStatus: %v", err)
	}

	t.Cleanup(func() {
		if sqlDB, e := gdb.DB(); e == nil {
			_ = sqlDB.Close()
		}
	})

	return &DbhaData{DB: hamysql.WithGormDB(gdb, nil)}, gdb
}

// statusRow is one DbhaDataStatus fixture row. stale marks rows kept outside the window.
type statusRow struct {
	machineID   string
	bkCloudID   int
	ip          string
	port        int
	dbType      haprobe.DbType
	harvestType haprobe.HarvestType
	stale       bool
}

// statsFixtureRows builds a fixture that mixes every de-duplication case at once:
// one instance reporting several collection groups, several instances sharing one IP,
// the same IP under different clouds, several db_types, and a row outside the window.
func statsFixtureRows() []statusRow {
	return []statusRow{
		// One instance reporting all three collection groups.
		{"m1", 0, "127.0.0.1", 3306, "mysql", haprobe.HarvestTypeDefault, false},
		{"m1", 0, "127.0.0.1", 3306, "mysql", haprobe.HarvestTypeHeartbeat, false},
		{"m1", 0, "127.0.0.1", 3306, "mysql", haprobe.HarvestTypeReplDelay, false},
		// A second instance on the same IP, reporting two groups.
		{"m1", 0, "127.0.0.1", 3307, "mysql", haprobe.HarvestTypeDefault, false},
		{"m1", 0, "127.0.0.1", 3307, "mysql", haprobe.HarvestTypeHeartbeat, false},
		// Another IP under the same db_type.
		{"m2", 0, "127.0.0.2", 3306, "mysql", haprobe.HarvestTypeDefault, false},
		// Same IP and port as the first instance but another cloud: a distinct instance and IP.
		{"m4", 1, "127.0.0.1", 3306, "mysql", haprobe.HarvestTypeDefault, false},
		// Another db_type.
		{"m3", 0, "127.0.0.3", 6379, "redis", haprobe.HarvestTypeDefault, false},
		// Outside the window: must be ignored by every count.
		{"m5", 0, "127.0.0.9", 3306, "mysql", haprobe.HarvestTypeDefault, true},
	}
}

func insertStatusRows(t *testing.T, gdb *gorm.DB, rows []statusRow, staleAt time.Time) {
	t.Helper()

	// Limit the INSERT to the columns the fixture needs. deleted_at is a plain time.Time in
	// the model, and its zero value is rejected by MySQL running in strict mode.
	columns := []string{
		hamodel.DbhaStatusFieldMachineID, hamodel.DbhaStatusFieldBkCloudID,
		hamodel.DbhaStatusFieldDbIp, hamodel.DbhaStatusFieldDbPort,
		hamodel.DbhaStatusFieldHarvestType, hamodel.DbhaStatusFieldDbTypeName,
		hamodel.DbhaStatusFieldUpdatedAt,
	}

	now := time.Now().Local()
	for i, r := range rows {
		// GORM only fills updated_at automatically when it is still zero, so an explicit
		// value survives and decides whether the row falls inside the window.
		updatedAt := now
		if r.stale {
			updatedAt = staleAt
		}
		record := &hamodel.DbhaDataStatus{
			MachineID:   r.machineID,
			BkCloudID:   r.bkCloudID,
			DbIp:        r.ip,
			DbPort:      r.port,
			HarvestType: r.harvestType,
			DbTypeName:  r.dbType,
			UpdatedAt:   updatedAt,
		}
		if err := gdb.Model(&hamodel.DbhaDataStatus{}).Select(columns).Create(record).Error; err != nil {
			t.Fatalf("failed to insert fixture row %d: %v", i, err)
		}
	}
}

func TestCountDbhaDataStatusUpdatedWithin(t *testing.T) {
	ha, gdb := newStatsTestDb(t)
	window := 5 * time.Minute

	insertStatusRows(t, gdb, statsFixtureRows(), time.Now().Local().Add(-2*window))

	got, err := ha.CountDbhaDataStatusUpdatedWithin(context.Background(), window)
	if err != nil {
		t.Fatalf("CountDbhaDataStatusUpdatedWithin failed: %v", err)
	}

	// [instance count, ip count] per (db_type, harvest_type).
	want := map[string][2]int64{
		"mysql/default":   {4, 3},
		"mysql/heartbeat": {2, 1},
		"mysql/repldelay": {1, 1},
		"redis/default":   {1, 1},
	}

	gotGroups := map[string][2]int64{}
	for _, item := range got {
		key := fmt.Sprintf("%s/%s", item.DbType, item.HarvestType)
		if _, dup := gotGroups[key]; dup {
			t.Fatalf("duplicate group returned for %s", key)
		}
		gotGroups[key] = [2]int64{item.InstanceCount, item.IPCount}
	}

	if len(gotGroups) != len(want) {
		t.Fatalf("group count mismatch, got: %v, want: %v", gotGroups, want)
	}
	for key, wantCounts := range want {
		gotCounts, ok := gotGroups[key]
		if !ok {
			t.Errorf("missing group %s, got: %v", key, gotGroups)
			continue
		}
		if gotCounts[0] != wantCounts[0] {
			t.Errorf("%s instance count mismatch, got: %d, want: %d", key, gotCounts[0], wantCounts[0])
		}
		if gotCounts[1] != wantCounts[1] {
			t.Errorf("%s ip count mismatch, got: %d, want: %d", key, gotCounts[1], wantCounts[1])
		}
	}
}

func TestCountDbhaDataStatusDeployedIPWithin(t *testing.T) {
	ha, gdb := newStatsTestDb(t)
	window := 5 * time.Minute

	insertStatusRows(t, gdb, statsFixtureRows(), time.Now().Local().Add(-2*window))

	got, err := ha.CountDbhaDataStatusDeployedIPWithin(context.Background(), window)
	if err != nil {
		t.Fatalf("CountDbhaDataStatusDeployedIPWithin failed: %v", err)
	}

	// harvest_type is not part of the grouping, so an IP reporting several collection groups
	// is counted once here while the per-group query counts it once per group (mysql: 3 vs 3+1+1).
	want := map[string]int64{"mysql": 3, "redis": 1}

	gotGroups := map[string]int64{}
	for _, item := range got {
		if _, dup := gotGroups[item.DbType.String()]; dup {
			t.Fatalf("duplicate group returned for %s", item.DbType)
		}
		gotGroups[item.DbType.String()] = item.Count
	}

	if len(gotGroups) != len(want) {
		t.Fatalf("group count mismatch, got: %v, want: %v", gotGroups, want)
	}
	for key, wantCount := range want {
		if gotCount, ok := gotGroups[key]; !ok {
			t.Errorf("missing group %s, got: %v", key, gotGroups)
		} else if gotCount != wantCount {
			t.Errorf("%s deployed ip count mismatch, got: %d, want: %d", key, gotCount, wantCount)
		}
	}
}
