/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package cmutil TODO
package cmutil

import (
	"time"

	"dbm-services/common/go-pubpkg/logger"

	"github.com/pkg/errors"
)

// RetryConfig TODO
type RetryConfig struct {
	Times     int           // 重试次数
	DelayTime time.Duration // 每次重试间隔
}

// RetriesExceeded TODO
// retries exceeded
const RetriesExceeded = "retries exceeded"

// Retry 重试
// 第 0 次也需要 delay 再运行
func Retry(r RetryConfig, f func() error) (err error) {
	for i := 0; i < r.Times; i++ {
		if err = f(); err == nil {
			return nil
		}
		logger.Warn("第%d次重试,函数错误:%s", i, err.Error())
		time.Sleep(r.DelayTime)
	}
	if err != nil {
		return errors.Wrap(err, RetriesExceeded)
	}
	return
}

// DecreasingRetry 递减Sleep重试
func DecreasingRetry() (err error) {
	return
}
