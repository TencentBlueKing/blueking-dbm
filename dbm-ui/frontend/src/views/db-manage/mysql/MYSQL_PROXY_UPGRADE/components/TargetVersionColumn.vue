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
    field="cluster.master_domain"
    :label="t('目标版本')"
    :min-width="200"
    required>
    <EditableBlock v-if="cluster.id">
      <div class="display-content">
        <div class="content-item">
          <div class="item-title">{{ t('数据库版本') }}：</div>
          <div class="item-content">
            <TableEditSelect
              ref="versionSelectRef"
              is-plain
              :list="versionSelectList"
              :model-value="modelValue.target_version"
              :placeholder="t('请选择')"
              :pop-width="240"
              :rules="versionRules"
              @change="(value) => handleVersionChange(value as string)">
            </TableEditSelect>
          </div>
        </div>
        <div class="content-item">
          <div class="item-title">{{ t('版本包文件') }}：</div>
          <div class="item-content">
            <TableEditSelect
              ref="packageSelectRef"
              is-plain
              :list="packageSelectList"
              :model-value="modelValue.pkg_id"
              :placeholder="t('请选择')"
              :pop-width="240"
              :rules="packageRules"
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
            </TableEditSelect>
          </div>
        </div>
        <div class="content-item">
          <div class="item-title">{{ t('字符集') }}：</div>
          <div class="item-content">
            {{ modelValue.charset }}
          </div>
        </div>
        <div class="content-item">
          <div class="item-title">{{ t('绑定模块') }}：</div>
          <div class="item-content">
            <span v-if="cluster.current_version === modelValue.target_version">{{ cluster.db_module_name }}</span>
            <TableEditSelect
              v-else
              ref="moduleSelectRef"
              is-plain
              :list="moduleSelectList"
              :model-value="modelValue.new_db_module_id"
              :placeholder="t('请选择')"
              :pop-width="240"
              :rules="moduleRules"
              @change="(value) => handleModuleChange(value as number)">
              <template #default="{ item }: { item: ServiceReturnType<typeof getModules>[number] }">
                <AuthTemplate
                  action-id="dbconfig_view"
                  :biz-id="item.bk_biz_id"
                  :permission="item.permission.dbconfig_view"
                  resource="mysql"
                  style="flex: 1">
                  <template #default="{ permission }">
                    <div
                      class="module-select-item"
                      :class="{ 'not-permission': !permission }"
                      data-id="dbconfig_view">
                      {{ item.name }}
                    </div>
                  </template>
                </AuthTemplate>
              </template>
              <template #footer>
                <div class="module-select-footer">
                  <AuthButton
                    action-id="dbconfig_edit"
                    :biz-id="bizId"
                    class="plus-button"
                    resource="mysql"
                    text
                    @click="handleCreateModule">
                    <DbIcon
                      class="footer-icon mr-4"
                      type="plus-8" />
                    {{ t('跳转新建模块') }}
                  </AuthButton>
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
            </TableEditSelect>
          </div>
        </div>
      </div>
    </EditableBlock>
    <EditableBlock
      v-else
      :placeholder="t('自动生成')" />
  </EditableColumn>
</template>

<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getModules } from '@services/source/cmdb';
  import { queryMysqlHigherVersionPkgList } from '@services/source/mysqlToolbox';

  import { TicketTypes } from '@common/const';

  import TableEditSelect, { type IListItem } from '@views/db-manage/mysql/common/edit/Select.vue';

  interface Props {
    cluster: {
      bk_cloud_id: number;
      cluster_type: string;
      current_version: string;
      db_module_id: number;
      db_module_name: string;
      id: number;
      master_domain: string;
      package_version: string;
      related_clusters: {
        id: number;
        master_domain: string;
      }[];
    };
    /**
     * 代表是否跨版本升级, 默认false
     */
    higherMajorVersion?: boolean;
  }

  const props = withDefaults(defineProps<Props>(), {
    higherMajorVersion: false,
  });

  const modelValue = defineModel<{
    charset: string;
    new_db_module_id: string | number;
    pkg_id: number;
    target_module_name: string;
    target_package: string;
    target_version: string;
  }>({
    default: () => ({
      charset: '',
      new_db_module_id: '',
      pkg_id: 0,
      target_module_name: '',
      target_package: '',
      target_version: '',
    }),
  });

  const { t } = useI18n();

  const route = useRoute();
  const router = useRouter();

  const bizId = window.PROJECT_CONFIG.BIZ_ID;

  const versionSelectList = ref<IListItem[]>([]);
  const packageSelectList = ref<IListItem[]>([]);
  const moduleSelectList = ref<IListItem[]>([]);

  const versionRules = [
    {
      message: t('数据库版本不能为空'),
      validator: (value: string) => Boolean(value),
    },
  ];
  const packageRules = [
    {
      message: t('版本包文件不能为空'),
      validator: (value: string) => Boolean(value),
    },
  ];
  const moduleRules = [
    {
      message: t('绑定模块不能为空'),
      validator: (value: string) => Boolean(value),
    },
  ];

  const { run: queryMysqlHigherVersionPkgListRun } = useRequest(queryMysqlHigherVersionPkgList, {
    manual: true,
    onSuccess(versions) {
      versionSelectList.value = versions.map((item) => ({
        id: item.version,
        name: item.version,
      }));
      packageSelectList.value = versions.map((packageItem) => ({
        id: packageItem.pkg_id,
        name: packageItem.pkg_name,
      }));
      if (versions.length) {
        const [lastestVersion] = versions;
        modelValue.value = {
          charset: '',
          new_db_module_id: '',
          pkg_id: lastestVersion.pkg_id,
          target_module_name: '',
          target_package: lastestVersion.pkg_name,
          target_version: lastestVersion.version,
        };

        fetchModuleList();
      }
    },
  });

  const { run: fetchModules } = useRequest(getModules, {
    manual: true,
    onSuccess(modules) {
      const currentModule = modules.find((moduleItem) => moduleItem.db_module_id === props.cluster.db_module_id);
      if (currentModule) {
        modelValue.value.charset = currentModule.db_module_info.conf_items[0]?.conf_value;

        moduleSelectList.value = modules
          .filter((item) => item.db_module_info.conf_items[1].conf_value === modelValue.value.target_version)
          .map((item) => ({
            ...item,
            id: item.db_module_id,
          }));
        modelValue.value.new_db_module_id = moduleSelectList.value[0]?.id;
        modelValue.value.target_module_name = moduleSelectList.value[0]?.name;
      }
    },
  });

  function fetchModuleList() {
    if (props.cluster) {
      fetchModules({
        bk_biz_id: bizId,
        cluster_type: props.cluster.cluster_type,
      });
    }
  }

  watch(
    () => props.cluster,
    () => {
      if (props.cluster.id) {
        queryMysqlHigherVersionPkgListRun({
          cluster_id: props.cluster.id,
          higher_major_version: props.higherMajorVersion,
        });
      }
    },
    {
      immediate: true,
    },
  );

  const handleVersionChange = (value: string) => {
    modelValue.value.target_version = value;
    fetchModuleList();
  };

  const handlePackageChange = (value: number) => {
    const findVersion = packageSelectList.value.find((item) => item.id === value);
    if (findVersion) {
      modelValue.value = {
        ...modelValue.value,
        pkg_id: findVersion.id as number,
        target_package: findVersion.name,
      };
    }
  };

  const handleModuleChange = (value: number) => {
    modelValue.value.new_db_module_id = value;
    modelValue.value.target_module_name = moduleSelectList.value.find((item) => item.id === value)?.name || '';
  };

  const handleCreateModule = () => {
    const url = router.resolve({
      name: 'SelfServiceCreateDbModule',
      params: {
        bk_biz_id: bizId,
        type: TicketTypes.MYSQL_SINGLE_APPLY,
      },
      query: {
        from: route.name as string,
      },
    });
    window.open(url.href, '_blank');
  };

  const handleRefreshModule = () => {
    fetchModuleList();
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

        .percent {
          margin-left: 4px;
          font-size: 12px;
          font-weight: bold;
          color: #313238;
        }

        .spec {
          margin-left: 2px;
          font-size: 12px;
          color: #979ba5;
        }

        :deep(.render-spec-box) {
          height: 22px;
          padding: 0;
        }
      }
    }
  }

  .default-display {
    cursor: not-allowed;
    background: #fafbfd;
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

  .module-select-item {
    display: flex;
    align-items: center;
    width: 100%;
    user-select: none;

    .not-permission {
      * {
        color: #70737a !important;
      }
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
