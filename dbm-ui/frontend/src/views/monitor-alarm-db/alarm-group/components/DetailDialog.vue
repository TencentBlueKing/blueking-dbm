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
  <BkSideslider
    :is-show="isShow"
    :title="title"
    :width="960"
    @closed="handleClose">
    <DbForm
      ref="formRef"
      class="detail-form"
      form-type="vertical"
      :model="formData">
      <BkFormItem
        :label="t('告警组名称')"
        property="name"
        required>
        <BkInput
          v-model="formData.name"
          :disabled="editDisabled"
          :placeholder="t('请输入告警组名称')" />
      </BkFormItem>
      <BkFormItem
        :label="t('通知对象')"
        property="receivers"
        required>
        <ReceiversSelector
          ref="receiversSelectorRef"
          v-model="formData.receivers"
          :group-type="detailData.group_type"
          :type="type" />
      </BkFormItem>
      <NoticeMethodFormItem
        ref="noticeMothodRef"
        :details="detailData.details"
        :type="type" />
    </DbForm>
    <template #footer>
      <BkButton
        class="mr-8"
        :loading="loading"
        theme="primary"
        @click="handleSubmit">
        {{ t('提交') }}
      </BkButton>
      <BkButton
        :disabled="loading"
        @click="handleClose">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkSideslider>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { useBeforeClose } from '@hooks';

  import { updateAlarmGroup } from '../common/services';
  import type {
    AlarmGroupDetailParams,
    AlarmGroupItem,
  } from '../common/types';

  import NoticeMethodFormItem from './NoticeMethodFormItem.vue';
  import ReceiversSelector from './ReceiversSelector.vue';

  interface Props {
    title: string,
    type: 'add' | 'edit' | 'copy' | '',
    detailData: AlarmGroupItem
  }

  const props = defineProps<Props>();
  const isShow = defineModel<boolean>({
    required: true,
  });

  const { t } = useI18n();
  const route = useRoute();


  const formRef = ref();
  const receiversSelectorRef = ref();
  const noticeMothodRef = ref();

  watch(isShow, (newVal) => {
    if (newVal && props.type !== 'add') {
      formData.name = props.detailData.name;
      formData.receivers = props.detailData.receivers.map(item => item.id);
    }
  });

  const formData = reactive({
    name: '',
    receivers: [] as string[],
  });
  const isPlatform = computed(() => route.matched[0]?.name === 'Platform');
  const editDisabled = computed(() => {
    if (isPlatform.value) return false;
    return props.type === 'edit' && props.detailData.group_type === 'PLATFORM';
  });

  const {
    loading,
    run: updateAlarmGroupRun,
  } = useRequest(updateAlarmGroup, {
    manual: true,
  });

  const handleSubmit = async () => {
    await formRef.value.validate();

    const { name } = formData;
    const params: AlarmGroupDetailParams = {
      name,
      receivers: receiversSelectorRef.value.getSelectedReceivers(),
      details: {
        alert_notice: noticeMothodRef.value.getSubmitData(),
      },
    };

    updateAlarmGroupRun(params);
  };

  const handleBeforeClose = useBeforeClose();
  const handleClose = async () => {
    const result = await handleBeforeClose();
    if (!result) return;

    formData.name = '';
    formData.receivers = [] as string[];

    window.changeConfirm = false;
    isShow.value = false;
  };
</script>

<style lang="less" scoped>
  .detail-form {
    padding: 24px 40px 40px;
  }
</style>
