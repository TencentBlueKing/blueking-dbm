package common

import (
	"testing"

	"dbm-services/mongodb/db-tools/mongo-toolkit-go/pkg/mymongo"
)

func TestReplicaSetServiceCheckRoleOK(t *testing.T) {
	t.Parallel()
	cases := []struct {
		name    string
		r       mymongo.IsMasterResult
		wantErr bool
	}{
		{
			name:    "primary",
			r:       mymongo.IsMasterResult{Primary: "h:27017", IsMaster: true},
			wantErr: false,
		},
		{
			name:    "secondary",
			r:       mymongo.IsMasterResult{Primary: "h:27017", Secondary: true},
			wantErr: false,
		},
		{
			name:    "no_primary",
			r:       mymongo.IsMasterResult{Primary: "", Secondary: true},
			wantErr: true,
		},
		{
			name:    "neither_primary_nor_secondary",
			r:       mymongo.IsMasterResult{Primary: "h:27017"},
			wantErr: true,
		},
	}
	for _, tc := range cases {
		tc := tc
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			err := replicaSetServiceCheckRoleOK(&tc.r)
			if tc.wantErr {
				if err == nil {
					t.Fatal("expected error")
				}
				return
			}
			if err != nil {
				t.Fatal(err)
			}
		})
	}
}
