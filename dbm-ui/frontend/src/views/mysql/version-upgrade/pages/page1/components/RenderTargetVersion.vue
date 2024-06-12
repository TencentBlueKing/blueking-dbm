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
            <span v-if="isLocal">{{ data.currentVersion }}</span>
            <TableEditSelect
              v-else
              ref="versionSelectRef"
              is-plain
              :list="versionSelectList"
              :model-value="localVersion"
              :placeholder="t('请选择')"
              :pop-width="240"
              :rules="versionRules"
              @change="(value) => handleVersionChange(value as string)">
              <template #default="{ item }">
                <span>{{ item.name }}</span>
                <!-- <BkTag
                  v-if="item.name.split('-')[1] === data.currentVersion.split('-')[1]"
                  class="ml-4"
                  size="small"
                  theme="info">
                  {{ t('当前版本') }}
                </BkTag> -->
              </template>
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
              <template #default="{ item }">
                <span>{{ item.name }}</span>
                <!-- <BkTag
                  v-if="item.name.split('-')[1] === data.currentVersion.split('-')[1]"
                  class="ml-4"
                  size="small"
                  theme="info">
                  {{ t('当前版本') }}
                </BkTag> -->
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
            <span v-if="isLocal">{{ data.moduleName }}</span>
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
  import { getPackages } from '@services/source/package';

  import { ClusterTypes, TicketTypes } from '@common/const';
  import { versionRegex } from '@common/regex';

  import TableEditSelect, { type IListItem } from '@views/mysql/common/edit/Select.vue';

  import { compareVersions } from '@utils';

  interface Props {
    isLoading: boolean;
    data?: {
      clusterId: number;
      clusterType: string;
      currentVersion: string;
      moduleName: string;
    };
    targetVersion?: string;
    targetPackage?: number;
    targetModule?: number;
    isLocal?: boolean; // 原地升级 或 迁移升级
  }

  interface Emits {
    (e: 'module-change', value: string): void;
  }

  interface Exposes {
    getValue: () => Promise<{
      pkg_id: number;
      new_db_module_id: number;
      display_info: {
        target_version: string;
        target_module_name: string;
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

  const { data: packageDataList, run: fetchClusterVersions } = useRequest(getPackages, {
    manual: true,
    onSuccess(versions) {
      const currentVersion = props.data!.currentVersion.match(versionRegex);
      if (currentVersion) {
        const versionMap = versions.results.reduce(
          (prevVerisonMap, versionItem) => {
            const version = versionItem.version.match(versionRegex);
            if (prevVerisonMap[versionItem.version]) {
              return prevVerisonMap;
            }
            if (version && compareVersions(version[0], currentVersion[0]) === 1) {
              return { ...prevVerisonMap, [versionItem.version]: versionItem.version };
            }
            return prevVerisonMap;
          },
          {} as Record<string, string>,
        );
        versionSelectList.value = Object.keys(versionMap).reduce(
          (prevList, mapItem) => [
            ...prevList,
            {
              id: mapItem,
              name: mapItem,
            },
          ],
          [] as [] as IListItem[],
        );
      }
    },
  });

  const { run: fetchModules } = useRequest(getModules, {
    manual: true,
    onSuccess(modules) {
      const moduleList: IListItem[] = [];
      const { moduleName } = props.data!;
      const currentModule = modules.find((moduleItem) => moduleItem.name === moduleName);
      if (currentModule) {
        const currentCharset = currentModule.db_module_info.conf_items.find(
          (confItem) => confItem.conf_name === 'charset',
        )!.conf_value;
        charset.value = currentCharset;
        emits('module-change', currentCharset);

        modules.forEach((moduleItem) => {
          const charset = currentModule.db_module_info.conf_items.find(
            (confItem) => confItem.conf_name === 'charset',
          )!.conf_value;
          if (charset === currentCharset) {
            moduleList.push({
              ...moduleItem,
              id: moduleItem.db_module_id,
              name: moduleItem.name,
            });
          }
        });
        moduleSelectList.value = moduleList;
      }
    },
  });

  watch(
    () => props.data?.clusterId,
    () => {
      if (props.data?.clusterId) {
        fetchClusterVersions({
          pkg_type: 'mysql',
          db_type: 'mysql',
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

  watch([() => props.data?.currentVersion, packageDataList], () => {
    if (props.data?.currentVersion) {
      const packageList = packageDataList.value?.results || [];
      const versionItem = packageList.find((item) => item.version === props.data?.currentVersion);
      if (versionItem) {
        // 当前大版本下高于当前小版本的所有版本
        const currentVersion = versionItem.name.match(versionRegex)![0];
        const nextMinorVersionList = currentVersion.split('.');
        nextMinorVersionList[1] = String(Number(nextMinorVersionList[1]) + 1);
        const nextMinorVersion = nextMinorVersionList.join('.');

        packageSelectList.value = packageList.reduce((prevList, versionItem) => {
          const version = versionItem.name.match(versionRegex);
          if (
            version &&
            compareVersions(version[0], currentVersion) === 1 &&
            compareVersions(version[0], nextMinorVersion) === -1
          ) {
            return [
              ...prevList,
              {
                id: versionItem.id,
                name: versionItem.name,
              },
            ];
          }
          return prevList;
        }, [] as IListItem[]);
      }
    } else {
      if (props.isLocal) {
        packageSelectList.value = [];
      }
    }
  });

  watch([localVersion, packageDataList], () => {
    if (localVersion.value) {
      const packageList = packageDataList.value?.results || [];
      const versionItem = packageList.find((item) => item.version === localVersion.value);
      if (versionItem) {
        // 当前大版本下的所有小版本
        const currentVersion = versionItem.version.match(versionRegex)![0];
        packageSelectList.value = packageList.reduce((prevList, versionItem) => {
          if (versionItem.name.includes(currentVersion)) {
            return [
              ...prevList,
              {
                id: versionItem.id,
                name: versionItem.name,
              },
            ];
          }
          return prevList;
        }, [] as IListItem[]);
      }
    } else {
      if (!props.isLocal) {
        localPackage.value = '';
        packageSelectList.value = [];
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
        type:
          props.data!.clusterType === ClusterTypes.TENDBSINGLE
            ? TicketTypes.MYSQL_SINGLE_APPLY
            : TicketTypes.MYSQL_HA_APPLY,
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
      return Promise.all([packageSelectRef.value!.getValue(), moduleSelectRef.value?.getValue()]).then(() => ({
        pkg_id: localPackage.value as number,
        new_db_module_id: localModule.value as number,
        display_info: {
          target_version: localVersion.value,
          target_module_name: moduleSelectList.value.find((item) => item.id === localModule.value)?.name || '',
        },
      }));
    },
  });
</script>

<style lang="less" scoped>
  .capacity-box {
    padding: 11px 16px;
    overflow: hidden;
    line-height: 24px;
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
    align-items: center;
    color: #63656e;
    height: 100%;
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
