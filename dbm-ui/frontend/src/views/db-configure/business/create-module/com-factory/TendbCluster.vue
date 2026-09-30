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
        <!-- 模块名 -->
        <FormItemWithHint
          class="form-item-name"
          :label="t('模块名称')"
          :model="formData.alias_name"
          property="alias_name"
          required
          :rules="rules.alias_name">
          <template #hint>
            {{ t('仅支持小写字母、数字、连字符，') }}
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

        <!-- 存储层：三级版本选型 + OS 约束（协议 §0：tendbcluster → remote，介质 mysql） -->
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

        <!-- 接入层：spider（协议 §0：tendbcluster → spider，介质 spider） -->
        <div class="layer-config-card">
          <div class="layer-title">{{ t('接入层') }}</div>
          <VersionOsEditor
            ref="spiderEditorRef"
            :db-type="DBTypes.MYSQL"
            pkg-type="spider"
            @before-series-change="handleBeforeSpiderSeriesChange"
            @change="handleSpiderChange" />
        </div>
      </DbCard>

      <!-- 参数配置 -->
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
              :version="
                tab.conf_type === 'proxyconf'
                  ? formData.spider_version
                  : tab.conf_type === 'dbconf'
                    ? formData.db_version
                    : tab.conf_file
              " />
          </BkTabPanel>
        </BkTab>
      </div>
    </DbForm>
    <template #action>
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
        {{ clusterTypeInfos[ClusterTypes.TENDBCLUSTER]?.name || ClusterTypes.TENDBCLUSTER }}
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

  const bizId = window.PROJECT_CONFIG.BIZ_ID;

  // 业务信息
  const bizInfo = computed(() => globalBizsStore.bizs.find((info) => info.bk_biz_id === bizId) || { name: '' });

  const moduleId = ref(Number(route.params.db_module_id));
  const isBindSuccessfully = ref(false);
  const isSubmitting = ref(false);

  // 表单数据
  const getFormData = () => ({
    alias_name: (route.query.alias_name ?? '') as string,
    charset: '',
    db_version: '',
    spider_version: '',
  });
  const formData = reactive(getFormData());
  const formRef = ref();

  const characterSets = ['utf8', 'utf8mb4', 'gbk', 'latin1', 'gb2312'];

  /** 触发表单校验（版本或字符集 change 时） */
  const handleValidate = () => {
    formRef.value?.validate();
  };

  /** 组件名 → 展示层名（提交校验提示用） */
  const componentLabelMap: Record<string, string> = {
    remote: '存储层',
    spider: '接入层',
  };

  /** 存储层（remote）选型值 */
  const storageVersion = ref<VersionOsValue>({
    distributionId: '',
    osMode: 'follow',
    osType: '',
    seriesId: '',
    specifyOs: [],
    versionId: '',
  });
  /** 接入层（spider）选型值 */
  const spiderVersion = ref<VersionOsValue>({
    distributionId: '',
    osMode: 'follow',
    osType: '',
    seriesId: '',
    specifyOs: [],
    versionId: '',
  });

  const storageEditorRef = ref<InstanceType<typeof VersionOsEditor>>();
  const spiderEditorRef = ref<InstanceType<typeof VersionOsEditor>>();

  /** 存储层选型变化：参数 Tab 的版本标识取系列名（同系列换版本号不重载） */
  const handleStorageChange = (value: VersionOsValue) => {
    storageVersion.value = value;
    formData.db_version = storageEditorRef.value?.getSeriesName() ?? '';
    handleValidate();
  };

  /** 接入层选型变化：Spider 参数 Tab 的版本标识同样取系列名 */
  const handleSpiderChange = (value: VersionOsValue) => {
    spiderVersion.value = value;
    formData.spider_version = spiderEditorRef.value?.getSeriesName() ?? '';
    handleValidate();
  };

  /** 模块信息卡折叠状态（提交失败时展开，避免错误提示被折叠隐藏） */
  const isModuleInfoExpanded = ref(true);

  /** §2.3 创建按钮可用性：两层版本都选齐，且指定范围模式下已选非空 */
  const isVersionSelectionComplete = computed(() => {
    const storage = storageVersion.value;
    const storageOk = storage.versionId !== '' && (storage.osMode === 'follow' || storage.specifyOs.length > 0);
    if (!storageOk) return false;
    const spider = spiderVersion.value;
    return spider.versionId !== '' && (spider.osMode === 'follow' || spider.specifyOs.length > 0);
  });

  /** 按 conf_type 取对应参数表的已修改项数（重载确认用） */
  const getChangedCountByConfType = (confType: string) => {
    const tab = confTabs.value.find((item) => item.conf_type === confType);
    return (tab && tableRefs.value[tab.name]?.changedCount) || 0;
  };

  /** 重置指定层的参数 Tab（系列切换会重建该 Tab，已改项随之丢弃） */
  const resetConfTab = (confType: string) => {
    const tab = confTabs.value.find((item) => item.conf_type === confType);
    if (tab) tableRefs.value[tab.name]?.handleReset?.();
  };

  /** 换存储层系列会重载存储参数 Tab：有已改项时二次确认，取消则版本下拉回滚 */
  const handleBeforeStorageSeriesChange = (next: () => void) => {
    const changedCount = getChangedCountByConfType('dbconf');
    if (changedCount === 0) {
      next();
      return;
    }
    InfoBox({
      cancelText: t('取消'),
      confirmText: t('确定'),
      content: t('存储层系列变更将重载参数配置，{n} 项已修改内容将被丢弃，是否继续？', { n: changedCount }),
      headerAlign: 'center',
      onConfirm: () => {
        resetConfTab('dbconf');
        next();
      },
      title: t('确认重载存储层参数'),
    });
  };

  /** 换接入层系列会重载 Spider 参数 Tab：同上 */
  const handleBeforeSpiderSeriesChange = (next: () => void) => {
    const changedCount = getChangedCountByConfType('proxyconf');
    if (changedCount === 0) {
      next();
      return;
    }
    InfoBox({
      cancelText: t('取消'),
      confirmText: t('确定'),
      content: t('接入层系列变更将重载参数配置，{n} 项已修改内容将被丢弃，是否继续？', { n: changedCount }),
      headerAlign: 'center',
      onConfirm: () => {
        resetConfTab('proxyconf');
        next();
      },
      title: t('确认重载接入层参数'),
    });
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

  // 参数配置 Tab — 用版本组合作为渲染 key，版本切换时强制重建 BkTab 及子组件
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

  watch(
    () => [formData.db_version, formData.spider_version],
    () => {
      fetchConfTabs({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        deploy_versions: JSON.stringify({ db_version: formData.db_version }),
        meta_cluster_type: ClusterTypes.TENDBCLUSTER,
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
    // 前端补齐校验：后端只校验 db_versions 必传，不校验各层齐全，提交前须确保 remote / spider 都选齐。
    // 放在 isSubmitting 之前：提前返回时不能把按钮留在 loading 态
    const validateResults = [
      { componentName: 'remote', result: storageEditorRef.value?.validate() },
      { componentName: 'spider', result: spiderEditorRef.value?.validate() },
    ];
    const invalid = validateResults.find((item) => item.result && !item.result.ok);
    if (invalid?.result) {
      messageError(`${t(componentLabelMap[invalid.componentName])}：${invalid.result.message}`);
      return;
    }

    isSubmitting.value = true;
    try {
      await formRef.value?.validate();

      // 新建模块
      const createResult = await createModules({
        alias_name: formData.alias_name,
        biz_id: bizId,
        cluster_type: ClusterTypes.TENDBCLUSTER,
        db_module_name: `${formData.alias_name}-${formData.spider_version}-${formData.db_version}-${formData.charset}`,
        // 协议 §0：tendbcluster 必须传 remote(存储层) + spider(接入层)，后端不校验各层是否传齐
        db_versions: {
          remote: storageEditorRef.value!.getWriteValue(),
          spider: spiderEditorRef.value!.getWriteValue(),
        },
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
          {
            conf_name: 'spider_version',
            conf_value: formData.spider_version,
            description: t('Spider版本'),
            op_type: 'update',
          },
        ],
        conf_type: 'deploy',
        level_name: 'module',
        level_value: moduleId.value,
        meta_cluster_type: ClusterTypes.TENDBCLUSTER,
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
          clusterType: ClusterTypes.TENDBCLUSTER,
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

  }

  // 模块信息白卡（DbCard）：内部承载存储层 / 接入层两个浅灰分组块
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
    row-gap: 4px;
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
    margin-left: 4px;
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
