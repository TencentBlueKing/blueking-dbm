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
import type MysqlMergeDiskSpaceModel from '@services/model/mysql/mysql-merge-disk-space';

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
      charset: string;
      db_module_id: number;
      db_module_name: string;
      db_version: string;
      module_alias_name: string;
      pkg_list: {
        full_version: number;
        major_version: number;
        pkg_id: number;
        pkg_name: string;
        sub_version: number;
      }[];
      spider_version: string;
      spider_version_num: number;
    }[]
  >(`/apis/mysql/toolbox/get_spider_version_modules/`, params);
}

/**
 * 获取mysql、tendbcluster存储层版本模块列表
 *  
  tendbsingle
  本地升级：
    "higher_major_version": true,
    "higher_sub_version": true

  tendbha、tendbcluster
  本地升级：
    "higher_major_version": false,
    "higher_sub_version": true

  迁移升级：
    "higher_major_version": true,
    "higher_sub_version": true
 */
export function getVersionModules(params: {
  cluster_id: number;
  higher_major_version?: boolean; // 是否查找更高主版本的模块
  higher_sub_version?: boolean; // 是否查找同大版本但子版本更高的模块
}) {
  return http.post<
    {
      charset: string;
      db_module_id: number;
      db_module_name: string;
      db_version: string;
      pkg_list: {
        pkg_id: number;
        pkg_name: string;
      }[];
    }[]
  >(`/apis/mysql/toolbox/get_storage_version_modules/`, params);
}

/**
 * 合并磁盘空间评估
 */
export const mergeDiskSpace = (params: {
  bk_biz_id: number;
  factor: number; // DB数据克隆单据调用factor=1，DB数据合并空间评估调用factor=2
  migrations: {
    clone_db_list?: string[];
    data_schema_grant?: string;
    db_list: string[];
    ignore_db_list?: string[];
    source_cluster: number;
    target_clusters: number[];
  }[];
}) => http.post<MysqlMergeDiskSpaceModel[]>('/apis/mysql/toolbox/mysql_disk_space/', params);
