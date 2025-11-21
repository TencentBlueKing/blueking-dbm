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
  <div class="db-toolbox">
    <BkForm
      class="toolbox-form mb-20"
      form-type="vertical"
      :model="modelValue">
      <BkFormItem
        :label="t('变更方式')"
        property="ticketType"
        required>
        <div class="card-checkbox-block">
          <CardCheckbox
            v-model="modelValue.ticketType"
            class="mb-8"
            :desc-list="[t('功能说明：将集群从当前主机迁移至新主机'), t('应用场景：用于“多实例共享主机”场景下的拆分')]"
            icon="bk-dbm-icon db-icon-plus-fill"
            :title="t('集群迁移')"
            :true-value="TicketTypes.SQLSERVER_CLUSTER_MIGRATE" />
          <CardCheckbox
            v-model="modelValue.ticketType"
            class="mb-8 ml-8"
            :desc-list="[
              t('功能说明：将主机上的所有集群整体迁移到新机器，新机器可以更换规格'),
              t('应用场景：用于裁撤主机迁移，待裁撤主机需处于正常状态'),
            ]"
            icon="bk-dbm-icon db-icon-minus-fill"
            :title="t('整机迁移')"
            :true-value="TicketTypes.SQLSERVER_HOST_MIGRATE" />
        </div>
      </BkFormItem>
      <slot />
    </BkForm>
  </div>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  import { TicketTypes } from '@common/const';

  import CardCheckbox from '@components/db-card-checkbox/CardCheckbox.vue';

  const { t } = useI18n();
  const router = useRouter();
  const route = useRoute();

  const modelValue = ref({
    ticketType: (route.meta.ticketType as TicketTypes) || TicketTypes.SQLSERVER_CLUSTER_MIGRATE,
  });

  watch(
    () => modelValue.value.ticketType,
    () => {
      router.push({
        name: modelValue.value.ticketType,
      });
    },
  );
</script>
<style lang="less" scoped>
  .card-checkbox-block {
    display: grid;
    grid-template-columns: 1fr 1fr;
  }
</style>
