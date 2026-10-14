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
    <template
      v-if="latestRecord"
      #desc>
      <I18nT
        keypath="最近修改_n_c_t"
        scope="global">
        <bk-user-display-name :user-id="latestRecord.operator" />
        <span>{{ latestRecord.modeText }}</span>
        <span>{{ latestRecord.createAtDisplay }}</span>
      </I18nT>
    </template>
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
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRoute } from 'vue-router';

  import type TicketModifyRecordModel from '@services/model/ticket/modify-record';
  import TicketModel from '@services/model/ticket/ticket';

  import InfoList, { Item } from './com-factory/components/info-list/Index.vue';
  import ComFactory from './com-factory/Index.vue';

  interface Props {
    data: TicketModel;
    modifyRecords: TicketModifyRecordModel[];
  }

  defineOptions({
    name: 'TicketTaskInfo',
  });

  const props = defineProps<Props>();

  const { t } = useI18n();
  const route = useRoute();

  const isTaskInfoCardCollapse = ref(true);

  // 只显示最近一次改单，任何状态（含终态）都显示
  const latestRecord = computed(() => _.last(props.modifyRecords));

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
