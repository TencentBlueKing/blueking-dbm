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
  <DbSideslider
    :cancel-handler="handleCancel"
    :cancel-text="t('取消')"
    :confirm-handler="handleSubmit"
    :confirm-text="t('提交')"
    :is-show="isShow"
    :show-footer="!editDisabled"
    :width="960"
    @closed="handleClose">
    <template #header>
      <div
        v-if="type === 'copy'"
        class="alarm-group-detail-dialog-head">
        <div class="alarm-group-detail-dialog-head-text">{{ sidesliderTitle }}【</div>
        <div class="alarm-group-detail-dialog-head-name">
          {{ detailData.name }}
        </div>
        <div class="alarm-group-detail-dialog-head-text">】</div>
      </div>
      <div v-else>
        {{ sidesliderTitle }}
      </div>
    </template>
    <DbForm
      ref="formRef"
      class="alarm-group-detail-form"
      form-type="vertical"
      :model="formData"
      @validate="handleFormValidate">
      <BkFormItem
        :class="{ 'is-hide-tip': !formData.name }"
        :label="t('告警组名称')"
        property="name"
        required
        :rules="nameRules">
        <BkInput
          v-model="formData.name"
          :disabled="editDisabled"
          :maxlength="50"
          :placeholder="t('请输入告警组名称')"
          show-word-limit />
        <div
          v-if="!hideTipMap.name"
          class="form-item-desc">
          {{ t('支持中文、字母、数字、连字符、下划线、点号，创建后可修改') }}
        </div>
      </BkFormItem>
      <NoticeMethodFormItem
        ref="noticeMethodRef"
        v-model:is-receivers-selector-show="isReceiversSelectorShow"
        :details="detailData.details"
        :disabled="editDisabled"
        :is-submiting="isSubmiting"
        :type="type" />
      <BkFormItem
        v-if="isReceiversSelectorShow"
        class="receivers-selector-form-item"
        :class="{ 'is-hide-tip': !formData.receivers.length }"
        :label="t('通知对象')"
        property="receivers"
        required>
        <ReceiversSelector
          ref="receiversSelectorRef"
          v-model="formData.receivers"
          :biz-id="bizId"
          :disabled="editDisabled"
          :is-built-in="detailData.is_built_in"
          :type="type" />
      </BkFormItem>
    </DbForm>
  </DbSideslider>
</template>

<script setup lang="ts">
  import type { UnwrapRef } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getAlarmGroupList, insertAlarmGroup, patchAlarmGroup } from '@services/source/monitorNoticeGroup';

  import { useBeforeClose } from '@hooks';

  import { noticeGroupNameRegex } from '@common/regex.ts';

  import { messageSuccess } from '@utils';

  import NoticeMethodFormItem from './components/NoticeMethodFormItemNew.vue';
  import ReceiversSelector from './components/ReceiversSelector.vue';

  interface Props {
    bizId: number;
    detailData: ServiceReturnType<typeof getAlarmGroupList>['results'][number];
    nameList: string[];
    type: 'add' | 'edit' | 'copy';
  }

  type Emits = (e: 'successed') => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();
  const isShow = defineModel<boolean>({
    required: true,
  });

  const { t } = useI18n();
  const handleBeforeClose = useBeforeClose();

  const titleMap: Record<string, string> = {
    add: t('新建告警组'),
    copy: t('克隆告警组'),
    edit: t('编辑告警组'),
  };

  const nameRules = [
    // {
    //   message: '',
    //   required: true,
    //   trigger: 'blur',
    //   validator: (value: string) => {
    //     if (value) {
    //       return true;
    //     }
    //     return '';
    //   },
    // },
    // {
    //   message: t('长度不能大于n', [80]),
    //   validator: (value: string) => value.length <= 80,
    // },
    {
      message: t('格式不正确，请勿使用特殊符号'),
      trigger: 'blur',
      validator: (value: string) => {
        return noticeGroupNameRegex.test(value);
      },
    },
    {
      message: t('告警组名称重复'),
      validator: (name: string) => {
        if (props.type !== 'edit') {
          return !props.nameList.includes(name);
        }

        return true;
      },
    },
  ];

  const formRef = useTemplateRef('formRef');
  const receiversSelectorRef = useTemplateRef('receiversSelectorRef');
  const noticeMethodRef = useTemplateRef('noticeMethodRef');

  const isReceiversSelectorShow = ref(false);
  const formData = reactive({
    name: '',
    receivers: [] as string[],
  });
  const hideTipMap = ref<Record<keyof UnwrapRef<typeof formData>, boolean>>({
    name: false,
    receivers: false,
  });
  const isSubmiting = ref(false);

  const editDisabled = computed(() => props.type === 'edit' && props.detailData.is_built_in);

  const sidesliderTitle = computed(() => `${titleMap[props.type]}`);

  const { runAsync: insertAlarmGroupRun } = useRequest(insertAlarmGroup, {
    manual: true,
  });

  const { runAsync: patchAlarmGroupRun } = useRequest(patchAlarmGroup, {
    manual: true,
  });

  watch(isShow, (newVal) => {
    if (newVal && props.type !== 'add') {
      formData.name = props.detailData.name;
      formData.receivers = props.detailData.receivers.map((item) => item.id);
    }
  });

  watch(
    () => formData.receivers,
    () => {
      formRef.value?.validate('receivers');
    },
  );

  const handleFormValidate = (property: string, result: boolean) => {
    hideTipMap.value[property as keyof typeof hideTipMap.value] =
      !result &&
      (property === 'receivers' ? formData.receivers.length > 0 : !!formData[property as keyof typeof formData]);
  };

  const runSuccess = (message: string) => {
    messageSuccess(message);
    handleClose(true);
    emits('successed');
  };

  const handleSubmit = async () => {
    try {
      isSubmiting.value = true;
      await formRef.value!.validate();

      const { name } = formData;
      const { alertNotice, channels } = noticeMethodRef.value!.getSubmitData();
      const receivers = receiversSelectorRef.value?.getSelectedReceivers() || [];

      if (props.type === 'edit') {
        await patchAlarmGroupRun({
          details: {
            alert_notice: alertNotice,
            channels,
          },
          id: props.detailData.id,
          name,
          receivers: isReceiversSelectorShow.value ? receivers : [],
        });
        runSuccess(t('编辑成功'));
      } else {
        await insertAlarmGroupRun({
          bk_biz_id: props.bizId,
          details: {
            alert_notice: alertNotice,
            channels,
          },
          name,
          receivers: isReceiversSelectorShow.value ? receivers : [],
        });
        runSuccess(t('创建成功'));
      }
    } finally {
      setTimeout(() => {
        isSubmiting.value = false;
      });
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

  const handleCancel = () => handleClose(true);
</script>

<style lang="less">
  .alarm-group-detail-dialog-head {
    display: flex;
    width: 100%;
    padding-right: 16px;

    .alarm-group-detail-dialog-head-name {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .alarm-group-detail-dialog-head-text {
      flex-shrink: 0;
    }
  }

  .alarm-group-detail-form {
    padding: 24px;

    .form-item-desc {
      position: absolute;
      top: 34px;
      font-size: 12px;
      line-height: 20px;
      color: #979ba5;

      &.is-last-tip {
        margin-top: -6px;
      }
    }

    .is-hide-tip {
      .bk-form-error {
        display: none;
      }
    }

    .receivers-selector-form-item {
      &.is-error {
        .user-selector-container {
          border-color: #ea3636;
          transition: all 0.15s;
        }
      }
    }
  }

  // .bk-tab-header-nav::-webkit-scrollbar {
  //   display: block;
  //   width: 4px;
  //   height: 4px;
  // }
</style>
