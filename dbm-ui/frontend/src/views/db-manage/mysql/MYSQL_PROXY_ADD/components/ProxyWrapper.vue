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
            :desc-list="[
              t('功能说明：为集群增加Proxy，新增Proxy沿用当前规格，关联集群将强制执行'),
              t('应用场景：集群负载升高需扩容、提升高可用能力时使用'),
            ]"
            icon="bk-dbm-icon db-icon-plus-fill"
            :title="t('添加 Proxy')"
            :true-value="TicketTypes.MYSQL_PROXY_ADD" />
          <CardCheckbox
            v-model="modelValue.ticketType"
            class="mb-8 ml-8"
            :desc-list="[
              t('功能说明：下架指定Proxy主机（主机上所有实例同步下架），实现集群缩容'),
              t('应用场景：集群负载降低、需削减资源成本时使用'),
            ]"
            icon="bk-dbm-icon db-icon-minus-fill"
            :title="t('减少 Proxy')"
            :true-value="TicketTypes.MYSQL_PROXY_REDUCE" />
          <CardCheckbox
            v-model="modelValue.ticketType"
            class="mb-8"
            :desc-list="[
              t('功能说明：对集群内所有Proxy统一执行升配/降配，关联集群将强制执行'),
              t('应用场景：Proxy性能不足需升配，或资源过剩需降配时使用'),
            ]"
            icon="bk-dbm-icon db-icon-shengji"
            :title="t('Proxy 升降配')"
            :true-value="TicketTypes.MYSQL_PROXY_CONF_CHANGE" />
          <CardCheckbox
            v-model="modelValue.ticketType"
            class="mb-8 ml-8"
            :desc-list="[
              t('功能说明：将目标Proxy主机替换为同规格新主机，原主机实例自动迁移'),
              t('应用场景：旧主机裁撤、硬件故障处理时使用'),
            ]"
            icon="bk-dbm-icon db-icon-kelong"
            :title="t('替换 Proxy')"
            :true-value="TicketTypes.MYSQL_PROXY_SWITCH" />
          <CardCheckbox
            v-model="modelValue.ticketType"
            :desc-list="[
              t('功能说明：将集群所有Proxy迁移至新主机组实现拆分'),
              t('应用场景：仅适用于“多实例共享主机”场景拆分Proxy实例，可减少资源竞争'),
            ]"
            icon="bk-dbm-icon db-icon-migration"
            :title="t('迁移 Proxy')"
            :true-value="TicketTypes.MYSQL_PROXY_MIGRATE" />
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
    ticketType: (route.meta.ticketType as TicketTypes) || TicketTypes.MYSQL_PROXY_ADD,
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
