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
  <BkDialog
    dialog-type="show"
    :draggable="false"
    height="auto"
    :is-show="props.isShow"
    quick-close
    :title="$t('修改密码')"
    :width="480"
    @closed="handleClose">
    <BkAlert
      class="mb-16"
      closable
      theme="warning"
      :title="$t('密码修改后，涉及实例将需要重新登录')" />
    <BkForm
      v-if="props.isShow"
      ref="accountRef"
      class="mb-36"
      form-type="vertical"
      :model="state.formData"
      :rules="rules">
      <BkFormItem
        ref="passwordItemRef"
        :label="$t('新密码')"
        property="password"
        required>
        <BkInput
          ref="passwordRef"
          v-model="state.formData.password"
          :placeholder="$t('请输入新密码')"
          type="password"
          @blur="handlePasswordBlur"
          @focus="handlePasswordFocus" />
      </BkFormItem>
      <BkFormItem
        ref="passwordItemConfirmRef"
        :label="$t('确认密码')"
        property="password"
        required>
        <BkInput
          ref="passwordConfirmRef"
          v-model="state.formData.passwordConfirm"
          :placeholder="$t('请再次输入新密码')"
          type="password"
          @blur="handlePasswordBlur"
          @focus="handlePasswordFocus" />
      </BkFormItem>
    </BkForm>
    <template #footer>
      <BkButton
        class="mr-8"
        :loading="state.isLoading"
        theme="primary"
        @click="handleSave">
        {{ $t('保存') }}
      </BkButton>
      <BkButton
        :disabled="state.isLoading"
        @click="handleClose">
        {{ $t('取消') }}
      </BkButton>
    </template>
  </BkDialog>
</template>


<script setup lang="ts">
  const props = defineProps({
    // eslint-disable-next-line vue/no-unused-properties
    isShow: {
      type: Boolean,
      default: false,
    },
    // eslint-disable-next-line vue/no-unused-properties
    info: {
      type: Object,
      default() {
        return {};
      },
    },
  });
  const emits = defineEmits(['update:isShow', 'success']);

  const state = reactive({
    formData: {
      password: '',
      user: '',
    },
    isLoading: false,
    publicKey: '',
  });

  const rules = [];

  const handlePasswordBlur = () => {
    //
  };

  const handlePasswordFocus = () => {
    //
  };

  const handleSave = () => {
    //
  };

  const handleClose = () => {
    emits('update:isShow', false);
  };
</script>
