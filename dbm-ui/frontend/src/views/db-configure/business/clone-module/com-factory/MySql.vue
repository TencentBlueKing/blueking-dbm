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
      class="clone-module-page"
      :label-width="160"
      :model="formData"
      :rules="rules"
      :scroll-align-to-top="false">
      <!-- 模块信息 + 存储层 / 接入层：同一张白卡，两个层用浅灰块分组 -->
      <DbCard
        v-model:collapse="isModuleInfoExpanded"
        class="module-info-card"
        mode="collapse"
        :title="t('模块信息')">
        <!-- 模块名 -->
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
              :placeholder="t('由英文字母、数字、连字符组成')"
              show-word-limit
              @change="handleValidate" />
            <DomainPreview :module-name="formData.alias_name" />
          </div>
        </FormItemWithHint>
        <!-- 字符集 -->
        <BkFormItem
          :label="t('字符集')"
          required>
          <DbSelect
            v-model="formData.charset"
            class="charset-select"
            :clearable="false"
            filterable
            :placeholder="t('请选择字符集')"
            @change="handleValidate">
            <DbOption
              v-for="(item, index) of characterSets"
              :key="index"
              :label="item"
              :value="item">
              <span>{{ item }}</span>
              <DbTag
                v-if="sourceCharset && item === sourceCharset"
                class="ml-5"
                theme="info">
                {{ t('源字符集') }}
              </DbTag>
            </DbOption>
          </DbSelect>
        </BkFormItem>

        <!-- 存储层：三级版本选型 + OS 约束；克隆带出源发行版，可改 -->
        <div class="layer-config-card">
          <div class="layer-title">{{ t('存储层') }}</div>
          <VersionOsEditor
            ref="storageEditorRef"
            v-model="storageVersion"
            :db-type="DBTypes.MYSQL"
            pkg-type="mysql"
            @before-series-change="handleBeforeStorageSeriesChange"
            @change="handleStorageChange" />
        </div>

        <!-- 接入层：仅 MySQL 主从（tendbha）；克隆带出源系列/版本，可改 -->
        <div
          v-if="clusterType === ClusterTypes.TENDBHA"
          class="layer-config-card">
          <div class="layer-title">{{ t('接入层') }}</div>
          <VersionOsEditor
            ref="proxyEditorRef"
            v-model="proxyVersion"
            :db-type="DBTypes.MYSQL"
            default-distribution-name="DBM"
            pkg-type="mysql-proxy"
            :show-distribution="false"
            @before-series-change="handleBeforeProxySeriesChange"
            @change="handleProxyChange" />
        </div>
      </DbCard>

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
      <!-- §2.3 创建按钮：该层版本未选齐则不可用；指定范围已选为空亦不可用 -->
      <BkButton
        class="w-88"
        :disabled="!isVersionSelectionComplete"
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
    render-directive="show"
    :show-footer="false"
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
    <!-- 数据库类型固定在导航栏展示（源模块已锁定，不随表单修改，与全局配置详情页同形） -->
    <span class="clone-module-nav">
      <DbTag theme="info">
        {{ clusterTypeInfos[clusterType]?.name || clusterType }}
      </DbTag>
      <span class="clone-module-meta">
        <span> {{ t('业务') }}：{{ bizInfo.name || '--' }} </span>
        <span> {{ t('源模块') }}：{{ String(route.query.moduleName) || '--' }} </span>
      </span>
    </span>
  </Teleport>
</template>

<script setup lang="ts">
  import InfoBox from 'bkui-vue/lib/info-box';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { checkDbModuleUnique, type ComponentVersionInfo, createModules, getModules } from '@services/source/cmdb';
  import {
    type CloneConfItem,
    type CloneModuleQueryResult,
    getLevelConfig,
    getListClusterModuleConfFiles,
    moduleCloneQuery,
    saveModulesDeployInfo,
  } from '@services/source/configs';
  import { getReleaseVersionList, getVersionSeriesList } from '@services/source/version';

  import { useGlobalBizs } from '@stores';

  import { clusterTypeInfos, ClusterTypes, DBTypes } from '@common/const';

  import DbTable from '@components/db-table/IndexNew.vue';
  import FormItemWithHint from '@components/form-item-with-hint/Index.vue';

  import DomainPreview from '@views/db-configure/components/DomainPreview.vue';
  import VersionOsEditor, { type VersionOsValue } from '@views/db-configure/components/VersionOsEditor.vue';
  import { saveConfigureState } from '@views/db-configure/utils/configureState';

  import { messageError, random } from '@utils';

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

  /** 模块信息卡展开态：校验失败时自动展开，避免错误提示被折叠隐藏 */
  const isModuleInfoExpanded = ref(true);

  // 每个 confFile 对应一个 ParamTable 实例
  const tableRefs = ref<Record<string, InstanceType<typeof ParamTable>>>({});
  /** 当前活跃 Tab 对应的 ParamTable 实例 */
  const currentParamTable = computed(() => tableRefs.value[activeConfType.value]);
  const setTableRef = (name: string, el: any) => {
    if (el) {
      tableRefs.value[name] = el;
    }
  };

  /**
   * §2.3 创建按钮可用性：各层版本选齐且指定范围模式下已选非空
   * 存储层必备；主从（tendbha）另需接入层选齐
   */
  const isVersionSelectionComplete = computed(() => {
    const storage = storageVersion.value;
    const storageOk = storage.versionId !== '' && (storage.osMode === 'follow' || storage.specifyOs.length > 0);
    if (!storageOk) return false;
    if (clusterType.value === ClusterTypes.TENDBHA) {
      const proxy = proxyVersion.value;
      return proxy.versionId !== '' && (proxy.osMode === 'follow' || proxy.specifyOs.length > 0);
    }
    return true;
  });

  // 表单数据
  const formData = reactive({
    alias_name: '',
    charset: '',
    db_version: '',
  });
  const formRef = ref();
  const sliderTableRef = ref();
  /** 源字符集（从路由取，由源模块列表页 moduleInfo.charset 传入） */
  const sourceCharset = ref<string>('');
  const isShowSlider = ref(false);
  // 当前活跃 Tab
  const activeConfType = ref('dbconf');
  const tabRenderKey = ref(random());
  const confTabs = ref<ServiceReturnType<typeof getListClusterModuleConfFiles>>([]);

  const characterSets = ['utf8', 'utf8mb4', 'gbk', 'latin1', 'gb2312'];

  // 集群类型 → 协议组件名映射（创建模块 db_versions 的 key）
  const clusterComponentNames: Record<string, string[]> = {
    [ClusterTypes.TENDBHA]: ['backend', 'proxy'],
    [ClusterTypes.TENDBSINGLE]: ['single'],
  };

  /** 组件名 → 展示层名（提交校验提示用） */
  const componentLabelMap: Record<string, string> = {
    backend: '存储层',
    proxy: '接入层',
    single: '存储层',
  };

  /** 存储层选型值（backend / single） */
  const storageVersion = ref<VersionOsValue>({
    distributionId: '',
    osMode: 'follow',
    osType: '',
    seriesId: '',
    specifyOs: [],
    versionId: '',
  });
  /** 接入层选型值（proxy，仅主从） */
  const proxyVersion = ref<VersionOsValue>({
    distributionId: '',
    osMode: 'follow',
    osType: '',
    seriesId: '',
    specifyOs: [],
    versionId: '',
  });

  const storageEditorRef = ref<InstanceType<typeof VersionOsEditor>>();
  const proxyEditorRef = ref<InstanceType<typeof VersionOsEditor>>();

  /**
   * 由源模块 db_version_info 还原三级选型的回填结构：
   * 发行版/系列按名称匹配版本接口的 ID，版本号直接用 db_version_id，OS 约束按 follow_package/effective_permit_os 还原
   */
  const buildVersionOsValue = async (
    info: ComponentVersionInfo | undefined,
    pkgType: string,
  ): Promise<VersionOsValue | undefined> => {
    if (!info?.db_version_id) return undefined;
    const distributionList = await getReleaseVersionList({ db_type: DBTypes.MYSQL, pkg_type: pkgType });
    const distribution = distributionList.find((item) => item.name === info.distribution);
    if (!distribution) return undefined;
    const seriesList = await getVersionSeriesList({ distribution: distribution.id });
    const series = seriesList.find((item) => item.name === info.version_series);
    if (!series) return undefined;
    return {
      distributionId: distribution.id,
      osMode: info.follow_package ? 'follow' : 'specify',
      osType: 'Linux',
      seriesId: series.id,
      specifyOs: [...info.effective_permit_os],
      versionId: info.db_version_id,
    };
  };

  /**
   * 克隆带出源模块的三级选型（注释见模板「克隆带出源发行版/系列版本」）：
   * 存量模块 db_version_info 为空时保持不选，由用户手动选择发行版
   */
  const { run: fetchSourceVersion } = useRequest(getModules, {
    manual: true,
    async onSuccess(modules) {
      const sourceInfo = modules.find((item) => item.db_module_id === Number(route.query.moduleId))?.db_version_info;
      if (!sourceInfo) return;
      const storageComponentName = clusterType.value === ClusterTypes.TENDBSINGLE ? 'single' : 'backend';
      const storageValue = await buildVersionOsValue(sourceInfo[storageComponentName], 'mysql');
      if (storageValue) {
        storageVersion.value = storageValue;
        // 回填不触发 change，参数 Tab / 克隆对比的版本标识（系列名）在这里显式同步一次
        formData.db_version = sourceInfo[storageComponentName]?.version_series ?? '';
        handleValidate();
      }
      const proxyValue = await buildVersionOsValue(sourceInfo.proxy, 'mysql-proxy');
      if (proxyValue) {
        proxyVersion.value = proxyValue;
      }
    },
  });

  /** 存储层选型变化：更新 db_version（参数 Tab 依赖）并同步校验 */
  const handleStorageChange = (value: VersionOsValue) => {
    storageVersion.value = value;
    // 参数 Tab 的版本标识取系列名（§4：同系列换版本号不重载）
    formData.db_version = storageEditorRef.value?.getSeriesName() ?? '';
    handleValidate();
  };

  const handleProxyChange = (value: VersionOsValue) => {
    proxyVersion.value = value;
  };

  /**
   * §4 重载确认：换存储层系列会重载 mysql 存储 Tab（克隆场景为 dbconf 对比 Tab）；
   * 已有审查结果时弹 InfoBox 二次确认（对象写「存储层」），取消则版本下拉回滚
   */
  const handleBeforeStorageSeriesChange = (next: () => void) => {
    const changedCount = totalCounts.value.changed + totalCounts.value.custom;
    if (changedCount === 0) {
      next();
      return;
    }
    InfoBox({
      cancelText: t('取消'),
      confirmText: t('确定'),
      content: t('存储层系列变更将重载参数配置_n_项审查内容将被丢弃_是否继续_', { n: changedCount }),
      headerAlign: 'center',
      onConfirm: () => {
        next();
      },
      title: t('确认重载存储层参数_'),
    });
  };

  /** §4：MySQL 主从无 proxy 参数 Tab，仅更新部署默认，直接放行 */
  const handleBeforeProxySeriesChange = (next: () => void) => {
    next();
  };

  /** 触发表单校验（版本或字符集 change 时） */
  const handleValidate = () => {
    formRef.value?.validate();
  };

  // 模块名校验规则
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
          if (!formData.alias_name || !formData.db_version || !formData.charset) return true;
          try {
            const data = await checkDbModuleUnique({
              bk_biz_id: String(bizId),
              cluster_type: clusterType.value,
              db_module_name: `${formData.alias_name}-${formData.db_version}-${formData.charset}`,
            });
            return data.is_unique
              ? true
              : t('该名称已被占用（{type} ：{version} / {charset}）', {
                  charset: formData.charset,
                  type: clusterTypeInfos[clusterType.value].name,
                  version: formData.db_version,
                });
          } catch {
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
    onSuccess(res) {
      const rawConfTabs = res || [];
      if (formData.db_version) {
        Object.assign(rawConfTabs[0], {
          conf_file: formData.db_version,
          conf_type: 'dbconf',
          name: formData.db_version,
        });
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
      nextTick(() => currentParamTable.value?.setData(items));
    },
  });

  // 初始化：从路由回填源模块名
  if (route.query.moduleName) {
    formData.alias_name = String(route.query.moduleName);
  }
  // 克隆带出源模块的三级选型（发行版 / 系列 / 版本号 / OS 约束）
  fetchSourceVersion({
    bk_biz_id: Number(bizId),
    cluster_type: clusterType.value,
  });
  if (route.query.confFile) {
    cloneResult.value.conf_file_info.conf_file = String(route.query.confFile);
  }
  // 源字符集从路由取（由源模块列表页 moduleInfo.charset 传入）
  if (route.query.charset) {
    sourceCharset.value = String(route.query.charset);
    formData.charset = String(route.query.charset);
  }

  // 版本变化时：刷新 Tab 列表 + 重新拉取参数对比结果
  watch(
    () => formData.db_version,
    () => {
      fetchConfTabs({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        deploy_versions: JSON.stringify({ db_version: formData.db_version }),
        meta_cluster_type: clusterType.value,
      });
      fetchCloneResult({
        conf_type: 'dbconf',
        meta_cluster_type: clusterType.value,
        source_bk_biz_id: String(bizId),
        source_conf_file: String(route.query.confFile || ''),
        source_module_id: String(route.query.moduleId || ''),
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
      level_value: String(route.query.moduleId || ''),
      meta_cluster_type: clusterType.value,
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
    // 前端补齐校验：后端只校验 db_versions 必传，不校验各层齐全，提交前须确保该集群类型的所有组件都传上来。
    // 放在 isSubmitting 之前：提前返回时不能把按钮留在 loading 态
    const componentNames = clusterComponentNames[clusterType.value] || [];
    const validateResults = [
      { componentName: 'backend', result: storageEditorRef.value?.validate() },
      ...(clusterType.value === ClusterTypes.TENDBHA
        ? [{ componentName: 'proxy', result: proxyEditorRef.value?.validate() }]
        : []),
    ];
    const invalid = validateResults.find((item) => item.result && !item.result.ok);
    if (invalid?.result) {
      // 校验失败必须给用户可见反馈，不能只打日志（否则点确定像没反应）
      messageError(`${t(componentLabelMap[invalid.componentName])}：${invalid.result.message}`);
      return;
    }

    try {
      await formRef.value?.validate();

      isSubmitting.value = true;

      // 组装 db_versions：{组件名: {db_version_id, permit_os_type, permit_os}}
      const dbVersions: Record<string, { db_version_id: number; permit_os: string[]; permit_os_type: string }> = {};
      if (componentNames.includes('single') || componentNames.includes('backend')) {
        dbVersions[componentNames[0]] = storageEditorRef.value!.getWriteValue();
      }
      if (componentNames.includes('proxy')) {
        dbVersions.proxy = proxyEditorRef.value!.getWriteValue();
      }

      // 创建模块
      const dbModuleName = `${formData.alias_name}-${formData.db_version}-${formData.charset}`;
      const createResult = await createModules({
        alias_name: formData.alias_name,
        biz_id: Number(bizId),
        cluster_type: clusterType.value,
        db_module_name: dbModuleName,
        db_versions: Object.keys(dbVersions).length > 0 ? dbVersions : undefined,
      });

      // 绑定部署信息
      await saveModulesDeployInfo({
        bk_biz_id: Number(bizId),
        conf_items: [
          { conf_name: 'charset', conf_value: formData.charset, description: t('字符集'), op_type: 'update' },
          { conf_name: 'db_version', conf_value: formData.db_version, description: t('数据库版本'), op_type: 'update' },
        ],
        conf_type: 'deploy',
        level_name: 'module',
        level_value: createResult.db_module_id,
        meta_cluster_type: clusterType.value,
        version: 'deploy_info',
      });

      window.changeConfirm = false;

      // 保存选中的树节点状态，确保跳转后树能自动选中新模块
      saveConfigureState({
        selectedParentId: `app-${bizId}`,
        selectedTreeId: `module-${createResult.db_module_id}`,
      });

      router.push({
        name: 'DbConfigureList',
        params: {
          clusterType: clusterType.value,
          parentId: `app-${bizId}`,
          treeId: `module-${createResult.db_module_id}`,
        },
      });
    } catch (e) {
      // 校验失败时展开模块信息卡，避免错误提示被折叠隐藏
      isModuleInfoExpanded.value = true;
      console.error(e);
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
    padding-bottom: 20px;

    :deep(.bk-form-item) {
      max-width: 690px;
    }

    /* 模块名称行不受 690px 限制：集群域名预览与输入框同行展示 */
    :deep(.form-item-name) {
      max-width: none;
    }
  }

  // 模块信息白卡：内部承载存储层 / 接入层两个浅灰分组块
  .module-info-card {
    border-radius: 2px;

    /* 层内「版本 / 操作系统版本」的 label 列与表单 label 列对齐
       （VersionOsEditor 自带 76px 固定列宽，此处按 label-width 160 覆盖） */
    :deep(.row-label) {
      width: 160px;
      padding-right: 22px;
    }

    .layer-config-card {
      padding: 16px 0;
      background: #f5f7fa;
      border-radius: 2px;

      & + .layer-config-card {
        margin-top: 16px;
      }

      .layer-title {
        width: 160px;
        padding-right: 22px;
        margin-bottom: 16px;
        font-size: 12px;
        font-weight: 700;
        color: #313238;
        text-align: right;
      }
    }
  }

  .form-item-name {
    :deep(.hint-warning) {
      color: rgb(255 156 1);
    }
  }

  .module-name-row {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 12px;
    align-items: center;

    .module-name-input {
      width: 520px;
      flex-shrink: 0;
    }
  }

  .charset-select {
    width: 520px;
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

    .version-form-item,
    .charset-form-item {
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

    /* Tab 头吸附：整页滚动到参数区时保持可见，明确当前配置的是哪一部分；
       底色必须不透明，否则表体会从吸顶区域透出来。
       top 取负的内容区上内边距：滚动容器按 padding box 裁剪内容，sticky 的 top: 0 却相对 content box，
       不抵消这段 padding 就会留出一条缝，表体行会从那道缝里露到 Tab 条上方 */
    :deep(.bk-tab-header) {
      position: sticky;
      top: calc(-1 * var(--db-content-padding-top, 0px));
      z-index: 99;
      background: #f0f1f5;
    }

    :deep(.bk-tab-content) {
      padding: 16px 16px 0;
    }
  }

  .action-bar {
    display: flex;
    padding: 16px 24px;
    margin-top: 16px;
    background: #fff;
    border-radius: 2px;
    align-items: center;
    gap: 8px;
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
      background: #dcdee5;
      content: '';
      transform: translateY(-50%);
    }
  }

  /* 导航栏：集群类型标签 + 业务 / 源模块信息（与全局配置详情页同形） */
  .clone-module-nav {
    display: inline-flex;
    gap: 8px;
    margin-left: 8px;
    align-items: center;
  }

  .clone-module-meta {
    display: inline-flex;
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

  .deprecated-sider-body {
    padding: 16px 20px;
  }
</style>
