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
  <TableTagInput
    ref="tagRef"
    :model-value="modelValue"
    :placeholder="t('请输入DB名称_支持通配符_含通配符的仅支持单个')"
    :rules="rules"
    @change="handleChange" />
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { checkSqlserverDbExist } from '@services/source/sqlserver'

  import TableTagInput from '@components/render-table/columns/tag-input/index.vue';

  import TableEditTag from '@views/mysql/common/edit/Tag.vue';

  interface Props {
    clusterId: number;
    modelValue?: string[];
    required?: boolean;
  }

  interface Emits {
    (e: 'change', value: string[]): void;
  }

  interface Exposes {
    getValue: () => Promise<string[]>;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  let noExitsDbList = [] as string[]

  const rules = [
    {
      validator: (value: string[]) => {
        const hasAllMatch = _.find(value, (item) => /%$/.test(item));
        return !(value.length > 1 && hasAllMatch);
      },
      message: t('一格仅支持单个_对象'),
    },
    {
      validator: (value: string[]) => {
        if (value.length > 0) {
          return props.clusterId > 0
        }
        return true
      },
      message: t('请先输入或选择集群'),
    },
    {
      validator: (value: string[]) => checkSqlserverDbExist({
        cluster_id: props.clusterId,
        db_list: value
      }).then((data) => {
        noExitsDbList = Object.entries(data).reduce((prevDbList, [dbName, isExists]) => {
          if (!isExists) {
            return [...prevDbList, dbName]
          }
          return prevDbList
        }, [] as string[])
        return noExitsDbList.length === 0
      }),
      message: () => t('目标DB不存在', [noExitsDbList.join('，')]),
    },
  ];

  if (props.required) {
    rules.unshift(
      {
        validator: (value: string[]) => value.length > 0,
        message: t('DB名不能为空'),
      }
    )
  }

  const tagRef = ref<InstanceType<typeof TableEditTag>>();
  const localValue = ref(props.modelValue || []);

  // 集群改变时 DB 需要重置
  watch(
    () => props.clusterId,
    () => {
      localValue.value = [];
    },
  );

  watch(
    () => props.modelValue,
    () => {
      if (props.modelValue) {
        localValue.value = props.modelValue;
      } else {
        localValue.value = [];
      }
    },
    {
      immediate: true,
    },
  );

  const handleChange = (value: string[]) => {
    localValue.value = value;
    emits('change', value);
  };

  defineExpose<Exposes>({
    getValue() {
      return tagRef.value!.getValue().then(() => localValue.value);
    },
  });
</script>

<style lang="less">
  .render-db-name {
    display: block;
  }
</style>
