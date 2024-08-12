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
	"encoding/json"
	"io"
	"net/http"
	"net/url"
	"time"

	"dbm-services/common/go-pubpkg/logger"
)

// GetIdcCityByLogicCityParam TODO
type GetIdcCityByLogicCityParam struct {
	LogicCityName string `json:"logic_city_name"`
}

// IdcCitysResp idc citys respone
type IdcCitysResp struct {
	Code      int      `json:"code"`
	Message   string   `json:"message"`
	Data      []string `json:"data"`
	RequestId string   `json:"request_id"`
}

// GetIdcCityByLogicCity 根据逻辑城市获取实际对应城市列表
func GetIdcCityByLogicCity(logicCity string) (idcCitys []string, err error) {
	var content []byte
	cli := NewDbmClient()
	u, err := url.JoinPath(cli.EndPoint, DBMLogicCityApi)
	if err != nil {
		return nil, err
	}
	p := GetIdcCityByLogicCityParam{
		LogicCityName: logicCity,
	}
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
	cli.addCookie(request)

	f := func() (content []byte, err error) {
		resp, err := cli.Client.Do(request)
		if err != nil {
			return nil, err
		}
		defer resp.Body.Close()
		content, err = io.ReadAll(resp.Body)
		if err != nil {
			logger.Error("read respone body failed %s", err.Error())
			return nil, err
		}
		return
	}

	for i := 0; i <= 3; i++ {
		content, err = f()
		if err == nil {
			break
		}
		logger.Error("read respone body failed %s", err.Error())
		time.Sleep(1 * time.Second)
	}

	if err != nil {
		logger.Error("try 3 time get real citys  from dbm failed %s", err.Error())
		return nil, err
	}

	logger.Info("respone %v", string(content))
	var d IdcCitysResp
	if err = json.Unmarshal(content, &d); err != nil {
		return nil, err
	}
	return d.Data, nil
}

// LogicCityInfo 逻辑城市信息
type LogicCityInfo struct {
	BkIdcCityId     int    `json:"bk_idc_city_id"`
	BkIdcCityName   string `json:"bk_idc_city_name"`
	LogicalCity     int    `json:"logical_city"`
	LogicalCityName string `json:"logical_city_name"`
}

// GetAllLogicCityInfo 获取所有逻辑城市信息
func GetAllLogicCityInfo() (idcCitys []LogicCityInfo, err error) {
	var content []byte
	cli := NewDbmClient()
	u, err := url.JoinPath(cli.EndPoint, DBMListAllLogicCityInfoApi)
	if err != nil {
		return nil, err
	}
	request, err := http.NewRequest(http.MethodGet, u, nil)
	if err != nil {
		return nil, err
	}
	request.Header.Add("content-type", "application/json;charset=utf-8")
	cli.addCookie(request)

	f := func() (content []byte, err error) {
		resp, err := cli.Client.Do(request)
		if err != nil {
			return nil, err
		}
		defer resp.Body.Close()
		content, err = io.ReadAll(resp.Body)
		if err != nil {
			logger.Error("read respone body failed %s", err.Error())
			return nil, err
		}
		return
	}
	for i := 0; i <= 3; i++ {
		content, err = f()
		if err == nil {
			break
		}
		logger.Error("read respone body failed %s", err.Error())
		time.Sleep(1 * time.Second)
	}

	if err != nil {
		logger.Error("try 3 time get real citys  from dbm failed %s", err.Error())
		return nil, err
	}
	logger.Info("respone %v", string(content))
	var d DbmBaseResp
	if err = json.Unmarshal(content, &d); err != nil {
		return nil, err
	}
	var d2 []LogicCityInfo
	if err = json.Unmarshal(d.Data, &d2); err != nil {
		return nil, err
	}
	return d2, nil
}
