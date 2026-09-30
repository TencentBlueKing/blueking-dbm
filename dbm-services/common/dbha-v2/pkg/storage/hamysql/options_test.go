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
	"strings"
	"testing"
	"time"
)

func applyOpts(t *testing.T, opts ...Option) options {
	t.Helper()
	o := defaultOptions
	for _, opt := range opts {
		if err := opt.apply(&o); err != nil {
			t.Fatalf("apply option failed, errmsg: %s", err)
		}
	}
	return o
}

func TestBuildDSNStringBaseline(t *testing.T) {
	t.Parallel()

	cases := []struct {
		name string
		opts []Option
		want string
	}{
		{
			name: "default params",
			opts: []Option{
				OptionUser("user"),
				OptionPassword("pass"),
				OptionIP("127.0.0.1"),
				OptionPort(3306),
				OptionDBName("dbname"),
			},
			want: "user:pass@tcp(127.0.0.1:3306)/dbname?charset=utf8mb4&parseTime=true&loc=Local",
		},
		{
			name: "charset empty",
			opts: []Option{
				OptionUser("user"),
				OptionPassword("pass"),
				OptionIP("127.0.0.1"),
				OptionPort(3306),
				OptionDBName("dbname"),
				OptionCharset(""),
			},
			want: "user:pass@tcp(127.0.0.1:3306)/dbname?parseTime=true&loc=Local",
		},
		{
			name: "charset empty with timeout",
			opts: []Option{
				OptionUser("user"),
				OptionPassword("pass"),
				OptionIP("127.0.0.1"),
				OptionPort(3306),
				OptionCharset(""),
				OptionTimeout(5 * time.Second),
			},
			want: "user:pass@tcp(127.0.0.1:3306)/?parseTime=true&loc=Local&timeout=5s",
		},
		{
			name: "proxy sqlx combination",
			opts: []Option{
				OptionUser("user"),
				OptionPassword("pass"),
				OptionIP("127.0.0.1"),
				OptionPort(3306),
				OptionCharset(""),
				OptionTimeout(5 * time.Second),
			},
			want: "user:pass@tcp(127.0.0.1:3306)/?parseTime=true&loc=Local&timeout=5s",
		},
		{
			name: "receiver current combination",
			opts: []Option{
				OptionUser("user"),
				OptionPassword("pass"),
				OptionIP("127.0.0.1"),
				OptionPort(3306),
				OptionDBName("dbname"),
				OptionReadTimeout(5 * time.Second),
				OptionWriteTimeout(5 * time.Second),
			},
			want: "user:pass@tcp(127.0.0.1:3306)/dbname?charset=utf8mb4&parseTime=true&loc=Local" +
				"&readTimeout=5s&writeTimeout=5s",
		},
	}

	for _, tc := range cases {
		tc := tc
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			got := applyOpts(t, tc.opts...).DSN()
			if got != tc.want {
				t.Fatalf("DSN mismatch\nwant: %s\ngot:  %s", tc.want, got)
			}
		})
	}
}

func TestBuildDSNStringNewOptions(t *testing.T) {
	t.Parallel()

	base := []Option{
		OptionUser("user"),
		OptionPassword("pass"),
		OptionIP("127.0.0.1"),
		OptionPort(3306),
		OptionDBName("dbname"),
	}

	t.Run("interpolate params on", func(t *testing.T) {
		t.Parallel()
		opts := append(append([]Option{}, base...), OptionInterpolateParams(true))
		dsn := applyOpts(t, opts...).DSN()
		if !strings.Contains(dsn, "interpolateParams=true") {
			t.Fatalf("expected interpolateParams=true in DSN, got: %s", dsn)
		}
	})

	t.Run("interpolate params off", func(t *testing.T) {
		t.Parallel()
		opts := append(append([]Option{}, base...), OptionInterpolateParams(false))
		dsn := applyOpts(t, opts...).DSN()
		if strings.Contains(dsn, "interpolateParams") {
			t.Fatalf("did not expect interpolateParams in DSN, got: %s", dsn)
		}
	})

	t.Run("auto max allowed packet", func(t *testing.T) {
		t.Parallel()
		opts := append(append([]Option{}, base...), OptionAutoMaxAllowedPacket(true))
		dsn := applyOpts(t, opts...).DSN()
		if !strings.Contains(dsn, "maxAllowedPacket=0") {
			t.Fatalf("expected maxAllowedPacket=0 in DSN, got: %s", dsn)
		}
	})

	t.Run("auto max allowed packet wins over explicit", func(t *testing.T) {
		t.Parallel()
		opts := append(append([]Option{}, base...),
			OptionMaxAllowedPacket(1024),
			OptionAutoMaxAllowedPacket(true),
		)
		dsn := applyOpts(t, opts...).DSN()
		if !strings.Contains(dsn, "maxAllowedPacket=0") {
			t.Fatalf("expected maxAllowedPacket=0 in DSN, got: %s", dsn)
		}
		if strings.Contains(dsn, "maxAllowedPacket=1024") {
			t.Fatalf("did not expect explicit maxAllowedPacket in DSN, got: %s", dsn)
		}
	})

	t.Run("charset empty with new options stays valid", func(t *testing.T) {
		t.Parallel()
		opts := []Option{
			OptionUser("user"),
			OptionPassword("pass"),
			OptionIP("127.0.0.1"),
			OptionPort(3306),
			OptionCharset(""),
			OptionInterpolateParams(true),
			OptionAutoMaxAllowedPacket(true),
		}
		dsn := applyOpts(t, opts...).DSN()
		if strings.Contains(dsn, "?&") {
			t.Fatalf("illegal DSN with ?&, got: %s", dsn)
		}
		if !strings.Contains(dsn, "interpolateParams=true") {
			t.Fatalf("expected interpolateParams=true, got: %s", dsn)
		}
		if !strings.Contains(dsn, "maxAllowedPacket=0") {
			t.Fatalf("expected maxAllowedPacket=0, got: %s", dsn)
		}
	})
}

func TestPoolOptionsZeroDoesNotChangeDefaults(t *testing.T) {
	t.Parallel()
	o := applyOpts(t,
		OptionMaxOpenConns(0),
		OptionMaxIdleConns(0),
		OptionConnMaxLifetime(0),
	)
	if o.maxOpenConns != 0 || o.maxIdleConns != 0 || o.connMaxLifetime != 0 {
		t.Fatalf("zero pool options should stay zero, got open:%d idle:%d lifetime:%s",
			o.maxOpenConns, o.maxIdleConns, o.connMaxLifetime)
	}
}

func TestSafeDSNHidesPassword(t *testing.T) {
	t.Parallel()
	o := applyOpts(t,
		OptionUser("user"),
		OptionPassword("secret-pass"),
		OptionIP("127.0.0.1"),
		OptionPort(3306),
		OptionDBName("dbname"),
	)
	safe := o.SafeDSN()
	if strings.Contains(safe, "secret-pass") {
		t.Fatalf("SafeDSN leaked password: %s", safe)
	}
	if !strings.Contains(safe, "<secret>") {
		t.Fatalf("SafeDSN missing secret placeholder: %s", safe)
	}
}
