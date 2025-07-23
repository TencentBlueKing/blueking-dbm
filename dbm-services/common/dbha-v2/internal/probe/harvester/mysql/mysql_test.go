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

package mysql_test

import (
	"context"
	"dbm-services/common/dbha-v2/internal/probe/config"
	"dbm-services/common/dbha-v2/internal/probe/harvester/mysql"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
	"testing"
	"time"
)

// TestMySQLHarvest test MySQL Harvest
func TestMySQLHarvest(t *testing.T) {
	mysqlPlugin := mysql.NewMySql(
		mysql.OptionReportInterval(5),
		mysql.OptionHost("localhost"),
		mysql.OptionPort(3306),
		mysql.OptionUser("root"),
		mysql.OptionPassword(""),
	)

	ctx := context.Background()

	// start Harvest
	harvestC, err := mysqlPlugin.Harvest(ctx)
	if err != nil {
		t.Errorf("harvest mysql status failed, errmsg(%v)", err)
		return
	}

	timeout := time.After(25 * time.Second)

	// wait probe to harvest data
	for {
		select {
		case <-ctx.Done():
			t.Log("context cancelled")
			return

		case <-timeout:
			t.Log("test timeout, no data received")
			return

		case data := <-harvestC:
			if data == nil {
				t.Log("received nil data")
				continue
			}

			// valid return data struct
			t.Logf("data type: %T, data.Data type: %T", data, data.Data)
			if mysqlMetric, ok := data.Data.(*haprobe.MySQLMetric); ok {
				t.Logf(" success to receive MySQL metric: ")
				t.Logf("  host metrics: %+v", mysqlMetric.Host)
				t.Logf("  database count: %d", len(mysqlMetric.Databases))

				// show detail info of single instance
				for i, dbMetric := range mysqlMetric.Databases {
					t.Logf("  - Database %d: %+v", i+1, dbMetric)
				}
			} else {
				t.Logf(" failed to receive MySQL metric. actual type is: %T", data.Data)
			}

			// exit the test immediately after receiving the data
			// also can to delete return, wait for timeout
			return
		}
	}
}

// TestMySQLMultipleInstances test MySQL multiple instances
func TestMySQLMultipleInstances(t *testing.T) {
	// create multiple instances
	instances := []config.InstanceConfig{
		{
			Host:     "localhost",
			Port:     3306,
			User:     "root",
			Password: "",
			Name:     "mysql-3306",
		},
		{
			Host:     "localhost",
			Port:     3307,
			User:     "root",
			Password: "",
			Name:     "mysql-3307",
		},
	}

	// multi-instance mode
	mysqlPlugin := mysql.NewMySql(
		mysql.OptionReportInterval(5),
		mysql.OptionInstances(instances),
	)

	ctx := context.Background()

	// start probe to harvest data
	harvestC, err := mysqlPlugin.Harvest(ctx)
	if err != nil {
		t.Errorf("harvest mysql status failed, errmsg(%v)", err)
		return
	}

	timeout := time.After(15 * time.Second)

	for {
		select {
		case <-ctx.Done():
			t.Log("context cancelled")
			return

		case <-timeout:
			t.Log("test timeout, no data received")
			return

		case data := <-harvestC:
			if data == nil {
				t.Log("received nil data")
				continue
			}

			if mysqlMetric, ok := data.Data.(*haprobe.MySQLMetric); ok {
				t.Logf("received mysql metric data for multiple instances:")
				t.Logf("  - Host metrics: %+v", mysqlMetric.Host)
				t.Logf("  - Database count: %d", len(mysqlMetric.Databases))

				// check if all configured instances are collected
				if len(mysqlMetric.Databases) != len(instances) {
					t.Logf("warning: expected %d databases, got %d", len(instances), len(mysqlMetric.Databases))
				}

				// show detail info of single instance
				for i, dbMetric := range mysqlMetric.Databases {
					t.Logf("  - Database %d: %+v", i+1, dbMetric)
				}
			} else {
				t.Logf("received data of type: %T, value: %+v", data.Data, data.Data)
			}

			// exit the test immediately after receiving the data
			// also can to delete return, wait for timeout
			return
		}
	}
}

// TestMySQLPluginInfo test plugin info
func TestMySQLPluginInfo(t *testing.T) {
	mysqlPlugin := mysql.NewMySql(
		mysql.OptionReportInterval(10),
		mysql.OptionHost("localhost"),
		mysql.OptionPort(3306),
		mysql.OptionUser("root"),
		mysql.OptionPassword(""),
	)

	name, err := mysqlPlugin.Name()
	if err != nil {
		t.Errorf("failed to get plugin name: %v", err)
	} else {
		t.Logf("plugin name: %s", name)
	}

	version, err := mysqlPlugin.Version()
	if err != nil {
		t.Errorf("failed to get plugin version: %v", err)
	} else {
		t.Logf("plugin version: %s", version)
	}

	err = mysqlPlugin.Close()
	if err != nil {
		t.Errorf("failed to close plugin: %v", err)
	} else {
		t.Log("plugin closed successfully")
	}
}

// TestMySQLRealTimeQPS test mysql realtime qps
func TestMySQLRealTimeQPS(t *testing.T) {
	mysqlPlugin := mysql.NewMySql(
		mysql.OptionReportInterval(3),
		mysql.OptionHost("localhost"),
		mysql.OptionPort(3306),
		mysql.OptionUser("root"),
		mysql.OptionPassword(""),
	)

	ctx := context.Background()

	harvestC, err := mysqlPlugin.Harvest(ctx)
	if err != nil {
		t.Errorf("harvest mysql status failed, errmsg(%v)", err)
		return
	}

	dataCount := 0
	maxDataCount := 3

	timeout := time.After(30 * time.Second)

	for {
		select {
		case <-ctx.Done():
			t.Log("context cancelled")
			return

		case <-timeout:
			t.Log("test timeout")
			return

		case data := <-harvestC:
			if data == nil {
				t.Log("received nil data")
				continue
			}

			dataCount++
			t.Logf("received data #%d", dataCount)

			if mysqlMetric, ok := data.Data.(*haprobe.MySQLMetric); ok {
				for i, dbMetric := range mysqlMetric.Databases {
					t.Logf("  Database %d QPS metrics:", i+1)
					t.Logf("  QPS: %d", dbMetric.QPS)
					t.Logf("  TPS: %d", dbMetric.TPS)
					t.Logf("  AvgQPS: %d", dbMetric.AvgQPS)
					t.Logf("  AvgTPS: %d", dbMetric.AvgTPS)
					t.Logf("  QueryTotal: %d", dbMetric.QueryTotal)
				}
			}

			if dataCount >= maxDataCount {
				t.Log("collected enough data for QPS analysis")
				return
			}
		}
	}
}
