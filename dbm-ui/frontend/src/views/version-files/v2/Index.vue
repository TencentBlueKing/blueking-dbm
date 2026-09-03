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
      :exclude="excludeDbTypes" />
    <!-- 包类型还在请求中时先展示骨架，避免闪一下「暂无包类型」空态 -->
    <div
      v-if="pkgTypeListLoading || renderPkgTypeList.length > 0"
      class="version-content-main">
      <div
        ref="pkgTabContainerRef"
        v-bk-loading="{ loading: pkgTypeListLoading }"
        class="pkg-tab-main-container">
        <BkTab
          :key="dbTypeActive"
          v-model:active="pkgActive"
          class="pkg-tab-main"
          :class="{ 'pkg-tab-main-scroll': isPkgTabScroll }"
          type="card-tab">
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
            v-for="item of renderPkgTypeList"
            :key="item.value"
            :label="item.name"
            :name="item.value">
            <template #label>
              <div class="tab-label-main">
                <span>{{ item.name }}</span>
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
                          @click="handleEditPkgType(item)">
                          {{ t('编辑包类型') }}
                        </AuthButton>
                      </BkDropdownItem>
                      <BkDropdownItem
                        v-bk-tooltips="{
                          content: t('该包类型存在 n 个版本，请清理后再操作', {
                            n: item.related_versions,
                          }),
                          disabled: item.can_delete,
                          placement: 'right',
                        }">
                        <DbPopconfirm
                          :confirm-handler="() => handleConfirmDeletePkgType(item)"
                          :confirm-text="t('删除')"
                          :content="t('删除操作无法撤回，请谨慎操作！')"
                          :disabled="!item.can_delete"
                          placement="bottom-start"
                          theme="danger"
                          :title="t('确认删除该包类型？')">
                          <AuthButton
                            action-id="package_manage"
                            :disabled="!item.can_delete"
                            :permission="hasPackageManagePermission"
                            :resource="dbTypeActive"
                            text>
                            {{ t('删除包类型') }}
                          </AuthButton>
                        </DbPopconfirm>
                      </BkDropdownItem>
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
          v-if="pkgActive && loadedDbType === dbTypeActive"
          :db-type="dbTypeActive"
          :has-package-manage-permission="hasPackageManagePermission"
          :pkg-label-map="pkgLabelMap"
          :pkg-type="pkgActive"
          :version-num="activePkgType?.version_num || 3"
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
    :data="editPkgTypeData"
    :db-type="dbTypeActive"
    :is-edit="isEditPkgType"
    :total-list="pkgTypeList || []"
    @success="handleGetPkgTypeList" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRoute, useRouter } from 'vue-router';

  import type { FunctionKeys } from '@services/model/function-controller/functionController';
  import { simpleCheckAllowed } from '@services/source/iam';
  import { getPkgTypeList, updatePkgType } from '@services/source/version';

  import { useFunController } from '@stores';

  import { DBTypeInfos, DBTypes } from '@common/const';

  import DbTab from '@components/db-tab/Index.vue';

  import { messageSuccess } from '@utils';

  import EditPkgType from './components/EditPkgType.vue';
  import List from './components/list/Index.vue';

  export type PkgTypeItem = ServiceReturnType<typeof getPkgTypeList>[number];

  const { t } = useI18n();
  const funControllerStore = useFunController();
  const route = useRoute();
  const router = useRouter();

  const excludeDbTypes: DBTypes[] = [DBTypes.TENDBCLUSTER, DBTypes.K8S_SURREALDB, DBTypes.K8S_QRRANT];

  // 包类型自身还受功能开关控制的场景（redis 的集群架构）
  const pkgTypeFunctionKeyMap: Record<string, FunctionKeys> = {
    tendisplus: 'PredixyTendisplusCluster',
    tendisssd: 'TwemproxyTendisSSDInstance',
    twemproxy: 'TwemproxyRedisInstance',
  };

  // 与 DbTab 的判据保持一致：模块开关与该 DB 类型的功能开关都取自同一份扁平数据
  const getFunctionMap = (dbType: DBTypes) => {
    const moduleId = DBTypeInfos[dbType]?.moduleId;
    return moduleId ? funControllerStore.funControllerData.getFlatData(moduleId) : {};
  };

  // 功能开关在路由挂载前已拉取完成，这里可以同步判断 URL 带来的 DB 类型是否可用
  const getInitialDbType = () => {
    const routeDbType = route.query.dbType as DBTypes;
    if (routeDbType && !excludeDbTypes.includes(routeDbType) && getFunctionMap(routeDbType)[routeDbType]) {
      return routeDbType;
    }
    return DBTypes.MYSQL;
  };

  const pkgActive = ref((route.query.pkgType as string) || '');
  const dbTypeActive = ref<DBTypes>(getInitialDbType());
  const isShowPkgTypeManage = ref(false);
  const hasPackageManagePermission = ref(false);
  const isEditPkgType = ref(false);
  const editPkgTypeData = ref<PkgTypeItem>();
  const isPkgTabScroll = ref(false);
  // 包类型列表按 DB 类型请求，切换 DB 类型后到响应回来之前 pkgTypeList 还是上一个类型的，用它标记列表的归属
  const loadedDbType = ref('');
  const pkgTabContainerRef = ref<HTMLElement>();

  const enabledFunctionMap = computed(() => getFunctionMap(dbTypeActive.value));

  const renderPkgTypeList = computed(() => {
    if (!enabledFunctionMap.value[dbTypeActive.value]) {
      return [];
    }
    return (pkgTypeList.value || []).filter((item) => {
      const functionKey = pkgTypeFunctionKeyMap[item.value];
      return !functionKey || Boolean(enabledFunctionMap.value[functionKey]);
    });
  });

  const pkgLabelMap = computed(() =>
    (pkgTypeList.value || []).reduce<Record<string, string>>(
      (dataMap, item) => Object.assign(dataMap, { [item.value]: item.name }),
      {},
    ),
  );

  const activePkgType = computed(() => (pkgTypeList.value || []).find((item) => item.value === pkgActive.value));

  const {
    data: pkgTypeList,
    loading: pkgTypeListLoading,
    run: fetchPkgTypeList,
  } = useRequest(getPkgTypeList, {
    manual: true,
    onSuccess(_data, params) {
      loadedDbType.value = params[0].db_type;
    },
  });

  const { runAsync: runDeletePkgType } = useRequest(updatePkgType, {
    manual: true,
    onSuccess() {
      messageSuccess(t('操作成功'));
      handleGetPkgTypeList();
    },
  });

  // 新建包类型后需要把选中项切到新建的那个上
  let newCreatePkgType: string | undefined = undefined;

  // 返回 Promise 交给 DbPopconfirm，由它接管确认按钮 loading 与请求成功后的关闭
  const handleConfirmDeletePkgType = (data: PkgTypeItem) => {
    if (!pkgTypeList.value?.length) {
      return Promise.resolve();
    }

    return runDeletePkgType({
      db_type: dbTypeActive.value,
      items: pkgTypeList.value.filter((item) => item.value !== data.value),
    });
  };

  const handleEditPkgType = (data: PkgTypeItem) => {
    editPkgTypeData.value = data;
    isEditPkgType.value = true;
    isShowPkgTypeManage.value = true;
  };

  const handleCreatePkgType = () => {
    isEditPkgType.value = false;
    editPkgTypeData.value = undefined;
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
    const dbType = dbTypeActive.value;
    hasPackageManagePermission.value = false;

    const hasPackageViewPermission = await simpleCheckAllowed(
      {
        action_id: 'package_view',
        is_raise_exception: true,
        resource_id: dbType,
      },
      {
        permission: 'page',
      },
    );
    if (!hasPackageViewPermission) {
      return;
    }

    const hasManagePermission = await simpleCheckAllowed({
      action_id: 'package_manage',
      resource_id: dbType,
    });
    // 连续切换 DB 类型时响应可能乱序，只认当前选中类型的结果
    if (dbType === dbTypeActive.value) {
      hasPackageManagePermission.value = hasManagePermission;
    }
  };

  const checkPkgTabScroll = () => {
    const tabListDom = pkgTabContainerRef.value?.querySelector('.tab-header-auto');
    const scrollWidth = tabListDom?.scrollWidth || 0;
    const clientWidth = tabListDom?.clientWidth || 0;
    isPkgTabScroll.value = scrollWidth > clientWidth;
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

  watch(
    renderPkgTypeList,
    () => {
      nextTick(() => {
        checkPkgTabScroll();
      });

      // 列表还没归属当前 DB 类型时不能动选中项，否则会把 URL 上带过来的初始值清掉
      if (loadedDbType.value !== dbTypeActive.value) {
        return;
      }

      const valueList = renderPkgTypeList.value.map((item) => item.value);
      if (valueList.length === 0) {
        pkgActive.value = '';
        return;
      }

      if (newCreatePkgType && valueList.includes(newCreatePkgType)) {
        pkgActive.value = newCreatePkgType;
        newCreatePkgType = undefined;
        return;
      }

      // 选中项在新列表里不存在（切换 DB 类型、包类型被删除、URL 上的值失效）时回落到第一项
      if (!valueList.includes(pkgActive.value)) {
        pkgActive.value = valueList[0];
      }
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

  onMounted(() => {
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

    .version-content-main {
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
