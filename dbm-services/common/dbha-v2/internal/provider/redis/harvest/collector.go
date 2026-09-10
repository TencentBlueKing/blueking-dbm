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

package harvest

import (
	"context"
	"fmt"
	"strings"
	"time"

	"dbm-services/common/dbha-v2/internal/probe/harvester/base"
	"dbm-services/common/dbha-v2/pkg/hanet"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"

	"github.com/redis/go-redis/v9"
)

const (
	// redisProbeDB is the DB index selected before the write probe, aligned with v1.
	redisProbeDB = "1"

	// redisProbeKeyPrefix is the fixed prefix of the write probe key.
	redisProbeKeyPrefix = "dbha:probe"

	// redisProbeValueLayout is the timestamp layout of the write probe value, aligned with v1.
	redisProbeValueLayout = "2006-01-02 15:04:05"

	// redis auth failure substrings, aligned with v1 CheckRedisErrIsAuthFail.
	redisAuthErrorNoauth      = "NOAUTH Authentication"
	redisAuthErrorWrongpass   = "WRONGPASS invalid"
	redisAuthErrorInvalidPass = "invalid password"
	redisAuthErrorPermDeny    = "auth permission deny"
)

type collector struct {
	base.Collector

	clusterType  haprobe.DbmMetadataClusterType
	machineType  haprobe.DbmMetadataMachineType
	accessLayer  haprobe.DbmMetadataAccessLayerType
	instanceRole haprobe.DbmMetadataInstanceRole
	user         string
	password     string
	endpoint     *hanet.Endpoint
	timeout      time.Duration
	rdb          *redis.Client
}

// open builds the redis client and pings it to establish the connection and
// complete authentication. The error is classified into a connection or auth
// DbEvent.
func (c *collector) open(ctx context.Context) (*haprobe.DbEvent, error) {
	addr := c.endpoint.Addr()

	timeout := c.timeout
	if timeout <= 0 {
		timeout = 3 * time.Second
	}

	c.rdb = redis.NewClient(&redis.Options{
		Addr:         addr,
		Username:     c.user,
		Password:     c.password,
		DialTimeout:  timeout,
		ReadTimeout:  timeout,
		WriteTimeout: timeout,
		PoolSize:     1,
		MinIdleConns: 0,
	})

	if err := c.rdb.Ping(ctx).Err(); err != nil {
		logger.Warn("failed to connect to redis, endpoint: %s, errmsg: %s", addr, err)
		return c.classifyOpenError(err), err
	}

	return nil, nil
}

func (c *collector) close() {
	if c.rdb == nil {
		return
	}
	if err := c.rdb.Close(); err != nil {
		logger.Warn("failed to close redis db, errmsg: %s", err)
	}
}

// isAuthError reports whether err is a redis authentication failure.
func isAuthError(err error) bool {
	if err == nil {
		return false
	}
	errStr := err.Error()
	return strings.Contains(errStr, redisAuthErrorNoauth) ||
		strings.Contains(errStr, redisAuthErrorWrongpass) ||
		strings.Contains(errStr, redisAuthErrorInvalidPass) ||
		strings.Contains(errStr, redisAuthErrorPermDeny)
}

// connectionExceptionEvent builds a connection-exception DbEvent.
func (c *collector) connectionExceptionEvent(err error) *haprobe.DbEvent {
	return &haprobe.DbEvent{
		Name:       haprobe.DbEventNameDetectFailure,
		Reason:     haprobe.DbEventNameReasonConnectionException,
		DbTypeName: haprobe.DbTypeRedis,
		Endpoint:   c.endpoint,
		Message:    err.Error(),
	}
}

// authExceptionEvent builds an auth-exception DbEvent.
func (c *collector) authExceptionEvent(err error) *haprobe.DbEvent {
	return &haprobe.DbEvent{
		Name:       haprobe.DbEventNameDetectRedisAuthFailureV1,
		Reason:     haprobe.DbEventNameReasonAuthException,
		DbTypeName: haprobe.DbTypeRedis,
		Endpoint:   c.endpoint,
		Message:    err.Error(),
	}
}

// classifyOpenError classifies the open (Ping) error into a DbEvent. Auth errors
// map to auth events, anything else maps to connection events.
func (c *collector) classifyOpenError(err error) *haprobe.DbEvent {
	if isAuthError(err) {
		return c.authExceptionEvent(err)
	}
	return c.connectionExceptionEvent(err)
}

// classifyCommandError classifies a command error. Auth errors map to auth
// events, anything else returns nil and is recorded as State=failed.
func (c *collector) classifyCommandError(err error) *haprobe.DbEvent {
	if isAuthError(err) {
		return c.authExceptionEvent(err)
	}
	return nil
}

// obtainReplicationInfo runs INFO Replication and returns the parsed key-value map.
// Callers read the fields they need (e.g. "role") from the returned map.
func (c *collector) obtainReplicationInfo(ctx context.Context) (map[string]string, error) {
	infoStr, err := c.rdb.Info(ctx, "Replication").Result()
	if err != nil {
		return nil, err
	}
	return parseRedisInfoToMap(infoStr), nil
}

// obtainHeartbeat runs SELECT and SET write probe and returns the raw results.
func (c *collector) obtainHeartbeat(ctx context.Context) (string, string, error) {
	selRsp, err := c.rdb.Do(ctx, "SELECT", redisProbeDB).Result()
	if err != nil {
		return "", "", err
	}
	// On success redis SELECT always replies with the simple string "OK"
	// (RESP2/RESP3, see https://redis.io/docs/latest/commands/select/); any
	// failure such as "ERR DB index is out of range" is returned as err above.
	// So no extra strings.Contains(selectResult, "OK") check is needed, unlike v1.
	selectResult, ok := selRsp.(string)
	if !ok {
		return "", "", fmt.Errorf("select result type is not string")
	}

	key := fmt.Sprintf("%s:%s:%d", redisProbeKeyPrefix, c.endpoint.Host, c.endpoint.Port)
	value := time.Now().Format(redisProbeValueLayout)

	setRsp, err := c.rdb.Do(ctx, "SET", key, value).Result()
	if err != nil {
		return selectResult, "", err
	}
	setResult, ok := setRsp.(string)
	if !ok {
		return selectResult, "", fmt.Errorf("set result type is not string")
	}

	return selectResult, setResult, nil
}

// obtainReadCheck runs TYPE twemproxy_mon read-only probe.
func (c *collector) obtainReadCheck(ctx context.Context) error {
	_, err := c.rdb.Type(ctx, "twemproxy_mon").Result()
	return err
}

func (c *collector) isTwemproxy() bool {
	return c.accessLayer == haprobe.DbmMetadataAccessLayerTypeProxy &&
		c.machineType == haprobe.DbmMetadataMachineTypeTwemProxy
}

func (c *collector) isPredixy() bool {
	return c.accessLayer == haprobe.DbmMetadataAccessLayerTypeProxy &&
		c.machineType == haprobe.DbmMetadataMachineTypePredixy
}

func (c *collector) isTendisCache() bool {
	return c.accessLayer == haprobe.DbmMetadataAccessLayerTypeStorage &&
		c.machineType == haprobe.DbmMetadataMachineTypeTendisCache
}

func (c *collector) isTendisSSD() bool {
	return c.accessLayer == haprobe.DbmMetadataAccessLayerTypeStorage &&
		c.machineType == haprobe.DbmMetadataMachineTypeTendisSSD
}

func (c *collector) isTendisPlus() bool {
	return c.accessLayer == haprobe.DbmMetadataAccessLayerTypeStorage &&
		c.machineType == haprobe.DbmMetadataMachineTypeTendisPlus
}

// isProxyInstance reports whether the collector is a supported proxy instance.
// It matches the (clusterType, machineType) pair to guard against an unknown
// cluster type being probed as a known proxy.
func (c *collector) isProxyInstance() bool {
	switch {
	case c.isTwemproxy():
		return c.clusterType == haprobe.DbmMetadataClusterTypeTwemproxyRedis ||
			c.clusterType == haprobe.DbmMetadataClusterTypeTwemproxyTendisSSD
	case c.isPredixy():
		return c.clusterType == haprobe.DbmMetadataClusterTypePredixyRedisCluster ||
			c.clusterType == haprobe.DbmMetadataClusterTypePredixyTendisplusCluster ||
			c.clusterType == haprobe.DbmMetadataClusterTypePredixyTendisplusInstance
	default:
		return false
	}
}

// isStorageInstance reports whether the collector is a supported storage instance.
// It matches the (clusterType, machineType) pair; storage layers of autonomous
// clusters (PredixyRedisCluster / PredixyTendisplusCluster) are deliberately excluded.
func (c *collector) isStorageInstance() bool {
	switch {
	case c.isTendisCache():
		return c.clusterType == haprobe.DbmMetadataClusterTypeTwemproxyRedis ||
			c.clusterType == haprobe.DbmMetadataClusterTypeRedis
	case c.isTendisSSD():
		return c.clusterType == haprobe.DbmMetadataClusterTypeTwemproxyTendisSSD
	case c.isTendisPlus():
		return c.clusterType == haprobe.DbmMetadataClusterTypePredixyTendisplusInstance
	default:
		return false
	}
}

// shouldSkipStorage PredixyRedisCluster / PredixyTendisplusCluster only probe their proxy layer.
func (c *collector) shouldSkipStorage() bool {
	return c.accessLayer == haprobe.DbmMetadataAccessLayerTypeStorage &&
		(c.clusterType == haprobe.DbmMetadataClusterTypePredixyRedisCluster ||
			c.clusterType == haprobe.DbmMetadataClusterTypePredixyTendisplusCluster)
}

func (c *collector) obtainHostStatus() (*haprobe.HostMetric, error) {
	hostStatus := &haprobe.HostMetric{}
	if err := c.SetCpuStatus(hostStatus); err != nil {
		logger.Warn("failed to update CPU status, errmsg: %s", err)
	}

	if err := c.SetNetStatus(hostStatus); err != nil {
		logger.Warn("failed to update Net status, errmsg: %s", err)
	}

	if err := c.SetMemoryStatus(hostStatus); err != nil {
		logger.Warn("failed to update memory status, errmsg: %s", err)
	}

	if err := c.SetDiskStatus(hostStatus); err != nil {
		logger.Warn("failed to update disk status, errmsg: %s", err)
	}

	return hostStatus, nil
}
