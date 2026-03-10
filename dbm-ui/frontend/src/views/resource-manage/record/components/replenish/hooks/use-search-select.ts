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
import { computed, onBeforeUnmount } from 'vue';
import { useI18n } from 'vue-i18n';

import { getUserList } from '@services/source/user';

import { type Props } from '@components/db-quick-search/bk-quick-search/Index.vue';
import { DBTypeInfos } from '@common/const';
import { makeMap } from '@utils';

const quickSearchValue = ref<Record<string, any>>({});

export default (options = {} as { exclude: string[] }) => {
  const { t } = useI18n();

  const quickSearchData = computed(() => {
    const serachList: Props['data'] = [
      {
        id: 'id',
        name: 'ID',
        type: 'input',
        validator: (value: string) => {
          return !isNaN(Number(value)) ? true : t('ID 只支持数字');
        },
      },
      {
        id: 'db_type',
        list: Object.values(DBTypeInfos).reduce<Record<'label' | 'value', string>[]>((acc, db) => {
          acc.push({
            label: db.name,
            value: db.id,
          });
          return acc;
        }, []),
        name: t('DB 类型'),
        type: 'multiple',
      },
      {
        id: 'creator',
        name: t('申请人'),
        remoteMethod: (params: { defaultValue?: string; keyword?: string }) => {
          const requestParams = {};
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
        id: 'create_at',
        name: t('申请时间'),
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
    ] as const;

    if (!options.exclude) {
      return serachList;
    }

    const excludeMap = makeMap(options.exclude);
    return serachList.filter((item) => !excludeMap[item.id]);
  });

  onBeforeUnmount(() => {
    quickSearchValue.value = {};
  });

  return {
    quickSearchData,
    quickSearchValue,
  };
};
