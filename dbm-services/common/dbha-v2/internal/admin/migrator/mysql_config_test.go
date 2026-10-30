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

package migrator

import (
	"strings"
	"testing"
	"time"

	"github.com/go-sql-driver/mysql"
)

func TestMigrateMySQLConfigKeepsConnectTimeoutOnly(t *testing.T) {
	cfg := migrateMySQLConfig("migrate_user", "secret", "tcp", "127.0.0.1:3306")
	if cfg.Params["timeout"] != "10s" {
		t.Fatalf("connect timeout: %s", cfg.Params["timeout"])
	}
	if _, ok := cfg.Params["readTimeout"]; ok {
		t.Fatal("read timeout is set")
	}
	if _, ok := cfg.Params["writeTimeout"]; ok {
		t.Fatal("write timeout is set")
	}
	parsed, err := mysql.ParseDSN(cfg.FormatDSN())
	if err != nil {
		t.Fatal(err)
	}
	if parsed.Timeout != 10*time.Second || parsed.ReadTimeout != 0 || parsed.WriteTimeout != 0 {
		t.Fatal("parsed migrate timeouts are not connect-only")
	}
	if strings.Contains(parsed.FormatDSN(), "readTimeout") || strings.Contains(parsed.FormatDSN(), "writeTimeout") {
		t.Fatal("dsn contains a read or write timeout")
	}
}

// Migration connections must parse and write times in UTC so server NOW() literals round-trip
// unchanged; a local zone with DST would shift literals that fall in its gap hour.
func TestMigrateMySQLConfigUsesUTC(t *testing.T) {
	cfg := migrateMySQLConfig("migrate_user", "secret", "tcp", "127.0.0.1:3306")
	if cfg.Loc != time.UTC {
		t.Fatalf("migrate loc is not utc, loc: %s", cfg.Loc)
	}
	parsed, err := mysql.ParseDSN(cfg.FormatDSN())
	if err != nil {
		t.Fatal(err)
	}
	if parsed.Loc != time.UTC {
		t.Fatalf("parsed migrate loc is not utc, loc: %s", parsed.Loc)
	}
}
