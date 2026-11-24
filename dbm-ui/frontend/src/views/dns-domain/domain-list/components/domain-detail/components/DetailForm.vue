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
  <!-- 以用户点击 / 按键判定主动修改，避免控件初始化回写被当成修改 -->
  <!-- 必须用捕获阶段：冒泡阶段时子组件的删除已同步改值，监听回调结束后的微任务里 watch 先跑，标记还没打上 -->
  <!-- 原生 input 冒泡：IP 输入框的文本回车或失焦才落成标签，键入时即视为修改 -->
  <div
    @click.capture="handleUserAction"
    @input="handleUserInput"
    @keydown.capture="handleUserAction">
    <DbForm
      ref="form"
      :model="formData"
      :rules="rules">
      <DbFormItem :label="t('域名')">
        {{ data.domain }}
      </DbFormItem>
      <DbFormItem :label="t('维护方式')">
        {{ data.maintain_type_display || '--' }}
      </DbFormItem>
      <DbFormItem
        :description="t('至少保留一个 IP，重复地址自动去重')"
        label="IP"
        property="ips"
        required>
        <DbTagInput
          v-model="formData.ips"
          allow-create
          multiple
          :placeholder="t('请输入 IP，按 Enter 确认')" />
      </DbFormItem>
      <DbFormItem
        :label="t('负责人')"
        property="owners"
        required>
        <DbMemberSelector v-model="formData.owners" />
      </DbFormItem>
      <DbFormItem
        :label="t('备注')"
        property="remark">
        <DbInput
          v-model="formData.remark"
          :maxlength="500"
          :rows="4"
          type="textarea" />
      </DbFormItem>
    </DbForm>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { DnsDomainDetail } from '@services/source/dnsDomain';

  import DbMemberSelector from '@components/db-member-selector/index.vue';

  import { isValidIpList } from '@views/dns-domain/utils';

  interface Props {
    data: DnsDomainDetail;
  }

  type Emits = (e: 'change') => void;

  interface Exposes {
    // 校验通过后返回提交内容，IP 为保存后的完整集合
    getValue: () => Promise<{ ips: string[]; owners: string[]; remark: string }>;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const formRef = useTemplateRef('form');

  const formData = reactive({
    ips: [...props.data.ips],
    owners: [...props.data.owners],
    remark: props.data.remark,
  });

  const rules = {
    ips: [
      {
        message: t('至少保留一个 IP'),
        trigger: 'change',
        validator: (value: string[]) => value.length > 0,
      },
      {
        message: t('请输入不带端口的 IPv4 地址'),
        trigger: 'change',
        validator: (value: string[]) => isValidIpList(value),
      },
    ],
    owners: [
      {
        message: t('至少保留 1 人'),
        trigger: 'change',
        validator: (value: string[]) => value.length > 0,
      },
    ],
  };

  let isUserAction = false;
  const handleUserAction = () => {
    isUserAction = true;
  };

  // 键盘输入一定是用户操作，不必等值写回 formData
  const handleUserInput = () => {
    isUserAction = true;
    emits('change');
  };

  watch(
    formData,
    () => {
      if (isUserAction) {
        emits('change');
      }
    },
    { deep: true },
  );

  defineExpose<Exposes>({
    getValue: () =>
      formRef.value!.validate().then(() => ({
        ips: [...new Set(formData.ips)],
        owners: formData.owners,
        remark: formData.remark,
      })),
  });
</script>
