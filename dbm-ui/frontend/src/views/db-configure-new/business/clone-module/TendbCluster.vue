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
            :maxlength="63"
            :placeholder="t('请输入模块名')"
            show-word-limit />
          <div
            v-if="isValueAllowed"
            class="form-item-tips">
            {{ t('仅支持小写字母、数字、连字符，同时会参与集群域名生成，创建后不可改') }}
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
                <i class="db-icon-mysql mr-5" />
              </template>
              TenDBCluster
            </BkTag>
            <DbVersionSelect
              v-model="formData.db_version"
              class="version-select-inline"
              :db-type="DBTypes.MYSQL"
              :source-version="String(route.query.conf_file || '')"
              @change="handleValidate" />
            <DbVersionSelect
              v-model="formData.spider_version"
              class="version-select-inline"
              :db-type="DBTypes.MYSQL"
              :placeholder="t('请选择xx', [t('接入层版本')])"
              :prefix="t('接入层版本')"
              query-key="spider"
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
      </div>

      <!-- 参数配置 Tab -->
      <div class="param-config-wrapper">
        <BkException
          v-if="!formData.db_version || confTabs.length === 0"
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
    <span class="clone-nav-desc"> {{ t('源模块') }}：{{ String(route.query.module_name) || '--' }} </span>
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

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, DBTypes } from '@common/const';

  import DbTable from '@components/db-table/IndexNew.vue';

  import { random } from '@utils';

  import DbVersionSelect from './components/DbVersionSelect.vue';
  import LevelConfigTable from './components/LevelConfigTable.vue';
  import ParamTable from './components/ParamTable.vue';

  defineOptions({
    name: 'SelfServiceCloneTendbCluster',
  });

  const { t } = useI18n();
  const router = useRouter();
  const route = useRoute();
  const globalBizsStore = useGlobalBizs();

  const bizId = window.PROJECT_CONFIG.BIZ_ID;

  // 业务信息
  const bizInfo = computed(() => globalBizsStore.bizs.find((info) => info.bk_biz_id === bizId) || { name: '' });

  const isSubmitting = ref(false);
  // 每个 confFile 对应一个 ParamTable 实例
  const tableRefs = ref<Record<string, InstanceType<typeof ParamTable>>>({});
  /** 当前活跃 Tab 对应的 ParamTable 实例 */
  const currentParamTable = computed(() => tableRefs.value[activeConfType.value]);
  const setTableRef = (name: string, el: any) => {
    if (el) {
      tableRefs.value[name] = el;
    }
  };

  // 表单数据
  const formData = reactive({
    alias_name: '',
    charset: '',
    db_version: '',
    spider_version: '',
  });
  const formRef = ref();
  const sliderTableRef = ref();
  /** 源字符集（从路由取） */
  const sourceCharset = ref<string>('');
  const isShowSlider = ref(false);
  // 当前活跃 Tab
  const activeConfType = ref('dbconf');
  const tabRenderKey = ref(random());
  const confTabs = ref<ServiceReturnType<typeof getListClusterModuleConfFiles>>([]);

  const characterSets = ['utf8', 'utf8mb4', 'gbk', 'latin1', 'gb2312'];

  const isValueAllowed = ref(true);

  /** 触发表单校验（版本或字符集 change 时） */
  const handleValidate = () => {
    formRef.value?.validate();
  };

  // 模块名校验规则
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
          if (!formData.alias_name || !formData.db_version || !formData.spider_version || !formData.charset)
            return true;
          try {
            const data = await checkDbModuleUnique({
              bk_biz_id: String(bizId),
              cluster_type: ClusterTypes.TENDBCLUSTER,
              db_module_name: `${formData.alias_name}-${formData.spider_version}-${formData.db_version}-${formData.charset}`,
            });
            isValueAllowed.value = !!data.is_unique;
            return data.is_unique
              ? true
              : t('该名称已被占用（{type} ：{spiderVersion}-{version} / {charset}）', {
                  charset: formData.charset,
                  spiderVersion: formData.spider_version,
                  type: 'TenDBCluster',
                  version: formData.db_version,
                });
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

  /** 全 Tab 汇总统计 */
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

  /** 获取克隆对比结果 */
  const { run: fetchCloneResult } = useRequest(moduleCloneQuery, {
    manual: true,
    onSuccess(res) {
      cloneResult.value = res;
      nextTick(() => currentParamTable.value?.refreshData());
    },
  });

  /** 获取配置文件 Tab 列表 */
  const { run: fetchConfTabs } = useRequest(getListClusterModuleConfFiles, {
    manual: true,
    onSuccess(rawConfTabs) {
      const tabs = rawConfTabs || [];
      tabs[0] = { conf_file: formData.db_version, conf_type: 'dbconf', name: formData.db_version };
      tabs[1] = {
        conf_file: formData.spider_version,
        conf_type: 'proxyconf',
        name: formData.spider_version,
      };
      confTabs.value = tabs;
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
      nextTick(() => currentParamTable.value?.setData(items));
    },
  });

  // 初始化：从路由回填源模块名
  if (route.query.module_name) {
    formData.alias_name = String(route.query.module_name);
  }
  if (route.query.conf_file) {
    cloneResult.value.conf_file_info.conf_file = String(route.query.conf_file);
  }
  if (route.query.charset) {
    sourceCharset.value = String(route.query.charset);
  }

  // 版本变化时：刷新 Tab 列表 + 重新拉取参数对比结果
  watch(
    () => [formData.db_version, formData.spider_version],
    () => {
      fetchConfTabs({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        deploy_versions: JSON.stringify({ db_version: formData.db_version }),
        meta_cluster_type: ClusterTypes.TENDBCLUSTER,
      });
      fetchCloneResult({
        conf_type: 'dbconf',
        meta_cluster_type: ClusterTypes.TENDBCLUSTER,
        source_bk_biz_id: String(bizId),
        source_conf_file: String(route.query.conf_file || ''),
        source_module_id: String(route.query.module_id || ''),
        target_bk_biz_id: String(bizId),
        target_conf_file: formData.db_version,
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

  /** Tab 切换时：非 dbconf 调用 getLevelConfig */
  watch(activeConfType, (tabKey) => {
    const currentTab = confTabs.value.find((t) => t.conf_file === tabKey);
    if (!currentTab || currentTab.conf_type === 'dbconf') return;

    fetchLevelConfig({
      bk_biz_id: Number(bizId),
      conf_type: currentTab.conf_type,
      level_name: 'module',
      level_value: String(route.query.module_id || ''),
      meta_cluster_type: ClusterTypes.TENDBCLUSTER,
      version: tabKey,
    });
  });

  // 初始化首屏数据（dbconf）
  nextTick(() => {
    if (currentConfItems.value.length) {
      currentParamTable.value?.setData(currentConfItems.value);
    }
  });

  // 显示废弃参数侧滑
  const handleShowDeprecated = () => {
    isShowSlider.value = true;
    nextTick(() => {
      sliderTableRef.value?.fetchData();
    });
  };

  /** 提交 */
  const handleSubmit = async () => {
    try {
      await formRef.value?.validate();

      isSubmitting.value = true;

      // 创建模块
      const dbModuleName = `${formData.alias_name}-${formData.spider_version}-${formData.db_version}-${formData.charset}`;
      const createResult = await createModules({
        alias_name: formData.alias_name,
        biz_id: Number(bizId),
        cluster_type: ClusterTypes.TENDBCLUSTER,
        db_module_name: dbModuleName,
      });

      // 绑定部署信息
      await saveModulesDeployInfo({
        bk_biz_id: Number(bizId),
        conf_items: [
          { conf_name: 'charset', conf_value: formData.charset, description: t('字符集'), op_type: 'update' },
          { conf_name: 'db_version', conf_value: formData.db_version, description: t('数据库版本'), op_type: 'update' },
          {
            conf_name: 'spider_version',
            conf_value: formData.spider_version,
            description: t('Spider版本'),
            op_type: 'update',
          },
        ],
        conf_type: 'deploy',
        level_name: 'module',
        level_value: createResult.db_module_id,
        meta_cluster_type: ClusterTypes.TENDBCLUSTER,
        version: 'deploy_info',
      });

      window.changeConfirm = false;
      router.push({
        name: 'DbConfigureList',
        params: { clusterType: ClusterTypes.TENDBCLUSTER },
        query: { parentId: `app-${bizId}`, treeId: `module-${createResult.db_module_id}` },
      });
    } catch (e) {
      console.error(e);
    }
    isSubmitting.value = false;
  };

  /** 取消 */
  const handleCancel = () => {
    routerBack();
  };

  const routerBack = () => {
    router.push({
      name: String(route.query.from || 'serviceApply'),
      params: { clusterType: ClusterTypes.TENDBCLUSTER },
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

    .version-select-inline,
    .charset-select-inline {
      width: auto;
      min-width: 180px;
    }
  }

  .form-item-tips {
    font-size: 12px;
    line-height: 20px;
    color: #979ba5;
    position: absolute;
  }

  .param-config-wrapper {
    margin-top: 16px;
    background: #fff;

    :deep(.bk-tab-content) {
      padding: 16px 16px 0;
    }
  }

  .db-type-tag {
    height: 30px;
    color: @primary-color;
    background: white;
    border: 1px solid @border-primary;
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
