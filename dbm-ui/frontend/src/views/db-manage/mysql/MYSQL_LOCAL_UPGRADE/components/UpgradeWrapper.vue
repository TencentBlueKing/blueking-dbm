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
  <div class="mysql-version-upgrade-page">
    <BkAlert
      class="mb-20"
      closable
      :title="
        t(
          '版本升级：主从接入层和单节点采用原地升级，存储层小版本升级采用原地升级（注意：暂不支持一主多从），大版本需提供新机迁移方式执行。同一主机所有关联集群将一并同步升级',
        )
      " />
    <BkForm
      class="upgrade-form"
      form-type="vertical"
      :model="modelValue">
      <BkFormItem
        :label="t('角色类型')"
        property="roleType"
        required>
        <BkRadioGroup
          v-model="modelValue.roleType"
          style="width: 450px"
          type="card"
          @change="handleChange">
          <BkRadioButton :label="TicketTypes.MYSQL_PROXY_UPGRADE">
            {{ t('主从 - 接入层') }}
          </BkRadioButton>
          <BkRadioButton label="haStorageLayer">
            {{ t('主从 - 存储层') }}
          </BkRadioButton>
          <BkRadioButton label="singleStorageLayer">
            {{ t('单节点') }}
          </BkRadioButton>
        </BkRadioGroup>
      </BkFormItem>
      <BkFormItem
        v-if="modelValue.roleType !== TicketTypes.MYSQL_PROXY_UPGRADE"
        :label="t('升级类型')"
        property="updateType"
        required>
        <CardCheckbox
          v-model="modelValue.updateType"
          :desc="t('适用于小版本升级，如 5.6.1 ->  5.6.2 ')"
          icon="rebuild"
          :title="t('原地升级')"
          :true-value="TicketTypes.MYSQL_LOCAL_UPGRADE" />
        <CardCheckbox
          v-model="modelValue.updateType"
          class="ml-8"
          :desc="t('适用于大版本升级，如 5.6.0 ->  5.7.0')"
          :disabled="modelValue.roleType === 'singleStorageLayer'"
          :disabled-tooltips="t('单节点仅支持原地升级')"
          icon="clone"
          :title="t('迁移升级')"
          :true-value="TicketTypes.MYSQL_MIGRATE_UPGRADE" />
      </BkFormItem>
      <slot />
    </BkForm>
  </div>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  import { TicketTypes } from '@common/const';

  import CardCheckbox from '@components/db-card-checkbox/CardCheckbox.vue';

  type Emits = (e: 'change', data: typeof modelValue.value) => void;

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<{
    roleType: string;
    updateType?: string;
  }>({
    required: true,
  });

  const { t } = useI18n();
  const router = useRouter();

  const handleChange = (value: string) => {
    if (value === TicketTypes.MYSQL_PROXY_UPGRADE) {
      router.push({
        name: TicketTypes.MYSQL_PROXY_UPGRADE,
      });
    } else {
      router.push({
        name: TicketTypes.MYSQL_LOCAL_UPGRADE,
        query: {
          roleType: value,
        },
      });
    }
    emits('change', modelValue.value);
  };

  watch(
    () => modelValue.value.updateType,
    () => {
      if (modelValue.value.updateType === TicketTypes.MYSQL_MIGRATE_UPGRADE) {
        router.push({
          name: TicketTypes.MYSQL_MIGRATE_UPGRADE,
        });
      } else {
        router.push({
          name: TicketTypes.MYSQL_LOCAL_UPGRADE,
        });
      }
      emits('change', modelValue.value);
    },
  );
</script>

<style lang="less" scoped>
  .mysql-version-upgrade-page {
    padding-bottom: 20px;

    .upgrade-form {
      margin: 24px 0;

      :deep(.bk-form-label) {
        font-size: 12px;
        font-weight: 700;
        color: #313238;
      }
    }
  }
</style>
