package scenesnapshot

import (
	"testing"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitoriteminterface"

	"github.com/go-viper/mapstructure/v2"
)

func TestInitSnapshotOptions(t *testing.T) {
	// 没开按需采集, 不填充默认值
	c := &Checker{}
	c.initSnapshotOptions()
	if c.SnapshotLongQueryTime != 0 || c.SnapshotThreadsRunning != 0 {
		t.Fatalf("should not set defaults when disabled: %+v", c)
	}

	// 保留时长和按需采集无关, 关闭时也要填默认值
	if c.SnapshotKeepHours != defaultSnapshotKeepHours {
		t.Fatalf("expect default keep hours %d, got %d",
			defaultSnapshotKeepHours, c.SnapshotKeepHours)
	}

	// 开了按需采集但没配阈值, 用默认值
	c = &Checker{SnapshotOnDemand: true}
	c.initSnapshotOptions()
	if c.SnapshotLongQueryTime != defaultSnapshotLongQueryTime {
		t.Fatalf("expect default long query time %d, got %d",
			defaultSnapshotLongQueryTime, c.SnapshotLongQueryTime)
	}
	if c.SnapshotThreadsRunning != defaultSnapshotThreadsRunning {
		t.Fatalf("expect default threads running %d, got %d",
			defaultSnapshotThreadsRunning, c.SnapshotThreadsRunning)
	}
	if c.SnapshotFreeConnections != defaultSnapshotFreeConnections {
		t.Fatalf("expect default free connections %d, got %d",
			defaultSnapshotFreeConnections, c.SnapshotFreeConnections)
	}

	// 配了阈值就用配置值
	c = &Checker{
		SnapshotOnDemand:        true,
		SnapshotLongQueryTime:   30,
		SnapshotThreadsRunning:  100,
		SnapshotFreeConnections: 50,
	}
	c.initSnapshotOptions()
	if c.SnapshotLongQueryTime != 30 || c.SnapshotThreadsRunning != 100 ||
		c.SnapshotFreeConnections != 50 {
		t.Fatalf("custom threshold overwritten: %+v", c)
	}
}

func TestNeedSnapshotAlwaysWhenDisabled(t *testing.T) {
	c := &Checker{}
	// 没开按需采集, 空 processlist 也要采集
	if !c.needSnapshotToDisk(nil) {
		t.Fatal("should always snapshot when on-demand disabled")
	}
}

func TestFindLongQuery(t *testing.T) {
	c := &Checker{SnapshotOnDemand: true}
	c.initSnapshotOptions()

	for _, cs := range []struct {
		desc      string
		processes []*mysqlProcess
		expectID  int64 // 0 表示不该命中
	}{
		{
			desc: "long query hit",
			processes: []*mysqlProcess{
				newProcess(1, "u1", "1.1.1.1:100", "db1", "Query", defaultSnapshotLongQueryTime+1,
					"Sending data", "select 1"),
			},
			expectID: 1,
		},
		{
			desc: "just on threshold not hit",
			processes: []*mysqlProcess{
				newProcess(2, "u1", "1.1.1.1:100", "db1", "Query", defaultSnapshotLongQueryTime,
					"Sending data", "select 1"),
			},
			expectID: 0,
		},
		{
			// 空闲连接 Time 再大也不算异常
			desc: "long sleep ignored",
			processes: []*mysqlProcess{
				newProcess(3, "u1", "1.1.1.1:100", "db1", "Sleep", 99999, "", ""),
			},
			expectID: 0,
		},
		{
			// 复制线程和 binlog dump 的 Time 一直很大, 必须排除
			desc: "replication ignored",
			processes: []*mysqlProcess{
				newProcess(4, "system user", "", "", "Connect", 99999, "", ""),
				newProcess(5, "repl", "1.1.1.2:100", "", "Binlog Dump GTID", 99999, "", ""),
			},
			expectID: 0,
		},
		{
			desc: "pick from mixed",
			processes: []*mysqlProcess{
				newProcess(6, "repl", "1.1.1.2:100", "", "Binlog Dump", 99999, "", ""),
				newProcess(7, "u1", "1.1.1.1:100", "db1", "Sleep", 3600, "", ""),
				newProcess(8, "u1", "1.1.1.1:100", "db1", "Query", defaultSnapshotLongQueryTime+10,
					"Sending data", "select 2"),
			},
			expectID: 8,
		},
	} {
		p := c.findLongQuery(cs.processes)
		if cs.expectID == 0 {
			if p != nil {
				t.Fatalf("%s: expect no hit, got id %d", cs.desc, p.Id.Int64)
			}
			continue
		}
		if p == nil {
			t.Fatalf("%s: expect id %d, got no hit", cs.desc, cs.expectID)
		}
		if p.Id.Int64 != cs.expectID {
			t.Fatalf("%s: expect id %d, got %d", cs.desc, cs.expectID, p.Id.Int64)
		}
	}
}

func TestFindLongQueryExcludeUser(t *testing.T) {
	c := &Checker{
		SnapshotOnDemand:             true,
		SnapshotLongQueryExcludeUser: []string{"dba_backup", " Checksum "},
	}
	c.initSnapshotOptions()

	// 被排除的 user, 跑多久都不触发
	excluded := []*mysqlProcess{
		newProcess(1, "dba_backup", "1.1.1.1:100", "db1", "Query", 99999, "Sending data", "select 1"),
		newProcess(2, "DBA_Backup", "1.1.1.1:100", "db1", "Query", 99999, "Sending data", "select 1"),
		newProcess(3, "checksum", "1.1.1.1:100", "db1", "Query", 99999, "Sending data", "select 1"),
	}
	if p := c.findLongQuery(excluded); p != nil {
		t.Fatalf("excluded user should not hit, got id %d user %s", p.Id.Int64, p.User.String)
	}

	// 没被排除的 user 照常触发
	mixed := append(excluded, newProcess(4, "app1", "1.1.1.1:100", "db1", "Query",
		defaultSnapshotLongQueryTime+1, "Sending data", "select 2"))
	p := c.findLongQuery(mixed)
	if p == nil || p.Id.Int64 != 4 {
		t.Fatalf("expect id 4, got %+v", p)
	}
}

func TestDecodeSnapshotOptions(t *testing.T) {
	opts := monitoriteminterface.ItemOptions{
		"snapshot_on_demand":               true,
		"snapshot_long_query_time":         30,
		"snapshot_long_query_exclude_user": []interface{}{"dba_backup", "checksum"},
		"snapshot_threads_running":         100,
		"snapshot_free_connections":        20,
	}

	var c Checker
	if err := mapstructure.Decode(opts, &c); err != nil {
		t.Fatal(err)
	}
	if !c.SnapshotOnDemand {
		t.Fatal("snapshot on demand should be enabled")
	}
	if c.SnapshotLongQueryTime != 30 {
		t.Fatalf("expect long query time 30, got %d", c.SnapshotLongQueryTime)
	}
	if c.SnapshotThreadsRunning != 100 {
		t.Fatalf("expect threads running 100, got %d", c.SnapshotThreadsRunning)
	}
	if c.SnapshotFreeConnections != 20 {
		t.Fatalf("expect free connections 20, got %d", c.SnapshotFreeConnections)
	}
	if len(c.SnapshotLongQueryExcludeUser) != 2 ||
		c.SnapshotLongQueryExcludeUser[0] != "dba_backup" ||
		c.SnapshotLongQueryExcludeUser[1] != "checksum" {
		t.Fatalf("unexpected exclude user: %v", c.SnapshotLongQueryExcludeUser)
	}
}
