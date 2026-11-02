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
	"slices"
	"testing"
)

const (
	setLockWait     = "SET SESSION lock_wait_timeout = 5"
	setInnodbWait   = "SET SESSION innodb_lock_wait_timeout = 5"
	resetLockWait   = "SET SESSION lock_wait_timeout = 100"
	resetInnodbWait = "SET SESSION innodb_lock_wait_timeout = 60"
)

// fakeSession records session statements and fails the ones listed in failing.
type fakeSession struct {
	queries []string
	failing map[string]error
}

func (f *fakeSession) exec(query string) error {
	f.queries = append(f.queries, query)

	return f.failing[query]
}

func runLockWaitScope(session *fakeSession, fn func() error) error {
	return lockWaitScope("127.0.0.1:3306", session.exec, lockWaitValues{lockWait: 100, innodbWait: 60}, fn)
}

func TestLockWaitScopeRestoresWithLiterals(t *testing.T) {
	session := &fakeSession{}
	if err := runLockWaitScope(session, func() error { return nil }); err != nil {
		t.Fatalf("unexpected error, errmsg: %s", err)
	}

	want := []string{setLockWait, setInnodbWait, resetInnodbWait, resetLockWait}
	if !slices.Equal(session.queries, want) {
		t.Fatalf("session statements: %q, want: %q", session.queries, want)
	}
}

func TestLockWaitScopeRestoresAfterPartialSet(t *testing.T) {
	cause := errors.New("set failed")
	session := &fakeSession{failing: map[string]error{setInnodbWait: cause}}
	ran := false
	err := runLockWaitScope(session, func() error { ran = true; return nil })

	if !errors.Is(err, cause) || ran {
		t.Fatalf("partial set should fail before fn, ran: %t, errmsg: %v", ran, err)
	}
	want := []string{setLockWait, setInnodbWait, resetLockWait}
	if !slices.Equal(session.queries, want) {
		t.Fatalf("session statements: %q, want: %q", session.queries, want)
	}
}

func TestLockWaitScopeFailsWhenRestoreFails(t *testing.T) {
	cause := errors.New("restore failed")
	session := &fakeSession{failing: map[string]error{resetLockWait: cause}}
	err := runLockWaitScope(session, func() error { return nil })

	if !errors.Is(err, cause) {
		t.Fatalf("restore failure should fail the statement, errmsg: %v", err)
	}
}

func TestLockWaitScopeRestoresRemainingAfterFailure(t *testing.T) {
	cause := errors.New("restore failed")
	session := &fakeSession{failing: map[string]error{resetInnodbWait: cause}}
	err := runLockWaitScope(session, func() error { return nil })

	if !errors.Is(err, cause) {
		t.Fatalf("restore failure should be returned, errmsg: %v", err)
	}
	if !slices.Contains(session.queries, resetLockWait) {
		t.Fatalf("lock_wait_timeout was not restored, statements: %q", session.queries)
	}
}

func TestLockWaitScopeKeepsStatementError(t *testing.T) {
	cause := errors.New("alter failed")
	session := &fakeSession{failing: map[string]error{resetLockWait: errors.New("restore failed")}}
	err := runLockWaitScope(session, func() error { return cause })

	if err != cause {
		t.Fatalf("statement error should be returned as is, errmsg: %v", err)
	}
	if !slices.Contains(session.queries, resetLockWait) || !slices.Contains(session.queries, resetInnodbWait) {
		t.Fatalf("both settings should be restored, statements: %q", session.queries)
	}
}
