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
  <!-- 与 DbForm 一致：以点击判定用户主动修改，避免控件初始化回写被当成修改 -->
  <div @click="handleUserAction">
    <DbForm
      ref="form"
      :model="formData"
      :rules="rules">
      <BkFormItem :label="t('域名')">
        {{ data.domain }}
      </BkFormItem>
      <BkFormItem :label="t('维护方式')">
        {{ data.maintain_type_display || '--' }}
      </BkFormItem>
      <BkFormItem
        :description="t('至少保留一个 IP，重复地址自动去重')"
        label="IP"
        property="ips"
        required>
        <DbTagInput
          v-model="formData.ips"
          allow-create
          multiple
          :placeholder="t('请输入 IP，按 Enter 确认')" />
      </BkFormItem>
      <BkFormItem
        :label="t('负责人')"
        property="owners"
        required>
        <DbMemberSelector v-model="formData.owners" />
      </BkFormItem>
      <BkFormItem
        :label="t('备注')"
        property="remark">
        <BkInput
          v-model="formData.remark"
          :maxlength="500"
          :rows="4"
          type="textarea" />
      </BkFormItem>
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
