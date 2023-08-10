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
  <BkLoading :loading="isLoading">
    <TableEditInput
      ref="inputRef"
      disabled
      :model-value="masterInstance"
      :placeholder="$t('输入集群后自动生成')"
      textarea />
  </BkLoading>
</template>
<script setup lang="ts">
  import {
    ref,
    watch,
  } from 'vue';
  import { useRequest } from 'vue-request';

  import { getDetail } from '@services/spider';

  import TableEditInput from '@views/mysql/common/edit/Input.vue';

  interface Props {
    clusterId: number
  }
  interface Exposes {
    getValue: () => Promise<{
      master: string
    }>
  }

  const props = defineProps<Props>();

  const masterInstance = ref('');

  const {
    loading: isLoading,
    run: fetchClusetrData,
  } = useRequest(getDetail, {
    manual: true,
    onSuccess(data) {
      [masterInstance.value] = data.spider_master[0].instance;
    },
  });

  watch(() => props.clusterId, () => {
    if (props.clusterId) {
      fetchClusetrData({
        id: props.clusterId,
      });
    }
  }, {
    immediate: true,
  });

  defineExpose<Exposes>({
    getValue() {
      return Promise.resolve({
        master: masterInstance.value,
      });
    },
  });
</script>
