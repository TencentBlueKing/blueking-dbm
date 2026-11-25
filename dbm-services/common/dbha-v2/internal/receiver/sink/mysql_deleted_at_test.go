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

package sink

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

	gormmysql "gorm.io/driver/mysql"
	"gorm.io/gorm"
)

const (
	statusOmitMachineID = "dbha_status_omit_test"
	statusOmitPort      = 41011
	statusOmitIP        = "127.0.0.1"
)

func TestStatusUpsertOmitsDeletedAt(t *testing.T) {
	gdb := openStatusOmitMySQL(t)
	old := time.Now().Local().Add(-48 * time.Hour).Truncate(time.Second)
	insertStaleStatus(t, gdb, old)
	t.Cleanup(func() {
		gdb.Where(fmt.Sprintf("%s = ?", hamodel.DbhaStatusFieldMachineID), statusOmitMachineID).
			Delete(&hamodel.DbhaDataStatus{})
		if sqlDB, err := gdb.DB(); err == nil {
			_ = sqlDB.Close()
		}
	})

	row := newStatusOmitRow()
	if err := (gormChunkWriter{}).write(context.Background(), gdb, []*hamodel.DbhaDataStatus{row}); err != nil {
		t.Fatalf("batch save failed, errmsg: %s", err)
	}
	assertStatusRefreshed(t, gdb, old)

	rewindStatusUpdatedAt(t, gdb, old)
	saver := &mysql{dbs: []*hamysql.GormDB{hamysql.WithGormDB(gdb, nil)}}
	saver.writeSaveEndpoints(&Message{Topic: "probe"}, newStatusOmitRow(), &WriteStats{})
	assertStatusRefreshed(t, gdb, old)
}

func newStatusOmitRow() *hamodel.DbhaDataStatus {
	return hamodel.NewDbhaData(&haprobe.HarvestData{
		HarvestBaseData: haprobe.HarvestBaseData{
			MachineID:   statusOmitMachineID,
			DbIp:        statusOmitIP,
			DbPort:      statusOmitPort,
			HarvestType: haprobe.HarvestTypeDefault,
		},
	})
}

func assertStatusRefreshed(t *testing.T, gdb *gorm.DB, old time.Time) {
	t.Helper()

	query := fmt.Sprintf("SELECT %s, %s IS NULL FROM %s WHERE %s = ? AND %s = ? AND %s = ? AND %s = ? AND %s = ?",
		hamodel.DbhaStatusFieldUpdatedAt, hamodel.DbhaStatusFieldDeletedAt, hamodel.DbhaDataStatusTableName,
		hamodel.DbhaStatusFieldMachineID, hamodel.DbhaStatusFieldBkCloudID, hamodel.DbhaStatusFieldDbIp,
		hamodel.DbhaStatusFieldDbPort, hamodel.DbhaStatusFieldHarvestType)
	var updated time.Time
	var deletedNull bool
	err := gdb.Raw(query, statusOmitMachineID, 0, statusOmitIP, statusOmitPort, haprobe.HarvestTypeDefault).
		Row().Scan(&updated, &deletedNull)
	if err != nil {
		t.Fatalf("read status row failed, errmsg: %s", err)
	}
	if !updated.After(old) || !deletedNull {
		t.Fatalf("status upsert must refresh updated_at and keep deleted_at null, updated: %s, deleted_null: %t",
			updated, deletedNull)
	}
}

func rewindStatusUpdatedAt(t *testing.T, gdb *gorm.DB, old time.Time) {
	t.Helper()

	query := fmt.Sprintf("UPDATE %s SET %s = ? WHERE %s = ? AND %s = ? AND %s = ? AND %s = ? AND %s = ?",
		hamodel.DbhaDataStatusTableName, hamodel.DbhaStatusFieldUpdatedAt,
		hamodel.DbhaStatusFieldMachineID, hamodel.DbhaStatusFieldBkCloudID, hamodel.DbhaStatusFieldDbIp,
		hamodel.DbhaStatusFieldDbPort, hamodel.DbhaStatusFieldHarvestType)
	err := gdb.Exec(query, old, statusOmitMachineID, 0, statusOmitIP, statusOmitPort, haprobe.HarvestTypeDefault).Error
	if err != nil {
		t.Fatalf("rewind updated_at failed, errmsg: %s", err)
	}
}

func insertStaleStatus(t *testing.T, gdb *gorm.DB, updatedAt time.Time) {
	t.Helper()

	columns := []string{
		hamodel.DbhaStatusFieldMachineID, hamodel.DbhaStatusFieldBkCloudID, hamodel.DbhaStatusFieldDbIp,
		hamodel.DbhaStatusFieldDbPort, hamodel.DbhaStatusFieldHarvestType, hamodel.DbhaStatusFieldUpdatedAt,
	}
	record := &hamodel.DbhaDataStatus{
		MachineID:   statusOmitMachineID,
		DbIp:        statusOmitIP,
		DbPort:      statusOmitPort,
		HarvestType: haprobe.HarvestTypeDefault,
		UpdatedAt:   updatedAt,
	}
	if err := gdb.Model(&hamodel.DbhaDataStatus{}).Select(columns).Create(record).Error; err != nil {
		t.Fatalf("insert status fixture failed, errmsg: %s", err)
	}
}

func openStatusOmitMySQL(t *testing.T) *gorm.DB {
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
	gdb, err := gorm.Open(gormmysql.Open(dsn), &gorm.Config{})
	if err != nil {
		t.Skipf("no MySQL available, skipping status upsert test, errmsg: %s", err)
	}
	if err := gdb.Exec("SELECT 1").Error; err != nil {
		t.Skipf("no MySQL available, skipping status upsert test, errmsg: %s", err)
	}
	if err := gdb.AutoMigrate(&hamodel.DbhaDataStatus{}); err != nil {
		t.Fatalf("auto migrate failed, errmsg: %s", err)
	}

	return gdb
}
