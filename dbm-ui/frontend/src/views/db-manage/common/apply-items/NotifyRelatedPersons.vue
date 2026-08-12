<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <div class="notify-related-persons">
    <DbFormItem
      :label="t('发送交付通知')"
      required>
      <div class="notify-wrapper">
        <BkSwitcher
          :model-value="modelValue.is_send"
          theme="primary"
          @change="handleSwitchChange" />
        <span
          v-if="modelValue.is_send"
          class="notify-desc">
          {{ t('默认通知提单人与主DBA，可追加收件人') }}
        </span>
      </div>
    </DbFormItem>
    <DbFormItem
      v-if="modelValue.is_send"
      class="mb-24"
      :label="t('收件人')">
      <MemberSelector
        v-model="personList"
        style="width: 435px" />
    </DbFormItem>
  </div>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getAdmins } from '@services/source/dbadmin';

  import { useUserProfile } from '@stores';

  import { DBTypes } from '@common/const';

  import MemberSelector from '@components/db-member-selector/index.vue';

  interface Props {
    bizId: number | '';
    dbType: DBTypes;
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<{
    is_send: boolean;
    msg_type: string[];
    receiver__username: string[];
  }>({ required: true });

  const { t } = useI18n();
  const { username } = useUserProfile();

  const personList = ref<string[]>([]);

  const { data: defaultAdminData } = useRequest(getAdmins, {
    defaultParams: [
      {
        bk_biz_id: 0,
        db_type: props.dbType,
      },
    ],
  });

  const { data: bizAdminData, run: runGetBizAdmins } = useRequest(getAdmins, {
    manual: true,
  });

  watch(
    () => props.bizId,
    () => {
      if (props.bizId) {
        runGetBizAdmins({
          bk_biz_id: Number(props.bizId),
          db_type: props.dbType,
        });
      }
    },
  );

  watch(
    () => modelValue.value.is_send,
    () => {
      if (!modelValue.value.is_send) {
        personList.value = [];
      }
    },
  );

  watch(
    () => modelValue.value.receiver__username,
    () => {
      if (modelValue.value.receiver__username.length > 0) {
        personList.value = modelValue.value.receiver__username.slice(2);
      }
    },
  );

  const handleSwitchChange = (value: boolean) => {
    const newValue = {
      ...modelValue.value,
      is_send: value,
      receiver__username: value ? [] : [],
    };
    modelValue.value = newValue;
  };

  /**
   * 提单人 + 主DBA + 收件人(与提单人、主DBA 合并去重)
   */
  const receiverUsername = () => {
    const defaultDba = defaultAdminData.value?.data?.[0]?.users[0];
    const bizMainDba = bizAdminData.value?.data?.[0]?.users[0] || '';
    const mainDbA = bizMainDba || defaultDba;
    return _.uniq([username, mainDbA, ...personList.value]);
  };

  defineExpose({
    getValue() {
      if (!modelValue.value.is_send) {
        return {};
      }
      return {
        ...modelValue.value,
        receiver__username: receiverUsername().join(','),
      };
    },
  });
</script>

<style lang="less">
  .notify-related-persons {
    .notify-wrapper {
      // display: flex;
      // align-items: center;

      .notify-desc {
        margin-left: 12px;
        font-size: 12px;
        line-height: 20px;
        color: #63656e;
      }
    }

    .bk-form-item:last-child {
      margin-bottom: 24px !important;
    }
  }
</style>
