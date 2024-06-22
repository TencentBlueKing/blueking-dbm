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
  <div>
    <TableEditInput
      ref="editRef"
      v-model="modelValue"
      :placeholder="t('支持使用 { } 占位，如db_{id} , id在执行开区时传入', { x: '{ }', y: '{id}' })"
      :rules="rules" />
    <!-- <BkSelect
      ref="selectRef"
      v-model="selectedValue"
      filterable
      @select="handleSelect">
    <template #trigger>
      <span></span>
    </template>
      <BkOption
        v-for="(item, index) in dataList"
        :id="item.value"
        :key="index"
        :name="item.label"/>
    </BkSelect> -->
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TableEditInput from '@views/spider-manage/common/edit/Input.vue';

  interface Props {
    dbName?: string;
  }

  interface Exposes {
    getValue: () => Promise<{
      target_db_pattern: string;
    }>;
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<string>({
    default: '',
  });

  const { t } = useI18n();

  const editRef = ref<InstanceType<typeof TableEditInput>>();
  // const selectRef = ref();
  // const selectedValue = ref('')

  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('不能为空'),
    },
    {
      validator: (value: string) => {
        const matches = value.match(/{(.*?)}/g);
        if (matches) {
          const extractedStrings = matches.map((match) => match.slice(1, -1));
          return extractedStrings.every((word) => /^[A-Za-z].*?$/.test(word));
        }
        return true;
      },
      message: t('变量只能以字母开头'),
    },
  ];

  // const dataList = [
  //   {
  //     value: 'APP',
  //     label: 'APP',
  //   }
  // ];

  // watch(modelValue, () => {
  //   if (/{$/.test(modelValue.value)) {
  //     selectRef.value.showPopover();
  //   }
  // })

  // const handleSelect = (value: string) => {
  //   modelValue.value = `${modelValue.value}${value}}`;
  // }

  watch(
    () => props.dbName,
    () => {
      if (props.dbName) {
        modelValue.value = `${props.dbName}_{ID}`;
      }
    },
  );

  defineExpose<Exposes>({
    getValue() {
      return editRef.value!.getValue().then(() => ({
        target_db_pattern: modelValue.value,
      }));
    },
  });
</script>
