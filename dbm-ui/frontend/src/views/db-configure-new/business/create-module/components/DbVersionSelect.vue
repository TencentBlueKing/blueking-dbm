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
    :prefix="prefix"
    @change="(val: string | number) => emit('change', val)">
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

  import { listPackages } from '@services/source/package';

  import { DBTypes } from '@common/const';

  import { t } from '@locales/index';

  interface Props {
    /** 数据库类型（如 mysql） */
    dbType: DBTypes;
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
    prefix: t('存储层版本'),
    queryKey: '',
  });

  const emit = defineEmits<(e: 'change', val: string | number) => void>();

  const modelValue = defineModel<string>({
    default: '',
  });

  const {
    data: versionList,
    loading,
    run: fetchVersions,
  } = useRequest(listPackages, {
    manual: true,
    onSuccess(data) {
      [modelValue.value] = data;
    },
  });

  // 监听 queryKey 变化获取版本列表
  watch(
    () => props.queryKey || props.dbType,
    () => {
      fetchVersions({
        db_type: props.dbType,
        query_key: props.queryKey || props.dbType,
      });
    },
    { immediate: true },
  );
</script>
