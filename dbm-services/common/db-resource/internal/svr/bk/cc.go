/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package bk

import (
	"strconv"
	"time"

	"github.com/pkg/errors"
	"github.com/samber/lo"

	"dbm-services/common/db-resource/internal/config"
	"dbm-services/common/go-pubpkg/cc.v3"
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
)

// BkCmdbClient bk cmdb client
var BkCmdbClient *cc.Client

// BkJobClient bk job client
var BkJobClient *cc.Client

// BkNodeManClient bk node man client
var BkNodeManClient *cc.Client

// CCModuleFields TODO
var CCModuleFields []string

// init CCClient
func InitCCClient() {
	var err error
	BkCmdbClient, err = NewClient(config.AppConfig.BkCmdbApiUrl)
	if err != nil {
		logger.Fatal("初始化 CMDB 客户端失败: API URL=%s, AppCode=%s, Username=%s, 错误详情: %s",
			config.AppConfig.BkCmdbApiUrl,
			config.AppConfig.BkSecretConfig.BkAppCode,
			config.AppConfig.BkSecretConfig.BkUserName,
			err.Error())
		return
	}
	BkJobClient, err = NewClient(config.AppConfig.BkJobApiUrl)
	if err != nil {
		logger.Fatal("初始化 BK Job 客户端失败: API URL=%s, AppCode=%s, Username=%s, 错误详情: %s",
			config.AppConfig.BkJobApiUrl,
			config.AppConfig.BkSecretConfig.BkAppCode,
			config.AppConfig.BkSecretConfig.BkUserName,
			err.Error())
		return
	}
	if lo.IsNotEmpty(config.AppConfig.BkNodeManApiUrl) {
		BkNodeManClient, err = NewClient(config.AppConfig.BkNodeManApiUrl)
		if err != nil {
			logger.Fatal("初始化 BK NodeMan 客户端失败: API URL=%s, AppCode=%s, Username=%s, 错误详情: %s",
				config.AppConfig.BkNodeManApiUrl,
				config.AppConfig.BkSecretConfig.BkAppCode,
				config.AppConfig.BkSecretConfig.BkUserName,
				err.Error())
			return
		}
	} else {
		logger.Warn("BK NodeMan API URL 为空，不初始化 BK NodeMan 客户端")
	}
	CCModuleFields = []string{
		"bk_host_id",
		"bk_cloud_id",
		"bk_host_innerip",
		"bk_asset_id",
		"bk_svr_owner_asset_id",
		"svr_device_class",
		"bk_mem",
		"bk_cpu",
		"bk_disk",
		"idc_city_id",
		"idc_city_name",
		"sub_zone",
		"sub_zone_id",
		"rack_id",
		"svr_type_name",
		"net_device_id",
		"bk_inner_switch_ip",
		"bk_outer_switch_ip",
		"bk_os_type",
		"bk_os_bit",
		"bk_os_version",
		"bk_os_name",
		"idc_id",
		"idc_name",
	}
}

var cli *cc.Client
var newClientErr error

// NewClient 创建BK CC客户端
func NewClient(apiUrl string) (*cc.Client, error) {
	if lo.IsEmpty(apiUrl) {
		return nil, errors.New("API URL 为空，请检查配置")
	}
	cli, newClientErr = cc.NewClient(apiUrl, cc.Secret{
		BKAppCode:   config.AppConfig.BkSecretConfig.BkAppCode,
		BKAppSecret: config.AppConfig.BkSecretConfig.BKAppSecret,
		BKUsername:  config.AppConfig.BkSecretConfig.BkUserName,
	})
	if config.AppConfig.Tenant.Enable {
		if lo.IsEmpty(config.AppConfig.Tenant.Id) {
			return nil, errors.New("租户ID为空，请检查配置")
		}
		cli, newClientErr = cc.NewClientWithTenant(apiUrl, cc.Secret{
			BKAppCode:   config.AppConfig.BkSecretConfig.BkAppCode,
			BKAppSecret: config.AppConfig.BkSecretConfig.BKAppSecret,
			BKUsername:  config.AppConfig.BkSecretConfig.BkUserName,
		}, config.AppConfig.Tenant.Id)
	}
	return cli, newClientErr
}

// BatchQueryHostsInfo 批量查询主机信息
func BatchQueryHostsInfo(bizId int, allHosts []string) (ccHosts []*cc.Host, notFoundHosts []string, err error) {
	for _, hosts := range cmutil.SplitGroup(allHosts, 200) {
		err = cmutil.Retry(cmutil.RetryConfig{Times: 3, DelayTime: 1 * time.Second}, func() error {
			data, resp, errx := cc.NewListBizHostsGw(BkCmdbClient, strconv.Itoa(bizId)).QueryListBizHosts(&cc.ListBizHostsParam{
				BkBizId: bizId,
				Fileds:  CCModuleFields,
				Page: cc.BKPage{
					Start: 0,
					Limit: len(hosts),
				},
				HostPropertyFilter: cc.HostPropertyFilter{
					Condition: "AND",
					Rules: []cc.Rule{
						{
							Field:    "bk_host_innerip",
							Operator: "in",
							Value:    hosts,
						},
					},
				},
			})
			if resp != nil {
				logger.Info("respone request id is %s,message:%s,code:%d", resp.RequestId, resp.Message, resp.Code)
				// 检查API响应状态码
				if resp.Code != 0 {
					logger.Error("QueryListBizHosts API returned error code: %d, message: %s", resp.Code, resp.Message)
					return errors.Errorf("API error code: %d, message: %s", resp.Code, resp.Message)
				}
			}
			if errx != nil {
				logger.Error("QueryListBizHosts failed for bizId:%d, hosts:%v, error:%s", bizId, hosts, errx.Error())
				return errx
			}
			ccHosts = append(ccHosts, data.Info...)
			return nil
		})
		// 如果重试失败，立即返回错误
		if err != nil {
			logger.Error("BatchQueryHostsInfo failed after retries for bizId:%d, hosts:%v, error:%s", bizId, hosts, err.Error())
			return nil, nil, err
		}
	}

	// 构建查找映射
	searchMap := make(map[string]struct{})
	for _, host := range allHosts {
		searchMap[host] = struct{}{}
	}

	// 标记已找到的主机
	for _, hf := range ccHosts {
		delete(searchMap, hf.InnerIP)
	}

	// 收集未找到的主机
	for host := range searchMap {
		notFoundHosts = append(notFoundHosts, host)
	}

	logger.Info("BatchQueryHostsInfo completed for bizId:%d, total hosts:%d, found:%d, not found:%d",
		bizId, len(allHosts), len(ccHosts), len(notFoundHosts))

	return ccHosts, notFoundHosts, nil
}
