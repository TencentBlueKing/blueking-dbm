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

import dayjs from 'dayjs';
import { useI18n } from 'vue-i18n';

import { getTicketGroupTypes } from '@services/source/ticket';
import { getUserList } from '@services/source/user';

import { type Props } from '@components/db-quick-search/bk-quick-search/Index.vue';

/**
 * 单据审批设置页搜索选择器配置
 *
 * 仅负责提供 quickSearchData 配置；搜索值的读写与 URL 同步统一由 useFetchData 通过 useUrlSearch 管理，
 * 避免在此处 watch searchValue 自行 router.replace 导致与路由导航冲突。
 */
export const useSearchSelect = () => {
  const { t } = useI18n();

  // 快捷搜索配置（从 List.vue 迁入，保持原字段顺序与表格列对应）
  const quickSearchData: Props['data'] = [
    {
      id: 'ticket_type_display',
      name: t('单据类型'),
      props: {
        checkStrictly: true,
        showAllLevels: true,
      },
      remoteMethod: () =>
        getTicketGroupTypes().then((data) =>
          data.map((item) => ({
            children: item.children.map((child) => ({
              label: child.label,
              value: `ticket_type__in#${child.value}`,
            })),
            label: item.label,
            value: `db_type#${item.value}`,
          })),
        ),
      type: 'multiple-cascader',
    },
    {
      description: t('单个值支持模糊搜索'),
      id: 'immute_domain',
      name: t('集群域名'),
      type: 'multiple-input',
    },
    {
      id: 'need_itsm',
      list: [
        { label: t('需审批'), value: 'true' },
        { label: t('免审批'), value: 'false' },
      ],
      name: t('是否审批'),
      type: 'multiple',
    },
    {
      id: 'updater',
      name: t('更新人'),
      remoteMethod: (params: { defaultValue?: string; keyword?: string }) => {
        const requestParams: Record<string, string> = {};
        if (params.defaultValue) {
          Object.assign(requestParams, { exact_lookups: params.defaultValue });
        }
        if (params.keyword) {
          Object.assign(requestParams, { fuzzy_lookups: params.keyword });
        }
        return getUserList(requestParams).then((data) =>
          data.results.map((item) => ({
            label: `${item.username} (${item.display_name})`,
            value: item.username,
          })),
        );
      },
      remoteSearch: true,
      type: 'multiple',
    },
    {
      id: 'update_at',
      name: t('更新时间'),
      props: {
        shortcuts: [
          {
            text: t('近 1 小时'),
            value: () => [dayjs().subtract(1, 'hour').toDate(), dayjs().toDate()],
          },
          {
            text: t('近 12 小时'),
            value: () => [dayjs().subtract(12, 'hour').toDate(), dayjs().toDate()],
          },
          {
            text: t('今天'),
            value: () => [dayjs().startOf('day').toDate(), dayjs().endOf('day').toDate()],
          },
          {
            text: t('近 7 天'),
            value: () => [dayjs().subtract(6, 'day').startOf('day').toDate(), dayjs().endOf('day').toDate()],
          },
          {
            text: t('近 1 个月'),
            value: () => [dayjs().subtract(1, 'month').startOf('day').toDate(), dayjs().endOf('day').toDate()],
          },
          {
            text: t('近 3 个月'),
            value: () => [dayjs().subtract(3, 'month').startOf('day').toDate(), dayjs().endOf('day').toDate()],
          },
          {
            text: t('近 6 个月'),
            value: () => [dayjs().subtract(6, 'month').startOf('day').toDate(), dayjs().endOf('day').toDate()],
          },
        ],
      },
      type: 'datetime-range',
    },
    {
      description: t('支持模糊搜索'),
      id: 'remark',
      name: t('备注'),
      type: 'input',
    },
  ];

  return {
    quickSearchData,
  };
};
