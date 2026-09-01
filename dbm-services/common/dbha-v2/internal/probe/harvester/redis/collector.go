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
	"bufio"
	"context"
	"fmt"
	"io"
	"net"
	"strings"
	"time"

	"dbm-services/common/dbha-v2/internal/probe/harvester/base"
	"dbm-services/common/dbha-v2/pkg/hanet"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"

	"github.com/redis/go-redis/v9"
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
	if c.rdb == nil {
		return
	}
	err := c.rdb.Close()
	if err != nil {
		logger.Warn("failed to close redis db, errmsg: %s", err)
		return
	}
}

func (c *collector) info(ctx context.Context, section string) (string, error) {
	if c.rdb == nil {
		return "", fmt.Errorf("redis client is not initialized")
	}

	if section == "" {
		return c.rdb.Info(ctx).Result()
	}
	return c.rdb.Info(ctx, strings.ToLower(section)).Result()
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

func (c *collector) obtainTwemproxyStatus(ctx context.Context) (*haprobe.RedisTwemproxyStatus, error) {
	addr := c.endpoint.Addr()

	conn, err := net.DialTimeout("tcp", addr, c.timeout)
	if err != nil {
		return nil, fmt.Errorf("failed to connect to twemproxy stats port:%s,errmsg: %w", addr, err)
	}
	defer conn.Close()

	if err := conn.SetReadDeadline(time.Now().Add(c.timeout)); err != nil {
		return nil, fmt.Errorf("failed to set read deadline: %w", err)
	}

	reader := bufio.NewReader(conn)
	data, err := io.ReadAll(reader)
	if err != nil {
		return nil, fmt.Errorf("failed to read twemproxy stats: %w", err)
	}

	status := &haprobe.RedisTwemproxyStatus{}
	parseInfoToTwemproxyStatus(data, status)
	return status, nil
}

func (c *collector) obtainPredixyStatus(ctx context.Context) (*haprobe.RedisPredixyStatus, error) {
	infoStr, err := c.info(ctx, "")
	if err != nil {
		return nil, err
	}

	status := &haprobe.RedisPredixyStatus{}
	parseInfoToPredixyStatus(infoStr, status)

	serversInfo, err := c.info(ctx, "Servers")
	if err != nil {
		logger.Warn("failed to get predixy servers info, errmsg: %s", err)
	} else {
		parsePredixyServersInfo(serversInfo, status)
	}

	return status, nil
}

func (c *collector) obtainTendisCacheStatus(ctx context.Context) (*haprobe.RedisTendisCacheStatus, error) {
	infoStr, err := c.info(ctx, "")
	if err != nil {
		return nil, err
	}

	status := &haprobe.RedisTendisCacheStatus{}
	parseInfoToTendisCacheStatus(infoStr, status)
	return status, nil
}

func (c *collector) obtainTendisSSDStatus(ctx context.Context) (*haprobe.RedisTendisSSDStatus, error) {
	infoStr, err := c.info(ctx, "")
	if err != nil {
		return nil, err
	}

	status := &haprobe.RedisTendisSSDStatus{}
	parseInfoToTendisSSDStatus(infoStr, status)
	return status, nil
}

func (c *collector) obtainTendisPlusStatus(ctx context.Context) (*haprobe.RedisTendisPlusStatus, error) {
	infoStr, err := c.info(ctx, "")
	if err != nil {
		return nil, err
	}

	status := &haprobe.RedisTendisPlusStatus{}
	parseInfoToTendisPlusStatus(infoStr, status)
	return status, nil
}

func (c *collector) obtainRedisClusterStatus(ctx context.Context) (*haprobe.RedisClusterStatus, error) {
	infoStr, err := c.info(ctx, "")
	if err != nil {
		return nil, err
	}

	status := &haprobe.RedisClusterStatus{}
	parseInfoToRedisClusterStatus(infoStr, status)
	return status, nil
}

func (c *collector) obtainHostStatus(ctx context.Context) (*haprobe.HostMetric, error) {
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
