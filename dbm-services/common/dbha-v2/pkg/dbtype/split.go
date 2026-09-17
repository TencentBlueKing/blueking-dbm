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

import (
	"fmt"
	"sync"

	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

var (
	splitMu          sync.RWMutex
	splitByClusterID = map[haprobe.DbType]bool{}
)

// RegisterSplitPolicy marks whether endpoints of a DbType must be grouped per
// cluster id. Probe credentials are resolved per (bk_cloud_id, cluster_id), so
// a DbType whose credentials are cluster-scoped must not merge endpoints of
// different clusters on one IP.
//
// It panics on an invalid DbType. An unregistered DbType defaults to false, so
// existing behaviour (mysql and friends) is unchanged.
func RegisterSplitPolicy(dt haprobe.DbType, split bool) {
	if dt == haprobe.DbTypeNone || dt == haprobe.DbTypeUnknown {
		panic(fmt.Sprintf("dbtype: refuse to register split policy for invalid DbType: %q", dt))
	}

	splitMu.Lock()
	defer splitMu.Unlock()

	splitByClusterID[dt] = split
}

// SplitByClusterOf reports whether endpoints of dt must be grouped per cluster id.
func SplitByClusterOf(dt haprobe.DbType) bool {
	splitMu.RLock()
	defer splitMu.RUnlock()

	return splitByClusterID[dt]
}
