package common

import (
	"os"
	"path/filepath"
	"strconv"
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

func TestInstanceOpStartProcessNameByDBType(t *testing.T) {
	cases := []struct {
		name   string
		dbType string
		want   string
	}{
		{name: "missing dbtype defaults mongod", dbType: "", want: "mongod"},
		{name: "mongod", dbType: "mongod", want: "mongod"},
		{name: "mongos", dbType: "mongos", want: "mongos"},
		{name: "other value defaults mongod", dbType: "shardsvr", want: "mongod"},
	}
	for _, tc := range cases {
		tc := tc
		t.Run(tc.name, func(t *testing.T) {
			const port = 27017
			root := t.TempDir()
			t.Setenv("MONGO_DATA_DIR", root)
			instanceDir := filepath.Join(root, "mongodata", strconv.Itoa(port))
			if err := os.MkdirAll(instanceDir, 0755); err != nil {
				t.Fatalf("mkdir instance dir failed: %v", err)
			}
			if tc.dbType != "" {
				if err := os.WriteFile(filepath.Join(instanceDir, "dbtype"), []byte(tc.dbType), 0644); err != nil {
					t.Fatalf("write dbtype failed: %v", err)
				}
			}

			op := &InstanceOp{Instance: &Instance{Port: port}}
			if got := op.startProcessNameByDBType(); got != tc.want {
				t.Fatalf("startProcessNameByDBType() = %q, want %q", got, tc.want)
			}
		})
	}
}
