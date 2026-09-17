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

package dbcred

import (
	"context"
	"errors"
	"testing"

	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

var errConfigureBoom = errors.New("configure boom")

type fakeProvider struct{}

func (p *fakeProvider) Fill(_ context.Context, _ int, _ []*Item) error { return nil }

type flakyProvider struct {
	err error
}

func (p *flakyProvider) Fill(_ context.Context, _ int, _ []*Item) error { return nil }

func (p *flakyProvider) Configure(_ ConfigLookup) error {
	return p.err
}

// snapshotForTest captures registry and unconfigured and returns a restore func.
func snapshotForTest() func() {
	mu.Lock()
	reg := make(map[haprobe.DbType]Resolver, len(registry))
	for k, v := range registry {
		reg[k] = v
	}
	unc := make(map[haprobe.DbType]struct{}, len(unconfigured))
	for k := range unconfigured {
		unc[k] = struct{}{}
	}
	mu.Unlock()

	return func() {
		mu.Lock()
		registry = reg
		unconfigured = unc
		mu.Unlock()
	}
}

func TestRegisterPanicsOnInvalidDbType(t *testing.T) {
	t.Cleanup(snapshotForTest())
	assertPanics(t, func() { Register(haprobe.DbTypeNone, &fakeProvider{}) })
}

func TestRegisterPanicsOnNilProvider(t *testing.T) {
	t.Cleanup(snapshotForTest())
	assertPanics(t, func() { Register(haprobe.DbTypeRedis, nil) })
}

func TestRegisterPanicsOnDuplicate(t *testing.T) {
	t.Cleanup(snapshotForTest())
	Register(haprobe.DbTypeRedis, &fakeProvider{})
	assertPanics(t, func() { Register(haprobe.DbTypeRedis, &fakeProvider{}) })
}

func TestLookupUnregisteredReturnsFalse(t *testing.T) {
	t.Cleanup(snapshotForTest())
	if _, ok := Lookup(haprobe.DbTypeMongo); ok {
		t.Fatal("expected lookup of unregistered dbtype to return false")
	}
}

func TestRegisteredDbTypesSorted(t *testing.T) {
	t.Cleanup(snapshotForTest())
	Register(haprobe.DbTypeRedis, &fakeProvider{})
	Register(haprobe.DbTypeMongo, &fakeProvider{})

	got := RegisteredDbTypes()
	want := []haprobe.DbType{haprobe.DbTypeMongo, haprobe.DbTypeRedis}
	if len(got) != len(want) {
		t.Fatalf("RegisteredDbTypes() = %v, want %v", got, want)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("RegisteredDbTypes() = %v, want sorted %v", got, want)
		}
	}
}

func TestConfigureAllRemovesUnconfiguredOnSuccess(t *testing.T) {
	t.Cleanup(snapshotForTest())

	dt := haprobe.DbTypeRedis
	p := &flakyProvider{err: errConfigureBoom}
	Register(dt, p)

	ConfigureAll(func(string) (DbmApi, bool) { return DbmApi{}, false })
	if got := UnconfiguredDbTypes(); len(got) != 1 || got[0] != dt {
		t.Fatalf("expected %s unconfigured, got: %v", dt, got)
	}

	p.err = nil
	ConfigureAll(func(string) (DbmApi, bool) { return DbmApi{}, false })
	if got := UnconfiguredDbTypes(); len(got) != 0 {
		t.Fatalf("expected unconfigured cleared after success, got: %v", got)
	}
}

func TestConfigureAllSkipsNonConfigurer(t *testing.T) {
	t.Cleanup(snapshotForTest())
	Register(haprobe.DbTypeRedis, &fakeProvider{})
	ConfigureAll(func(string) (DbmApi, bool) { return DbmApi{}, false })
	if got := UnconfiguredDbTypes(); len(got) != 0 {
		t.Fatalf("non-configurer must not be marked unconfigured, got: %v", got)
	}
}

func assertPanics(t *testing.T, fn func()) {
	t.Helper()
	defer func() {
		if recover() == nil {
			t.Fatal("expected panic")
		}
	}()
	fn()
}
