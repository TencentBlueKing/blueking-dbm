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
  <BkLoading :loading="isLoading">
    <div
      v-overflow-tips
      class="capacity-box"
      :class="{ 'default-display': !data }">
      <span
        v-if="!data"
        style="color: #c4c6cc">
        {{ t('选择集群后自动生成') }}
      </span>
      <div
        v-else
        class="display-content">
        <div class="content-item">
          <div class="item-title">{{ t('数据库版本') }}：</div>
          <div class="item-content">
            <TableEditSelect
              ref="versionSelectRef"
              is-plain
              :list="versionSelectList"
              :model-value="localVersion"
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
              :model-value="localPackage"
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
            {{ charset }}
          </div>
        </div>
        <div class="content-item">
          <div class="item-title">{{ t('绑定模块') }}：</div>
          <div class="item-content">
            <span v-if="isCurrentMajorVersion">{{ data.moduleName }}</span>
            <TableEditSelect
              v-else
              ref="moduleSelectRef"
              is-plain
              :list="moduleSelectList"
              :model-value="localModule"
              :placeholder="t('请选择')"
              :pop-width="240"
              :rules="moduleRules"
              @change="(value) => handleModuleChange(value as number)">
              <template #default="{ item }: { item: IListItem | ServiceReturnType<typeof getModules>[number] }">
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
    </div>
  </BkLoading>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getModules } from '@services/source/cmdb';
  import { queryMysqlHigherVersionPkgList } from '@services/source/mysqlToolbox';

  import { TicketTypes } from '@common/const';

  import TableEditSelect, { type IListItem } from '@views/db-manage/mysql/common/edit/Select.vue';

  interface Props {
    isLoading: boolean;
    data?: {
      clusterId: number;
      clusterType: string;
      currentVersion: string;
      moduleName: string;
      moduleId: number;
    };
    targetVersion?: string;
    targetPackage?: number;
    targetModule?: number;
  }

  interface Emits {
    (e: 'module-change', value: string): void;
  }

  interface Exposes {
    getValue: () => Promise<{
      pkg_id: number;
      new_db_module_id?: number;
      display_info: {
        target_version: string;
        target_package: string;
        target_module_name?: string;
      };
    }>;
  }

  const props = withDefaults(defineProps<Props>(), {
    data: undefined,
    targetVersion: undefined,
    targetPackage: undefined,
    targetModule: undefined,
    isLocal: true,
  });
  const emits = defineEmits<Emits>();

  const route = useRoute();
  const router = useRouter();
  const { t } = useI18n();

  const versionSelectRef = ref<InstanceType<typeof TableEditSelect>>();
  const packageSelectRef = ref<InstanceType<typeof TableEditSelect>>();
  const moduleSelectRef = ref<InstanceType<typeof TableEditSelect>>();
  const localVersion = ref<string>('');
  const localPackage = ref<number | ''>('');
  const localModule = ref<number | ''>('');
  const versionSelectList = ref<IListItem[]>([]);
  const packageSelectList = ref<IListItem[]>([]);
  const moduleSelectList = ref<IListItem[]>([]);
  const charset = ref('');

  let versionMap = {} as Record<string, ServiceReturnType<typeof queryMysqlHigherVersionPkgList>>;

  const bizId = window.PROJECT_CONFIG.BIZ_ID;

  const versionRules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('数据库版本不能为空'),
    },
  ];

  const packageRules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('版本包文件不能为空'),
    },
  ];

  const moduleRules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('绑定模块不能为空'),
    },
  ];

  const isCurrentMajorVersion = computed(() => {
    if (localVersion.value) {
      return props.data?.currentVersion === localVersion.value;
    }
    return true;
  });

  const { run: queryMysqlHigherVersionPkgListRun } = useRequest(queryMysqlHigherVersionPkgList, {
    manual: true,
    onSuccess(versions) {
      versionMap = versions.reduce(
        (prevMap, versionItem) => {
          if (versionItem.version in prevMap) {
            prevMap[versionItem.version].push(versionItem);
            return prevMap;
          }
          return Object.assign(prevMap, { [versionItem.version]: [versionItem] });
        },
        {} as Record<string, ServiceReturnType<typeof queryMysqlHigherVersionPkgList>>,
      );

      versionSelectList.value = Object.keys(versionMap).map((version) => ({
        id: version,
        name: version,
      }));

      if (!localVersion.value && versionSelectList.value.length) {
        localVersion.value = versionSelectList.value[0].id as string;
        fetchModuleList();
      }

      if (localVersion.value) {
        packageSelectList.value = (versionMap[localVersion.value] || []).map((versionItem) => ({
          id: versionItem.pkg_id,
          name: versionItem.pkg_name,
        }));

        if (!localPackage.value && packageSelectList.value.length) {
          localPackage.value = packageSelectList.value[0].id as number;
        }
      }
    },
  });

  const { run: fetchModules } = useRequest(getModules, {
    manual: true,
    onSuccess(modules) {
      const moduleList: IListItem[] = [];
      const { moduleId } = props.data!;
      const currentModule = modules.find((moduleItem) => moduleItem.db_module_id === moduleId);
      if (currentModule) {
        const currentCharset = currentModule.db_module_info.conf_items.find(
          (confItem) => confItem.conf_name === 'charset',
        )!.conf_value;
        charset.value = currentCharset;
        emits('module-change', currentCharset);

        modules.forEach((moduleItem) => {
          let moduleItemCharset = '';
          let moduleItemDbVersion = '';
          moduleItem.db_module_info.conf_items.forEach((confItem) => {
            if (confItem.conf_name === 'charset') {
              moduleItemCharset = confItem.conf_value;
            } else if (confItem.conf_name === 'db_version') {
              moduleItemDbVersion = confItem.conf_value;
            }
          });
          if (moduleItemCharset === currentCharset && moduleItemDbVersion === localVersion.value) {
            moduleList.push({
              ...moduleItem,
              id: moduleItem.db_module_id,
              name: moduleItem.alias_name,
            });
          }
        });
        moduleSelectList.value = moduleList;

        if (moduleList.length === 1) {
          localModule.value = moduleList[0].id as number;
        }
      }
    },
  });

  watch(
    () => props.data?.clusterId,
    () => {
      if (props.data?.clusterId) {
        queryMysqlHigherVersionPkgListRun({
          cluster_id: props.data.clusterId,
          higher_all_version: true,
        });
      }
    },
    {
      immediate: true,
    },
  );

  watch(
    () => props.targetVersion,
    () => {
      if (props.targetVersion) {
        localVersion.value = props.targetVersion;
      }
    },
    {
      immediate: true,
    },
  );

  watch(
    () => props.targetPackage,
    () => {
      if (props.targetPackage) {
        localPackage.value = props.targetPackage;
      }
    },
    {
      immediate: true,
    },
  );

  watch(
    () => props.targetModule,
    () => {
      if (props.targetModule) {
        localModule.value = props.targetModule;
      }
    },
    {
      immediate: true,
    },
  );

  watch(localVersion, () => {
    if (localVersion.value) {
      packageSelectList.value = (versionMap[localVersion.value] || []).map((versionItem) => ({
        id: versionItem.pkg_id,
        name: versionItem.pkg_name,
      }));

      if (packageSelectList.value.length) {
        localPackage.value = packageSelectList.value[0].id as number;
      }
    }
  });

  const fetchModuleList = () => {
    if (props.data) {
      fetchModules({
        bk_biz_id: bizId,
        cluster_type: props.data.clusterType,
      });
    }
  };

  watch(
    () => props.data?.moduleName,
    () => {
      if (props.data?.moduleName) {
        fetchModuleList();
      }
    },
    {
      immediate: true,
    },
  );

  const handleVersionChange = (value: string) => {
    localVersion.value = value;
    localModule.value = '';
    fetchModuleList();
  };

  const handlePackageChange = (value: number) => {
    localPackage.value = value;
  };

  const handleModuleChange = (value: number) => {
    localModule.value = value;
  };

  const handleCreateModule = () => {
    const url = router.resolve({
      name: 'SelfServiceCreateDbModule',
      params: {
        type: TicketTypes.MYSQL_SINGLE_APPLY,
        bk_biz_id: bizId,
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

  defineExpose<Exposes>({
    getValue() {
      if (isCurrentMajorVersion.value) {
        return packageSelectRef.value!.getValue().then(() => ({
          pkg_id: localPackage.value as number,
          display_info: {
            target_version: localVersion.value,
            target_package: packageSelectList.value.find((item) => item.id === localPackage.value)?.name || '',
          },
        }));
      }
      return Promise.all([packageSelectRef.value!.getValue(), moduleSelectRef.value!.getValue()]).then(() => ({
        pkg_id: localPackage.value as number,
        new_db_module_id: localModule.value,
        display_info: {
          target_version: localVersion.value,
          target_package: packageSelectList.value.find((item) => item.id === localPackage.value)?.name || '',
          target_module_name: moduleSelectList.value.find((item) => item.id === localModule.value)?.name || '',
        },
      }));
    },
  });
</script>

<style lang="less" scoped>
  .capacity-box {
    padding: 8px 16px;
    overflow: hidden;
    line-height: 26px;
    color: #63656e;
    text-overflow: ellipsis;
    white-space: nowrap;

    .display-content {
      display: flex;
      flex-direction: column;

      .content-item {
        display: flex;
        align-items: center;
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
