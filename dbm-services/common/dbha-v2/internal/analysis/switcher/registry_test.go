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

package switcher

import (
	"context"
	"testing"

	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

type fakeSwitcher struct {
	dbType haprobe.DbType
}

func (f *fakeSwitcher) DbTypeName() haprobe.DbType {
	return f.dbType
}

func (f *fakeSwitcher) AlarmEvents() AlarmEvents {
	return AlarmEvents{
		Success: haprobe.DbEventNameMysqlSwitchSuccessV1,
		Failure: haprobe.DbEventNameMysqlSwitchFailureV1,
	}
}

func (f *fakeSwitcher) Switch(_ context.Context, _ *Request) *Response {
	return &Response{}
}

func TestRegisterNilFactory(t *testing.T) {
	registry := NewRegistry()

	err := registry.Register(haprobe.DbTypeMySql, nil)
	if err == nil {
		t.Fatalf("expected error for nil factory")
	}
}

func TestRegisterDuplicateDbType(t *testing.T) {
	registry := NewRegistry()

	err := registry.Register(haprobe.DbTypeMySql, func() Switcher {
		return &fakeSwitcher{dbType: haprobe.DbTypeMySql}
	})
	if err != nil {
		t.Fatalf("register mysql factory failed, errmsg: %s", err)
	}

	err = registry.Register(haprobe.DbTypeMySql, func() Switcher {
		return &fakeSwitcher{dbType: haprobe.DbTypeMySql}
	})
	if err == nil {
		t.Fatalf("expected duplicate registration error")
	}
}

func TestBuildEnabledFiltersDisabledDbTypes(t *testing.T) {
	registry := NewRegistry()
	for _, dbType := range []haprobe.DbType{haprobe.DbTypeMySql, haprobe.DbTypeRedis} {
		typ := dbType
		err := registry.Register(typ, func() Switcher {
			return &fakeSwitcher{dbType: typ}
		})
		if err != nil {
			t.Fatalf("register dbType %s failed, errmsg: %s", typ, err)
		}
	}

	switchers := registry.BuildEnabled([]haprobe.DbType{haprobe.DbTypeRedis})

	if _, ok := switchers[haprobe.DbTypeRedis]; ok {
		t.Fatalf("redis switcher should be disabled")
	}
	if _, ok := switchers[haprobe.DbTypeMySql]; !ok {
		t.Fatalf("mysql switcher should be enabled")
	}
}

func TestNewDefaultRegistryContainsMysqlAndRedis(t *testing.T) {
	registry, err := NewDefaultRegistry()
	if err != nil {
		t.Fatalf("new default registry failed, errmsg: %s", err)
	}

	switchers := registry.BuildEnabled(nil)
	if _, ok := switchers[haprobe.DbTypeMySql]; !ok {
		t.Fatalf("mysql switcher should exist in default registry")
	}
	if _, ok := switchers[haprobe.DbTypeRedis]; !ok {
		t.Fatalf("redis switcher should exist in default registry")
	}
}

func TestDefaultSwitcherAlarmEvents(t *testing.T) {
	mysqlEvents := (&Mysql{}).AlarmEvents()
	if mysqlEvents.Success != haprobe.DbEventNameMysqlSwitchSuccessV1 {
		t.Fatalf("unexpected mysql success event: %s", mysqlEvents.Success)
	}
	if mysqlEvents.Failure != haprobe.DbEventNameMysqlSwitchFailureV1 {
		t.Fatalf("unexpected mysql failure event: %s", mysqlEvents.Failure)
	}

	redisEvents := (&Redis{}).AlarmEvents()
	if redisEvents.Success != haprobe.DbEventNameRedisSwitchSuccessV1 {
		t.Fatalf("unexpected redis success event: %s", redisEvents.Success)
	}
	if redisEvents.Failure != haprobe.DbEventNameRedisSwitchFailureV1 {
		t.Fatalf("unexpected redis failure event: %s", redisEvents.Failure)
	}
}
