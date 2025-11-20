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
  <EditableColumn
    field="target_version"
    :label="t('目标版本')"
    :min-width="200"
    required
    :rules="rules">
    <EditableBlock>
      <div
        v-if="cluster.id"
        class="display-content">
        <div class="content-item">
          <div class="item-title">{{ t('绑定模块') }}：</div>
          <div class="item-content">
            <InnerSelect
              is-plain
              :list="moduleSelectList"
              :model-value="newDbModuleId"
              @change="(value) => handleModuleChange(value as number)">
              <template #default="{ item }">
                <div class="module-option-item">
                  <div class="module-option-label">
                    {{ item.name }}
                  </div>
                  <div class="module-opiton-info">
                    {{ item.info }}
                  </div>
                </div>
              </template>
              <template #footer>
                <div class="module-select-footer">
                  <BkButton
                    class="plus-button"
                    text
                    @click="handleCreateModule">
                    <DbIcon
                      class="footer-icon mr-4"
                      type="plus-8" />
                    {{ t('跳转新建模块') }}
                  </BkButton>
                  <BkButton
                    class="refresh-button"
                    text
                    @click="handleRefreshModule">
                    <DbIcon
                      class="footer-icon"
                      type="refresh-2" />
                  </BkButton>
                </div>
              </template>
            </InnerSelect>
          </div>
        </div>
        <div class="content-item">
          <div class="item-title">{{ t('数据库版本') }}：</div>
          <div class="item-content">
            {{ currentModule?.db_version || '' }}
          </div>
        </div>
        <div class="content-item">
          <div class="item-title">{{ t('字符集') }}：</div>
          <div class="item-content">
            {{ currentModule?.charset || '' }}
          </div>
        </div>
        <div class="content-item">
          <div class="item-title">{{ t('版本包文件') }}：</div>
          <div class="item-content">
            <InnerSelect
              is-plain
              :list="packageSelectList"
              :model-value="pkgId"
              @change="(value) => handlePackageChange(value as number)">
              <template #default="{ item, index }">
                <div class="target-version-select-option">
                  <div
                    v-overflow-tips
                    class="option-name">
                    {{ item.name }}
                  </div>
                  <BkTag
                    v-if="index === 0"
                    class="ml-4"
                    size="small"
                    theme="info">
                    {{ t('推荐') }}
                  </BkTag>
                </div>
              </template>
            </InnerSelect>
          </div>
        </div>
      </div>
    </EditableBlock>
  </EditableColumn>
</template>

<script lang="ts" setup>
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import { getVersionModules } from '@services/source/mysqlToolbox';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import InnerSelect from '@views/db-manage/mysql/MYSQL_LOCAL_UPGRADE/components/InnerSelect.vue';

  type ModulesInfo = ServiceReturnType<typeof getVersionModules>[0];

  interface Props {
    cluster: {
      cluster_type: ClusterTypes;
      id: number;
      master_domain: string;
      related_clusters: {
        id: number;
        master_domain: string;
      }[];
    } & TendbhaModel;
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<{
    charset: string;
    db_module_name: string;
    db_version: string;
    pkg_name: string;
  }>({
    required: true,
  });

  const newDbModuleId = defineModel<number>('newDbModuleId', {
    required: true,
  });

  const pkgId = defineModel<number>('pkgId', {
    required: true,
  });

  const { t } = useI18n();

  const route = useRoute();
  const router = useRouter();

  const packageSelectList = ref<
    {
      id: number;
      name: string;
    }[]
  >([]);
  const moduleSelectList = ref<
    Array<
      {
        id: number;
        info: string;
        name: string;
      } & ModulesInfo
    >
  >([]);
  const currentModule = ref<ModulesInfo>();

  const rules = [
    {
      message: t('请确保选填完整'),
      trigger: 'blur',
      validator: () => _.every(modelValue.value, _.identity),
    },
  ];

  const { run: fetchModuleList } = useRequest(getVersionModules, {
    manual: true,
    onSuccess(data) {
      moduleSelectList.value = data.map((module) => ({
        ...module,
        id: module.db_module_id,
        info: `${module.db_version || ''}，${module.charset || ''}`,
        name: module.db_module_name,
      }));

      const [firstModule] = moduleSelectList.value;
      if (firstModule) {
        newDbModuleId.value = firstModule.id;
        currentModule.value = firstModule;

        packageSelectList.value = firstModule.pkg_list.map((item) => ({
          id: item.pkg_id,
          name: item.pkg_name,
        }));

        const [firstPackage] = packageSelectList.value;
        if (firstPackage) {
          pkgId.value = firstPackage.id;
        }

        modelValue.value = {
          charset: firstModule.charset,
          db_module_name: firstModule.db_module_name,
          db_version: firstModule.db_version,
          pkg_name: firstPackage?.name || '',
        };
      }
    },
  });

  watch(
    () => props.cluster.id,
    () => {
      if (props.cluster.id) {
        fetchModuleList({
          cluster_id: props.cluster.id,
          higher_major_version: true,
          higher_sub_version: true,
        });
      }
    },
    {
      immediate: true,
    },
  );

  // 单据克隆回填
  watch(moduleSelectList, () => {
    if (modelValue.value.db_module_name) {
      pkgId.value = Number(_.get(_.find(packageSelectList.value, { name: modelValue.value.pkg_name }), 'id', 0));
      newDbModuleId.value = Number(
        _.get(_.find(moduleSelectList.value, { name: modelValue.value.db_module_name }), 'id', 0),
      );
    }
  });

  const handlePackageChange = (value: number) => {
    const findPackage = packageSelectList.value.find((item) => item.id === value);
    if (findPackage) {
      pkgId.value = value;
      modelValue.value.pkg_name = findPackage.name;
    }
  };

  const handleModuleChange = (value: number) => {
    newDbModuleId.value = value;
    const findModule = moduleSelectList.value.find((item) => item.id === value);
    if (!findModule) return;
    currentModule.value = findModule;
    const pkgList = findModule.pkg_list.map((item) => ({
      id: item.pkg_id,
      name: item.pkg_name,
    }));
    packageSelectList.value = pkgList;
    const [firstPackage] = pkgList;
    if (firstPackage) {
      pkgId.value = firstPackage.id;
    }

    modelValue.value = {
      charset: findModule.charset,
      db_module_name: findModule.db_module_name,
      db_version: findModule.db_version,
      pkg_name: firstPackage?.name || '',
    };
  };

  const handleCreateModule = () => {
    const url = router.resolve({
      name: 'SelfServiceCreateDbModule',
      params: {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        type:
          props.cluster.cluster_type === ClusterTypes.TENDBSINGLE
            ? TicketTypes.MYSQL_SINGLE_APPLY
            : TicketTypes.MYSQL_HA_APPLY,
      },
      query: {
        from: route.name as string,
      },
    });
    window.open(url.href, '_blank');
  };

  const handleRefreshModule = () => {
    fetchModuleList({
      cluster_id: props.cluster.id,
      higher_major_version: true,
      higher_sub_version: true,
    });
  };
</script>

<style lang="less" scoped>
  .display-content {
    display: flex;
    flex-direction: column;

    .content-item {
      display: flex;
      width: 100%;

      .item-title {
        width: 72px;
        text-align: right;
      }

      .item-content {
        flex: 1;
        display: flex;
        align-items: center;
        overflow: hidden;
      }
    }
  }
</style>
<style lang="less">
  .target-version-select-option {
    display: flex;
    align-items: center;

    .option-name {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .module-option-item {
    display: flex;
    width: 100%;

    .module-option-label {
      flex: 1;
      width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .module-opiton-info {
      margin-left: auto;
      color: #979ba5;
    }
  }

  .module-select-footer {
    display: flex;
    height: 100%;
    color: #63656e;
    align-items: center;
    justify-content: center;

    .plus-button {
      flex: 1;
      padding-left: 36px;
    }

    .refresh-button {
      width: 42px;
      border-left: 1px solid #dcdee5;
    }

    .footer-icon {
      font-size: 16px;
    }
  }
</style>
