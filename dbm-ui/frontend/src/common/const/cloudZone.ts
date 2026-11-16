/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
 */

/**
 * 可用区 code → 中文名称映射（前端维护）
 * 后端各接口下发的可用区是标识值（如 ap-guangzhou-1），展示时转中文；提交与筛选仍传标识原值
 */
export const cloudZoneNameMap: Record<string, string> = {
  'ap-chongqing-1': '重庆一区',
  'ap-guangzhou-10': '广州十区',
  'ap-guangzhou-11': '广州十一区',
  'ap-guangzhou-3': '广州三区',
  'ap-guangzhou-4': '广州四区',
  'ap-guangzhou-5': '广州五区',
  'ap-guangzhou-6': '广州六区',
  'ap-guangzhou-7': '广州七区',
  'ap-guangzhou-8': '广州八区',
  'ap-guangzhou-9': '广州九区',
  'ap-hongkong-2': '香港二区',
  'ap-nanjing-1': '南京一区',
  'ap-nanjing-2': '南京二区',
  'ap-nanjing-3': '南京三区',
  'ap-nanjing-4': '南京四区',
  'ap-shanghai-2': '上海二区',
  'ap-shanghai-3': '上海三区',
  'ap-shanghai-4': '上海四区',
  'ap-shanghai-5': '上海五区',
  'ap-shanghai-6': '上海六区',
  'ap-shanghai-7': '上海七区',
  'ap-shanghai-8': '上海八区',
  'ap-shanghai-9': '上海九区',
  'ap-shenyang-ec-1': '沈阳一区',
  'ap-shenzhen-1': '深圳一区',
  'ap-shenzhen-2_archived': '深圳二区（已归档）',
  'ap-shenzhen-3': '深圳三区',
  'ap-shenzhen-4': '深圳四区',
  'ap-shenzhen-5': '深圳五区',
  'ap-singapore-1': '新加坡一区',
  'ap-singapore-2': '新加坡二区',
  'ap-singapore-3': '新加坡三区',
  'ap-tianjin-1': '天津一区',
  'ap-tianjin-2': '天津二区',
  'ap-tianjin-3': '天津三区',
  'ap-xian-ec-1': '西安一区',
};

/** 可用区展示名：未登记的标识值回退原值展示 */
export const getCloudZoneName = (zone?: string) => (zone ? cloudZoneNameMap[zone] || zone : '');
