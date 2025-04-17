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

// init TODO
func init() {
	var err error
	BkCmdbClient, err = NewClient(config.AppConfig.BkCmdbApiUrl)
	if err != nil {
		logger.Fatal("init cmdb client failed %s", err.Error())
		return
	}
	BkJobClient, err = NewClient(config.AppConfig.BkJobApiUrl)
	if err != nil {
		logger.Fatal("init bk job client failed %s", err.Error())
		return
	}
	BkNodeManClient, err = NewClient(config.AppConfig.BkNodeManApiUrl)
	if err != nil {
		logger.Fatal("init bk node man client failed %s", err.Error())
		return
	}
	CCModuleFields = []string{
		"bk_host_id",
		"bk_cloud_id",
		"bk_host_innerip",
		"bk_asset_id",
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
	}
}

var cli *cc.Client
var clierr error

// NewClient TODO
func NewClient(apiurl string) (*cc.Client, error) {
	cli, clierr = cc.NewClient(apiurl, cc.Secret{
		BKAppCode:   config.AppConfig.BkSecretConfig.BkAppCode,
		BKAppSecret: config.AppConfig.BkSecretConfig.BKAppSecret,
		BKUsername:  config.AppConfig.BkSecretConfig.BkUserName,
	})
	return cli, clierr
}

// BatchQueryHostsInfo TODO
func BatchQueryHostsInfo(bizId int, allhosts []string) (ccHosts []*cc.Host, nofoundHosts []string, err error) {
	for _, hosts := range cmutil.SplitGroup(allhosts, 200) {
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
			}
			if errx != nil {
				logger.Error("QueryListBizHosts failed %s", errx.Error())
				return errx
			}
			ccHosts = append(ccHosts, data.Info...)
			return nil
		})
	}
	searchMap := make(map[string]struct{})
	for _, host := range allhosts {
		searchMap[host] = struct{}{}
	}
	for _, hf := range ccHosts {
		delete(searchMap, hf.InnerIP)
		logger.Info("cc info %v", hf)
	}
	for host := range searchMap {
		nofoundHosts = append(nofoundHosts, host)
	}
	return ccHosts, nofoundHosts, err
}
