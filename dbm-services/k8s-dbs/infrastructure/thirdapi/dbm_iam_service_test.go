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

	"k8s-dbs/infrastructure/response"
)

// newDbmAPIServiceForTest 仅供测试使用，绕过 sync.Once 创建实例
func newDbmAPIServiceForTest(apiURL string) *DbmAPIService {
	return &DbmAPIService{
		syncDataAPIURL:   apiURL,
		innerBkAppCode:   "test_inner_code",
		innerBkAppSecret: "test_inner_secret",
		dbmAuthAPIURL:    apiURL,
	}
}

func newTestServer(t *testing.T, handler http.HandlerFunc) (*httptest.Server, *DbmAPIService) {
	t.Helper()
	srv := httptest.NewServer(handler)
	svc := newDbmAPIServiceForTest(srv.Listener.Addr().String())
	return srv, svc
}

func respondJSON(w http.ResponseWriter, v interface{}) {
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(v)
}

// --- SimpleCheckAllowed tests ---

func TestSimpleCheckAllowed_Allowed(t *testing.T) {
	srv, svc := newTestServer(t, func(w http.ResponseWriter, r *http.Request) {
		// 验证认证 Header 中使用的是环境变量中的内部凭据
		auth := r.Header.Get("X-Bkapi-Authorization")
		assert.NotEmpty(t, auth)
		assert.Contains(t, auth, "user1")
		assert.Contains(t, auth, "test_inner_code")
		assert.Contains(t, auth, "test_inner_secret")

		// 验证请求体格式
		var body map[string]interface{}
		require.NoError(t, json.NewDecoder(r.Body).Decode(&body))
		assert.Equal(t, "k8s_surrealdb_apply", body["action_id"])
		assert.Equal(t, float64(3), body["bk_biz_id"])
		assert.Equal(t, true, body["is_raise_exception"])

		respondJSON(w, map[string]interface{}{
			"result":  true,
			"code":    0,
			"data":    true,
			"message": "",
		})
	})
	defer srv.Close()

	allowed, applyData, err := svc.SimpleCheckAllowed("user1", "k8s_surrealdb_apply", 3, "")
	require.NoError(t, err)
	assert.True(t, allowed)
	assert.Nil(t, applyData)
}

func TestSimpleCheckAllowed_NotAllowed_WithApplyData(t *testing.T) {
	srv, svc := newTestServer(t, func(w http.ResponseWriter, r *http.Request) {
		respondJSON(w, map[string]interface{}{
			"result": false,
			"code":   response.PermissionDeniedCode,
			"data": map[string]interface{}{
				"permission": map[string]interface{}{
					"system_id":   "bk_dbm",
					"system_name": "数据库管理",
					"actions": []map[string]interface{}{
						{
							"id":   "k8s_surrealdb_apply",
							"name": "K8s SurrealDB 部署",
							"related_resource_types": []map[string]interface{}{
								{
									"system_id":   "bk_cmdb",
									"system_name": "配置平台",
									"type":        "biz",
									"type_name":   "业务",
									"instances": [][]map[string]interface{}{
										{{"type": "biz", "type_name": "业务", "id": "3", "name": "DBA"}},
									},
								},
							},
						},
					},
				},
				"apply_url": "https://iam.example.com/apply?cache_id=abc123",
			},
			"message": "当前用户无 [K8s SurrealDB 部署] 权限（9900403）",
		})
	})
	defer srv.Close()

	allowed, applyData, err := svc.SimpleCheckAllowed("example", "k8s_surrealdb_apply", 3, "")
	require.NoError(t, err)
	assert.False(t, allowed)
	require.NotNil(t, applyData)
	assert.Equal(t, "https://iam.example.com/apply?cache_id=abc123", applyData.ApplyURL)
	assert.Equal(t, "bk_dbm", applyData.Permission.SystemID)
	require.Len(t, applyData.Permission.Actions, 1)
	assert.Equal(t, "k8s_surrealdb_apply", applyData.Permission.Actions[0].ID)
}

func TestSimpleCheckAllowed_NotAllowed_NoData(t *testing.T) {
	srv, svc := newTestServer(t, func(w http.ResponseWriter, r *http.Request) {
		// is_raise_exception=false 的情况（实际不会发生，但测试 code=0 + data=false）
		respondJSON(w, map[string]interface{}{
			"result":  true,
			"code":    0,
			"data":    false,
			"message": "",
		})
	})
	defer srv.Close()

	allowed, applyData, err := svc.SimpleCheckAllowed("user1", "k8s_surrealdb_apply", 3, "")
	require.NoError(t, err)
	assert.False(t, allowed)
	assert.Nil(t, applyData)
}

func TestSimpleCheckAllowed_DBMError(t *testing.T) {
	srv, svc := newTestServer(t, func(w http.ResponseWriter, r *http.Request) {
		respondJSON(w, map[string]interface{}{
			"result":  false,
			"code":    8700500,
			"data":    nil,
			"message": "系统错误",
		})
	})
	defer srv.Close()

	allowed, _, err := svc.SimpleCheckAllowed("user1", "k8s_surrealdb_apply", 3, "")
	assert.Error(t, err)
	assert.False(t, allowed)
	assert.Contains(t, err.Error(), "DBM simple_check_allowed 返回失败")
}

func TestSimpleCheckAllowed_HTTPError(t *testing.T) {
	srv, svc := newTestServer(t, func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
	})
	defer srv.Close()

	allowed, _, err := svc.SimpleCheckAllowed("user1", "k8s_surrealdb_apply", 3, "")
	assert.Error(t, err)
	assert.False(t, allowed)
}

func TestSimpleCheckAllowed_AuthAPIURLNotConfigured(t *testing.T) {
	svc := &DbmAPIService{
		syncDataAPIURL:   "localhost:8080",
		innerBkAppCode:   "test_code",
		innerBkAppSecret: "test_secret",
		dbmAuthAPIURL:    "",
	}

	allowed, applyData, err := svc.SimpleCheckAllowed("user1", "k8s_surrealdb_apply", 3, "")
	assert.Error(t, err)
	assert.False(t, allowed)
	assert.Nil(t, applyData)
	assert.Contains(t, err.Error(), "DBM_AUTH_API_URL")
}

func TestSimpleCheckAllowed_RequestBodyFormat(t *testing.T) {
	srv, svc := newTestServer(t, func(w http.ResponseWriter, r *http.Request) {
		var body map[string]interface{}
		require.NoError(t, json.NewDecoder(r.Body).Decode(&body))

		// 验证请求体格式符合 simple_check_allowed
		assert.Contains(t, body, "action_id")
		assert.Contains(t, body, "bk_biz_id")
		assert.Contains(t, body, "resource_id")
		assert.Contains(t, body, "is_raise_exception")

		// 不应有 action_ids、resources 等 check_allowed 的字段
		assert.NotContains(t, body, "action_ids")
		assert.NotContains(t, body, "resources")
		assert.NotContains(t, body, "bk_username")

		respondJSON(w, map[string]interface{}{
			"result":  true,
			"code":    0,
			"data":    true,
			"message": "",
		})
	})
	defer srv.Close()

	_, _, err := svc.SimpleCheckAllowed("user1", "k8s_surrealdb_apply", 100465, "cluster-1")
	require.NoError(t, err)
}
