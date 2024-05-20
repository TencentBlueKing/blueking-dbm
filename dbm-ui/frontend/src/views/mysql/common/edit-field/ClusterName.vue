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
  <TableEditInput
    ref="editRef"
    v-model="localValue"
    :placeholder="t('请输入或选择集群')"
    :rules="rules"
    @submit="handleInputFinish" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { queryClusters } from '@services/source/mysqlCluster';

  import { useGlobalBizs } from '@stores';

  import { batchSplitRegex, domainRegex } from '@common/regex';

  import TableEditInput from '@components/render-table/columns/input/index.vue';

  interface Props {
    data?: string;
  }

  interface Emits {
    (e: 'inputFinish', value: string): void;
  }

  interface Exposes {
    getValue: () => Promise<string>;
  }

  const props = withDefaults(defineProps<Props>(), {
    data: '',
    inputed: () => [],
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

  const localValue = ref(props.data);
  const editRef = ref();

  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('目标集群不能为空'),
    },
    {
      validator: (value: string) => domainRegex.test(value),
      message: t('目标集群输入格式有误'),
    },
    {
      validator: (value: string) => queryClusters({
        cluster_filters: value.split(batchSplitRegex).map(item => ({
          immute_domain: item,
        })),
        bk_biz_id: currentBizId,
      }).then((data) => {
        if (data.length > 0) {
          return true;
        }
        return false;
      }),
      message: t('目标集群不存在'),
    },
  ];

  watch(
    () => props.data,
    (data) => {
      localValue.value = data;
    },
    {
      immediate: true,
    },
  );

  const handleInputFinish = (value: string) => {
    emits('inputFinish', value);
  };

  defineExpose<Exposes>({
    getValue() {
      return editRef.value.getValue().then(() => localValue.value);
    },
  });
</script>
