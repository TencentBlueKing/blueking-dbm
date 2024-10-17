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
  <SmartAction :offset-target="getSmartActionOffsetTarget">
    <div class="password-temporary-modify">
      <div
        v-if="submitting"
        class="submitting-mask">
        <DbIcon
          class="submitting-icon"
          svg
          type="sync-pending" />
        <p class="submitting-text">
          {{ t('密码正在修改中，请稍等') }}
        </p>
      </div>
      <UpdateResult
        v-else-if="submitted"
        :password="formData.password"
        :submit-length="submitLength"
        :submit-res="submitRes"
        :submit-role-map="submitRoleMap"
        @refresh="handleRefresh"
        @retry="handleSubmit" />
      <DbForm
        v-else
        ref="formRef"
        class="password-form"
        :label-width="200"
        :model="formData">
        <InstanceList v-model="formData.instanceList" />
        <BkFormItem
          :label="t('统一临时密码')"
          property="password"
          required>
          <PasswordInput
            v-model="formData.password"
            :button-disabled="!instanceDbType"
            :button-disabled-tip="t('请先添加实例')"
            :db-type="instanceDbType" />
        </BkFormItem>
        <ValidDuration
          v-model="formData.validDuration"
          v-model:valid-duration-type="formData.validDurationType" />
      </DbForm>
    </div>
    <template
      v-if="!submitting && !submitted"
      #action>
      <BkButton
        class="w-88"
        theme="primary"
        @click="submitValidator">
        {{ t('提交') }}
      </BkButton>
      <DbPopconfirm
        :confirm-handler="handleReset"
        :content="t('重置将会清空当前填写的所有内容_请谨慎操作')"
        :title="t('确认重置页面')">
        <BkButton class="ml8 w-88">
          {{ t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
  </SmartAction>
  <RenderPasswordInstance />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { modifyAdminPassword } from '@services/source/permission';

  import { ClusterTypes, DBTypes } from '@common/const';

  import PasswordInput from '@views/db-manage/common/password-input/Index.vue';

  import InstanceList from './components/form-item/InstanceList.vue';
  import ValidDuration from './components/form-item/ValidDuration.vue';
  import RenderPasswordInstance from './components/render-passwrod-instance/Index.vue';
  import UpdateResult from './components/UpdateResult.vue';

  const { t } = useI18n();

  const createDefaultData = () => ({
    instanceList: [] as { ip: string; port: number; bk_cloud_id: number; cluster_type: ClusterTypes; role: string }[],
    password: '',
    validDuration: 1,
    validDurationType: 'day',
  });

  const submitted = ref(false);
  const submitLength = ref(0);
  const formRef = ref();
  const submitRoleMap = shallowRef<Record<string, string>>({});
  const formData = reactive(createDefaultData());
  const instanceDbType = ref<DBTypes>();

  watch(
    formData,
    () => {
      console.log('formData = ', formData);
      const { instanceList } = formData;
      if (instanceList.length > 0) {
        const instance = instanceList[0];
        const dbTypeMap = {
          [ClusterTypes.TENDBSINGLE]: DBTypes.MYSQL,
          [ClusterTypes.TENDBHA]: DBTypes.MYSQL,
          [ClusterTypes.TENDBCLUSTER]: DBTypes.TENDBCLUSTER,
          [ClusterTypes.SQLSERVER_HA]: DBTypes.SQLSERVER,
          [ClusterTypes.SQLSERVER_SINGLE]: DBTypes.SQLSERVER,
        } as Record<ClusterTypes, DBTypes>;
        instanceDbType.value = dbTypeMap[instance.cluster_type];
      }
    },
    {
      deep: true,
    },
  );

  const {
    loading: submitting,
    run: modifyAdminPasswordRun,
    data: submitRes,
  } = useRequest(modifyAdminPassword, {
    manual: true,
    onSuccess() {
      submitted.value = true;
      window.changeConfirm = false;
    },
  });

  const getSmartActionOffsetTarget = () => document.querySelector('.bk-form-content');

  const submitValidator = async () => {
    await formRef.value.validate();

    handleSubmit(formData.instanceList);
  };

  const handleSubmit = (
    instanceList: {
      ip: string;
      port: number;
      bk_cloud_id: number;
      cluster_type: ClusterTypes;
      role: string;
    }[] = [],
  ) => {
    const instanceListParam: typeof instanceList = [];
    const roleMap: Record<string, string> = {};
    instanceList.forEach((instance) => {
      const { ip, port, bk_cloud_id, role, cluster_type } = instance;

      roleMap[`${ip}:${port}`] = role;
      instanceListParam.push({
        ip,
        port,
        bk_cloud_id,
        role,
        cluster_type,
      });
    });

    let lockHour = formData.validDuration;
    if (formData.validDurationType === 'day') {
      lockHour = formData.validDuration * 24;
    }

    const params = {
      lock_hour: lockHour,
      password: formData.password,
      instance_list: instanceListParam,
    };

    submitLength.value = instanceListParam.length;
    submitRoleMap.value = roleMap;
    modifyAdminPasswordRun(params);
  };

  const handleReset = () => {
    Object.assign(formData, createDefaultData());
  };

  const handleRefresh = () => {
    handleReset();
    submitted.value = false;
  };
</script>

<style lang="less" scoped>
  .password-temporary-modify {
    margin-bottom: 32px;
    background-color: #fff;
    border-radius: 2px;

    .submitting-mask {
      padding: 90px 0 138px;
      text-align: center;

      .submitting-icon {
        font-size: 64px;
        color: @primary-color;
        animation: rotate 2s linear infinite;
      }

      .submitting-text {
        margin-top: 36px;
        font-size: 24px;
        color: #313238;
      }

      @keyframes rotate {
        0% {
          transform: rotate(0deg);
        }

        100% {
          transform: rotate(-360deg);
        }
      }
    }

    .password-form {
      padding: 32px 0 24px;
      border-radius: 2px;
      box-shadow: 0 3px 4px 0 #0000000a;

      :deep(.password-form-instance) {
        display: flex;
        align-items: center;
      }

      :deep(.password-form-item) {
        width: 386px;
      }
    }

    .btn-area {
      padding: 24px 0 24px 200px;
      background-color: #f5f7fa;
    }

    :deep(.instance-tip) {
      color: #ff9c01;
    }

    :deep(.type-icon) {
      font-size: 16px;
    }

    .form-item-input {
      min-width: 300px;
    }

    .form-item-suffix {
      width: 88px;
    }
  }
</style>
