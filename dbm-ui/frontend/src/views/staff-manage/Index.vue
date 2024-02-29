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
  <BkLoading
    class="staff-manage-page"
    :loading="isLoading">
    <SmartAction :offset-target="getSmartActionOffsetTarget">
      <DbForm
        ref="staffFormRef"
        class="staff-setting"
        :label-width="168"
        :model="adminList">
        <DbCard
          v-for="(item, index) of adminList"
          :key="item.db_type"
          class="mb-16"
          :title="item.db_type_display">
          <BkFormItem
            label="DBA"
            :property="`${index}.users`"
            required
            :rules="rules">
            <DbMemberSelector v-model="item.users" />
          </BkFormItem>
        </DbCard>
      </DbForm>
      <template #action>
        <div class="setting-footer">
          <AuthButton
            action-id="dba_administrator_edit"
            class="mr-8 w-88"
            :loading="isSubmitting"
            theme="primary"
            @click="handleSubmit">
            {{ $t('保存') }}
          </AuthButton>
          <BkButton
            v-if="!isPlatform"
            class="w-88"
            :disabled="isSubmitting"
            @click="handleReset">
            {{ $t('重置') }}
          </BkButton>
        </div>
      </template>
    </SmartAction>
  </BkLoading>
</template>
<script setup lang="ts">
  import { Message } from 'bkui-vue';
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getAdmins, updateAdmins } from '@services/source/dbadmin';
  import type { AdminItem } from '@services/types/staffSetting';

  import { useInfo } from '@hooks';

  import DbMemberSelector from '@components/db-member-selector/index.vue';

  const { t } = useI18n();
  const route = useRoute();

  const getSmartActionOffsetTarget = () => document.querySelector('.bk-form-content');

  const isPlatform = route.name === 'PlatformStaffManage';
  const bizId = isPlatform ? 0 : window.PROJECT_CONFIG.BIZ_ID;

  const staffFormRef = ref();
  const adminList = shallowRef<AdminItem[]>([]);

  let adminListMemo: AdminItem[] = [];

  const rules = [
    {
      validator: (value: string[]) => value.length > 0,
      trigger: 'blur',
      message: t('必填项'),
    },
  ];

  const { loading: isLoading, run: getAdminsMethod } = useRequest(getAdmins, {
    defaultParams: [
      {
        bk_biz_id: bizId,
      },
    ],
    onSuccess(result) {
      adminList.value = result;
      adminListMemo = _.cloneDeep(result);
    },
  });

  const { loading: isSubmitting, run: updateAdminsMethod } = useRequest(updateAdmins, {
    manual: true,
    onSuccess() {
      Message({
        message: t('保存成功'),
        theme: 'success',
      });
      getAdminsMethod({
        bk_biz_id: bizId,
      });
      window.changeConfirm = false;
    },
  });

  /**
   * 编辑人员列表
   */

  const handleSubmit = async () => {
    const validate = await staffFormRef.value
      .validate()
      .then(() => true)
      .catch(() => false);
    if (!validate) {
      return;
    }

    updateAdminsMethod({
      bk_biz_id: bizId,
      db_admins: adminList.value,
    });
  };

  const handleReset = () => {
    useInfo({
      title: t('确认重置'),
      content: t('重置将会恢复上次保存的内容'),
      onConfirm: () => {
        adminList.value = adminListMemo;
        return true;
      },
    });
  };
</script>
<style lang="less">
  .staff-manage-page {
    .bk-form-item {
      max-width: 690px;
    }

    .db-card {
      & ~ .db-card {
        margin-top: 16px;
      }
    }
  }
</style>
