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
    @change="handleChange" />
</template>
<script lang="ts">
  const tagMemo = {} as Record<string, string[]>;
</script>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import TableEditTag from '@components/render-table/columns/db-table-name/Index.vue';

  import { makeMap, random } from '@utils';

  interface Props {
    allowEmpty?: boolean;
    checkDuplicate?: boolean;
  }

  interface Exposes {
    getValue: () => Promise<string[]>;
  }

  const props = withDefaults(defineProps<Props>(), {
    allowEmpty: false,
    checkDuplicate: false,
  });

  const modelValue = defineModel<string[]>({
    default: () => [],
  });

  const { t } = useI18n();

  const instanceKey = random();
  tagMemo[instanceKey] = [];

  const editTagRef = ref<InstanceType<typeof TableEditTag>>();

  const systemDbNames = ['mysql', 'db_infobase', 'information_schema', 'performance_schema', 'sys', 'infodba_schema'];

  const rules = [
    {
      validator: (value: string[]) => {
        if (props.allowEmpty) {
          return true;
        }

        return value && value.length > 0;
      },
      message: t('DB 名不能为空'),
    },
    {
      validator: (value: string[]) => _.every(value, (item) => /^(?!stage_truncate)(?!.*dba_rollback$).*/.test(item)),
      message: t('不能以stage_truncate开头或dba_rollback结尾'),
    },
    {
      validator: (value: string[]) => _.every(value, (item) => /^[-_a-zA-Z0-9*?%]{0,35}$/.test(item)),
      message: t('库表名支持数字、字母、中划线、下划线，最大35字符'),
    },
    {
      validator: (value: string[]) => _.every(value, (item) => !systemDbNames.includes(item)),
      message: t('不允许输入系统库和特殊库'),
    },
    {
      validator: (value: string[]) =>
        !_.some(value, (item) => (/\*/.test(item) && item.length > 1) || (value.length > 1 && item === '*')),
      message: t('* 只能独立使用'),
    },
    {
      validator: (value: string[]) => _.every(value, (item) => !/^[%?]$/.test(item)),
      message: t('% 或 ? 不允许单独使用'),
    },
    {
      validator: (value: string[]) => {
        if (!props.checkDuplicate) {
          return true;
        }

        const otherTagMap = { ...tagMemo };
        delete otherTagMap[instanceKey];

        const nextValueMap = makeMap(value);
        return _.flatten(Object.values(otherTagMap)).every((item) => !nextValueMap[item]);
      },
      message: t('DB名不允许重复'),
    },
  ];

  watch(
    modelValue,
    () => {
      if (props.checkDuplicate) {
        tagMemo[instanceKey] = modelValue.value;
      }
    },
    {
      immediate: true,
    },
  );

  const handleChange = (value: string[]) => {
    modelValue.value = value;
    if (props.checkDuplicate) {
      tagMemo[instanceKey] = value;
    }
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
