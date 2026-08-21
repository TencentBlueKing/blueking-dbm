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

package middleware

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"k8s-dbs/common/constant"
	infresp "k8s-dbs/infrastructure/response"
)

// mockIAMChecker 实现 iamChecker 接口，供测试注入
type mockIAMChecker struct {
	allowed   bool
	applyData *infresp.ApplyData
	err       error
	called    bool
}

func (m *mockIAMChecker) SimpleCheckAllowed(_, _ string, _ int, _ string) (bool, *infresp.ApplyData, error) {
	m.called = true
	return m.allowed, m.applyData, m.err
}

// mockClusterTypeResolver 实现 ClusterTypeResolver 接口，供测试注入
type mockClusterTypeResolver struct {
	clusterType  string
	addonType    string
	dbmClusterID uint64
	err          error
}

func (m *mockClusterTypeResolver) Resolve(_ string, _ []byte) (*ResolveResult, error) {
	if m.err != nil {
		return nil, m.err
	}
	return &ResolveResult{ClusterType: m.clusterType, AddonType: m.addonType, DbmClusterID: m.dbmClusterID}, nil
}

// toJSON 将 map 序列化为 JSON bytes，用于测试
func toJSON(v interface{}) []byte {
	b, _ := json.Marshal(v)
	return b
}

// --- checkIAMPermission unit tests ---

func TestCheckIAMPermission_APINotInMapping(t *testing.T) {
	checker := &mockIAMChecker{allowed: false}
	resolver := &mockClusterTypeResolver{clusterType: "k8s_surrealdb_ha"}

	allowed, applyData, err := checkIAMPermission(checker, resolver, "unknown_api", toJSON(map[string]interface{}{}), "user1")

	assert.NoError(t, err)
	assert.True(t, allowed)
	assert.Nil(t, applyData)
}

func TestCheckIAMPermission_SkippedAPI_Passthrough(t *testing.T) {
	checker := &mockIAMChecker{}
	resolver := &mockClusterTypeResolver{clusterType: "k8s_surrealdb_ha"}

	// APIMetaAddonCategoryCreate 不在 APIToIAMAction 中，应跳过鉴权
	allowed, _, err := checkIAMPermission(checker, resolver, constant.APIMetaAddonCategoryCreate, toJSON(map[string]interface{}{}), "user1")

	assert.NoError(t, err)
	assert.True(t, allowed)
}

func TestCheckIAMPermission_ResolverError(t *testing.T) {
	checker := &mockIAMChecker{}
	resolver := &mockClusterTypeResolver{err: newResolverError("解析失败")}

	allowed, _, err := checkIAMPermission(checker, resolver, constant.APIClusterDelete, toJSON(map[string]interface{}{
		"clusterName": "c",
	}), "user1")

	assert.Error(t, err)
	assert.False(t, allowed)
	assert.True(t, IsResolverError(err))
}

func TestCheckIAMPermission_CreateCluster_Allowed(t *testing.T) {
	checker := &mockIAMChecker{allowed: true}
	resolver := &mockClusterTypeResolver{clusterType: "k8s_surrealdb_ha"}

	allowed, applyData, err := checkIAMPermission(checker, resolver, constant.APIClusterCreate, toJSON(map[string]interface{}{
		"bkBizId": 123,
	}), "user1")

	assert.NoError(t, err)
	assert.True(t, allowed)
	assert.Nil(t, applyData)
}

func TestCheckIAMPermission_CreateCluster_MissingBkBizId_Error(t *testing.T) {
	checker := &mockIAMChecker{allowed: true}
	resolver := &mockClusterTypeResolver{clusterType: "k8s_surrealdb_ha"}

	allowed, _, err := checkIAMPermission(checker, resolver, constant.APIClusterCreate, toJSON(map[string]interface{}{}), "user1")

	assert.Error(t, err)
	assert.False(t, allowed)
	assert.Contains(t, err.Error(), "bkBizId")
}

func TestCheckIAMPermission_CreateCluster_ZeroBkBizId_Error(t *testing.T) {
	checker := &mockIAMChecker{allowed: true}
	resolver := &mockClusterTypeResolver{clusterType: "k8s_surrealdb_ha"}

	allowed, _, err := checkIAMPermission(checker, resolver, constant.APIClusterCreate, toJSON(map[string]interface{}{
		"bkBizId": 0,
	}), "user1")

	assert.Error(t, err)
	assert.False(t, allowed)
}

func TestCheckIAMPermission_DeleteCluster_NotAllowed_WithApplyData(t *testing.T) {
	expectedData := &infresp.ApplyData{
		Permission: infresp.PermissionData{
			SystemID:   "bk_dbm",
			SystemName: "数据库管理",
			Actions: []infresp.PermissionAction{
				{ID: "k8s_surrealdb_destroy", Name: "K8s SurrealDB HA 下架"},
			},
		},
		ApplyURL: "https://iam.example.com/apply",
	}
	checker := &mockIAMChecker{allowed: false, applyData: expectedData}
	resolver := &mockClusterTypeResolver{clusterType: "k8s_surrealdb_ha", dbmClusterID: 42}

	allowed, applyData, err := checkIAMPermission(checker, resolver, constant.APIClusterDelete, toJSON(map[string]interface{}{
		"clusterName": "cluster-1",
	}), "user1")

	assert.NoError(t, err)
	assert.False(t, allowed)
	assert.NotNil(t, applyData)
	assert.Equal(t, expectedData.ApplyURL, applyData.ApplyURL)
	assert.Equal(t, "bk_dbm", applyData.Permission.SystemID)
}

func TestCheckIAMPermission_DBMError(t *testing.T) {
	checker := &mockIAMChecker{err: fmt.Errorf("DBM unavailable")}
	resolver := &mockClusterTypeResolver{clusterType: "k8s_surrealdb_ha", dbmClusterID: 42}

	_, _, err := checkIAMPermission(checker, resolver, constant.APIClusterDelete, toJSON(map[string]interface{}{
		"clusterName": "cluster-1",
	}), "user1")

	assert.Error(t, err)
	assert.False(t, IsResolverError(err), "DBM error should not be a resolver error")
}

func TestCheckIAMPermission_StorageWhitelistUnset_CallsIAM(t *testing.T) {
	t.Setenv(iamExemptStorageWhitelistEnv, "")
	checker := &mockIAMChecker{allowed: true}
	resolver := &mockClusterTypeResolver{clusterType: "k8s_surrealdb_ha", addonType: "surrealdb", dbmClusterID: 42}

	allowed, _, err := checkIAMPermission(checker, resolver, constant.APIClusterDelete, toJSON(map[string]interface{}{
		"clusterName": "cluster-1",
	}), "user1")

	assert.NoError(t, err)
	assert.True(t, allowed)
	assert.True(t, checker.called, "unset whitelist should keep IAM check enabled")
}

func TestCheckIAMPermission_StorageWhitelistMatched_SkipsIAM(t *testing.T) {
	t.Setenv(iamExemptStorageWhitelistEnv, "surrealdb,qdrant")
	checker := &mockIAMChecker{allowed: false, err: fmt.Errorf("should not call IAM")}
	resolver := &mockClusterTypeResolver{clusterType: "k8s_surrealdb_ha", addonType: "surrealdb", dbmClusterID: 0}

	allowed, applyData, err := checkIAMPermission(checker, resolver, constant.APIClusterDelete, toJSON(map[string]interface{}{
		"clusterName": "cluster-1",
	}), "user1")

	assert.NoError(t, err)
	assert.True(t, allowed)
	assert.Nil(t, applyData)
	assert.False(t, checker.called, "matched whitelist should skip IAM check")
}

func TestCheckIAMPermission_StorageWhitelistNotMatched_CallsIAM(t *testing.T) {
	t.Setenv(iamExemptStorageWhitelistEnv, "surrealdb,qdrant")
	checker := &mockIAMChecker{allowed: true}
	resolver := &mockClusterTypeResolver{clusterType: "k8s_milvus_ha", addonType: "milvus", dbmClusterID: 42}

	allowed, _, err := checkIAMPermission(checker, resolver, constant.APIClusterDelete, toJSON(map[string]interface{}{
		"clusterName": "cluster-1",
	}), "user1")

	assert.NoError(t, err)
	assert.True(t, allowed)
	assert.True(t, checker.called, "non-matched whitelist should keep IAM check enabled")
}

func TestCheckIAMPermission_StorageWhitelistTrimAndCaseInsensitive(t *testing.T) {
	t.Setenv(iamExemptStorageWhitelistEnv, " SurrealDB , qDrAnT ")
	checker := &mockIAMChecker{allowed: false, err: fmt.Errorf("should not call IAM")}
	resolver := &mockClusterTypeResolver{clusterType: "k8s_qdrant_ha", addonType: "qdrant", dbmClusterID: 0}

	allowed, _, err := checkIAMPermission(checker, resolver, constant.APIClusterDelete, toJSON(map[string]interface{}{
		"clusterName": "cluster-1",
	}), "user1")

	assert.NoError(t, err)
	assert.True(t, allowed)
	assert.False(t, checker.called, "whitelist match should ignore spaces and case")
}

func TestCheckIAMPermission_StorageWhitelistOnlyEmptyItems_CallsIAM(t *testing.T) {
	t.Setenv(iamExemptStorageWhitelistEnv, " , ,, ")
	checker := &mockIAMChecker{allowed: true}
	resolver := &mockClusterTypeResolver{clusterType: "k8s_surrealdb_ha", addonType: "surrealdb", dbmClusterID: 42}

	allowed, _, err := checkIAMPermission(checker, resolver, constant.APIClusterDelete, toJSON(map[string]interface{}{
		"clusterName": "cluster-1",
	}), "user1")

	assert.NoError(t, err)
	assert.True(t, allowed)
	assert.True(t, checker.called, "empty whitelist items should not enable exemption")
}

// --- APIAuthMiddleware integration tests ---

func setupRouter(checker iamChecker, resolver ClusterTypeResolver) *gin.Engine {
	gin.SetMode(gin.TestMode)
	r := gin.New()
	r.Use(apiAuthMiddlewareWithDeps(checker, resolver))
	r.GET("/v4/dbs/cluster/desc", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"result": true})
	})
	r.POST("/v4/dbs/cluster/create", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"result": true, "data": "created"})
	})
	r.POST("/v4/dbs/cluster/delete", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"result": true, "data": "deleted"})
	})
	r.POST("/unknown/path", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"result": true})
	})
	r.POST("/v4/dbs/addon/install", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"result": true, "data": "installed"})
	})
	return r
}

func defaultResolver() *mockClusterTypeResolver {
	return &mockClusterTypeResolver{clusterType: "k8s_surrealdb_ha", addonType: "surrealdb", dbmClusterID: 42}
}

func TestAPIAuthMiddleware_GETRequest_Passthrough(t *testing.T) {
	r := setupRouter(&mockIAMChecker{allowed: false}, defaultResolver())
	req := httptest.NewRequest(http.MethodGet, "/v4/dbs/cluster/desc", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)
	assert.Equal(t, http.StatusOK, w.Code)
}

func TestAPIAuthMiddleware_UnregisteredPath_Passthrough(t *testing.T) {
	r := setupRouter(&mockIAMChecker{allowed: false}, defaultResolver())
	w := testPostJSON(r, "/unknown/path", map[string]interface{}{
		"bk_username": "user1",
	})
	assert.Equal(t, http.StatusOK, w.Code)
}

func TestAPIAuthMiddleware_EmptyBody_Error(t *testing.T) {
	r := setupRouter(&mockIAMChecker{allowed: true}, defaultResolver())
	req := httptest.NewRequest(http.MethodPost, "/v4/dbs/cluster/create", nil)
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)
	assert.Equal(t, http.StatusOK, w.Code)
	var resp map[string]interface{}
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	assert.False(t, resp["result"].(bool))
}

func TestAPIAuthMiddleware_NoBKUsername_Rejected(t *testing.T) {
	r := setupRouter(&mockIAMChecker{allowed: false}, defaultResolver())
	w := testPostJSON(r, "/v4/dbs/cluster/create", map[string]interface{}{
		"bkBizId": 123,
	})
	assert.Equal(t, http.StatusOK, w.Code)
	var resp map[string]interface{}
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	assert.False(t, resp["result"].(bool))
	assert.Contains(t, resp["message"], "bk_username")
}

func TestAPIAuthMiddleware_EmptyBKUsername_Rejected(t *testing.T) {
	r := setupRouter(&mockIAMChecker{allowed: false}, defaultResolver())
	w := testPostJSON(r, "/v4/dbs/cluster/create", map[string]interface{}{
		"bk_username": "",
		"bkBizId":     123,
	})
	assert.Equal(t, http.StatusOK, w.Code)
	var resp map[string]interface{}
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	assert.False(t, resp["result"].(bool))
	assert.Contains(t, resp["message"], "bk_username")
}

func TestAPIAuthMiddleware_UserAllowed_Passthrough(t *testing.T) {
	r := setupRouter(&mockIAMChecker{allowed: true}, defaultResolver())
	w := testPostJSON(r, "/v4/dbs/cluster/delete", map[string]interface{}{
		"clusterName": "cluster-1",
		"bk_username": "user1",
	})
	assert.Equal(t, http.StatusOK, w.Code)
	var resp map[string]interface{}
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	assert.True(t, resp["result"].(bool))
	assert.Equal(t, "deleted", resp["data"])
}

func TestAPIAuthMiddleware_UserNotAllowed_PermissionDenied(t *testing.T) {
	applyData := &infresp.ApplyData{
		Permission: infresp.PermissionData{
			SystemID:   "bk_dbm",
			SystemName: "数据库管理",
			Actions: []infresp.PermissionAction{
				{ID: "k8s_surrealdb_destroy", Name: "K8s SurrealDB HA 下架"},
			},
		},
		ApplyURL: "https://iam.example.com/apply",
	}
	r := setupRouter(&mockIAMChecker{allowed: false, applyData: applyData}, defaultResolver())
	w := testPostJSON(r, "/v4/dbs/cluster/delete", map[string]interface{}{
		"clusterName": "cluster-1",
		"bk_username": "user1",
	})
	assert.Equal(t, http.StatusOK, w.Code)
	var resp map[string]interface{}
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	assert.False(t, resp["result"].(bool))

	data, ok := resp["data"].(map[string]interface{})
	require.True(t, ok, "data 字段应为对象")
	assert.NotEmpty(t, data["apply_url"], "应包含申请链接")
	perm, ok := data["permission"].(map[string]interface{})
	require.True(t, ok, "应包含 permission 字段")
	assert.Equal(t, "bk_dbm", perm["system_id"])
}

func TestAPIAuthMiddleware_IAMError_ThirdAPIError(t *testing.T) {
	r := setupRouter(&mockIAMChecker{err: fmt.Errorf("IAM unreachable")}, defaultResolver())
	w := testPostJSON(r, "/v4/dbs/cluster/delete", map[string]interface{}{
		"clusterName": "cluster-1",
		"bk_username": "user1",
	})
	assert.Equal(t, http.StatusOK, w.Code)
	var resp map[string]interface{}
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	assert.False(t, resp["result"].(bool))
}

func TestAPIAuthMiddleware_UserNotAllowed_NilApplyData(t *testing.T) {
	// 测试 allowed=false, applyData=nil 路径（如 AdminOnlyAction）
	r := setupRouter(&mockIAMChecker{allowed: false, applyData: nil}, defaultResolver())
	w := testPostJSON(r, "/v4/dbs/cluster/delete", map[string]interface{}{
		"clusterName": "cluster-1",
		"bk_username": "user1",
	})
	assert.Equal(t, http.StatusOK, w.Code)
	var resp map[string]interface{}
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	assert.False(t, resp["result"].(bool))
	assert.Nil(t, resp["data"], "applyData 为 nil 时 data 字段应为 null")
}

// --- 新增测试维度 ---

func TestAPIAuthMiddleware_ResolverError_ReturnsParameterInvalidError(t *testing.T) {
	// resolver 返回错误时，middleware 应返回 ParameterInvalidError（非 ThirdAPIError）
	resolverErr := &mockClusterTypeResolver{err: newResolverError("集群类型解析失败")}
	r := setupRouter(&mockIAMChecker{allowed: true}, resolverErr)
	w := testPostJSON(r, "/v4/dbs/cluster/delete", map[string]interface{}{
		"clusterName": "cluster-1",
		"bk_username": "user1",
	})
	assert.Equal(t, http.StatusOK, w.Code)
	var resp map[string]interface{}
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	assert.False(t, resp["result"].(bool))

	// 验证错误码为 ParameterInvalidError（不是 ThirdAPIError）
	code, ok := resp["code"].(float64)
	require.True(t, ok, "响应应包含 code 字段")
	assert.Equal(t, float64(1532113), code, "resolver error should return ParameterInvalidError code")
}

func TestAPIAuthMiddleware_ResolverInitFailed_ReturnsError(t *testing.T) {
	// 模拟 resolver 初始化失败
	resolverErr := &mockClusterTypeResolver{err: newResolverError("provider 尚未初始化")}
	r := setupRouter(&mockIAMChecker{allowed: true}, resolverErr)
	w := testPostJSON(r, "/v4/dbs/cluster/delete", map[string]interface{}{
		"clusterName": "cluster-1",
		"bk_username": "user1",
	})
	assert.Equal(t, http.StatusOK, w.Code)
	var resp map[string]interface{}
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	assert.False(t, resp["result"].(bool))
	assert.Contains(t, resp["message"], "参数校验失败")
}

// --- Addon 操作鉴权测试 ---

func TestAPIAuthMiddleware_AddonInstall_Allowed(t *testing.T) {
	t.Setenv("BKBASE_BK_BIZ_ID", "100")
	r := setupRouter(&mockIAMChecker{allowed: true}, defaultResolver())
	w := testPostJSON(r, "/v4/dbs/addon/install", map[string]interface{}{
		"k8sClusterName": "minikube",
		"addonType":      "qdrant",
		"addonVersion":   "1.0.0",
		"bk_username":    "user1",
	})
	assert.Equal(t, http.StatusOK, w.Code)
	var resp map[string]interface{}
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	assert.True(t, resp["result"].(bool))
	assert.Equal(t, "installed", resp["data"])
}

func TestAPIAuthMiddleware_AddonInstall_NotAllowed(t *testing.T) {
	t.Setenv("BKBASE_BK_BIZ_ID", "100")
	r := setupRouter(&mockIAMChecker{allowed: false, applyData: &infresp.ApplyData{
		ApplyURL: "https://iam.example.com/apply",
	}}, defaultResolver())
	w := testPostJSON(r, "/v4/dbs/addon/install", map[string]interface{}{
		"k8sClusterName": "minikube",
		"addonType":      "qdrant",
		"bk_username":    "user1",
	})
	assert.Equal(t, http.StatusOK, w.Code)
	var resp map[string]interface{}
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	assert.False(t, resp["result"].(bool))
}

func TestAPIAuthMiddleware_AddonInstall_MissingBkbaseBizId(t *testing.T) {
	// BKBASE_BK_BIZ_ID 未设置，addon 鉴权应失败
	r := setupRouter(&mockIAMChecker{allowed: true}, defaultResolver())
	w := testPostJSON(r, "/v4/dbs/addon/install", map[string]interface{}{
		"k8sClusterName": "minikube",
		"addonType":      "qdrant",
		"bk_username":    "user1",
	})
	assert.Equal(t, http.StatusOK, w.Code)
	var resp map[string]interface{}
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	assert.False(t, resp["result"].(bool))
	assert.Contains(t, resp["message"], "BKBASE_BK_BIZ_ID")
}

func TestAPIAuthMiddleware_AddonInstall_NoBkUsername_Rejected(t *testing.T) {
	r := setupRouter(&mockIAMChecker{allowed: false}, defaultResolver())
	w := testPostJSON(r, "/v4/dbs/addon/install", map[string]interface{}{
		"k8sClusterName": "minikube",
		"addonType":      "qdrant",
	})
	assert.Equal(t, http.StatusOK, w.Code)
	var resp map[string]interface{}
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	assert.False(t, resp["result"].(bool))
	assert.Contains(t, resp["message"], "bk_username")
}

func TestCheckIAMPermission_AddonInstall_UsesFixedActionID(t *testing.T) {
	t.Setenv("BKBASE_BK_BIZ_ID", "100")
	var capturedActionID string
	checker := &mockIAMCheckerCapture{
		allowed:        true,
		capturedAction: &capturedActionID,
	}
	resolver := &mockClusterTypeResolver{clusterType: "k8s_surrealdb_ha"}

	allowed, _, err := checkIAMPermission(checker, resolver, constant.APIAddonInstall, toJSON(map[string]interface{}{}), "user1")

	assert.NoError(t, err)
	assert.True(t, allowed)
	assert.Equal(t, "k8s_addon_manage", capturedActionID, "addon should use fixed action_id, not per-type")
}

// mockIAMCheckerCapture captures the actionID passed to SimpleCheckAllowed
type mockIAMCheckerCapture struct {
	allowed        bool
	capturedAction *string
}

func (m *mockIAMCheckerCapture) SimpleCheckAllowed(_, actionID string, _ int, _ string) (bool, *infresp.ApplyData, error) {
	*m.capturedAction = actionID
	return m.allowed, nil, nil
}

func TestAPIAuthMiddleware_InvalidJSON_Error(t *testing.T) {
	// 测试非法 JSON 请求体
	r := setupRouter(&mockIAMChecker{allowed: true}, defaultResolver())
	req := httptest.NewRequest(http.MethodPost, "/v4/dbs/cluster/create",
		strings.NewReader("{invalid json"))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)
	assert.Equal(t, http.StatusOK, w.Code)
	var resp map[string]interface{}
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	assert.False(t, resp["result"].(bool))
}
