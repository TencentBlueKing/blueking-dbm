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
  <TableEditTag
    ref="editTagRef"
    :model-value="modelValue"
    :placeholder="t('请输入DB名称_支持通配符_含通配符的仅支持单个')"
    :rules="rules"
    @change="handleChange">
    <template #tip>
      <div>{{ t('不允许输入系统库，如"msdb", "model", "tempdb", "Monitor"') }}</div>
      <div>{{ t('DB名、表名不允许为空，忽略DB名、忽略表名不允许为 *') }}</div>
      <div>{{ t('支持 %（指代任意长度字符串）,*（指代全部）2个通配符') }}</div>
      <div>{{ t('单元格可同时输入多个对象，使用换行，空格或；，｜分隔，按 Enter 或失焦完成内容输入') }}</div>
      <div>{{ t('包含通配符时, 每一单元格只允许输入单个对象。% 不能独立使用， * 只能单独使用') }}</div>
    </template>
  </TableEditTag>
</template>
<script lang="ts">
  const tagMemo = {} as Record<string, string[]>;
</script>
<script setup lang="ts">
  import _ from 'lodash';
  import { onBeforeUnmount, ref, watch } from 'vue';
  import { useI18n } from 'vue-i18n';

  import TableEditTag from '@components/render-table/columns/tag-input/index.vue';

  import { makeMap, random } from '@utils';

  interface Exposes {
    getValue: () => Promise<string[]>;
  }

  const { t } = useI18n();

  const instanceKey = random();
  tagMemo[instanceKey] = [];

  const modelValue = defineModel<string[]>({
    default: () => [],
  });

  const disabledTagMap = {
    monitor: true,
    model: true,
    msdb: true,
    tempdb: true,
  };
  const rules = [
    {
      validator: (value: string[]) => {
        tagMemo[instanceKey] = value;
        return value && value.length > 0;
      },
      message: t('DB名不能为空'),
    },
    {
      validator: (value: string[]) => !(value.includes('master') && value.length > 1),
      message: t('有 master 时只允许一个'),
    },
    {
      validator: (value: string[]) => _.every(value, (item) => !disabledTagMap[item as keyof typeof disabledTagMap]),
      message: t(`DB名不能支持 n`, { n: Object.keys(disabledTagMap).join(',') }),
    },
    {
      validator: (value: string[]) => !_.some(value, (item) => /\*/.test(item) && item.length > 1),
      message: t('* 只能独立使用'),
    },
    {
      validator: (value: string[]) => _.every(value, (item) => !/^%$/.test(item)),
      message: t('% 不允许单独使用'),
    },
    {
      validator: (value: string[]) => {
        if (_.some(value, (item) => /[*%?]/.test(item))) {
          return value.length < 2;
        }
        return true;
      },
      message: t('含通配符的单元格仅支持输入单个对象'),
    },
    {
      validator: (value: string[]) => {
        const otherTagMap = { ...tagMemo };
        delete otherTagMap[instanceKey];

        const nextValueMap = makeMap(value);
        return _.flatten(Object.values(otherTagMap)).every((item) => !nextValueMap[item]);
      },
      message: t('DB名不允许重复'),
    },
  ];

  const editTagRef = ref<InstanceType<typeof TableEditTag>>();

  watch(
    modelValue,
    () => {
      tagMemo[instanceKey] = modelValue.value;
    },
    {
      immediate: true,
    },
  );

  const handleChange = (value: string[]) => {
    modelValue.value = value;
    tagMemo[instanceKey] = value;
  };

  onBeforeUnmount(() => {
    delete tagMemo[instanceKey];
  });

  defineExpose<Exposes>({
    getValue() {
      return editTagRef.value!.getValue().then(() => modelValue.value);
    },
  });
</script>
