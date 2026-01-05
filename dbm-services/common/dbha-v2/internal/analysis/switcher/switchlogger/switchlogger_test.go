/**
 * MIT License
 *
 * Copyright (c) 2023 Tencent BlueKing
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

package switchlogger

import (
	"fmt"
	"os"
	"strconv"
	"testing"
	"time"

	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
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

// TestLogToDbHandler tests complete open-close cycle
func TestLogToDbHandler(t *testing.T) {
	for i := 1; i <= 3; i++ {
		t.Run(fmt.Sprintf("Cycle test iteration %d", i), func(t *testing.T) {
			handler := NewLogToDbHandler("tcp", testConfig.IP, testConfig.Port, testConfig.User, testConfig.Passwd)

			// Open connection
			err := handler.Open()
			if err != nil {
				t.Fatalf("Open failed on iteration %d: %v", i, err)
			}
			t.Logf("Open succeeded on iteration %d", i)

			// Write test record
			record := &hamodel.DbSwitchingLog{
				BkBizID:     123,
				BkCloudID:   0,
				DbIP:        "127.0.0.1",
				DbPort:      3306,
				ClusterName: "test-cluster",
				DbTypeName:  "mysql",
				Level:       "info",
				Content:     fmt.Sprintf("test record %d", i),
				CreatedTime: time.Now(),
			}

			err = handler.Append(record)
			if err != nil {
				t.Fatalf("Append failed on iteration %d: %v", i, err)
			}
			t.Logf("Append succeeded on iteration %d", i)

			// Close connection
			handler.Close()
		})
	}

	t.Log("Complete open-close cycle test finished, please check if there are 3 test records in the database")
}

// TestLogToStdHandler tests the default switch logger
func TestLogToStdHandler(t *testing.T) {
	for i := 1; i <= 3; i++ {
		t.Run(fmt.Sprintf("Cycle test iteration %d", i), func(t *testing.T) {
			handler := NewLogToStdHandler()

			// Write test record
			record := &hamodel.DbSwitchingLog{
				BkBizID:     123,
				BkCloudID:   0,
				DbIP:        "127.0.0.1",
				DbPort:      3306,
				ClusterName: "test-cluster",
				DbTypeName:  "mysql",
				Level:       "info",
				Content:     fmt.Sprintf("test record %d", i),
				CreatedTime: time.Now(),
			}

			err := handler.Append(record)
			if err != nil {
				t.Fatalf("Append failed on iteration %d: %v", i, err)
			}
			t.Logf("Append succeeded on iteration %d", i)
		})
	}

	t.Log("test finished, please check if there are 3 test records in the console")
}
