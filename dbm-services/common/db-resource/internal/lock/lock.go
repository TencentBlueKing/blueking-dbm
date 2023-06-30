/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package lock TODO
package lock

import (
	"context"
	"fmt"
	"time"

	"dbm-services/common/db-resource/internal/config"
	"dbm-services/common/go-pubpkg/logger"

	"github.com/go-redis/redis/v8"
)

var rdb *redis.Client

// init TODO
func init() {
	logger.Info("redis addr %s", config.AppConfig.Redis.Addr)
	rdb = redis.NewClient(&redis.Options{
		Addr:     config.AppConfig.Redis.Addr,
		Password: config.AppConfig.Redis.Password,
		DB:       0,
	})
}

// RedisLock TODO
type RedisLock struct {
	Name    string
	RandKey string
	Expiry  time.Duration
}

// TryLock TODO
func (r *RedisLock) TryLock() (err error) {
	ok, err := rdb.SetNX(context.TODO(), r.Name, r.RandKey, r.Expiry).Result()
	if err != nil {
		return err
	}
	if !ok {
		return fmt.Errorf("setnx %s lock failed", r.Name)
	}
	return nil
}

// Unlock TODO
func (r *RedisLock) Unlock() (err error) {
	luaStript := `if redis.call('get',KEYS[1]) == ARGV[1] then return redis.call('del',KEYS[1]) else return 0 end`
	v, err := rdb.Eval(context.TODO(), luaStript, []string{r.Name}, []interface{}{r.RandKey}).Int()
	if err != nil {
		logger.Error("del lock failed %s", err.Error())
		return err
	}
	if v != 1 {
		return fmt.Errorf("unlock failed,key is %s,val %s", r.Name, r.RandKey)
	}
	return nil
}
