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
  <SmartAction>
    <BkAlert
      class="mb-16"
      closable
      theme="info"
      :title="
        t('模块是配置管理单元_用于组织一组使用相同数据库配置_版本_字符集等_的集群_新建模块的参数默认继承业务级当前值_')
      " />
    <DbForm
      ref="formRef"
      class="create-module-page"
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
        <BkFormItem
          :label="t('字符集')"
          required>
          <DbSelect
            v-model="formData.charset"
            class="charset-select"
            :clearable="false"
            :disabled="isBindSuccessfully"
            filterable
            :placeholder="t('请选择字符集')"
            @change="handleValidate">
            <DbOption
              v-for="(item, index) of characterSets"
              :key="index"
              :label="item"
              :value="item" />
          </DbSelect>
        </BkFormItem>

        <!-- 存储层：三级版本选型 + OS 约束（仅启用版本可选） -->
        <div class="layer-config-card">
          <div class="layer-title">{{ t('存储层') }}</div>
          <VersionOsEditor
            ref="storageEditorRef"
            :db-type="DBTypes.MYSQL"
            default-distribution-name="TXSQL"
            pkg-type="mysql"
            @before-series-change="handleBeforeStorageSeriesChange"
            @change="handleStorageChange" />
        </div>

        <!-- 接入层：仅 MySQL 主从（tendbha）；系列 → 版本号，发行版隐式 DBM -->
        <div
          v-if="clusterType === ClusterTypes.TENDBHA"
          class="layer-config-card">
          <div class="layer-title">{{ t('接入层') }}</div>
          <VersionOsEditor
            ref="proxyEditorRef"
            :db-type="DBTypes.MYSQL"
            default-distribution-name="DBM"
            pkg-type="mysql-proxy"
            :show-distribution="false"
            @before-series-change="handleBeforeProxySeriesChange"
            @change="handleProxyChange" />
        </div>
      </DbCard>

      <!-- 参数配置 — 四个 Tab -->
      <div class="param-config-wrapper">
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
              <span class="param-tab-label">
                {{ tab.name }}
                <span
                  v-if="(tabChangedCountMap[tab.conf_file] ?? 0) > 0"
                  class="tab-modified-dot" />
              </span>
            </template>
            <ParamTable
              :ref="(el: any) => setTableRef(tab.name, el)"
              :conf-type="tab.conf_type"
              :namespace="tab.namespace"
              :sticky-operations="activeConfType === tab.conf_file"
              :version="tab.conf_file" />
          </BkTabPanel>
        </BkTab>
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
      <DbResetButton
        class="ml-8"
        :confirm-handler="handleReset"
        :disabled="isSubmitting" />
      <BkButton
        class="w-88 ml-8"
        :disabled="isSubmitting"
        @click="handleCancel">
        {{ t('取消') }}
      </BkButton>
      <template v-if="totalChangedCount > 0">
        <I18nT
          class="total-change-stats"
          keypath="总计已修改n项"
          tag="span">
          <template #n>
            <span class="change-count">{{ totalChangedCount }}</span>
          </template>
        </I18nT>
        <span class="stats-tips">{{ t('提交后将固化为自定义_不再随业务变化') }}</span>
      </template>
    </template>
  </SmartAction>
  <Teleport to="#dbContentTitleAppend">
    <span class="create-module-nav">
      <DbTag theme="info">
        {{ clusterTypeInfos[clusterType]?.name || clusterType }}
      </DbTag>
      <span class="create-module-nav-desc"> {{ t('业务') }} : {{ bizInfo.name }} </span>
    </span>
  </Teleport>
</template>

<script setup lang="ts">
  import InfoBox from 'bkui-vue/lib/info-box';
  import _ from 'lodash';
  import { I18nT, useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { checkDbModuleUnique, createModules } from '@services/source/cmdb';
  import { getListClusterModuleConfFiles, saveModulesDeployInfo } from '@services/source/configs';

  import { useGlobalBizs } from '@stores';

  import { clusterTypeInfos, ClusterTypes, DBTypes } from '@common/const';

  import FormItemWithHint from '@components/form-item-with-hint/Index.vue';

  import DomainPreview from '@views/db-configure/components/DomainPreview.vue';
  import VersionOsEditor, { type VersionOsValue } from '@views/db-configure/components/VersionOsEditor.vue';
  import { saveConfigureState } from '@views/db-configure/utils/configureState';

  import { messageError, random } from '@utils';

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

  const moduleId = ref(Number(route.params.db_module_id));
  const isBindSuccessfully = ref(false);
  const isSubmitting = ref(false);

  /** 模块信息卡展开态：校验失败时自动展开，避免错误提示被折叠隐藏 */
  const isModuleInfoExpanded = ref(true);

  // 表单数据
  const getFormData = () => ({
    alias_name: (route.query.alias_name ?? '') as string,
    charset: '',
    db_version: '',
  });
  const formData = reactive(getFormData());
  const formRef = ref();

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
   * §4 重载确认：换存储层系列会重载 mysql 存储 Tab；
   * 该 Tab 有已改项时弹 InfoBox 二次确认（对象写「存储层」），取消则版本下拉回滚
   */
  const handleBeforeStorageSeriesChange = (next: () => void) => {
    const changedCount = tableRefs.value?.dbconf?.changedCount ?? 0;
    if (changedCount === 0) {
      next();
      return;
    }
    InfoBox({
      cancelText: t('取消'),
      confirmText: t('确定'),
      content: t('存储层系列变更将重载参数配置_n_项已修改内容将被丢弃_是否继续_', { n: changedCount }),
      headerAlign: 'center',
      onConfirm: () => {
        tableRefs.value?.dbconf?.handleReset?.();
        next();
      },
      title: t('确认重载存储层参数_'),
    });
  };

  /**
   * §4 重载确认：换接入层系列（TenDBCluster 重载 Spider 配置 Tab；MySQL 主从无 proxy 参数 Tab 仅更新部署默认）
   * 当前集群类型为主从，无 proxy 参数 Tab，直接放行
   */
  const handleBeforeProxySeriesChange = (next: () => void) => {
    next();
  };

  const characterSets = ['utf8', 'utf8mb4', 'gbk', 'latin1', 'gb2312'];

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

  // 参数配置 Tab — 用 db_version 作为渲染 key，版本切换时强制重建整个 BkTab 及其子组件
  const activeConfType = ref('dbconf');
  const tabRenderKey = ref(random());
  const confTabs = ref<ServiceReturnType<typeof getListClusterModuleConfFiles>>([]);

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

  watch(
    () => formData.db_version,
    () => {
      fetchConfTabs({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        deploy_versions: JSON.stringify({ db_version: formData.db_version }),
        meta_cluster_type: clusterType.value,
      });
    },
  );

  // 每个 confType 对应一个 ParamTable 实例
  const tableRefs = ref<Record<string, InstanceType<typeof ParamTable>>>({});
  const setTableRef = (name: string, el: any) => {
    if (el) {
      tableRefs.value[name] = el;
    }
  };

  /** 所有 Tab 的总计已修改数量 */
  const totalChangedCount = computed(() =>
    Object.values(tableRefs.value).reduce((sum, ref) => sum + (ref?.changedCount ?? 0), 0),
  );

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

  /** 每个 Tab 的已修改数量（用于 Tab 小黄点） */
  const tabChangedCountMap = computed(() => {
    const map: Record<string, number> = {};
    confTabs.value.forEach((tab) => {
      const tableRef = tableRefs.value[tab.name];
      map[tab.conf_file] = tableRef?.changedCount ?? 0;
    });
    return map;
  });

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
      window.changeConfirm = true;
      // 校验失败必须给用户可见反馈，不能只打日志（否则点确定像没反应）
      messageError(`${t(componentLabelMap[invalid.componentName])}：${invalid.result.message}`);
      return;
    }

    isSubmitting.value = true;
    try {
      await formRef.value?.validate();

      // 组装 db_versions：{组件名: {db_version_id, permit_os_type, permit_os}}
      const dbVersions: Record<string, { db_version_id: number; permit_os: string[]; permit_os_type: string }> = {};
      if (componentNames.includes('single') || componentNames.includes('backend')) {
        dbVersions[componentNames[0]] = storageEditorRef.value!.getWriteValue();
      }
      if (componentNames.includes('proxy')) {
        dbVersions.proxy = proxyEditorRef.value!.getWriteValue();
      }

      // 新建模块
      const createResult = await createModules({
        alias_name: formData.alias_name,
        biz_id: bizId,
        cluster_type: clusterType.value,
        db_module_name: `${formData.alias_name}-${formData.db_version}-${formData.charset}`,
        db_versions: Object.keys(dbVersions).length > 0 ? dbVersions : undefined,
      });
      moduleId.value = createResult.db_module_id;

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
        meta_cluster_type: clusterType.value,
        version: 'deploy_info',
      });
      isBindSuccessfully.value = true;

      // 绑定各 tab 参数配置
      const bindTasks = Object.values(tableRefs.value)
        .filter((ref) => ref?.hasChange?.())
        .map((ref) => ref.bindConfigParameters());
      await Promise.all(bindTasks);

      window.changeConfirm = false;

      // 保存选中的树节点状态，确保跳转后树能自动选中新模块
      saveConfigureState({
        selectedParentId: `app-${bizId}`,
        selectedTreeId: moduleId.value ? `module-${moduleId.value}` : '',
      });

      // 跳转到数据库配置并选中新模块
      router.push({
        name: 'DbConfigureList',
        params: {
          clusterType: clusterType.value,
          parentId: `app-${bizId}`,
          treeId: moduleId.value ? `module-${moduleId.value}` : '',
        },
      });
    } catch (e) {
      // 校验失败时展开模块信息卡，避免错误提示被折叠隐藏
      isModuleInfoExpanded.value = true;
      console.log(e);
    }
    isSubmitting.value = false;
  };

  /** 重置 */
  const handleReset = () => {
    _.merge(formData, getFormData());
    Object.values(tableRefs.value).forEach((ref) => ref?.handleReset?.());
    nextTick(() => {
      window.changeConfirm = false;
    });
  };

  /** 取消 */
  const handleCancel = () => {
    emits('routerBack');
  };
</script>

<style lang="less" scoped>
  .create-module-page {
    --module-form-content-width: 960px;

    padding-bottom: 20px;

    :deep(.bk-form-item) {
      max-width: calc(160px + var(--module-form-content-width));
    }

    /* 模块名称行不受宽度限制，域名预览与输入框同行展示 */
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

    :deep(.row-content) {
      max-width: var(--module-form-content-width);
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
      width: var(--module-form-content-width);
      max-width: 100%;
      flex-shrink: 0;
    }
  }

  .charset-select {
    width: var(--module-form-content-width);
    max-width: 100%;
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

  .total-change-stats {
    margin-left: 16px;
    font-size: 13px;
    line-height: 20px;
    color: #63656e;

    .change-count {
      margin: 0 2px;
      font-weight: 700;
      color: #f59500;
    }
  }

  .stats-tips {
    margin-left: 8px;
    font-size: 12px;
    line-height: 20px;
    color: #979ba5;
  }

  .param-tab-label {
    display: inline-flex;
    height: 42px;
    padding-right: 8px;
    align-items: center;
  }

  .tab-modified-dot {
    position: absolute;
    top: 10px;
    right: 16px;
    width: 8px;
    height: 8px;
    background: #f59500;
    border: 1px solid #fff;
    border-radius: 50%;
    box-sizing: border-box;
  }

  /* 导航栏：集群类型标签 + 业务信息（与全局配置详情页同形） */
  .create-module-nav {
    display: inline-flex;
    gap: 8px;
    margin-left: 8px;
    align-items: center;
  }

  .create-module-nav-desc {
    position: relative;
    padding-left: 8px;
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
    background: #dcdee5;
    content: '';
    transform: translateY(-50%);
  }
</style>
