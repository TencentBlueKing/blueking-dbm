/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package meta TODO
package meta

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"slices"
	"time"

	"dbm-services/common/db-resource/internal/config"
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
)

const (
	// DBMCityUrl 查询逻辑城市映射
	DBMCityUrl = "/apis/proxypass/dbmeta/bk_city_name/"
	// DBMEnviron 查询DBM环境变量
	DBMEnviron = "/apis/conf/system_settings/environ/"
)

// GetIdcCityByLogicCityParam TODO
type GetIdcCityByLogicCityParam struct {
	LogicCityName string `json:"logic_city_name"`
}

// IdcCitysResp TODO
type IdcCitysResp struct {
	Code      int      `json:"code"`
	Message   string   `json:"message"`
	Data      []string `json:"data"`
	RequestId string   `json:"request_id"`
}

// DbmEnvResp TODO
type DbmEnvResp struct {
	Data      DbmEnvData `json:"data"`
	Code      int        `json:"code"`
	Message   string     `json:"message"`
	RequestId string     `json:"request_id"`
}

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

// GetDbmEnv TODO
func GetDbmEnv() (data DbmEnvData, err error) {
	u, err := getRequestUrl(DBMEnviron)
	if err != nil {
		return DbmEnvData{}, err
	}
	logger.Info("request url %s", u)
	req, err := http.NewRequest(http.MethodGet, u, nil)
	if err != nil {
		return DbmEnvData{}, err
	}
	addCookie(req)
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
	var rpdata DbmEnvResp
	if err = json.Unmarshal(content, &rpdata); err != nil {
		return DbmEnvData{}, err
	}
	if rpdata.Code != 0 {
		return DbmEnvData{}, errors.New(rpdata.Message)
	}
	logger.Info("get dbm env respone body %s", string(content))
	return rpdata.Data, nil
}

func addCookie(request *http.Request) {
	request.AddCookie(&http.Cookie{Name: "bk_app_code", Path: "/", Value: config.AppConfig.BkSecretConfig.BkAppCode,
		MaxAge: 86400})
	request.AddCookie(&http.Cookie{Name: "bk_app_secret", Path: "/", Value: config.AppConfig.BkSecretConfig.BKAppSecret,
		MaxAge: 86400})
}

func getRequestUrl(apiaddr string) (string, error) {
	base := config.AppConfig.DbMeta
	if cmutil.IsEmpty(config.AppConfig.DbMeta) {
		base = "http://bk-dbm"
	}
	return url.JoinPath(base, apiaddr)
}

// GetIdcCityByLogicCity 根据逻辑城市获取实际对应城市列表
func GetIdcCityByLogicCity(logicCity string) (idcCitys []string, err error) {
	var content []byte
	var resp *http.Response
	u, err := getRequestUrl(DBMCityUrl)
	if err != nil {
		return nil, err
	}
	p := GetIdcCityByLogicCityParam{
		LogicCityName: logicCity,
	}
	client := &http.Client{} // 客户端,被Get,Head以及Post使用
	body, err := json.Marshal(p)
	if err != nil {
		logger.Error("marshal GetIdcCityByLogicCityParam body failed %s ", err.Error())
		return nil, err
	}
	request, err := http.NewRequest(http.MethodPost, u, bytes.NewBuffer(body))
	if err != nil {
		return nil, err
	}
	request.Header.Add("content-type", "application/json;charset=utf-8")
	addCookie(request)
	for i := 0; i <= 5; i++ {
		resp, err = client.Do(request)
		if err != nil {
			if resp != nil {
				if slices.Contains([]int{http.StatusInternalServerError, http.StatusTooManyRequests, http.StatusGatewayTimeout},
					resp.StatusCode) {
					time.Sleep(200 * time.Millisecond)
					continue
				}
			}
			logger.Error("request %s failed %s", request.RequestURI, err.Error())
			return nil, err
		}
		content, err = io.ReadAll(resp.Body)
		if err != nil {
			logger.Error("read respone body failed %s", err.Error())
			return nil, err
		}
		break
	}
	defer resp.Body.Close()
	logger.Info("respone %v", string(content))
	var d IdcCitysResp
	if err = json.Unmarshal(content, &d); err != nil {
		return nil, err
	}
	return d.Data, nil
}
