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

type messageWrapper struct {
	Items []struct {
		Data json.RawMessage `json:"data"`
	} `json:"items"`
}

// QueryKafkaMetaWithBkDataId query data_id from bklog api metadata_get_data_id
func QueryKafkaMetaWithBkDataId(sinker *Sinker, bkdata *config.BkmApiInfo) error {
	params := url.Values{}
	params.Add("bk_data_id", strconv.Itoa(sinker.RuntimeConfig.BkDataId))

	metaApiPath := "app/metadata/get_data_id" // bkmonitorv3:metadata_get_data_id
	urlPath, err := url.JoinPath(bkdata.BkApiUrl, metaApiPath)
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

	content, err := json.Marshal(struct {
		BkAppCode   string `json:"bk_app_code"`
		BkAppSecret string `json:"bk_app_secret"`
		BkUsername  string `json:"bk_username"`
	}{
		BkAppCode:   bkdata.BkAppCode,
		BkAppSecret: bkdata.BkAppSecret,
		BkUsername:  "fake",
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
