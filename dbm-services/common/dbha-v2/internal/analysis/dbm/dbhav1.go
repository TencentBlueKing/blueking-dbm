/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

package dbm

import (
	"context"
	"encoding/json"
	"net/http"
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/hanet"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
)

// Dbhav1BlackWhiteListItem defined the item of black white list in dbha-v1.
type Dbhav1BlackWhiteListItem struct {
	ID            uint      `json:"id"`
	BkBizID       int       `json:"bk_biz_id"`
	ClusterID     int       `json:"cluster_id"`
	ClusterName   string    `json:"cluster_name"`
	SwitchVersion string    `json:"switch_version"`
	Status        string    `json:"status"`
	CreatedAt     time.Time `json:"created_at"`
	UpdatedAt     time.Time `json:"updated_at"`
}

// Dbhav1BlackWhitelistQueryArgs represents the query args for getting black white list in dbha-v1.
type Dbhav1BlackWhitelistQueryArgs struct {
	BkBizID       int    `json:"bk_biz_id,omitempty"`
	BkCloudID     int    `json:"bk_cloud_id,omitempty"`
	ClusterID     int    `json:"cluster_id,omitempty"`
	ClusterName   string `json:"cluster_name,omitempty"`
	SwitchVersion string `json:"switch_version,omitempty"`
	Status        string `json:"status,omitempty"`
}

// Dbhav1BlackWhitelistGetRequest represents the request for getting black white list in dbha-v1.
type Dbhav1BlackWhitelistGetRequest struct {
	BkCloudID    int                           `json:"bk_cloud_id"`
	DbCloudToken string                        `json:"db_cloud_token"`
	Name         string                        `json:"name"`
	QueryArgs    Dbhav1BlackWhitelistQueryArgs `json:"query_args"`
}

// Dbhav1BlackWhiteListResponse represents the response structure for black white list query in dbha-v1.
type Dbhav1BlackWhiteListResponse struct {
	Code    int                         `json:"code"`
	Message string                      `json:"msg"`
	Data    []*Dbhav1BlackWhiteListItem `json:"data"`
}

func (c *Client) requestBlackWhiteList(ctx context.Context, req *Dbhav1BlackWhitelistGetRequest) (int, *Dbhav1BlackWhiteListResponse, error) {
	data, err := json.Marshal(&req)
	if err != nil {
		return 0, nil, gerrors.Newf(gerrors.InvalidJson, "failed to marshal black white list request, %s", err)
	}

	apiCfg := config.Cfg.Workflow.Dbhav1ApiBlackWhitelistGet
	cli := c.getRequestClientWithTimeout(apiCfg.Timeout)

	start := time.Now()
	code, resp, err := cli.Post(ctx, apiCfg.Api, data)
	c.ReportAPIMetric(start, apiCfg.Api, hanet.HttpMethodPost, code, err)
	if err != nil {
		return code, nil, err
	}

	if http.StatusOK != code {
		return code, nil, gerrors.Newf(gerrors.HttpRequestFailure, "HTTP responded with a bad code: %d", code)
	}

	if len(resp) == 0 {
		return code, nil, gerrors.Newf(gerrors.Failure, "no response from dbha-v1")
	}

	blackWhiteListRsp := &Dbhav1BlackWhiteListResponse{}
	if err := json.Unmarshal(resp, blackWhiteListRsp); err != nil {
		return code, nil, gerrors.Newf(gerrors.InvalidJson, "failed to unmarshal black white list response, %s", err)
	}

	return code, blackWhiteListRsp, nil
}

// GetBlackWhiteListFromDbhaV1 gets black white list from dbha-v1
func (c *Client) GetBlackWhiteListFromDbhaV1(ctx context.Context, bkCloudId int, bkBizId int) ([]*Dbhav1BlackWhiteListItem, error) {
	req := Dbhav1BlackWhitelistGetRequest{
		BkCloudID:    bkCloudId,
		DbCloudToken: config.Cfg.Workflow.Dbhav1ApiBlackWhitelistGet.Token,
		Name:         "get_black_white_list",
		QueryArgs: Dbhav1BlackWhitelistQueryArgs{
			BkCloudID:     bkCloudId,
			BkBizID:       bkBizId,
			SwitchVersion: string(hamodel.SwitchVersionV2),
			Status:        string(hamodel.StatusTypeEnabled),
		},
	}

	logger.Debug(
		"dbha-v1 black white list query request, bk_cloud_id: %d, bk_biz_id: %d, switch_version: %s, status: %s",
		bkCloudId, bkBizId, hamodel.SwitchVersionV2, hamodel.StatusTypeEnabled)

	_, response, err := c.requestBlackWhiteList(ctx, &req)
	if err != nil {
		return nil, err
	}

	logger.Debug("dbha-v1 black white list query response, list_len: %d", len(response.Data))

	if response.Code != 0 {
		return nil, gerrors.Newf(gerrors.Failure,
			"failed to get black white list from dbha-v1, code: %d, message: %s",
			response.Code, response.Message)
	}

	return response.Data, nil
}
