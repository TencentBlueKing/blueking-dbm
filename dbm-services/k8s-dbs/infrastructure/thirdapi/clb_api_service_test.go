package thirdapi

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"sync"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	infreq "k8s-dbs/infrastructure/request"
)

// TestCreateClb_Success 测试 CLB 创建成功场景
// Mock API 返回：result=true, data=["lb-test"], code="1500200", message="ok"
func TestCreateClb_Success(t *testing.T) {
	// Mock 成功的响应数据
	successResponse := map[string]interface{}{
		"result":  true,
		"data":    []string{"lb-test"},
		"code":    "1500200",
		"message": "ok",
		"errors":  nil,
	}

	// 创建 mock HTTP 服务器
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// 验证请求路径
		assert.Equal(t, "/ops/create_clb", r.URL.Path)
		assert.Equal(t, "POST", r.Method)
		assert.Equal(t, "application/json", r.Header.Get("Content-Type"))

		// 验证请求体
		var reqBody map[string]interface{}
		err := json.NewDecoder(r.Body).Decode(&reqBody)
		require.NoError(t, err)
		assert.Equal(t, "ap-guangzhou", reqBody["region"])
		assert.Equal(t, "vpc-test", reqBody["vpc_id"])
		assert.Equal(t, "test-clb-name", reqBody["clb_name"])
		assert.Equal(t, float64(1), reqBody["clb_nums"])
		assert.Equal(t, "testuser", reqBody["username"])
		assert.Equal(t, "backupuser", reqBody["backup_username"])

		// 返回成功响应
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(successResponse)
	}))
	defer server.Close()

	// 设置环境变量
	os.Setenv("BKBASE_CLB_API_URL", server.URL)
	os.Setenv("BKBASE_CLB_USERNAME", "testuser")
	os.Setenv("BKBASE_CLB_BACKUP_USERNAME", "backupuser")
	defer func() {
		os.Unsetenv("BKBASE_CLB_API_URL")
		os.Unsetenv("BKBASE_CLB_USERNAME")
		os.Unsetenv("BKBASE_CLB_BACKUP_USERNAME")
	}()

	// 重置单例，确保使用新的环境变量
	clbOnce = sync.Once{}
	clbInstance = nil

	// 执行测试
	svc := GetClbAPIService()
	req := &infreq.CreateClbRequest{
		Region:  "ap-guangzhou",
		VpcID:   "vpc-test",
		ClbName: "test-clb-name",
		ClbNums: 1,
	}

	clbID, err := svc.CreateClb(req)

	// 验证结果
	require.NoError(t, err)
	assert.Equal(t, "lb-test", clbID)
}

// TestCreateClb_Failure 测试 CLB 创建失败场景
// Mock API 返回：result=false, data=[], code="1500500", message="没有可用的子网"
func TestCreateClb_Failure(t *testing.T) {
	// Mock 失败的响应数据
	failureResponse := map[string]interface{}{
		"result":  false,
		"data":    []string{},
		"code":    "1500500",
		"message": "没有可用的子网",
		"errors":  nil,
	}

	// 创建 mock HTTP 服务器
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// 返回失败响应（HTTP 状态码仍然是 200）
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(failureResponse)
	}))
	defer server.Close()

	// 设置环境变量
	os.Setenv("BKBASE_CLB_API_URL", server.URL)
	os.Setenv("BKBASE_CLB_USERNAME", "testuser")
	os.Setenv("BKBASE_CLB_BACKUP_USERNAME", "backupuser")
	defer func() {
		os.Unsetenv("BKBASE_CLB_API_URL")
		os.Unsetenv("BKBASE_CLB_USERNAME")
		os.Unsetenv("BKBASE_CLB_BACKUP_USERNAME")
	}()

	// 重置单例
	clbOnce = sync.Once{}
	clbInstance = nil

	// 执行测试
	svc := GetClbAPIService()
	req := &infreq.CreateClbRequest{
		Region:  "ap-guangzhou",
		VpcID:   "vpc-test",
		ClbName: "test-clb-name",
		ClbNums: 1,
	}

	clbID, err := svc.CreateClb(req)

	// 验证结果
	require.Error(t, err)
	assert.Empty(t, clbID)
	assert.Contains(t, err.Error(), "创建 CLB 失败 [1500500]: 没有可用的子网")
}

// TestCreateClb_EmptyData 测试 CLB 创建返回空列表场景
// Mock API 返回：result=true, data=[], code="1500200", message="ok"
func TestCreateClb_EmptyData(t *testing.T) {
	// Mock 成功但 data 为空的响应数据
	emptyDataResponse := map[string]interface{}{
		"result":  true,
		"data":    []string{},
		"code":    "1500200",
		"message": "ok",
		"errors":  nil,
	}

	// 创建 mock HTTP 服务器
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(emptyDataResponse)
	}))
	defer server.Close()

	// 设置环境变量
	os.Setenv("BKBASE_CLB_API_URL", server.URL)
	os.Setenv("BKBASE_CLB_USERNAME", "testuser")
	os.Setenv("BKBASE_CLB_BACKUP_USERNAME", "backupuser")
	defer func() {
		os.Unsetenv("BKBASE_CLB_API_URL")
		os.Unsetenv("BKBASE_CLB_USERNAME")
		os.Unsetenv("BKBASE_CLB_BACKUP_USERNAME")
	}()

	// 重置单例
	clbOnce = sync.Once{}
	clbInstance = nil

	// 执行测试
	svc := GetClbAPIService()
	req := &infreq.CreateClbRequest{
		Region:  "ap-guangzhou",
		VpcID:   "vpc-test",
		ClbName: "test-clb-name",
		ClbNums: 1,
	}

	clbID, err := svc.CreateClb(req)

	// 验证结果
	require.Error(t, err)
	assert.Empty(t, clbID)
	assert.Contains(t, err.Error(), "创建 CLB 返回空列表 [1500200]")
}

// TestGetClb_Success 测试获取 CLB 成功场景
// Mock API 返回：result=true, data包含CLB详细信息, code="1500200", message="ok"
func TestGetClb_Success(t *testing.T) {
	// Mock 成功的响应数据（数据已脱敏）
	successResponse := map[string]interface{}{
		"result": true,
		"data": []map[string]interface{}{
			{
				"LoadBalancerId":   "lb-xxxxxx1",
				"LoadBalancerName": "test-clb-name",
				"LoadBalancerType": "INTERNAL",
				"LoadBalancerVips": "10.0.x.x",
				"VpcId":            "vpc-xxxxx",
				"Zones": []string{
					"ap-region-1",
					"ap-region-2",
				},
			},
		},
		"code":    "1500200",
		"message": "ok",
		"errors":  nil,
	}

	// 创建 mock HTTP 服务器
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// 验证请求路径
		assert.Equal(t, "/ops/get_clb", r.URL.Path)
		assert.Equal(t, "POST", r.Method)
		assert.Equal(t, "application/json", r.Header.Get("Content-Type"))

		// 验证请求体
		var reqBody map[string]interface{}
		err := json.NewDecoder(r.Body).Decode(&reqBody)
		require.NoError(t, err)
		assert.Equal(t, "ap-region", reqBody["region"])
		assert.Equal(t, "testuser", reqBody["username"])
		assert.Equal(t, "backupuser", reqBody["backup_username"])

		// 返回成功响应
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(successResponse)
	}))
	defer server.Close()

	// 设置环境变量
	os.Setenv("BKBASE_CLB_API_URL", server.URL)
	os.Setenv("BKBASE_CLB_USERNAME", "testuser")
	os.Setenv("BKBASE_CLB_BACKUP_USERNAME", "backupuser")
	defer func() {
		os.Unsetenv("BKBASE_CLB_API_URL")
		os.Unsetenv("BKBASE_CLB_USERNAME")
		os.Unsetenv("BKBASE_CLB_BACKUP_USERNAME")
	}()

	// 重置单例
	clbOnce = sync.Once{}
	clbInstance = nil

	// 执行测试
	svc := GetClbAPIService()
	req := &infreq.GetClbRequest{
		Region: "ap-region",
		ClbIDs: []string{"lb-xxxxxx1"},
	}

	resp, err := svc.GetClb(req)

	// 验证结果
	require.NoError(t, err)
	require.NotNil(t, resp)
	assert.True(t, resp.Result)
	assert.Equal(t, "1500200", resp.Code)
	assert.Equal(t, "ok", resp.Message)
	require.Len(t, resp.Data, 1)
	assert.Equal(t, "lb-xxxxxx1", resp.Data[0].LoadBalancerID)
	assert.Equal(t, "INTERNAL", resp.Data[0].LoadBalancerType)
	assert.Equal(t, "10.0.x.x", resp.Data[0].LoadBalancerVips)
}

// TestGetClb_Failure 测试获取 CLB 失败场景
// Mock API 返回：result=false, data=[], code="1500500", message包含错误信息
func TestGetClb_Failure(t *testing.T) {
	// Mock 失败的响应数据（数据已脱敏）
	failureResponse := map[string]interface{}{
		"result":  false,
		"data":    []map[string]interface{}{},
		"code":    "1500500",
		"message": "[TencentCloudSDKException] code:InvalidParameterValue.Length message:The length of loadbalancerId 'lb-xxxxx' is not valid. requestId:xxxx-xxxx-xxxx",
		"errors":  nil,
	}

	// 创建 mock HTTP 服务器
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// 返回失败响应
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(failureResponse)
	}))
	defer server.Close()

	// 设置环境变量
	os.Setenv("BKBASE_CLB_API_URL", server.URL)
	os.Setenv("BKBASE_CLB_USERNAME", "testuser")
	os.Setenv("BKBASE_CLB_BACKUP_USERNAME", "backupuser")
	defer func() {
		os.Unsetenv("BKBASE_CLB_API_URL")
		os.Unsetenv("BKBASE_CLB_USERNAME")
		os.Unsetenv("BKBASE_CLB_BACKUP_USERNAME")
	}()

	// 重置单例
	clbOnce = sync.Once{}
	clbInstance = nil

	// 执行测试
	svc := GetClbAPIService()
	req := &infreq.GetClbRequest{
		Region: "ap-region",
		ClbIDs: []string{"lb-xxxxx"},
	}

	resp, err := svc.GetClb(req)

	// 验证结果
	require.Error(t, err)
	assert.Nil(t, resp)
	assert.Contains(t, err.Error(), "获取 CLB 失败 [1500500]")
	assert.Contains(t, err.Error(), "InvalidParameterValue.Length")
}

// TestGetClb_EmptyData 测试获取 CLB 返回空列表场景
// Mock API 返回：result=true, data=[], code="1500200", message="ok"
func TestGetClb_EmptyData(t *testing.T) {
	// Mock 成功但 data 为空的响应数据
	emptyDataResponse := map[string]interface{}{
		"result":  true,
		"data":    []map[string]interface{}{},
		"code":    "1500200",
		"message": "ok",
		"errors":  nil,
	}

	// 创建 mock HTTP 服务器
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(emptyDataResponse)
	}))
	defer server.Close()

	// 设置环境变量
	os.Setenv("BKBASE_CLB_API_URL", server.URL)
	os.Setenv("BKBASE_CLB_USERNAME", "testuser")
	os.Setenv("BKBASE_CLB_BACKUP_USERNAME", "backupuser")
	defer func() {
		os.Unsetenv("BKBASE_CLB_API_URL")
		os.Unsetenv("BKBASE_CLB_USERNAME")
		os.Unsetenv("BKBASE_CLB_BACKUP_USERNAME")
	}()

	// 重置单例
	clbOnce = sync.Once{}
	clbInstance = nil

	// 执行测试
	svc := GetClbAPIService()
	req := &infreq.GetClbRequest{
		Region: "ap-region",
		ClbIDs: []string{"lb-xxxxx"},
	}

	resp, err := svc.GetClb(req)

	// 验证结果
	require.Error(t, err)
	assert.Nil(t, resp)
	assert.Contains(t, err.Error(), "获取 CLB 返回空列表 [1500200]")
}
