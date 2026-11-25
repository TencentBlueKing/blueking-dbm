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

// Package storage implements the HA MySQL data access used by the analysis module: metadata and
// status reads for detection, switching logs and strategies, and retention cleanup of stale rows.
package storage

import (
	"context"
	"errors"
	"fmt"
	"time"

	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"

	mysqldriver "github.com/go-sql-driver/mysql"
)

// RetentionErrorKind classifies an error returned by the retention queries.
type RetentionErrorKind int

const (
	// RetentionErrorOther covers every error that is neither a timeout nor a lock conflict.
	RetentionErrorOther RetentionErrorKind = iota
	// RetentionErrorTimeout means the statement hit MAX_EXECUTION_TIME or its context deadline.
	RetentionErrorTimeout
	// RetentionErrorConflict means the statement failed on a deadlock or a lock wait timeout.
	RetentionErrorConflict
)

const (
	mysqlErrLockWaitTimeout  = 1205
	mysqlErrDeadlock         = 1213
	mysqlErrMaxExecutionTime = 3024
)

// StatusKey is the primary key of a t_dbha_status row.
type StatusKey struct {
	MachineID   string
	BkCloudID   int
	DbIP        string
	DbPort      int
	HarvestType string
}

// StatusWindowRow is one row of a t_dbha_status retention window.
type StatusWindowRow struct {
	Key       StatusKey
	UpdatedAt time.Time
}

// StatusCursor marks where the next t_dbha_status window starts. The zero value starts at the
// first row. Exclusive skips every row whose machine_id equals MachineID.
type StatusCursor struct {
	MachineID string
	Exclusive bool
}

// MetadataKey is the primary key of a t_dbm_metadata row.
type MetadataKey struct {
	BkCloudID int
	IP        string
	Port      int
}

// MetadataWindowRow is one row of a t_dbm_metadata retention window.
type MetadataWindowRow struct {
	Key       MetadataKey
	UpdatedAt time.Time
}

// MetadataCursor marks where the next t_dbm_metadata window starts. When Set is false the window
// starts at the first row. Exclusive skips every row whose (bk_cloud_id, ip) equals the cursor.
type MetadataCursor struct {
	Set       bool
	BkCloudID int
	IP        string
	Exclusive bool
}

type statusWindowScan struct {
	MachineID   string    `gorm:"column:machine_id"`
	BkCloudID   int       `gorm:"column:bk_cloud_id"`
	DbIP        string    `gorm:"column:db_ip"`
	DbPort      int       `gorm:"column:db_port"`
	HarvestType string    `gorm:"column:harvest_type"`
	UpdatedAt   time.Time `gorm:"column:updated_at"`
}

type metadataWindowScan struct {
	BkCloudID int       `gorm:"column:bk_cloud_id"`
	IP        string    `gorm:"column:ip"`
	Port      int       `gorm:"column:port"`
	UpdatedAt time.Time `gorm:"column:updated_at"`
}

// HasSwitchInProgress reports whether any switch started after since is still marked doing in
// t_db_switching_snapshot_log. Records older than since are ignored so that a process crash that
// left a doing record behind cannot block retention forever. timeout bounds the query.
func (ha *DbhaData) HasSwitchInProgress(ctx context.Context, since time.Time, timeout time.Duration) (bool, error) {
	ctx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	query := fmt.Sprintf("SELECT 1 FROM %s WHERE %s = ? AND %s > ? LIMIT 1",
		hamodel.DbSwitchingSnapshotLogTableName,
		hamodel.DbSwitchingSnapshotLogFieldStatus,
		hamodel.DbSwitchingSnapshotLogFieldStartTime,
	)

	var found []int
	err := ha.DB.DB().WithContext(ctx).
		Raw(query, hamodel.DbSwitchingSnapshotLogStatusDoing, since).
		Scan(&found).Error
	if err != nil {
		return false, wrapRetentionError(err)
	}

	return len(found) > 0, nil
}

// HasRecentUpdate reports whether table holds at least one row updated after since. table must be
// hamodel.DbhaDataStatusTableName or hamodel.DbmMetadataTableName, otherwise an InvalidParameter
// error is returned. timeout bounds the query both on the server (MAX_EXECUTION_TIME) and on the
// client context.
func (ha *DbhaData) HasRecentUpdate(ctx context.Context, table string, since time.Time,
	timeout time.Duration) (bool, error) {

	var updatedAtColumn string
	switch table {
	case hamodel.DbhaDataStatusTableName:
		updatedAtColumn = hamodel.DbhaStatusFieldUpdatedAt
	case hamodel.DbmMetadataTableName:
		updatedAtColumn = hamodel.DbmMetadataFieldUpdatedAt
	default:
		return false, gerrors.Newf(gerrors.InvalidParameter, "unsupported retention table: %s", table)
	}

	ctx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	query := recentUpdateQuery(table, updatedAtColumn, timeout)

	var found []int
	if err := ha.DB.DB().WithContext(ctx).Raw(query, since).Scan(&found).Error; err != nil {
		return false, wrapRetentionError(err)
	}

	return len(found) > 0, nil
}

// ScanStatusWindow returns up to limit rows of t_dbha_status in primary key order, starting at
// cursor. Only the primary key and updated_at are read. limit must be positive. timeout bounds
// the query both on the server and on the client context. An empty result means the table end.
func (ha *DbhaData) ScanStatusWindow(ctx context.Context, cursor StatusCursor, limit int,
	timeout time.Duration) ([]StatusWindowRow, error) {

	ctx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	var scanned []statusWindowScan
	query := statusWindowQuery(cursor.Exclusive, timeout)
	err := ha.DB.DB().WithContext(ctx).Raw(query, cursor.MachineID, limit).Scan(&scanned).Error
	if err != nil {
		return nil, wrapRetentionError(err)
	}

	rows := make([]StatusWindowRow, 0, len(scanned))
	for _, s := range scanned {
		rows = append(rows, StatusWindowRow{
			Key: StatusKey{
				MachineID:   s.MachineID,
				BkCloudID:   s.BkCloudID,
				DbIP:        s.DbIP,
				DbPort:      s.DbPort,
				HarvestType: s.HarvestType,
			},
			UpdatedAt: s.UpdatedAt,
		})
	}

	return rows, nil
}

// ScanMetadataWindow returns up to limit rows of t_dbm_metadata in primary key order, starting at
// cursor. Only the primary key and updated_at are read. limit must be positive. timeout bounds
// the query both on the server and on the client context. An empty result means the table end.
func (ha *DbhaData) ScanMetadataWindow(ctx context.Context, cursor MetadataCursor, limit int,
	timeout time.Duration) ([]MetadataWindowRow, error) {

	ctx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	query, args := metadataWindowQuery(cursor, timeout)

	var scanned []metadataWindowScan
	err := ha.DB.DB().WithContext(ctx).Raw(query, append(args, limit)...).Scan(&scanned).Error
	if err != nil {
		return nil, wrapRetentionError(err)
	}

	rows := make([]MetadataWindowRow, 0, len(scanned))
	for _, s := range scanned {
		rows = append(rows, MetadataWindowRow{
			Key:       MetadataKey{BkCloudID: s.BkCloudID, IP: s.IP, Port: s.Port},
			UpdatedAt: s.UpdatedAt,
		})
	}

	return rows, nil
}

// DeleteStatusByPK deletes the t_dbha_status rows identified by keys that are still older than
// cutoff. Rows refreshed after the scan are kept because updated_at is re-checked by the DELETE.
// It returns the number of deleted rows; an empty keys slice deletes nothing.
func (ha *DbhaData) DeleteStatusByPK(ctx context.Context, keys []StatusKey, cutoff time.Time,
	timeout time.Duration) (int64, error) {

	if len(keys) == 0 {
		return 0, nil
	}

	tuples := make([][]any, 0, len(keys))
	for _, k := range keys {
		tuples = append(tuples, []any{k.MachineID, k.BkCloudID, k.DbIP, k.DbPort, k.HarvestType})
	}

	return ha.execRetentionDelete(ctx, statusDeleteQuery(), tuples, cutoff, timeout)
}

// DeleteMetadataByPK deletes the t_dbm_metadata rows identified by keys that are still older than
// cutoff. Rows refreshed after the scan are kept because updated_at is re-checked by the DELETE.
// It returns the number of deleted rows; an empty keys slice deletes nothing.
func (ha *DbhaData) DeleteMetadataByPK(ctx context.Context, keys []MetadataKey, cutoff time.Time,
	timeout time.Duration) (int64, error) {

	if len(keys) == 0 {
		return 0, nil
	}

	tuples := make([][]any, 0, len(keys))
	for _, k := range keys {
		tuples = append(tuples, []any{k.BkCloudID, k.IP, k.Port})
	}

	return ha.execRetentionDelete(ctx, metadataDeleteQuery(), tuples, cutoff, timeout)
}

func (ha *DbhaData) execRetentionDelete(ctx context.Context, query string, tuples [][]any,
	cutoff time.Time, timeout time.Duration) (int64, error) {

	ctx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	result := ha.DB.DB().WithContext(ctx).Exec(query, tuples, cutoff)
	if result.Error != nil {
		return 0, wrapRetentionError(result.Error)
	}

	return result.RowsAffected, nil
}

// RetentionErrorKindOf classifies err returned by the retention queries. Errors wrapped by gerrors
// keep their cause, so the MySQL error number is still inspected.
func RetentionErrorKindOf(err error) RetentionErrorKind {
	if err == nil {
		return RetentionErrorOther
	}

	var gerr *gerrors.Error
	if errors.As(err, &gerr) && gerr.HasCode(gerrors.Timeout) {
		return RetentionErrorTimeout
	}
	if isRetentionTimeout(err) {
		return RetentionErrorTimeout
	}

	var myErr *mysqldriver.MySQLError
	if errors.As(err, &myErr) && (myErr.Number == mysqlErrDeadlock || myErr.Number == mysqlErrLockWaitTimeout) {
		return RetentionErrorConflict
	}

	return RetentionErrorOther
}

// statusWindowQuery builds the t_dbha_status window scan. Ordering by the cursor prefix alone keeps
// the scan on the primary key regardless of the column order the live primary key ended up with
// after schema convergence; the cursor value is compared by MySQL only, so the column collation
// decides equality and order.
func statusWindowQuery(exclusive bool, timeout time.Duration) string {
	op := ">="
	if exclusive {
		op = ">"
	}

	return fmt.Sprintf("SELECT /*+ MAX_EXECUTION_TIME(%d) */ %s, %s, %s, %s, %s, %s FROM %s "+
		"WHERE %s %s ? ORDER BY %s LIMIT ?",
		timeout.Milliseconds(),
		hamodel.DbhaStatusFieldMachineID, hamodel.DbhaStatusFieldBkCloudID, hamodel.DbhaStatusFieldDbIp,
		hamodel.DbhaStatusFieldDbPort, hamodel.DbhaStatusFieldHarvestType, hamodel.DbhaStatusFieldUpdatedAt,
		hamodel.DbhaDataStatusTableName,
		hamodel.DbhaStatusFieldMachineID, op, hamodel.DbhaStatusFieldMachineID,
	)
}

// metadataWindowQuery builds the t_dbm_metadata window scan and its cursor arguments; the trailing
// LIMIT placeholder is left for the caller.
func metadataWindowQuery(cursor MetadataCursor, timeout time.Duration) (string, []any) {
	where := ""
	var args []any
	if cursor.Set {
		op := ">="
		if cursor.Exclusive {
			op = ">"
		}
		where = fmt.Sprintf("WHERE (%s > ? OR (%s = ? AND %s %s ?)) ",
			hamodel.DbmMetadataFieldBkCloudID, hamodel.DbmMetadataFieldBkCloudID,
			hamodel.DbmMetadataFieldListenIP, op)
		args = []any{cursor.BkCloudID, cursor.BkCloudID, cursor.IP}
	}

	query := fmt.Sprintf("SELECT /*+ MAX_EXECUTION_TIME(%d) */ %s, %s, %s, %s FROM %s %sORDER BY %s, %s LIMIT ?",
		timeout.Milliseconds(),
		hamodel.DbmMetadataFieldBkCloudID, hamodel.DbmMetadataFieldListenIP, hamodel.DbmMetadataFieldListenPort,
		hamodel.DbmMetadataFieldUpdatedAt,
		hamodel.DbmMetadataTableName, where,
		hamodel.DbmMetadataFieldBkCloudID, hamodel.DbmMetadataFieldListenIP,
	)

	return query, args
}

// recentUpdateQuery is the health check. It does not force idx_updated_at: a database that has not
// run the migration yet must keep scanning instead of failing the statement.
func recentUpdateQuery(table, column string, timeout time.Duration) string {
	return fmt.Sprintf("SELECT /*+ MAX_EXECUTION_TIME(%d) */ 1 FROM %s WHERE %s > ? LIMIT 1",
		timeout.Milliseconds(), table, column)
}

// statusDeleteQuery deletes by primary key. FORCE INDEX is written in the multi-table form because
// MySQL 5.7 rejects an index hint on a single-table DELETE. PRIMARY exists before and after the
// updated_at index migration, so this statement does not depend on that migration.
func statusDeleteQuery() string {
	return fmt.Sprintf("DELETE t FROM %s AS t FORCE INDEX (PRIMARY) WHERE (%s, %s, %s, %s, %s) IN ? AND %s < ?",
		hamodel.DbhaDataStatusTableName,
		hamodel.DbhaStatusFieldMachineID, hamodel.DbhaStatusFieldBkCloudID, hamodel.DbhaStatusFieldDbIp,
		hamodel.DbhaStatusFieldDbPort, hamodel.DbhaStatusFieldHarvestType, hamodel.DbhaStatusFieldUpdatedAt,
	)
}

// metadataDeleteQuery deletes by primary key and keeps the same PRIMARY hint as statusDeleteQuery.
func metadataDeleteQuery() string {
	return fmt.Sprintf("DELETE t FROM %s AS t FORCE INDEX (PRIMARY) WHERE (%s, %s, %s) IN ? AND %s < ?",
		hamodel.DbmMetadataTableName,
		hamodel.DbmMetadataFieldBkCloudID, hamodel.DbmMetadataFieldListenIP, hamodel.DbmMetadataFieldListenPort,
		hamodel.DbmMetadataFieldUpdatedAt,
	)
}

// wrapRetentionError classifies before wrapping so callers can tell timeouts from other failures
// by the gerrors code alone.
func wrapRetentionError(err error) error {
	if isRetentionTimeout(err) {
		return gerrors.NewE(gerrors.Timeout, err)
	}

	return gerrors.NewE(gerrors.MysqlFailure, err)
}

func isRetentionTimeout(err error) bool {
	if errors.Is(err, context.DeadlineExceeded) {
		return true
	}

	var myErr *mysqldriver.MySQLError

	return errors.As(err, &myErr) && myErr.Number == mysqlErrMaxExecutionTime
}
