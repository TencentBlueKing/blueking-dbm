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
	"strings"
	"testing"
	"time"

	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"

	mysqldriver "github.com/go-sql-driver/mysql"
	"gorm.io/driver/mysql"
	"gorm.io/gorm"
)

// The retention integration tests only ever delete rows they inserted themselves: status rows carry
// the machine_id prefix below, metadata rows the fixture cloud ID, snapshot rows the switch_id prefix.
// They never run the full cleanup loop, which scans the whole table and could touch other rows.
const (
	retentionFixturePrefix  = "dbha_retention_test_"
	retentionFixtureCloudID = 990001
	retentionFixtureIP      = "127.0.0.1"
	retentionTestTimeout    = 10 * time.Second
	retentionTestRetention  = 14 * 24 * time.Hour
)

func newRetentionTestDb(t *testing.T) (*DbhaData, *gorm.DB) {
	t.Helper()

	if os.Getenv("DB_TEST_SKIP_MYSQL") != "" {
		t.Skip("DB_TEST_SKIP_MYSQL is set")
	}

	cfg := statsTestConfig
	dsn := fmt.Sprintf("%s:%s@tcp(%s:%d)/%s?charset=utf8mb4&parseTime=True&loc=Local",
		cfg.User, cfg.Passwd, cfg.IP, cfg.Port, cfg.DBName)
	gdb, err := gorm.Open(mysql.Open(dsn), &gorm.Config{})
	if err != nil {
		t.Skipf("no MySQL available, skipping retention test, errmsg: %s", err)
	}
	if err := gdb.Exec("SELECT 1").Error; err != nil {
		t.Skipf("no MySQL available, skipping retention test, errmsg: %s", err)
	}

	if err := gdb.AutoMigrate(&hamodel.DbhaDataStatus{}, &hamodel.DbmMetadata{}); err != nil {
		t.Fatalf("auto migrate failed, errmsg: %s", err)
	}
	// GORM cannot auto-migrate the snapshot model (unique index on a longtext column); production
	// creates it through the migrator, so the test only ensures the columns the switch check reads.
	snapshotDDL := fmt.Sprintf("CREATE TABLE IF NOT EXISTS %s (`id` bigint unsigned AUTO_INCREMENT, "+
		"`%s` varchar(64), `%s` varchar(32), `%s` datetime(3) NULL, PRIMARY KEY (`id`), "+
		"UNIQUE INDEX `idx_switch_id` (`%s`), INDEX `idx_status` (`%s`), INDEX `idx_time` (`%s`))",
		hamodel.DbSwitchingSnapshotLogTableName,
		hamodel.DbSwitchingSnapshotLogFieldSwitchID, hamodel.DbSwitchingSnapshotLogFieldStatus,
		hamodel.DbSwitchingSnapshotLogFieldStartTime, hamodel.DbSwitchingSnapshotLogFieldSwitchID,
		hamodel.DbSwitchingSnapshotLogFieldStatus, hamodel.DbSwitchingSnapshotLogFieldStartTime)
	if err := gdb.Exec(snapshotDDL).Error; err != nil {
		t.Fatalf("create snapshot table failed, errmsg: %s", err)
	}

	deleteRetentionFixtures(t, gdb)
	t.Cleanup(func() {
		deleteRetentionFixtures(t, gdb)
		if sqlDB, e := gdb.DB(); e == nil {
			_ = sqlDB.Close()
		}
	})

	return &DbhaData{DB: hamysql.WithGormDB(gdb, nil)}, gdb
}

func deleteRetentionFixtures(t *testing.T, gdb *gorm.DB) {
	t.Helper()

	steps := []error{
		gdb.Where(fmt.Sprintf("%s LIKE ?", hamodel.DbhaStatusFieldMachineID), retentionFixturePrefix+"%").
			Delete(&hamodel.DbhaDataStatus{}).Error,
		gdb.Where(fmt.Sprintf("%s = ?", hamodel.DbmMetadataFieldBkCloudID), retentionFixtureCloudID).
			Delete(&hamodel.DbmMetadata{}).Error,
		gdb.Where(fmt.Sprintf("%s LIKE ?", hamodel.DbSwitchingSnapshotLogFieldSwitchID), retentionFixturePrefix+"%").
			Delete(&hamodel.DbSwitchingSnapshotLog{}).Error,
	}
	for _, err := range steps {
		if err != nil {
			t.Fatalf("delete retention fixtures failed, errmsg: %s", err)
		}
	}
}

func insertRetentionStatus(t *testing.T, gdb *gorm.DB, machine string, port int, updatedAt time.Time) StatusKey {
	t.Helper()

	// Only the needed columns are written: deleted_at is a plain time.Time whose zero value strict
	// MySQL rejects, and an explicit updated_at survives GORM's auto-fill.
	columns := []string{
		hamodel.DbhaStatusFieldMachineID, hamodel.DbhaStatusFieldBkCloudID, hamodel.DbhaStatusFieldDbIp,
		hamodel.DbhaStatusFieldDbPort, hamodel.DbhaStatusFieldHarvestType, hamodel.DbhaStatusFieldUpdatedAt,
	}
	record := &hamodel.DbhaDataStatus{
		MachineID:   retentionFixturePrefix + machine,
		DbIp:        retentionFixtureIP,
		DbPort:      port,
		HarvestType: "default",
		UpdatedAt:   updatedAt,
	}
	if err := gdb.Model(&hamodel.DbhaDataStatus{}).Select(columns).Create(record).Error; err != nil {
		t.Fatalf("insert status fixture failed, errmsg: %s", err)
	}

	return StatusKey{MachineID: record.MachineID, DbIP: retentionFixtureIP, DbPort: port, HarvestType: "default"}
}

func insertRetentionMetadata(t *testing.T, gdb *gorm.DB, port int, updatedAt time.Time) MetadataKey {
	t.Helper()

	columns := []string{
		hamodel.DbmMetadataFieldBkCloudID, hamodel.DbmMetadataFieldListenIP, hamodel.DbmMetadataFieldListenPort,
		hamodel.DbmMetadataFieldUpdatedAt,
	}
	record := &hamodel.DbmMetadata{
		BkCloudID: retentionFixtureCloudID,
		IP:        retentionFixtureIP,
		Port:      port,
		UpdatedAt: updatedAt,
	}
	if err := gdb.Model(&hamodel.DbmMetadata{}).Select(columns).Create(record).Error; err != nil {
		t.Fatalf("insert metadata fixture failed, errmsg: %s", err)
	}

	return MetadataKey{BkCloudID: retentionFixtureCloudID, IP: retentionFixtureIP, Port: port}
}

func countRetentionStatusFixtures(t *testing.T, gdb *gorm.DB) int64 {
	t.Helper()

	var n int64
	err := gdb.Model(&hamodel.DbhaDataStatus{}).
		Where(fmt.Sprintf("%s LIKE ?", hamodel.DbhaStatusFieldMachineID), retentionFixturePrefix+"%").
		Count(&n).Error
	if err != nil {
		t.Fatalf("count status fixtures failed, errmsg: %s", err)
	}

	return n
}

func TestRetentionStatusWindowAndDelete(t *testing.T) {
	ha, gdb := newRetentionTestDb(t)
	ctx := context.Background()
	now := time.Now().Local()
	stale := now.Add(-20 * 24 * time.Hour)

	var keys []StatusKey
	keys = append(keys, insertRetentionStatus(t, gdb, "m1", 20001, stale))
	keys = append(keys, insertRetentionStatus(t, gdb, "m1", 20002, now))
	keys = append(keys, insertRetentionStatus(t, gdb, "m2", 20001, stale))
	keys = append(keys, insertRetentionStatus(t, gdb, "m3", 20001, now))

	rows, err := ha.ScanStatusWindow(ctx, StatusCursor{MachineID: retentionFixturePrefix}, 1000, retentionTestTimeout)
	if err != nil {
		t.Fatalf("scan status window failed, errmsg: %s", err)
	}
	staleSeen := 0
	fixtureSeen := 0
	for _, r := range rows {
		if !strings.HasPrefix(r.Key.MachineID, retentionFixturePrefix) {
			continue
		}
		fixtureSeen++
		if r.UpdatedAt.Before(now.Add(-retentionTestRetention)) {
			staleSeen++
		}
	}
	if fixtureSeen != 4 || staleSeen != 2 {
		t.Fatalf("window should return 4 fixture rows with 2 stale, got: %d/%d", fixtureSeen, staleSeen)
	}

	excl, err := ha.ScanStatusWindow(ctx, StatusCursor{MachineID: retentionFixturePrefix + "m1", Exclusive: true},
		1000, retentionTestTimeout)
	if err != nil {
		t.Fatalf("scan exclusive window failed, errmsg: %s", err)
	}
	for _, r := range excl {
		if r.Key.MachineID == retentionFixturePrefix+"m1" {
			t.Fatalf("exclusive cursor must skip the cursor prefix")
		}
	}

	// All four keys are submitted; the re-check on updated_at must keep the two fresh rows.
	deleted, err := ha.DeleteStatusByPK(ctx, keys, now.Add(-retentionTestRetention), retentionTestTimeout)
	if err != nil {
		t.Fatalf("delete status failed, errmsg: %s", err)
	}
	if deleted != 2 {
		t.Fatalf("expected 2 stale rows deleted, got: %d", deleted)
	}
	if left := countRetentionStatusFixtures(t, gdb); left != 2 {
		t.Fatalf("fresh rows must survive the delete, left: %d", left)
	}
}

func TestRetentionMetadataWindowAndDelete(t *testing.T) {
	ha, gdb := newRetentionTestDb(t)
	ctx := context.Background()
	now := time.Now().Local()
	stale := now.Add(-20 * 24 * time.Hour)

	keys := []MetadataKey{
		insertRetentionMetadata(t, gdb, 30001, stale),
		insertRetentionMetadata(t, gdb, 30002, now),
		insertRetentionMetadata(t, gdb, 30003, stale),
	}

	cursor := MetadataCursor{Set: true, BkCloudID: retentionFixtureCloudID, IP: retentionFixtureIP}
	rows, err := ha.ScanMetadataWindow(ctx, cursor, 1000, retentionTestTimeout)
	if err != nil {
		t.Fatalf("scan metadata window failed, errmsg: %s", err)
	}
	fixtureSeen := 0
	for _, r := range rows {
		if r.Key.BkCloudID == retentionFixtureCloudID {
			fixtureSeen++
		}
	}
	if fixtureSeen != 3 {
		t.Fatalf("window should return 3 fixture rows, got: %d", fixtureSeen)
	}

	cursor.Exclusive = true
	excl, err := ha.ScanMetadataWindow(ctx, cursor, 1000, retentionTestTimeout)
	if err != nil {
		t.Fatalf("scan exclusive metadata window failed, errmsg: %s", err)
	}
	for _, r := range excl {
		if r.Key.BkCloudID == retentionFixtureCloudID && r.Key.IP == retentionFixtureIP {
			t.Fatalf("exclusive cursor must skip the cursor prefix")
		}
	}

	if _, err := ha.ScanMetadataWindow(ctx, MetadataCursor{}, 10, retentionTestTimeout); err != nil {
		t.Fatalf("scan from table start failed, errmsg: %s", err)
	}

	deleted, err := ha.DeleteMetadataByPK(ctx, keys, now.Add(-retentionTestRetention), retentionTestTimeout)
	if err != nil {
		t.Fatalf("delete metadata failed, errmsg: %s", err)
	}
	if deleted != 2 {
		t.Fatalf("expected 2 stale metadata rows deleted, got: %d", deleted)
	}

	if n, _ := ha.DeleteMetadataByPK(ctx, nil, now, retentionTestTimeout); n != 0 {
		t.Fatalf("empty key list must delete nothing, got: %d", n)
	}
}

func TestRetentionHasRecentUpdate(t *testing.T) {
	ha, gdb := newRetentionTestDb(t)
	ctx := context.Background()
	now := time.Now().Local()

	insertRetentionStatus(t, gdb, "recent", 20001, now)
	insertRetentionMetadata(t, gdb, 30001, now)

	for _, table := range []string{hamodel.DbhaDataStatusTableName, hamodel.DbmMetadataTableName} {
		found, err := ha.HasRecentUpdate(ctx, table, now.Add(-time.Minute), retentionTestTimeout)
		if err != nil || !found {
			t.Fatalf("table %s should have a recent row, found: %t, errmsg: %v", table, found, err)
		}

		found, err = ha.HasRecentUpdate(ctx, table, now.Add(time.Hour), retentionTestTimeout)
		if err != nil || found {
			t.Fatalf("table %s must not report rows from the future, found: %t, errmsg: %v", table, found, err)
		}
	}

	_, err := ha.HasRecentUpdate(ctx, "t_unknown", now, retentionTestTimeout)
	if RetentionErrorKindOf(err) != RetentionErrorOther || err == nil {
		t.Fatalf("unknown table must be rejected, errmsg: %v", err)
	}
}

func TestRetentionHasSwitchInProgress(t *testing.T) {
	ha, gdb := newRetentionTestDb(t)
	ctx := context.Background()
	now := time.Now().Local()
	since := now.Add(-10 * time.Minute)

	before, err := ha.HasSwitchInProgress(ctx, since, retentionTestTimeout)
	if err != nil {
		t.Fatalf("switch check failed, errmsg: %s", err)
	}

	insertSnapshot := func(id string, start time.Time) {
		columns := []string{hamodel.DbSwitchingSnapshotLogFieldSwitchID, hamodel.DbSwitchingSnapshotLogFieldStatus,
			hamodel.DbSwitchingSnapshotLogFieldStartTime}
		record := &hamodel.DbSwitchingSnapshotLog{
			SwitchID:  retentionFixturePrefix + id,
			Status:    hamodel.DbSwitchingSnapshotLogStatusDoing,
			StartTime: &start,
		}
		if err := gdb.Select(columns).Create(record).Error; err != nil {
			t.Fatalf("insert snapshot fixture failed, errmsg: %s", err)
		}
	}

	// A doing record older than switchTimeout is a crash leftover and must not count.
	insertSnapshot("old", now.Add(-time.Hour))
	if !before {
		found, err := ha.HasSwitchInProgress(ctx, since, retentionTestTimeout)
		if err != nil || found {
			t.Fatalf("stale doing record must be ignored, found: %t, errmsg: %v", found, err)
		}
	}

	insertSnapshot("new", now)
	found, err := ha.HasSwitchInProgress(ctx, since, retentionTestTimeout)
	if err != nil || !found {
		t.Fatalf("fresh doing record must be found, found: %t, errmsg: %v", found, err)
	}
}

func TestRetentionQueryPlans(t *testing.T) {
	_, gdb := newRetentionTestDb(t)
	now := time.Now().Local()

	// Enough rows that the optimizer weighs the index instead of a trivial full scan.
	const fixtureRows = 3000
	insertBulkRetentionFixtures(t, gdb, fixtureRows, now)

	cutoff := now.Add(-retentionTestRetention)
	metaQuery, metaArgs := metadataWindowQuery(MetadataCursor{Set: true, BkCloudID: retentionFixtureCloudID,
		IP: retentionFixtureIP}, retentionTestTimeout)
	statusTuples := [][]any{
		{retentionFixturePrefix + "b00001", 0, retentionFixtureIP, 20001, "default"},
		{retentionFixturePrefix + "b00002", 0, retentionFixtureIP, 20002, "default"},
	}
	metaTuples := [][]any{
		{retentionFixtureCloudID, retentionFixtureIP, 40001},
		{retentionFixtureCloudID, retentionFixtureIP, 40002},
	}

	cases := []struct {
		name       string
		query      string
		args       []any
		noFilesort bool
	}{
		{"status window", statusWindowQuery(false, retentionTestTimeout),
			[]any{retentionFixturePrefix, 20000}, true},
		{"metadata window", metaQuery, append(metaArgs, 20000), true},
		{"status delete", statusDeleteQuery(), []any{statusTuples, cutoff}, false},
		{"metadata delete", metadataDeleteQuery(), []any{metaTuples, cutoff}, false},
	}

	for _, c := range cases {
		var plan []map[string]any
		if err := gdb.Raw("EXPLAIN "+c.query, c.args...).Scan(&plan).Error; err != nil {
			t.Fatalf("%s: explain failed, errmsg: %s", c.name, err)
		}
		if len(plan) != 1 {
			t.Fatalf("%s: unexpected plan rows: %v", c.name, plan)
		}

		typ, key, extra := planField(plan[0], "type"), planField(plan[0], "key"), planField(plan[0], "Extra")
		if typ != "range" || key != "PRIMARY" {
			t.Fatalf("%s: expected range scan on PRIMARY, got type: %s, key: %s", c.name, typ, key)
		}
		if c.noFilesort && strings.Contains(extra, "filesort") {
			t.Fatalf("%s: window scan must not sort, extra: %s", c.name, extra)
		}
	}

	since := now.Add(-time.Hour)
	health := []struct {
		name   string
		table  string
		column string
	}{
		{"status health", hamodel.DbhaDataStatusTableName, hamodel.DbhaStatusFieldUpdatedAt},
		{"metadata health", hamodel.DbmMetadataTableName, hamodel.DbmMetadataFieldUpdatedAt},
	}
	for _, c := range health {
		var plan []map[string]any
		query := recentUpdateQuery(c.table, c.column, retentionTestTimeout)
		if err := gdb.Raw("EXPLAIN "+query, since).Scan(&plan).Error; err != nil {
			t.Fatalf("%s: explain failed, errmsg: %s", c.name, err)
		}
		if len(plan) != 1 {
			t.Fatalf("%s: unexpected plan rows: %v", c.name, plan)
		}
		if key := planField(plan[0], "key"); key != "idx_updated_at" {
			t.Fatalf("%s: expected idx_updated_at, got key: %s", c.name, key)
		}
	}
}

func TestRetentionErrorKindOf(t *testing.T) {
	cases := []struct {
		name string
		err  error
		want RetentionErrorKind
	}{
		{"deadlock", &mysqldriver.MySQLError{Number: 1213}, RetentionErrorConflict},
		{"lock wait", &mysqldriver.MySQLError{Number: 1205}, RetentionErrorConflict},
		{"max execution time", &mysqldriver.MySQLError{Number: 3024}, RetentionErrorTimeout},
		{"context deadline", context.DeadlineExceeded, RetentionErrorTimeout},
		{"no delete privilege", &mysqldriver.MySQLError{Number: 1142}, RetentionErrorOther},
		{"wrapped deadlock", gerrors.NewE(gerrors.MysqlFailure, &mysqldriver.MySQLError{Number: 1213}),
			RetentionErrorConflict},
		{"wrapped timeout", wrapRetentionError(&mysqldriver.MySQLError{Number: 3024}), RetentionErrorTimeout},
		{"nil", nil, RetentionErrorOther},
	}

	for _, c := range cases {
		if got := RetentionErrorKindOf(c.err); got != c.want {
			t.Fatalf("%s: got kind %d, want %d", c.name, got, c.want)
		}
	}

	wrapped := wrapRetentionError(context.DeadlineExceeded)
	gerr, ok := wrapped.(*gerrors.Error)
	if !ok || !gerr.HasCode(gerrors.Timeout) {
		t.Fatalf("timeouts must be wrapped with the timeout code, got: %v", wrapped)
	}
	other := wrapRetentionError(&mysqldriver.MySQLError{Number: 1142})
	if gerr, ok := other.(*gerrors.Error); !ok || !gerr.HasCode(gerrors.MysqlFailure) {
		t.Fatalf("other errors must be wrapped with the mysql failure code, got: %v", other)
	}
}

func insertBulkRetentionFixtures(t *testing.T, gdb *gorm.DB, n int, now time.Time) {
	t.Helper()

	statusValues := make([]string, 0, n)
	metaValues := make([]string, 0, n)
	// A few fresh rows sit in a backlog of stale rows. The health check looks for updates inside the
	// last hour, which is the distribution where idx_updated_at is useful. A table of almost all fresh
	// rows may legally scan the whole table, so this fixture does not try to represent that case.
	const freshRows = 32
	for i := 0; i < n; i++ {
		ts := now.Add(-20 * 24 * time.Hour).Format(time.DateTime)
		if i < freshRows {
			ts = now.Format(time.DateTime)
		}
		statusValues = append(statusValues, fmt.Sprintf("('%sb%05d', 0, '%s', %d, 'default', '%s')",
			retentionFixturePrefix, i, retentionFixtureIP, 20000+i%10, ts))
		metaValues = append(metaValues, fmt.Sprintf("(%d, '%s', %d, '%s')",
			retentionFixtureCloudID, retentionFixtureIP, 40000+i, ts))
	}

	statusSQL := fmt.Sprintf("INSERT INTO %s (%s, %s, %s, %s, %s, %s) VALUES %s",
		hamodel.DbhaDataStatusTableName,
		hamodel.DbhaStatusFieldMachineID, hamodel.DbhaStatusFieldBkCloudID, hamodel.DbhaStatusFieldDbIp,
		hamodel.DbhaStatusFieldDbPort, hamodel.DbhaStatusFieldHarvestType, hamodel.DbhaStatusFieldUpdatedAt,
		strings.Join(statusValues, ","))
	metaSQL := fmt.Sprintf("INSERT INTO %s (%s, %s, %s, %s) VALUES %s",
		hamodel.DbmMetadataTableName,
		hamodel.DbmMetadataFieldBkCloudID, hamodel.DbmMetadataFieldListenIP, hamodel.DbmMetadataFieldListenPort,
		hamodel.DbmMetadataFieldUpdatedAt, strings.Join(metaValues, ","))

	for _, stmt := range []string{statusSQL, metaSQL, "ANALYZE TABLE " + hamodel.DbhaDataStatusTableName + ", " +
		hamodel.DbmMetadataTableName} {
		if err := gdb.Exec(stmt).Error; err != nil {
			t.Fatalf("insert bulk fixtures failed, errmsg: %s", err)
		}
	}
}

func planField(row map[string]any, name string) string {
	switch v := row[name].(type) {
	case nil:
		return ""
	case []byte:
		return string(v)
	default:
		return fmt.Sprintf("%v", v)
	}
}
