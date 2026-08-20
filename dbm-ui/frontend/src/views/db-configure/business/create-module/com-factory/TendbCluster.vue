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
      class="create-module-page db-scroll-y"
      :label-width="100"
      :model="formData"
      :rules="rules"
      :scroll-align-to-top="false">
      <!-- 模块信息 & 绑定数据库配置（紧凑布局） -->
      <div class="module-info-card">
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
                :disabled="isBindSuccessfully"
                filterable
                :placeholder="t('请选择字符集')"
                :prefix="t('字符集')"
                @change="handleValidate">
                <BkOption
                  v-for="(item, index) of characterSets"
                  :key="index"
                  :label="item"
                  :value="item" />
              </BkSelect>
            </FormItemWithHint>
          </div>
        </BkFormItem>
      </div>

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
              {{ tab.name }}
              <span
                v-if="(tabChangedCountMap[tab.conf_file] ?? 0) > 0"
                class="tab-modified-dot" />
            </template>
            <ParamTable
              :ref="(el: any) => setTableRef(tab.name, el)"
              :conf-type="tab.conf_type"
              :namespace="tab.namespace"
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
    <span class="create-module-nav-desc"> {{ t('业务') }} : {{ bizInfo.name }} </span>
  </Teleport>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { I18nT, useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { checkDbModuleUnique, createModules } from '@services/source/cmdb';
  import { getListClusterModuleConfFiles, saveModulesDeployInfo } from '@services/source/configs';

  import { useGlobalBizs } from '@stores';

  import { clusterTypeInfos, ClusterTypes, DBTypes } from '@common/const';

  import FormItemWithHint from '@components/form-item-with-hint/Index.vue';

  import { saveConfigureState } from '@views/db-configure/utils/configureState';

  import { random } from '@utils';

  import DbVersionSelect from '../components/DbVersionSelect.vue';
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
    isSubmitting.value = true;
    try {
      await formRef.value?.validate();

      // 新建模块
      const createResult = await createModules({
        alias_name: formData.alias_name,
        biz_id: bizId,
        cluster_type: ClusterTypes.TENDBCLUSTER,
        db_module_name: `${formData.alias_name}-${formData.spider_version}-${formData.db_version}-${formData.charset}`,
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
      width: 371px;
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
      min-width: 240px;
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

  .tab-modified-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    margin-left: 4px;
    background: #f59500;
    border-radius: 50%;
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
    background: #dcdee5;
    content: '';
    transform: translateY(-50%);
  }
</style>
