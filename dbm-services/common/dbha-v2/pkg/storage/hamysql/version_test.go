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

package hamysql

import (
	"context"
	"database/sql"
	"database/sql/driver"
	"errors"
	"io"
	"sync"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"gorm.io/driver/mysql"
	"gorm.io/gorm"
)

// versionFakeDriver is a minimal database/sql driver serving "SELECT VERSION()" and plain
// Exec calls. It fails the first failures queries so tests can verify that errors are never
// cached, and the first execFailures execs with a 1064 error to exercise the retry path.
type versionFakeDriver struct {
	mu           sync.Mutex
	queries      int
	failures     int
	version      string
	execs        []string
	execFailures int
}

func (d *versionFakeDriver) Open(string) (driver.Conn, error) {
	return &versionFakeConn{d: d}, nil
}

func (d *versionFakeDriver) query() (driver.Rows, error) {
	d.mu.Lock()
	defer d.mu.Unlock()
	d.queries++
	if d.queries <= d.failures {
		return nil, errors.New("fake version query failure")
	}
	return &versionFakeRows{columns: []string{"VERSION()"}, values: [][]driver.Value{{d.version}}}, nil
}

func (d *versionFakeDriver) exec(query string) (driver.Result, error) {
	d.mu.Lock()
	defer d.mu.Unlock()
	d.execs = append(d.execs, query)
	if len(d.execs) <= d.execFailures {
		return nil, errors.New("Error 1064 (42000): You have an error in your SQL syntax")
	}
	return versionFakeResult{}, nil
}

func (d *versionFakeDriver) queryCount() int {
	d.mu.Lock()
	defer d.mu.Unlock()
	return d.queries
}

func (d *versionFakeDriver) execHistory() []string {
	d.mu.Lock()
	defer d.mu.Unlock()
	return append([]string(nil), d.execs...)
}

type versionFakeResult struct{}

func (versionFakeResult) LastInsertId() (int64, error) { return 0, nil }
func (versionFakeResult) RowsAffected() (int64, error) { return 0, nil }

type versionFakeConn struct {
	d *versionFakeDriver
}

func (c *versionFakeConn) Prepare(string) (driver.Stmt, error) {
	return nil, errors.New("not supported")
}
func (c *versionFakeConn) Close() error              { return nil }
func (c *versionFakeConn) Begin() (driver.Tx, error) { return nil, errors.New("not supported") }

func (c *versionFakeConn) QueryContext(_ context.Context, _ string, _ []driver.NamedValue) (driver.Rows, error) {
	return c.d.query()
}

func (c *versionFakeConn) ExecContext(_ context.Context, query string, _ []driver.NamedValue) (driver.Result, error) {
	return c.d.exec(query)
}

type versionFakeRows struct {
	columns []string
	values  [][]driver.Value
	idx     int
}

func (r *versionFakeRows) Columns() []string { return r.columns }
func (r *versionFakeRows) Close() error      { return nil }

func (r *versionFakeRows) Next(dest []driver.Value) error {
	if r.idx >= len(r.values) {
		return io.EOF
	}
	copy(dest, r.values[r.idx])
	r.idx++
	return nil
}

func newGormDBWithFakeDriver(t *testing.T, drv *versionFakeDriver, drvName string) *GormDB {
	t.Helper()
	sql.Register(drvName, drv)

	sqlDB, err := sql.Open(drvName, "")
	require.NoError(t, err)

	gdb, err := gorm.Open(&mysql.Dialector{
		Config: &mysql.Config{Conn: sqlDB, DriverName: drvName, SkipInitializeWithVersion: true},
	}, &gorm.Config{})
	require.NoError(t, err)

	return WithGormDB(gdb, func() { sqlDB.Close() })
}

func TestVersionCachesOnlySuccess(t *testing.T) {
	drv := &versionFakeDriver{version: "8.4.0-txsql", failures: 1}
	db := newGormDBWithFakeDriver(t, drv, "hamysql-version-fake-retry")
	defer db.Close()

	ctx := context.Background()

	_, err := db.Version(ctx)
	require.Error(t, err)
	assert.Equal(t, 1, drv.queryCount())

	version, err := db.Version(ctx)
	require.NoError(t, err)
	assert.Equal(t, "8.4.0-txsql", version)
	assert.Equal(t, 2, drv.queryCount())

	version, err = db.Version(ctx)
	require.NoError(t, err)
	assert.Equal(t, "8.4.0-txsql", version)
	assert.Equal(t, 2, drv.queryCount(), "cached version must not trigger another query")

	useReplica, err := db.UseReplicaNaming(ctx)
	require.NoError(t, err)
	assert.True(t, useReplica)
	assert.Equal(t, 2, drv.queryCount())
}

func TestChangeReplicationToRetry(t *testing.T) {
	drv := &versionFakeDriver{version: "8.4.0", execFailures: 1}
	db := newGormDBWithFakeDriver(t, drv, "hamysql-version-fake-changerepl")
	defer db.Close()

	src := ReplSource{
		Host:         "192.168.1.1",
		Port:         3306,
		User:         "repl",
		Password:     "p@ssMASTER9x",
		AutoPosition: AutoPositionOn,
	}
	sqlText, err := db.ChangeReplicationTo(context.Background(), src)
	require.NoError(t, err)

	execs := drv.execHistory()
	require.Len(t, execs, 2)
	assert.Contains(t, execs[0], "CHANGE REPLICATION SOURCE TO")
	assert.Contains(t, execs[1], "CHANGE MASTER TO")
	assert.Contains(t, sqlText, "CHANGE MASTER TO")

	// the auto-enabled public key clause is dropped on retry (falsified version evidence)
	assert.Contains(t, execs[0], "GET_SOURCE_PUBLIC_KEY = 1")
	assert.NotContains(t, execs[1], "PUBLIC_KEY")
}

func TestChangeReplicationToRetryKeepsExplicitPublicKey(t *testing.T) {
	drv := &versionFakeDriver{version: "8.4.0", execFailures: 1}
	db := newGormDBWithFakeDriver(t, drv, "hamysql-version-fake-retry-pubkey")
	defer db.Close()

	src := ReplSource{
		Host:         "192.168.1.1",
		Port:         3306,
		User:         "repl",
		Password:     "secret",
		AutoPosition: AutoPositionOn,
		GetPublicKey: GetPublicKeyOn,
	}
	_, err := db.ChangeReplicationTo(context.Background(), src)
	require.NoError(t, err)

	execs := drv.execHistory()
	require.Len(t, execs, 2)
	assert.Contains(t, execs[0], "GET_SOURCE_PUBLIC_KEY = 1")
	assert.Contains(t, execs[1], "GET_MASTER_PUBLIC_KEY = 1")
}

func TestChangeReplicationToPublicKeyAuto(t *testing.T) {
	src := ReplSource{
		Host:         "192.168.1.1",
		Port:         3306,
		User:         "repl",
		Password:     "secret",
		AutoPosition: AutoPositionOn,
	}

	drv84 := &versionFakeDriver{version: "8.4.0-txsql"}
	db84 := newGormDBWithFakeDriver(t, drv84, "hamysql-version-fake-pubkey-84")
	defer db84.Close()
	_, err := db84.ChangeReplicationTo(context.Background(), src)
	require.NoError(t, err)
	assert.Contains(t, drv84.execHistory()[0], "GET_SOURCE_PUBLIC_KEY = 1")

	drv80 := &versionFakeDriver{version: "8.0.36-tmysql-3.2.2"}
	db80 := newGormDBWithFakeDriver(t, drv80, "hamysql-version-fake-pubkey-80")
	defer db80.Close()
	_, err = db80.ChangeReplicationTo(context.Background(), src)
	require.NoError(t, err)
	assert.NotContains(t, drv80.execHistory()[0], "PUBLIC_KEY")

	drv57 := &versionFakeDriver{version: "5.7.44"}
	db57 := newGormDBWithFakeDriver(t, drv57, "hamysql-version-fake-pubkey-57")
	defer db57.Close()
	_, err = db57.ChangeReplicationTo(context.Background(), src)
	require.NoError(t, err)
	assert.NotContains(t, drv57.execHistory()[0], "PUBLIC_KEY")

	// explicit off wins over the version-based default
	drvOff := &versionFakeDriver{version: "8.4.0"}
	dbOff := newGormDBWithFakeDriver(t, drvOff, "hamysql-version-fake-pubkey-off")
	defer dbOff.Close()
	srcOff := src
	srcOff.GetPublicKey = GetPublicKeyOff
	_, err = dbOff.ChangeReplicationTo(context.Background(), srcOff)
	require.NoError(t, err)
	assert.NotContains(t, drvOff.execHistory()[0], "PUBLIC_KEY")
}
