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

// Package credential registers the Redis credential resolver.
package credential

import (
	"context"
	"fmt"

	redispasswd "dbm-services/common/dbha-v2/internal/provider/redis/passwd"
	"dbm-services/common/dbha-v2/pkg/dbcred"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

var _ dbcred.Resolver = (*resolver)(nil)
var _ dbcred.Configurer = (*resolver)(nil)

type resolver struct{}

// Fill resolves redis credentials for one machine's instances in as few remote
// calls as possible: cluster ids are deduplicated and fetched in one batch,
// then each instance is served from the process-wide cache.
func (r *resolver) Fill(ctx context.Context, bkCloudID int, items []*dbcred.Item) error {
	if len(items) == 0 {
		return nil
	}

	ids := make([]int, 0, len(items))
	seen := make(map[int]struct{}, len(items))
	for _, it := range items {
		if _, dup := seen[it.Instance.ClusterID]; dup {
			continue
		}
		seen[it.Instance.ClusterID] = struct{}{}
		ids = append(ids, it.Instance.ClusterID)
	}

	// Prefetch the batch (200 clusters per request, singleflight + 30min cache).
	//
	// A prefetch error is NOT fatal: BatchFill attempts every batch and returns
	// only the first error, so part of the clusters may already be cached. Keep
	// going so each instance is decided on its own - a cache hit succeeds, a miss
	// triggers one more singleflight fetch. Bailing out here would drop instances
	// that were in fact already resolvable, contradicting per-instance verdicts.
	if err := redispasswd.BatchFill(bkCloudID, ids); err != nil {
		logger.Warn("prefetch redis credentials failed, bk_cloud_id: %d, cluster_ids: %v, errmsg: %s",
			bkCloudID, ids, err)
	}

	var firstErr error
	for _, it := range items {
		credential, err := redispasswd.GetDbInstPasswd(
			bkCloudID, it.Instance.ClusterID, it.Instance.MachineType)
		if err != nil {
			logger.Warn("resolve redis credential failed, cluster_id: %d, machine_type: %s, errmsg: %s",
				it.Instance.ClusterID, it.Instance.MachineType, err)
			if firstErr == nil {
				firstErr = err
			}
			continue // leave empty, never substitute a placeholder
		}
		it.Password = credential
	}
	return firstErr
}

// dbmApiNameQueryRedisPassword names the DBM API entry this resolver needs.
// It mirrors analysis' DbmApiQueryRedisPassword so operators configure the same
// service (api/token) via the shared COMMON_DBM_API_QUERY_REDIS_PASSWORD_* vars.
const dbmApiNameQueryRedisPassword = "queryRedisPassword"

// Configure resolves the password-service entry BY NAME and hands it to the
// passwd client.
//
// Returning an error puts this DbType into the unconfigured set: startup
// continues (Warn), and every Fill afterwards fails per instance, yielding an
// empty password that falls through to the liveness double-check.
func (r *resolver) Configure(lookup dbcred.ConfigLookup) error {
	api, ok := lookup(dbmApiNameQueryRedisPassword)
	if !ok {
		return fmt.Errorf("dbm api %q not configured", dbmApiNameQueryRedisPassword)
	}
	redispasswd.ApplyQueryConfig(redispasswd.QueryConfig{
		API:     api.Api,
		Token:   api.Token,
		Timeout: api.Timeout,
	})
	return nil
}

func init() {
	dbcred.Register(haprobe.DbTypeRedis, &resolver{})
}
