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
        <template v-if="modelValue.roleType === 'spider'">
          <CardCheckbox
            v-model="modelValue.updateType"
            :desc="t('适用于小版本升级，如 3.6.1 -> 3.6.3 或 3.6.1 -> 3.7.3')"
            icon="rebuild"
            :title="t('原地升级')"
            :true-value="TicketTypes.TENDBCLUSTER_LOCAL_UPGRADE" />
          <CardCheckbox
            v-model="modelValue.updateType"
            class="ml-8"
            :desc="t('适用于大版本升级，如 spider1.x -> spider3.x')"
            icon="clone"
            :title="t('迁移升级')"
            :true-value="TicketTypes.TENDBCLUSTER_SPIDER_UPGRADE" />
        </template>

        <template v-else>
          <CardCheckbox
            v-model="modelValue.updateType"
            :desc="t('适用于小版本升级，如 5.6.1 ->  5.6.2')"
            icon="rebuild"
            :title="t('原地升级')"
            :true-value="TicketTypes.TENDBCLUSTER_REMOTE_UPGRADE" />
          <CardCheckbox
            v-model="modelValue.updateType"
            class="ml-8"
            :desc="t('适用于大版本升级，如 5.6.0 ->  5.7.0')"
            icon="clone"
            :title="t('迁移升级')"
            :true-value="TicketTypes.TENDBCLUSTER_MIGRATE_UPGRADE" />
        </template>
      </BkFormItem>
      <slot />
    </BkForm>
  </div>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  import { TicketTypes } from '@common/const';

  import CardCheckbox from '@views/db-manage/common/db-card-checkbox/CardCheckbox.vue';

  import { switchSiblingRoute } from '@utils';

  const modelValue = defineModel<{
    roleType: string;
    updateType: string;
  }>({
    required: true,
  });
  const { t } = useI18n();
  const router = useRouter();

  // 当前页面的角色类型，跳转被离开确认取消时还原
  let currentRoleType = modelValue.value.roleType;

  const handleChange = (value: string) => {
    const previousRoleType = currentRoleType;
    currentRoleType = value;
    // 离开确认被取消时选项还原为当前页面
    switchSiblingRoute(
      () =>
        router.push({
          name: value === 'spider' ? TicketTypes.TENDBCLUSTER_LOCAL_UPGRADE : TicketTypes.TENDBCLUSTER_REMOTE_UPGRADE,
        }),
      () => {
        currentRoleType = previousRoleType;
        modelValue.value.roleType = previousRoleType;
      },
    );
  };

  watch(
    () => modelValue.value.updateType,
    (_, oldUpdateType) => {
      // 离开确认被取消时选项还原为当前页面；还原触发的跳转目标是当前页面，不会再拦截
      switchSiblingRoute(
        () =>
          router.push({
            name: modelValue.value.updateType,
          }),
        () => {
          modelValue.value.updateType = oldUpdateType;
        },
      );
    },
  );
</script>
