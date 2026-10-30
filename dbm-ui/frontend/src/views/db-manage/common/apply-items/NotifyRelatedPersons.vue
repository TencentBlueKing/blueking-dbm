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
          :disabled="isDisabled"
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
        :disabled="isDisabled"
        style="width: 435px" />
    </DbFormItem>
  </div>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getAdmins } from '@services/source/dbadmin';

  import { useTicketModifyState } from '@hooks';

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
  const modifyState = useTicketModifyState();
  // 重新编辑、代为修改可改交付通知（随改单接口的 config 提交），调整申请只能改资源条件，只读
  const isDisabled = Boolean(modifyState?.isAdjustApply);
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

  // 提单人：改单时取单据的提单人，代为修改的操作人是审批人，不能把审批人当成提单人
  const creator = computed(() => modifyState?.ticketData.value?.creator || username);
  // 主 DBA：业务主 DBA 优先，没有时取平台默认 DBA
  const mainDba = computed(
    () => bizAdminData.value?.data?.[0]?.users[0] || defaultAdminData.value?.data?.[0]?.users[0] || '',
  );

  watch(
    () => modelValue.value.is_send,
    () => {
      if (!modelValue.value.is_send) {
        personList.value = [];
      }
    },
  );

  /**
   * 回填收件人：receiver__username 只存额外收件人，原样回填
   * 旧单据（没有 default_receiver_username）存的是「提单人 + 主DBA + 追加收件人」去重后的完整名单，无法区分谁是追加的，
   * 按名字或位置剔除都会丢人，所以同样原样回填
   */
  watch(
    () => modelValue.value.receiver__username,
    (receivers) => {
      if (receivers.length > 0) {
        personList.value = receivers.filter(Boolean);
      }
    },
    {
      immediate: true,
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

  defineExpose({
    getValue() {
      if (!modelValue.value.is_send) {
        return {};
      }
      return {
        ...modelValue.value,
        // 默认收件人：提单人 + 主DBA
        default_receiver_username: _.uniq([creator.value, mainDba.value].filter(Boolean)).join(','),
        // 额外收件人：仅用户追加的，没有追加时传空字符串
        receiver__username: _.uniq(personList.value.filter(Boolean)).join(','),
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
