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
  <SmartAction>
    <div class="db-backup-page">
      <BkAlert
        theme="info"
        :title="$t('所有库表备份_除MySQL系统库和DBA专用库外')" />
      <DbForm
        ref="formRef"
        form-type="vertical"
        :model="formData"
        style="margin-top: 16px;">
        <TargetCluster v-model="formData.cluster_ids" />
        <!-- <BkFormItem
          v-model="formData.online"
          :label="$t('备份选项')"
          property="online"
          required>
          <BkRadioGroup>
            <BkRadio label>
              {{ $t('在线备份') }}
            </BkRadio>
            <BkRadio :label="false">
              {{ $t('停机备份') }}
            </BkRadio>
          </BkRadioGroup>
        </BkFormItem> -->
        <BkFormItem
          :label="$t('备份类型')"
          property="backup_type"
          required>
          <BkRadioGroup v-model="formData.backup_type">
            <BkRadio label="logical">
              {{ $t('逻辑备份') }}
            </BkRadio>
          </BkRadioGroup>
        </BkFormItem>
        <BkFormItem
          :label="$t('备份保存时间')"
          property="file_tag"
          required>
          <BkRadioGroup v-model="formData.file_tag">
            <BkRadio label="MYSQL_FULL_BACKUP">
              {{ $t('30天') }}
            </BkRadio>
            <BkRadio label="LONGDAY_DBFILE_3Y">
              {{ $t('3年') }}
            </BkRadio>
          </BkRadioGroup>
        </BkFormItem>
      </DbForm>
    </div>
    <template #action>
      <BkButton
        class="w-88"
        :loading="isSubmitting"
        theme="primary"
        @click="handleSubmit">
        {{ $t('提交') }}
      </BkButton>
      <DbPopconfirm
        :confirm-handler="handleReset"
        :content="$t('重置将会情况当前填写的所有内容_请谨慎操作')"
        :title="$t('确认重置页面')">
        <BkButton
          class="ml8 w-88"
          :disabled="isSubmitting">
          {{ $t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
  </SmartAction>
</template>

<script setup lang="ts">
  import {
    reactive,
    ref,
  } from 'vue';
  import { useRouter } from 'vue-router';

  // TODO INTERFACE done
  // import { createTicket } from '@services/ticket';
  import { createTicket } from '@services/ticket';

  import { useGlobalBizs } from '@stores';

  import TargetCluster from './components/TargetCluster.vue';

  const createDefaultData = () => ({
    cluster_ids: [],
    // online: true,
    backup_type: 'logical',
    file_tag: 'MYSQL_FULL_BACKUP',
  });

  const router = useRouter();
  const { currentBizId } = useGlobalBizs();

  const formRef = ref();
  const formData = reactive(createDefaultData());

  const isSubmitting = ref(false);

  const handleSubmit = () => {
    formRef.value.validate()
      .then(() => {
        isSubmitting.value = true;
        createTicket({
          bk_biz_id: currentBizId,
          ticket_type: 'MYSQL_HA_FULL_BACKUP',
          remark: '',
          details: {
            infos: {
              ...formData,
            },
          },
        }).then((data) => {
          window.changeConfirm = false;
          router.push({
            name: 'MySQLDBBackup',
            params: {
              page: 'success',
            },
            query: {
              ticketId: data.id,
            },
          });
        })
          .finally(() => {
            isSubmitting.value = false;
          });
      });
  };

  const handleReset = () => {
    Object.assign(formData, createDefaultData());
  };
</script>

<style lang="less">
  .db-backup-page {
    padding-bottom: 20px;

    .bk-form-label {
      font-weight: bold;
      color: #313238;
    }
  }
</style>
