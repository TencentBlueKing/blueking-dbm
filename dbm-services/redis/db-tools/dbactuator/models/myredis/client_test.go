package myredis

import (
	"net"
	"regexp"
	"strconv"
	"strings"
	"sync"
	"testing"
	"time"

	"dbm-services/redis/db-tools/dbactuator/mylog"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"

	"github.com/smartystreets/goconvey/convey"
)

func TestNeedSaveConfigRewriteWorkaroundByVersion(t *testing.T) {
	mylog.UnitTestInitLog()
	convey.Convey("need save config rewrite workaround by version", t, func() {
		need, err := needSaveConfigRewriteWorkaroundByVersion("6.0.16")
		convey.So(err, convey.ShouldBeNil)
		convey.So(need, convey.ShouldBeTrue)

		need, err = needSaveConfigRewriteWorkaroundByVersion("6.2.1")
		convey.So(err, convey.ShouldBeNil)
		convey.So(need, convey.ShouldBeTrue)

		need, err = needSaveConfigRewriteWorkaroundByVersion("6.2.2")
		convey.So(err, convey.ShouldBeNil)
		convey.So(need, convey.ShouldBeFalse)

		need, err = needSaveConfigRewriteWorkaroundByVersion("7.0.0")
		convey.So(err, convey.ShouldBeNil)
		convey.So(need, convey.ShouldBeFalse)
	})
}

func TestFormatSaveConfigValue(t *testing.T) {
	mylog.UnitTestInitLog()
	convey.Convey("format save config value", t, func() {
		convey.So(formatSaveConfigValue(""), convey.ShouldEqual, `""`)
		convey.So(formatSaveConfigValue("   "), convey.ShouldEqual, `""`)
		convey.So(formatSaveConfigValue("900 1 300 10"), convey.ShouldEqual, "900 1 300 10")
		convey.So(formatSaveConfigValue(" 900 1 "), convey.ShouldEqual, "900 1")
	})
}

func unusedLocalRedisAddr(t *testing.T) string {
	t.Helper()
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("listen on random local port failed: %v", err)
	}
	addr := listener.Addr().(*net.TCPAddr)
	port := addr.Port
	if err := listener.Close(); err != nil {
		t.Fatalf("close random local listener failed: %v", err)
	}
	return net.JoinHostPort("127.0.0.1", strconv.Itoa(port))
}

func TestNewRedisClientReturnsQuicklyWithoutRetry(t *testing.T) {
	mylog.UnitTestInitLog()
	addr := unusedLocalRedisAddr(t)
	start := time.Now()

	cli, err := NewRedisClient(addr, "", 0, consts.TendisTypeRedisInstance, 200*time.Millisecond)
	if cli != nil {
		cli.Close()
	}
	if err == nil {
		t.Fatalf("expected ping once to fail for unused addr:%s", addr)
	}
	if elapsed := time.Since(start); elapsed > time.Second {
		t.Fatalf("ping once took too long: %s", elapsed)
	}
}

func TestConnectWithRetryUsesExplicitRetryBudget(t *testing.T) {
	mylog.UnitTestInitLog()
	addr := unusedLocalRedisAddr(t)
	cli := &RedisClient{
		Addr:    addr,
		DB:      0,
		DbType:  consts.TendisTypeRedisInstance,
		nodesMu: &sync.Mutex{},
	}
	start := time.Now()
	err := cli.connect(50*time.Millisecond, 180*time.Millisecond, 50*time.Millisecond)
	cli.Close()
	if err == nil {
		t.Fatalf("expected retrying connect to fail for unused addr:%s", addr)
	}
	elapsed := time.Since(start)
	if elapsed < 50*time.Millisecond {
		t.Fatalf("retrying connect did not wait for retry budget, elapsed:%s", elapsed)
	}
	if elapsed > time.Second {
		t.Fatalf("retrying connect exceeded expected test budget, elapsed:%s", elapsed)
	}
}

func TestCmdWhiteListFiltersExporterAndHandshakeMonitorLines(t *testing.T) {
	re, err := regexp.Compile("(?i)" + strings.Join(CmdWhiteList, "|"))
	if err != nil {
		t.Fatalf("CmdWhiteList is not a valid regex: %v", err)
	}

	filtered := []string{
		`1789972397.740697 [0 1.1.1.1:59888] "hello" "3"`,
		`1789096881.334293 [0 1.1.1.1:36430] "CLIENT" "SETNAME" "redis_exporter"`,
		`1789096881.334402 [0 1.1.1.1:36430] "CONFXX" "GET" "*"`,
		`1789096881.336021 [0 1.1.1.1:36430] "rocksprop" "rocksdb.levelstats"`,
		`1789096881.336309 [0 1.1.1.1:36430] "binlogsize"`,
	}
	for _, line := range filtered {
		if !re.MatchString(line) {
			t.Errorf("expected whitelist to filter monitor line: %s", line)
		}
	}

	business := `1789096881.400000 [0 1.1.1.1:12345] "get" "user:1"`
	if re.MatchString(business) {
		t.Errorf("whitelist should not filter business command: %s", business)
	}
}
