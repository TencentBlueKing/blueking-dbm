<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <SmartAction>
    <BkAlert
      class="mb-16"
      closable
      theme="info"
      :title="
        t('基于源模块创建新模块_常用于数据库版本升级_源模块自定义值将保留_新版本不兼容的参数将被废弃_请审慎后创建_')
      " />
    <DbForm
      ref="formRef"
      class="clone-module-page db-scroll-y"
      :label-width="168"
      :model="formData"
      :rules="rules">
      <!-- 模块信息 & 绑定数据库配置（紧凑布局） -->
      <DbCard
        mode="collapse"
        :title="t('模块信息')">
        <BkFormItem
          class="form-item-name"
          :label="t('模块名称')"
          property="alias_name"
          required>
          <BkInput
            v-model="formData.alias_name"
            :maxlength="63"
            :placeholder="t('请输入模块名')"
            show-word-limit />
          <div
            v-if="isValueAllowed"
            class="form-item-tips">
            {{ t('仅支持小写字母、数字、连字符，同时会参与集群域名生成，创建后不可改') }}
          </div>
        </BkFormItem>
        <BkFormItem
          :label="t('数据库信息')"
          required>
          <div class="db-config-row">
            <BkTag
              class="db-type-tag"
              theme="info"
              type="stroke">
              <template #icon>
                <DbIcon
                  class="mr-4"
                  type="sqlserver" />
              </template>
              {{ clusterTypeInfos[clusterType]?.name || 'SQLServer' }}
            </BkTag>
            <DbVersionSelect
              v-model="formData.version"
              class="version-select-inline"
              :db-type="DBTypes.SQLSERVER"
              @change="handleValidate" />
            <BkSelect
              v-model="formData.charset"
              class="charset-select-inline"
              :clearable="false"
              filterable
              :placeholder="t('请选择字符集')"
              :prefix="t('字符集')"
              @change="handleValidate">
              <BkOption
                v-for="(item, index) of characterSets"
                :key="index"
                :label="item"
                :value="item">
                <span>{{ item }}</span>
                <BkTag
                  v-if="sourceCharset && item === sourceCharset"
                  class="ml-5"
                  theme="info">
                  {{ t('源字符集') }}
                </BkTag>
              </BkOption>
            </BkSelect>
          </div>
        </BkFormItem>
      </DbCard>

      <!-- SQLServer 额外配置 -->
      <DbCard
        class="mt-16"
        mode="collapse"
        :title="t('绑定数据库配置')">
        <BkFormItem
          :label="t('操作系统版本')"
          property="operatingSystemVersion"
          required>
          <BkSelect
            v-model="formData.operatingSystemVersion"
            collapse-tags
            filterable
            multiple
            multiple-mode="tag"
            :placeholder="t('请选择操作系统版本')">
            <BkOption
              v-for="item in operatingSystemVersionList"
              :key="item"
              :label="item"
              :value="item" />
          </BkSelect>
        </BkFormItem>
        <BkFormItem
          :label="t('实例内存分配比率 (50~80%)')"
          property="memoryAllocationRatio"
          required>
          <div class="input-box">
            <BkInput
              v-model="formData.memoryAllocationRatio"
              class="num-input"
              :max="80"
              :min="50"
              :placeholder="t('请输入')"
              type="number" />
            <span class="unit-text">%</span>
          </div>
        </BkFormItem>
        <BkFormItem
          :label="t('最大系统保留内存')"
          property="maxSystemReservedMemory"
          required>
          <div class="input-box">
            <BkInput
              v-model="formData.maxSystemReservedMemory"
              class="num-input"
              disabled
              :min="1"
              :placeholder="t('请输入')"
              type="number" />
            <span class="unit-text">GB</span>
          </div>
        </BkFormItem>
        <BkFormItem
          :label="t('主从方式')"
          property="haMode"
          required>
          <BkRadioGroup
            v-model="formData.haMode"
            disabled>
            <BkRadio
              v-for="item in haModeList"
              :key="item.value"
              :label="item.value">
              {{ item.label }}
            </BkRadio>
          </BkRadioGroup>
        </BkFormItem>
      </DbCard>
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
        @click="handleCancel">
        {{ t('取消') }}
      </BkButton>
    </template>
  </SmartAction>

  <Teleport to="#dbContentTitleAppend">
    <span class="clone-nav-desc"> {{ t('业务') }}：{{ bizInfo.name }} </span>
    <span class="clone-nav-desc"> {{ t('源模块') }}：{{ String(route.query.module_name) || '--' }} </span>
  </Teleport>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { checkDbModuleUnique, createModules } from '@services/source/cmdb';
  import { saveModulesDeployInfo } from '@services/source/configs';
  import { listSqlserverSystemVersion } from '@services/source/version';

  import { useGlobalBizs } from '@stores';

  import { clusterTypeInfos, ClusterTypes, DBTypes } from '@common/const';

  import DbVersionSelect from './components/DbVersionSelect.vue';

  defineOptions({
    name: 'SelfServiceCloneSqlServer',
  });

  const { t } = useI18n();
  const router = useRouter();
  const route = useRoute();
  const globalBizsStore = useGlobalBizs();

  const clusterType = ref(route.query.cluster_type as ClusterTypes);
  const bizId = window.PROJECT_CONFIG.BIZ_ID;

  // 业务信息
  const bizInfo = computed(() => globalBizsStore.bizs.find((info) => info.bk_biz_id === bizId) || { name: '' });

  const isSubmitting = ref(false);

  const haModeList = [
    { label: t('镜像'), value: 'mirroring' },
    { label: 'always on', value: 'always_on' },
  ];

  const characterSets = ['Chinese_PRC_CI_AS', 'Latin1_General_100_CI_AS'];
  /** 源字符集（从路由取，由源模块列表页 moduleInfo.charset 传入） */
  const sourceCharset = ref<string>('');
  const isValueAllowed = ref(true);

  // 表单数据
  const getFormData = () => ({
    alias_name: '',
    charset: 'Chinese_PRC_CI_AS',
    haMode: 'mirroring',
    maxSystemReservedMemory: 32,
    memoryAllocationRatio: 80,
    operatingSystemVersion: [] as string[],
    version: '',
  });
  const formData = reactive(getFormData());
  const formRef = ref();

  /** 触发表单校验（版本或字符集 change 时） */
  const handleValidate = () => {
    formRef.value?.validate();
  };

  const rules = {
    alias_name: [
      {
        message: '',
        required: true,
        trigger: 'blur',
        validator: (value: string) => {
          if (value) return true;
          return '';
        },
      },
      {
        message: t('模块名格式不正确'),
        trigger: 'blur',
        validator: (value: string) => {
          if (/^[a-z0-9][a-z0-9-]*[a-z0-9]$/.test(value) || /^[a-z0-9]$/.test(value)) return true;
          isValueAllowed.value = false;
          return false;
        },
      },
      {
        message: t('模块名不能以连字符开头或结尾'),
        trigger: 'blur',
        validator: (value: string) => {
          if (!/^-|-$/.test(value[0]) && !/^-|-$/.test(value[value.length - 1])) return true;
          isValueAllowed.value = false;
          return false;
        },
      },
      {
        message: '',
        trigger: 'blur',
        async validator() {
          if (!formData.alias_name || !formData.version || !formData.charset) return true;
          try {
            const data = await checkDbModuleUnique({
              bk_biz_id: String(bizId),
              cluster_type: clusterType.value,
              db_module_name: `${formData.alias_name}`,
            });
            isValueAllowed.value = !!data.is_unique;
            return data.is_unique
              ? true
              : t('该名称已被占用（{type} ：{version}）', {
                  type: clusterTypeInfos[clusterType.value].name,
                  version: formData.version,
                });
          } catch {
            isValueAllowed.value = false;
            return false;
          }
        },
      },
    ],
  };

  // 操作系统版本列表
  const { data: operatingSystemVersionList, run: fetchSystemVersions } = useRequest(listSqlserverSystemVersion, {
    manual: true,
  });

  // 初始化：从路由回填源模块名
  if (route.query.module_name) {
    formData.alias_name = String(route.query.module_name);
  }
  // 源字符集从路由取（由源模块列表页 moduleInfo.charset 传入）
  if (route.query.charset) {
    sourceCharset.value = String(route.query.charset);
    formData.charset = String(route.query.charset);
  }

  // 版本变化时重新获取操作系统版本、更新主从方式
  watch(
    () => formData.version,
    (version) => {
      if (version) {
        formData.operatingSystemVersion = [];
        formData.haMode = Number(version.slice(-4)) > 2017 ? 'always_on' : 'mirroring';
        fetchSystemVersions({ sqlserver_version: version });
      }
    },
    { immediate: true },
  );

  // 初始化回填
  if (route.query.module_name) formData.alias_name = String(route.query.module_name);
  if (route.query.charset) formData.charset = String(route.query.charset);

  // 创建模块 + 绑定配置
  let latestModuleId = 0;

  /** 提交 */
  const handleSubmit = async () => {
    isSubmitting.value = true;
    try {
      await formRef.value?.validate();

      // 新建模块
      const createResult = await createModules({
        alias_name: formData.alias_name,
        biz_id: bizId,
        cluster_type: clusterType.value,
        db_module_name: formData.alias_name,
      });
      if (createResult.db_module_id) {
        latestModuleId = createResult.db_module_id;

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
              conf_value: formData.version,
              description: t('数据库版本'),
              op_type: 'update',
            },
            {
              conf_name: 'buffer_percent',
              conf_value: `${formData.memoryAllocationRatio}`,
              description: t('实际内存分配比率'),
              op_type: 'update',
            },
            {
              conf_name: 'max_remain_mem_gb',
              conf_value: String(formData.maxSystemReservedMemory),
              description: t('最大系统保留内存'),
              op_type: 'update',
            },
            {
              conf_name: 'sync_type',
              conf_value: formData.haMode,
              description: t('主从方式'),
              op_type: 'update',
            },
            {
              conf_name: 'system_version',
              conf_value: formData.operatingSystemVersion.map((v) => v.replace(/\s*/g, '')).join(','),
              description: t('操作系统版本'),
              op_type: 'update',
            },
          ],
          conf_type: 'deploy',
          level_name: 'module',
          level_value: createResult.db_module_id,
          meta_cluster_type: clusterType.value,
          version: 'deploy_info',
        });
      }

      window.changeConfirm = false;

      router.push({
        name: 'DbConfigureList',
        params: {
          clusterType: clusterType.value,
        },
        query: {
          parentId: `app-${bizId}`,
          treeId: latestModuleId ? `module-${latestModuleId}` : '',
        },
      });
    } catch (e) {
      console.log(e);
    }
    isSubmitting.value = false;
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
  .clone-module-page {
    height: 100%;
    padding-bottom: 20px;

    :deep(.bk-form-item) {
      max-width: 690px;
    }
  }

  .db-config-row {
    display: flex;
    align-items: center;
    gap: 12px;

    .version-select-inline,
    .charset-select-inline {
      width: auto;
      min-width: 160px;
    }

    .charset-select-inline {
      min-width: 140px;
    }
  }

  .db-type-tag {
    height: 30px;
    color: @primary-color;
    background: white;
    border: 1px solid @border-primary;
  }

  .form-item-tips {
    font-size: 12px;
    line-height: 20px;
    color: #979ba5;
    position: absolute;
  }

  .input-box {
    display: flex;
    align-items: center;
    width: 100%;

    .num-input {
      height: 32px;
    }

    .unit-text {
      margin-left: 12px;
      font-size: 12px;
      color: #63656e;
    }
  }

  .clone-nav-desc {
    position: relative;
    padding-left: 8px;
    margin-left: 8px;
    font-family: 'Microsoft YaHei', sans-serif;
    font-size: 14px;
    line-height: 22px;
    color: #979ba5;

    &::before {
      position: absolute;
      top: 50%;
      left: 0;
      width: 1px;
      height: 16px;
      content: '';
      background: #dcdee5;
      transform: translateY(-50%);
    }
  }

  .deprecated-sider-body {
    padding: 16px 20px;
  }
</style>
