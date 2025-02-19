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
  <BkTable :data="data">
    <BkTableColumn
      field="ip"
      :label="t('节点 IP')" />
    <BkTableColumn
      field="alive"
      :label="t('Agent状态')">
      <template #default="{ row }">
        <RenderHostStatus :data="row.alive" />
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="bk_disk"
      :label="t('磁盘_GB')" />
    <BkTableColumn
      v-if="isShowInstanceColumn"
      field="instance_num"
      :label="t('每台主机实例数')" />
  </BkTable>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import RenderHostStatus from '@components/render-host-status/Index.vue';

  interface Props {
    data: {
      alive: number;
      bk_disk: number;
      instance_num?: number;
      ip: string;
    }[];
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const isShowInstanceColumn = props.data.find((item) => item.instance_num !== undefined);
</script>
