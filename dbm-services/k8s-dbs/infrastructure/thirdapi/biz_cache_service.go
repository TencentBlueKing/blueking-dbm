/*
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.

Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.

Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
https://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

package thirdapi

import (
	"encoding/json"
	"fmt"
	"log/slog"
	"strings"
	"sync"
	"time"

	"k8s-dbs/common/util"
	infresp "k8s-dbs/infrastructure/response"

	"k8s.io/utils/env"
)

const bizListPath = "/v4/meta/bizs/"
const bizCacheRefreshInterval = 10 * time.Minute

var (
	bizCacheInstance *BizCacheService
	bizCacheMu       sync.Mutex
)

// BizCacheService 缓存 bk-base 的有效业务 ID 集合，定时从网关刷新。
type BizCacheService struct {
	bizAPIURL string
	appCode   string
	appSecret string
	ttl       time.Duration

	mu          sync.RWMutex
	validBizIDs map[uint64]struct{}
	loaded      bool // 是否至少成功加载过一次

	stopCh chan struct{}
}

// GetBizCacheService 获取或创建 BizCacheService 单例
func GetBizCacheService() *BizCacheService {
	bizCacheMu.Lock()
	defer bizCacheMu.Unlock()

	if bizCacheInstance != nil {
		return bizCacheInstance
	}

	bizAPIURL := env.GetString("BKBASE_BIZ_API_URL", "")
	appCode := env.GetString("INNER_BK_APP_CODE", "")
	appSecret := env.GetString("INNER_BK_APP_SECRET", "")

	svc := &BizCacheService{
		bizAPIURL:   bizAPIURL,
		appCode:     appCode,
		appSecret:   appSecret,
		ttl:         bizCacheRefreshInterval,
		validBizIDs: make(map[uint64]struct{}),
		stopCh:      make(chan struct{}),
	}

	if bizAPIURL == "" {
		slog.Warn("BKBASE_BIZ_API_URL 未配置，bizID 校验将拒绝所有请求")
	} else {
		// 启动时同步拉取一次
		if fetchErr := svc.refresh(); fetchErr != nil {
			slog.Error("BizCacheService 首次拉取失败", "error", fetchErr)
		}
		// 后台 goroutine 定时刷新
		go svc.backgroundRefresh()
	}

	bizCacheInstance = svc
	slog.Info("BizCacheService 初始化完成", "bizAPIURL", bizAPIURL, "refreshInterval", bizCacheRefreshInterval)
	return svc
}

// IsValidBizID 校验 bizID 是否在缓存的有效集合中。
//   - URL 未配置: 返回 (false, error)
//   - 缓存尚未就绪（首次拉取失败）: 返回 (false, error)
//   - 正常校验: 返回 (bool, nil)
func (s *BizCacheService) IsValidBizID(bizID uint64) (bool, error) {
	if s.bizAPIURL == "" {
		return false, fmt.Errorf("BKBASE_BIZ_API_URL 未配置，无法校验业务 ID")
	}

	s.mu.RLock()
	defer s.mu.RUnlock()

	if !s.loaded {
		return false, fmt.Errorf("业务 ID 缓存尚未就绪")
	}

	_, ok := s.validBizIDs[bizID]
	return ok, nil
}

// Stop 停止后台刷新 goroutine
func (s *BizCacheService) Stop() {
	close(s.stopCh)
}

func (s *BizCacheService) backgroundRefresh() {
	ticker := time.NewTicker(s.ttl)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			if err := s.refresh(); err != nil {
				slog.Error("BizCacheService 定时刷新失败，保留旧缓存", "error", err)
			}
		case <-s.stopCh:
			slog.Info("BizCacheService 后台刷新已停止")
			return
		}
	}
}

// refresh 从 bk-base 网关拉取业务列表并更新缓存。
// 成功时替换整个缓存；失败时保留旧缓存不变。
func (s *BizCacheService) refresh() error {
	var url string
	if strings.HasPrefix(s.bizAPIURL, "http://") || strings.HasPrefix(s.bizAPIURL, "https://") {
		url = s.bizAPIURL + bizListPath
	} else {
		url = fmt.Sprintf("https://%s%s", s.bizAPIURL, bizListPath)
	}

	authHeader, err := json.Marshal(map[string]string{
		"bk_app_code":   s.appCode,
		"bk_app_secret": s.appSecret,
	})
	if err != nil {
		return fmt.Errorf("构建鉴权 Header 失败: %w", err)
	}

	options := &util.RequestOptions{
		Headers: map[string]string{
			"X-Bkapi-Authorization": string(authHeader),
		},
	}

	resp, err := util.BaseHTTPClient.GetWithResponse(url, options)
	if err != nil {
		return fmt.Errorf("HTTP 请求失败: %w", err)
	}

	var bizResp infresp.BkbaseBizResponse
	if err := util.BaseHTTPClient.ParseResponse(resp, &bizResp); err != nil {
		return fmt.Errorf("解析响应失败: %w", err)
	}

	if !bizResp.Result {
		msg := "<nil>"
		if bizResp.Message != nil {
			msg = *bizResp.Message
		}
		return fmt.Errorf("bk-base 返回失败: code=%s, message=%s", bizResp.Code, msg)
	}

	newSet := make(map[uint64]struct{}, len(bizResp.Data))
	for _, item := range bizResp.Data {
		newSet[item.BkBizID] = struct{}{}
	}

	s.mu.Lock()
	s.validBizIDs = newSet
	s.loaded = true
	s.mu.Unlock()

	slog.Info("BizCacheService 刷新完成", "count", len(newSet))
	return nil
}
