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
	"strings"
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchcore"
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
