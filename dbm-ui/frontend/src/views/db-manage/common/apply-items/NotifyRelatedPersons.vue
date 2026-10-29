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
   * 回填收件人：单据存的是「提单人 + 主DBA + 追加收件人」去重后的完整名单，去重后无法区分谁是追加的
   * （如主 DBA 同时被手动追加），按名字或位置剔除都会丢人，所以原样回填完整名单；提交时再与提单人、主 DBA 合并去重，结果不变
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

  /**
   * 提单人 + 主DBA + 收件人(与提单人、主DBA 合并去重)
   */
  const receiverUsername = () => _.uniq([creator.value, mainDba.value, ...personList.value].filter(Boolean));

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
