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
    :width="960"
    @closed="handleClose">
    <template #header>
      <div
        v-if="type === 'copy'"
        class="detail-dialog-head">
        <div class="detail-dialog-head-text">
          {{ sidesliderTitle }}【
        </div>
        <div class="detail-dialog-head-name">
          {{ detailData.name }}
        </div>
        <div class="detail-dialog-head-text">
          】
        </div>
      </div>
      <div v-else>
        {{ sidesliderTitle }}
      </div>
    </template>
    <DbForm
      ref="formRef"
      class="detail-form"
      form-type="vertical"
      :model="formData">
      <BkFormItem
        :label="t('告警组名称')"
        property="name"
        required
        :rules="nameRules">
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
          :biz-id="bizId"
          :is-built-in="detailData.is_built_in"
          :type="type" />
      </BkFormItem>
      <NoticeMethodFormItem
        ref="noticeMethodRef"
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

  import {
    getAlarmGroupList,
    insertAlarmGroup,
    updateAlarmGroup,
  } from '@services/monitorAlarm';

  import { useBeforeClose } from '@hooks';

  import { messageSuccess } from '@utils';

  import NoticeMethodFormItem from './NoticeMethodFormItem.vue';
  import ReceiversSelector from './ReceiversSelector.vue';

  interface Props {
    type: 'add' | 'edit' | 'copy',
    detailData: ServiceReturnType<typeof getAlarmGroupList>['results'][number],
    bizId: number,
    nameList: string[]
  }

  interface Emits {
    (e: 'successed'): void,
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();
  const isShow = defineModel<boolean>({
    required: true,
  });

  const { t } = useI18n();
  const route = useRoute();
  const handleBeforeClose = useBeforeClose();

  const isPlatform = route.matched[0]?.name === 'Platform';
  const titleMap: Record<string, string> = {
    add: t('新建告警组'),
    edit: t('编辑告警组'),
    copy: t('克隆告警组'),
  };

  const nameRules = [
    {
      message: t('长度不能大于n', [80]),
      validator: (value: string)  => value.length <= 80,
    },
    {
      message: t('告警组名称重复'),
      validator: (name: string) => {
        if (props.type === 'copy') {
          return !props.nameList.includes(name);
        }

        return true;
      },
    },
  ];

  const formRef = ref();
  const receiversSelectorRef = ref();
  const noticeMethodRef = ref();
  const formData = reactive({
    name: '',
    receivers: [] as string[],
  });

  const loading = computed(() => insertLoading.value || updateLoading.value);
  const editDisabled = computed(() => {
    if (isPlatform) {
      return false;
    }
    return props.type === 'edit' && props.detailData.is_built_in;
  });
  const sidesliderTitle = computed(() => `${titleMap[props.type]}`);

  const {
    loading: insertLoading,
    run: insertAlarmGroupRun,
  } = useRequest(insertAlarmGroup, {
    manual: true,
    onSuccess() {
      runSuccess(t('创建成功'));
    },
  });

  const {
    loading: updateLoading,
    run: updateAlarmGroupRun,
  } = useRequest(updateAlarmGroup, {
    manual: true,
    onSuccess() {
      runSuccess(t('编辑成功'));
    },
  });

  watch(isShow, (newVal) => {
    if (newVal && props.type !== 'add') {
      formData.name = props.detailData.name;
      formData.receivers = props.detailData.receivers.map(item => item.id);
    }
  });

  const runSuccess = (message: string) => {
    messageSuccess(message);
    handleClose(true);
    emits('successed');
  };

  const handleSubmit = async () => {
    await formRef.value.validate();

    const { name } = formData;
    const params = {
      bk_biz_id: props.bizId,
      name,
      receivers: receiversSelectorRef.value.getSelectedReceivers(),
      details: {
        alert_notice: noticeMethodRef.value.getSubmitData(),
      },
    };

    if (props.type === 'edit') {
      updateAlarmGroupRun({
        ...params,
        id: props.detailData.id,
      });
    } else {
      insertAlarmGroupRun(params);
    }
  };

  const handleClose = async (isRequest = false) => {
    if (!isRequest) {
      const result = await handleBeforeClose();
      if (!result) {
        return;
      }
    }

    formData.name = '';
    formData.receivers = [] as string[];
    isShow.value = false;

    nextTick(() => {
      window.changeConfirm = false;
    });
  };
</script>

<style lang="less" scoped>
  .detail-dialog-head {
    display: flex;
    width: 100%;
    padding-right: 16px;

    .detail-dialog-head-name {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .detail-dialog-head-text {
      flex-shrink: 0;
    }
  }

  .detail-form {
    padding: 24px 40px 40px;
  }

  :deep(.bk-tab-header-nav::-webkit-scrollbar) {
    display: block;
    width: 4px;
    height: 4px;
  }
</style>
