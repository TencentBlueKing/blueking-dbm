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
  <EditInfo
    class="pt-20"
    :columns="columns"
    :data="data" />
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { ResourceRedisItem } from '@services/types/clusters';

  import EditInfo, {
    type InfoColumn,
  } from '@components/editable-info/index.vue';

  interface Props {
    data: ResourceRedisItem
  }

  defineProps<Props>();

  const { t } = useI18n();

  const columns:InfoColumn[][] = [
    [{
      label: t('集群名称'),
      key: 'cluster_name',
    }, {
      label: t('集群别名'),
      key: 'cluster_alias',
    }, {
      label: t('域名'),
      key: 'master_domain',
    }],
    [{
      label: t('架构版本'),
      key: 'cluster_type_name',
    }, {
      label: t('数据库版本'),
      key: 'major_version',
    }, {
      label: t('地域'),
      key: 'region',
    }, {
      label: t('创建人'),
      key: 'creator',
    }, {
      label: t('创建时间'),
      key: 'create_at',
    }],
  ];
</script>
