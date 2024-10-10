/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package dbmapi TODO
package dbmapi

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"

	"dbm-services/common/db-resource/internal/config"
	"dbm-services/common/db-resource/internal/svr/meta"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
)

// DbmSpec Data dbm 规格信息
type DbmSpec struct {
	SpecId          int                    `json:"spec_id"`
	SpecName        string                 `json:"spec_name"`
	SpecClusterType string                 `json:"spec_cluster_type"`
	SpecMachineType string                 `json:"spec_machine_type"`
	DeviceClass     []string               `json:"device_class"`
	Mem             meta.FloatMeasureRange `json:"mem"`
	Cpu             meta.MeasureRange      `json:"cpu"`
	StorageSpecs    []RealDiskSpec         `json:"storage_spec"`
}

// RealDiskSpec 真实磁盘规格
type RealDiskSpec struct {
	DiskType   string `json:"type"`
	Size       int    `json:"size"`
	MountPoint string `json:"mount_point"`
}

// DbmSpecBaseResp dbm 规格信息
type DbmSpecBaseResp struct {
	Count   int       `json:"code"`
	Results []DbmSpec `json:"results"`
}

// DbmBaseResp dbm base api respone data
type DbmBaseResp struct {
	Code      int             `json:"code"`
	Message   string          `json:"message"`
	RequestId string          `json:"request_id"`
	Data      json.RawMessage `json:"data"`
}

// DbmClient request client
type DbmClient struct {
	EndPoint  string
	AppCode   string
	AppSecret string
	Client    *http.Client
}

// NewDbmClient TODO
func NewDbmClient() *DbmClient {
	base := config.AppConfig.DbMeta
	if cmutil.IsEmpty(config.AppConfig.DbMeta) {
		base = "http://bk-dbm"
	}
	return &DbmClient{
		EndPoint:  base,
		AppCode:   config.AppConfig.BkSecretConfig.BkAppCode,
		AppSecret: config.AppConfig.BkSecretConfig.BKAppSecret,
		Client:    &http.Client{},
	}
}

// GetDbmSpec 获取dbm规格
func (c *DbmClient) GetDbmSpec(queryParam map[string]string) (specData []DbmSpec, err error) {
	fullUrl, err := url.JoinPath(c.EndPoint, DBMSpecApi)
	if err != nil {
		return nil, err
	}
	u, err := url.Parse(fullUrl)
	if err != nil {
		return nil, err
	}
	query := u.Query()
	for k, v := range queryParam {
		query.Set(k, v)
	}
	query.Set("limit", "-1")
	u.RawQuery = query.Encode()
	request, err := http.NewRequest("GET", u.String(), nil)
	if err != nil {
		return nil, err
	}
	c.addCookie(request)
	resp, err := c.Client.Do(request)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		logger.Error("read respone body failed %s", err.Error())
		return
	}
	var rpdata DbmBaseResp
	if err = json.Unmarshal(body, &rpdata); err != nil {
		logger.Error("unmarshal respone body failed %s", err.Error())
		return
	}
	if rpdata.Code != 0 {
		return nil, fmt.Errorf("respone code:%d,message:%s", rpdata.Code, rpdata.Message)
	}
	var specRespData DbmSpecBaseResp
	if err = json.Unmarshal(rpdata.Data, &specRespData); err != nil {
		logger.Error("unmarshal  DbmBaseResp body failed %s", err.Error())
		return
	}
	return specRespData.Results, nil
}

func (c *DbmClient) addCookie(request *http.Request) {
	request.AddCookie(&http.Cookie{Name: "bk_app_code", Path: "/", Value: c.AppCode,
		MaxAge: 86400})
	request.AddCookie(&http.Cookie{Name: "bk_app_secret", Path: "/", Value: c.AppSecret,
		MaxAge: 86400})
}
