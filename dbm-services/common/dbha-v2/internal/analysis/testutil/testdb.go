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

package testutil

import (
	"testing"

	"dbm-services/common/dbha-v2/internal/analysis/storage"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"

	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

// TestDbhaData wraps DbhaData for testing, providing access to both DbhaData and the underlying GormDB.
type TestDbhaData struct {
	DbhaData *storage.DbhaData
	GormDB   *gorm.DB
}

// NewTestDbhaData creates a DbhaData instance backed by SQLite in-memory database for unit testing.
// It auto-migrates tables and closes the connection when the test ends.
func NewTestDbhaData(t *testing.T) *TestDbhaData {
	t.Helper()

	gormDB, err := gorm.Open(sqlite.Open(":memory:"), &gorm.Config{})
	if err != nil {
		t.Fatalf("failed to open sqlite in-memory database: %v", err)
	}

	// auto-migrate tables
	if err := gormDB.AutoMigrate(&hamodel.DbSwitchingStrategy{}); err != nil {
		t.Fatalf("failed to auto migrate DbSwitchingStrategy: %v", err)
	}

	t.Cleanup(func() {
		sqlDB, _ := gormDB.DB()
		if sqlDB != nil {
			sqlDB.Close()
		}
	})

	return &TestDbhaData{
		DbhaData: &storage.DbhaData{DB: hamysql.NewGormDBForTest(gormDB)},
		GormDB:   gormDB,
	}
}

// InsertStrategies inserts strategy records in batch into the test database.
func InsertStrategies(t *testing.T, hadata *storage.DbhaData, strategies ...*hamodel.DbSwitchingStrategy) {
	t.Helper()
	for _, s := range strategies {
		if err := hadata.DB.DB().Create(s).Error; err != nil {
			t.Fatalf("failed to insert strategy: %v", err)
		}
	}
}
