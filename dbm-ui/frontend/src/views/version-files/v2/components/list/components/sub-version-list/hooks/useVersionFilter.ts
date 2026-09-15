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

import type { Ref } from 'vue';
import type { ComponentProps } from 'vue-component-type-helpers';
import { useI18n } from 'vue-i18n';

import DbVersionModel from '@services/model/version-file/db-version';

import DbQuickSearch from '@components/db-quick-search/Index.vue';
import MultipleSelect from '@components/db-table/components/MultipleSelect.vue';

import { versionStageList } from '@views/version-files/v2/common';

type QuickSearchData = ComponentProps<typeof DbQuickSearch>['data'];

type TableColumnFilter = Record<
  string,
  {
    component?: unknown;
    name: string;
    props?: Record<string, unknown>;
    showConfirmAndReset?: boolean;
    type?: 'multiple' | 'single' | 'input';
  }
>;

/**
 * 版本列表的筛选项。
 * 搜索栏与表头筛选共用同一批字段，字段名同时是搜索栏的 id、表格列的 col-key 以及前端过滤时读取的行属性，
 * 三者必须完全一致，所以集中在这里声明，不要在两边各写一份。
 */
export default function useVersionFilter(dbVersionList?: Ref<DbVersionModel[] | undefined>) {
  const { t } = useI18n();

  const fieldLabelMap = computed(() => ({
    description: t('描述'),
    enable: t('启停'),
    full_version: t('版本号'),
    name: t('版本名'),
    phase: t('版本阶段'),
    updater: t('更新人'),
  }));

  // 筛选值全链路按字符串传递，与行属性比较时两边都会 toString
  const enableOptions = computed(() => [
    {
      label: t('是'),
      value: 'true',
    },
    {
      label: t('否'),
      value: 'false',
    },
  ]);

  // 候选项来自当前发行版下的全量版本，搜索栏与表头筛选共用，不随折叠、筛选变化
  const makeFieldOptions = (field: 'full_version' | 'updater') =>
    computed(() => {
      const valueSet = new Set((dbVersionList?.value || []).map((item) => item[field]).filter(Boolean));
      return Array.from(valueSet).map((item) => ({
        label: item,
        value: item,
      }));
    });

  const fullVersionOptions = makeFieldOptions('full_version');
  const updaterOptions = makeFieldOptions('updater');

  const searchSelectData = computed<QuickSearchData>(() => [
    {
      id: 'name',
      name: fieldLabelMap.value.name,
    },
    {
      id: 'phase',
      list: versionStageList.map((item) => ({
        label: item.label,
        value: item.value,
      })),
      name: fieldLabelMap.value.phase,
      type: 'multiple',
    },
    {
      id: 'full_version',
      list: fullVersionOptions.value,
      name: fieldLabelMap.value.full_version,
      type: 'multiple',
    },
    {
      id: 'enable',
      list: enableOptions.value,
      name: fieldLabelMap.value.enable,
      type: 'multiple',
    },
    {
      id: 'description',
      name: fieldLabelMap.value.description,
    },
    {
      id: 'updater',
      list: updaterOptions.value,
      name: fieldLabelMap.value.updater,
      type: 'multiple',
    },
  ]);

  const tableColumnFilter = computed<TableColumnFilter>(() => ({
    enable: {
      component: markRaw(MultipleSelect),
      name: fieldLabelMap.value.enable,
      props: {
        list: enableOptions.value,
      },
      showConfirmAndReset: true,
      type: 'multiple',
    },
    full_version: {
      component: markRaw(MultipleSelect),
      name: fieldLabelMap.value.full_version,
      props: {
        list: fullVersionOptions.value,
      },
      showConfirmAndReset: true,
      type: 'multiple',
    },
    name: {
      name: fieldLabelMap.value.name,
      showConfirmAndReset: true,
      type: 'input',
    },
    updater: {
      component: markRaw(MultipleSelect),
      name: fieldLabelMap.value.updater,
      props: {
        list: updaterOptions.value,
      },
      showConfirmAndReset: true,
      type: 'multiple',
    },
  }));

  return {
    searchSelectData,
    tableColumnFilter,
  };
}
