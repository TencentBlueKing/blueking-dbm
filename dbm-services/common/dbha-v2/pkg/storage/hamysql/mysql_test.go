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

package hamysql_test

import (
	"context"
	"errors"
	"log"
	"os"
	"strconv"
	"testing"
	"time"

	"dbm-services/common/dbha-v2/pkg/storage/hamysql"
)

type timeoutTestConfig struct {
	host           string
	port           int
	user           string
	password       string
	sqlText        string
	connectTimeout time.Duration
	execTimeout    time.Duration
}

func getTimeoutTestConfig(t *testing.T) timeoutTestConfig {
	t.Helper()

	host := os.Getenv("DBHA_MYSQL_TIMEOUT_HOST")
	portStr := os.Getenv("DBHA_MYSQL_TIMEOUT_PORT")
	user := os.Getenv("DBHA_MYSQL_TIMEOUT_USER")
	password := os.Getenv("DBHA_MYSQL_TIMEOUT_PASSWORD")
	sqlText := os.Getenv("DBHA_MYSQL_TIMEOUT_SQL")
	connectTimeoutStr := os.Getenv("DBHA_MYSQL_CONNECT_TIMEOUT")
	execTimeoutStr := os.Getenv("DBHA_MYSQL_EXEC_TIMEOUT")

	port, err := strconv.Atoi(portStr)
	if err != nil {
		t.Fatalf("invalid timeout port(%s), errmsg(%s)", portStr, err)
	}
	connectTimeout, err := time.ParseDuration(connectTimeoutStr)
	if err != nil {
		t.Fatalf("invalid connect timeout(%s), errmsg(%s)", connectTimeoutStr, err)
	}
	execTimeout, err := time.ParseDuration(execTimeoutStr)
	if err != nil {
		t.Fatalf("invalid exec timeout(%s), errmsg(%s)", execTimeoutStr, err)
	}

	return timeoutTestConfig{
		host:           host,
		port:           port,
		user:           user,
		password:       password,
		sqlText:        sqlText,
		connectTimeout: connectTimeout,
		execTimeout:    execTimeout,
	}
}

func TestNew(t *testing.T) {
	endpoints := os.Getenv("DBHA_MYSQL_ENDPOINTS")
	user := os.Getenv("DBHA_MYSQL_USER")
	password := os.Getenv("DBHA_MYSQL_PASSWORD")

	log.Println("endpoints:", endpoints)
	log.Println("user:", user)
	log.Println("password:", password)

	hadb, err := hamysql.NewGormDB()
	if err != nil {
		t.Fatalf("create mysql instance failed, errmsg(%v)", err)
	}

	tables, err := hadb.DB().Migrator().GetTables()
	if err != nil {
		t.Fatalf("failed to get all tables, errmsg(%s)", err)
	}

	for _, table := range tables {
		t.Logf("table(%s)", table)
	}

}

func TestSqlxDBForProxy(t *testing.T) {
	host := os.Getenv("PROXY_HOST")
	port, err := strconv.Atoi(os.Getenv("PROXY_PORT"))
	if err != nil {
		t.Fatalf("invalid port(%s), errmsg(%s)", os.Getenv("PROXY_PORT"), err)
	}
	user := os.Getenv("PROXY_USER")
	password := os.Getenv("PROXY_PASSWORD")

	log.Println("host:", host)
	log.Println("port:", port)
	log.Println("user:", user)
	log.Println("password:", password)

	log.Println("This mysql connection configuration is designed for proxy or tdbctl node only, " +
		"make sure there is no extra sql is executed when building this connection")
	proxyDB, err := hamysql.NewSqlxDB(
		hamysql.OptionProto("tcp"),
		hamysql.OptionIP(host),
		hamysql.OptionPort(port),
		hamysql.OptionUser(user),
		hamysql.OptionPassword(password),
		hamysql.OptionCharset(""),
	)
	if err != nil {
		t.Fatalf("failed to connect to proxy(%s:%d), errmsg: %s",
			host, port, err.Error())
	}

	defer proxyDB.Close()

	// test query
	var version []string
	if err := proxyDB.DB().Select(&version, "SELECT VERSION()"); err != nil {
		t.Fatalf("failed to query version, errmsg: %s", err)
	}
	log.Println("proxy version: ", version[0])
}

func TestGormDBTimeout(t *testing.T) {
	cfg := getTimeoutTestConfig(t)

	log.Println("host:", cfg.host)
	log.Println("port:", cfg.port)
	log.Println("user:", cfg.user)
	log.Println("password:", cfg.password)
	log.Println("sql:", cfg.sqlText)
	log.Println("connect timeout:", cfg.connectTimeout)
	log.Println("exec timeout:", cfg.execTimeout)

	start := time.Now()

	db, err := hamysql.NewGormDB(
		hamysql.OptionProto("tcp"),
		hamysql.OptionIP(cfg.host),
		hamysql.OptionPort(cfg.port),
		hamysql.OptionUser(cfg.user),
		hamysql.OptionPassword(cfg.password),
		hamysql.OptionTimeout(cfg.connectTimeout),
	)
	if err != nil {
		elapsed := time.Since(start)
		log.Printf("gorm create failed, timeout=%t, err=%v, elapsed=%s",
			os.IsTimeout(err) || errors.Is(err, context.DeadlineExceeded), err, elapsed)
		return
	}
	defer db.Close()

	ctx, cancel := context.WithTimeout(context.Background(), cfg.execTimeout)
	defer cancel()

	err = db.DBWithContext(ctx).Exec(cfg.sqlText).Error
	elapsed := time.Since(start)
	log.Printf("gorm exec success=%t, timeout=%t, ctxErr=%v, err=%v, elapsed=%s",
		err == nil,
		os.IsTimeout(err) || errors.Is(err, context.DeadlineExceeded) || errors.Is(ctx.Err(), context.DeadlineExceeded),
		ctx.Err(),
		err,
		elapsed,
	)
}

func TestSqlxDBTimeout(t *testing.T) {
	cfg := getTimeoutTestConfig(t)

	log.Println("host:", cfg.host)
	log.Println("port:", cfg.port)
	log.Println("user:", cfg.user)
	log.Println("password:", cfg.password)
	log.Println("sql:", cfg.sqlText)
	log.Println("connect timeout:", cfg.connectTimeout)
	log.Println("exec timeout:", cfg.execTimeout)

	start := time.Now()

	db, err := hamysql.NewSqlxDB(
		hamysql.OptionProto("tcp"),
		hamysql.OptionIP(cfg.host),
		hamysql.OptionPort(cfg.port),
		hamysql.OptionUser(cfg.user),
		hamysql.OptionPassword(cfg.password),
		hamysql.OptionTimeout(cfg.connectTimeout),
	)
	if err != nil {
		elapsed := time.Since(start)
		log.Printf("sqlx create failed, timeout=%t, err=%v, elapsed=%s",
			os.IsTimeout(err) || errors.Is(err, context.DeadlineExceeded), err, elapsed)
		return
	}
	defer db.Close()

	ctx, cancel := context.WithTimeout(context.Background(), cfg.execTimeout)
	defer cancel()

	_, err = db.DB().ExecContext(ctx, cfg.sqlText)
	elapsed := time.Since(start)
	log.Printf("sqlx exec success=%t, timeout=%t, ctxErr=%v, err=%v, elapsed=%s",
		err == nil,
		os.IsTimeout(err) || errors.Is(err, context.DeadlineExceeded) || errors.Is(ctx.Err(), context.DeadlineExceeded),
		ctx.Err(),
		err,
		elapsed,
	)
}

// switchConnectTimeout matches switchcore.DbConnectTimeout when the config value is unset.
const switchConnectTimeout = 10 * time.Second

type endpointTestConfig struct {
	host     string
	port     int
	user     string
	password string
	sql1     string
	sql2     string
}

func getEndpointTestConfig(t *testing.T, prefix string) endpointTestConfig {
	t.Helper()

	host := os.Getenv(prefix + "_HOST")
	portStr := os.Getenv(prefix + "_PORT")
	user := os.Getenv(prefix + "_USER")
	password := os.Getenv(prefix + "_PASSWORD")
	port, err := strconv.Atoi(portStr)
	if err != nil {
		t.Fatalf("invalid %s port(%s), errmsg(%s)", prefix, portStr, err)
	}

	return endpointTestConfig{
		host:     host,
		port:     port,
		user:     user,
		password: password,
		sql1:     os.Getenv(prefix + "_SQL1"),
		sql2:     os.Getenv(prefix + "_SQL2"),
	}
}

// TestSwitchConnectTdbctl opens a tdbctl connection with the same options as
// TdbctlOperator.ConnectTdbctlNode, then runs TDBCTL_SQL1 and TDBCTL_SQL2.
// An empty SQL is skipped.
func TestSwitchConnectTdbctl(t *testing.T) {
	cfg := getEndpointTestConfig(t, "TDBCTL")

	log.Println("host:", cfg.host)
	log.Println("port:", cfg.port)
	log.Println("user:", cfg.user)
	log.Println("password:", cfg.password)
	log.Println("sql1:", cfg.sql1)
	log.Println("sql2:", cfg.sql2)
	log.Println("connect timeout:", switchConnectTimeout)

	start := time.Now()
	db, err := hamysql.NewGormDB(
		hamysql.OptionProto("tcp"),
		hamysql.OptionIP(cfg.host),
		hamysql.OptionPort(cfg.port),
		hamysql.OptionUser(cfg.user),
		hamysql.OptionPassword(cfg.password),
		hamysql.OptionTimeout(switchConnectTimeout),
		hamysql.OptionSkipInitializeWithVersion(false),
		hamysql.OptionDisableDatetimePrecision(true),
		hamysql.OptionCharset(""),
	)
	elapsed := time.Since(start)
	if err != nil {
		t.Fatalf("connect tdbctl(%s:%d) failed, elapsed=%s, errmsg: %s",
			cfg.host, cfg.port, elapsed, err.Error())
	}
	defer db.Close()

	log.Printf("connect tdbctl(%s:%d) success, elapsed=%s", cfg.host, cfg.port, elapsed)

	if cfg.sql1 != "" {
		ctx, cancel := context.WithTimeout(context.Background(), switchConnectTimeout)
		err = db.DBWithContext(ctx).Exec(cfg.sql1).Error
		cancel()
		if err != nil {
			t.Fatalf("exec tdbctl sql1 failed, sql=%s, errmsg: %s", cfg.sql1, err.Error())
		}
		log.Printf("exec tdbctl sql1 success, sql=%s", cfg.sql1)
	}
	if cfg.sql2 != "" {
		ctx, cancel := context.WithTimeout(context.Background(), switchConnectTimeout)
		err = db.DBWithContext(ctx).Exec(cfg.sql2).Error
		cancel()
		if err != nil {
			t.Fatalf("exec tdbctl sql2 failed, sql=%s, errmsg: %s", cfg.sql2, err.Error())
		}
		log.Printf("exec tdbctl sql2 success, sql=%s", cfg.sql2)
	}
}

// TestSwitchConnectProxy opens a mysql-proxy admin connection with the same
// options as ProxyRefreshBackends, then runs PROXY_SQL1 and PROXY_SQL2.
// An empty SQL is skipped. NewSqlxDB itself runs "select version()".
func TestSwitchConnectProxy(t *testing.T) {
	cfg := getEndpointTestConfig(t, "PROXY")

	log.Println("host:", cfg.host)
	log.Println("port:", cfg.port)
	log.Println("user:", cfg.user)
	log.Println("password:", cfg.password)
	log.Println("sql1:", cfg.sql1)
	log.Println("sql2:", cfg.sql2)
	log.Println("connect timeout:", switchConnectTimeout)

	start := time.Now()
	db, err := hamysql.NewSqlxDB(
		hamysql.OptionIP(cfg.host),
		hamysql.OptionPort(cfg.port),
		hamysql.OptionUser(cfg.user),
		hamysql.OptionPassword(cfg.password),
		hamysql.OptionCharset(""),
		hamysql.OptionTimeout(switchConnectTimeout),
	)
	elapsed := time.Since(start)
	if err != nil {
		t.Fatalf("connect proxy(%s:%d) failed, elapsed=%s, errmsg: %s",
			cfg.host, cfg.port, elapsed, err.Error())
	}
	defer db.Close()

	log.Printf("connect proxy(%s:%d) success, elapsed=%s", cfg.host, cfg.port, elapsed)

	if cfg.sql1 != "" {
		ctx, cancel := context.WithTimeout(context.Background(), switchConnectTimeout)
		_, err = db.DB().ExecContext(ctx, cfg.sql1)
		cancel()
		if err != nil {
			t.Fatalf("exec proxy sql1 failed, sql=%s, errmsg: %s", cfg.sql1, err.Error())
		}
		log.Printf("exec proxy sql1 success, sql=%s", cfg.sql1)
	}
	if cfg.sql2 != "" {
		ctx, cancel := context.WithTimeout(context.Background(), switchConnectTimeout)
		_, err = db.DB().ExecContext(ctx, cfg.sql2)
		cancel()
		if err != nil {
			t.Fatalf("exec proxy sql2 failed, sql=%s, errmsg: %s", cfg.sql2, err.Error())
		}
		log.Printf("exec proxy sql2 success, sql=%s", cfg.sql2)
	}
}

func TestNewGormDBWithTimeoutRejectsConflictingOptions(t *testing.T) {
	_, err := hamysql.NewGormDBWithTimeout(hamysql.OptionSkipInitializeWithVersion(false))
	if err == nil {
		t.Fatal("expected error when SkipInitializeWithVersion is false")
	}
	log.Printf("SkipInitializeWithVersion(false) rejected, errmsg: %s", err)

	_, err = hamysql.NewGormDBWithTimeout(hamysql.OptionAutoSelectVersion(false))
	if err == nil {
		t.Fatal("expected error when AutoSelectVersion is false")
	}
	log.Printf("AutoSelectVersion(false) rejected, errmsg: %s", err)
}

func TestNewGormDBWithTimeoutTdbctlOptions(t *testing.T) {
	// Same options as ConnectTdbctlNode, except SkipInitializeWithVersion stays true
	// so OptionTimeout covers the connect. Charset is empty, so there is no SET NAMES.
	cfg := getEndpointTestConfig(t, "TDBCTL")

	db, err := hamysql.NewGormDBWithTimeout(
		hamysql.OptionProto("tcp"),
		hamysql.OptionIP(cfg.host),
		hamysql.OptionPort(cfg.port),
		hamysql.OptionUser(cfg.user),
		hamysql.OptionPassword(cfg.password),
		hamysql.OptionTimeout(switchConnectTimeout),
		hamysql.OptionDisableDatetimePrecision(true),
		hamysql.OptionCharset(""),
	)
	if err != nil {
		t.Fatalf("connect tdbctl(%s:%d) failed, errmsg: %s", cfg.host, cfg.port, err)
	}
	defer db.Close()

	version, err := db.Version(context.Background())
	if err != nil {
		t.Fatalf("version: %s", err)
	}
	log.Printf("connect tdbctl(%s:%d) with timeout wrapper, version=%s", cfg.host, cfg.port, version)
}

func TestNewGormDBWithTimeoutBusyConnect(t *testing.T) {
	// Charset causes SET NAMES. AutoMaxAllowedPacket causes SELECT @@max_allowed_packet.
	// AutoSelectVersion is forced, so SELECT VERSION() runs after connect.
	cfg := getEndpointTestConfig(t, "TDBCTL")

	db, err := hamysql.NewGormDBWithTimeout(
		hamysql.OptionProto("tcp"),
		hamysql.OptionIP(cfg.host),
		hamysql.OptionPort(cfg.port),
		hamysql.OptionUser(cfg.user),
		hamysql.OptionPassword(cfg.password),
		hamysql.OptionTimeout(switchConnectTimeout),
		hamysql.OptionCharset("utf8mb4"),
		hamysql.OptionAutoMaxAllowedPacket(true),
		hamysql.OptionParseTime(true),
		hamysql.OptionLoc("Local"),
		hamysql.OptionReadTimeout(switchConnectTimeout),
		hamysql.OptionWriteTimeout(switchConnectTimeout),
		hamysql.OptionInterpolateParams(true),
		hamysql.OptionDisableDatetimePrecision(true),
	)
	if err != nil {
		t.Fatalf("connect tdbctl(%s:%d) failed, errmsg: %s", cfg.host, cfg.port, err)
	}
	defer db.Close()

	version, err := db.Version(context.Background())
	if err != nil {
		t.Fatalf("version: %s", err)
	}
	log.Printf("busy connect tdbctl(%s:%d), version=%s", cfg.host, cfg.port, version)
}
