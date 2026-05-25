package dbm

import (
	"encoding/json"
	"testing"

	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

func TestDbInstMetadataUnmarshalJSONRoleCompatibility(t *testing.T) {
	t.Parallel()

	testCases := []struct {
		name                 string
		payload              map[string]any
		expectedInstanceRole haprobe.DbmMetadataInstanceRole
		expectedSpiderRole   haprobe.DbmMetadataSpiderRole
	}{
		{
			name: "only instance role",
			payload: map[string]any{
				"instance_role": haprobe.MySQLStorageMaster,
				"ip":            "127.0.0.1",
				"port":          20000,
			},
			expectedInstanceRole: haprobe.MySQLStorageMaster,
			expectedSpiderRole:   "",
		},
		{
			name: "only spider role",
			payload: map[string]any{
				"spider_role": haprobe.TenDBClusterSpiderMaster,
				"ip":          "127.0.0.1",
				"port":        20000,
			},
			expectedInstanceRole: haprobe.TenDBClusterProxyMaster,
			expectedSpiderRole:   haprobe.TenDBClusterSpiderMaster,
		},
		{
			name: "both roles with same value",
			payload: map[string]any{
				"instance_role": haprobe.TenDBClusterProxySlave,
				"spider_role":   haprobe.TenDBClusterSpiderSlave,
				"ip":            "127.0.0.1",
				"port":          20000,
			},
			expectedInstanceRole: haprobe.TenDBClusterProxySlave,
			expectedSpiderRole:   haprobe.TenDBClusterSpiderSlave,
		},
		{
			name: "both roles conflict",
			payload: map[string]any{
				"instance_role": haprobe.MySQLStorageMaster,
				"spider_role":   haprobe.TenDBClusterSpiderSlave,
				"ip":            "127.0.0.1",
				"port":          20000,
			},
			expectedInstanceRole: haprobe.MySQLStorageMaster,
			expectedSpiderRole:   haprobe.TenDBClusterSpiderSlave,
		},
		{
			name: "both roles missing",
			payload: map[string]any{
				"ip":   "127.0.0.1",
				"port": 20000,
			},
			expectedInstanceRole: "",
			expectedSpiderRole:   "",
		},
	}

	for _, testCase := range testCases {
		testCase := testCase
		t.Run(testCase.name, func(t *testing.T) {
			t.Parallel()

			rawData, err := json.Marshal(testCase.payload)
			if err != nil {
				t.Fatalf("marshal payload failed, err: %s", err)
			}

			metadata := DbInstMetadata{}
			if err = json.Unmarshal(rawData, &metadata); err != nil {
				t.Fatalf("unmarshal payload failed, err: %s", err)
			}

			if metadata.InstanceRole != testCase.expectedInstanceRole {
				t.Fatalf("unexpected instance role, expected: %s, actual: %s",
					testCase.expectedInstanceRole, metadata.InstanceRole)
			}

			if metadata.SpiderRole != testCase.expectedSpiderRole {
				t.Fatalf("unexpected spider role, expected: %s, actual: %s",
					testCase.expectedSpiderRole, metadata.SpiderRole)
			}
		})
	}
}
