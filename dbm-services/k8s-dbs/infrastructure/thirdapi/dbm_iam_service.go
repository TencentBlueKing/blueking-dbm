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
	"encoding/json"
	"fmt"
	"log/slog"
	"strings"

	"github.com/go-resty/resty/v2"
	"github.com/pkg/errors"

	"k8s-dbs/common/util"
	infreq "k8s-dbs/infrastructure/request"
	infresp "k8s-dbs/infrastructure/response"
)

// SimpleCheckAllowed 调用 DBM 的 /iam/simple_check_allowed/ 接口做鉴权。
// bkAppCode/bkAppSecret 来自环境变量 INNER_BK_APP_CODE / INNER_BK_APP_SECRET。
// is_raise_exception=true 时，无权限会返回 code=9900403 + permission 和 apply_url。
// 返回值：
//   - allowed=true, applyData=nil  → 有权限
//   - allowed=false, applyData!=nil → 无权限，附带申请信息
//   - err!=nil → 调用失败
func (d *DbmAPIService) SimpleCheckAllowed(
	username, actionID string, bkBizID int, resourceID string,
) (bool, *infresp.ApplyData, error) {
	if d.dbmAuthAPIURL == "" {
		return false, nil, fmt.Errorf("环境变量 DBM_AUTH_API_URL 未配置，无法进行 IAM 鉴权")
	}
	url := fmt.Sprintf("http://%s/iam/simple_check_allowed/", d.dbmAuthAPIURL)
	req := infreq.SimpleCheckAllowedRequest{
		ActionID:         actionID,
		BkBizID:          bkBizID,
		ResourceID:       resourceID,
		IsRaiseException: true,
	}

	authHeader, err := json.Marshal(map[string]string{
		"bk_app_code":   d.innerBkAppCode,
		"bk_app_secret": d.innerBkAppSecret,
		"bk_username":   username,
	})
	if err != nil {
		return false, nil, errors.Wrap(err, "构建鉴权 Header 失败")
	}
	options := &util.RequestOptions{
		Headers: map[string]string{
			"X-Bkapi-Authorization": string(authHeader),
		},
	}

	resp, err := util.BaseHTTPClient.PostWithResponse(url, req, options)
	if err != nil {
		return false, nil, errors.Wrapf(err, "simple_check_allowed HTTP 请求失败 (url=%s)", url)
	}

	result, err := validateAndParseResponse(resp, url)
	if err != nil {
		return false, nil, err
	}

	slog.Info("[DEBUG-IAM] DBM simple_check_allowed 原始响应",
		"code", result.Code,
		"message", result.Message,
		"data_raw", string(result.Data),
		"action_id", req.ActionID,
		"username", username,
	)

	return interpretCheckResult(result)
}

func validateAndParseResponse(
	resp *resty.Response, url string,
) (*infresp.SimpleCheckAllowedResponse, error) {
	statusCode := resp.StatusCode()
	if statusCode < 200 || statusCode >= 300 {
		body := truncateBody(resp.String(), 200)
		return nil, fmt.Errorf("simple_check_allowed 返回非 2xx (url=%s, status=%d): %s", url, statusCode, body)
	}
	contentType := resp.Header().Get("Content-Type")
	if contentType != "" && !strings.Contains(contentType, "application/json") {
		body := truncateBody(resp.String(), 200)
		return nil, fmt.Errorf(
			"simple_check_allowed 响应非 JSON (url=%s, status=%d, content-type=%s): %s",
			url, statusCode, contentType, body)
	}

	var result infresp.SimpleCheckAllowedResponse
	if err := json.Unmarshal(resp.Body(), &result); err != nil {
		body := truncateBody(resp.String(), 200)
		return nil, errors.Wrapf(err, "simple_check_allowed 响应解析失败 (url=%s, status=%d, body=%s)",
			url, statusCode, body)
	}
	return &result, nil
}

func interpretCheckResult(
	result *infresp.SimpleCheckAllowedResponse,
) (bool, *infresp.ApplyData, error) {
	if result.Code == infresp.PermissionDeniedCode {
		var applyData infresp.ApplyData
		if err := json.Unmarshal(result.Data, &applyData); err != nil {
			return false, nil, errors.Wrap(err, "解析权限申请数据失败")
		}
		slog.Info("[DEBUG-IAM] 解析到 applyData",
			"apply_url", applyData.ApplyURL,
			"system_id", applyData.Permission.SystemID,
			"actions_count", len(applyData.Permission.Actions),
		)
		return false, &applyData, nil
	}

	if result.Code != 0 {
		return false, nil, fmt.Errorf("DBM simple_check_allowed 返回失败(code=%d): %s", result.Code, result.Message)
	}

	var allowed bool
	if err := json.Unmarshal(result.Data, &allowed); err != nil {
		return false, nil, errors.Wrap(err, "解析鉴权结果失败")
	}
	return allowed, nil, nil
}

// truncateBody 截断响应体用于错误日志，避免超长 HTML 页面污染日志。
func truncateBody(s string, maxLen int) string {
	if len(s) <= maxLen {
		return s
	}
	return s[:maxLen] + "...(truncated)"
}
