package middleware

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"

	"github.com/gin-gonic/gin"
)

// testPostJSON 发送 POST JSON 请求到 gin.Engine，返回 ResponseRecorder。
// 供 api_auth_middleware_test.go 和 api_auth_e2e_test.go 共用。
func testPostJSON(r *gin.Engine, path string, body interface{}) *httptest.ResponseRecorder {
	bodyBytes, _ := json.Marshal(body)
	req := httptest.NewRequest(http.MethodPost, path, bytes.NewReader(bodyBytes))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)
	return w
}
