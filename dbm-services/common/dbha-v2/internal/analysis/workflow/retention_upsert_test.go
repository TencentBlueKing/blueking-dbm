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

package workflow

import (
	"fmt"
	"os"
	"strconv"
	"testing"
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/dbm"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"

	"gorm.io/driver/mysql"
	"gorm.io/gorm"
)

const saveRespondFixtureCloudID = 990002

func TestSaveRespondRefreshesUpdatedAt(t *testing.T) {
	gdb := openSaveRespondMySQL(t)
	old := time.Now().Local().Add(-48 * time.Hour).Truncate(time.Second)
	const port = 41002
	insertStaleMetadata(t, gdb, port, old)
	t.Cleanup(func() {
		gdb.Where(fmt.Sprintf("%s = ?", hamodel.DbmMetadataFieldBkCloudID), saveRespondFixtureCloudID).
			Delete(&hamodel.DbmMetadata{})
		if sqlDB, err := gdb.DB(); err == nil {
			_ = sqlDB.Close()
		}
	})

	syncer := &Synchronizer{db: hamysql.WithGormDB(gdb, nil)}
	err := syncer.saveRespond(&dbm.Response{Data: []*dbm.DbInstMetadata{{
		BkCloudID: saveRespondFixtureCloudID,
		IP:        "127.0.0.1",
		Port:      port,
		Status:    dbm.Running,
	}}})
	if err != nil {
		t.Fatalf("save metadata failed, errmsg: %s", err)
	}

	var got time.Time
	err = gdb.Model(&hamodel.DbmMetadata{}).
		Where(fmt.Sprintf("%s = ? AND %s = ? AND %s = ?",
			hamodel.DbmMetadataFieldBkCloudID, hamodel.DbmMetadataFieldListenIP, hamodel.DbmMetadataFieldListenPort),
			saveRespondFixtureCloudID, "127.0.0.1", port).
		Pluck(hamodel.DbmMetadataFieldUpdatedAt, &got).Error
	if err != nil || !got.After(old) {
		t.Fatalf("save must refresh updated_at, got: %s, previous: %s, errmsg: %v", got, old, err)
	}
}

func openSaveRespondMySQL(t *testing.T) *gorm.DB {
	t.Helper()

	if os.Getenv("DB_TEST_SKIP_MYSQL") != "" {
		t.Skip("DB_TEST_SKIP_MYSQL is set")
	}

	port := 3306
	if value := os.Getenv("DB_TEST_PORT"); value != "" {
		parsed, err := strconv.Atoi(value)
		if err != nil {
			t.Fatalf("invalid db port, errmsg: %s", err)
		}
		port = parsed
	}
	ip := os.Getenv("DB_TEST_IP")
	if ip == "" {
		ip = "127.0.0.1"
	}
	user := os.Getenv("DB_TEST_USER")
	if user == "" {
		user = "test_user"
	}
	passwd := os.Getenv("DB_TEST_PASSWD")
	if passwd == "" {
		passwd = "test_password"
	}
	dbName := os.Getenv("DB_TEST_DB")
	if dbName == "" {
		dbName = "test_dbha_data"
	}

	dsn := fmt.Sprintf("%s:%s@tcp(%s:%d)/%s?charset=utf8mb4&parseTime=True&loc=Local", user, passwd, ip, port, dbName)
	gdb, err := gorm.Open(mysql.Open(dsn), &gorm.Config{})
	if err != nil {
		t.Skipf("no MySQL available, skipping save test, errmsg: %s", err)
	}
	if err := gdb.Exec("SELECT 1").Error; err != nil {
		t.Skipf("no MySQL available, skipping save test, errmsg: %s", err)
	}
	if err := gdb.AutoMigrate(&hamodel.DbmMetadata{}); err != nil {
		t.Fatalf("auto migrate failed, errmsg: %s", err)
	}

	return gdb
}

func insertStaleMetadata(t *testing.T, gdb *gorm.DB, port int, updatedAt time.Time) {
	t.Helper()

	columns := []string{
		hamodel.DbmMetadataFieldBkCloudID, hamodel.DbmMetadataFieldListenIP, hamodel.DbmMetadataFieldListenPort,
		hamodel.DbmMetadataFieldUpdatedAt,
	}
	record := &hamodel.DbmMetadata{
		BkCloudID: saveRespondFixtureCloudID,
		IP:        "127.0.0.1",
		Port:      port,
		UpdatedAt: updatedAt,
	}
	if err := gdb.Model(&hamodel.DbmMetadata{}).Select(columns).Create(record).Error; err != nil {
		t.Fatalf("insert metadata fixture failed, errmsg: %s", err)
	}
}
