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

package redisswitch

import (
	"context"
	"fmt"
	"strconv"
	"strings"
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchcore"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/storage/haredis"
)

const (
	defaultRedisSwitchTimeout  = 10 * time.Second
	defaultRedisCommandTimeout = 10 * time.Second

	// redisSwitchDB is used by SLAVEOF.
	redisSwitchDB = 0
	// redisHeartbeatDB is used by INFO/GET heartbeat.
	redisHeartbeatDB = 1
)

func redisCommandTimeout() time.Duration {
	d := config.Cfg.Workflow.SwitchFlow.Redis.CommandTimeout
	if d <= 0 {
		return defaultRedisCommandTimeout
	}
	return d
}

func (ins *RedisStorageSwitchInstance) commandContext() (context.Context, context.CancelFunc) {
	timeout := ins.Timeout
	if timeout <= 0 {
		timeout = redisCommandTimeout()
	}
	return context.WithTimeout(context.Background(), timeout)
}

// buildRedisConn builds a redis connection.
func (ins *RedisStorageSwitchInstance) buildRedisConn(ip string, port int, db int) (*haredis.Client, error) {
	if err := ins.ensurePassword(); err != nil {
		return nil, err
	}

	cmdTimeout := ins.Timeout
	if cmdTimeout <= 0 {
		cmdTimeout = redisCommandTimeout()
	}

	return haredis.NewClient(
		haredis.OptionIP(ip),
		haredis.OptionPort(port),
		haredis.OptionPassword(ins.Password),
		haredis.OptionDB(db),
		haredis.OptionDialTimeout(switchcore.DbConnectTimeout()),
		haredis.OptionReadWriteTimeout(cmdTimeout),
	)
}

// parseRedisInfo parses the redis info string into a map.
// the return map is guaranteed to be non-nil.
func parseRedisInfo(info string) map[string]string {
	infoRet := make(map[string]string)
	infoList := strings.Split(info, "\n")
	for _, infoItem := range infoList {
		infoItem = strings.TrimSpace(infoItem)
		if strings.HasPrefix(infoItem, "#") {
			continue
		}
		if len(infoItem) == 0 {
			continue
		}
		list01 := strings.SplitN(infoItem, ":", 2)
		if len(list01) < 2 {
			continue
		}
		infoRet[strings.TrimSpace(list01[0])] = strings.TrimSpace(list01[1])
	}
	return infoRet
}

// instanceHeartbeatKey is the dbmon key written by MSET, {ip}:{port}:time.
func instanceHeartbeatKey(ip string, port int) string {
	return fmt.Sprintf("%s:%d:time", ip, port)
}

// kvStoreHeartbeatKey is the adminset key dbmon writes once for every kvstore.
func kvStoreHeartbeatKey(ip string, port int) string {
	return fmt.Sprintf("%s_%d:heartbeat", ip, port)
}

// parseKvstoreCount parses the kvstorecount result:
//
//	[kvstorecount, count]
func parseKvstoreCount(raw []interface{}) (int, error) {
	if len(raw) < 2 || raw[1] == nil {
		return 0, gerrors.Newf(gerrors.Failure, "kvstorecount result is empty")
	}
	countText, ok := raw[1].(string)
	if !ok {
		return 0, gerrors.Newf(gerrors.Failure, "kvstorecount value is not a string")
	}
	count, err := strconv.Atoi(countText)
	if err != nil || count <= 0 {
		return 0, gerrors.Newf(gerrors.Failure, "kvstorecount value is invalid: %s", countText)
	}
	return count, nil
}

// parseAdmingetHeartbeat parses adminget output:
//
//	[[storeID, unixSeconds], ...]
func parseAdmingetHeartbeat(raw interface{}) (map[int]int64, error) {
	rows, ok := raw.([]interface{})
	if !ok {
		return nil, gerrors.Newf(gerrors.Failure, "adminget result is not a list")
	}
	heartbeats := make(map[int]int64, len(rows))
	for _, row := range rows {
		pair, ok := row.([]interface{})
		if !ok || len(pair) != 2 || pair[0] == nil || pair[1] == nil {
			continue
		}
		storeText, ok := pair[0].(string)
		if !ok {
			continue
		}
		valueText, ok := pair[1].(string)
		if !ok {
			continue
		}
		storeID, err := strconv.Atoi(storeText)
		if err != nil {
			continue
		}
		unixSec, err := strconv.ParseInt(valueText, 10, 64)
		if err != nil {
			return nil, gerrors.Newf(gerrors.Failure, "kvstore %d heartbeat is not a unix timestamp: %s", storeID, valueText)
		}
		heartbeats[storeID] = unixSec
	}
	return heartbeats, nil
}
