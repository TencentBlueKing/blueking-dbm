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
  <StretchLayout
    v-if="!isPreChecking"
    :left-width="400"
    :min-left-width="300"
    name="ticketList"
    style="background: #fff"
    @change="handleStretchLayoutChange">
    <template #list>
      <List />
    </template>
    <template
      v-if="ticketId"
      #right>
      <Detail :ticket-id="ticketId" />
    </template>
  </StretchLayout>
</template>
<script setup lang="ts">
  import { computed } from 'vue';
  import { useRoute, useRouter } from 'vue-router';

  import { useUrlSearch } from '@hooks';

  import StretchLayout from '@components/stretch-layout/StretchLayout.vue';

  import useDetailPreCheck from '@views/ticket-center/common/hooks/use-detail-precheck';
  import Detail from '@views/ticket-center/common/ticket-detail/Index.vue';

  import List from './components/list/Index.vue';

  const router = useRouter();
  const route = useRoute();
  const { getSearchParams } = useUrlSearch();

  // params.ticketId 会运行中改变，需要要响应变化
  const ticketId = computed(() => Number(route.params.ticketId) || 0);

  const isPreChecking = useDetailPreCheck({
    id: ticketId.value,
  });

  const handleStretchLayoutChange = (value: boolean) => {
    if (!value) {
      router.replace({
        params: {
          ticketId: '',
        },
        query: {
          ...getSearchParams(),
          selectId: route.params.ticketId,
        },
      });
    }
  };
</script>
