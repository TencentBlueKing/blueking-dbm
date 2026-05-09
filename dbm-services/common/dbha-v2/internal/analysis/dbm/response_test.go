package dbm

import (
	"encoding/json"
	"testing"
)

func TestDbInstMetadataUnmarshalJSONRoleCompatibility(t *testing.T) {
	t.Parallel()

	testCases := []struct {
		name                 string
		payload              map[string]any
		expectedInstanceRole DbmMetadataInstanceRole
		expectedSpiderRole   DbmMetadataSpiderRole
	}{
		{
			name: "only instance role",
			payload: map[string]any{
				"instance_role": MySQLStorageMaster,
				"ip":            "127.0.0.1",
				"port":          20000,
			},
			expectedInstanceRole: MySQLStorageMaster,
			expectedSpiderRole:   "",
		},
		{
			name: "only spider role",
			payload: map[string]any{
				"spider_role": TenDBClusterSpiderMaster,
				"ip":          "127.0.0.1",
				"port":        20000,
			},
			expectedInstanceRole: TenDBClusterProxyMaster,
			expectedSpiderRole:   TenDBClusterSpiderMaster,
		},
		{
			name: "both roles with same value",
			payload: map[string]any{
				"instance_role": TenDBClusterProxySlave,
				"spider_role":   TenDBClusterSpiderSlave,
				"ip":            "127.0.0.1",
				"port":          20000,
			},
			expectedInstanceRole: TenDBClusterProxySlave,
			expectedSpiderRole:   TenDBClusterSpiderSlave,
		},
		{
			name: "both roles conflict",
			payload: map[string]any{
				"instance_role": MySQLStorageMaster,
				"spider_role":   TenDBClusterSpiderSlave,
				"ip":            "127.0.0.1",
				"port":          20000,
			},
			expectedInstanceRole: MySQLStorageMaster,
			expectedSpiderRole:   TenDBClusterSpiderSlave,
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
