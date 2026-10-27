package rpc

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"net"
	"net/http"
	"net/netip"
	"net/url"
	"strconv"
	"strings"
	"time"
	"unicode/utf8"

	"dbm-services/mysql/db-remote-service/pkg/config"

	"github.com/gin-contrib/requestid"
	"github.com/gin-gonic/gin"
)

const (
	// dtsAPIPathPrefix 仅允许转发到 DTS Master OpenAPI
	dtsAPIPathPrefix = "/api/v1/"
	// maxRequestBodyBytes 入站请求体上限
	maxRequestBodyBytes = 16 << 20
	// maxRespBodyBytes 上游响应体读取上限
	maxRespBodyBytes = 32 << 20
	// maxErrMsgRunes 回显 DTS 业务错误信息的最大字符数
	maxErrMsgRunes = 512
	// maxConcurrentForwards DTS RPC 同时转发的最大请求数, 独立于 MySQL 的 GlobalSemaphore
	maxConcurrentForwards = 64
	// 日志中调用方可控字段的最大字符数
	maxLogMethodRunes = 16
	maxLogURLRunes    = 512
	maxLogAddrRunes   = 128
)

// forwardSem 限制 DTS RPC 并发, 防止慢请求耗尽 DRS 内存与连接
var forwardSem = make(chan struct{}, maxConcurrentForwards)

var allowedMethods = map[string]struct{}{
	http.MethodGet:    {},
	http.MethodPost:   {},
	http.MethodPut:    {},
	http.MethodPatch:  {},
	http.MethodDelete: {},
}

// httpClient 不跟随重定向, 不使用环境代理, 避免经合法地址 30x 跳转或代理到任意目标
var httpClient = newHTTPClient()

func newHTTPClient() *http.Client {
	transport := http.DefaultTransport.(*http.Transport).Clone()
	transport.Proxy = nil
	return &http.Client{
		Timeout:   600 * time.Second,
		Transport: transport,
		CheckRedirect: func(*http.Request, []*http.Request) error {
			return http.ErrUseLastResponse
		},
	}
}

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

	c.Request.Body = http.MaxBytesReader(c.Writer, c.Request.Body, maxRequestBodyBytes)

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

	logMethod := slog.String("method", truncateRunes(req.Method, maxLogMethodRunes))
	logURL := slog.String("url", truncateRunes(req.URL, maxLogURLRunes))
	logAddr := slog.String("dts_master_addr", truncateRunes(req.DTSMasterAddr, maxLogAddrRunes))

	slog.Info("v2 mysql-dts rpc request",
		slog.String("request_id", rid),
		logMethod, logURL, logAddr,
	)

	target, method, err := buildTarget(req.DTSMasterAddr, req.Method, req.URL)
	if err != nil {
		slog.Warn("v2 mysql-dts rpc rejected",
			slog.String("request_id", rid),
			logMethod, logURL, logAddr,
			slog.String("reason", err.Error()),
		)
		c.JSON(http.StatusBadRequest, gin.H{
			"code": 1,
			"msg":  fmt.Sprintf("invalid request: %s", err),
			"data": nil,
		})
		return
	}

	release, err := acquireForwardSlot(c.Request.Context())
	if err != nil {
		slog.Warn("v2 mysql-dts rpc throttled",
			slog.String("request_id", rid),
			slog.String("error", err.Error()),
		)
		// 使用 429 而非 503: dbm-ui 清理流程会把含 "503" 的异常视为可忽略, 限流不能被静默跳过
		c.JSON(http.StatusTooManyRequests, gin.H{
			"code": 1,
			"data": nil,
			"msg":  fmt.Sprintf("dts rpc busy: %s", err),
		})
		return
	}
	defer release()

	start := time.Now()

	data, err := forwardToDTSMaster(c.Request.Context(), target, method, req.Params)
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

// acquireForwardSlot 获取转发并发槽位, 排队期间调用方断开则放弃
func acquireForwardSlot(ctx context.Context) (func(), error) {
	select {
	case forwardSem <- struct{}{}:
		return func() { <-forwardSem }, nil
	case <-ctx.Done():
		return nil, ctx.Err()
	}
}

// buildTarget 校验 method / dts_master_addr / url 并构造目标 URL
func buildTarget(addr string, method string, path string) (*url.URL, string, error) {
	m := strings.ToUpper(strings.TrimSpace(method))
	if _, ok := allowedMethods[m]; !ok {
		return nil, "", fmt.Errorf("unsupported http method: %s", method)
	}

	hostPort, err := validateMasterAddr(addr, allowedMasterPorts())
	if err != nil {
		return nil, "", err
	}

	pu, err := validateAPIPath(path)
	if err != nil {
		return nil, "", err
	}

	return &url.URL{Scheme: "http", Host: hostPort, Path: pu.Path, RawPath: pu.RawPath}, m, nil
}

func allowedMasterPorts() map[int]struct{} {
	if config.RuntimeConfig != nil && len(config.RuntimeConfig.MySQLDTSMasterPorts) > 0 {
		return config.RuntimeConfig.MySQLDTSMasterPorts
	}
	return map[int]struct{}{config.DefaultMySQLDTSMasterPort: {}}
}

// validateMasterAddr 仅允许 IP:port, 禁止 scheme / userinfo / 域名 / 特殊地址, 端口须在白名单内
func validateMasterAddr(addr string, ports map[int]struct{}) (string, error) {
	addr = strings.TrimSpace(addr)
	if addr == "" || strings.ContainsAny(addr, "/@?#\\ \t\r\n%") {
		return "", errors.New("invalid dts_master_addr: must be ip:port")
	}

	host, portStr, err := net.SplitHostPort(addr)
	if err != nil {
		return "", errors.New("invalid dts_master_addr: must be ip:port")
	}

	ip, err := netip.ParseAddr(host)
	if err != nil {
		return "", errors.New("invalid dts_master_addr: host must be an ip literal")
	}
	ip = ip.Unmap()
	if ip.IsLoopback() || ip.IsUnspecified() || ip.IsLinkLocalUnicast() || ip.IsMulticast() ||
		ip == netip.AddrFrom4([4]byte{255, 255, 255, 255}) {
		return "", fmt.Errorf("invalid dts_master_addr: forbidden ip %s", ip)
	}

	port, err := strconv.Atoi(portStr)
	if err != nil || port <= 0 || port > 65535 {
		return "", errors.New("invalid dts_master_addr: bad port")
	}
	if _, ok := ports[port]; !ok {
		return "", fmt.Errorf("invalid dts_master_addr: port %d not allowed", port)
	}

	return net.JoinHostPort(ip.String(), strconv.Itoa(port)), nil
}

// validateAPIPath 仅允许 /api/v1/ 前缀, 禁止 query / fragment / 反斜杠 / 控制字符以及 . 和 .. 路径段(含百分号编码形式)
func validateAPIPath(p string) (*url.URL, error) {
	p = "/" + strings.TrimLeft(strings.TrimSpace(p), "/")
	if !strings.HasPrefix(p, dtsAPIPathPrefix) {
		return nil, fmt.Errorf("invalid url: must start with %s", dtsAPIPathPrefix)
	}
	if strings.ContainsAny(p, "?#\\") {
		return nil, errors.New("invalid url: contains forbidden character")
	}

	pu, err := url.Parse(p)
	if err != nil {
		return nil, fmt.Errorf("invalid url: %w", err)
	}
	if pu.Scheme != "" || pu.Host != "" || pu.User != nil {
		return nil, errors.New("invalid url: must be a path")
	}
	if !strings.HasPrefix(pu.Path, dtsAPIPathPrefix) {
		return nil, fmt.Errorf("invalid url: must start with %s", dtsAPIPathPrefix)
	}
	for _, r := range pu.Path {
		if r < 0x20 || r == 0x7f || r == '\\' {
			return nil, errors.New("invalid url: contains forbidden character")
		}
	}
	for _, seg := range strings.Split(pu.Path, "/") {
		if seg == "." || seg == ".." {
			return nil, errors.New("invalid url: path traversal not allowed")
		}
	}
	return pu, nil
}

// forwardToDTSMaster 将请求转发到真实的 DTS Master
func forwardToDTSMaster(ctx context.Context, u *url.URL, method string, params map[string]any) (any, error) {
	var (
		req *http.Request
		err error
	)

	target := *u
	switch method {
	case http.MethodGet, http.MethodDelete:
		q := url.Values{}
		for k, v := range params {
			q.Add(k, fmt.Sprintf("%v", v))
		}
		target.RawQuery = q.Encode()
		req, err = http.NewRequestWithContext(ctx, method, target.String(), nil)
	case http.MethodPost, http.MethodPut, http.MethodPatch:
		jsonBody, jsonErr := json.Marshal(params)
		if jsonErr != nil {
			return nil, fmt.Errorf("marshal params failed: %w", jsonErr)
		}
		req, err = http.NewRequestWithContext(ctx, method, target.String(), bytes.NewReader(jsonBody))
		if err == nil {
			req.Header.Set("Content-Type", "application/json")
		}
	default:
		return nil, fmt.Errorf("unsupported http method: %s", method)
	}

	if err != nil {
		return nil, fmt.Errorf("create request failed: %w", err)
	}

	resp, err := httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request to dts master failed: %w", err)
	}
	defer func() { _ = resp.Body.Close() }()

	respBody, err := io.ReadAll(io.LimitReader(resp.Body, maxRespBodyBytes+1))
	if err != nil {
		return nil, fmt.Errorf("read response body failed: %w", err)
	}
	if len(respBody) > maxRespBodyBytes {
		return nil, errors.New("dts master response too large")
	}

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return nil, fmt.Errorf("dts master returned status %d%s", resp.StatusCode, formatDTSError(respBody))
	}

	if len(respBody) == 0 {
		return nil, nil
	}

	var result any
	if err := json.Unmarshal(respBody, &result); err != nil {
		return nil, fmt.Errorf("dts master returned non-JSON response (status %d)", resp.StatusCode)
	}
	return result, nil
}

// formatDTSError 仅提取 DTS 标准错误结构中的 error_code / error_msg, 其余内容一律不回显。
// 调用方依赖 error_code(如 49001)与 error_msg 中的关键字判断业务状态, 因此这两个字段需要保留。
func formatDTSError(body []byte) string {
	// 两个字段分开解析: error_msg 不是字符串时只丢弃 error_msg, 不影响 error_code 透传
	var raw struct {
		ErrorCode any             `json:"error_code"`
		ErrorMsg  json.RawMessage `json:"error_msg"`
	}
	if len(body) == 0 || json.Unmarshal(body, &raw) != nil {
		return ""
	}
	var errMsg string
	if len(raw.ErrorMsg) > 0 {
		_ = json.Unmarshal(raw.ErrorMsg, &errMsg)
	}

	var parts []string
	switch code := raw.ErrorCode.(type) {
	case float64:
		parts = append(parts, "error_code: "+strconv.FormatInt(int64(code), 10))
	case string:
		if len(code) <= 32 {
			parts = append(parts, "error_code: "+code)
		}
	}
	if msg := truncateRunes(errMsg, maxErrMsgRunes); msg != "" {
		parts = append(parts, "error_msg: "+msg)
	}
	if len(parts) == 0 {
		return ""
	}
	return ": " + strings.Join(parts, ", ")
}

func truncateRunes(s string, n int) string {
	if utf8.RuneCountInString(s) <= n {
		return s
	}
	return string([]rune(s)[:n])
}
