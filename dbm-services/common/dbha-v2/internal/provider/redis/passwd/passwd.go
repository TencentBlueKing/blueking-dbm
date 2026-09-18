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

// Package redispasswd fetches redis instance and machine passwords from the DBM
// password service and caches them in one process-wide cache.
//
// The service address is not read from any component config directly, since this
// package is shared by binaries whose config layouts differ. A component registers
// a loader closure with RegisterConfigLoader, which is invoked on the first
// password lookup rather than at registration time, so it is safe to call from
// init where config values are not populated yet.
package redispasswd

import (
	"time"

	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// QueryConfig carries everything needed to reach the DBM password service.
type QueryConfig struct {
	// API is the full password query URL. An empty value makes every lookup fail.
	API string
	// Token authenticates the caller against the DBM proxy.
	Token string
	// Timeout bounds a single query. Zero falls back to the HTTP client default.
	Timeout time.Duration
}

// ConfigLoader reads QueryConfig out of the component's own configuration
// and must not call back into this package. Concurrent first lookups may each invoke it.
type ConfigLoader func() QueryConfig

// RegisterConfigLoader installs the closure used to obtain the query config,
// replacing any earlier one. It has no effect once the config has been resolved.
func RegisterConfigLoader(fn ConfigLoader) {
	instance().registerLoader(fn)
}

// ApplyQueryConfig overrides the query config and drops every cached password, so
// passwords fetched against the previous endpoint are never reused.
func ApplyQueryConfig(cfg QueryConfig) {
	instance().applyConfig(cfg)
}

// GetDbInstPasswd returns the password shared by the redis storage or proxy
// instances of one cluster. Callers must propagate the error instead of falling
// back to a placeholder: a wrong password is indistinguishable from an
// unreachable instance.
func GetDbInstPasswd(bkCloudID, clusterID int, machineType haprobe.DbmMetadataMachineType) (string, error) {
	return instance().dbInstPasswd(bkCloudID, clusterID, machineType)
}

// GetMachinePasswd returns the OS password of the redis machines of a cloud area.
// It is keyed by a fixed pseudo instance rather than by host, so one value covers
// every machine.
func GetMachinePasswd(bkCloudID int) (string, error) {
	return instance().machinePasswd(bkCloudID)
}

// BatchFill warms the cache for the given clusters in batches, skipping the ones
// already cached. It returns the first error but always attempts every batch,
// since a partially warmed cache is still useful.
func BatchFill(bkCloudID int, clusterIDs []int) error {
	return instance().batchFill(bkCloudID, clusterIDs)
}
