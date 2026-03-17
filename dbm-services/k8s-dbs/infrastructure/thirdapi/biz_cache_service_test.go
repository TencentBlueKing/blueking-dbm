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
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// newBizCacheServiceForTest 仅供测试使用，绕过单例和环境变量
func newBizCacheServiceForTest(serverURL string) *BizCacheService {
	return &BizCacheService{
		bizAPIURL:   serverURL, // httptest 服务器地址，已含 http:// scheme
		appCode:     "test_app_code",
		appSecret:   "test_app_secret",
		ttl:         0, // 测试中不启动后台刷新
		validBizIDs: make(map[uint64]struct{}),
		stopCh:      make(chan struct{}),
	}
}

func respondBizJSON(w http.ResponseWriter, v interface{}) {
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(v)
}

// --- IsValidBizID tests ---

func TestIsValidBizID_ValidID(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// 验证鉴权 Header
		auth := r.Header.Get("X-Bkapi-Authorization")
		assert.NotEmpty(t, auth)
		assert.Contains(t, auth, "test_app_code")
		assert.Contains(t, auth, "test_app_secret")

		respondBizJSON(w, map[string]interface{}{
			"result":  true,
			"code":    "00",
			"data":    []map[string]interface{}{{"bk_biz_id": 75}, {"bk_biz_id": 100}},
			"message": nil,
		})
	}))
	defer srv.Close()

	svc := newBizCacheServiceForTest(srv.URL)
	// 手动改为 http（测试服务器不支持 https）
	svc.bizAPIURL = srv.URL

	err := svc.refresh()
	require.NoError(t, err)

	valid, err := svc.IsValidBizID(75)
	assert.NoError(t, err)
	assert.True(t, valid)

	valid, err = svc.IsValidBizID(100)
	assert.NoError(t, err)
	assert.True(t, valid)
}

func TestIsValidBizID_InvalidID(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		respondBizJSON(w, map[string]interface{}{
			"result":  true,
			"code":    "00",
			"data":    []map[string]interface{}{{"bk_biz_id": 75}},
			"message": nil,
		})
	}))
	defer srv.Close()

	svc := newBizCacheServiceForTest(srv.URL)
	err := svc.refresh()
	require.NoError(t, err)

	valid, err := svc.IsValidBizID(999)
	assert.NoError(t, err)
	assert.False(t, valid)
}

func TestIsValidBizID_URLNotConfigured(t *testing.T) {
	svc := &BizCacheService{
		bizAPIURL:   "",
		validBizIDs: make(map[uint64]struct{}),
		stopCh:      make(chan struct{}),
	}

	valid, err := svc.IsValidBizID(75)
	assert.Error(t, err)
	assert.False(t, valid)
	assert.Contains(t, err.Error(), "BKBASE_BIZ_API_URL")
}

func TestIsValidBizID_CacheNotReady(t *testing.T) {
	svc := &BizCacheService{
		bizAPIURL:   "some-host",
		validBizIDs: make(map[uint64]struct{}),
		loaded:      false,
		stopCh:      make(chan struct{}),
	}

	valid, err := svc.IsValidBizID(75)
	assert.Error(t, err)
	assert.False(t, valid)
	assert.Contains(t, err.Error(), "缓存尚未就绪")
}

// --- refresh tests ---

func TestRefresh_Success(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		respondBizJSON(w, map[string]interface{}{
			"result": true,
			"code":   "00",
			"data": []map[string]interface{}{
				{"bk_biz_id": 10},
				{"bk_biz_id": 20},
				{"bk_biz_id": 30},
			},
			"message": nil,
		})
	}))
	defer srv.Close()

	svc := newBizCacheServiceForTest(srv.URL)
	err := svc.refresh()

	assert.NoError(t, err)
	assert.True(t, svc.loaded)
	assert.Len(t, svc.validBizIDs, 3)

	_, ok10 := svc.validBizIDs[10]
	_, ok20 := svc.validBizIDs[20]
	_, ok30 := svc.validBizIDs[30]
	assert.True(t, ok10)
	assert.True(t, ok20)
	assert.True(t, ok30)
}

func TestRefresh_APIError(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		msg := "internal error"
		respondBizJSON(w, map[string]interface{}{
			"result":  false,
			"code":    "50",
			"data":    nil,
			"message": msg,
		})
	}))
	defer srv.Close()

	svc := newBizCacheServiceForTest(srv.URL)
	err := svc.refresh()

	assert.Error(t, err)
	assert.Contains(t, err.Error(), "bk-base 返回失败")
	assert.False(t, svc.loaded)
}

func TestRefresh_HTTPError(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
	}))
	defer srv.Close()

	svc := newBizCacheServiceForTest(srv.URL)
	err := svc.refresh()

	assert.Error(t, err)
	assert.False(t, svc.loaded)
}

func TestRefresh_PreservesOldOnFailure(t *testing.T) {
	callCount := 0
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		callCount++
		if callCount == 1 {
			// 首次成功
			respondBizJSON(w, map[string]interface{}{
				"result":  true,
				"code":    "00",
				"data":    []map[string]interface{}{{"bk_biz_id": 42}},
				"message": nil,
			})
		} else {
			// 第二次失败
			respondBizJSON(w, map[string]interface{}{
				"result":  false,
				"code":    "99",
				"data":    nil,
				"message": "gateway timeout",
			})
		}
	}))
	defer srv.Close()

	svc := newBizCacheServiceForTest(srv.URL)

	// 首次刷新成功
	err := svc.refresh()
	require.NoError(t, err)
	assert.True(t, svc.loaded)
	_, ok := svc.validBizIDs[42]
	assert.True(t, ok)

	// 第二次刷新失败 — 旧缓存应保留
	err = svc.refresh()
	assert.Error(t, err)
	assert.True(t, svc.loaded) // 仍为 true
	_, ok = svc.validBizIDs[42]
	assert.True(t, ok) // 旧数据仍在
}
