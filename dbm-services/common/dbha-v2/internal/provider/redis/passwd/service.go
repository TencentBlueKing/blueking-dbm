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

package redispasswd

import (
	"encoding/base64"
	"fmt"
	"math/rand/v2"
	"strconv"
	"sync"
	"time"

	"dbm-services/common/dbha-v2/pkg/cache"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"

	"golang.org/x/sync/singleflight"
)

// Components and users recognized by the DBM password service.
const (
	componentRedis           = "redis"
	componentRedisProxy      = "redis_proxy"
	componentRedisProxyAdmin = "redis_proxy_admin"

	userInstanceDefault = "default"
	userMachineDefault  = "mysql"

	// machineInstanceIP is the pseudo instance the machine password is stored under.
	machineInstanceIP = "0.0.0.0"
)

const (
	// maxPasswdEntries bounds the cache; beyond it the LRU drops the coldest keys.
	maxPasswdEntries = 8000

	passwdTTL = 30 * time.Minute
	// passwdTTLJitter spreads the refetches of entries cached in the same burst.
	passwdTTLJitter = 600 * time.Second

	// maxBatchInstances caps how many clusters one query asks for.
	maxBatchInstances = 200
)

// service owns the process-wide password cache and the resolved query config.
type service struct {
	cache *cache.HighPerformanceTTLCache[string]

	// inflight collapses concurrent lookups of the same cache key into one query.
	inflight singleflight.Group

	mu       sync.Mutex
	cfg      QueryConfig
	resolved bool
	loader   ConfigLoader
}

// The one service of the process, reached through instance().
var (
	svcOnce sync.Once
	svc     *service
)

// instance returns the process-wide service, creating it on first use.
func instance() *service {
	svcOnce.Do(func() {
		svc = &service{
			cache: cache.NewHighPerformanceTTLCacheWithSize[string](maxPasswdEntries),
		}
	})

	return svc
}

// registerLoader stores the closure resolving the query config.
func (s *service) registerLoader(fn ConfigLoader) {
	s.mu.Lock()
	defer s.mu.Unlock()

	s.loader = fn
}

// applyConfig replaces the query config and drops the passwords it produced.
func (s *service) applyConfig(cfg QueryConfig) {
	s.mu.Lock()
	s.cfg = cfg
	s.resolved = true
	s.mu.Unlock()

	s.cache.Clear()
}

// queryConfig returns the query config, invoking the registered loader the first
// time it is needed. The loader runs unlocked so it can never deadlock the caller.
func (s *service) queryConfig() (QueryConfig, error) {
	s.mu.Lock()
	cfg, resolved, loader := s.cfg, s.resolved, s.loader
	s.mu.Unlock()

	if !resolved {
		if loader == nil {
			return QueryConfig{}, gerrors.New(gerrors.InvalidConfiguration,
				"no redis password query config registered")
		}

		loaded := loader()

		s.mu.Lock()
		if !s.resolved {
			s.cfg = loaded
			s.resolved = true
		}
		cfg = s.cfg
		s.mu.Unlock()
	}

	if cfg.API == "" {
		return QueryConfig{}, gerrors.New(gerrors.InvalidConfiguration,
			"redis password query api is empty")
	}

	return cfg, nil
}

// dbInstPasswd returns the cluster password, fetching it once on a cache miss.
func (s *service) dbInstPasswd(
	bkCloudID, clusterID int, machineType haprobe.DbmMetadataMachineType,
) (string, error) {
	key := instanceCacheKey(clusterID, componentName(machineType))

	if passwd, ok := s.cache.Get(key); ok {
		return passwd, nil
	}

	if _, err, _ := s.inflight.Do(key, func() (any, error) {
		return nil, s.fetchInstances(bkCloudID, []int{clusterID})
	}); err != nil {
		return "", err
	}

	passwd, ok := s.cache.Get(key)
	if !ok {
		return "", gerrors.Newf(gerrors.NotExist,
			"no redis password, cluster_id: %d, machine_type: %s", clusterID, machineType)
	}

	return passwd, nil
}

// machinePasswd returns the machine password, fetching it once on a cache miss.
func (s *service) machinePasswd(bkCloudID int) (string, error) {
	key := machineCacheKey(bkCloudID)

	if passwd, ok := s.cache.Get(key); ok {
		return passwd, nil
	}

	if _, err, _ := s.inflight.Do(key, func() (any, error) {
		return nil, s.fetchMachine(bkCloudID, key)
	}); err != nil {
		return "", err
	}

	passwd, ok := s.cache.Get(key)
	if !ok {
		return "", gerrors.Newf(gerrors.NotExist,
			"no redis machine password, bk_cloud_id: %d", bkCloudID)
	}

	return passwd, nil
}

// batchFill queries the clusters that are not cached yet, in batches.
func (s *service) batchFill(bkCloudID int, clusterIDs []int) error {
	pending := make([]int, 0, len(clusterIDs))
	seen := make(map[int]struct{}, len(clusterIDs))

	for _, clusterID := range clusterIDs {
		if _, dup := seen[clusterID]; dup {
			continue
		}
		seen[clusterID] = struct{}{}

		// One query covers every component, so any hit means the cluster is done.
		if _, ok := s.cache.Get(instanceCacheKey(clusterID, componentRedis)); ok {
			continue
		}
		if _, ok := s.cache.Get(instanceCacheKey(clusterID, componentRedisProxy)); ok {
			continue
		}

		pending = append(pending, clusterID)
	}

	var firstErr error
	for start := 0; start < len(pending); start += maxBatchInstances {
		end := min(start+maxBatchInstances, len(pending))

		if err := s.fetchInstances(bkCloudID, pending[start:end]); err != nil {
			logger.Warn("failed to prefetch redis passwords, cluster_ids: %v, errmsg: %s",
				pending[start:end], err)
			if firstErr == nil {
				firstErr = err
			}
		}
	}

	return firstErr
}

// fetchInstances caches every component the service returns for the given
// clusters, not just the one the caller asked for.
func (s *service) fetchInstances(bkCloudID int, clusterIDs []int) error {
	if len(clusterIDs) == 0 {
		return nil
	}

	instances := make([]passwdInstance, 0, len(clusterIDs))
	for _, clusterID := range clusterIDs {
		instances = append(instances, passwdInstance{
			IP:        strconv.Itoa(clusterID),
			Port:      0,
			BkCloudID: bkCloudID,
		})
	}

	users := []passwdUser{
		{UserName: userInstanceDefault, Component: componentRedis},
		{UserName: userInstanceDefault, Component: componentRedisProxy},
	}

	// One password per instance and user, plus room for an over-reporting service.
	items, err := s.query(bkCloudID, instances, users, len(instances)*2+1)
	if err != nil {
		return err
	}

	for _, item := range items {
		passwd, decodeErr := decodePasswd(item.Password)
		if decodeErr != nil {
			logger.Warn("failed to decode redis password, ip: %s(cluster_id), component: %s, errmsg: %s",
				item.IP, item.Component, decodeErr)
			continue
		}

		s.cache.Set(cacheKey(item.IP, item.Component), passwd, passwdExpiration())
	}

	return nil
}

// fetchMachine caches the first machine password the service returns.
func (s *service) fetchMachine(bkCloudID int, key string) error {
	// The pseudo instance sits in cloud area 0 even though the request does not.
	instances := []passwdInstance{{IP: machineInstanceIP, Port: 0, BkCloudID: 0}}
	users := []passwdUser{{UserName: userMachineDefault, Component: componentRedis}}

	items, err := s.query(bkCloudID, instances, users, 1)
	if err != nil {
		return err
	}

	for _, item := range items {
		passwd, decodeErr := decodePasswd(item.Password)
		if decodeErr != nil {
			logger.Warn("failed to decode redis machine password, errmsg: %s", decodeErr)
			continue
		}

		s.cache.Set(key, passwd, passwdExpiration())
		return nil
	}

	return nil
}

// decodePasswd decodes a password as returned by the service.
func decodePasswd(encoded string) (string, error) {
	decoded, err := base64.StdEncoding.DecodeString(encoded)
	if err != nil {
		return "", gerrors.NewE(gerrors.InvalidParameter, err)
	}

	return string(decoded), nil
}

// componentName maps a machine type onto the component holding its credentials.
func componentName(machineType haprobe.DbmMetadataMachineType) string {
	switch machineType {
	case haprobe.DbmMetadataMachineTypeTwemProxy, haprobe.DbmMetadataMachineTypePredixy:
		return componentRedisProxy
	case haprobe.DbmMetadataMachineTypeTendisCache,
		haprobe.DbmMetadataMachineTypeTendisPlus,
		haprobe.DbmMetadataMachineTypeTendisSSD:
		return componentRedis
	default:
		return componentRedisProxyAdmin
	}
}

// instanceCacheKey builds the cache key of one cluster component.
func instanceCacheKey(clusterID int, component string) string {
	return cacheKey(strconv.Itoa(clusterID), component)
}

// cacheKey joins a cluster id and a component. Response items carry the cluster id
// in their ip field, so they build their key through here too.
func cacheKey(clusterID, component string) string {
	return fmt.Sprintf("%s-%s", clusterID, component)
}

// machineCacheKey builds the cache key of the machine password of a cloud area.
func machineCacheKey(bkCloudID int) string {
	return fmt.Sprintf("machine-%d", bkCloudID)
}

// passwdExpiration returns a jittered TTL.
func passwdExpiration() time.Duration {
	return passwdTTL + time.Duration(rand.Int64N(int64(passwdTTLJitter)))
}
