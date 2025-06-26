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
  <DbCard
    v-model:collapse="isTaskInfoCardCollapse"
    mode="collapse"
    :title="t('需求信息')">
    <ComFactory :data="data" />
    <InfoList>
      <Item
        :label="t('备注')"
        style="width: 100%">
        <div style="margin-top: 4px; line-height: 24px; white-space: normal">
          {{ data.remark || '--' }}
        </div>
      </Item>
    </InfoList>
  </DbCard>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRoute } from 'vue-router';

  import TicketModel from '@services/model/ticket/ticket';

  import InfoList, { Item } from './com-factory/components/info-list/Index.vue';
  import ComFactory from './com-factory/Index.vue';

  interface Props {
    data: TicketModel;
  }

  defineOptions({
    name: 'TicketTaskInfo',
  });

  defineProps<Props>();

  const { t } = useI18n();
  const route = useRoute();

  const isTaskInfoCardCollapse = ref(true);

  watch(
    route,
    () => {
      isTaskInfoCardCollapse.value = true;
    },
    {
      immediate: true,
    },
  );
</script>
