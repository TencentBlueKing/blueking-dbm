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

<!--
  修改说明：源表单之后、页脚之前的独立分组，代为修改与调整申请必填，重新编辑不展示。
  修改说明不在各申请页的表单 model 里，用独立表单校验，由改单提交前调用
-->
<template>
  <DbForm
    v-if="isShow"
    ref="form"
    class="mt-16"
    form-type="vertical"
    :model="formData">
    <DbCard :title="t('修改说明')">
      <BkFormItem
        :label="t('修改说明')"
        property="remark"
        required>
        <DbInput
          v-model="formData.remark"
          :maxlength="500"
          :placeholder="placeholder"
          :rows="4"
          show-word-limit
          type="textarea" />
      </BkFormItem>
    </DbCard>
  </DbForm>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModifyRecordModel from '@services/model/ticket/modify-record';

  import { useTicketModifyState } from '@hooks';

  const { t } = useI18n();
  const modifyState = useTicketModifyState();

  const formRef = useTemplateRef('form');

  const isShow = computed(() => Boolean(modifyState && modifyState.mode !== TicketModifyRecordModel.MODE_RE_EDIT));

  const placeholder = computed(() =>
    modifyState?.mode === TicketModifyRecordModel.MODE_ADJUST_APPLY
      ? t('请说明调整资源申请条件的原因')
      : t('请说明修改的内容与原因，提交后提单人可见'),
  );

  const formData = reactive({
    remark: '',
  });

  watch(
    () => formData.remark,
    () => {
      if (modifyState) {
        modifyState.modifyRemark.value = formData.remark;
      }
    },
  );

  if (modifyState && isShow.value) {
    modifyState.validateRemark = () => formRef.value!.validate();
  }
</script>
