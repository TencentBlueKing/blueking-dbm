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

// Package thirdapi 封装对外部第三方服务（如 DBM、CLB）API 的调用
package thirdapi

import (
	"fmt"
	"log/slog"
	"strings"
	"sync"

	"k8s-dbs/common/util"
	infreq "k8s-dbs/infrastructure/request"
	infresp "k8s-dbs/infrastructure/response"

	"github.com/pkg/errors"
	"k8s.io/utils/env"
)

const createClbPath = "/ops/create_clb"

const getClbInfoPath = "/ops/get_clb"

// ClbAPIService CLB API 服务，用于调用 bk-base 的 CLB 创建接口
type ClbAPIService struct {
	clbAPIURL        string // CLB 创建接口域名，来自环境变量 BKBASE_CLB_API_URL
	username         string // 操作用户名，来自环境变量 BKBASE_CLB_USERNAME
	backupUsername   string // 备份操作用户名，来自环境变量 BKBASE_CLB_BACKUP_USERNAME
	operationProduct string // 操作产品，来自环境变量 BKBASE_CLB_OPERATION_PRODUCT
	firstLevelBiz    string // 一级业务，来自环境变量 BKBASE_CLB_FIRST_LEVEL_BIZ
	secondLevelBiz   string // 二级业务，来自环境变量 BKBASE_CLB_SECOND_LEVEL_BIZ
}

var (
	clbInstance *ClbAPIService
	clbOnce     sync.Once
)

// InitClbAPIService 初始化 CLB API 服务（仅从环境变量加载配置）
func InitClbAPIService() {
	clbOnce.Do(func() {
		clbInstance = &ClbAPIService{
			clbAPIURL:        env.GetString("BKBASE_CLB_API_URL", ""),
			username:         env.GetString("BKBASE_CLB_USERNAME", ""),
			backupUsername:   env.GetString("BKBASE_CLB_BACKUP_USERNAME", ""),
			operationProduct: env.GetString("BKBASE_CLB_OPERATION_PRODUCT", ""),
			firstLevelBiz:    env.GetString("BKBASE_CLB_FIRST_LEVEL_BIZ", ""),
			secondLevelBiz:   env.GetString("BKBASE_CLB_SECOND_LEVEL_BIZ", ""),
		}

		if err := clbInstance.validate(); err != nil {
			slog.Warn("CLB 配置不完整，CLB 创建功能将不可用", "missing", err)
		}

		slog.Info("CLB API 服务初始化完成", "clbAPIURL", clbInstance.clbAPIURL)
	})
}

// GetClbAPIService 获取 CLB API 服务实例
func GetClbAPIService() *ClbAPIService {
	InitClbAPIService()
	return clbInstance
}

// NewClbAPIService ClbAPIService 构造函数（保持向后兼容）
func NewClbAPIService() *ClbAPIService {
	return GetClbAPIService()
}

// CreateClb 创建 CLB，调用 bk-base 的 /ops/create_clb 接口。
// 请求参数通过 request 传入（包含 region、vpc_id 等），成功时返回第一个 CLB ID。
func (c *ClbAPIService) CreateClb(request *infreq.CreateClbRequest) (string, error) {
	if err := c.validate(); err != nil {
		return "", err
	}

	url := c.buildURL(createClbPath)

	reqData := map[string]interface{}{
		"region":            request.Region,
		"vpc_id":            request.VpcID,
		"clb_name":          request.ClbName,
		"clb_nums":          request.ClbNums,
		"username":          c.username,
		"backup_username":   c.backupUsername,
		"operation_product": c.operationProduct,
		"first_level_biz":   c.firstLevelBiz,
		"second_level_biz":  c.secondLevelBiz,
	}

	resp, err := util.BaseHTTPClient.PostWithResponse(url, reqData, nil)
	if err != nil {
		return "", errors.Wrap(err, "创建 CLB HTTP 请求失败")
	}

	if resp.StatusCode() < 200 || resp.StatusCode() >= 300 {
		body := truncateBody(resp.String(), 200)
		return "", fmt.Errorf("创建 CLB 返回非 2xx (status=%d): %s", resp.StatusCode(), body)
	}

	var clbResp infresp.CreateClbAPIResponse
	if err := util.BaseHTTPClient.ParseResponse(resp, &clbResp); err != nil {
		return "", errors.Wrap(err, "创建 CLB 响应解析失败")
	}

	if !clbResp.Result {
		slog.Error("创建 CLB 失败",
			"code", clbResp.Code,
			"message", clbResp.Message,
			"errors", clbResp.Errors,
			"clb_name", request.ClbName,
		)
		return "", fmt.Errorf("创建 CLB 失败 [%s]: %s", clbResp.Code, clbResp.Message)
	}

	if len(clbResp.Data) == 0 {
		slog.Error("创建 CLB 返回空列表",
			"code", clbResp.Code,
			"clb_name", request.ClbName,
		)
		return "", fmt.Errorf("创建 CLB 返回空列表 [%s]", clbResp.Code)
	}

	clbID := clbResp.Data[0]
	slog.Info("创建 CLB 成功",
		"clb_id", clbID,
		"clb_name", request.ClbName,
		"code", clbResp.Code,
	)

	return clbID, nil
}

// GetClb 获取 CLB
func (c *ClbAPIService) GetClb(request *infreq.GetClbRequest) (*infresp.GetClbAPIResponse, error) {
	if err := c.validate(); err != nil {
		return nil, err
	}

	url := c.buildURL(getClbInfoPath)

	reqData := map[string]interface{}{
		"region":            request.Region,
		"clb_ids":           request.ClbIDs,
		"username":          c.username,
		"backup_username":   c.backupUsername,
		"operation_product": c.operationProduct,
		"first_level_biz":   c.firstLevelBiz,
		"second_level_biz":  c.secondLevelBiz,
	}

	resp, err := util.BaseHTTPClient.PostWithResponse(url, reqData, nil)
	if err != nil {
		return nil, errors.Wrap(err, "获取 CLB 信息失败")
	}

	if resp.StatusCode() < 200 || resp.StatusCode() >= 300 {
		body := truncateBody(resp.String(), 200)
		return nil, fmt.Errorf("获取 CLB 返回非 2xx (status=%d): %s", resp.StatusCode(), body)
	}

	var clbResp infresp.GetClbAPIResponse
	if err := util.BaseHTTPClient.ParseResponse(resp, &clbResp); err != nil {
		return nil, errors.Wrap(err, "获取 CLB 响应解析失败")
	}

	if !clbResp.Result {
		slog.Error("获取 CLB 失败",
			"code", clbResp.Code,
			"message", clbResp.Message,
			"errors", clbResp.Errors,
			"clb_ids", request.ClbIDs,
		)
		return nil, fmt.Errorf("获取 CLB 失败 [%s]: %s", clbResp.Code, clbResp.Message)
	}

	if len(clbResp.Data) == 0 {
		slog.Error("获取 CLB 返回空列表",
			"code", clbResp.Code,
			"clb_ids", request.ClbIDs,
		)
		return nil, fmt.Errorf("获取 CLB 返回空列表 [%s]", clbResp.Code)
	}

	return &clbResp, nil
}

// validate 校验 CLB 服务配置是否完整，一次性返回所有缺失的必填项。
func (c *ClbAPIService) validate() error {
	var missing []string
	if c.clbAPIURL == "" {
		missing = append(missing, "BKBASE_CLB_API_URL")
	}
	if c.operationProduct == "" {
		missing = append(missing, "BKBASE_CLB_OPERATION_PRODUCT")
	}
	if c.firstLevelBiz == "" {
		missing = append(missing, "BKBASE_CLB_FIRST_LEVEL_BIZ")
	}
	if c.secondLevelBiz == "" {
		missing = append(missing, "BKBASE_CLB_SECOND_LEVEL_BIZ")
	}
	if len(missing) > 0 {
		return fmt.Errorf("CLB 配置缺失: %s", strings.Join(missing, ", "))
	}
	return nil
}

func (c *ClbAPIService) buildURL(path string) string {
	if strings.HasPrefix(c.clbAPIURL, "http://") || strings.HasPrefix(c.clbAPIURL, "https://") {
		return c.clbAPIURL + path
	}
	return fmt.Sprintf("https://%s%s", c.clbAPIURL, path)
}
