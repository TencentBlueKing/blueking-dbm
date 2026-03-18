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
	"testing"

	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"

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

	return &DbhaData{DB: hamysql.NewGormDBForTest(gormDB)}
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

	strategies, err := ha.ReadSwitchingStrategyWithBkBizId(100)
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

	strategies, err := ha.ReadSwitchingStrategyWithBkBizId(100)
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

	strategies, err := ha.ReadSwitchingStrategyWithBkBizId(100)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if len(strategies) != 0 {
		t.Errorf("expected 0 strategies for bizId=100, got %d", len(strategies))
	}
}

func TestReadSwitchingStrategy_EmptyTable(t *testing.T) {
	ha := newTestDbhaData(t)

	strategies, err := ha.ReadSwitchingStrategyWithBkBizId(100)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if len(strategies) != 0 {
		t.Errorf("expected 0 strategies for empty table, got %d", len(strategies))
	}
}
