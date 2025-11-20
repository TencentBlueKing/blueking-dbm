// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package core

import (
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"dbm-services/common/reverseapi/define"
	"dbm-services/common/reverseapi/pkg"

	"github.com/avast/retry-go/v4"
	"github.com/pkg/errors"
)

const reverseApiBase = "apis/proxypass/reverse_api"

type apiResponse struct {
	Result  bool            `json:"result"`
	Code    int             `json:"code"`
	Message string          `json:"message"`
	Errors  json.RawMessage `json:"errors"`
	Data    json.RawMessage `json:"data"`
}

type Core struct {
	bkCloudId  int64
	nginxAddrs []string
	ip         string
	debug      bool
	client     *http.Client
	retryOpts  []retry.Option
}

func (c *Core) BkCloudId() int64 {
	return c.bkCloudId
}

func (c *Core) NginxAddrs() []string {
	return c.nginxAddrs
}

// SetTimeout 这个地方要大于服务端的超时
func (c *Core) SetTimeout(n int) {
	c.client.Timeout = time.Duration(n) * time.Second
}

var DefaultRetryOpts = []retry.Option{
	retry.Attempts(3),
	retry.Delay(1 * time.Second),
	retry.DelayType(retry.FixedDelay),
}

// NewCoreWithAddr
/*
根据 nginx addrs 的内容格式不同, bkCloudId 不是必要的参数
1. 格式是 IP:PORT 时, bkCloudId 必须是正确的, 有意义的
2. 格式是 BK_CLOUD_ID:IP:PORT 时, bkCloudId 可以随便写一个, 会被文件内容覆盖
*/
func NewCoreWithAddr(bkCloudId int64, mixAddrs []string, retryOpts ...retry.Option) (*Core, error) {
	// default timeout is 10s
	return NewCoreWithAddrWithTimeout(bkCloudId, mixAddrs, 10*time.Second, retryOpts...)
}

// NewCoreWithAddrWithTimeout 带超时
func NewCoreWithAddrWithTimeout(
	bkCloudId int64, mixAddrs []string, timeout time.Duration, retryOpts ...retry.Option) (*Core, error) {
	var err error
	var addrs []string
	bkCloudIdMap := make(map[int64]struct{})

	for _, line := range mixAddrs {
		var addr string
		splitLine := strings.Split(line, ":")
		switch len(splitLine) {
		case 2:
			bkCloudIdMap[bkCloudId] = struct{}{}
			_, err = strconv.ParseInt(splitLine[1], 10, 64)
			if err != nil {
				return nil, errors.Wrapf(err, "bad nginx proxy port: %s", line)
			}
			addr = fmt.Sprintf("%s:%s", splitLine[0], splitLine[1])
		case 3:
			bkCloudId, err = strconv.ParseInt(splitLine[0], 10, 64)
			if err != nil {
				return nil, errors.Wrapf(err, "bad nginx bk cloud id: %s", line)
			}
			_, err = strconv.ParseInt(splitLine[2], 10, 64)
			if err != nil {
				return nil, errors.Wrapf(err, "bad nginx proxy port: %s", line)
			}
			bkCloudIdMap[bkCloudId] = struct{}{}
			addr = fmt.Sprintf("%s:%s", splitLine[1], splitLine[2])
		default:
			return nil, errors.Errorf("failed parse line from: %s", line)
		}
		addrs = append(addrs, addr)
	}
	if len(bkCloudIdMap) > 1 {
		return nil, errors.Errorf("different bk cloud id from %v", mixAddrs)
	}

	return &Core{
		bkCloudId:  bkCloudId,
		nginxAddrs: addrs,
		debug:      false,
		client: &http.Client{
			Transport: &http.Transport{
				MaxIdleConnsPerHost: 2,
				MaxIdleConns:        2,
				MaxConnsPerHost:     5,
			},
			Timeout: timeout,
		},
		retryOpts: retryOpts,
	}, nil
}

// NewCoreWithAddrsFile
/*
根据 nginx addrs file 的内容格式不同, bkCloudId 不是必要的参数
1. 格式是 IP:PORT 时, bkCloudId 必须是正确的, 有意义的
2. 格式是 BK_CLOUD_ID:IP:PORT 时, bkCloudId 可以随便写一个, 会被文件内容覆盖
*/
func NewCoreWithAddrsFile(bkCloudId int64, alterNginxAddrsFile string, retryOpts ...retry.Option) (*Core, error) {
	if !filepath.IsAbs(alterNginxAddrsFile) {
		cwd, _ := os.Getwd()
		alterNginxAddrsFile = filepath.Join(cwd, alterNginxAddrsFile)
	}
	lines, err := pkg.ReadNginxProxyAddrs(alterNginxAddrsFile)
	if err != nil {
		return nil, errors.Wrap(err, "failed to read nginx proxy addrs")
	}

	return NewCoreWithAddr(bkCloudId, lines, retryOpts...)
}

// NewCore With Default address file and timeout
/*
根据 nginx addrs file 的内容格式不同, bkCloudId 不是必要的参数
1. 格式是 IP:PORT 时, bkCloudId 必须是正确的, 有意义的
2. 格式是 BK_CLOUD_ID:IP:PORT 时, bkCloudId 可以随便写一个, 会被文件内容覆盖
*/
func NewCore(bkCloudId int64, retryOpts ...retry.Option) (*Core, error) {
	return NewCoreWithAddrsFile(
		bkCloudId,
		filepath.Join(define.DefaultCommonConfigDir, define.DefaultNginxProxyAddrsFileName),
		retryOpts...,
	)
}

func NewDebugCore(bkCloudId int64, ip string, addrs []string, retryOpts ...retry.Option) *Core {
	return &Core{
		bkCloudId:  bkCloudId,
		nginxAddrs: addrs,
		debug:      true,
		ip:         ip,
		client: &http.Client{
			Transport: &http.Transport{
				MaxIdleConnsPerHost: 5,
				MaxIdleConns:        5,
				MaxConnsPerHost:     100,
			},
		},
		retryOpts: retryOpts,
	}
}
