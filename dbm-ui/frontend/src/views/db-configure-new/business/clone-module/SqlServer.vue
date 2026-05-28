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
        t('基于源模块创建新模块_常用于数据库版本升级_源模块自定义值将保留_新版本不兼容的参数将被废弃_请审慎后创建')
      " />
    <DbForm
      ref="formRef"
      class="clone-module-page db-scroll-y"
      :label-width="168"
      :model="formData"
      :rules="rules">
      <!-- 模块信息 -->
      <div class="module-info-card">
        <!-- 模块名 -->
        <BkFormItem
          class="form-item-name"
          :label="t('模块名称')"
          property="alias_name"
          required>
          <BkInput
            v-model="formData.alias_name"
            :placeholder="t('由英文字母_数字_连字符_组成')"
            @blur="handleValidate" />
          <div
            v-if="isValueAllowed"
            class="form-item-tips">
            {{ t('模块名由英文字母、数字、连字符-组成；同时也会参与集群域名生成') }}
          </div>
        </BkFormItem>
        <!-- 数据库信息 -->
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
              {{ ticketInfo.name }}
            </BkTag>
            <DbVersionSelect
              v-model="formData.version"
              class="version-select-inline"
              :db-type="DBTypes.SQLSERVER"
              :meta-cluster-type="ticketInfo.type"
              :source-version="String(route.query.conf_file || '')"
              @change="handleValidate" />
            <BkSelect
              v-model="formData.character_set"
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
      </div>

      <!-- 参数配置 Tab -->
      <div class="param-config-wrapper">
        <BkException
          v-if="!formData.version || confTabs.length === 0"
          :description="t('请先选择目标数据库版本')"
          scene="part"
          type="empty" />
        <template v-else>
          <BkTab
            :key="tabRenderKey"
            v-model:active="activeConfType"
            type="card-tab">
            <BkTabPanel
              v-for="tab of confTabs"
              :key="tab.conf_file"
              :name="tab.conf_file"
              render-directive="show">
              <template #label>
                {{ tab.name }}
              </template>
              <ParamTable
                :ref="(el: any) => setTableRef(tab.conf_file, el)"
                :deprecated-count="removedCount"
                @deprecated-click="handleShowDeprecated" />
            </BkTabPanel>
          </BkTab>
        </template>
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
        @click="handleCancel">
        {{ t('取消') }}
      </BkButton>
      <!-- 全 Tab 统计汇总 -->
      <template v-if="totalCounts.custom > 0 || totalCounts.changed > 0 || totalCounts.removed > 0">
        <span
          v-if="totalCounts.custom > 0"
          class="action-stat-chip custom ml-16">
          {{ t('自定义') }}<span class="stat-num">{{ totalCounts.custom }}</span>
        </span>
        <span
          v-if="totalCounts.changed > 0"
          class="action-stat-chip changed">
          {{ t('参数值变化') }}<span class="stat-num">{{ totalCounts.changed }}</span>
        </span>
        <span
          v-if="totalCounts.removed > 0"
          class="action-stat-chip removed"
          @click="handleShowDeprecated">
          {{ t('已废弃') }}<span class="stat-num">{{ totalCounts.removed }}</span>
        </span>
      </template>
    </template>
  </SmartAction>

  <!-- 废弃参数侧滑 -->
  <BkSideslider
    :is-show="isShowSlider"
    quick-close
    width="600px"
    @closed="isShowSlider = false">
    <template #header>
      {{ t('废弃参数详情') }}
      <span class="sideslider-sub-title">
        {{ activeConfType }}：{{ t('共n个参数将不进入新模块', { n: deprecatedItems.length }) }}
      </span>
    </template>
    <div class="deprecated-sider-body">
      <DbTable
        ref="sliderTableRef"
        :data-source="deprecatedDataSource"
        row-key="conf_name">
        <TableColumn
          col-key="conf_name"
          :min-width="300"
          :title="t('参数名')" />
      </DbTable>
    </div>
  </BkSideslider>

  <Teleport to="#dbContentTitleAppend">
    <span class="clone-nav-desc"> {{ t('业务') }}：{{ bizInfo.name }} </span>
    <span class="clone-nav-desc">
      {{ t('源模块') }}：{{ cloneResult.conf_file_info?.conf_file || String(route.query.conf_file) || '--' }}
    </span>
  </Teleport>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { checkDbModuleUnique, createModules } from '@services/source/cmdb';
  import {
    type CloneConfItem,
    type CloneModuleQueryResult,
    getListClusterModuleConfFiles,
    moduleCloneQuery,
    saveModulesDeployInfo,
  } from '@services/source/configs';

  import { useGlobalBizs } from '@stores';

  import { DBTypes, sqlServerType, type SqlServerTypeString } from '@common/const';

  import DbIcon from '@components/db-icon/';
  import DbTable from '@components/db-table/IndexNew.vue';

  import { random } from '@utils';

  import DbVersionSelect from './components/DbVersionSelect.vue';
  import ParamTable from './components/ParamTable.vue';

  defineOptions({
    name: 'SelfServiceCloneSqlServer',
  });

  const { t } = useI18n();
  const router = useRouter();
  const route = useRoute();
  const globalBizsStore = useGlobalBizs();

  const ticketInfo = sqlServerType[route.params.ticketType as SqlServerTypeString];
  const bizId = window.PROJECT_CONFIG.BIZ_ID;

  // 业务信息
  const bizInfo = computed(() => globalBizsStore.bizs.find((info) => info.bk_biz_id === bizId) || { name: '' });

  const isSubmitting = ref(false);
  const tableRefs = ref<Record<string, InstanceType<typeof ParamTable>>>({});
  const currentParamTable = computed(() => tableRefs.value[activeConfType.value]);
  const setTableRef = (name: string, el: any) => {
    if (el) tableRefs.value[name] = el;
  };

  // 表单数据
  const formData = reactive({
    alias_name: '',
    character_set: 'Chinese_PRC_CI_AS',
    version: '',
  });
  const formRef = ref();
  const sliderTableRef = ref();
  const sourceCharset = ref<string>('');
  const isShowSlider = ref(false);
  const activeConfType = ref('dbconf');
  const tabRenderKey = ref(random());
  const confTabs = ref<ServiceReturnType<typeof getListClusterModuleConfFiles>>([]);

  const characterSets = ['Chinese_PRC_CI_AS', 'Latin1_General_100_CI_AS'];
  const isValueAllowed = ref(true);

  /** 触发表单校验 */
  const handleValidate = () => {
    formRef.value?.validate();
  };

  // 模块名校验规则
  const rules = {
    alias_name: [
      {
        message: t('模块名称不能为空'),
        required: true,
        trigger: 'blur',
        validator: (value: string) => {
          if (value) return true;
          isValueAllowed.value = false;
          return false;
        },
      },
      {
        message: t('由英文字母_数字_连字符_组成'),
        trigger: 'blur',
        validator: (value: string) => {
          if (/^[0-9a-zA-Z-]+$/.test(value)) return true;
          isValueAllowed.value = false;
          return false;
        },
      },
      {
        message: t('该模块名已存在'),
        trigger: 'blur',
        async validator() {
          if (!formData.alias_name || !formData.version || !formData.character_set) return true;
          try {
            const data = await checkDbModuleUnique({
              bk_biz_id: String(bizId),
              cluster_type: ticketInfo.type,
              db_module_name: `${formData.alias_name}`,
            });
            isValueAllowed.value = !!data.is_unique;
            return data.is_unique;
          } catch {
            isValueAllowed.value = false;
            return false;
          }
        },
      },
    ],
  };

  // 克隆查询原始结果
  const cloneResult = ref<CloneModuleQueryResult>({
    bk_biz_id: '',
    conf_file_info: {
      conf_file: '',
      conf_file_lc: '',
      conf_type: '',
      conf_type_lc: '',
      created_at: '',
      description: '',
      namespace: '',
      namespace_info: '',
      updated_at: '',
      updated_by: '',
    },
    conf_names_deprecated: null,
    conf_names_value_diff: {},
    conf_names_value_modified: null,
    content: {},
    level_name: '',
    level_value: '',
  });

  const currentConfItems = computed<CloneConfItem[]>(() => {
    if (!cloneResult.value.content) return [];
    const modifiedSet = new Set(cloneResult.value.conf_names_value_modified || []);
    const diffMap = cloneResult.value.conf_names_value_diff || {};
    return Object.values(cloneResult.value.content).map((item) => {
      const diffValue = (diffMap as Record<string, string>)[item.conf_name];
      const isInDiff = diffValue !== undefined;
      return {
        ...item,
        diff_type: !isInDiff ? 'none' : diffValue === '_NONE_' ? 'new' : 'changed',
        source_conf_value: diffValue && diffValue !== '_NONE_' ? diffValue : undefined,
        value_source: modifiedSet.has(item.conf_name) ? 'custom' : 'source',
      };
    });
  });

  const totalCounts = computed(() => {
    const items = currentConfItems.value;
    return {
      changed: items.filter((i) => i.diff_type === 'changed' || i.diff_type === 'new').length,
      custom: items.filter((i) => i.value_source === 'custom').length,
      removed: deprecatedNames.value.length,
    };
  });

  const removedCount = computed(() => deprecatedNames.value.length);
  const deprecatedNames = computed(() => cloneResult.value.conf_names_deprecated || []);
  const deprecatedItems = computed<CloneConfItem[]>(() =>
    deprecatedNames.value.map((name) => {
      const item = cloneResult.value.content[name];
      return item
        ? { ...item, diff_type: 'removed' as const, value_source: 'source' as const }
        : ({
            conf_name: name,
            conf_value: '',
            description: '',
            diff_type: 'removed' as const,
            flag_disable: 0,
            flag_locked: 0,
            level_name: 'plat',
            level_value: '',
            op_type: '',
            stage: 0,
            up_level_value: null,
            value_source: 'source' as const,
          } satisfies CloneConfItem);
    }),
  );
  const deprecatedDataSource = () =>
    Promise.resolve({ count: deprecatedItems.value.length, results: deprecatedItems.value });

  const { run: fetchCloneResult } = useRequest(moduleCloneQuery, {
    manual: true,
    onSuccess(res) {
      cloneResult.value = res;
      nextTick(() => currentParamTable.value?.refreshData());
    },
  });

  const { run: fetchConfTabs } = useRequest(getListClusterModuleConfFiles, {
    manual: true,
    onSuccess(rawConfTabs) {
      const tabs = rawConfTabs || [];
      tabs[0] = { conf_file: formData.version, conf_type: 'dbconf', name: formData.version };
      confTabs.value = tabs;
      tabRenderKey.value = random();
    },
  });

  // 初始化回填
  if (route.query.module_name) formData.alias_name = String(route.query.module_name);
  if (route.query.conf_file) cloneResult.value.conf_file_info.conf_file = String(route.query.conf_file);
  if (route.query.charset) sourceCharset.value = String(route.query.charset);

  watch(
    () => formData.version,
    () => {
      fetchConfTabs({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        deploy_versions: JSON.stringify({ db_version: formData.version }),
        meta_cluster_type: ticketInfo.type,
      });
      fetchCloneResult({
        conf_type: 'dbconf',
        meta_cluster_type: ticketInfo.type,
        source_bk_biz_id: String(bizId),
        source_conf_file: String(route.query.conf_file || ''),
        source_module_id: String(route.query.module_id || ''),
        target_bk_biz_id: String(bizId),
        target_conf_file: formData.version,
      });
    },
  );

  watch(
    currentConfItems,
    (items) => {
      nextTick(() => currentParamTable.value?.setData(items));
    },
    { immediate: true },
  );

  nextTick(() => {
    if (currentConfItems.value.length) currentParamTable.value?.setData(currentConfItems.value);
  });

  const handleShowDeprecated = () => {
    isShowSlider.value = true;
    nextTick(() => sliderTableRef.value?.fetchData());
  };

  /** 提交 */
  const handleSubmit = async () => {
    try {
      await formRef.value?.validate();
      isSubmitting.value = true;

      const createResult = await createModules({
        alias_name: formData.alias_name,
        biz_id: Number(bizId),
        cluster_type: ticketInfo.type,
        db_module_name: formData.alias_name,
      });

      await saveModulesDeployInfo({
        bk_biz_id: Number(bizId),
        conf_items: [
          { conf_name: 'charset', conf_value: formData.character_set, description: t('字符集'), op_type: 'update' },
          { conf_name: 'db_version', conf_value: formData.version, description: t('数据库版本'), op_type: 'update' },
        ],
        conf_type: 'deploy',
        level_name: 'module',
        level_value: createResult.db_module_id,
        meta_cluster_type: ticketInfo.type,
        version: 'deploy_info',
      });

      window.changeConfirm = false;
      router.push({
        name: 'DbConfigureList',
        params: { clusterType: ticketInfo.type },
        query: { parentId: `app-${bizId}`, treeId: `module-${createResult.db_module_id}` },
      });
    } catch (e) {
      console.error(e);
    }
    isSubmitting.value = false;
  };

  const handleCancel = () => routerBack();

  const routerBack = () => {
    router.push({
      name: String(route.query.from || 'serviceApply'),
      params: { clusterType: ticketInfo.type },
    });
  };

  defineExpose({ routerBack });
</script>

<style lang="less" scoped>
  .clone-module-page {
    height: 100%;
    padding-bottom: 20px;

    :deep(.bk-form-item) {
      max-width: 690px;
    }
  }

  .module-info-card {
    padding: 24px;
    background: #fff;
    border-radius: 2px;
  }

  .db-config-row {
    display: flex;
    align-items: center;
    gap: 12px;

    .version-select-inline {
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
    margin-top: 4px;
    font-size: 12px;
    line-height: 20px;
    color: #979ba5;
  }

  .param-config-wrapper {
    margin-top: 16px;
    background: #fff;

    :deep(.bk-tab-content) {
      padding: 16px 16px 0;
    }
  }

  .sideslider-sub-title {
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
      height: 14px;
      content: '';
      background: #dcdee5;
      transform: translateY(-50%);
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

  .action-stat-chip {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 8px;
    font-size: 12px;
    line-height: 18px;
    color: #63656e;

    .stat-num {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 18px;
      height: 18px;
      padding: 0 5px;
      border-radius: 9px;
      font-size: 11px;
      font-weight: 600;
      color: #fff;
    }

    &.custom .stat-num {
      background: #f59500;
    }

    &.changed .stat-num {
      background: #3a84ff;
    }

    &.removed {
      cursor: pointer;

      .stat-num {
        background: #ea3636;
      }
    }
  }

  .deprecated-sider-body {
    padding: 16px 20px;
  }
</style>
