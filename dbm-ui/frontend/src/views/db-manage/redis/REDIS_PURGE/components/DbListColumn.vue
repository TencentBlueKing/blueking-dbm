<!--
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
-->

<template>
  <EditableColumn
    ref="editableColumn"
    :append-rules="rules"
    field="dbList"
    :label="t('清档范围')"
    :loading="isFetching"
    required
    :width="200">
    <EditableSelect
      v-model="selectValue"
      :all-option-id="ALL_DB"
      :all-option-text="t('全部')"
      :clearable="false"
      :list="selectList"
      :loading="isFetching"
      multiple
      :multiple-mode="selectValue.length === 0 || selectValue.find((item) => item === ALL_DB) ? 'default' : 'tag'"
      show-all />
  </EditableColumn>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { getRedisClusterDbs } from '@services/source/redis';

  import { ClusterTypes } from '@common/const';

  interface Props {
    cluster: {
      cluster_type: string;
      id: number;
    };
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<number[]>({
    required: true,
  });

  const { t } = useI18n();

  // 「全部」对应的占位值，与具体 DB 号互斥（利用 DbSelect 的 showAll 行为）
  const ALL_DB = 'all';

  const dbs = ref<number[]>([]);
  const isDbsLoaded = ref(false);
  const isFetching = ref(false);

  const isMasterSlave = computed(() => props.cluster.cluster_type === ClusterTypes.REDIS_INSTANCE);

  // 行内下拉：「全部」由 showAll 提供，list 只放可选 DB 号；值为字符串以兼容占位值 all
  const selectList = computed(() => dbs.value.map((db) => ({ label: `DB${db}`, value: String(db) })));

  // 行数据 dbList 为空数组即「全部」，与提交契约 db_list: [] 一致
  const selectValue = computed<string[]>({
    get: () => (modelValue.value.length ? modelValue.value.map(String) : [ALL_DB]),
    set: (value) => {
      modelValue.value = [...new Set(value.filter((item) => item !== ALL_DB).map(Number))];
    },
  });

  const rules = [
    {
      message: '',
      required: true,
      trigger: 'change',
      validator: () => {
        return true;
      },
    },
    {
      message: t('当前架构仅支持清空全部数据'),
      trigger: 'change',
      validator: (value: number[]) => {
        if (!value.length || !props.cluster.id || isMasterSlave.value) {
          return true;
        }
        return false;
      },
    },
  ];

  // 批量录入 / 回填写入的 DB 号可能早于（或晚于）databases 加载，这里持续兜底滤除超出可选范围的号
  watch(
    [isDbsLoaded, () => [...modelValue.value]],
    () => {
      if (!isDbsLoaded.value) {
        return;
      }
      const filtered = modelValue.value.filter((db) => dbs.value.includes(db));
      if (filtered.length !== modelValue.value.length) {
        modelValue.value = filtered;
      }
    },
    { immediate: true },
  );

  const fetchDbs = () => {
    const clusterId = props.cluster.id;
    if (!clusterId) {
      return;
    }
    // 非主从架构不支持指定 DB，直接清掉已写入的号
    if (!isMasterSlave.value) {
      isDbsLoaded.value = false;
      dbs.value = [];
      if (modelValue.value.length) {
        modelValue.value = [];
      }
      return;
    }
    isFetching.value = true;
    getRedisClusterDbs({ cluster_id: clusterId })
      .then((data) => {
        // 响应到达时集群可能已被切换，只写入仍归属当前集群的结果
        if (props.cluster.id === clusterId) {
          dbs.value = data.dbs;
          isDbsLoaded.value = true;
          // 批量录入 / 回填写入的 DB 号超出可选范围时直接去除
          modelValue.value = modelValue.value.filter((db) => data.dbs.includes(db));
        }
      })
      .finally(() => {
        isFetching.value = false;
      });
  };

  watch(() => [props.cluster.id, props.cluster.cluster_type], fetchDbs, {
    immediate: true,
  });
</script>
