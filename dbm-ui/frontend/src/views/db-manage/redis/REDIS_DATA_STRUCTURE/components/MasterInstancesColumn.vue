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
    ref="editableTableColumn"
    :append-rules="rules"
    :disabled-method="() => !cluster.id || isTendisplus"
    field="master_instances"
    :label="t('待构造的实例')"
    required
    :width="300">
    <EditableSelect
      v-model="modelValue"
      :clearable="false"
      collapse-tags
      :list="selectList"
      multiple
      multiple-mode="tag"
      :placeholder="t('请选择实例')"
      show-select-all />
  </EditableColumn>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import RedisModel from '@services/model/redis/redis';

  interface Props {
    cluster: {
      cluster_type: string;
      id: number;
      redis_master: RedisModel['redis_master'];
    };
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<string[]>({
    required: true,
  });

  const { t } = useI18n();

  const rules = [
    {
      message: t('请选择实例'),
      trigger: 'change',
      validator: (arr: string[]) => arr.length > 0,
    },
  ];

  const isTendisplus = computed(() => props.cluster.cluster_type === 'PredixyTendisplusCluster');
  const selectList = computed(() =>
    props.cluster.redis_master.map((item) => ({ label: item.instance, value: item.instance })),
  );

  watch(
    () => props.cluster.redis_master,
    () => {
      if (modelValue.value.length === 0) {
        modelValue.value = props.cluster.redis_master.map((item) => item.instance);
      }
    },
  );
</script>
<style lang="less" scoped>
  .item-input {
    width: 100%;
    height: 40px;
    border: 1px solid transparent;

    :deep(.bk-select-trigger) {
      height: 100%;
      background: transparent;

      .bk-input {
        position: relative;
        height: 100%;
        overflow: hidden;
        background: transparent;
        border: none;
        outline: none;

        input {
          background: transparent;
        }
      }
    }

    &:hover {
      background-color: #fafbfd;
      border-color: #a3c5fd;
    }
  }

  .content {
    position: relative;

    .more-box {
      position: absolute;
      top: 0;
      right: 3px;

      .bk-tag {
        padding: 0 4px;
      }
    }
  }
</style>
