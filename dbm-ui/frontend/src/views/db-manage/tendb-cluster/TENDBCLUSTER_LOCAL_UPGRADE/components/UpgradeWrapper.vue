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
    <BkAlert
      class="mb-20"
      closable
      :title="t('版本升级：小版本可直接升级，跨版本需通过迁移升级，迁修升级需要相应版本的模块')" />
    <BkForm
      class="toolbox-form"
      form-type="vertical"
      :model="modelValue">
      <BkFormItem>
        <BkRadioGroup
          v-model="modelValue.roleType"
          style="width: 450px"
          type="card"
          @change="handleChange">
          <BkRadioButton label="spider">
            {{ t('接入层') }}
          </BkRadioButton>
          <BkRadioButton label="remote">
            {{ t('存储层') }}
          </BkRadioButton>
        </BkRadioGroup>
      </BkFormItem>
      <BkFormItem
        :label="t('升级类型')"
        property="updateType"
        required>
        <CardCheckbox
          v-model="modelValue.updateType"
          :desc="t('适用于小版本升级，如 3.6.1 -> 3.6.3 或 3.6.1 -> 3.7.3')"
          icon="rebuild"
          :title="t('原地升级')"
          :true-value="firstTabValue" />
        <CardCheckbox
          v-model="modelValue.updateType"
          class="ml-8"
          :desc="t('适用于大版本升级，如 spider1.x -> spider3.x')"
          :disabled="modelValue.roleType === 'remote'"
          icon="clone"
          :title="t('迁移升级')"
          :true-value="TicketTypes.TENDBCLUSTER_SPIDER_UPGRADE" />
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

  const firstTabValue = ref(route.meta.ticketType as TicketTypes);

  const modelValue = ref({
    roleType: 'spider',
    updateType: '',
  });

  const handleChange = (value: string) => {
    if (value === 'spider') {
      router.push({
        name: TicketTypes.TENDBCLUSTER_LOCAL_UPGRADE,
      });
    } else {
      router.push({
        name: TicketTypes.TENDBCLUSTER_REMOTE_UPGRADE,
      });
    }
  };

  watch(
    () => modelValue.value.updateType,
    () => {
      router.push({
        name: modelValue.value.updateType,
      });
    },
  );

  onMounted(() => {
    const ticketType = route.meta.ticketType as TicketTypes;
    firstTabValue.value =
      ticketType === TicketTypes.TENDBCLUSTER_REMOTE_UPGRADE
        ? TicketTypes.TENDBCLUSTER_REMOTE_UPGRADE
        : TicketTypes.TENDBCLUSTER_LOCAL_UPGRADE;
    modelValue.value = {
      roleType: ticketType === TicketTypes.TENDBCLUSTER_REMOTE_UPGRADE ? 'remote' : 'spider',
      updateType: ticketType,
    };
  });
</script>
