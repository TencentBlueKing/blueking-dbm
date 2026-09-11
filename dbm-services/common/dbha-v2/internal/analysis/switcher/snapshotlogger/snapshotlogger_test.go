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

package snapshotlogger

import (
	"encoding/json"
	"fmt"
	"os"
	"strconv"
	"testing"
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/storage"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"

	"github.com/stretchr/testify/assert"
	"go.uber.org/zap"
)

// database connection configuration with environment variable support
var testConfig = struct {
	IP     string
	Port   int
	User   string
	Passwd string
}{
	IP:     getEnvWithDefault("DB_TEST_IP", "127.0.0.1"),
	Port:   getEnvAsIntWithDefault("DB_TEST_PORT", 3306),
	User:   getEnvWithDefault("DB_TEST_USER", "test_user"),
	Passwd: getEnvWithDefault("DB_TEST_PASSWD", "test_password"),
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

// mockLogger captures log output for testing.
type mockLogger struct {
	messages []string
}

func (m *mockLogger) OriginLogger() *zap.Logger { return nil }

func (m *mockLogger) Debug(format string, args ...any) {
	m.messages = append(m.messages, "DEBUG: "+fmt.Sprintf(format, args...))
}

func (m *mockLogger) Info(format string, args ...any) {
	m.messages = append(m.messages, "INFO: "+fmt.Sprintf(format, args...))
}

func (m *mockLogger) Warn(format string, args ...any) {
	m.messages = append(m.messages, "WARN: "+fmt.Sprintf(format, args...))
}

func (m *mockLogger) Error(format string, args ...any) {
	m.messages = append(m.messages, "ERROR: "+fmt.Sprintf(format, args...))
}

func (m *mockLogger) Fatal(format string, args ...any) {
	m.messages = append(m.messages, "FATAL: "+fmt.Sprintf(format, args...))
}

// Ensure mockLogger implements logger.Logger at compile time.
var _ logger.Logger = (*mockLogger)(nil)

// newTestSnapshotData creates a SwitchingSnapshotData for testing.
func newTestSnapshotData() *SwitchingSnapshotData {
	now := time.Now()
	return &SwitchingSnapshotData{
		StdSwitchingSnapshotData: StdSwitchingSnapshotData{
			StartTime:            &now,
			BkBizID:              123,
			BkCloudID:            0,
			Reason:               "test reason",
			DbType:               "mysql",
			ActionScope:          "cluster",
			StrategyJSON:         json.RawMessage(`{"name":"strategy1"}`),
			FailureInstancesJSON: json.RawMessage(`[{"ip":"127.0.0.1","port":3306}]`),
			MetadataSetJSON:      json.RawMessage(`[{"ip":"127.0.0.1","port":3306}]`),
		},
		DbSwitchingSnapshotLog: &hamodel.DbSwitchingSnapshotLog{
			SwitchID:    "switch-001",
			BkBizID:     123,
			BkCloudID:   0,
			Reason:      "test reason",
			DbType:      "mysql",
			ActionScope: "cluster",
			Action:      hamodel.SnapshotActionTypePreSwitch,
			StartTime:   &now,
			Status:      hamodel.DbSwitchingSnapshotLogStatusDoing,
		},
	}
}

// newTestSnapshotDataWithDB creates a SwitchingSnapshotData with metadata for DB logging.
func newTestSnapshotDataWithDB() *SwitchingSnapshotData {
	now := time.Now()
	return &SwitchingSnapshotData{
		StdSwitchingSnapshotData: StdSwitchingSnapshotData{
			BkBizID:     123,
			BkCloudID:   0,
			Reason:      "test reason",
			StartTime:   &now,
			DbType:      "mysql",
			ActionScope: "cluster",
		},
		DbSwitchingSnapshotLog: &hamodel.DbSwitchingSnapshotLog{
			SwitchID:    fmt.Sprintf("test-switch-%d", now.UnixNano()),
			BkBizID:     123,
			BkCloudID:   0,
			Reason:      "test reason",
			DbType:      "mysql",
			ActionScope: "cluster",
			StartTime:   &now,
			Status:      hamodel.DbSwitchingSnapshotLogStatusDoing,
		},
	}
}

// --- Tests for DbSnapshotHandler (end-to-end, requires real DB) ---

// TestDbSnapshotHandler_PreSwitchLog_PostSwitchLog_Cycle tests the complete PreSwitchLog-PostSwitchLog cycle
func TestDbSnapshotHandler_PreSwitchLog_PostSwitchLog_Cycle(t *testing.T) {
	for i := 1; i <= 3; i++ {
		t.Run(fmt.Sprintf("Cycle test iteration %d", i), func(t *testing.T) {
			handler := NewDbSnapshotHandler("tcp",
				testConfig.IP,
				testConfig.Port,
				testConfig.User,
				testConfig.Passwd,
				SwitchSnapshotLogDefaultDbWriteTimeout,
				SwitchSnapshotLogDefaultDbConnectTimeout,
				SwitchSnapshotLogDefaultDbOpenCheckTimeout)

			err := handler.Open()
			if err != nil {
				t.Fatalf("Open failed on iteration %d: %v", i, err)
			}
			defer handler.Close()

			record := newTestSnapshotDataWithDB()
			record.DbSwitchingSnapshotLog.SwitchID = fmt.Sprintf("test-switch-%d-iter%d", time.Now().UnixNano(), i)

			// PreSwitchLog creates the record
			err = handler.PreSwitchLog(record)
			if err != nil {
				t.Fatalf("PreSwitchLog failed on iteration %d: %v", i, err)
			}
			t.Logf("PreSwitchLog succeeded on iteration %d, switchId: %s", i, record.DbSwitchingSnapshotLog.SwitchID)

			// Simulate post-switch: set result and finished time
			now := time.Now()
			record.DbSwitchingSnapshotLog.FinishedTime = &now
			record.DbSwitchingSnapshotLog.Result = "switching completed successfully"
			record.DbSwitchingSnapshotLog.Status = hamodel.DbSwitchingSnapshotLogStatusSuccess

			// PostSwitchLog updates the record
			err = handler.PostSwitchLog(record)
			if err != nil {
				t.Fatalf("PostSwitchLog failed on iteration %d: %v", i, err)
			}
			t.Logf("PostSwitchLog succeeded on iteration %d", i)
		})
	}

	t.Log("Complete PreSwitchLog-PostSwitchLog cycle test finished, please check records in the database")
}

// --- Tests for DbSnapshotHandler (parameter validation, no DB required) ---

// TestDbSnapshotHandler_ParameterValidation tests parameter validation of DbSnapshotHandler
func TestDbSnapshotHandler_ParameterValidation(t *testing.T) {
	t.Run("NewDbSnapshotHandler", func(t *testing.T) {
		hdl := NewDbSnapshotHandler("tcp", "127.0.0.1", 3306, "root", "password",
			1*time.Second, 3*time.Second, 10*time.Second)

		assert.NotNil(t, hdl)
		assert.Equal(t, "tcp", hdl.Proto)
		assert.Equal(t, "127.0.0.1", hdl.Ip)
		assert.Equal(t, 3306, hdl.Port)
		assert.Equal(t, "root", hdl.User)
		assert.Equal(t, "password", hdl.Passwd)
		assert.Equal(t, 1*time.Second, hdl.writeTimeout)
		assert.Equal(t, 3*time.Second, hdl.connectTimeout)
		assert.Equal(t, 10*time.Second, hdl.openCheckTimeout)
	})

	t.Run("Close_NilLogDb", func(t *testing.T) {
		hdl := NewDbSnapshotHandler("tcp", "127.0.0.1", 3306, "root", "password",
			1*time.Second, 3*time.Second, 10*time.Second)
		// Close should not panic when logDb is nil
		hdl.Close()
	})

	t.Run("PreSwitchLog_NilRecord", func(t *testing.T) {
		hdl := NewDbSnapshotHandler("tcp", "127.0.0.1", 3306, "root", "password",
			1*time.Second, 3*time.Second, 10*time.Second)
		err := hdl.PreSwitchLog(nil)
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "nil")
	})

	t.Run("PreSwitchLog_NilLogDb", func(t *testing.T) {
		hdl := NewDbSnapshotHandler("tcp", "127.0.0.1", 3306, "root", "password",
			1*time.Second, 3*time.Second, 10*time.Second)
		err := hdl.PreSwitchLog(newTestSnapshotData())
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "mysql instance for before writing switch snapshot log is nil")
	})

	t.Run("PreSwitchLog_NilDbSwitchingSnapshotLog", func(t *testing.T) {
		hdl := NewDbSnapshotHandler("tcp", "127.0.0.1", 3306, "root", "password",
			1*time.Second, 3*time.Second, 10*time.Second)
		hdl.logDb = &storage.DbhaData{}
		record := &SwitchingSnapshotData{}
		err := hdl.PreSwitchLog(record)
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "dbSwitchingSnapshotLog is nil for before db switching snapshot")
	})

	t.Run("PostSwitchLog_NilRecord", func(t *testing.T) {
		hdl := NewDbSnapshotHandler("tcp", "127.0.0.1", 3306, "root", "password",
			1*time.Second, 3*time.Second, 10*time.Second)
		err := hdl.PostSwitchLog(nil)
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "nil")
	})

	t.Run("PostSwitchLog_NilDbSwitchingSnapshotLog", func(t *testing.T) {
		hdl := NewDbSnapshotHandler("tcp", "127.0.0.1", 3306, "root", "password",
			1*time.Second, 3*time.Second, 10*time.Second)
		record := &SwitchingSnapshotData{}
		err := hdl.PostSwitchLog(record)
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "dbSwitchingSnapshotLog is nil for after db switching snapshot")
	})

	t.Run("PostSwitchLog_ZeroRecordID", func(t *testing.T) {
		hdl := NewDbSnapshotHandler("tcp", "127.0.0.1", 3306, "root", "password",
			1*time.Second, 3*time.Second, 10*time.Second)
		hdl.logDb = &storage.DbhaData{}
		err := hdl.PostSwitchLog(newTestSnapshotData())
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "recordID is 0")
	})

	t.Run("PostSwitchLog_NilLogDb", func(t *testing.T) {
		hdl := NewDbSnapshotHandler("tcp", "127.0.0.1", 3306, "root", "password",
			1*time.Second, 3*time.Second, 10*time.Second)
		// Set a non-zero ID so the check passes the ID==0 guard and reaches the logDb==nil check
		record := newTestSnapshotData()
		record.DbSwitchingSnapshotLog.ID = 1
		err := hdl.PostSwitchLog(record)
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "mysql instance for after writing switch snapshot log is nil")
	})

	t.Run("Open_AlreadyOpened", func(t *testing.T) {
		hdl := NewDbSnapshotHandler("tcp", "127.0.0.1", 3306, "root", "password",
			1*time.Second, 3*time.Second, 10*time.Second)
		hdl.logDb = &storage.DbhaData{}
		err := hdl.Open()
		assert.NoError(t, err)
	})

	t.Run("CheckSwitchSnapshotTableExists_NilLogDb", func(t *testing.T) {
		hdl := NewDbSnapshotHandler("tcp", "127.0.0.1", 3306, "root", "password",
			1*time.Second, 3*time.Second, 10*time.Second)
		err := hdl.CheckSwitchSnapshotTableExists(nil)
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "mysql instance for writing switch snapshot log is nil")
	})

	t.Run("DefaultTimeouts", func(t *testing.T) {
		assert.Equal(t, 3*time.Second, SwitchSnapshotLogDefaultDbConnectTimeout)
		assert.Equal(t, 10*time.Second, SwitchSnapshotLogDefaultDbOpenCheckTimeout)
		assert.Equal(t, 1*time.Second, SwitchSnapshotLogDefaultDbWriteTimeout)
	})
}

// --- Tests for StdSnapshotHandler ---

// TestStdSnapshotHandler_PreSwitchLog_PostSwitchLog_Cycle tests the complete PreSwitchLog-PostSwitchLog cycle of StdSnapshotHandler
func TestStdSnapshotHandler_PreSwitchLog_PostSwitchLog_Cycle(t *testing.T) {
	ml := &mockLogger{}
	handler := NewStdSnapshotHandler(ml)

	for i := 1; i <= 3; i++ {
		t.Run(fmt.Sprintf("Cycle test iteration %d", i), func(t *testing.T) {
			record := newTestSnapshotData()
			record.DbSwitchingSnapshotLog.SwitchID = fmt.Sprintf("switch-std-%d", i)

			// PreSwitchLog
			ml.messages = nil
			err := handler.PreSwitchLog(record)
			if err != nil {
				t.Fatalf("PreSwitchLog failed on iteration %d: %v", i, err)
			}
			t.Logf("PreSwitchLog succeeded on iteration %d", i)
			// Verify PreSwitchLog output contains switch ID and pre-switch type
			assert.Contains(t, ml.messages[0], record.DbSwitchingSnapshotLog.SwitchID)
			assert.Contains(t, ml.messages[0], hamodel.SnapshotActionTypePreSwitch.String())

			// Simulate post-switch
			now := time.Now()
			record.DbSwitchingSnapshotLog.FinishedTime = &now
			record.DbSwitchingSnapshotLog.Result = "switching completed successfully"
			record.DbSwitchingSnapshotLog.Status = hamodel.DbSwitchingSnapshotLogStatusSuccess
			record.DbSwitchingSnapshotLog.Action = hamodel.SnapshotActionTypePostSwitch

			// PostSwitchLog
			ml.messages = nil
			err = handler.PostSwitchLog(record)
			if err != nil {
				t.Fatalf("PostSwitchLog failed on iteration %d: %v", i, err)
			}
			t.Logf("PostSwitchLog succeeded on iteration %d", i)
			// Verify PostSwitchLog output contains switch ID and post-switch type
			assert.Contains(t, ml.messages[0], record.DbSwitchingSnapshotLog.SwitchID)
			assert.Contains(t, ml.messages[0], hamodel.SnapshotActionTypePostSwitch.String())
		})
	}

	t.Log("test finished, please check if there are 6 log records in the console")
}

// TestStdSnapshotHandler_ParameterValidation tests parameter validation of StdSnapshotHandler
func TestStdSnapshotHandler_ParameterValidation(t *testing.T) {
	t.Run("NewStdSnapshotHandler", func(t *testing.T) {
		ml := &mockLogger{}
		hdl := NewStdSnapshotHandler(ml)
		assert.NotNil(t, hdl)
		assert.Equal(t, ml, hdl.logger)
	})

	t.Run("Open", func(t *testing.T) {
		hdl := NewStdSnapshotHandler(&mockLogger{})
		err := hdl.Open()
		assert.NoError(t, err)
	})

	t.Run("Close", func(t *testing.T) {
		hdl := NewStdSnapshotHandler(&mockLogger{})
		hdl.Close()
	})

	t.Run("PreSwitchLog_NilLogger", func(t *testing.T) {
		hdl := NewStdSnapshotHandler(nil)
		err := hdl.PreSwitchLog(newTestSnapshotData())
		assert.NoError(t, err)
	})

	t.Run("PreSwitchLog_NilRecord", func(t *testing.T) {
		hdl := NewStdSnapshotHandler(&mockLogger{})
		err := hdl.PreSwitchLog(nil)
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "nil")
	})

	t.Run("PreSwitchLog_NilDbSwitchingSnapshotLog", func(t *testing.T) {
		hdl := NewStdSnapshotHandler(&mockLogger{})
		record := &SwitchingSnapshotData{}
		err := hdl.PreSwitchLog(record)
		assert.Error(t, err)
	})

	t.Run("PostSwitchLog_NilLogger", func(t *testing.T) {
		hdl := NewStdSnapshotHandler(nil)
		err := hdl.PostSwitchLog(newTestSnapshotData())
		assert.NoError(t, err)
	})

	t.Run("PostSwitchLog_NilRecord", func(t *testing.T) {
		hdl := NewStdSnapshotHandler(&mockLogger{})
		err := hdl.PostSwitchLog(nil)
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "nil")
	})

	t.Run("PostSwitchLog_NilDbSwitchingSnapshotLog", func(t *testing.T) {
		hdl := NewStdSnapshotHandler(&mockLogger{})
		record := &SwitchingSnapshotData{}
		err := hdl.PostSwitchLog(record)
		assert.Error(t, err)
	})
}
