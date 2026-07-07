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
  <div class="version-files-page">
    <DbTab
      v-model="dbTypeActive"
      :exclude="[DBTypes.TENDBCLUSTER, DBTypes.K8S_SURREALDB, DBTypes.K8S_QRRANT]" />
    <div
      v-if="renderPkgTypeList.length > 0"
      class="veriosn-content-main">
      <div
        v-bk-loading="{ loading: pkgTypeListLoading }"
        class="pkg-tab-main-container">
        <BkTab
          :key="dbTypeActive"
          v-model:active="pkgActive"
          class="pkg-tab-main"
          :class="{ 'pkg-tab-main-scroll': isPkgTabScroll }"
          type="card-tab"
          @change="handlePkgTabChange">
          <template #add>
            <AuthTemplate
              action-id="package_manage"
              class="manage-pkg-type-main"
              :permission="hasPackageManagePermission"
              :resource="dbTypeActive"
              @click="handleCreatePkgType">
              <div class="manage-pkg-type-icon">
                <DbIcon type="add" />
              </div>
            </AuthTemplate>
          </template>
          <BkTabPanel
            v-for="tab of renderPkgTypeList"
            :key="tab.name"
            :label="tab.label"
            :name="tab.name">
            <template #label>
              <div class="tab-label-main">
                <span>{{ tab.label }}</span>
                <BkDropdown trigger="click">
                  <div class="tab-label-more">
                    <DbIcon type="more" />
                  </div>
                  <template #content>
                    <BkDropdownMenu>
                      <BkDropdownItem>
                        <AuthButton
                          action-id="package_manage"
                          :permission="hasPackageManagePermission"
                          :resource="dbTypeActive"
                          text
                          @click="() => handleEditPkgType(tab)">
                          {{ t('编辑包类型') }}
                        </AuthButton>
                      </BkDropdownItem>
                      <BkPopConfirm
                        :confirm-config="{
                          theme: 'danger',
                        }"
                        :confirm-text="t('删除')"
                        :content="t('删除操作无法撤回，请谨慎操作！')"
                        :popover-options="{
                          placement: 'bottom-start',
                        }"
                        :title="t('确认删除该包类型？')"
                        trigger="click"
                        width="280"
                        @confirm="() => handleConfirmDeletePkgType(tab)">
                        <BkDropdownItem
                          v-bk-tooltips="{
                            content: t('该包类型存在 n 个版本，请清理后再操作', {
                              n: pkgTypeItemMap[tab.name].related_versions,
                            }),
                            disabled: pkgTypeItemMap[tab.name].can_delete,
                            placement: 'right',
                          }">
                          <AuthButton
                            action-id="package_manage"
                            :disabled="!pkgTypeItemMap[tab.name].can_delete"
                            :permission="hasPackageManagePermission"
                            :resource="dbTypeActive"
                            text>
                            {{ t('删除包类型') }}
                          </AuthButton>
                        </BkDropdownItem>
                      </BkPopConfirm>
                    </BkDropdownMenu>
                  </template>
                </BkDropdown>
              </div>
            </template>
          </BkTabPanel>
        </BkTab>
      </div>
      <div class="content-main">
        <List
          :db-type="dbTypeActive"
          :has-package-manage-permission="hasPackageManagePermission"
          :pkg-label-map="pkgLabelMap"
          :pkg-type="pkgActive"
          :tabs="renderTabs"
          :version-num="currentPkgType?.version_num || 3"
          @refresh-pkg-type-list="handleGetPkgTypeList" />
      </div>
    </div>
    <BkException
      v-else
      class="pkg-type-empty-main"
      type="empty">
      <span>{{ t('该数据库类型下暂无包类型') }}</span>
      <span class="ml-4 mr-4">,</span>
      <span class="mr-4">{{ t('立即') }}</span>
      <BkButton
        size="small"
        text
        theme="primary"
        @click="handleCreatePkgType">
        {{ t('新建包类型') }}
      </BkButton>
    </BkException>
  </div>
  <EditPkgType
    v-model:is-show="isShowPkgTypeManage"
    :data="currentPkgType"
    :db-type="dbTypeActive"
    :existed-identifier-list="existedIdentifierList"
    :is-edit="isEditPkgType"
    :total-list="pkgTypeList || []"
    @success="handleGetPkgTypeList" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRoute, useRouter } from 'vue-router';

  import type {
    ControllerBaseInfo,
    ExtractedControllerDataKeys,
    FunctionKeys,
  } from '@services/model/function-controller/functionController';
  import { simpleCheckAllowed } from '@services/source/iam';
  import { getPkgTypeList, updatePkgType } from '@services/source/version';

  import { useFunController } from '@stores';

  import { DBTypes } from '@common/const';

  import DbTab from '@components/db-tab/Index.vue';

  import { messageSuccess } from '@utils';

  import EditPkgType from './components/EditPkgType.vue';
  import List from './components/list/Index.vue';

  export interface TabItem {
    children: {
      controllerId?: FunctionKeys;
      label: string;
      name: string;
    }[];
    controller: {
      id?: FunctionKeys;
      moduleId: ExtractedControllerDataKeys;
    };
    label: string;
    name: string;
  }

  export type PkgTypeItem = ServiceReturnType<typeof getPkgTypeList>[number];

  const { t } = useI18n();
  const funControllerStore = useFunController();
  const route = useRoute();
  const router = useRouter();

  const tabChildrenControllerIdMap: Record<string, FunctionKeys> = {
    tendisplus: 'PredixyTendisplusCluster',
    tendisssd: 'TwemproxyTendisSSDInstance',
    twemproxy: 'TwemproxyRedisInstance',
  };

  const pkgActive = ref('');
  const dbTypeActive = ref<DBTypes>(DBTypes.MYSQL);
  const isShowPkgTypeManage = ref(false);
  const hasPackageManagePermission = ref(false);
  const isEditPkgType = ref(false);
  const currentPkgType = ref<PkgTypeItem>();
  const isPkgTabScroll = ref(false);
  const tabs = ref<TabItem[]>([
    {
      children: [
        {
          label: 'MySQL',
          name: DBTypes.MYSQL,
        },
      ],
      controller: {
        moduleId: 'mysql',
      },
      label: 'MySQL',
      name: DBTypes.MYSQL,
    },
    // {
    //   children: [
    //     {
    //       label: 'TenDBCluster',
    //       name: DBTypes.TENDBCLUSTER,
    //     },
    //   ],
    //   controller: {
    //     moduleId: 'mysql',
    //   },
    //   label: 'TenDBCluster',
    //   name: DBTypes.TENDBCLUSTER,
    // },
    {
      children: [
        {
          label: 'Redis',
          name: DBTypes.REDIS,
        },
      ],
      controller: {
        moduleId: 'redis',
      },
      label: 'Redis',
      name: DBTypes.REDIS,
    },
    {
      children: [
        {
          label: 'ES',
          name: DBTypes.ES,
        },
      ],
      controller: {
        id: 'es',
        moduleId: 'bigdata',
      },
      label: 'ES',
      name: DBTypes.ES,
    },
    {
      children: [
        {
          label: 'Kafka',
          name: DBTypes.KAFKA,
        },
      ],
      controller: {
        id: 'kafka',
        moduleId: 'bigdata',
      },
      label: 'Kafka',
      name: DBTypes.KAFKA,
    },
    {
      children: [
        {
          label: 'HDFS',
          name: DBTypes.HDFS,
        },
      ],
      controller: {
        id: 'hdfs',
        moduleId: 'bigdata',
      },
      label: 'HDFS',
      name: DBTypes.HDFS,
    },
    {
      children: [
        {
          label: 'Plusar',
          name: DBTypes.PULSAR,
        },
      ],
      controller: {
        id: 'pulsar',
        moduleId: 'bigdata',
      },
      label: 'Pulsar',
      name: DBTypes.PULSAR,
    },
    {
      children: [
        {
          label: 'InfluxDB',
          name: DBTypes.INFLUXDB,
        },
      ],
      controller: {
        id: 'influxdb',
        moduleId: 'bigdata',
      },
      label: 'InfluxDB',
      name: DBTypes.INFLUXDB,
    },
    {
      children: [
        {
          label: 'Riak',
          name: DBTypes.RIAK,
        },
      ],
      controller: {
        id: 'riak',
        moduleId: 'bigdata',
      },
      label: 'Riak',
      name: DBTypes.RIAK,
    },
    {
      children: [
        {
          label: 'MongoDB',
          name: DBTypes.MONGODB,
        },
      ],
      controller: {
        moduleId: 'mongodb',
      },
      label: 'MongoDB',
      name: DBTypes.MONGODB,
    },
    {
      children: [
        {
          label: 'SQLServer',
          name: DBTypes.SQLSERVER,
        },
      ],
      controller: {
        moduleId: 'sqlserver',
      },
      label: 'SQLServer',
      name: DBTypes.SQLSERVER,
    },
    {
      children: [
        {
          label: 'Doris',
          name: DBTypes.DORIS,
        },
      ],
      controller: {
        id: 'doris',
        moduleId: 'bigdata',
      },
      label: 'Doris',
      name: DBTypes.DORIS,
    },
    {
      children: [
        {
          label: 'Oracle',
          name: DBTypes.ORACLE,
        },
      ],
      controller: {
        moduleId: 'oracle',
      },
      label: 'Oracle',
      name: DBTypes.ORACLE,
    },
  ]);

  const existedIdentifierList = computed(() => pkgTypeList.value?.map((item) => item.value.toLocaleLowerCase()) || []);

  const pkgLabelMap = computed(() =>
    tabs.value.reduce<Record<string, string>>((dataMap, item) => {
      item.children.forEach((child) => {
        Object.assign(dataMap, {
          [child.name]: child.label,
        });
      });
      return dataMap;
    }, {}),
  );

  const renderTabs = computed(() =>
    tabs.value.reduce<TabItem[]>((result, item) => {
      const { id, moduleId } = item.controller;
      const data = funControllerStore.funControllerData[moduleId] as any;
      // 整个模块没有开启
      if (!data || data.is_enabled !== true) {
        return result;
      }
      const children = data.children as Record<FunctionKeys, ControllerBaseInfo>;
      // 模块中的功能没开启
      if (id && !children[id]?.is_enabled) {
        return result;
      }
      const tabChildren = item.children.filter((child) => {
        // 不需要校验功能是否开启
        if (child.controllerId === undefined) {
          return true;
        }
        return children[child.controllerId]?.is_enabled;
      });
      result.push({
        ...item,
        children: tabChildren,
      });
      return result;
    }, []),
  );

  const activeTabInfo = computed(() => {
    const tabList = renderTabs.value.find((item) => item.name === dbTypeActive.value);
    return tabList
      ? tabList
      : {
          children: [],
          label: '',
          name: '',
        };
  });

  const renderPkgTypeList = computed(() => activeTabInfo.value?.children || []);
  const pkgTypeItemMap = computed(
    () =>
      pkgTypeList.value?.reduce<Record<string, PkgTypeItem>>((acc, item) => {
        Object.assign(acc, {
          [item.value]: item,
        });
        return acc;
      }, {}) || {},
  );

  const {
    data: pkgTypeList,
    loading: pkgTypeListLoading,
    run: fetchPkgTypeList,
  } = useRequest(getPkgTypeList, {
    manual: true,
    onSuccess(data) {
      const targetTabIndex = tabs.value.findIndex((item) => item.name === dbTypeActive.value);
      if (targetTabIndex !== -1) {
        tabs.value[targetTabIndex].children = data.map((item) => ({
          controllerId: tabChildrenControllerIdMap[item.value],
          label: item.name,
          name: item.value,
        }));
      }
      nextTick(() => {
        if (newCreatePkgType) {
          pkgActive.value = newCreatePkgType;
          newCreatePkgType = undefined;
        }
        handlePkgTabChange(pkgActive.value);
      });
      setTimeout(() => {
        checkPkgTabScroll();
      }, 1000);
    },
  });

  const { run: runDeletePkgType } = useRequest(updatePkgType, {
    manual: true,
    onSuccess() {
      messageSuccess(t('操作成功'));
      handleGetPkgTypeList();
    },
  });

  let isFirstLoad = true;
  let newCreatePkgType: string | undefined = undefined;

  const handlePkgTabChange = (name: string) => {
    currentPkgType.value = pkgTypeList.value?.find((item) => item.value === name);
  };

  const handleConfirmDeletePkgType = (tab: { label: string; name: string }) => {
    if (!pkgTypeList.value?.length) {
      return;
    }

    runDeletePkgType({
      db_type: dbTypeActive.value,
      items: pkgTypeList.value.filter((item) => item.value !== tab.name),
    });
  };

  const handleEditPkgType = () => {
    isEditPkgType.value = true;
    isShowPkgTypeManage.value = true;
  };

  const handleGetPkgTypeList = (data?: { name: string; value: string }) => {
    if (data) {
      newCreatePkgType = data.value;
    }
    fetchPkgTypeList({
      db_type: dbTypeActive.value,
    });
  };

  const checkPackagePermission = async () => {
    const hasPackageViewPermission = await simpleCheckAllowed(
      {
        action_id: 'package_view',
        is_raise_exception: true,
        resource_id: dbTypeActive.value,
      },
      {
        permission: 'page',
      },
    );
    if (!hasPackageViewPermission) {
      return;
    }

    hasPackageManagePermission.value = await simpleCheckAllowed({
      action_id: 'package_manage',
      resource_id: dbTypeActive.value,
    });
  };

  watch(
    dbTypeActive,
    () => {
      handleGetPkgTypeList();
      checkPackagePermission();
    },
    {
      immediate: true,
    },
  );

  watch([dbTypeActive, pkgActive], () => {
    if (!dbTypeActive.value || !pkgActive.value) {
      return;
    }

    const { dbType, pkgType } = route.query;
    if (dbType === dbTypeActive.value && pkgType === pkgActive.value) {
      return;
    }

    router.replace({
      query: {
        ...route.query,
        dbType: dbTypeActive.value,
        pkgType: pkgActive.value,
      },
    });
  });

  watch(pkgTypeList, () => {
    nextTick(() => {
      checkPkgTabScroll();
    });

    if (!pkgTypeList.value?.length) {
      return;
    }

    if (isFirstLoad) {
      isFirstLoad = false;
      return;
    }

    const valueList = pkgTypeList.value.map((item) => item.value);
    if (pkgActive.value && valueList.includes(pkgActive.value)) {
      return;
    }

    pkgActive.value = pkgTypeList.value[0]?.value || '';
  });

  const handleCreatePkgType = () => {
    isEditPkgType.value = false;
    currentPkgType.value = undefined;
    isShowPkgTypeManage.value = true;
  };

  const checkPkgTabScroll = () => {
    const tabListDom = document.querySelector('.tab-header-auto');
    const scrollWidth = tabListDom?.scrollWidth || 0;
    const clientWidth = tabListDom?.clientWidth || 0;
    isPkgTabScroll.value = scrollWidth > clientWidth;
  };

  onMounted(() => {
    const { dbType } = route.query;
    if (dbType) {
      dbTypeActive.value = dbType as DBTypes;
    }
    const pkgType = route.query.pkgType as string;
    if (pkgType) {
      setTimeout(() => {
        pkgActive.value = pkgType;
        handlePkgTabChange(pkgType);
      }, 500);
    }

    window.addEventListener('resize', checkPkgTabScroll);
  });

  onBeforeUnmount(() => {
    window.removeEventListener('resize', checkPkgTabScroll);
  });
</script>
<style lang="less">
  .version-files-page {
    display: flex;
    height: 100%;
    flex-direction: column;

    .veriosn-content-main {
      display: flex;
      padding: 20px 24px;
      overflow: hidden;
      flex: 1;
      flex-direction: column;

      .pkg-tab-main-container {
        position: relative;
        height: 42px;

        .bk-tab-header-operation {
          display: flex;
          width: 42px;
          height: 42px;
          background: #f0f1f5;
          border-radius: 0 4px 0 0;
          justify-content: center;
          align-items: center;

          .bk-tab-header-item {
            padding: 0;

            &::after {
              display: none;
            }
          }
        }
      }

      .pkg-tab-main {
        &.pkg-tab-main-scroll {
          .bk-tab-header-operation {
            box-shadow: -2px 0 4px 0 #0000001a;
          }
        }

        .bk-tab-content {
          display: none;
        }

        .bk-tab-header--active {
          .tab-label-more {
            display: flex !important;
          }
        }

        .tab-label-main {
          display: flex;
          align-items: center;
          justify-content: center;

          .tab-label-more {
            justify-content: center;
            align-items: center;
            display: none;
            width: 26px;
            height: 26px;
            margin-left: 8px;
            border-radius: 2px;

            &:hover {
              background: #e1ecff;
            }
          }
        }
      }

      .manage-pkg-type-main {
        display: flex;
        width: 42px;
        height: 42px;
        justify-content: center;
        align-items: center;

        .manage-pkg-type-icon {
          display: flex;
          width: 26px;
          height: 26px;
          color: #3a84ff;
          border-radius: 2px;
          justify-content: center;
          align-items: center;

          &:hover {
            background: #e1ecff;
          }
        }
      }

      .content-main {
        overflow: hidden;
        background-color: #fff;
        flex: 1;
      }
    }
  }
</style>
