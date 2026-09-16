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
