// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package consumer

import (
	"encoding/json"
	"io"
	"net/http"
	"net/url"
	"os"
	"strconv"

	"github.com/pkg/errors"
	"golang.org/x/exp/slog"

	"dbm-services/common/db-event-consumer/pkg/config"
)

// QueryKafkaMetaWithBkDataId query data_id from bklog api metadata_get_data_id
func QueryKafkaMetaWithBkDataId(sinker *Sinker, bkdata *config.BkmApiInfo) error {
	if bkdata == nil {
		slog.Error("bkm_api_info config for bklog is nil", slog.Any("table", sinker.RuntimeConfig.ModelTable))
		return errors.New("bkm_api_info config for bklog is nil")
	}
	params := url.Values{}
	params.Add("bk_data_id", strconv.Itoa(sinker.RuntimeConfig.BkDataId))

	metaApiPath := "app/metadata/get_data_id" // bkmonitorv3:metadata_get_data_id
	urlPath, err := url.JoinPath(bkdata.BkmonitorApiUrl, metaApiPath)
	if err != nil {
		slog.Error("join api path", err)
		return err
	}

	endpoint, err := url.Parse(urlPath)
	if err != nil {
		slog.Error("parse url", err, slog.String("url", urlPath))
		return err
	}

	endpoint.RawQuery = params.Encode()

	req, err := http.NewRequest(http.MethodGet, endpoint.String(), nil)
	if err != nil {
		slog.Error("new request", err)
		return err
	}
	if bkdata.BkUsername == "" {
		bkdata.BkUsername = "admin"
	}
	content, err := json.Marshal(struct {
		BkAppCode   string `json:"bk_app_code"`
		BkAppSecret string `json:"bk_app_secret"`
		BkUsername  string `json:"bk_username"`
	}{
		BkAppCode:   bkdata.BkAppCode,
		BkAppSecret: bkdata.BkAppSecret,
		BkUsername:  bkdata.BkUsername,
	})
	if err != nil {
		slog.Error("pack header", err.Error())
		return err
	}
	slog.Info("pack header", slog.String("header", string(content)))

	req.Header.Set("X-Bkapi-Authorization", string(content))
	if bkTenantId := os.Getenv("BK_TENANT_ID"); bkTenantId != "" {
		req.Header.Set("X-Bk-Tenant-Id", bkTenantId)
	}
	slog.Info("request", slog.Any("request", req))

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		slog.Error("call http api", err)
		return err
	}
	if resp.StatusCode < 200 || resp.StatusCode >= 400 {
		err := errors.Errorf("code: %d, msg: %s", resp.StatusCode, resp.Status)
		slog.Error("call http api", err)
		return err
	}

	defer func() {
		_ = resp.Body.Close()
	}()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		slog.Error("read body", err)
		return err
	}
	var res struct {
		RequestId int    `json:"request_id"`
		Result    bool   `json:"result"`
		Code      int    `json:"code"`
		Message   string `json:"message"`
		Data      struct {
			MqConfig config.BkDataKafkaMeta `json:"mq_config"`
		} `json:"data"`
	}
	err = json.Unmarshal(body, &res)
	if err != nil {
		slog.Error("unmarshal response", err)
		return err
	}
	if !res.Result {
		err := errors.Errorf("api failed code: %d, message: %s", res.Code, res.Message)
		slog.Error("check api response", err)
		return err
	}
	sinker.MetaInfo = &config.KafkaMeta{
		AuthInfo: res.Data.MqConfig.AuthInfo,
	}
	sinker.MetaInfo.ClusterConfig.Brokers = res.Data.MqConfig.ClusterConfig.DomainName
	sinker.MetaInfo.ClusterConfig.Port = res.Data.MqConfig.ClusterConfig.Port
	sinker.RuntimeConfig.Topic = res.Data.MqConfig.StorageConfig.Topic

	slog.Info("get meta info",
		slog.Any("table", sinker.RuntimeConfig.ModelTable),
		slog.Any("bk_data_id", sinker.RuntimeConfig.BkDataId),
		slog.Any("topic", sinker.RuntimeConfig.Topic),
		slog.Any("meta", sinker.MetaInfo))

	return nil
}

// ListBkDataId 调用 bklog databus_collectors 接口获取 collectors 列表
// 按 collector_config_name_en 匹配提取 bk_data_id，返回 map[collector_config_name_en]*BkDataConfig
func ListBkDataId(bkdata *config.BkmApiInfo) (map[string]*config.BkDataConfig, error) {
	if bkdata == nil {
		return nil, errors.New("bkm_api_info config for bklog is nil")
	}
	listCollectorsPath := "databus_collectors"
	urlPath, err := url.JoinPath(bkdata.BklogApiUrl, listCollectorsPath)
	if err != nil {
		slog.Error("join api path", err)
		return nil, err
	}

	params := url.Values{}
	params.Add("bk_biz_id", strconv.Itoa(bkdata.BkBizId))
	params.Add("pagesize", "100")
	params.Add("page", "1")

	endpoint, err := url.Parse(urlPath)
	if err != nil {
		slog.Error("parse url", err, slog.String("url", urlPath))
		return nil, err
	}
	endpoint.RawQuery = params.Encode()

	req, err := http.NewRequest(http.MethodGet, endpoint.String(), nil)
	if err != nil {
		slog.Error("new request", err)
		return nil, err
	}
	if bkdata.BkUsername == "" {
		bkdata.BkUsername = "admin"
	}
	content, err := json.Marshal(struct {
		BkAppCode   string `json:"bk_app_code"`
		BkAppSecret string `json:"bk_app_secret"`
		BkUsername  string `json:"bk_username"`
	}{
		BkAppCode:   bkdata.BkAppCode,
		BkAppSecret: bkdata.BkAppSecret,
		BkUsername:  bkdata.BkUsername,
	})
	if err != nil {
		slog.Error("pack header", err.Error())
		return nil, err
	}

	req.Header.Set("X-Bkapi-Authorization", string(content))
	if bkTenantId := os.Getenv("BK_TENANT_ID"); bkTenantId != "" {
		req.Header.Set("X-Bk-Tenant-Id", bkTenantId)
	}
	slog.Info("ListBkDataId request", slog.String("url", endpoint.String()))

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		slog.Error("call http api", err)
		return nil, err
	}
	if resp.StatusCode < 200 || resp.StatusCode >= 400 {
		err := errors.Errorf("code: %d, msg: %s", resp.StatusCode, resp.Status)
		slog.Error("call http api", err)
		return nil, err
	}

	defer func() {
		_ = resp.Body.Close()
	}()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		slog.Error("read body", err)
		return nil, err
	}

	var res struct {
		Result  bool   `json:"result"`
		Code    int    `json:"code"`
		Message string `json:"message"`
		Data    struct {
			Total int                   `json:"total"`
			List  []config.BkDataConfig `json:"list"`
		} `json:"data"`
	}
	err = json.Unmarshal(body, &res)
	if err != nil {
		slog.Error("unmarshal response", err)
		return nil, err
	}
	if !res.Result {
		err := errors.Errorf("api failed code: %d, message: %s", res.Code, res.Message)
		slog.Error("check api response", err)
		return nil, err
	}

	// 按 collector_config_name_en 构建 map
	collectorsMap := make(map[string]*config.BkDataConfig, len(res.Data.List))
	for i := range res.Data.List {
		c := &res.Data.List[i]
		if c.CollectorConfigNameEn != "" {
			collectorsMap[c.CollectorConfigNameEn] = c
		}
	}
	slog.Info("ListBkDataId result", slog.Int("total", res.Data.Total))

	return collectorsMap, nil
}
