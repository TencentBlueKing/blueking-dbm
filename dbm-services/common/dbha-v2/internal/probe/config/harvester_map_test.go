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

package config_test

import (
	"os"
	"path/filepath"
	"testing"
	"time"

	"dbm-services/common/dbha-v2/internal/probe/config"
)

func TestLoad_HarvesterMapNamedBlocks(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "probe.yaml")
	content := `
name: probe
harvester:
  mysql:
    user: mysql_user
    password: mysql_pwd
    interval: 20s
    timeout: 5s
    endpoints:
      - ip: 127.0.0.1
        ports: ["3306"]
        clusterType: tendbha
        machineType: backend
        accessLayer: storage
        proto: tcp
  mysqlProxyAdmin:
    user: proxy_user
    password: proxy_pwd
    interval: 20s
    timeout: 5s
    endpoints:
      - ip: 127.0.0.2
        adminPorts: ["33060"]
        clusterType: tendbha
        machineType: proxy
        accessLayer: proxy
        proto: tcp
  redis:
    user: redis_user
    password: redis_pwd
    interval: 15s
    timeout: 3s
    endpoints:
      - ip: 127.0.0.3
        ports: ["6379"]
        clusterType: RedisInstance
        machineType: tendiscache
        accessLayer: storage
        proto: tcp
`
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatalf("write config failed, errmsg: %s", err)
	}
	if err := config.Load(path); err != nil {
		t.Fatalf("load config failed, errmsg: %s", err)
	}

	mysql := config.Cfg.Harvester.Block(config.HarvesterBlockMySQL)
	if mysql == nil || mysql.User != "mysql_user" || len(mysql.Endpoints) != 1 {
		t.Fatalf("unexpected mysql block: %+v", mysql)
	}
	if mysql.Interval != 20*time.Second || mysql.Timeout != 5*time.Second {
		t.Fatalf("unexpected mysql timing: interval=%s timeout=%s", mysql.Interval, mysql.Timeout)
	}
	if !config.Cfg.Harvester.HasEndpoints(config.HarvesterBlockMySQLProxyAdmin) {
		t.Fatal("expected mysqlProxyAdmin endpoints")
	}
	redis := config.Cfg.Harvester.Block(config.HarvesterBlockRedis)
	if redis == nil || redis.User != "redis_user" || len(redis.Endpoints) != 1 {
		t.Fatalf("unexpected redis block: %+v", redis)
	}
}

func TestLoad_ExtraHarvesterCamelCaseBlock(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "probe.yaml")
	content := `
name: probe
harvester:
  myNewDb:
    user: new_user
    password: new_pwd
    interval: 20s
    timeout: 5s
    endpoints:
      - ip: 127.0.0.31
        ports: ["9092"]
        clusterType: kafka
        machineType: broker
        accessLayer: storage
        proto: tcp
`
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatalf("write config failed, errmsg: %s", err)
	}
	if err := config.Load(path); err != nil {
		t.Fatalf("load config failed, errmsg: %s", err)
	}

	for _, name := range []string{"myNewDb", "mynewdb", "MYNEWDB"} {
		block := config.Cfg.Harvester.Block(name)
		if block == nil || block.User != "new_user" || len(block.Endpoints) != 1 {
			t.Fatalf("Block(%q) unexpected: %+v", name, block)
		}
	}
	for key := range config.Cfg.Harvester.Extra {
		if key != "mynewdb" {
			t.Fatalf("Extra key %q is not normalized", key)
		}
	}
}
