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

	"dbm-services/common/go-pubpkg/logger"
)

// ResourceDeleteHost resource_delete 主机参数
type ResourceDeleteHost struct {
	BkCloudID int    `json:"bk_cloud_id"`
	IP        string `json:"ip"`
	BkHostID  int    `json:"bk_host_id"`
}

// ResourceDelete 请求 DBM API 从资源池删除主机并转入待回收池/故障池
func ResourceDelete(hosts []ResourceDeleteHost, event, remark string) error {
	if len(hosts) == 0 {
		return nil
	}
	cli := NewDbmClient()
	u, err := url.JoinPath(cli.EndPoint, DBMResourceDeleteApi)
	if err != nil {
		return err
	}
	body, err := json.Marshal(map[string]interface{}{
		"hosts":  hosts,
		"event":  event,
		"remark": remark,
	})
	if err != nil {
		logger.Error("marshal ResourceDelete body failed %s", err.Error())
		return err
	}
	ctx, cancel := context.WithTimeout(context.Background(), dissolveCheckTimeout)
	defer cancel()
	request, err := http.NewRequestWithContext(ctx, http.MethodPost, u, bytes.NewBuffer(body))
	if err != nil {
		return err
	}
	request.Header.Add("content-type", "application/json;charset=utf-8")
	cli.addCookie(request)

	resp, err := cli.Client.Do(request)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	content, err := io.ReadAll(resp.Body)
	if err != nil {
		logger.Error("read ResourceDelete response body failed %s", err.Error())
		return err
	}
	logger.Info("ResourceDelete response %s", string(content))

	var baseResp DbmBaseResp
	if err = json.Unmarshal(content, &baseResp); err != nil {
		return err
	}
	if baseResp.Code != 0 {
		return fmt.Errorf("ResourceDelete response code:%d, message:%s", baseResp.Code, baseResp.Message)
	}
	return nil
}
