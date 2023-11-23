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

import type { MainViewRouteNameValues } from '@views/main-views/common/const';

import 'vue-router';

export interface RouteMeteTag {
  theme: string
  text: string
}
declare module 'vue-router' {
  interface RouteMeta {
    routeParentName?: MainViewRouteNameValues | string, // 父级路由名称
    submenuId?: string // 用于判断 bk-menu submenu 激活状态
    activeMenu?: string // 用于判断子路由的 bk-menu 激动状态
    navName?: string // 用于设置面包屑 name
    isMenu?: boolean // 判断是否为 bk-menu 导航，若是则不现实返回按钮
    tags?: Tag[] // 用于设置面包屑 tags
    showBack?: boolean // 用于判断是否显示面包屑返回按钮
    fullScreen?: boolean // 用于判断是否满屏幕
    group?: string // 用于设置顶部导航分组
    skeleton?: string
  }
}

export {};

