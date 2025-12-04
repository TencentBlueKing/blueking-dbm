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

	"k8s-dbs/common/util"
	infreq "k8s-dbs/infrastructure/request"

	"github.com/pkg/errors"
	"k8s.io/utils/env"

	infresp "k8s-dbs/infrastructure/response"
)

// DbmAPIService DBM API 服务
type DbmAPIService struct {
	dbmAPIURL   string
	bkAppCode   string
	bkAppSecret string
}

// NewDbmAPIService DbmAPIService 构造函数
func NewDbmAPIService() *DbmAPIService {
	dbmAPIURL := env.GetString("DBM_API_URL", "localhost:8080")
	bkAppCode := env.GetString("DBM_BK_APP_CODE", "default_app_code")
	bkAppSecret := env.GetString("DBM_BK_APP_SECRET", "default_app_secret")

	if dbmAPIURL == "" {
		slog.Warn("DBM API URL configuration is required")
	}
	if bkAppCode == "" || bkAppSecret == "" {
		slog.Warn("BK_APP_CODE and BK_APP_SECRET configuration is required")
	}
	return &DbmAPIService{
		dbmAPIURL:   dbmAPIURL,
		bkAppCode:   bkAppCode,
		bkAppSecret: bkAppSecret,
	}
}

// sendDBMRequest 发送DBM API请求的通用方法
func (d *DbmAPIService) sendDBMRequest(url string, request interface{}) (infresp.DbmAPIResponse, error) {
	// 构建Cookies
	options := &util.RequestOptions{
		Cookies: map[string]string{
			"bk_app_code":   d.bkAppCode,
			"bk_app_secret": d.bkAppSecret,
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

// SyncClusterCreated 同步集群创建到 DBM
func (d *DbmAPIService) SyncClusterCreated(request *infreq.CreateClusterRequest) (infresp.DbmAPIResponse, error) {
	url := fmt.Sprintf("http://%s/apis/proxypass/k8s/cluster/create/", d.dbmAPIURL)
	return d.sendDBMRequest(url, request)
}

// SyncClusterUpdated 同步集群更新到 DBM
func (d *DbmAPIService) SyncClusterUpdated(request *infreq.UpdateClusterRequest) (infresp.DbmAPIResponse, error) {
	url := fmt.Sprintf("http://%s/apis/proxypass/k8s/cluster/update/", d.dbmAPIURL)
	return d.sendDBMRequest(url, request)
}

// SyncClusterDeleted 同步集群下架到 DBM
func (d *DbmAPIService) SyncClusterDeleted(request *infreq.DeleteClusterRequest) (infresp.DbmAPIResponse, error) {
	url := fmt.Sprintf("http://%s/apis/proxypass/k8s/cluster/delete/", d.dbmAPIURL)
	return d.sendDBMRequest(url, request)
}
