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
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"

	"dbm-services/common/go-pubpkg/logger"
)

// DbmEnvData TODO
type DbmEnvData struct {
	BK_DOMAIN         string `json:"BK_DOMAIN"`
	CC_IDLE_MODULE_ID int    `json:"CC_IDLE_MODULE_ID"`
	CC_MANAGE_TOPO    struct {
		SetId            int `json:"set_id"`
		DirtyModuleId    int `json:"dirty_module_id"`
		ResourceModuleId int `json:"resource_module_id"`
	} `json:"CC_MANAGE_TOPO"`
}

// GetDbmEnv get dbm env
func GetDbmEnv() (data DbmEnvData, err error) {
	c := NewDbmClient()
	return c.getDbmEnv()
}

// getDbmEnv get dbm env
func (c *DbmClient) getDbmEnv() (data DbmEnvData, err error) {
	u, err := url.JoinPath(c.EndPoint, DBMEnvironApi)
	if err != nil {
		return DbmEnvData{}, err
	}
	logger.Info("request url %s", u)
	req, err := http.NewRequest(http.MethodGet, u, nil)
	if err != nil {
		return DbmEnvData{}, err
	}
	c.addCookie(req)
	var content []byte
	resp, err := http.DefaultClient.Do(req)
	if resp.Body != nil {
		content, err = io.ReadAll(resp.Body)
		if err != nil {
			logger.Error("read respone body failed %s", err.Error())
			return data, err
		}
	}
	if err != nil {
		return DbmEnvData{}, fmt.Errorf("respone body %s,err:%v", string(content), err)
	}
	defer resp.Body.Close()
	logger.Info("get dbm env respone body %s", string(content))

	var rpdata DbmBaseResp
	if err = json.Unmarshal(content, &rpdata); err != nil {
		return DbmEnvData{}, err
	}
	if rpdata.Code != 0 {
		return DbmEnvData{}, errors.New(rpdata.Message)
	}
	var dbmEnvResp DbmEnvData
	if err = json.Unmarshal(rpdata.Data, &dbmEnvResp); err != nil {
		return DbmEnvData{}, err
	}
	return dbmEnvResp, nil
}
