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

package dbtype

import "dbm-services/common/dbha-v2/pkg/storage/haprobe"

// snapshotForTest captures current catalog + harvest-block registry state and
// returns a restore func. Use with t.Cleanup(snapshotForTest()).
func snapshotForTest() func() {
	catalogMu.Lock()
	harvestBlockMu.Lock()

	byCT := copyClusterTypeMap(byClusterType)
	byDT := copyDbTypeSliceMap(byDbType)
	reg := copyDbTypeSet(registeredTypes)
	builtin := copyDbTypeSet(builtinTypes)
	provider := copyDbTypeSet(providerTypes)
	blocksByDT := copyHarvestBlocksByDbType(harvestBlocksByDbType)
	blocksByName := copyHarvestBlockByName(harvestBlockByName)

	harvestBlockMu.Unlock()
	catalogMu.Unlock()

	return func() {
		catalogMu.Lock()
		harvestBlockMu.Lock()
		byClusterType = byCT
		byDbType = byDT
		registeredTypes = reg
		builtinTypes = builtin
		providerTypes = provider
		harvestBlocksByDbType = blocksByDT
		harvestBlockByName = blocksByName
		harvestBlockMu.Unlock()
		catalogMu.Unlock()
	}
}

func copyClusterTypeMap(
	src map[haprobe.DbmMetadataClusterType]haprobe.DbType,
) map[haprobe.DbmMetadataClusterType]haprobe.DbType {
	out := make(map[haprobe.DbmMetadataClusterType]haprobe.DbType, len(src))
	for k, v := range src {
		out[k] = v
	}
	return out
}

func copyDbTypeSliceMap(
	src map[haprobe.DbType][]haprobe.DbmMetadataClusterType,
) map[haprobe.DbType][]haprobe.DbmMetadataClusterType {
	out := make(map[haprobe.DbType][]haprobe.DbmMetadataClusterType, len(src))
	for k, v := range src {
		cp := make([]haprobe.DbmMetadataClusterType, len(v))
		copy(cp, v)
		out[k] = cp
	}
	return out
}

func copyDbTypeSet(src map[haprobe.DbType]struct{}) map[haprobe.DbType]struct{} {
	out := make(map[haprobe.DbType]struct{}, len(src))
	for k := range src {
		out[k] = struct{}{}
	}
	return out
}

func copyHarvestBlocksByDbType(
	src map[haprobe.DbType][]HarvestBlock,
) map[haprobe.DbType][]HarvestBlock {
	out := make(map[haprobe.DbType][]HarvestBlock, len(src))
	for k, v := range src {
		cp := make([]HarvestBlock, len(v))
		copy(cp, v)
		out[k] = cp
	}
	return out
}

func copyHarvestBlockByName(src map[string]HarvestBlock) map[string]HarvestBlock {
	out := make(map[string]HarvestBlock, len(src))
	for k, v := range src {
		out[k] = v
	}
	return out
}
