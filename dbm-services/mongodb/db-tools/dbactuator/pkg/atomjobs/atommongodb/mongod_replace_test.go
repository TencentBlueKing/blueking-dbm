package atommongodb

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/jobruntime"
)

func TestValidateRsQuorumAfterRemove(t *testing.T) {
	healthy := func(host string) rsRemainingMember {
		return rsRemainingMember{Host: host, Votes: 1, Health: 1, State: 2, StateStr: "SECONDARY"}
	}
	failed := func(host string) rsRemainingMember {
		return rsRemainingMember{Host: host, Votes: 1, Health: 0, State: 8, StateStr: "DOWN"}
	}

	cases := []struct {
		name      string
		remaining []rsRemainingMember
		wantErr   bool
	}{
		{
			name:      "2 remaining 1 failed — refuse, cannot keep PRIMARY",
			remaining: []rsRemainingMember{healthy("a:27017"), failed("b:27017")},
			wantErr:   true,
		},
		{
			name:      "2 remaining both healthy — allow",
			remaining: []rsRemainingMember{healthy("a:27017"), healthy("b:27017")},
			wantErr:   false,
		},
		{
			name:      "3 remaining 1 failed — allow",
			remaining: []rsRemainingMember{healthy("a:27017"), healthy("b:27017"), failed("c:27017")},
			wantErr:   false,
		},
		{
			name:      "3 remaining 2 failed — refuse exceeds half",
			remaining: []rsRemainingMember{healthy("a:27017"), failed("b:27017"), failed("c:27017")},
			wantErr:   true,
		},
		{
			name:      "5 remaining 2 failed — allow",
			remaining: []rsRemainingMember{healthy("a"), healthy("b"), healthy("c"), failed("d"), failed("e")},
			wantErr:   false,
		},
		{
			name:      "5 remaining 3 failed — refuse exceeds half",
			remaining: []rsRemainingMember{healthy("a"), healthy("b"), failed("c"), failed("d"), failed("e")},
			wantErr:   true,
		},
		{
			name: "hidden votes=0 ignored, 2 voting healthy — allow",
			remaining: []rsRemainingMember{
				healthy("a:27017"),
				healthy("b:27017"),
				{Host: "backup:27017", Votes: 0, Health: 0, State: 8, StateStr: "DOWN"},
			},
			wantErr: false,
		},
		{
			name:      "no remaining voting members — refuse",
			remaining: []rsRemainingMember{{Host: "backup:27017", Votes: 0, Health: 1, State: 2, StateStr: "SECONDARY"}},
			wantErr:   true,
		},
		{
			name:      "empty remaining — refuse",
			remaining: nil,
			wantErr:   true,
		},
		{
			name:      "1 remaining healthy — allow, degenerates to single node",
			remaining: []rsRemainingMember{healthy("a:27017")},
			wantErr:   false,
		},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			err := validateRsQuorumAfterRemove(tc.remaining)
			if tc.wantErr && err == nil {
				t.Fatal("expected error")
			}
			if !tc.wantErr && err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
		})
	}
}

func TestBuildReplicaSetRemoveQuorumEvalEscapesSource(t *testing.T) {
	source := `127.0.0.1:27017"; throw new Error("injected")`
	eval := buildReplicaSetRemoveQuorumEval(source)
	sourceJSON, err := json.Marshal(source)
	if err != nil {
		t.Fatalf("json.Marshal: %v", err)
	}
	if !strings.Contains(eval, "var source = "+string(sourceJSON)) {
		t.Fatalf("source is not JSON escaped in eval: %s", eval)
	}
}

func TestCheckQuorumWithRetryRechecksMajorityRefuse(t *testing.T) {
	calls := 0
	sleeps := 0
	refuse := fmt.Errorf("after remove, remaining voting members=2 healthy=1 failed=1 (b); no strict majority, refuse rs.remove")
	remaining, err := checkQuorumWithRetry(func() ([]rsRemainingMember, error) {
		calls++
		if calls < 3 {
			return nil, refuse
		}
		return []rsRemainingMember{{Host: "a", Votes: 1, Health: 1}}, nil
	}, 3, time.Millisecond, func(time.Duration) { sleeps++ })
	if err != nil {
		t.Fatal(err)
	}
	if calls != 3 || sleeps != 2 {
		t.Fatalf("calls=%d sleeps=%d", calls, sleeps)
	}
	if !isSingleVotingSurvivor(remaining) {
		t.Fatal("expected single voting survivor")
	}
}

func TestCheckQuorumWithRetryDoesNotRetryEvalError(t *testing.T) {
	calls := 0
	_, err := checkQuorumWithRetry(func() ([]rsRemainingMember, error) {
		calls++
		return nil, fmt.Errorf("check remaining rs quorum before remove fail: dial")
	}, 3, time.Millisecond, func(time.Duration) {})
	if err == nil || calls != 1 {
		t.Fatalf("calls=%d err=%v", calls, err)
	}
}

func TestBuildReplicaSetRemoveEvalEscapesSource(t *testing.T) {
	source := `127.0.0.1:27017"; throw new Error("injected")`
	eval := buildReplicaSetRemoveEval(source)
	sourceJSON, err := json.Marshal(source)
	if err != nil {
		t.Fatalf("json.Marshal: %v", err)
	}
	if !strings.Contains(eval, "var source = "+string(sourceJSON)) {
		t.Fatalf("source is not JSON escaped in eval: %s", eval)
	}
	if !strings.Contains(eval, "rs.remove(source)") {
		t.Fatalf("eval missing rs.remove(source): %s", eval)
	}
	if !strings.Contains(eval, "JSON.stringify") {
		t.Fatalf("eval must print JSON result: %s", eval)
	}
}

func TestParseRsRemoveResultAndError(t *testing.T) {
	ok, err := parseRsRemoveResult(`{"ok":1,"code":0,"codeName":"","errmsg":""}`)
	if err != nil {
		t.Fatal(err)
	}
	if rsRemoveResultError(ok) != nil {
		t.Fatal("ok=1 must not produce error")
	}

	busy109, err := parseRsRemoveResult(
		`{"ok":0,"code":109,"codeName":"ConfigurationInProgress","errmsg":"Cannot run replSetReconfig because the node is currently updating its configuration"}`,
	)
	if err != nil {
		t.Fatal(err)
	}
	re109 := rsRemoveResultError(busy109)
	if !isReconfigBusy(re109) {
		t.Fatalf("code 109 must be reconfig-busy, got %v", re109)
	}

	busy308, err := parseRsRemoveResult(
		`{"ok":0,"code":308,"codeName":"CurrentConfigNotCommittedYet","errmsg":"Cannot run replSetReconfig because the current config is not yet committed"}`,
	)
	if err != nil {
		t.Fatal(err)
	}
	if !isReconfigBusy(rsRemoveResultError(busy308)) {
		t.Fatal("code 308 must be reconfig-busy")
	}

	other, err := parseRsRemoveResult(`{"ok":0,"code":10107,"codeName":"NotWritablePrimary","errmsg":"not primary"}`)
	if err != nil {
		t.Fatal(err)
	}
	if isReconfigBusy(rsRemoveResultError(other)) {
		t.Fatal("NotWritablePrimary must not match reconfig-busy")
	}

	if _, err := parseRsRemoveResult("not-json"); err == nil {
		t.Fatal("expected parse error")
	}
}

func TestIsReconfigBusy(t *testing.T) {
	if !isReconfigBusy(&rsRemoveError{Code: errCodeConfigurationInProgress, CodeName: "ConfigurationInProgress", Errmsg: "busy"}) {
		t.Fatal("expected code 109 to match")
	}
	if !isReconfigBusy(&rsRemoveError{Code: errCodeCurrentConfigNotCommittedYet, CodeName: "CurrentConfigNotCommittedYet", Errmsg: "uncommitted"}) {
		t.Fatal("expected code 308 to match")
	}
	if isReconfigBusy(&rsRemoveError{Code: 10107, CodeName: "NotWritablePrimary", Errmsg: "not primary"}) {
		t.Fatal("NotWritablePrimary must not match")
	}
	// Production Run3 path only yields "exit status 1" — string matching would
	// have falsely depended on stderr text that never reaches err.Error().
	if isReconfigBusy(fmt.Errorf("run mongo eval fail: exit status 1")) {
		t.Fatal("bare exit status must not match reconfig-busy")
	}
	if isReconfigBusy(fmt.Errorf(
		"run mongo eval fail: exit status 1: MongoServerError: Cannot run replSetReconfig because the node is currently updating its configuration",
	)) {
		t.Fatal("stderr-in-error-string must not match; retry is by typed code only")
	}
	if isReconfigBusy(nil) {
		t.Fatal("nil must not match")
	}
}

func TestRemoveWithRetryRetriesReconfigBusy(t *testing.T) {
	for _, code := range []int{errCodeConfigurationInProgress, errCodeCurrentConfigNotCommittedYet} {
		t.Run(fmt.Sprintf("code_%d", code), func(t *testing.T) {
			calls := 0
			sleeps := 0
			warns := 0
			busy := &rsRemoveError{Code: code, CodeName: "busy", Errmsg: "reconfig settling"}
			err := removeWithRetry(func() error {
				calls++
				if calls < 3 {
					return busy
				}
				return nil
			}, 5, time.Millisecond, func(time.Duration) { sleeps++ }, func(string, ...interface{}) { warns++ })
			if err != nil {
				t.Fatalf("err=%v", err)
			}
			if calls != 3 || sleeps != 2 || warns != 2 {
				t.Fatalf("calls=%d sleeps=%d warns=%d", calls, sleeps, warns)
			}
		})
	}
}

func TestRemoveWithRetryDoesNotRetryOtherErrors(t *testing.T) {
	cases := []error{
		fmt.Errorf("run mongo eval fail: exit status 1"),
		&rsRemoveError{Code: 10107, CodeName: "NotWritablePrimary", Errmsg: "not primary"},
		fmt.Errorf("after remove, remaining voting members=2 healthy=1 failed=1 (b); no strict majority, refuse rs.remove"),
	}
	for _, want := range cases {
		t.Run(want.Error(), func(t *testing.T) {
			calls := 0
			err := removeWithRetry(func() error {
				calls++
				return want
			}, 5, time.Millisecond, func(time.Duration) {}, func(string, ...interface{}) {})
			if err == nil || calls != 1 {
				t.Fatalf("calls=%d err=%v", calls, err)
			}
		})
	}
}

func TestRemoveWithRetryExhaustsAttempts(t *testing.T) {
	calls := 0
	sleeps := 0
	busy := &rsRemoveError{
		Code:     errCodeConfigurationInProgress,
		CodeName: "ConfigurationInProgress",
		Errmsg:   "currently updating its configuration",
	}
	err := removeWithRetry(func() error {
		calls++
		return busy
	}, 3, time.Millisecond, func(time.Duration) { sleeps++ }, nil)
	if err == nil {
		t.Fatal("expected error after exhausting retries")
	}
	if calls != 3 || sleeps != 2 {
		t.Fatalf("calls=%d sleeps=%d", calls, sleeps)
	}
	if !isReconfigBusy(err) {
		t.Fatalf("expected busy error propagated, got %v", err)
	}
}

// TestExecRsRemovePathViaFakeMongo drives runMongoEvalOutput → execRsRemove →
// removeWithRetry with a fake mongo binary that prints JSON results on stdout
// and exits 0. This is the production path: stderr-based string matching would
// never see the ConfigurationInProgress text because Run3 only returns
// "exit status N".
func TestExecRsRemovePathViaFakeMongo(t *testing.T) {
	dir := t.TempDir()
	stateFile := filepath.Join(dir, "calls")
	if err := os.WriteFile(stateFile, []byte("0"), 0o644); err != nil {
		t.Fatal(err)
	}
	fakeMongo := filepath.Join(dir, "mongo")
	script := fmt.Sprintf(`#!/bin/bash
set -e
n=$(cat %q)
n=$((n+1))
echo "$n" > %q
# Only react to --eval that contains rs.remove; other probes should not happen
# in this unit test (we call execRsRemove directly).
if [ "$n" -lt 3 ]; then
  echo '{"ok":0,"code":109,"codeName":"ConfigurationInProgress","errmsg":"Cannot run replSetReconfig because the node is currently updating its configuration"}'
  exit 0
fi
echo '{"ok":1,"code":0,"codeName":"","errmsg":""}'
exit 0
`, stateFile, stateFile)
	if err := os.WriteFile(fakeMongo, []byte(script), 0o755); err != nil {
		t.Fatal(err)
	}

	logBuf := &bytes.Buffer{}
	rt := &jobruntime.JobGenericRuntime{
		Logger: logger.New(logBuf, false, logger.InfoLevel),
	}
	r := &MongoDReplace{
		runtime: rt,
		Mongo:   fakeMongo,
		ConfParams: &MongoDReplaceConfParams{
			AdminUsername: "u",
			AdminPassword: "p",
		},
		PrimaryIP:   "127.0.0.1",
		PrimaryPort: 27017,
	}

	calls := 0
	sleeps := 0
	eval := buildReplicaSetRemoveEval("127.0.0.1:27017")
	err := removeWithRetry(func() error {
		calls++
		return r.execRsRemove(eval)
	}, 5, time.Millisecond, func(time.Duration) { sleeps++ }, func(string, ...interface{}) {})
	if err != nil {
		t.Fatalf("err=%v log=%s", err, logBuf.String())
	}
	if calls != 3 || sleeps != 2 {
		t.Fatalf("calls=%d sleeps=%d", calls, sleeps)
	}
}
