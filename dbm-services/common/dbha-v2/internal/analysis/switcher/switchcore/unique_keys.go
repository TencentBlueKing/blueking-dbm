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

package switchcore

import (
	"fmt"
	"strings"

	"dbm-services/common/dbha-v2/internal/analysis/dbm"
)

type MetadataKey string

func (metadataKey MetadataKey) String() string {
	return string(metadataKey)
}

type ClusterKey string

func (clusterKey ClusterKey) String() string {
	return string(clusterKey)
}

// HostKey is a unique key for a machine in a cloud
type HostKey struct {
	BkCloudID int
	IP        string
}

func (hostKey HostKey) String() string {
	return fmt.Sprintf("%d:%s", hostKey.BkCloudID, hostKey.IP)
}

type InstMetadataMap map[MetadataKey]*dbm.DbInstMetadata

// GenerateMetadataKey generates a unique key for instance metadata
func GenerateMetadataKey(bkCloudId int, ip string, port int) MetadataKey {
	return MetadataKey(fmt.Sprintf("%d:%s:%d", bkCloudId, ip, port))
}

// ExtractMetadataKeys extracts the keys of the instance data map as a slice of strings.
func ExtractMetadataKeys[T any](instDataMap map[MetadataKey]T) []string {
	keys := make([]string, 0, len(instDataMap))

	for instKey := range instDataMap {
		keys = append(keys, string(instKey))
	}

	return keys
}

// JoinMetadataKeys joins a slice of metadata keys with a separator
func JoinMetadataKeys(keys []MetadataKey, separator string) string {
	keysStr := make([]string, 0, len(keys))
	for _, key := range keys {
		keysStr = append(keysStr, string(key))
	}
	return strings.Join(keysStr, separator)
}

// GenerateClusterKey generates a unique key for cluster-level lock.
func GenerateClusterKey(bkCloudId int, clusterId int) ClusterKey {
	return ClusterKey(fmt.Sprintf("%d:%d", bkCloudId, clusterId))
}

// GenerateHostKey generates a unique key for host-level grouping.
func GenerateHostKey(bkCloudId int, ip string) HostKey {
	return HostKey{
		BkCloudID: bkCloudId,
		IP:        ip,
	}
}

// ParseHostKey parses a HostKey into its cloud ID and IP components
func ParseHostKey(hostKey HostKey) (bkCloudId int, ip string) {
	return hostKey.BkCloudID, hostKey.IP
}
