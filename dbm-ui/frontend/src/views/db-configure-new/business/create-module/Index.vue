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
    <DbForm
      ref="formRef"
      class="create-module-page db-scroll-y"
      :label-width="168"
      :model="formData">
      <!-- 模块信息 -->
      <DbCard
        mode="collapse"
        :title="t('模块信息')">
        <BkFormItem
          :label="t('模块名称')"
          property="alias_name"
          required
          :rules="rules.alias_name">
          <BkInput
            v-model="formData.alias_name"
            :placeholder="t('由英文字母_数字_连字符_组成')"
            :readonly="isReadonly" />
        </BkFormItem>
      </DbCard>

      <!-- 绑定数据库配置 -->
      <DbCard
        class="mt-16"
        mode="collapse"
        :title="t('绑定数据库配置')">
        <BkFormItem
          :label="t('数据库类型')"
          required>
          <BkTag
            class="db-type-tag"
            theme="info"
            type="stroke">
            <template #icon>
              <i class="db-icon-mysql mr-5" />
            </template>
            {{ ticketInfo.name }}
          </BkTag>
        </BkFormItem>
        <BkFormItem
          :label="t('数据库版本')"
          property="db_version"
          required>
          <DeployVersion
            v-model="formData.db_version"
            :db-type="DBTypes.MYSQL"
            :placeholder="t('请选择数据库版本')"
            query-key="mysql" />
        </BkFormItem>
        <BkFormItem
          :label="t('字符集')"
          property="charset"
          required>
          <BkSelect
            v-model="formData.charset"
            :clearable="false"
            :disabled="isBindSuccessfully"
            filterable
            :placeholder="t('请选择字符集')">
            <BkOption
              v-for="(item, index) in characterSets"
              :key="index"
              :label="item"
              :value="item" />
          </BkSelect>
        </BkFormItem>
      </DbCard>

      <!-- 参数配置 — 四个 Tab -->
      <div class="param-config-wrapper">
        <BkTab
          v-model:active="activeConfType"
          type="card-tab">
          <BkTabPanel
            v-for="tab of confTabs"
            :key="tab.conf_file"
            :label="tab.name"
            :name="tab.conf_file"
            render-directive="if">
            <ParamTable
              :ref="(el: any) => setTableRef(tab.name, el)"
              :cluster-type="ticketInfo.type"
              :conf-type="tab.conf_type"
              :version="formData.db_version" />
          </BkTabPanel>
        </BkTab>
      </div>
    </DbForm>
    <template #action>
      <BkButton
        class="w-88"
        :loading="isSubmitting"
        theme="primary"
        @click="handleSubmit">
        {{ t('确定') }}
      </BkButton>
      <BkButton
        class="w-88 ml-8"
        :disabled="isSubmitting"
        @click="handleReset">
        {{ t('重置') }}
      </BkButton>
      <BkButton
        class="w-88 ml-8"
        :disabled="isSubmitting"
        @click="handleCancel">
        {{ t('取消') }}
      </BkButton>
    </template>
  </SmartAction>
  <Teleport to="#dbContentTitleAppend">
    <span class="create-module-nav-desc"> {{ t('业务') }} : {{ bizInfo.name }} </span>
  </Teleport>
</template>

<script setup lang="ts">
  import InfoBox from 'bkui-vue/lib/info-box';
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { createModules } from '@services/source/cmdb';
  import { getListClusterModuleConfFiles, getModuleDetail, saveModulesDeployInfo } from '@services/source/configs';

  import { useGlobalBizs } from '@stores';

  import { DBTypes, mysqlType, type MysqlTypeString } from '@common/const';

  import ParamTable from '@views/db-configure-new/components/ParamTable.vue';
  import DeployVersion from '@views/db-manage/common/apply-items/DeployVersion.vue';

  const { t } = useI18n();
  const router = useRouter();
  const route = useRoute();
  const globalBizsStore = useGlobalBizs();

  const getSmartActionOffsetTarget = () => document.querySelector('.bk-form-content');

  const ticketType = route.params.type as MysqlTypeString;
  const ticketInfo = mysqlType[ticketType];
  const bizId = window.PROJECT_CONFIG.BIZ_ID;

  // 业务信息
  const bizInfo = computed(() => globalBizsStore.bizs.find((info) => info.bk_biz_id === bizId) || { name: '' });

  const isNewModule = !route.params.db_module_id;
  const moduleId = ref(Number(route.params.db_module_id));
  const isReadonly = computed(() => (isNewModule ? !!moduleId.value : true));
  const isBindSuccessfully = ref(false);
  const isSubmitting = ref(false);

  // 表单数据
  const getFormData = () => ({
    alias_name: (route.query.alias_name ?? '') as string,
    charset: '',
    db_version: '',
  });
  const formData = reactive(getFormData());
  const formRef = ref();

  const characterSets = ['utf8', 'utf8mb4', 'gbk', 'latin1', 'gb2312'];

  // 克隆模块时获取原模块配置
  const cloneModuleId = route.query.moduleId;
  if (cloneModuleId) {
    useRequest(getModuleDetail, {
      defaultParams: [{ module_id: Number(cloneModuleId) }],
      onSuccess(res) {
        formData.alias_name = res.alias_name ?? '';
        formData.charset = res.charset ?? '';
        formData.db_version = res.db_version ?? '';
      },
    });
  }

  const rules = {
    alias_name: [
      {
        message: t('模块名称不能为空'),
        required: true,
        trigger: 'blur',
      },
      {
        message: t('只能英文字母开头'),
        pattern: /^[A-Za-z]/,
        trigger: 'blur',
      },
      {
        message: t('由英文字母_数字_连字符_组成'),
        pattern: /^[0-9a-zA-Z-]+$/,
        trigger: 'blur',
      },
    ],
  };

  // 参数配置 Tab
  const activeConfType = ref('dbconf');
  const { data: confTabs, run: fetchConfTabs } = useRequest(getListClusterModuleConfFiles, {
    manual: true,
  });

  watch(
    () => formData.db_version,
    () => {
      if (formData.db_version) {
        fetchConfTabs({
          bk_biz_id: bizId,
          deploy_versions: JSON.stringify({
            db_version: formData.db_version,
          }),
          meta_cluster_type: ticketInfo.type,
        });
      }
    },
    { immediate: true },
  );

  // 每个 confType 对应一个 ParamTable 实例
  const tableRefs = ref<Record<string, InstanceType<typeof ParamTable>>>({});
  const setTableRef = (name: string, el: any) => {
    if (el) {
      tableRefs.value[name] = el;
    }
  };

  /** 提交 */
  const handleSubmit = async () => {
    isSubmitting.value = true;
    try {
      await formRef.value?.validate();

      // 新建模块
      if (!isReadonly.value) {
        const dbModuleName = `${formData.alias_name}-${formData.db_version}-${formData.charset}`;
        const createResult = await createModules({
          alias_name: formData.alias_name,
          biz_id: bizId,
          cluster_type: ticketInfo.type,
          db_module_name: dbModuleName,
        });
        moduleId.value = createResult.db_module_id;
      }

      // 绑定数据库配置
      await saveModulesDeployInfo({
        bk_biz_id: bizId,
        conf_items: [
          {
            conf_name: 'charset',
            conf_value: formData.charset,
            description: t('字符集'),
            op_type: 'update',
          },
          {
            conf_name: 'db_version',
            conf_value: formData.db_version,
            description: t('数据库版本'),
            op_type: 'update',
          },
        ],
        conf_type: 'deploy',
        level_name: 'module',
        level_value: moduleId.value,
        meta_cluster_type: ticketInfo.type,
        version: 'deploy_info',
      });
      isBindSuccessfully.value = true;

      // 绑定各 tab 参数配置
      const bindTasks = Object.values(tableRefs.value)
        .filter((ref) => ref?.hasChange?.())
        .map((ref) => ref.bindConfigParameters());
      await Promise.all(bindTasks);

      window.changeConfirm = false;

      // 跳转到数据库配置并选中新模块
      router.push({
        name: 'DbConfigureList',
        params: {
          clusterType: ticketInfo.type,
        },
        query: {
          parentId: `app-${bizId}`,
          treeId: moduleId.value ? `module-${moduleId.value}` : '',
        },
      });
    } catch (e) {
      console.log(e);
    }
    isSubmitting.value = false;
  };

  /** 重置 */
  const handleReset = () => {
    InfoBox({
      cancelText: t('取消'),
      content: t('重置后_将会清空当前填写的内容'),
      onConfirm: () => {
        const resetData = isNewModule ? getFormData() : { charset: '', version: '' };
        _.merge(formData, resetData);
        Object.values(tableRefs.value).forEach((ref) => ref?.handleReset?.());
        nextTick(() => {
          window.changeConfirm = false;
        });
        return true;
      },
      title: t('确认重置表单内容'),
    });
  };

  /** 取消 */
  const handleCancel = () => {
    routerBack();
  };

  const routerBack = () => {
    if (!route.query.from) {
      router.push({
        name: 'serviceApply',
      });
      return;
    }
    router.push({
      name: String(route.query.from),
      params: {
        clusterType: route.query.clusterType as string,
      },
    });
  };

  defineExpose({
    routerBack,
  });
</script>

<style lang="less" scoped>
  @import '@styles/mixins';

  .create-module-page {
    height: 100%;
    padding-bottom: 20px;

    :deep(.bk-form-item) {
      max-width: 690px;
    }
  }

  .param-config-wrapper {
    margin-top: 16px;
    background: #fff;

    :deep(.bk-tab-content) {
      padding: 16px;
    }
  }

  .db-type-tag {
    height: 30px;
    color: @primary-color;
    background: white;
    border: 1px solid @border-primary;
  }

  .create-module-nav-desc {
    position: relative;
    padding-left: 8px;
    margin-left: 8px;
    font-family: 'Microsoft YaHei', sans-serif;
    font-size: 14px;
    line-height: 22px;
    color: #979ba5;
  }

  .create-module-nav-desc::before {
    position: absolute;
    top: 50%;
    left: 0;
    width: 1px;
    height: 16px;
    content: '';
    background: #dcdee5;
    transform: translateY(-50%);
  }
</style>
