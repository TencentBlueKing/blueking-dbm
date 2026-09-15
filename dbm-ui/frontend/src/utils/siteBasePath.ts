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

/**
 * 站点根路径，作为 vue-router 的 base
 *
 * BK_SITE_PATH 由后端模板注入，为 / 或 /dbm/ 形式，未注入时（本地开发）占位符原样保留，按根路径处理。
 * 去掉尾斜杠后与 vue-router 内部的 base 取值一致（根路径为空串），可直接与路由 path 拼接
 */
export const siteBasePath =
  window.BK_SITE_PATH && !window.BK_SITE_PATH.includes('{{') ? window.BK_SITE_PATH.replace(/\/+$/, '') : '';
