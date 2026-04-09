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

package validator

import (
	"bytes"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	commentity "k8s-dbs/common/entity"
	coreentity "k8s-dbs/core/entity"

	"github.com/gin-gonic/gin"
	"github.com/go-playground/validator/v10"
	"k8s.io/apimachinery/pkg/api/resource"
)

// ---------------------- 测试辅助 ----------------------

// newTestValidator 构造独立的 validator 实例并注册 ResourceQuota 结构体级校验器，
// 避免依赖 gin binding 的全局单例。
func newTestValidator(t *testing.T) *validator.Validate {
	t.Helper()
	v := validator.New()
	RegisterResourceQuotaValidators(v)
	return v
}

// hasTag 判断 ValidationErrors 中是否包含指定 tag
func hasTag(err error, tag string) bool {
	var ve validator.ValidationErrors
	if !errors.As(err, &ve) {
		return false
	}
	for _, fe := range ve {
		if fe.Tag() == tag {
			return true
		}
	}
	return false
}

// mustQ 构造 resource.Quantity，测试专用
func mustQ(s string) resource.Quantity {
	return resource.MustParse(s)
}

// bindingRequest 模拟 K8sNamespaceRequest 的最小结构，
// 用于验证 gin binding 会自动触发 ResourceQuota 的结构体级校验。
type bindingRequest struct {
	Name                    string                    `json:"name" binding:"required"`
	ResourceQuota           *coreentity.ResourceQuota `json:"resourceQuota,omitempty"`
	commentity.BKAdditional `json:",inline"`
}

// setupBindingRouter 构造启用了 gin binding 的路由，复现 controller 的 ShouldBindJSON + ValidateError 链路
func setupBindingRouter() *gin.Engine {
	gin.SetMode(gin.TestMode)
	r := gin.New()
	r.POST("/namespace", func(c *gin.Context) {
		var req bindingRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			_, msg := ValidateError(err, req)
			c.JSON(http.StatusBadRequest, gin.H{"error": msg})
			return
		}
		c.JSON(http.StatusOK, gin.H{"ok": true})
	})
	return r
}

// postJSON 发送 JSON 请求并返回响应记录
func postJSON(t *testing.T, r *gin.Engine, body any) *httptest.ResponseRecorder {
	t.Helper()
	buf, err := json.Marshal(body)
	if err != nil {
		t.Fatalf("marshal body failed: %v", err)
	}
	req := httptest.NewRequest(http.MethodPost, "/namespace", bytes.NewReader(buf))
	req.Header.Set("Content-Type", "application/json")
	rr := httptest.NewRecorder()
	r.ServeHTTP(rr, req)
	return rr
}

// quotaBody 构造带 resourceQuota 的请求体
func quotaBody(request, limit map[string]any) map[string]any {
	return map[string]any{
		"name":        "ns",
		"bk_app_code": "app",
		"bk_username": "user",
		"resourceQuota": map[string]any{
			"request": request,
			"limit":   limit,
		},
	}
}

// ---------------------- 4 个必要测试 ----------------------

// 1. CPU 超限：request.cpu > limit.cpu 应通过 gin binding 返回 400 且中文消息正确
func TestResourceQuota_CPUExceeds(t *testing.T) {
	rr := postJSON(t, setupBindingRouter(), quotaBody(
		map[string]any{"cpu": "8", "memory": "2Gi"},
		map[string]any{"cpu": "4", "memory": "8Gi"},
	))
	if rr.Code != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d, body=%s", rr.Code, rr.Body.String())
	}
	if !strings.Contains(rr.Body.String(), "cpu request 不能大于 limit") {
		t.Fatalf("expected cpu error msg, got: %s", rr.Body.String())
	}
}

// 2. Memory 超限：request.memory > limit.memory 应返回 400 且中文消息正确
func TestResourceQuota_MemoryExceeds(t *testing.T) {
	rr := postJSON(t, setupBindingRouter(), quotaBody(
		map[string]any{"cpu": "2", "memory": "16Gi"},
		map[string]any{"cpu": "4", "memory": "8Gi"},
	))
	if rr.Code != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d, body=%s", rr.Code, rr.Body.String())
	}
	if !strings.Contains(rr.Body.String(), "memory request 不能大于 limit") {
		t.Fatalf("expected memory error msg, got: %s", rr.Body.String())
	}
}

// 3. 合法配额：request ≤ limit 应通过校验（单元层直接验证 Struct 校验逻辑）
func TestResourceQuota_Valid(t *testing.T) {
	v := newTestValidator(t)
	rq := coreentity.ResourceQuota{
		Request: coreentity.Resource{CPU: mustQ("2"), Memory: mustQ("2Gi")},
		Limit:   coreentity.Resource{CPU: mustQ("4"), Memory: mustQ("8Gi")},
	}
	if err := v.Struct(rq); err != nil {
		t.Fatalf("expected no error, got: %v", err)
	}
}

// 4. 零值跳过：Request 或 Limit 一方为零时不校验一致性（保持 omitempty 语义）
func TestResourceQuota_ZeroValueSkips(t *testing.T) {
	v := newTestValidator(t)
	// Request.CPU 有值，Limit.CPU 零值 → 应放行（非零校验由 provider 层负责）
	rq := coreentity.ResourceQuota{
		Request: coreentity.Resource{CPU: mustQ("8"), Memory: mustQ("2Gi")},
		Limit:   coreentity.Resource{CPU: resource.Quantity{}, Memory: mustQ("8Gi")},
	}
	if err := v.Struct(rq); err != nil {
		t.Fatalf("expected no error when limit.cpu is zero, got: %v", err)
	}
}
