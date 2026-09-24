package atommongodb

import (
	"encoding/json"
	"strings"
	"testing"
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
