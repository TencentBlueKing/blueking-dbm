package mongodb_rpc

import (
	"os/exec"
	"reflect"
	"testing"

	"go.mongodb.org/mongo-driver/bson"
)

func TestIsMongoVersionAtLeast44(t *testing.T) {
	tests := []struct {
		version string
		want    bool
	}{
		{version: "3.6.0", want: false},
		{version: "4.2.19", want: false},
		{version: "4.3.9", want: false},
		{version: "4.4.0", want: true},
		{version: "4.4.25", want: true},
		{version: "mongo-4.4.25", want: true},
		{version: "mongodb-5.0.14", want: true},
		{version: "invalid", want: false},
	}
	for _, tt := range tests {
		t.Run(tt.version, func(t *testing.T) {
			if got := isMongoVersionAtLeast44(tt.version); got != tt.want {
				t.Fatalf("isMongoVersionAtLeast44(%q) = %v, want %v", tt.version, got, tt.want)
			}
		})
	}
}

func TestNeedsWebconsoleShStatusRole(t *testing.T) {
	if needsWebconsoleShStatusRole(ClusterTypeReplicaSet, "4.4.25") {
		t.Fatal("replica set should not need sh.status role")
	}
	if needsWebconsoleShStatusRole(ClusterTypeShardedCluster, "4.2.19") {
		t.Fatal("sharded cluster below 4.4 should not need sh.status role")
	}
	if !needsWebconsoleShStatusRole(ClusterTypeShardedCluster, "4.4.25") {
		t.Fatal("sharded cluster >=4.4 should need sh.status role")
	}
}

func TestExpectedWebconsoleRoles(t *testing.T) {
	lowRoles := expectedWebconsoleRoles(ClusterTypeShardedCluster, "4.2.19")
	if len(lowRoles) != 1 || lowRoles[0].role != readAnyDatabase {
		t.Fatalf("expected only readAnyDatabase for 4.2, got %+v", lowRoles)
	}

	replicaRoles := expectedWebconsoleRoles(ClusterTypeReplicaSet, "4.4.25")
	if len(replicaRoles) != 1 || replicaRoles[0].role != readAnyDatabase {
		t.Fatalf("replica set 4.4 should only have readAnyDatabase, got %+v", replicaRoles)
	}

	shardedRoles := expectedWebconsoleRoles(ClusterTypeShardedCluster, "4.4.25")
	if len(shardedRoles) != 2 {
		t.Fatalf("expected 2 roles for sharded 4.4, got %+v", shardedRoles)
	}
	if shardedRoles[1].role != webconsoleShStatusRole {
		t.Fatalf("expected custom sh.status role, got %+v", shardedRoles)
	}
}

func TestRoleSetHelpers(t *testing.T) {
	expected := expectedWebconsoleRoles(ClusterTypeShardedCluster, "4.4.25")
	existing := []roleRef{{role: readAnyDatabase, db: "admin"}}
	if hasUnexpectedRoles(existing, expected) {
		t.Fatal("readAnyDatabase only should not be unexpected")
	}
	missing := missingRoles(existing, expected)
	if len(missing) != 1 || missing[0].role != webconsoleShStatusRole {
		t.Fatalf("missing role mismatch: %+v", missing)
	}

	existingWithExtra := []roleRef{
		{role: readAnyDatabase, db: "admin"},
		{role: "clusterMonitor", db: "admin"},
	}
	if !hasUnexpectedRoles(existingWithExtra, expected) {
		t.Fatal("clusterMonitor should be unexpected for minimal role set")
	}
}

func TestExistingRolesFromUsersInfo(t *testing.T) {
	users := bson.A{
		bson.M{
			"roles": bson.A{
				bson.M{"role": readAnyDatabase, "db": "admin"},
			},
		},
	}
	got, err := existingRolesFromUsersInfo(users)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	want := []roleRef{{role: readAnyDatabase, db: "admin"}}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("roles mismatch: got %+v want %+v", got, want)
	}
}

func TestBuildArgsShellBinByVersion(t *testing.T) {
	if _, err := exec.LookPath("mongo"); err != nil {
		t.Skip("mongo not in PATH")
	}
	if _, err := exec.LookPath("mongosh"); err != nil {
		t.Skip("mongosh not in PATH")
	}

	tests := []struct {
		version string
		wantBin string
	}{
		{version: "4.2.19", wantBin: "mongo"},
		{version: "4.4.25", wantBin: "mongosh"},
		{version: "5.0.14", wantBin: "mongosh"},
	}
	for _, tt := range tests {
		t.Run(tt.version, func(t *testing.T) {
			shell := &MongoShell{
				MongoVersion: tt.version,
				MongoHost: MongoHost{
					Host:     "127.0.0.1:27017",
					UserName: "u",
					Password: "p",
				},
				ReadPref: "secondary",
			}
			_, err := buildArgs(shell)
			if err != nil {
				t.Fatalf("buildArgs failed: %v", err)
			}
			if shell.ShellBin != tt.wantBin {
				t.Fatalf("ShellBin = %q, want %q", shell.ShellBin, tt.wantBin)
			}
		})
	}
}
