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
  <div class="receivers-selector-wrapper">
    <MemberSelector
      v-model="modelValue"
      :disabled="disabled"
      :placeholder="t('请选择通知对象')" />
    <div
      v-if="memberList.length > 0"
      class="receivers-list">
      <div
        v-for="(memberItem, index) in memberList"
        :key="index"
        class="receivers-list-item">
        <div class="receivers-list-label">
          {{ memberItem.label }}
        </div>
        <div class="receivers-list-value">
          {{ memberItem.value }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { getUserGroupList } from '@services/source/cmdb';
  import { getAlarmGroupList } from '@services/source/monitorNoticeGroup';

  import MemberSelector from '@components/db-member-selector/index.vue';

  type UserGroup = ServiceReturnType<typeof getUserGroupList>[number];

  interface Props {
    disabled: boolean;
  }

  interface Exposes {
    getSelectedReceivers: () => ServiceReturnType<typeof getAlarmGroupList>['results'][number]['receivers'];
  }

  interface RecipientItem {
    display_name: string;
    type: string;
    username: string;
  }

  defineProps<Props>();
  const modelValue = defineModel<string[]>({
    required: true,
  });

  const { t } = useI18n();

  const itemMap: Record<string, RecipientItem> = {};
  const userGroupMap: Record<string, Pick<UserGroup, 'display_name' | 'members'>> = {};

  const memberList = computed(() => {
    const userGroupList: {
      label: string;
      value: string;
    }[] = [];
    const userList: string[] = [];

    modelValue.value.forEach((valueItem) => {
      const userGroupMapItem = userGroupMap[valueItem];
      if (userGroupMapItem) {
        userGroupList.push({
          label: userGroupMapItem.display_name,
          value: userGroupMapItem.members.join('，'),
        });
      } else {
        userList.push(valueItem);
      }
    });

    if (userList.length > 0) {
      return [
        ...userGroupList,
        {
          label: t('其他'),
          value: userList.join('，'),
        },
      ];
    }

    return userGroupList;
  });

  defineExpose<Exposes>({
    getSelectedReceivers() {
      return modelValue.value.map((modelValueItem) => ({
        id: modelValueItem,
        type: itemMap[modelValueItem]?.type || 'user',
      }));
    },
  });
</script>

<style lang="less" scoped>
  .receivers-selector-wrapper {
    .receivers-list {
      padding: 12px 16px;
      background: #f5f7fa;

      .receivers-list-item {
        font-size: 12px;

        &:not(:first-child) {
          margin-top: 16px;
        }
      }

      .receivers-list-label {
        line-height: 20px;
        color: #979ba5;
      }

      .receivers-list-value {
        margin-top: 2px;
        line-height: 16px;
        color: #63656e;
      }
    }
  }
</style>
