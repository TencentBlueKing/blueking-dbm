/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package dbmapi

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"time"

	"dbm-services/common/go-pubpkg/logger"
)

// dissolveCheckTimeout SaaS + HCM 链路超时（DataAPI 默认约 30s，留足余量）
const dissolveCheckTimeout = 90 * time.Second

// CheckHostIsDissolved 请求 DBM API 查询待裁撤主机 ID 列表
func CheckHostIsDissolved(bkHostIds []int) (dissolvedHostIds []int, err error) {
	cli := NewDbmClient()
	u, err := url.JoinPath(cli.EndPoint, DBMDissolveHostsCheckApi)
	if err != nil {
		return nil, err
	}
	body, err := json.Marshal(map[string]interface{}{
		"bk_host_ids": bkHostIds,
	})
	if err != nil {
		logger.Error("marshal CheckHostIsDissolved body failed %s", err.Error())
		return nil, err
	}
	ctx, cancel := context.WithTimeout(context.Background(), dissolveCheckTimeout)
	defer cancel()
	request, err := http.NewRequestWithContext(ctx, http.MethodPost, u, bytes.NewBuffer(body))
	if err != nil {
		return nil, err
	}
	request.Header.Add("content-type", "application/json;charset=utf-8")
	cli.addCookie(request)

	resp, err := cli.Client.Do(request)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	content, err := io.ReadAll(resp.Body)
	if err != nil {
		logger.Error("read CheckHostIsDissolved response body failed %s", err.Error())
		return nil, err
	}
	logger.Info("CheckHostIsDissolved response %s", string(content))

	var baseResp DbmBaseResp
	if err = json.Unmarshal(content, &baseResp); err != nil {
		return nil, err
	}
	if baseResp.Code != 0 {
		return nil, fmt.Errorf("CheckHostIsDissolved response code:%d, message:%s", baseResp.Code, baseResp.Message)
	}
	if len(baseResp.Data) == 0 || string(baseResp.Data) == "null" {
		return []int{}, nil
	}
	if err = json.Unmarshal(baseResp.Data, &dissolvedHostIds); err != nil {
		return nil, err
	}
	return dissolvedHostIds, nil
}
