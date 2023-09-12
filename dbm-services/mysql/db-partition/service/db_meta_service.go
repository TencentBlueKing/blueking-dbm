/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package service

import (
	"encoding/json"
	"fmt"
	"net/http"

	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/mysql/db-partition/util"

	"github.com/spf13/viper"
	"golang.org/x/exp/slog"
)

// Tendbha TODO
const Tendbha string = "tendbha"

// Tendbsingle TODO
const Tendbsingle string = "tendbsingle"

// Tendbcluster TODO
const Tendbcluster string = "tendbcluster"

// CheckFailed TODO
const CheckFailed string = "FAILED"

// CheckSucceeded TODO
const CheckSucceeded string = "SUCCEEDED"

// ExecuteAsynchronous TODO
const ExecuteAsynchronous string = "UNKNOWN"

// BackendMaster TODO
const BackendMaster string = "backend_master"

// Orphan TODO
const Orphan string = "orphan"

// CreateDbmTicket bk-dbm生成单据的接口
func CreateDbmTicket(config Ticket) (int, error) {
	var ticketId int
	type Data struct {
		Id                int     `json:"id"`
		Creator           string  `json:"creator"`
		CreateAt          string  `json:"create_at"`
		Updater           string  `json:"updater"`
		UpdateAt          string  `json:"update_at"`
		TicketType        string  `json:"ticket_type"`
		Status            string  `json:"status"`
		Remark            string  `json:"remark"`
		Group             string  `json:"group"`
		Details           Details `json:"details"`
		TicketTypeDisplay string  `json:"ticket_type_display"`
		StatusDisplay     string  `json:"status_display"`
		CostTime          int     `json:"cost_time"`
		BkBizName         string  `json:"bk_biz_name"`
		BkAppAbbr         string  `json:"bk_app_abbr"`
		IgnoreDuplication bool    `json:"ignore_duplication"`
		BkBizId           int     `json:"bk_biz_id"`
		IsReviewed        bool    `json:"is_reviewed"`
	}

	var resp Data
	c := util.NewClientByHosts(viper.GetString("dbm_ticket_service"))
	result, err := c.Do(http.MethodPost, "tickets/", config)
	if err != nil {
		slog.Error("msg", err)
		return ticketId, err
	}
	if err = json.Unmarshal(result.Data, &resp); err != nil {
		return ticketId, err
	}
	return resp.Id, nil
}

// Domain GetClusterInfo 函数的入参
type Domain struct {
	EntryName string `json:"entry_name" url:"entry_name"`
}

// Instance GetCluster 函数返回的结构体
type Instance struct {
	Proxies      []Proxy   `json:"proxies"`
	Storages     []Storage `json:"storages"`
	SpiderMaster []Proxy   `json:"spider_master"`
	SpiderSlave  []Proxy   `json:"spider_slave"`
	ClusterType  string    `json:"cluster_type"`
	BkBizId      int64     `json:"bk_biz_id"`
	DbModuleId   int64     `json:"db_module_id"`
	BindTo       string    `json:"bind_to"`
	EntryRole    string    `json:"entry_role"`
	BkCloudId    int64     `json:"bk_cloud_id"`
	ImmuteDomain string    `json:"immute_domain"`
}

// Proxy proxy 实例
type Proxy struct {
	IP        string `json:"ip"`
	Port      int    `json:"port"`
	AdminPort int    `json:"admin_port"`
	Status    string `json:"status"`
}

// Storage mysql 后端节点
type Storage struct {
	IP           string `json:"ip"`
	Port         int    `json:"port"`
	InstanceRole string `json:"instance_role"`
	Status       string `json:"status"`
}

// Cluster GetAllClustersInfo 函数返回 Cluster 数组
type Cluster struct {
	DbModuleId   int64     `json:"db_module_id"`
	BkBizId      string    `json:"bk_biz_id"`
	Proxies      []Proxy   `json:"proxies"`
	Storages     []Storage `json:"storages"`
	ClusterType  string    `json:"cluster_type"`
	ImmuteDomain string    `json:"immute_domain"`
}

// BkBizId 业务 id，QueryAccountRule、GetAllClustersInfo 函数的入参
type BkBizId struct {
	BkBizId int64 `json:"bk_biz_id" url:"bk_biz_id"`
}

// GetCluster 根据域名获取集群信息
func GetCluster(dns Domain, ClusterType string) (Instance, error) {
	c := util.NewClientByHosts(viper.GetString("db_meta_service"))
	var resp Instance
	url := fmt.Sprintf("/db_meta/priv_manager/%s/cluster_instances", ClusterType)
	result, err := c.Do(http.MethodGet, url, dns)
	if err != nil {
		slog.Error(url, err)
		return resp, errno.DomainNotExists.Add(fmt.Sprintf(" %s: %s", dns.EntryName, err.Error()))
	}
	if err := json.Unmarshal(result.Data, &resp); err != nil {
		return resp, err
	}
	return resp, nil
}
