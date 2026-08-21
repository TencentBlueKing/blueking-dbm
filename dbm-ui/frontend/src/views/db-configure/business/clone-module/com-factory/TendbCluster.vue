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
        <!-- 模块名 -->
        <FormItemWithHint
          class="form-item-name"
          :label="t('模块名称')"
          :model="formData.alias_name"
          property="alias_name"
          required
          :rules="rules.alias_name">
          <template #hint>
            {{ t('仅支持小写字母、数字、连字符，') }}<span class="hint-warning">{{ t('创建后不可改') }}</span>
          </template>
          <div class="module-name-row">
            <BkInput
              v-model="formData.alias_name"
              class="module-name-input"
              :maxlength="63"
              :placeholder="t('请输入模块名')"
              show-word-limit
              @change="handleValidate" />
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
                <i class="db-icon-mysql mr-5" />
              </template>
              {{ clusterTypeInfos[ClusterTypes.TENDBCLUSTER]?.name }}
            </BkTag>
            <FormItemWithHint
              class="version-form-item"
              property="db_version"
              required
              :show-label="false">
              <DbVersionSelect
                v-model="formData.db_version"
                class="version-select-inline"
                :db-type="DBTypes.MYSQL"
                :prefix="t('存储层版本')"
                :source-version="String(route.query.confFile || '')"
                @change="handleValidate" />
            </FormItemWithHint>
            <FormItemWithHint
              class="version-form-item"
              property="spider_version"
              required
              :show-label="false">
              <DbVersionSelect
                v-model="formData.spider_version"
                class="version-select-inline"
                :db-type="DBTypes.MYSQL"
                :placeholder="t('请选择xx', [t('接入层版本')])"
                :prefix="t('接入层版本')"
                query-key="spider"
                :source-version="String(route.query.spiderConfFile || '')"
                @change="handleValidate" />
            </FormItemWithHint>
            <FormItemWithHint
              class="charset-form-item"
              property="charset"
              required
              :show-label="false">
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
            </FormItemWithHint>
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
              <!-- dbconf / proxyconf：克隆对比模式，含 diff/废弃 -->
              <ParamTable
                v-if="tab.conf_type === 'dbconf' || tab.conf_type === 'proxyconf'"
                :ref="(el: any) => setTableRef(tab.conf_file, el)"
                :deprecated-count="getDeprecatedCount(tab.conf_type)"
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
      <span> {{ t('业务') }}：{{ bizInfo.name }} </span>
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

  import { useGlobalBizs } from '@stores';

  import { clusterTypeInfos, ClusterTypes, DBTypes } from '@common/const';

  import DbTable from '@components/db-table/IndexNew.vue';
  import FormItemWithHint from '@components/form-item-with-hint/Index.vue';

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
          if (!formData.alias_name || !formData.db_version || !formData.spider_version || !formData.charset)
            return true;
          try {
            const data = await checkDbModuleUnique({
              bk_biz_id: String(bizId),
              cluster_type: ClusterTypes.TENDBCLUSTER,
              db_module_name: `${formData.alias_name}-${formData.spider_version}-${formData.db_version}-${formData.charset}`,
            });
            return data.is_unique
              ? true
              : t('该名称已被占用（{type} ：{spiderVersion}-{version} / {charset}）', {
                  charset: formData.charset,
                  spiderVersion: formData.spider_version,
                  type: 'TenDBCluster',
                  version: formData.db_version,
                });
          } catch {
            return false;
          }
        },
      },
    ],
  };

  /** 创建空的 CloneModuleQueryResult */
  const createEmptyCloneResult = (): CloneModuleQueryResult => ({
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

  // 克隆查询原始结果（按 conf_type 分组）
  const cloneResultMap = reactive<Record<string, CloneModuleQueryResult>>({
    dbconf: createEmptyCloneResult(),
    proxyconf: createEmptyCloneResult(),
  });

  /** 获取当前活跃 Tab 对应的 cloneResult */
  const currentCloneResult = computed(() => cloneResultMap[activeConfTypeConfType.value] || createEmptyCloneResult());

  /** 当前活跃 Tab 的 conf_type */
  const activeConfTypeConfType = computed(() => {
    const tab = confTabs.value.find((t) => t.conf_file === activeConfType.value);
    return tab?.conf_type || 'dbconf';
  });

  /** 将 content 对象转为数组，并标注 value_source 和 diff_type */
  const currentConfItems = computed<CloneConfItem[]>(() => {
    const result = currentCloneResult.value;
    if (!result.content) return [];
    const modifiedSet = new Set(result.conf_names_value_modified || []);
    const diffMap = result.conf_names_value_diff || {};

    return Object.values(result.content).map((item) => {
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
    const allItems = [...getConfItems('dbconf'), ...getConfItems('proxyconf')];
    return {
      changed: allItems.filter((i) => i.diff_type === 'changed' || i.diff_type === 'new').length,
      custom: allItems.filter((i) => i.value_source === 'custom').length,
      removed: getDeprecatedNames('dbconf').length + getDeprecatedNames('proxyconf').length,
    };
  });

  /** 获取指定 conf_type 的废弃参数名列表 */
  const getDeprecatedNames = (confType: string): string[] => cloneResultMap[confType]?.conf_names_deprecated || [];

  /** 获取指定 conf_type 的 conf items */
  const getConfItems = (confType: string): CloneConfItem[] => {
    const result = cloneResultMap[confType];
    if (!result?.content) return [];
    const modifiedSet = new Set(result.conf_names_value_modified || []);
    const diffMap = result.conf_names_value_diff || {};
    return Object.values(result.content).map((item) => {
      const diffValue = (diffMap as Record<string, string>)[item.conf_name];
      const isInDiff = diffValue !== undefined;
      return {
        ...item,
        diff_type: !isInDiff ? 'none' : diffValue === '_NONE_' ? 'new' : 'changed',
        source_conf_value: diffValue && diffValue !== '_NONE_' ? diffValue : undefined,
        value_source: modifiedSet.has(item.conf_name) ? 'custom' : 'source',
      };
    });
  };

  /** 获取指定 conf_type 的废弃数量 */
  const getDeprecatedCount = (confType: string): number => getDeprecatedNames(confType).length;

  /** 废弃参数名列表（当前 Tab） */
  const deprecatedNames = computed(() => getDeprecatedNames(activeConfTypeConfType.value));

  /** 废弃参数列表（用于侧滑展示，当前 Tab） */
  const deprecatedItems = computed<CloneConfItem[]>(() => {
    const names = deprecatedNames.value;
    const result = currentCloneResult.value;
    return names.map((name) => {
      const item = result.content[name];
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
    });
  });

  /** 废弃侧滑数据源 */
  const deprecatedDataSource = () =>
    Promise.resolve({ count: deprecatedItems.value.length, results: deprecatedItems.value });

  /** 获取克隆对比结果（直接调用，避免 useRequest 连续调用时取消前一个请求） */
  const fetchCloneResult = (params: {
    conf_type: string;
    meta_cluster_type: string;
    source_bk_biz_id: string;
    source_conf_file: string;
    source_module_id: string;
    target_bk_biz_id: string;
    target_conf_file: string;
  }) => {
    return moduleCloneQuery(params)
      .then((res) => {
        const confType = params.conf_type;
        cloneResultMap[confType] = res;
        // 刷新当前活跃 Tab 的表格（如果正在查看此 conf_type）
        const currentTab = confTabs.value.find((t) => t.conf_file === activeConfType.value);
        if (currentTab?.conf_type === confType) {
          nextTick(() => currentParamTable.value?.refreshData());
        }
      })
      .catch(() => {});
  };

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
      if (formData.spider_version) {
        Object.assign(rawConfTabs[1], {
          conf_file: formData.spider_version,
          conf_type: 'proxyconf',
          name: formData.spider_version,
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
  if (route.query.confFile) {
    cloneResultMap.dbconf.conf_file_info.conf_file = String(route.query.confFile);
  }
  if (route.query.spiderConfFile) {
    cloneResultMap.proxyconf.conf_file_info.conf_file = String(route.query.spiderConfFile);
  }
  // 源字符集从路由取（由源模块列表页 moduleInfo.charset 传入）
  if (route.query.charset) {
    sourceCharset.value = String(route.query.charset);
    formData.charset = String(route.query.charset);
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
      // 存储层版本差异对比
      if (formData.db_version) {
        fetchCloneResult({
          conf_type: 'dbconf',
          meta_cluster_type: ClusterTypes.TENDBCLUSTER,
          source_bk_biz_id: String(bizId),
          source_conf_file: String(route.query.confFile || ''),
          source_module_id: String(route.query.moduleId || ''),
          target_bk_biz_id: String(bizId),
          target_conf_file: formData.db_version,
        });
      }
      // 接入层版本差异对比
      if (formData.spider_version) {
        fetchCloneResult({
          conf_type: 'proxyconf',
          meta_cluster_type: ClusterTypes.TENDBCLUSTER,
          source_bk_biz_id: String(bizId),
          source_conf_file: String(route.query.spiderConfFile || ''),
          source_module_id: String(route.query.moduleId || ''),
          target_bk_biz_id: String(bizId),
          target_conf_file: formData.spider_version,
        });
      }
    },
  );

  watch(
    currentConfItems,
    (items) => {
      nextTick(() => currentParamTable.value?.setData(items));
    },
    { immediate: true },
  );

  /** Tab 切换时：非 dbconf/proxyconf 调用 getLevelConfig */
  watch(activeConfType, (tabKey) => {
    const currentTab = confTabs.value.find((t) => t.conf_file === tabKey);
    if (!currentTab) return;
    // dbconf / proxyconf 使用克隆对比数据，无需 getLevelConfig
    if (currentTab.conf_type === 'dbconf' || currentTab.conf_type === 'proxyconf') {
      nextTick(() => currentParamTable.value?.refreshData());
      return;
    }

    fetchLevelConfig({
      bk_biz_id: Number(bizId),
      conf_type: currentTab.conf_type,
      level_name: 'module',
      level_value: String(route.query.moduleId || ''),
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
    // BkSideslider 内容懒渲染，需等 DbTable 挂载后再 fetchData
    const stop = watch(sliderTableRef, (val) => {
      if (val) {
        nextTick(() => sliderTableRef.value?.fetchData());
        stop();
      }
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

      // 保存选中的树节点状态，确保跳转后树能自动选中新模块
      saveConfigureState({
        selectedParentId: `app-${bizId}`,
        selectedTreeId: `module-${createResult.db_module_id}`,
      });

      router.push({
        name: 'DbConfigureList',
        params: {
          clusterType: ClusterTypes.TENDBCLUSTER,
          parentId: `app-${bizId}`,
          treeId: `module-${createResult.db_module_id}`,
        },
      });
    } catch (e) {
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
      color: rgb(255 156 1);
    }
  }

  .module-name-row {
    display: flex;
    align-items: center;

    .module-name-input {
      width: 370px;
      flex-shrink: 0;
    }
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
