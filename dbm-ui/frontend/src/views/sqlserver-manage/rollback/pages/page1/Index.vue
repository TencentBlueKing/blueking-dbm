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
    <div class="rollback-page">
      <BkAlert
        closable
        theme="info"
        :title="
          t('新建一个单节点实例_通过全备_binlog的方式_将数据库恢复到过去的某一时间点或者某个指定备份文件的状态')
        " />
      <BkForm
        form-type="vertical"
        style="margin-top: 20px">
        <BkFormItem
          :label="t('构造类型')"
          required>
          <BkRadioGroup v-model="actionType">
            <BkRadioButton
              label="local"
              style="width: 200px">
              {{ t('原地定点构造') }}
            </BkRadioButton>
            <BkRadioButton
              label="otherCluster"
              style="width: 200px">
              {{ t('定点构造到其他集群') }}
            </BkRadioButton>
          </BkRadioGroup>
        </BkFormItem>
      </BkForm>
      <Component
        :is="renderCom"
        ref="tableRef" />
    </div>
    <template #action>
      <BkButton
        class="w-88"
        :loading="isSubmitting"
        theme="primary"
        @click="handleSubmit">
        {{ t('提交') }}
      </BkButton>
      <DbPopconfirm
        :confirm-handler="handleReset"
        :content="t('重置将会情况当前填写的所有内容_请谨慎操作')"
        :title="t('确认重置页面')">
        <BkButton
          class="ml8 w-88"
          :disabled="isSubmitting">
          {{ t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
  </SmartAction>
</template>
<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import { createTicket } from '@services/source/ticket';

  import RenderLocal from './components/local/Index.vue';
  import RenderOtherCluster from './components/other-cluster/Index.vue';

  const router = useRouter();
  const { t } = useI18n();

  const comMap = {
    local: RenderLocal,
    otherCluster: RenderOtherCluster,
  };

  const tableRef = ref<InstanceType<typeof RenderLocal>>();
  const actionType = ref<keyof typeof comMap>('local');
  const isSubmitting = ref(false);

  const renderCom = computed(() => comMap[actionType.value]);

  const handleSubmit = () => {
    isSubmitting.value = true;
    tableRef
      .value!.submit()
      .then((data) =>
        createTicket({
          ticket_type: 'SQLSERVER_ROLLBACK',
          remark: '',
          details: {
            is_local: actionType.value === 'local',
            infos: data,
          },
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        }).then((data) => {
          window.changeConfirm = false;
          router.push({
            name: 'sqlServerDBRollback',
            params: {
              page: 'success',
            },
            query: {
              ticketId: data.id,
            },
          });
        }),
      )
      .finally(() => {
        isSubmitting.value = false;
      });
  };

  const handleReset = () => {
    tableRef.value!.reset();
  };
</script>
<style lang="less">
  .rollback-page {
    padding-bottom: 20px;
  }
</style>
