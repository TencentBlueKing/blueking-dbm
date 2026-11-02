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
      :title="
        t(
          '版本升级：主从接入层和单节点采用原地升级，存储层小版本升级采用原地升级（注意：暂不支持一主多从），大版本需提供新机迁移方式执行。同一主机所有关联集群将一并同步升级',
        )
      " />
    <BkForm
      class="toolbox-form"
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
          :desc="t('适用于小版本升级，如 5.6.1 ->  5.6.2')"
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

  import CardCheckbox from '@views/db-manage/common/db-card-checkbox/CardCheckbox.vue';

  import { switchSiblingRoute } from '@utils';

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

  // 当前页面的角色类型，跳转被离开确认取消时还原
  let currentRoleType = modelValue.value.roleType;
  // 正在还原升级类型：还原触发的 watch 不再跳转
  let isUpdateTypeRollback = false;

  const handleChange = (value: string) => {
    const previousRoleType = currentRoleType;
    currentRoleType = value;
    // 离开确认被取消时选项还原为当前页面
    const rollback = () => {
      currentRoleType = previousRoleType;
      modelValue.value.roleType = previousRoleType;
    };

    if (value === TicketTypes.MYSQL_PROXY_UPGRADE) {
      // 跳到另一个页面，不需要通知当前页面重置
      switchSiblingRoute(
        () =>
          router.push({
            name: TicketTypes.MYSQL_PROXY_UPGRADE,
          }),
        rollback,
      );
      return;
    }

    switchSiblingRoute(
      () =>
        router.push({
          name: TicketTypes.MYSQL_LOCAL_UPGRADE,
          query: {
            roleType: value,
          },
        }),
      rollback,
    );
    emits('change', modelValue.value);
  };

  /**
   * 升级类型切换都是跳到另一个页面（原地升级 / 迁移升级），不通知当前页面重置：
   * 原来先重置再跳转，离开确认被取消时当前页面数据已被清空
   */
  watch(
    () => modelValue.value.updateType,
    (_, oldUpdateType) => {
      if (isUpdateTypeRollback) {
        isUpdateTypeRollback = false;
        return;
      }
      // 离开确认被取消时选项还原为当前页面
      const rollback = () => {
        isUpdateTypeRollback = true;
        modelValue.value.updateType = oldUpdateType;
      };
      if (modelValue.value.updateType === TicketTypes.MYSQL_MIGRATE_UPGRADE) {
        switchSiblingRoute(
          () =>
            router.push({
              name: TicketTypes.MYSQL_MIGRATE_UPGRADE,
            }),
          rollback,
        );
      } else {
        switchSiblingRoute(
          () =>
            router.push({
              name: TicketTypes.MYSQL_LOCAL_UPGRADE,
            }),
          rollback,
        );
      }
    },
  );
</script>
