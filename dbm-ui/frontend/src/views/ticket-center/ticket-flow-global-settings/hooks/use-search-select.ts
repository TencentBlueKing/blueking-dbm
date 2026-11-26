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

import type { Props as QuickSearchProps } from '@components/db-quick-search/bk-quick-search/Index.vue';

// 仅提供搜索项，搜索值与列表刷新由页面管理。
export const useSearchSelect = () => {
  const { t } = useI18n();
  const searchSelectList: QuickSearchProps['data'] = [
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
      id: 'need_itsm',
      list: [
        { label: t('需审批'), value: 'true' },
        { label: t('免审批'), value: 'false' },
        { label: t('逐单判定'), value: 'null' },
      ],
      name: t('审批'),
      type: 'multiple',
    },
    {
      id: 'need_manual_confirm',
      list: [
        { label: t('需确认'), value: 'true' },
        { label: t('免确认'), value: 'false' },
        { label: t('逐单判定'), value: 'null' },
      ],
      name: t('确认执行'),
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
  ];

  return { searchSelectList };
};
