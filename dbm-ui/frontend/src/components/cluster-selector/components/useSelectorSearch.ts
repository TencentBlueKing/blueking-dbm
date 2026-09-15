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
import _ from 'lodash';
import { useI18n } from 'vue-i18n';

import { queryBizClusterAttrs } from '@services/source/dbbase';
import { listTag } from '@services/source/tag';

import { useGlobalBizs } from '@stores';

import { type Props as QuickSearchProps } from '@components/db-quick-search/bk-quick-search/Index.vue';

/**
 * 集群/实例选择器搜索：维护 DbQuickSearch 的搜索值、搜索条件与远程候选项
 *
 * @param attrs queryBizClusterAttrs 要拉的候选项字段，同时决定搜索栏显示哪些条件
 * @param customSelectList 调用方自定义的搜索条件，给了就整组替换标准条件，「标签」仍然保留
 */
export const useSelectorSearch = (
  clusterType: string,
  attrs: string[],
  customSelectList?: QuickSearchProps['data'],
) => {
  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();

  const searchValue = ref<Record<string, string>>({});
  const columnAttrs = ref<Record<string, { text: string; value: string }[]>>({});

  queryBizClusterAttrs({
    bk_biz_id: currentBizId,
    cluster_attrs: attrs.join(','),
    cluster_type: clusterType,
  }).then((result) => {
    columnAttrs.value = result;
  });

  // 候选项接口返回前取到空数组，条件本身按 attrs 同步决定，不等接口
  const getAttrOptions = (field: string) =>
    (columnAttrs.value[field] || []).map((item) => ({
      label: item.text,
      value: item.value,
    }));

  /**
   * 显示哪些条件由 attrs 决定：attrs 同时决定拉哪些候选项，同源才不会出现
   * 「候选项拉了但搜索栏没有对应条件」。
   *
   * 列筛选的字段必须在这里有同名条件：两者共用 searchValue，而 DbQuickSearch 回显时
   * 只按自己的条件列表重建值，没声明的字段会被静默丢掉，表现为列筛选点了没反应。
   * region / time_zone 两个 attr 既没有搜索条件也没有列，只是拉了没用
   */
  const getBaseSelectList = () =>
    _.filter(
      [
        {
          id: 'domain',
          name: t('访问入口'),
          type: 'multiple-input',
        },
        {
          id: 'instance',
          name: t('IP 或 IP:Port'),
          type: 'multiple-input',
        },
        {
          id: 'status',
          list: [
            {
              label: t('正常'),
              value: 'normal',
            },
            {
              label: t('异常'),
              value: 'abnormal',
            },
          ],
          name: t('状态'),
          type: 'multiple',
        },
        attrs.includes('db_module_id') && {
          id: 'db_module_id',
          list: getAttrOptions('db_module_id'),
          name: t('所属模块'),
          type: 'multiple',
        },
        attrs.includes('cluster_type') && {
          id: 'cluster_type',
          list: getAttrOptions('cluster_type'),
          name: t('架构版本'),
          type: 'multiple',
        },
        {
          id: 'name',
          name: t('集群名称'),
          type: 'multiple-input',
        },
        attrs.includes('bk_cloud_id') && {
          id: 'bk_cloud_id',
          list: getAttrOptions('bk_cloud_id'),
          name: t('管控区域'),
          type: 'multiple',
        },
        attrs.includes('major_version') && {
          id: 'major_version',
          list: getAttrOptions('major_version'),
          name: t('版本'),
          type: 'multiple',
        },
      ],
      (item) => item,
    ) as QuickSearchProps['data'];

  const searchSelectData = computed(
    () =>
      [
        ...(customSelectList ?? getBaseSelectList()),
        {
          id: 'tag',
          name: t('标签'),
          props: {
            checkStrictly: true,
            showAllLevels: true,
          },
          remoteMethod: () =>
            listTag(
              {
                bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
                limit: -1,
                offset: 0,
                type: 'cluster',
              },
              {
                cache: true,
              },
            ).then((data) => {
              const keyValueMap: Record<string, { label: string; value: string }[]> = {};
              data.results.forEach((item) => {
                if (!keyValueMap[item.key]) {
                  keyValueMap[item.key] = [];
                }
                keyValueMap[item.key].push({
                  label: item.value,
                  value: `tag_ids#${item.id}`,
                });
              });

              return Object.keys(keyValueMap).map((tagKey) => ({
                children: keyValueMap[tagKey],
                label: tagKey,
                value: `tag_keys#${tagKey}`,
              }));
            }),
          type: 'multiple-cascader',
        },
      ] as QuickSearchProps['data'],
  );

  return {
    columnAttrs,
    searchSelectData,
    searchValue,
  };
};
