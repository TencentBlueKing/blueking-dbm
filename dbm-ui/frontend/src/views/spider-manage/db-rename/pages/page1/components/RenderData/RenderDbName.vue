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
  <div
    ref="rootRef"
    class="render-db-name">
    <TableEditInput
      ref="inputRef"
      v-model="localValue"
      :disabled="!clusterId"
      :placeholder="placeholder"
      :rules="rules" />
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { checkClusterDatabase } from '@services/remoteService';

  import TableEditInput from '@components/tools-table-input/index.vue';

  interface Props {
    clusterId: number,
    modelValue?: string,
    placeholder?: string,
    checkExist?: boolean
  }

  interface Exposes {
    getValue: (field: string) => Promise<Record<string, string[]>>
  }

  const props = withDefaults(defineProps<Props>(), {
    placeholder: '',
    modelValue: '',
    checkExist: false,
  });

  const { t } = useI18n();
  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('DB名不能为空'),
    },
    {
      validator: (value: string) => !value.startsWith('stage_truncate'),
      message: t('不可以stage_truncate开头'),
    },
    {
      validator: (value: string) => !value.endsWith('dba_rollback'),
      message: t('不可以dba_rollback结尾'),
    },
    {
      validator: (value: string) => /^[a-zA-z][a-zA-Z0-9_-]{1,39}$/.test(value),
      message: t('由字母_数字_下划线_减号_字符组成以字母开头'),
    },
    {
      validator: (value: string) => {
        if (!props.checkExist) {
          return true;
        }
        return checkClusterDatabase({
          infos: [
            {
              cluster_id: props.clusterId,
              db_names: [value],
            },
          ],
        }).then(data => (data.length > 0 ? data[0].check_info[value] : false));
      },
      message: t('DB 不存在'),
    },
  ];

  const rootRef = ref();
  const inputRef = ref();
  const localValue = ref(props.modelValue);

  // 集群改变时 DB 需要重置
  watch(() => props.clusterId, () => {
    localValue.value = '';
  });

  watch(() => props.modelValue, () => {
    if (props.modelValue) {
      localValue.value = props.modelValue;
    } else {
      localValue.value = '';
    }
  }, {
    immediate: true,
  });

  defineExpose<Exposes>({
    getValue(field: string) {
      return inputRef.value.getValue()
        .then(() => ({
          [field]: localValue.value,
        }));
    },
  });
</script>
<style lang="less">
  .render-db-name {
    display: block;
  }
</style>
