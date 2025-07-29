/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
 */
import http from '@services/http';

/**
 * 查询mysql版本升级可用版本列表
 */
export function queryMysqlHigherVersionPkgList(params: {
  cluster_id: number;
  higher_all_version?: boolean; // 单节点本地升级 获取可用的升级包
  higher_major_version?: boolean; // 代表是否跨版本升级, 默认false
}) {
  return http.post<
    {
      pkg_id: number;
      pkg_name: string;
      version: string;
    }[]
  >(`/apis/mysql/toolbox/query_higher_version_pkg_list/`, params);
}

/**
 * 查询spider版本升级可用版本列表
 */
export function querySpiderHigherVersionPkgList(params: {
  cluster_id: number;
  higher_major_version?: boolean; // 返回高于当前集群主版本的包
  higher_sub_version?: boolean; // 返回高于当前集群子版本的包
}) {
  return http.post<
    {
      pkg_id: number;
      pkg_name: string;
      version: string;
    }[]
  >(`/apis/mysql/toolbox/query_spider_higher_version_pkg_list/`, params);
}

/**
 * 获取spider版本模块列表
 */
export function getSpiderVersionModules(params: {
  cluster_id: number;
  higher_major_version?: boolean; // 是否查找更高主版本的模块
  higher_sub_version?: boolean; // 是否查找同大版本但子版本更高的模块
}) {
  return http.post<
    {
      db_module_id: number;
      db_module_name: string;
      spider_version: string;
      module_alias_name: string;
      db_version: string;
      charset: string;
      spider_version_num: number;
      pkg_list: {
        pkg_id: number;
        pkg_name: string;
        major_version: number;
        sub_version: number;
        full_version: number;
      }[];
    }[]
  >(`/apis/mysql/toolbox/get_spider_version_modules/`, params);
}
