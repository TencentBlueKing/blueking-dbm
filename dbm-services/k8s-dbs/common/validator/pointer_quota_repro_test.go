package validator

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	coreentity "k8s-dbs/core/entity"

	"github.com/gin-gonic/gin"
)

// 复现 CreateCluster 实际请求链路：
// entity.Request -> Spec -> []ComponentResource（Request/Limit 为 *Resource，非 ResourceQuota）。
// 历史上此处未注册 ComponentResource 的结构体级校验，导致 request.cpu > limit.cpu 也返回成功。
type createClusterRequest struct {
	Name string          `json:"name" binding:"required"`
	Spec coreentity.Spec `json:"spec"`
}

func TestBinding_ComponentResource_CPUExceeds(t *testing.T) {
	gin.SetMode(gin.TestMode)
	r := gin.New()
	r.POST("/cluster", func(c *gin.Context) {
		var req createClusterRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			ok, msg := ValidateError(err, req)
			_ = ok
			c.JSON(http.StatusBadRequest, gin.H{"error": msg})
			return
		}
		c.JSON(http.StatusOK, gin.H{"ok": true})
	})

	body := map[string]any{
		"name": "cluster-1",
		"spec": map[string]any{
			"componentList": []any{
				map[string]any{
					"componentName": "qdrant",
					"request":       map[string]any{"cpu": "2", "memory": "2Gi"},
					"limit":         map[string]any{"cpu": "1", "memory": "1Gi"},
				},
			},
		},
	}
	buf, _ := json.Marshal(body)
	rr := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodPost, "/cluster", bytes.NewReader(buf))
	req.Header.Set("Content-Type", "application/json")
	r.ServeHTTP(rr, req)

	if rr.Code == http.StatusOK {
		t.Errorf("BUG REPRO: ComponentResource 未触发 request ≤ limit 校验（返回 200，校验未生效）")
	}
	if rr.Code != http.StatusOK && !strings.Contains(rr.Body.String(), "cpu request 不能大于 limit") {
		t.Errorf("status=%d 但消息不含预期内容, body=%s", rr.Code, rr.Body.String())
	}
}
