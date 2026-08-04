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
      <template v-if="submitted">
        <UpdateResult
          :instance-list="formData.instanceList"
          :password="formData.password"
          :root-id="rootId"
          @refresh="handleRefresh"
          @retry="handleSubmit" />
      </template>
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
            :db-type="instanceDbType"
            @verify-result="verifyResult" />
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
        v-if="hasPermission"
        v-bk-tooltips="{
          content: t('密码不符合要求'),
          disabled: !Boolean(formData.password) || passwordIsPass,
        }"
        class="w-88"
        :disabled="!passwordIsPass || !instanceDbType"
        :loading="permissionChecking"
        theme="primary"
        @click="handleSubmit">
        {{ t('提交') }}
      </BkButton>
      <BkButton
        v-else
        v-bk-tooltips="{
          content: t('密码不符合要求'),
          disabled: !Boolean(formData.password) || passwordIsPass,
        }"
        v-cursor
        class="w-88 auth-button-disable"
        :disabled="!passwordIsPass || !instanceDbType"
        :loading="permissionChecking"
        theme="primary"
        @click="handleRequestPermission">
        {{ t('提交') }}
      </BkButton>
      <DbPopconfirm
        :confirm-handler="handleReset"
        :content="t('重置将会清空当前填写的所有内容_请谨慎操作')"
        :title="t('确认重置页面')">
        <BkButton class="ml-8 w-88">
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

  import { checkAuthAllowed, getApplyDataLink } from '@services/source/iam';
  import { modifyAdminPassword } from '@services/source/permission';

  import { ClusterTypes, DBTypes } from '@common/const';

  import PasswordInput from '@views/db-manage/common/password-input/Index.vue';

  import { permissionDialog } from '@utils';

  import InstanceList, { type IRowData } from './components/form-item/InstanceList.vue';
  import ValidDuration from './components/form-item/ValidDuration.vue';
  import RenderPasswordInstance from './components/render-passwrod-instance/Index.vue';
  import UpdateResult from './components/UpdateResult.vue';

  const { t } = useI18n();

  const createDefaultData = () => ({
    instanceList: [] as IRowData[],
    password: '',
    validDuration: 1,
    validDurationType: 'day',
  });

  const formRef = ref();
  const rootId = ref('');
  const instanceDbType = ref<DBTypes>(DBTypes.MYSQL);
  const passwordIsPass = ref(false);
  const submitted = ref(false);
  const permissionChecking = ref(false);
  // 集群级修改权限检查结果：无权限时提交按钮置灰，hover 显示锁头，点击弹权限申请
  const hasPermission = ref(true);
  const formData = reactive(createDefaultData());

  /**
   * 修改临时密码权限 action（按 DB 类型区分）
   * - mysql_manage
   * - tendbcluster_manage
   * - sqlserver_manage
   */
  const adminPwdModifyActionMap: Record<string, string> = {
    [DBTypes.MYSQL]: 'mysql_manage',
    [DBTypes.SQLSERVER]: 'sqlserver_manage',
    [DBTypes.TENDBCLUSTER]: 'tendbcluster_manage',
  };

  // 当前待检查的 action 与资源列表
  const permissionParams = computed(() => {
    const actionId = adminPwdModifyActionMap[instanceDbType.value];
    const clusterIds = [...new Set(formData.instanceList.map((instance) => instance.cluster_id))];
    return {
      actionId,
      resources: clusterIds.map((id) => ({
        id,
        type: instanceDbType.value,
      })),
    };
  });

  // 实例列表变化时：更新 DB 类型 + 提前检查修改权限，决定提交按钮是否可点击
  watch(
    () => formData.instanceList,
    async () => {
      const { instanceList } = formData;
      if (instanceList.length > 0) {
        // 从首个实例的集群类型推导 DB 类型（不依赖 instanceDbType 的更新时序）
        const dbTypeMap = {
          [ClusterTypes.SQLSERVER_HA]: DBTypes.SQLSERVER,
          [ClusterTypes.SQLSERVER_SINGLE]: DBTypes.SQLSERVER,
          [ClusterTypes.TENDBCLUSTER]: DBTypes.TENDBCLUSTER,
          [ClusterTypes.TENDBHA]: DBTypes.MYSQL,
          [ClusterTypes.TENDBSINGLE]: DBTypes.MYSQL,
        } as Record<ClusterTypes, DBTypes>;
        const dbType = dbTypeMap[instanceList[0].cluster_type];
        if (dbType) {
          instanceDbType.value = dbType;
        }
      }

      const { actionId, resources } = permissionParams.value;
      if (!actionId || resources.length < 1) {
        hasPermission.value = true;
        return;
      }
      try {
        const allowedList = await checkAuthAllowed({
          action_ids: [actionId],
          resources,
        });
        hasPermission.value = allowedList.some((item) => item.action_id === actionId && item.is_allowed);
      } catch {
        // 检查失败时放行，由提交时的兜底校验处理
        hasPermission.value = true;
      }
    },
    {
      deep: true,
      immediate: true,
    },
  );

  // 无权限提交：获取申请链接渲染权限申请弹窗
  const handleRequestPermission = async () => {
    permissionChecking.value = true;
    try {
      const { actionId, resources } = permissionParams.value;
      const applyData = await getApplyDataLink({
        action_ids: [actionId],
        resources,
      });
      permissionDialog(applyData);
    } finally {
      permissionChecking.value = false;
    }
  };

  const { loading: submitting, run: modifyAdminPasswordRun } = useRequest(modifyAdminPassword, {
    manual: true,
    onSuccess(data) {
      submitted.value = true;
      window.changeConfirm = false;
      rootId.value = data;
    },
  });

  const getSmartActionOffsetTarget = () => document.querySelector('.bk-form-content');

  const verifyResult = (isPass: boolean) => {
    passwordIsPass.value = isPass;
  };

  // 有权限提交
  const handleSubmit = async (
    instanceList: {
      bk_cloud_id: number;
      cluster_type: ClusterTypes;
      ip: string;
      port: number;
      role: string;
    }[] = [],
  ) => {
    // 表单可见时先校验（失败重试场景表单不可见，跳过校验）
    if (formRef.value) {
      try {
        await formRef.value.validate();
      } catch {
        // 校验不通过，停留在当前表单
        return;
      }
    }
    const roleMap: Record<string, string> = {};
    const instanceListParam = (instanceList.length ? instanceList : formData.instanceList).map((instance) => {
      const { bk_cloud_id, cluster_type, ip, port, role } = instance;
      roleMap[`${ip}:${port}`] = role;
      return { bk_cloud_id, cluster_type, ip, port, role };
    });

    const lockHour = formData.validDuration * (formData.validDurationType === 'day' ? 24 : 1);

    modifyAdminPasswordRun({
      instance_list: instanceListParam,
      is_async: true,
      lock_hour: lockHour,
      password: formData.password,
    });
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
