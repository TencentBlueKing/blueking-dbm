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
	"errors"
	"fmt"
	"strings"
	"testing"

	"dbm-services/common/dbha-v2/pkg/logger"

	"go.uber.org/zap"
)

func TestRunReleasesStoresAfterIdentityFailure(t *testing.T) {
	calls := []string{}
	left := newTrackedStore("left", testIdentity("u1"), &calls)
	right := newTrackedStore("right", testIdentity("u2"), &calls)
	right.identityErr = errors.New("identity failed")

	if err := run(Options{Type: MigrateTypeSchema}, []Store{left, right}); err == nil {
		t.Fatal("identity failure should stop migration")
	}
	assertCalls(t, calls, "identity:left", "identity:right", "unlock:right", "unlock:left")
	assertUnlocks(t, left, right)
}

func TestRunReleasesAttemptedStoresInReverse(t *testing.T) {
	calls := []string{}
	left := newTrackedStore("left", testIdentity("u1"), &calls)
	right := newTrackedStore("right", testIdentity("u2"), &calls)
	right.lockErr = errors.New("lock failed")

	if err := run(Options{Type: MigrateTypeSchema}, []Store{left, right}); err == nil {
		t.Fatal("lock failure should stop migration")
	}
	assertCalls(
		t,
		calls,
		"identity:left",
		"identity:right",
		"lock:left",
		"lock:right",
		"unlock:right",
		"unlock:left",
	)
	assertUnlocks(t, left, right)
}

func TestRunReleasesDeduplicatedAliases(t *testing.T) {
	calls := []string{}
	left := newTrackedStore("left", testIdentity("u1"), &calls)
	alias := newTrackedStore("alias", testIdentity("u1"), &calls)

	if err := run(Options{Type: MigrateTypeSchema}, []Store{left, alias}); err != nil {
		t.Fatal(err)
	}
	assertCalls(t, calls, "identity:left", "identity:alias", "lock:left", "unlock:left", "unlock:alias")
	assertUnlocks(t, left, alias)
	if left.ddl == 0 || alias.ddl != 0 {
		t.Fatal("deduplicated aliases should migrate once")
	}
}

func TestRunContinuesCleanupAfterUnlockFailure(t *testing.T) {
	calls := []string{}
	left := newTrackedStore("left", testIdentity("u1"), &calls)
	right := newTrackedStore("right", testIdentity("u2"), &calls)
	unlockCause := errors.New("unlock failed")
	right.unlockErr = unlockCause
	warns := captureWarn(t)

	if err := run(Options{Type: MigrateTypeSchema}, []Store{left, right}); err != nil {
		t.Fatal(err)
	}
	assertCalls(
		t,
		calls,
		"identity:left",
		"identity:right",
		"lock:left",
		"lock:right",
		"unlock:right",
		"unlock:left",
	)
	assertUnlocks(t, left, right)
	assertUnlockWarning(t, warns, right.Endpoint(), unlockCause)
}

func TestRunPreservesMigrationErrorAfterUnlockFailure(t *testing.T) {
	calls := []string{}
	left := newTrackedStore("left", testIdentity("u1"), &calls)
	right := newTrackedStore("right", testIdentity("u2"), &calls)
	migrateCause := errors.New("ddl failed")
	unlockCause := errors.New("unlock failed")
	right.ddlErr = migrateCause
	right.unlockErr = unlockCause
	warns := captureWarn(t)

	err := run(Options{Type: MigrateTypeSchema}, []Store{left, right})
	if !errors.Is(err, migrateCause) || errors.Is(err, unlockCause) {
		t.Fatalf("unlock error replaced the migration error, errmsg: %s", err)
	}
	assertUnlocks(t, left, right)
	assertUnlockWarning(t, warns, right.Endpoint(), unlockCause)
}

type trackedStore struct {
	*memStore
	name         string
	calls        *[]string
	identityErr  error
	lockErr      error
	unlockErr    error
	loadErr      error
	databaseErr  error
	ledgerErr    error
	ddlErr       error
	recordErr    error
	probeErr     error
	nonEmptyErr  error
	duplicateErr error
	unlocks      int
}

func newTrackedStore(name string, id Identity, calls *[]string) *trackedStore {
	return &trackedStore{memStore: newMem(name, id), name: name, calls: calls}
}

func (s *trackedStore) Identity() (Identity, error) {
	s.record("identity")
	if s.identityErr != nil {
		return Identity{}, s.identityErr
	}
	return s.memStore.Identity()
}

func (s *trackedStore) Lock() error {
	s.record("lock")
	if s.lockErr != nil {
		return s.lockErr
	}
	return s.memStore.Lock()
}

func (s *trackedStore) Unlock() error {
	s.record("unlock")
	s.unlocks++
	if err := s.memStore.Unlock(); err != nil {
		return err
	}
	return s.unlockErr
}

func (s *trackedStore) Load() (*Snapshot, error) {
	if s.loadErr != nil {
		return nil, s.loadErr
	}
	return s.memStore.Load()
}

func (s *trackedStore) LoadStep(table string) (*Snapshot, error) {
	if s.loadErr != nil {
		return nil, s.loadErr
	}
	return s.memStore.LoadStep(table)
}

func (s *trackedStore) EnsureDatabase() error {
	if s.databaseErr != nil {
		return s.databaseErr
	}
	return s.memStore.EnsureDatabase()
}

func (s *trackedStore) EnsureSchemaLedger() error {
	if s.ledgerErr != nil {
		return s.ledgerErr
	}
	return s.memStore.EnsureSchemaLedger()
}

func (s *trackedStore) ExecDDL(sql string) error {
	if s.ddlErr != nil {
		return s.ddlErr
	}
	return s.memStore.ExecDDL(sql)
}

func (s *trackedStore) RecordSchema(version int64, name string) error {
	if s.recordErr != nil {
		return s.recordErr
	}
	return s.memStore.RecordSchema(version, name)
}

func (s *trackedStore) ProbeFacts(snap *Snapshot, scope factScope) error {
	if s.probeErr != nil {
		return s.probeErr
	}
	return s.memStore.ProbeFacts(snap, scope)
}

func (s *trackedStore) TableNonEmpty(table string) (bool, error) {
	if s.nonEmptyErr != nil {
		return false, s.nonEmptyErr
	}
	return s.memStore.TableNonEmpty(table)
}

func (s *trackedStore) DuplicateSamples(table string, keys []keyExpr, limit int) ([]duplicateSample, error) {
	if s.duplicateErr != nil {
		return nil, s.duplicateErr
	}
	return s.memStore.DuplicateSamples(table, keys, limit)
}

func (s *trackedStore) record(action string) {
	*s.calls = append(*s.calls, action+":"+s.name)
}

func testIdentity(uuid string) Identity {
	return Identity{ServerUUID: uuid, Hostname: uuid, Port: 3306}
}

func assertUnlocks(t *testing.T, stores ...*trackedStore) {
	t.Helper()
	for _, store := range stores {
		if store.unlocks != 1 {
			t.Fatalf("unlock count, endpoint: %s, count: %d", store.Endpoint(), store.unlocks)
		}
	}
}

func captureWarn(t *testing.T) *warnLog {
	t.Helper()
	previous := logger.Log()
	recorded := &warnLog{}
	logger.SetLogger(recorded)
	t.Cleanup(func() { logger.SetLogger(previous) })
	return recorded
}

func assertUnlockWarning(t *testing.T, recorded *warnLog, endpoint string, cause error) {
	t.Helper()
	for _, line := range recorded.warnings {
		if strings.Contains(line, "endpoint: "+endpoint) && strings.Contains(line, "errmsg: "+cause.Error()) {
			return
		}
	}
	t.Fatalf("missing unlock warning, endpoint: %s, warnings: %v", endpoint, recorded.warnings)
}

type warnLog struct {
	warnings []string
	infos    []string
}

func (l *warnLog) OriginLogger() *zap.Logger { return nil }

func (l *warnLog) Debug(string, ...any) {}

func (l *warnLog) Info(format string, args ...any) {
	l.infos = append(l.infos, fmt.Sprintf(format, args...))
}

func (l *warnLog) Warn(format string, args ...any) {
	l.warnings = append(l.warnings, fmt.Sprintf(format, args...))
}

func (l *warnLog) Error(string, ...any) {}

func (l *warnLog) Fatal(string, ...any) {}

func assertCalls(t *testing.T, got []string, want ...string) {
	t.Helper()
	if len(got) != len(want) {
		t.Fatalf("calls length, got: %v, want: %v", got, want)
	}
	for index := range want {
		if got[index] != want[index] {
			t.Fatalf("call index: %d, got: %s, want: %s", index, got[index], want[index])
		}
	}
}
