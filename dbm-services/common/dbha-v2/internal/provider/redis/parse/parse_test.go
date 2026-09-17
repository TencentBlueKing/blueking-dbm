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

package redisparse

import (
	"encoding/json"
	"errors"
	"testing"

	"dbm-services/common/dbha-v2/internal/analysis/parser"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// Verifies this package's own init registration; the allanalysis aggregation
// path is covered by the workflow provider-import test.
func TestRedisProcesserRegistered(t *testing.T) {
	p, ok := parser.Lookup(haprobe.DbTypeRedis)
	if !ok || p == nil {
		t.Fatal("redis processer not registered via redisparse init")
	}
}

func TestStatusProcessInvalidJSON(t *testing.T) {
	var s Status
	_, err := s.Process(json.RawMessage(`{not-json`))
	if err == nil {
		t.Fatal("expected error for invalid JSON")
	}
	if !errors.Is(err, errInvalidRedisStatus) || err.Error() != errInvalidRedisStatus.Error() {
		t.Fatalf("unexpected errmsg: %s", err)
	}
}

func TestStatusProcessAllNil(t *testing.T) {
	var s Status
	event, err := s.Process(json.RawMessage(`{}`))
	if err != nil {
		t.Fatalf("unexpected errmsg: %s", err)
	}
	if event != nil {
		t.Fatalf("expected nil event for all-nil status, got: %#v", event)
	}
}

func TestStatusProcessFailedState(t *testing.T) {
	cases := []struct {
		name string
		raw  string
	}{
		{"replication failed", `{"replication_status":{"state":"failed","failure_reason":"ERR unknown command"}}`},
		{"heartbeat failed", `{"heartbeat_status":{"state":"failed","failure_reason":"MOVED 123"}}`},
		{"read_check failed", `{"read_check_status":{"state":"failed","failure_reason":"ERR"}}`},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			var s Status
			event, err := s.Process(json.RawMessage(tc.raw))
			if err != nil {
				t.Fatalf("unexpected errmsg: %s", err)
			}
			if event == nil {
				t.Fatal("expected event for failed state")
			}
			if event.Name != haprobe.DbEventNameDetectFailure {
				t.Fatalf("unexpected event name: %s, want %s", event.Name, haprobe.DbEventNameDetectFailure)
			}
		})
	}
}

func TestStatusProcessOk(t *testing.T) {
	cases := []struct {
		name string
		raw  string
	}{
		{"slave replication ok", `{"replication_status":{"state":"ok","role":"slave"}}`},
		{"proxy read-check ok", `{"read_check_status":{"state":"ok"}}`},
		{"master heartbeat ok", `{"replication_status":{"state":"ok","role":"master"},"heartbeat_status":{"state":"ok","select_result":"OK","set_result":"OK"}}`},
		{"master set MOVED is acceptable", `{"replication_status":{"state":"ok","role":"master"},"heartbeat_status":{"state":"ok","select_result":"OK","set_result":"MOVED 123"}}`},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			var s Status
			event, err := s.Process(json.RawMessage(tc.raw))
			if err != nil {
				t.Fatalf("unexpected errmsg: %s", err)
			}
			if event != nil {
				t.Fatalf("expected nil event, got: %#v", event)
			}
		})
	}
}

func TestStatusProcessHeartbeatDefensive(t *testing.T) {
	cases := []struct {
		name string
		raw  string
	}{
		{"select result lacks OK", `{"replication_status":{"state":"ok","role":"master"},"heartbeat_status":{"state":"ok","select_result":"ERR","set_result":"OK"}}`},
		{"set result lacks OK/MOVED", `{"replication_status":{"state":"ok","role":"master"},"heartbeat_status":{"state":"ok","select_result":"OK","set_result":"ERR"}}`},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			var s Status
			event, err := s.Process(json.RawMessage(tc.raw))
			if err != nil {
				t.Fatalf("unexpected errmsg: %s", err)
			}
			if event == nil {
				t.Fatal("expected defensive event")
			}
			if event.Name != haprobe.DbEventNameDetectFailure {
				t.Fatalf("unexpected event name: %s", event.Name)
			}
		})
	}
}
