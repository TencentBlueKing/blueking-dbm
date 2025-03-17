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
    :label="t('缩容的IP')"
    :min-width="200">
    <EditableSelect
      v-model="localValue"
      filterable
      :list="ipSelectList"
      multiple
      @change="handleChange">
      <template #option="{ item }">
        <div
          v-bk-tooltips="{
            disabled: !item.disabled,
            content: item.tip,
            placement: 'top',
          }"
          class="option-item">
          <DbStatus :theme="item.status === 'running' ? 'success' : 'danger'" />
          <span class="text-overflow">{{ item.label }}</span>
          <span>{{ item.bk_city ? `(${item.bk_city})` : '' }}</span>
        </div>
      </template>
    </EditableSelect>
  </EditableColumn>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  import MongoDBModel from '@services/model/mongodb/mongodb';

  interface Props {
    rowData: {
      cluster: {
        cluster_spec: MongoDBModel['cluster_spec'];
        mongos: MongoDBModel['mongos'];
      };
    };
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<
    {
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    }[]
  >({
    default: () => [],
    required: true,
  });
  const { t } = useI18n();
  const localValue = ref<string[]>([]);

  const ipSelectList = computed(() => {
    const currentSpec = {
      ...(props.rowData.cluster.mongos?.[0]?.spec_config || {}),
      count: props.rowData.cluster.mongos.length || 0,
    };
    const reduceIpList = props.rowData.cluster.mongos.map((item) => ({
      disabled: false,
      label: item.ip,
      value: item.ip,
      ...item,
    }));
    if (currentSpec.count - localValue.value.length < 3) {
      return reduceIpList.map((item) => {
        Object.assign(item, {
          disabled: !localValue.value.includes(item.value as string),
          tip: t('缩容后不能少于2台'),
        });
        return item;
      });
    }
    return reduceIpList.map((item) => {
      Object.assign(item, {
        disabled: false,
      });
      return item;
    });
  });

  const handleChange = (value: string[]) => {
    modelValue.value = ipSelectList.value
      .filter((item) => value.includes(item.ip))
      .map((item) => ({
        bk_cloud_id: item.bk_cloud_id,
        bk_host_id: item.bk_host_id,
        ip: item.ip,
      }));
    window.changeConfirm = true;
  };

  watch(
    () => modelValue.value,
    () => {
      localValue.value = modelValue.value.map((item) => item.ip);
    },
    {
      immediate: true,
    },
  );
</script>
<style lang="less" scoped>
  .option-item {
    display: flex;
    width: 100%;
    align-items: center;
  }
</style>
