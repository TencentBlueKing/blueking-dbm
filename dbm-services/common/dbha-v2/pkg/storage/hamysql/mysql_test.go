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
