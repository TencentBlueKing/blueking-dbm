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

package detection

import (
	"testing"

	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

type fakeDetectable struct {
	dbType haprobe.DbType
}

func (f fakeDetectable) DbTypeName() haprobe.DbType { return f.dbType }

// snapshotForTest captures detectables and returns a restore func.
func snapshotForTest() func() {
	mu.Lock()
	saved := make(map[haprobe.DbType]Detectable, len(detectables))
	for k, v := range detectables {
		saved[k] = v
	}
	mu.Unlock()

	return func() {
		mu.Lock()
		detectables = saved
		mu.Unlock()
	}
}

// resetForTest empties the registry and restores it when the test finishes.
func resetForTest(t *testing.T) {
	t.Helper()
	t.Cleanup(snapshotForTest())
	mu.Lock()
	detectables = map[haprobe.DbType]Detectable{}
	mu.Unlock()
}

func assertPanics(t *testing.T, fn func()) {
	t.Helper()
	defer func() {
		if r := recover(); r == nil {
			t.Fatal("expected panic")
		}
	}()
	fn()
}

func TestRegisterPanicsOnInvalidDbType(t *testing.T) {
	resetForTest(t)
	assertPanics(t, func() { Register(haprobe.DbTypeNone, fakeDetectable{haprobe.DbTypeNone}) })
	assertPanics(t, func() { Register(haprobe.DbTypeUnknown, fakeDetectable{haprobe.DbTypeUnknown}) })
}

func TestRegisterPanicsOnNilDetectable(t *testing.T) {
	resetForTest(t)
	assertPanics(t, func() { Register(haprobe.DbTypeEs, nil) })
}

func TestRegisterPanicsOnDuplicate(t *testing.T) {
	resetForTest(t)
	Register(haprobe.DbTypeEs, fakeDetectable{haprobe.DbTypeEs})
	assertPanics(t, func() { Register(haprobe.DbTypeEs, fakeDetectable{haprobe.DbTypeEs}) })
}

func TestLookupAndRegisteredDbTypes(t *testing.T) {
	resetForTest(t)
	if _, ok := Lookup(haprobe.DbTypeMySql); ok {
		t.Fatal("unregistered DbType must not be found")
	}

	Register(haprobe.DbTypeRedis, fakeDetectable{haprobe.DbTypeRedis})
	Register(haprobe.DbTypeMySql, fakeDetectable{haprobe.DbTypeMySql})

	if _, ok := Lookup(haprobe.DbTypeRedis); !ok {
		t.Fatal("registered DbType not found")
	}
	got := RegisteredDbTypes()
	want := []haprobe.DbType{haprobe.DbTypeMySql, haprobe.DbTypeRedis}
	if len(got) != len(want) {
		t.Fatalf("RegisteredDbTypes = %v, want %v", got, want)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("RegisteredDbTypes = %v, want %v", got, want)
		}
	}
}

func TestValidateAcceptsMatchingDetectable(t *testing.T) {
	resetForTest(t)
	Register(haprobe.DbTypeMySql, fakeDetectable{haprobe.DbTypeMySql})
	if err := Validate(nil); err != nil {
		t.Fatalf("Validate failed, errmsg: %s", err)
	}
}

func TestValidateDetectsMismatchedDetectable(t *testing.T) {
	resetForTest(t)
	Register(haprobe.DbTypeEs, fakeDetectable{haprobe.DbTypeKafka})
	if err := Validate(nil); err == nil {
		t.Fatal("Validate must fail when Detectable does not match its key")
	}
}

func TestValidateAcceptsCoveredSwitcherDbTypes(t *testing.T) {
	resetForTest(t)
	Register(haprobe.DbTypeMySql, fakeDetectable{haprobe.DbTypeMySql})
	Register(haprobe.DbTypeRedis, fakeDetectable{haprobe.DbTypeRedis})
	if err := Validate([]haprobe.DbType{
		haprobe.DbTypeMySql, haprobe.DbTypeRedis,
	}); err != nil {
		t.Fatalf("Validate failed, errmsg: %s", err)
	}
}

func TestValidateAcceptsUncoveredSwitcherDbTypes(t *testing.T) {
	resetForTest(t)
	Register(haprobe.DbTypeMySql, fakeDetectable{haprobe.DbTypeMySql})
	if err := Validate([]haprobe.DbType{
		haprobe.DbTypeRedis, haprobe.DbTypeKafka, haprobe.DbTypeMySql,
	}); err != nil {
		t.Fatalf("Validate must not fail for uncovered switcher DbTypes, errmsg: %s", err)
	}
}

func TestValidateAcceptsEmptySwitcherTypes(t *testing.T) {
	resetForTest(t)
	if err := Validate(nil); err != nil {
		t.Fatalf("Validate failed, errmsg: %s", err)
	}
}
