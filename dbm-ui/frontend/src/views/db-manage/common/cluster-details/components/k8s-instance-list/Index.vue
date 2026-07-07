<template>
  <div class="k8s-cluster-detail-instance-list-box">
    <div class="action-box mb-16">
      <div
        v-if="slots.role"
        class="role-slot">
        <slot name="role" />
        <div class="slot-divider ml-12 mr-12"></div>
      </div>
      <InstanceBatchCopy
        field="podName"
        :get-table-data="getBatchCopyData"
        :selected="selectedList" />
      <InstanceBatchCopy
        class="ml-8"
        field="node"
        :get-table-data="getBatchCopyData"
        :selected="selectedList" />
      <AuthButton
        :action-id="`${dbType}_manage`"
        class="ml-8"
        :disabled="originalData.length === 0"
        :permission="clusterData.permission[`${dbType}_manage` as keyof typeof clusterData.permission]"
        :resource="clusterData.id"
        style="width: 105px"
        @click="handlePatchComponentConfigShow">
        {{ t('配置变更') }}
      </AuthButton>
      <AuthButton
        :action-id="`${dbType}_manage`"
        class="ml-8"
        :disabled="originalData.length === 0"
        :permission="clusterData.permission[`${dbType}_manage` as keyof typeof clusterData.permission]"
        :resource="clusterData.id"
        style="width: 105px"
        @click="handleBatchRestart">
        {{ t('重启') }}
      </AuthButton>
      <BkDropdown
        class="instance-batch-copy"
        :popover-options="{
          clickContentAutoHide: true,
        }"
        trigger="click">
        <template #default="{ popoverShow }">
          <BkButton
            class="ml-8"
            :disabled="originalData.length === 0"
            style="width: 105px">
            {{ t('更多配置') }}
            <DbIcon
              class="ml-4"
              :class="{ 'is-show': popoverShow }"
              type="up-big" />
          </BkButton>
        </template>
        <template #content>
          <BkDropdownMenu class="dropdown-menu-with-button">
            <AuthTemplate
              :action-id="`${dbType}_manage`"
              :permission="clusterData.permission[`${dbType}_manage` as keyof typeof clusterData.permission]"
              :resource="clusterData.id">
              <BkDropdownItem>
                <BkButton
                  style="width: 105px"
                  text
                  @click="handleVscalingComponentShow">
                  {{ t('升降配置') }}
                </BkButton>
              </BkDropdownItem>
              <BkDropdownItem v-if="!(clusterType === ClusterTypes.K8S_SURREALDB_HA && role === 'surreal')">
                <BkButton
                  style="width: 105px"
                  text
                  @click="handleVexpansionComponentShow">
                  {{ t('磁盘扩容') }}
                </BkButton>
              </BkDropdownItem>
              <BkDropdownItem v-if="[ClusterTypes.K8S_SURREALDB_HA, ClusterTypes.K8S_QDRANT_HA].includes(clusterType)">
                <BkButton
                  style="width: 105px"
                  text
                  @click="handleHscalingComponentShow">
                  {{ t('水平扩容') }}
                </BkButton>
              </BkDropdownItem>
            </AuthTemplate>
          </BkDropdownMenu>
        </template>
      </BkDropdown>
      <DbQuickSearch
        v-model="searchValue"
        :data="quickSearchData"
        :placeholder="t('请输入或选择条件搜索')"
        style="width: 500px; margin-left: auto"
        @change="handleQuickSearchChange" />
    </div>
    <div ref="rootRef">
      <BkLoading :loading="isLoading">
        <PrimaryTable
          ref="instanceTable"
          :data="tableFilterData"
          :max-height="tableMaxHeight"
          row-key="podName"
          :selected-row-keys="selectedRowKeys"
          @select-change="handleSelectChange">
          <TableColumn
            col-key="row-select"
            fixed="left"
            type="multiple"
            :width="40" />
          <InstanceAddressColumn
            :cluster-data="clusterData"
            :cluster-type="clusterType"
            :role="role" />
          <TableColumn
            col-key="status"
            :min-width="80"
            :title="t('状态')">
            <template #default="{ row }: { row: IColumnData }">
              <ClusterK8sInstanceStatus :data="row.status" />
            </template>
          </TableColumn>
          <TableColumn
            col-key="resourceQuota"
            :min-width="150"
            :title="t('资源配置')">
            <template #default="{ row }: { row: IColumnData }">
              {{ row.resourceQuotaDisplay }}
            </template>
          </TableColumn>
          <TableColumn
            col-key="cpuPercent"
            :min-width="240"
            :title="t('CPU 使用率')">
            <template #default="{ row }: { row: IColumnData }">
              <UsageRate :data="row.resourceUsage.cpuPercent" />
            </template>
          </TableColumn>
          <TableColumn
            col-key="memoryPercent"
            :min-width="240"
            :title="t('内存使用率')">
            <template #default="{ row }: { row: IColumnData }">
              <UsageRate :data="row.resourceUsage.memoryPercent" />
            </template>
          </TableColumn>
          <TableColumn
            col-key="storagePercent"
            :min-width="240"
            :title="t('存储使用率')">
            <template #default="{ row }: { row: IColumnData }">
              <UsageRate :data="row.resourceUsage.storagePercent" />
            </template>
          </TableColumn>
          <TableColumn
            col-key="createdTimeDisplay"
            :title="t('部署时间')"
            :width="180" />
          <TableColumn
            col-key="action"
            fixed="right"
            :title="t('操作')"
            :width="60">
            <template #default="{ row }: { row: IColumnData }">
              <AuthButton
                :action-id="`${dbType}_manage`"
                :permission="clusterData.permission[`${dbType}_manage` as keyof typeof clusterData.permission]"
                :resource="clusterData.id"
                text
                theme="primary"
                @click="
                  handleDeleteInstance(
                    {
                      bk_username: userProfile.username,
                      clusterName: clusterData.cluster_name,
                      k8sClusterName: clusterData.k8s_cluster_name,
                      namespace: clusterData.namespace,
                      podName: row.podName,
                    },
                    row.node,
                  )
                ">
                {{ t('删除') }}
              </AuthButton>
            </template>
          </TableColumn>
        </PrimaryTable>
      </BkLoading>
    </div>
    <PatchComponentConfig
      v-if="isPatchComponentConfigShow"
      v-model="isPatchComponentConfigShow"
      :cluster-data="clusterData"
      :role="role"
      @success="handleOperateSuccess" />
    <VscalingComponent
      v-model="isVscalingComponentShow"
      :cluster-data="clusterData"
      :data="originalData"
      :role="role"
      @success="handleOperateSuccess" />
    <VexpansionComponent
      v-model="isVexpansionComponentShow"
      :cluster-data="clusterData"
      :data="originalData"
      :role="role"
      @success="handleOperateSuccess" />
    <HscalingComponent
      v-model="isHscalingComponentShow"
      :cluster-data="clusterData"
      :count="originalData.length"
      :role="role"
      @success="handleOperateSuccess" />
  </div>
</template>
<script lang="tsx">
  import _ from 'lodash';
  import type { VNode } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRoute, useRouter } from 'vue-router';

  import QdrantHaDetailModel from '@services/model/qdrant/qdrant-ha-detail';
  import SurrealdbHaDetailModel from '@services/model/surrealdb/surrealdb-ha-detail';
  import SurrealdbSingleDetailModel from '@services/model/surrealdb/surrealdb-single-detail';

  // import { restartComponent } from '@services/source/kubernetesToolbox.ts';
  import { useUrlSearch } from '@hooks';

  import { useUserProfile } from '@stores';

  import { clusterTypeInfos, ClusterTypes } from '@common/const';

  import ClusterK8sInstanceStatus from '@components/cluster-k8s-instance-status/Index.vue';

  import { useK8sInstanceOperations } from '@views/db-manage/common/hooks';
  import InstanceBatchCopy from '@views/db-manage/common/instance-batch-copy/Index.vue';
  import useClusterInstanceList from '@views/db-manage/hooks/useClusterInstaceList';

  import { getOffset, messageSuccess } from '@utils';

  import { URL_INSTANCE_MEMO_KEY } from '../../constants';

  import HscalingComponent from './components/batch-operation/HscalingComponent.vue';
  import PatchComponentConfig from './components/batch-operation/PatchComponentConfig.vue';
  import VexpansionComponent from './components/batch-operation/VexpansionComponent.vue';
  import VscalingComponent from './components/batch-operation/VscalingComponent.vue';
  import InstanceAddressColumn from './components/instance-address-column/Index.vue';
  import UsageRate from './components/UsageRate.vue';
  import { useQuickSearch } from './useQuickSerach';

  interface ClusterTypeRelateClusterModel {
    [ClusterTypes.K8S_QDRANT_HA]: QdrantHaDetailModel;
    [ClusterTypes.K8S_SURREALDB_HA]: SurrealdbHaDetailModel;
    [ClusterTypes.K8S_SURREALDB_SINGLE]: SurrealdbSingleDetailModel;
  }

  type IColumnData = ServiceReturnType<
    ReturnType<typeof useClusterInstanceList<keyof ClusterTypeRelateClusterModel>>
  >['results'][number];
</script>
<script setup lang="tsx" generic="T extends keyof ClusterTypeRelateClusterModel">
  export interface Props<T extends keyof ClusterTypeRelateClusterModel> {
    clusterData: ClusterTypeRelateClusterModel[T];
    clusterType: T;
    role: string;
  }

  export interface Emits {
    (e: 'refresh'): void;
    (e: 'request-success', list: IColumnData[]): void;
  }

  export interface Slots {
    role: () => VNode;
  }

  const props = defineProps<Props<T>>();
  const emits = defineEmits<Emits>();
  const slots = defineSlots<Slots>();

  const { t } = useI18n();
  const userProfile = useUserProfile();
  const route = useRoute();
  const router = useRouter();
  const { getSearchParams, replaceSearchParams } = useUrlSearch();
  const { handleFilterList, handleMergeSearchParams, quickSearchData, searchValue } = useQuickSearch();
  const requestHandler = useClusterInstanceList(props.clusterType);
  const { handleDeleteInstance, handleRestartInstance } = useK8sInstanceOperations({
    onSuccess: () => handleOperateSuccess(),
  });

  const dbType = clusterTypeInfos[props.clusterType].dbType;

  const rootRef = useTemplateRef('rootRef');

  const isLoading = ref(false);
  const tableMaxHeight = ref<number | 'auto'>('auto');
  const tableFilterData = ref<IColumnData[]>([]);
  const isPatchComponentConfigShow = ref(false);
  const isVscalingComponentShow = ref(false);
  const isVexpansionComponentShow = ref(false);
  const isHscalingComponentShow = ref(false);

  const selectedRowKeys = ref<number[]>([]);
  const selectedList = shallowRef<IColumnData[]>([]);

  const originalData = computed(() => {
    const currentComponentName = props.role;
    return (instanceData.value?.results || []).filter(
      (item) => item.componentName === currentComponentName,
    ) as IColumnData[];
  });

  const { data: instanceData, run } = useRequest(requestHandler, {
    manual: true,
    onAfter() {
      isLoading.value = false;
    },
    onSuccess(result) {
      emits('request-success', result.results);
      // handleQuickSearchChange();
    },
    pollingInterval: 10 * 1000,
  });

  watch(originalData, () => {
    handleQuickSearchChange();
  });

  // watch(
  //   () => props.role,
  //   () => {
  //     fetchData();
  //   },
  // );

  const getBatchCopyData = () => {
    return Promise.resolve(originalData.value);
  };

  const fetchData = () => {
    isLoading.value = true;
    run({
      cluster_name: props.clusterData.cluster_name,
      k8s_cluster_name: props.clusterData.k8s_cluster_name,
      namespace: props.clusterData.namespace,
      // role: props.role,
    });
  };

  const handleQuickSearchChange = _.debounce(() => {
    const filterList = handleFilterList(originalData.value);

    router.replace({
      query: {
        ...replaceSearchParams(handleMergeSearchParams(getSearchParams()), false),
        [URL_INSTANCE_MEMO_KEY]: encodeURIComponent(JSON.stringify(searchValue.value)),
      },
    });
    tableFilterData.value = filterList;
  }, 100);

  const handleSelectChange = (value: (string | number)[], { selectedRowData }: { selectedRowData: unknown[] }) => {
    selectedRowKeys.value = value as number[];
    selectedList.value = selectedRowData as IColumnData[];
  };

  const handleOperateSuccess = () => {
    messageSuccess(t('操作成功'));
    selectedRowKeys.value = [];
    selectedList.value = [];
    fetchData();
    emits('refresh');
  };

  const handleBatchRestart = () => {
    handleRestartInstance(
      {
        bk_username: userProfile.username,
        clusterName: props.clusterData.cluster_name,
        k8sClusterName: props.clusterData.k8s_cluster_name,
        namespace: props.clusterData.namespace,
        restart: [
          {
            componentName: props.role,
          },
        ],
      },
      props.role,
      originalData.value.length,
    );
  };

  const handlePatchComponentConfigShow = () => {
    isPatchComponentConfigShow.value = true;
  };

  // const handlePatchComponentConfigSuccess = () => {
  //   restartComponent({
  //     bk_username: userProfile.username,
  //     clusterName: props.clusterData.cluster_name,
  //     k8sClusterName: props.clusterData.k8s_cluster_name,
  //     namespace: props.clusterData.namespace,
  //     restart: [
  //       {
  //         componentName: props.role,
  //       },
  //     ],
  //   }).then(() => {
  //     handleOperateSuccess();
  //   });
  // };

  const handleVscalingComponentShow = () => {
    isVscalingComponentShow.value = true;
  };

  const handleVexpansionComponentShow = () => {
    isVexpansionComponentShow.value = true;
  };

  const handleHscalingComponentShow = () => {
    isHscalingComponentShow.value = true;
  };

  onMounted(() => {
    searchValue.value = JSON.parse(decodeURIComponent(String(route.query[URL_INSTANCE_MEMO_KEY] || '{}')));
    fetchData();

    setTimeout(() => {
      tableMaxHeight.value = window.innerHeight - getOffset(rootRef.value as HTMLElement).top - 60 - 20 - 20;
    });
  });
</script>
<style lang="less">
  .k8s-cluster-detail-instance-list-box {
    padding: 18px 0;

    .action-box {
      display: flex;

      .role-slot {
        display: flex;
        align-items: center;

        .slot-divider {
          width: 1px;
          height: 15px;
          background: #dcdee5;
        }
      }
    }
  }

  .k8s-cluster-detail-instance-replace-model {
    .bk-modal-content div {
      font-size: 14px;
    }

    .tips-item {
      padding: 2px 0;
    }
  }
</style>
