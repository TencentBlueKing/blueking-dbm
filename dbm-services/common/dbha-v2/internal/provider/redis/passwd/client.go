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

package redispasswd

import (
	"context"
	"encoding/json"
	"net/http"
	"time"

	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/hanet"
	"dbm-services/common/dbha-v2/pkg/logger"
)

const (
	// queryAttempts bounds how many times one query is sent, the first included.
	queryAttempts = 3
	// queryBackoff is waited before the second attempt, then doubled.
	queryBackoff = 200 * time.Millisecond
)

// passwdInstance identifies one entry in the password service. Redis passwords are
// stored per cluster, so IP carries the cluster id rather than an address.
type passwdInstance struct {
	IP        string `json:"ip"`
	Port      int    `json:"port"`
	BkCloudID int    `json:"bk_cloud_id"`
}

// passwdUser selects which credential of an instance to read.
type passwdUser struct {
	UserName  string `json:"username"`
	Component string `json:"component"`
}

// queryPasswdRequest is the body of one password query.
type queryPasswdRequest struct {
	DbCloudToken string           `json:"db_cloud_token"`
	BkCloudID    int              `json:"bk_cloud_id"`
	Instances    []passwdInstance `json:"instances"`
	Users        []passwdUser     `json:"users"`
	Limit        int              `json:"limit"`
	Offset       int              `json:"offset"`
}

// passwdItem is one returned credential. Password is base64 encoded.
type passwdItem struct {
	IP        string `json:"ip"`
	Port      int    `json:"port"`
	BkCloudID int    `json:"bk_cloud_id"`
	UserName  string `json:"username"`
	Password  string `json:"password"`
	Component string `json:"component"`
}

// queryPasswdData is the payload of a successful query.
type queryPasswdData struct {
	Count int          `json:"count"`
	Items []passwdItem `json:"items"`
}

// queryPasswdResponse is the DBM proxy envelope. Only Code is checked: this
// endpoint does not always carry "result", so relying on it would reject good
// responses.
type queryPasswdResponse struct {
	Code    int             `json:"code"`
	Message string          `json:"message"`
	Data    queryPasswdData `json:"data"`
}

// query asks the password service for the credentials of the given instances,
// retrying a failed attempt a few times before giving up.
//
// Callers reach this through singleflight, so the retries of concurrent lookups
// are shared instead of multiplied.
func (s *service) query(
	bkCloudID int, instances []passwdInstance, users []passwdUser, limit int,
) ([]passwdItem, error) {
	cfg, err := s.queryConfig()
	if err != nil {
		return nil, err
	}

	req := queryPasswdRequest{
		DbCloudToken: cfg.Token,
		BkCloudID:    bkCloudID,
		Instances:    instances,
		Users:        users,
		Limit:        limit,
	}

	data, err := json.Marshal(&req)
	if err != nil {
		return nil, gerrors.Newf(gerrors.InvalidJson, "failed to marshal request, errmsg: %s", err)
	}

	backoff := queryBackoff
	for attempt := 1; ; attempt++ {
		items, err := post(cfg, data)
		if err == nil {
			return items, nil
		}
		if attempt == queryAttempts {
			return nil, err
		}

		logger.Warn("retrying redis password query, attempt: %d, errmsg: %s", attempt, err)
		time.Sleep(backoff)
		backoff *= 2
	}
}

// post sends one query.
//
// It does not reuse analysis' dbm.Client, whose package pulls in the analysis
// config and metric definitions that this package must stay free of. The HTTP
// client is built per call so a config reload never has to invalidate it.
func post(cfg QueryConfig, data []byte) ([]passwdItem, error) {
	cli := hanet.NewHttpClientWithHeaders(map[string]string{"Content-Type": "application/json"})
	if cfg.Timeout > 0 {
		cli.SetTimeout(cfg.Timeout)
	}

	code, resp, err := cli.Post(context.Background(), cfg.API, data)
	if err != nil {
		return nil, err
	}

	if code != http.StatusOK {
		return nil, gerrors.Newf(gerrors.HttpRequestFailure,
			"password service responded with a bad code: %d", code)
	}

	rsp := &queryPasswdResponse{}
	if err := json.Unmarshal(resp, rsp); err != nil {
		return nil, gerrors.Newf(gerrors.InvalidJson, "failed to unmarshal response, errmsg: %s", err)
	}

	if rsp.Code != 0 {
		return nil, gerrors.Newf(gerrors.Failure,
			"password query failed, code: %d, errmsg: %s", rsp.Code, rsp.Message)
	}

	return rsp.Data.Items, nil
}
