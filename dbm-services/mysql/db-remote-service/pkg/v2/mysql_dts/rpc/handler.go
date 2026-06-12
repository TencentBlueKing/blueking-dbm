package rpc

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"net/url"
	"strings"
	"time"

	"github.com/gin-contrib/requestid"
	"github.com/gin-gonic/gin"
)

// DTSRPCRequest 代理请求体
type DTSRPCRequest struct {
	Method        string         `json:"method" binding:"required"`
	URL           string         `json:"url" binding:"required"`
	Params        map[string]any `json:"params"`
	DTSMasterAddr string         `json:"dts_master_addr" binding:"required"`
}

// Handler 将请求代理转发到真实的 DTS Master
func Handler(c *gin.Context) {
	rid := requestid.Get(c)

	var req DTSRPCRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"code": 1,
			"msg":  fmt.Sprintf("invalid request: %s", err),
			"data": nil,
		})
		return
	}

	if req.Params == nil {
		req.Params = map[string]any{}
	}

	slog.Info("v2 mysql-dts rpc request",
		slog.String("request_id", rid),
		slog.String("method", req.Method),
		slog.String("url", req.URL),
		slog.String("dts_master_addr", req.DTSMasterAddr),
	)

	start := time.Now()

	data, err := forwardToDTSMaster(req.DTSMasterAddr, req.Method, req.URL, req.Params)
	elapsed := time.Since(start)

	if err != nil {
		slog.Error("v2 mysql-dts rpc forward failed",
			slog.String("request_id", rid),
			slog.Duration("elapsed", elapsed),
			slog.String("error", err.Error()),
		)
		c.JSON(http.StatusBadGateway, gin.H{
			"code": 1,
			"data": nil,
			"msg":  fmt.Sprintf("forward to dts master failed: %s", err),
		})
		return
	}

	slog.Info("v2 mysql-dts rpc finished",
		slog.String("request_id", rid),
		slog.Duration("elapsed", elapsed),
	)

	c.JSON(http.StatusOK, gin.H{
		"code": 0,
		"data": data,
		"msg":  "",
	})
}

// forwardToDTSMaster 将请求转发到真实的 DTS Master
func forwardToDTSMaster(addr string, method string, path string, params map[string]any) (any, error) {
	// Python 侧传入的是 1.1.1.1:1083 格式，不带 scheme
	if !strings.HasPrefix(addr, "http://") && !strings.HasPrefix(addr, "https://") {
		addr = "http://" + addr
	}
	u, err := url.Parse(strings.TrimRight(addr, "/") + "/" + strings.TrimLeft(path, "/"))
	if err != nil {
		return nil, fmt.Errorf("invalid dts_master_addr or url: %w", err)
	}

	var req *http.Request

	switch strings.ToUpper(method) {
	case http.MethodGet, http.MethodDelete:
		q := u.Query()
		for k, v := range params {
			q.Add(k, fmt.Sprintf("%v", v))
		}
		u.RawQuery = q.Encode()
		req, err = http.NewRequest(strings.ToUpper(method), u.String(), nil)
	case http.MethodPost, http.MethodPut, http.MethodPatch:
		jsonBody, jsonErr := json.Marshal(params)
		if jsonErr != nil {
			return nil, fmt.Errorf("marshal params failed: %w", jsonErr)
		}
		req, err = http.NewRequest(strings.ToUpper(method), u.String(), bytes.NewReader(jsonBody))
		if err == nil {
			req.Header.Set("Content-Type", "application/json")
		}
	default:
		return nil, fmt.Errorf("unsupported http method: %s", method)
	}

	if err != nil {
		return nil, fmt.Errorf("create request failed: %w", err)
	}

	client := &http.Client{Timeout: 600 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request to dts master failed: %w", err)
	}
	defer func() { _ = resp.Body.Close() }()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("read response body failed: %w", err)
	}

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return nil, fmt.Errorf("dts master returned status %d: %s", resp.StatusCode, string(respBody))
	}

	if len(respBody) == 0 {
		return nil, nil
	}

	var result any
	if err := json.Unmarshal(respBody, &result); err != nil {
		return nil, fmt.Errorf("dts master returned non-JSON response: %s", string(respBody))
	}
	return result, nil
}
