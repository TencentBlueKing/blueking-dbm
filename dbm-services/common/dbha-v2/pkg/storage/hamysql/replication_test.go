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
	"errors"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestUseReplicaNamingByVersion(t *testing.T) {
	cases := []struct {
		version string
		want    bool
	}{
		{"8.4.0", true},
		{"8.4.0-txsql", true},
		{"8.4.3", true},
		{"9.0.0", true},
		{"8.0.36", false},
		{"8.0.36-tmysql-3.2.2", false},
		{"5.7.44", false},
		{"10.3.7-MariaDB-tspider-3.7.12", false},
		{"11.4.2-MariaDB-log", false},
		{"", false},
	}

	for _, c := range cases {
		assert.Equal(t, c.want, UseReplicaNamingByVersion(c.version), "version: %q", c.version)
	}
}

func TestChangeReplicationSQL(t *testing.T) {
	src := ReplSource{
		Host:     "192.168.1.1",
		Port:     3306,
		User:     "repl",
		Password: "secret",
		LogFile:  "mysql-bin.000001",
		LogPos:   154,
	}

	legacy := ChangeReplicationSQL(false, src)
	assert.Equal(t, "CHANGE MASTER TO MASTER_HOST = '192.168.1.1', MASTER_PORT = 3306, "+
		"MASTER_USER = 'repl', MASTER_PASSWORD = 'secret', "+
		"MASTER_LOG_FILE = 'mysql-bin.000001', MASTER_LOG_POS = 154, MASTER_AUTO_POSITION = 0", legacy)

	replica := ChangeReplicationSQL(true, src)
	assert.Equal(t, "CHANGE REPLICATION SOURCE TO SOURCE_HOST = '192.168.1.1', SOURCE_PORT = 3306, "+
		"SOURCE_USER = 'repl', SOURCE_PASSWORD = 'secret', "+
		"SOURCE_LOG_FILE = 'mysql-bin.000001', SOURCE_LOG_POS = 154, SOURCE_AUTO_POSITION = 0", replica)

	noUser := ChangeReplicationSQL(false, ReplSource{Host: "192.168.1.1", Port: 20000, LogFile: "binlog.000002", LogPos: 4})
	assert.Equal(t, "CHANGE MASTER TO MASTER_HOST = '192.168.1.1', MASTER_PORT = 20000, "+
		"MASTER_LOG_FILE = 'binlog.000002', MASTER_LOG_POS = 4, MASTER_AUTO_POSITION = 0", noUser)

	autoPos := ChangeReplicationSQL(true, ReplSource{Host: "192.168.1.2", Port: 26000, User: "repl",
		AutoPosition: AutoPositionOn})
	assert.Equal(t, "CHANGE REPLICATION SOURCE TO SOURCE_HOST = '192.168.1.2', SOURCE_PORT = 26000, "+
		"SOURCE_USER = 'repl', SOURCE_PASSWORD = '', SOURCE_AUTO_POSITION = 1", autoPos)

	omit := ChangeReplicationSQL(false, ReplSource{Host: "192.168.1.1", Port: 3306, User: "repl",
		LogFile: "mysql-bin.000001", LogPos: 154, AutoPosition: AutoPositionOmit})
	assert.Equal(t, "CHANGE MASTER TO MASTER_HOST = '192.168.1.1', MASTER_PORT = 3306, "+
		"MASTER_USER = 'repl', MASTER_PASSWORD = '', MASTER_LOG_FILE = 'mysql-bin.000001', MASTER_LOG_POS = 154", omit)

	pubKeyLegacy := ChangeReplicationSQL(false, ReplSource{Host: "192.168.1.1", Port: 3306, User: "repl",
		Password: "secret", LogFile: "mysql-bin.000001", LogPos: 154,
		AutoPosition: AutoPositionOmit, GetPublicKey: GetPublicKeyOn})
	assert.Equal(t, "CHANGE MASTER TO MASTER_HOST = '192.168.1.1', MASTER_PORT = 3306, "+
		"MASTER_USER = 'repl', MASTER_PASSWORD = 'secret', MASTER_LOG_FILE = 'mysql-bin.000001', "+
		"MASTER_LOG_POS = 154, GET_MASTER_PUBLIC_KEY = 1", pubKeyLegacy)

	pubKeyReplica := ChangeReplicationSQL(true, ReplSource{Host: "192.168.1.1", Port: 3306, User: "repl",
		Password: "secret", AutoPosition: AutoPositionOn, GetPublicKey: GetPublicKeyOn})
	assert.Equal(t, "CHANGE REPLICATION SOURCE TO SOURCE_HOST = '192.168.1.1', SOURCE_PORT = 3306, "+
		"SOURCE_USER = 'repl', SOURCE_PASSWORD = 'secret', SOURCE_AUTO_POSITION = 1, "+
		"GET_SOURCE_PUBLIC_KEY = 1", pubKeyReplica)
}

func TestMaskSecret(t *testing.T) {
	sqlText := "CHANGE MASTER TO MASTER_HOST = '192.168.1.1', MASTER_PASSWORD = 'p@ss', MASTER_PORT = 3306"
	assert.Equal(t, "CHANGE MASTER TO MASTER_HOST = '192.168.1.1', MASTER_PASSWORD = '<secret>', MASTER_PORT = 3306",
		maskSecret(sqlText, "p@ss"))
	assert.Equal(t, sqlText, maskSecret(sqlText, ""))
}

func TestChangeReplicationSQLKeepsKeywordLikeValues(t *testing.T) {
	src := ReplSource{
		Host:     "MASTER.DB.LOCAL",
		Port:     3306,
		User:     "repl",
		Password: "aMASTER9x",
		LogFile:  "MASTER-bin.000001",
		LogPos:   154,
	}

	legacy := ChangeReplicationSQL(false, src)
	assert.Contains(t, legacy, "MASTER_HOST = 'MASTER.DB.LOCAL'")
	assert.Contains(t, legacy, "MASTER_PASSWORD = 'aMASTER9x'")
	assert.Contains(t, legacy, "MASTER_LOG_FILE = 'MASTER-bin.000001'")

	replica := ChangeReplicationSQL(true, src)
	assert.Contains(t, replica, "SOURCE_HOST = 'MASTER.DB.LOCAL'")
	assert.Contains(t, replica, "SOURCE_PASSWORD = 'aMASTER9x'")
	assert.Contains(t, replica, "SOURCE_LOG_FILE = 'MASTER-bin.000001'")
}

func TestReplStatements(t *testing.T) {
	drv := &versionFakeDriver{version: "8.4.0-txsql"}
	db := newGormDBWithFakeDriver(t, drv, "hamysql-version-fake-stmts-84")
	defer db.Close()

	stmts, err := db.ReplStatements(context.Background())
	require.NoError(t, err)
	assert.Equal(t, "SHOW REPLICA STATUS", stmts.ShowSlaveStatus)
	assert.Equal(t, "SHOW BINARY LOG STATUS", stmts.ShowMasterStatus)
	assert.Equal(t, "START REPLICA", stmts.StartSlave)
	assert.Equal(t, "STOP REPLICA", stmts.StopSlave)
	assert.Equal(t, "RESET REPLICA ALL", stmts.ResetSlaveAll)

	drvLegacy := &versionFakeDriver{version: "8.0.36"}
	dbLegacy := newGormDBWithFakeDriver(t, drvLegacy, "hamysql-version-fake-stmts-80")
	defer dbLegacy.Close()

	stmts, err = dbLegacy.ReplStatements(context.Background())
	require.NoError(t, err)
	assert.Equal(t, "SHOW SLAVE STATUS", stmts.ShowSlaveStatus)
	assert.Equal(t, "SHOW MASTER STATUS", stmts.ShowMasterStatus)
	assert.Equal(t, "START SLAVE", stmts.StartSlave)
	assert.Equal(t, "STOP SLAVE", stmts.StopSlave)
	assert.Equal(t, "RESET SLAVE /*!50516 ALL */", stmts.ResetSlaveAll)
}

func TestReplicationStatusNormalize(t *testing.T) {
	t.Run("replica columns are normalized back", func(t *testing.T) {
		status := &ReplicationStatus{
			SourceHost:          "192.168.1.1",
			SourcePort:          3306,
			SourceLogFile:       "mysql-bin.000001",
			ReadSourceLogPos:    154,
			RelaySourceLogFile:  "mysql-bin.000002",
			ExecSourceLogPos:    200,
			ReplicaIORunning:    "Yes",
			ReplicaSQLRunning:   "No",
			SecondsBehindSource: sql.NullInt64{Int64: 7, Valid: true},
			SourceServerID:      42,
		}
		status.Normalize()

		assert.Equal(t, "192.168.1.1", status.MasterHost)
		assert.Equal(t, 3306, status.MasterPort)
		assert.Equal(t, "mysql-bin.000001", status.MasterLogFile)
		assert.Equal(t, uint64(154), status.ReadMasterLogPos)
		assert.Equal(t, "mysql-bin.000002", status.RelayMasterLogFile)
		assert.Equal(t, uint64(200), status.ExecMasterLogPos)
		assert.Equal(t, "Yes", status.SlaveIORunning)
		assert.Equal(t, "No", status.SlaveSQLRunning)
		assert.Equal(t, sql.NullInt64{Int64: 7, Valid: true}, status.SecondsBehindMaster)
		assert.Equal(t, uint64(42), status.MasterServerID)
	})

	t.Run("legacy values win when both families are present", func(t *testing.T) {
		status := &ReplicationStatus{
			MasterHost:          "192.168.1.1",
			SourceHost:          "192.168.1.2",
			MasterPort:          3306,
			SourcePort:          3307,
			SlaveIORunning:      "Yes",
			ReplicaIORunning:    "No",
			MasterServerID:      11,
			SourceServerID:      22,
			RelayMasterLogFile:  "mysql-bin.000009",
			SecondsBehindMaster: sql.NullInt64{Int64: 3, Valid: true},
			SecondsBehindSource: sql.NullInt64{Int64: 9, Valid: true},
		}
		status.Normalize()

		assert.Equal(t, "192.168.1.1", status.MasterHost)
		assert.Equal(t, 3306, status.MasterPort)
		assert.Equal(t, "Yes", status.SlaveIORunning)
		assert.Equal(t, uint64(11), status.MasterServerID)
		assert.Equal(t, "mysql-bin.000009", status.RelayMasterLogFile)
		assert.Equal(t, sql.NullInt64{Int64: 3, Valid: true}, status.SecondsBehindMaster)
	})

	t.Run("NULL or negative replica delay never overwrites", func(t *testing.T) {
		status := &ReplicationStatus{SecondsBehindSource: sql.NullInt64{Valid: false}}
		status.Normalize()
		assert.Equal(t, sql.NullInt64{}, status.SecondsBehindMaster)

		status = &ReplicationStatus{SecondsBehindSource: sql.NullInt64{Int64: -1, Valid: true}}
		status.Normalize()
		assert.Equal(t, sql.NullInt64{}, status.SecondsBehindMaster)
	})
}

func TestIsMySQLSyntaxError(t *testing.T) {
	assert.True(t, isMySQLSyntaxError(errors.New("Error 1064 (42000): You have an error in your SQL syntax")))
	assert.False(t, isMySQLSyntaxError(errors.New("Error 1045 (28000): Access denied")))
	assert.False(t, isMySQLSyntaxError(nil))
}
