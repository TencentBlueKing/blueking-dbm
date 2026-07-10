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
      :label-width="100"
      :model="formData"
      :rules="rules"
      :scroll-align-to-top="false">
      <!-- 模块信息 -->
      <div class="module-info-card">
        <!-- 模块名称 -->
        <FormItemWithHint
          class="form-item-name"
          :label="t('模块名称')"
          :model="formData.alias_name"
          property="alias_name"
          required
          :rules="rules.alias_name">
          <template #hint>
            {{ t('仅支持小写字母、数字、连字符，同时会参与集群域名生成，') }}
            <span class="hint-warning">{{ t('创建后不可改') }}</span>
          </template>
          <div class="module-name-row">
            <BkInput
              v-model="formData.alias_name"
              class="module-name-input"
              :maxlength="63"
              :placeholder="t('请输入模块名')"
              show-word-limit
              @change="handleValidate" />
            <DomainPreview :module-name="formData.alias_name" />
          </div>
        </FormItemWithHint>
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
              {{ clusterTypeInfos[clusterType]?.name }}
            </BkTag>
            <FormItemWithHint
              class="custom-form-item version-select-inline"
              property="version"
              required
              :show-label="false">
              <DbVersionSelect
                v-model="formData.version"
                :db-type="DBTypes.SQLSERVER"
                :source-version="String(route.query.confFile || '')"
                @change="handleValidate" />
            </FormItemWithHint>
            <BkInput
              class="ha-mode-input"
              disabled
              :model-value="haModeDisplay"
              :prefix="t('主从方式')" />
            <FormItemWithHint
              class="custom-form-item charset-select-inline"
              property="character_set"
              required
              :show-label="false">
              <BkSelect
                v-model="formData.character_set"
                :clearable="false"
                filterable
                :placeholder="t('请选择')"
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
            </FormItemWithHint>
          </div>
        </BkFormItem>
        <!-- 部署规格 -->
        <BkFormItem
          :label="t('部署规格')"
          required>
          <div class="db-config-row">
            <FormItemWithHint
              class="custom-form-item os-version-select-inline"
              property="operatingSystemVersion"
              required
              :show-label="false">
              <BkSelect
                v-model="formData.operatingSystemVersion"
                filterable
                multiple
                :placeholder="t('请选择（可多选）')"
                :prefix="t('操作系统版本')">
                <BkOption
                  v-for="item in operatingSystemVersionList"
                  :key="item"
                  :label="item"
                  :value="item" />
              </BkSelect>
            </FormItemWithHint>
            <FormItemWithHint
              class="custom-form-item memory-allocation-ratio-input"
              property="memoryAllocationRatio"
              required
              :show-label="false">
              <BkInput
                v-model="formData.memoryAllocationRatio"
                :max="80"
                :min="50"
                :prefix="t('内存分配比率')"
                suffix="%"
                type="number" />
            </FormItemWithHint>
            <FormItemWithHint
              class="custom-form-item reserved-memory-input"
              property="maxSystemReservedMemory"
              required
              :show-label="false">
              <BkInput
                v-model="formData.maxSystemReservedMemory"
                class="reserved-memory-input"
                disabled
                :min="1"
                :prefix="t('最大 OS 保留内存')"
                suffix="GB"
                type="number" />
            </FormItemWithHint>
          </div>
        </BkFormItem>
      </div>

      <!-- 参数配置 — 克隆对比模式 -->
      <div class="param-config-wrapper mt-16">
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
                <span
                  v-if="(tabChangedCountMap[tab.conf_file] ?? 0) > 0"
                  class="tab-modified-dot" />
              </template>
              <!-- 首个 Tab（dbconf）：克隆对比模式，含 diff/废弃 -->
              <ParamTable
                v-if="tab.conf_type === 'dbconf'"
                :ref="(el: any) => setTableRef(tab.conf_file, el)"
                :deprecated-count="removedCount"
                @deprecated-click="handleShowDeprecated" />
              <!-- 其他 Tab：层级配置模式，仅自定义过滤 -->
              <LevelConfigTable
                v-else
                :ref="(el: any) => setTableRef(tab.conf_file, el)" />
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
  <DbSideslider
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
  </DbSideslider>

  <Teleport to="#dbContentTitleAppend">
    <span class="clone-module-meta">
      <span> {{ t('业务') }}：{{ bizInfo.name || '--' }} </span>
      <span> {{ t('源模块') }}：{{ String(route.query.moduleName) || '--' }} </span>
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
    getLevelConfig,
    getListClusterModuleConfFiles,
    moduleCloneQuery,
    saveModulesDeployInfo,
  } from '@services/source/configs';
  import { listSqlserverSystemVersion } from '@services/source/version';

  import { useGlobalBizs } from '@stores';

  import { clusterTypeInfos, ClusterTypes, DBTypes } from '@common/const';

  import DbTable from '@components/db-table/IndexNew.vue';
  import FormItemWithHint from '@components/form-item-with-hint/Index.vue';

  import DomainPreview from '@views/db-configure/components/DomainPreview.vue';
  import { saveConfigureState } from '@views/db-configure/utils/configureState';

  import { random } from '@utils';

  import DbVersionSelect from '../components/DbVersionSelect.vue';
  import LevelConfigTable from '../components/LevelConfigTable.vue';
  import ParamTable from '../components/ParamTable.vue';

  type Emits = (e: 'routerBack') => void;

  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const router = useRouter();
  const route = useRoute();
  const globalBizsStore = useGlobalBizs();

  const clusterType = ref(route.params.clusterType as ClusterTypes);
  const bizId = window.PROJECT_CONFIG.BIZ_ID;

  // 业务信息
  const bizInfo = computed(() => globalBizsStore.bizs.find((info) => info.bk_biz_id === bizId) || { name: '' });

  const isSubmitting = ref(false);

  const characterSets = ['Chinese_PRC_CI_AS', 'Latin1_General_100_CI_AS'];

  /** 源字符集（从路由取，由源模块列表页 moduleInfo.charset 传入） */
  const sourceCharset = ref<string>('');

  // 表单数据（与新建模块保持一致）
  const getFormData = () => ({
    alias_name: '',
    character_set: 'Chinese_PRC_CI_AS',
    haMode: 'mirroring',
    maxSystemReservedMemory: 32,
    memoryAllocationRatio: 80,
    operatingSystemVersion: [] as string[],
    version: '',
  });
  const formData = reactive(getFormData());
  const formRef = ref();

  const haModeDisplay = computed(() => (formData.haMode === 'mirroring' ? t('镜像') : 'always on'));

  /** 触发表单校验（版本或字符集 change 时） */
  const handleValidate = () => {
    formRef.value?.validate();
  };

  const rules = {
    alias_name: [
      {
        message: t('格式不正确_请勿使用中文_大写字母_空格_下划线或特殊符号'),
        trigger: 'blur',
        validator: (value: string) => {
          if (/^[a-z0-9-]+$/.test(value)) {
            return true;
          }
          return false;
        },
      },
      {
        message: t('不能以连字符开头或结尾'),
        trigger: 'blur',
        validator: (value: string) => {
          if (/^(?!-).*(?<!-)$/.test(value)) {
            return true;
          }
          return false;
        },
      },
      {
        message: '',
        trigger: 'blur',
        async validator() {
          if (!formData.alias_name || !formData.version || !formData.character_set) return true;
          try {
            const data = await checkDbModuleUnique({
              bk_biz_id: String(bizId),
              cluster_type: clusterType.value,
              db_module_name: `${formData.alias_name}`,
            });
            return data.is_unique
              ? true
              : t('该名称已被占用（{type} ：{version}）', {
                  type: clusterTypeInfos[clusterType.value].name,
                  version: formData.version,
                });
          } catch {
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

  // 版本变化时重新获取操作系统版本、更新主从方式
  watch(
    () => formData.version,
    (version) => {
      if (version) {
        formData.haMode = Number(version.slice(-4)) > 2017 ? 'always_on' : 'mirroring';
        fetchSystemVersions({ sqlserver_version: version });
      }
    },
    { immediate: true },
  );

  // 初始化：从路由回填源模块信息
  if (route.query.moduleName) {
    formData.alias_name = String(route.query.moduleName);
  }
  // 源字符集从路由取（由源模块列表页 moduleInfo.charset 传入）
  if (route.query.charset) {
    sourceCharset.value = String(route.query.charset);
    formData.character_set = String(route.query.charset);
  }

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

  /** 将 content 对象转为数组，并标注 value_source 和 diff_type */
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

  // 参数配置 Tab
  const activeConfType = ref('dbconf');
  const tabRenderKey = ref(random());
  const confTabs = ref<ServiceReturnType<typeof getListClusterModuleConfFiles>>([]);

  // 每个 confFile 对应一个 Table 实例
  const tableRefs = ref<Record<string, any>>({});
  const setTableRef = (name: string, el: any) => {
    if (el) {
      tableRefs.value[name] = el;
    }
  };

  /** 所有 Tab 的总计已修改数量（用于 Tab 小黄点） */
  const tabChangedCountMap = computed(() => {
    const map: Record<string, number> = {};
    confTabs.value.forEach((tab) => {
      if (tab.conf_type === 'dbconf') {
        const tableRef = tableRefs.value[tab.conf_file];
        map[tab.conf_file] = tableRef?.changedCount ?? 0;
      } else {
        map[tab.conf_file] = 0;
      }
    });
    return map;
  });

  /** 全 Tab 汇总统计（用于底部操作栏展示） */
  const totalCounts = computed(() => {
    const items = currentConfItems.value;
    return {
      changed: items.filter((i) => i.diff_type === 'changed' || i.diff_type === 'new').length,
      custom: items.filter((i) => i.value_source === 'custom').length,
      removed: deprecatedNames.value.length,
    };
  });

  /** 废弃数量 */
  const removedCount = computed(() => deprecatedNames.value.length);

  /** 废弃参数名列表 */
  const deprecatedNames = computed(() => cloneResult.value.conf_names_deprecated || []);

  /** 废弃参数列表（用于侧滑展示） */
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

  /** 废弃侧滑数据源 */
  const deprecatedDataSource = () =>
    Promise.resolve({ count: deprecatedItems.value.length, results: deprecatedItems.value });

  const sliderTableRef = ref();
  const isShowSlider = ref(false);

  /** 获取克隆对比结果 */
  const { run: fetchCloneResult } = useRequest(moduleCloneQuery, {
    manual: true,
    onSuccess(res) {
      cloneResult.value = res;
      nextTick(() => {
        const currentTable = tableRefs.value[activeConfType.value];
        currentTable?.refreshData?.();
      });
    },
  });

  /** 获取配置文件 Tab 列表 */
  const { run: fetchConfTabs } = useRequest(getListClusterModuleConfFiles, {
    manual: true,
    onSuccess(res) {
      const rawConfTabs = res || [];
      if (formData.version) {
        Object.assign(rawConfTabs[0], { conf_file: formData.version, conf_type: 'dbconf', name: formData.version });
      }
      confTabs.value = rawConfTabs;
      tabRenderKey.value = random();
    },
  });

  /** 获取非 dbconf Tab 的层级配置数据 */
  const { run: fetchLevelConfig } = useRequest(getLevelConfig, {
    manual: true,
    onSuccess(res) {
      const items: CloneConfItem[] = (res.conf_items || []).map((item) => ({
        conf_name: item.conf_name,
        conf_value: item.conf_value ?? '',
        description: item.description || '',
        diff_type: 'none' as const,
        flag_disable: item.flag_disable ?? 0,
        flag_encrypt: item.flag_encrypt ?? 0,
        flag_locked: item.flag_locked ?? 0,
        flag_readonly: item.flag_readonly ?? 0,
        flag_visible: item.flag_visible ?? 1,
        level_name: (item.level_name as any) || 'plat',
        level_value: item.leval_value ?? '',
        need_restart: item.need_restart ?? 0,
        op_type: item.op_type || '',
        source_conf_value: undefined,
        stage: 0,
        up_level_value: null,
        value_allowed: item.value_allowed || '',
        value_default: item.value_default || '',
        value_source: 'source' as const,
        value_type: item.value_type || 'STRING',
        value_type_sub: item.value_type_sub || '',
      }));
      nextTick(() => {
        const currentTable = tableRefs.value[activeConfType.value];
        currentTable?.setData?.(items);
      });
    },
  });

  // 版本变化时：刷新 Tab 列表 + 重新拉取参数对比结果
  watch(
    () => formData.version,
    () => {
      if (!formData.version) return;
      fetchConfTabs({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        deploy_versions: JSON.stringify({ db_version: formData.version }),
        meta_cluster_type: clusterType.value,
      });
      fetchCloneResult({
        conf_type: 'dbconf',
        meta_cluster_type: clusterType.value,
        source_bk_biz_id: String(bizId),
        source_conf_file: String(route.query.confFile || ''),
        source_module_id: String(route.query.moduleId || ''),
        target_bk_biz_id: String(bizId),
        target_conf_file: formData.version,
      });
    },
  );

  // 克隆对比结果变化时，刷新当前 Tab 的表格数据
  watch(
    currentConfItems,
    (items) => {
      nextTick(() => {
        const currentTable = tableRefs.value[activeConfType.value];
        currentTable?.setData?.(items);
      });
    },
    { immediate: true },
  );

  /** Tab 切换时：非 dbconf 调用 getLevelConfig */
  watch(activeConfType, (tabKey) => {
    const currentTab = confTabs.value.find((t) => t.conf_file === tabKey);
    if (!currentTab || currentTab.conf_type === 'dbconf') return;

    fetchLevelConfig({
      bk_biz_id: Number(bizId),
      conf_type: currentTab.conf_type,
      level_name: 'module',
      level_value: String(route.query.moduleId || ''),
      meta_cluster_type: clusterType.value,
      version: tabKey,
    });
  });

  // 显示废弃参数侧滑
  const handleShowDeprecated = () => {
    isShowSlider.value = true;
    nextTick(() => {
      sliderTableRef.value?.fetchData?.();
    });
  };

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

        // 绑定数据库配置（部署规格）
        await saveModulesDeployInfo({
          bk_biz_id: bizId,
          conf_items: [
            {
              conf_name: 'charset',
              conf_value: formData.character_set,
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

        // 绑定各 tab 参数配置（克隆模式：仅提交有变化的 ParamTable）
        const bindTasks = Object.values(tableRefs.value)
          .filter((ref) => ref?.hasChange?.())
          .map((ref) => ref.bindConfigParameters?.());
        await Promise.all(bindTasks);
      }

      window.changeConfirm = false;

      // 保存选中的树节点状态，确保跳转后树能自动选中新模块
      saveConfigureState({
        selectedParentId: `app-${bizId}`,
        selectedTreeId: latestModuleId ? `module-${latestModuleId}` : '',
      });

      router.push({
        name: 'DbConfigureList',
        params: {
          clusterType: clusterType.value,
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
    emits('routerBack');
  };
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
    box-shadow: 0 2px 4px 0 rgb(25 25 41 / 5%);
  }

  .form-item-name {
    :deep(.hint-warning) {
      color: rgb(255, 156, 1);
    }
  }

  .module-name-row {
    display: flex;
    align-items: center;

    .module-name-input {
      width: 420px;
      flex-shrink: 0;
    }
  }

  .db-config-row {
    display: flex;
    flex-wrap: nowrap;
    align-items: center;
    gap: 12px;
    width: 100%;
    min-width: 0;

    > *:not(.db-type-tag) {
      min-width: 140px;
    }

    .db-type-tag {
      height: 32px;
      min-width: 140px;
      color: @primary-color;
      background: white;
      border: 1px solid @border-primary;
      flex: 0 0 auto;
      justify-content: center;
    }

    .version-select-inline {
      min-width: 268px;
    }

    .ha-mode-input {
      min-width: 180px;
    }

    .charset-select-inline {
      min-width: 220px;
    }

    .os-version-select-inline {
      min-width: 420px;
    }

    .memory-allocation-ratio-input {
      min-width: 180px;
    }

    .reserved-memory-input {
      min-width: 220px;
    }

    .custom-form-item {
      margin-bottom: 0;

      :deep(.bk-form-content) {
        margin-bottom: 0;
      }
    }
  }

  .param-config-wrapper {
    margin-top: 16px;
    background: #fff;
    border-radius: 2px;
    box-shadow: 0 2px 4px 0 rgb(25 25 41 / 5%);

    :deep(.bk-tab-content) {
      padding: 16px 16px 0;
    }
  }

  .tab-modified-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    margin-left: 4px;
    background: #f59500;
    border-radius: 50%;
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
      height: 18px;
      min-width: 18px;
      padding: 0 5px;
      font-size: 11px;
      font-weight: 600;
      color: #fff;
      border-radius: 9px;
      align-items: center;
      justify-content: center;
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
      height: 16px;
      background: #dcdee5;
      content: '';
      transform: translateY(-50%);
    }
  }

  .clone-module-meta {
    display: inline-flex;
    margin-left: 8px;
    font-size: 14px;
    color: #979ba5;
    align-items: center;
    gap: 8px;

    & > span + span {
      margin-left: 8px;
    }

    &::before {
      display: inline-block;
      width: 1px;
      height: 14px;
      background: #dcdee5;
      content: '';
    }
  }

  .deprecated-sider-body {
    padding: 16px 20px;
  }
</style>
