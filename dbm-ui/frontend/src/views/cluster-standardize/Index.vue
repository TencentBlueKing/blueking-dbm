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
  <Success v-if="submitted" />
  <template v-else>
    <DbTab
      v-model="active"
      :exclude="exclude" />
    <Component :is="comMap[active]" />
  </template>
</template>

<script setup lang="ts">
  import { DBTypes } from '@common/const';

  import DbTab from '@components/db-tab/Index.vue';

  import Mysql from './components/mysql/Index.vue';
  import Success from './components/Success.vue';
  import Tendbcluster from './components/tendbcluster/Index.vue';

  const router = useRouter();
  const route = useRoute();

  const exclude = Object.values(DBTypes).filter((type) => ![DBTypes.TENDBCLUSTER, DBTypes.MYSQL].includes(type));

  const comMap = {
    [DBTypes.MYSQL]: Mysql,
    [DBTypes.TENDBCLUSTER]: Tendbcluster,
  } as Record<string, any>;

  const active = ref(DBTypes.MYSQL);

  const page = computed(() => (route.params.page as string) || active.value);
  const submitted = computed(() => page.value === 'success');

  watchEffect(() => {
    router.push({
      name: 'PlatformClusterStandardize',
      params: {
        page: page.value,
      },
    });
  });
</script>
