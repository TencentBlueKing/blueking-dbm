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
  <div class="db-toolbox">
    <BkAlert
      class="mb-20"
      closable
      :title="
        t(
          '通过全备 + binlog 的方式，将数据库恢复到过去的某一时间点或者某个指定备份文件的状态。数据可以构造到新临时单节点，可以选择已有的集群',
        )
      " />
    <BkForm
      ref="formRef"
      class="mb-24 toolbox-form"
      form-type="vertical"
      :model="formData">
      <BkFormItem
        :label="t('时区')"
        required>
        <TimeZonePicker style="width: 450px" />
      </BkFormItem>
      <BkFormItem
        :label="t('构造类型')"
        required>
        <BkRadioGroup
          v-model="formData.fixpointType"
          style="width: 450px"
          type="card"
          @change="handleChange">
          <BkRadioButton :label="TicketTypes.MYSQL_FIXPOINT_EXIST_CLUSTER">
            {{ t('在已有集群上构造数据') }}
          </BkRadioButton>
          <BkRadioButton :label="TicketTypes.MYSQL_FIXPOINT_NEW_CLUSTER">
            {{ t('在新集群上构造数据') }}
          </BkRadioButton>
        </BkRadioGroup>
      </BkFormItem>
      <slot />
    </BkForm>
  </div>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  import { TicketTypes } from '@common/const';

  import TimeZonePicker from '@components/time-zone-picker/index.vue';

  const { t } = useI18n();
  const router = useRouter();
  const route = useRoute();

  const formData = reactive({
    fixpointType: (route.meta.ticketType as TicketTypes) || TicketTypes.MYSQL_FIXPOINT_EXIST_CLUSTER,
  });

  const handleChange = (value: string) => {
    router.push({
      name: value,
    });
  };
</script>
