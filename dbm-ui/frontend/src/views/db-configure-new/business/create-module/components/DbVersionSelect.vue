<!--
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
-->

<template>
  <BkSelect
    v-model="modelValue"
    :clearable="false"
    filterable
    :loading="loading"
    :placeholder="placeholder"
    :prefix="prefix">
    <BkOption
      v-for="(item, index) of versionList"
      :key="item"
      :label="item"
      :value="item">
      <span>{{ item }}</span>
      <BkTag
        v-if="index === 0"
        class="ml-5"
        theme="success">
        {{ t('推荐') }}
      </BkTag>
    </BkOption>
  </BkSelect>
</template>

<script setup lang="ts">
  import { useRequest } from 'vue-request';

  import { getListClusterModuleConfFiles } from '@services/source/configs';
  import { listPackages } from '@services/source/package';

  import { type ClusterTypes, DBTypes } from '@common/const';

  import { t } from '@locales/index';

  export interface ConfTabItem {
    conf_file: string;
    conf_type: string;
    name: string;
  }

  interface Props {
    /** 数据库类型（如 mysql） */
    dbType: DBTypes;
    /** 集群类型（如 tendbha） */
    metaClusterType: ClusterTypes;
    /** 占位文本 */
    placeholder?: string;
    /** 前缀标签 */
    prefix?: string;
    /** 查询 key（用于区分不同版本接口，如 mysql / spider） */
    queryKey?: string;
  }

  defineOptions({
    name: 'DbVersionSelect',
  });

  const props = withDefaults(defineProps<Props>(), {
    placeholder: t('请选择数据库版本'),
    prefix: t('数据库版本'),
    queryKey: '',
  });

  const emit = defineEmits<(e: 'confTabsChange', tabs: ConfTabItem[]) => void>();
  const modelValue = defineModel<string>({
    default: '',
  });

  // 版本列表
  const {
    data: versionList,
    loading,
    run: fetchVersions,
  } = useRequest(listPackages, {
    manual: true,
    onSuccess(data) {
      if (data?.length) {
        modelValue.value = data[0];
      }
    },
  });

  // 配置 Tab 原始数据（仅在版本首次可用时请求一次）
  const rawConfTabs = ref<ConfTabItem[]>([]);
  const { run: fetchConfTabs } = useRequest(getListClusterModuleConfFiles, {
    manual: true,
    onSuccess(data) {
      rawConfTabs.value = data || [];
    },
  });

  /**
   * 最终 confTabs：
   * - conf_type 为 "dbconf" 的项，其 conf_file 和 name 与当前选中的 modelValue 保持一致
   * - 其他类型保持原始 API 返回值不变
   */
  const resolvedConfTabs = computed(() =>
    rawConfTabs.value.map((tab) =>
      tab.conf_type === 'dbconf' ? { ...tab, conf_file: modelValue.value, name: modelValue.value } : tab,
    ),
  );

  // 监听 resolvedConfTabs 变化通知父组件
  watch(
    () => resolvedConfTabs.value,
    (tabs) => {
      if (tabs.length > 0) {
        emit('confTabsChange', tabs);
      }
    },
  );

  // 监听 queryKey 变化获取版本列表
  watch(
    () => props.queryKey || props.dbType,
    () => {
      const key = props.queryKey || (props.dbType as string);
      fetchVersions({
        db_type: props.dbType,
        query_key: key,
      });
    },
    { immediate: true },
  );

  // 仅在版本首次有值时请求一次配置 Tab 列表，后续切换版本不再重新请求
  watch(
    () => modelValue.value,
    (version) => {
      if (version && rawConfTabs.value.length === 0) {
        fetchConfTabs({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          deploy_versions: JSON.stringify({ db_version: version }),
          meta_cluster_type: props.metaClusterType,
        });
      }
    },
  );

  defineExpose({
    confTabs: resolvedConfTabs,
  });
</script>
