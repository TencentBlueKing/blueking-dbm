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
	"fmt"
	"log/slog"
	"sync"

	"k8s-dbs/common/util"
	infreq "k8s-dbs/infrastructure/request"

	"github.com/pkg/errors"
	"k8s.io/utils/env"

	infresp "k8s-dbs/infrastructure/response"
)

// DbmAPIService DBM API 服务
type DbmAPIService struct {
	syncDataAPIURL   string // 内部直连地址（同步用），来自 DBM_SYNCDATA_API_URL
	innerBkAppCode   string // 统一凭据，用于同步 Cookie 和鉴权 Header，来自 INNER_BK_APP_CODE
	innerBkAppSecret string // 统一凭据，来自 INNER_BK_APP_SECRET
	dbmAuthAPIURL    string // 鉴权地址（host:port/path），来自 DBM_AUTH_API_URL
}

var (
	instance *DbmAPIService
	once     sync.Once
)

// InitDbmAPIService 初始化DBM API服务（仅从环境变量加载配置）
func InitDbmAPIService() {
	once.Do(func() {
		syncDataAPIURL := env.GetString("DBM_SYNCDATA_API_URL", "localhost:8080")
		innerBkAppCode := env.GetString("INNER_BK_APP_CODE", "")
		innerBkAppSecret := env.GetString("INNER_BK_APP_SECRET", "")
		dbmAuthAPIURL := env.GetString("DBM_AUTH_API_URL", "")

		if syncDataAPIURL == "" {
			slog.Warn("DBM_SYNCDATA_API_URL 未配置，数据同步功能将不可用")
		}
		if dbmAuthAPIURL == "" {
			slog.Warn("DBM_AUTH_API_URL 未配置，IAM 鉴权功能将不可用")
		}
		if innerBkAppCode == "" || innerBkAppSecret == "" {
			slog.Warn("INNER_BK_APP_CODE / INNER_BK_APP_SECRET 未配置")
		}

		instance = &DbmAPIService{
			syncDataAPIURL:   syncDataAPIURL,
			innerBkAppCode:   innerBkAppCode,
			innerBkAppSecret: innerBkAppSecret,
			dbmAuthAPIURL:    dbmAuthAPIURL,
		}
		slog.Info("DBM API服务初始化完成",
			"syncDataAPIURL", syncDataAPIURL, "dbmAuthAPIURL", dbmAuthAPIURL)
	})
}

// GetDbmAPIService 获取DBM API服务实例
func GetDbmAPIService() *DbmAPIService {
	InitDbmAPIService() // once.Do 内部幂等，首次后为 no-op
	return instance
}

// NewDbmAPIService DbmAPIService 构造函数（保持向后兼容）
func NewDbmAPIService() *DbmAPIService {
	return GetDbmAPIService()
}

// sendDBMRequest 发送DBM同步请求，使用环境变量中的凭据（Cookie 认证）
func (d *DbmAPIService) sendDBMRequest(url string, request interface{}) (infresp.DbmAPIResponse, error) {
	options := &util.RequestOptions{
		Cookies: map[string]string{
			"bk_app_code":   d.innerBkAppCode,
			"bk_app_secret": d.innerBkAppSecret,
		},
	}

	// 发送请求
	resp, err := util.BaseHTTPClient.PostWithResponse(url, request, options)
	if err != nil {
		return infresp.DbmAPIResponse{}, errors.Wrap(err, "failed to send HTTP request")
	}

	// 解析响应
	var response infresp.DbmAPIResponse
	if err := util.BaseHTTPClient.ParseResponse(resp, &response); err != nil {
		return infresp.DbmAPIResponse{}, errors.Wrap(err, "failed to parse response")
	}

	// 检查响应结果
	if !response.Result {
		return response, fmt.Errorf("DBM API request failed: %s", response.Message)
	}

	return response, nil
}

// SyncClusterCreated 同步集群创建到 DBM，返回 DBM 分配的集群 ID。
//
// DBM create_cluster API 返回格式: {"result":true, "data":{"id":<int>, ...}}
// 经 encoding/json 标准反序列化后，data 为 map[string]interface{}，id 为 float64。
func (d *DbmAPIService) SyncClusterCreated(request *infreq.CreateClusterRequest) (uint64, error) {
	url := fmt.Sprintf("http://%s/apis/proxypass/k8s/cluster/create/", d.syncDataAPIURL)
	response, err := d.sendDBMRequest(url, request)
	if err != nil {
		return 0, err
	}

	dataMap, ok := response.Data.(map[string]interface{})
	if !ok {
		return 0, fmt.Errorf("unexpected response data type: %T", response.Data)
	}
	id, ok := dataMap["id"].(float64)
	if !ok || id <= 0 {
		return 0, fmt.Errorf("invalid or missing 'id' in response data: %v", dataMap["id"])
	}
	return uint64(id), nil
}

// SyncClusterUpdated 同步集群更新到 DBM
func (d *DbmAPIService) SyncClusterUpdated(request *infreq.UpdateClusterRequest) (infresp.DbmAPIResponse, error) {
	url := fmt.Sprintf("http://%s/apis/proxypass/k8s/cluster/update/", d.syncDataAPIURL)
	return d.sendDBMRequest(url, request)
}

// SyncClusterDeleted 同步集群下架到 DBM
func (d *DbmAPIService) SyncClusterDeleted(request *infreq.DeleteClusterRequest) (infresp.DbmAPIResponse, error) {
	url := fmt.Sprintf("http://%s/apis/proxypass/k8s/cluster/delete/", d.syncDataAPIURL)
	return d.sendDBMRequest(url, request)
}

// SyncDomainCreated 同步域名创建到 DBM DNS 服务，在 ClusterEntry 表中创建接入层条目。
func (d *DbmAPIService) SyncDomainCreated(request *infreq.CreateDomainRequest) (infresp.DbmAPIResponse, error) {
	url := fmt.Sprintf("http://%s/apis/proxypass/k8s/domain/create/", d.syncDataAPIURL)
	return d.sendDBMRequest(url, request)
}

// SyncDomainGet 查询域名解析记录
func (d *DbmAPIService) SyncDomainGet(request *infreq.GetDomainRequest) (infresp.DbmAPIResponse, error) {
	url := fmt.Sprintf("http://%s/apis/proxypass/k8s/domain/get/", d.syncDataAPIURL)
	return d.sendDBMRequest(url, request)
}

// SyncDomainDeleted 删除域名解析记录及 ClusterEntry
func (d *DbmAPIService) SyncDomainDeleted(request *infreq.DeleteDomainRequest) (infresp.DbmAPIResponse, error) {
	url := fmt.Sprintf("http://%s/apis/proxypass/k8s/domain/delete/", d.syncDataAPIURL)
	return d.sendDBMRequest(url, request)
}
