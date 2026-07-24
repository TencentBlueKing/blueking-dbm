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
    :all-option-id="STAR"
    :all-option-text="t('全部表（*）')"
    :clearable="!disabled"
    collapse-tags
    :disabled="disabled || multiDbLocked"
    filterable
    :loading="loading"
    :model-value="modelValue"
    multiple
    multiple-mode="tag"
    :no-match-text="t('无匹配项')"
    :placeholder="placeholder"
    :show-all="mode === 'include' && !multiDbLocked"
    show-select-all
    @change="handleChange">
    <template #tag="{ selected }">
      <BkTag
        v-for="item in selected"
        :key="item.value ?? item"
        closable
        @close="() => handleRemoveTag(item.value ?? item)">
        {{ item.value === STAR ? STAR : (item.label ?? item.value ?? item) }}
      </BkTag>
    </template>
    <BkOption
      v-for="name in candidateTables"
      :key="name"
      :label="name"
      :value="name" />
  </BkSelect>
</template>

<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  import { getClusterTablesNameList } from '@services/source/remoteService';

  interface Props {
    clusterId?: number;
    databases?: string[];
    disabled?: boolean;
    mode?: 'include' | 'ignore';
    multiDbLocked?: boolean;
    placeholder?: string;
  }

  const props = withDefaults(defineProps<Props>(), {
    clusterId: undefined,
    databases: () => [],
    disabled: false,
    mode: 'include',
    multiDbLocked: false,
    placeholder: '',
  });

  const modelValue = defineModel<string[]>({ default: () => [] });

  const { t } = useI18n();

  const STAR = '*';

  const loading = ref(false);
  const candidateTables = ref<string[]>([]);

  // 候选表获取：单库取该库表，多库取并集去重排序
  const fetchTables = async () => {
    if (!props.clusterId || props.databases.length === 0) {
      candidateTables.value = [];
      return;
    }
    try {
      loading.value = true;
      const data = await getClusterTablesNameList({
        cluster_db_infos: [
          {
            cluster_id: props.clusterId,
            dbs: props.databases,
          },
        ],
      });
      const clusterData = data.find((item) => item.cluster_id === props.clusterId);
      const tableData = clusterData?.table_data ?? {};
      if (props.databases.length === 1) {
        candidateTables.value = [...(tableData[props.databases[0]] ?? [])];
      } else {
        const set = new Set<string>();
        props.databases.forEach((db) => {
          (tableData[db] ?? []).forEach((table) => set.add(table));
        });
        candidateTables.value = Array.from(set).sort();
      }
    } catch {
      candidateTables.value = [];
    } finally {
      loading.value = false;
    }
  };

  watch(
    () => [props.clusterId, props.databases],
    () => {
      fetchTables();
    },
    { deep: true, immediate: true },
  );

  // 多库锁定时强制 tables = ['*']
  watch(
    () => props.multiDbLocked,
    (locked) => {
      if (locked && props.mode === 'include') {
        if (!(modelValue.value.length === 1 && modelValue.value[0] === STAR)) {
          modelValue.value = [STAR];
        }
      }
    },
    { immediate: true },
  );

  const handleChange = (value: string[]) => {
    // include 模式：选具体表时清空 *；选 * 时清空具体表（BkSelect show-all 已处理）
    if (props.mode === 'include' && !props.multiDbLocked) {
      const hasStar = value.includes(STAR);
      const prevHasStar = modelValue.value.includes(STAR);
      if (hasStar && !prevHasStar) {
        // 刚选了 *，清空其它
        modelValue.value = [STAR];
        return;
      }
      if (hasStar && prevHasStar && value.length > 1) {
        // 已有 * 又选了具体表，移除 *
        modelValue.value = value.filter((v) => v !== STAR);
        return;
      }
    }
    modelValue.value = value;
  };

  const handleRemoveTag = (value: string) => {
    modelValue.value = modelValue.value.filter((v) => v !== value);
  };

  defineExpose({ loading });
</script>
