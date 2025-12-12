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

package redis

import (
	"context"
	"fmt"
	"time"

	"dbm-services/common/dbha-v2/internal/probe/harvester/base"
	"dbm-services/common/dbha-v2/pkg/hanet"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"

	"github.com/redis/go-redis/v9"
)

type collector struct {
	base.Collector

	clusterType haprobe.DbmMetadataClusterType
	machineType haprobe.DbmMetadataMachineType
	accessLayer haprobe.DbmMetadataAccessLayerType
	password    string
	endpoint    *hanet.Endpoint
	timeout     time.Duration
	rdb         *redis.Client
	ctx         context.Context
}

func (c *collector) open() (*haprobe.DbEvent, error) {
	addr := fmt.Sprintf("%s:%d", c.endpoint.Host, c.endpoint.Port)

	timeout := c.timeout
	if timeout <= 0 {
		timeout = 3 * time.Second
	}

	c.ctx = context.Background()
	c.rdb = redis.NewClient(&redis.Options{
		Addr:         addr,
		Password:     c.password,
		DialTimeout:  timeout,
		ReadTimeout:  timeout,
		WriteTimeout: timeout,
		PoolSize:     1,
		MinIdleConns: 0,
	})

	if err := c.rdb.Ping(c.ctx).Err(); err != nil {
		logger.Warn("failed to connect to redis %s, %v", addr, err)
		event := &haprobe.DbEvent{
			Name:       haprobe.DbEventNameDetectFailure,
			Reason:     haprobe.DbEventNameReasonConnectionException,
			DbTypeName: haprobe.DbTypeRedis,
			Endpoint:   c.endpoint,
			Message:    err.Error(),
		}
		return event, err
	}

	return nil, nil
}

func (c *collector) close() {
	if c.rdb != nil {
		err := c.rdb.Close()
		if err != nil {
			return
		}
	}
}

func (c *collector) info(section string) (string, error) {
	if c.rdb == nil {
		return "", fmt.Errorf("redis client is nil")
	}

	var result string
	var err error

	if section == "" {
		result, err = c.rdb.Info(c.ctx).Result()
	} else {
		result, err = c.rdb.Info(c.ctx, section).Result()
	}

	return result, err
}

func (c *collector) infoMap(section string) (map[string]string, error) {
	infoStr, err := c.info(section)
	if err != nil {
		return nil, err
	}

	return parseRedisInfoToMap(infoStr), nil
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

func (c *collector) isRedisCluster() bool {
	return c.accessLayer == haprobe.DbmMetadataAccessLayerTypeStorage &&
		(c.clusterType == haprobe.DbmMetadataClusterTypePredixyRedisCluster)
}

func (c *collector) obtainTwemproxyStatus() (*haprobe.RedisTwemproxyStatus, error) {
	// TODO
	return &haprobe.RedisTwemproxyStatus{}, nil
}

func (c *collector) obtainPredixyStatus() (*haprobe.RedisPredixyStatus, error) {
	// TODO
	return &haprobe.RedisPredixyStatus{}, nil
}

func (c *collector) obtainTendisCacheStatus() (*haprobe.RedisTendisCacheStatus, error) {
	infoStr, err := c.info("")
	if err != nil {
		return nil, err
	}

	status := &haprobe.RedisTendisCacheStatus{}
	parseInfoToTendisCacheStatus(infoStr, status)
	return status, nil
}

func (c *collector) obtainTendisSSDStatus() (*haprobe.RedisTendisSSDStatus, error) {
	// TODO
	return &haprobe.RedisTendisSSDStatus{}, nil
}

func (c *collector) obtainTendisPlusStatus() (*haprobe.RedisTendisPlusStatus, error) {
	infoStr, err := c.info("")
	if err != nil {
		return nil, err
	}

	status := &haprobe.RedisTendisPlusStatus{}
	parseInfoToTendisPlusStatus(infoStr, status)
	return status, nil
}

func (c *collector) obtainRedisClusterStatus() (*haprobe.RedisClusterStatus, error) {
	infoStr, err := c.info("")
	if err != nil {
		return nil, err
	}

	status := &haprobe.RedisClusterStatus{}
	parseInfoToRedisClusterStatus(infoStr, status)
	return status, nil
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
