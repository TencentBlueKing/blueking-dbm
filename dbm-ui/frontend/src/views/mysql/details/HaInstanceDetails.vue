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
  <BkResizeLayout
    :border="false"
    class="instance-details"
    collapsible
    initial-divide="280px"
    :max="380"
    :min="280">
    <template #aside>
      <AsideList
        ref="asideListRef"
        :active-item="detailState.details"
        :data="state.data"
        :limit="state.pagination.limit"
        :loading="state.loading"
        :placeholder="$t('实例')"
        show-key="instance_address"
        :total="state.pagination.count"
        @change-page="handleChangePage"
        @item-selected="handleClickItem"
        @return-page="handleChangePage"
        @search-clear="handleSearchChange"
        @search-enter="handleSearchChange" />
    </template>
    <template #main>
      <div class="instance-details__main db-scroll-y">
        <BkLoading
          :loading="detailState.loading"
          :z-index="10">
          <DbCard
            class="instance-details__base"
            mode="collapse"
            :title="$t('基本信息')">
            <EditInfo
              :columns="columns"
              :data="detailState.details" />
          </DbCard>
          <DbCard
            mode="collapse"
            style="box-shadow: none;"
            :title="$t('参数配置')">
            <BkLoading :loading="configState.loading">
              <DbOriginalTable
                :columns="configState.columns"
                :data="configState.data.conf_items"
                :min-height="0"
                :show-overflow-tooltip="false" />
            </BkLoading>
          </DbCard>
        </BkLoading>
      </div>
    </template>
  </BkResizeLayout>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import { getResourceInstanceDetails } from '@services/clusters';
  import { getLevelConfig } from '@services/configs';
  import type { InstanceDetails, ResourceInstance } from '@services/types/clusters';
  import type { ConfigBaseDetails } from '@services/types/configs';

  import {
    useGlobalBizs,
    useMainViewStore,
  } from '@stores';

  import {
    type ClusterInstStatus,
    clusterInstStatus,
    DBTypes,
  } from '@common/const';

  import AsideList from '@components/cluster-details/AsideList.vue';
  import DbStatus from '@components/db-status/index.vue';
  import EditInfo, {
    type InfoColumn,
  } from '@components/editable-info/index.vue';

  import { useInstanceData } from './hooks/useInstancesData';

  import type { TableColumnRender } from '@/types/bkui-vue';

  const props = defineProps({
    clusterType: {
      type: String,
      required: true,
    },
  });

  // 设置主视图padding
  const mainViewStore = useMainViewStore();
  mainViewStore.hasPadding = false;

  const { t } = useI18n();
  const router = useRouter();
  const route = useRoute();
  const globalBizsStore = useGlobalBizs();
  const {
    state,
    fetchResourceInstances,
  } = useInstanceData(props);

  const detailState = reactive({
    details: {} as InstanceDetails,
    search: '',
    loading: false,
  });
  const asideListRef = ref<InstanceType<typeof AsideList> | null>(null);
  const activeInst = computed(() => route.params.address as string);

  onMounted(async () => {
    state.pagination.limit = 50;

    const params = {
      instance_address: route.params.address as string,
      cluster_id: Number(route.params.clusterId),
    };
    try {
      const results = await Promise.allSettled([fetchResourceInstances(), fetchInstDetails(params)]);
      const detailsResult = results[1];
      if (detailsResult.status !== 'rejected') {
        const target = state.data.find(item => item.instance_address === activeInst.value);
        // 记录当前选中项在第几页
        asideListRef.value?.setActiveLocationPage(1);
        if (target === undefined) {
          // 确保 details 赋值成功后再添加
          setTimeout(() => {
            state.data.unshift(detailsTransformItem());
          });
        }
      }
    } catch (e) {
      console.error(e);
    }
  });

  /**
   * 将详情值构造成列表值
   */
  function detailsTransformItem() {
    return {
      cluster: detailState.details.cluster_id,
      create_at: detailState.details.create_at,
      instance_address: detailState.details.instance_address,
      master_domain: detailState.details.master_domain,
      role: detailState.details.role,
      slave_domain: detailState.details.slave_domain,
      status: detailState.details.status,
      bk_cloud_id: detailState.details.bk_cloud_id,
      bk_host_id: detailState.details.bk_host_id,
      cluster_id: detailState.details.cluster_id,
      cluster_type: detailState.details.cluster_type,
    };
  }

  /**
   * 获取实例详情
   */
  function fetchInstDetails(data: ResourceInstance) {
    const params = {
      bk_biz_id: globalBizsStore.currentBizId,
      type: props.clusterType,
      instance_address: data.instance_address,
      cluster_id: data.cluster_id,
    };
    detailState.loading = true;
    getResourceInstanceDetails(params, DBTypes.MYSQL)
      .then((res) => {
        detailState.details = res;
        mainViewStore.$patch({
          breadCrumbsTitle: t('MySQL高可用实例详情【name】', { name: detailState.details.instance_address }),
        });
        // 获取参数配置
        fetchClusterConfig();
      })
      .finally(() => {
        detailState.loading = false;
      });
  }

  /**
   * 翻页
   */
  function handleChangePage(page: number) {
    state.pagination.current = page;
    fetchResourceInstances(detailState.search)
      .then(() => {
        if (!detailState.search) {
          // 非搜索状态的时候，记录选中项在第几页
          const target = state.data.find(item => item.instance_address === activeInst.value);
          if (target) {
            asideListRef.value?.setActiveLocationPage(page);
          }

          // 记录选中项在第一页 & 处于第一页 & 没有找到选中内容，将选中项置顶到第一页
          if (asideListRef.value?.isInsertToPage() && target === undefined) {
            state.data.unshift(detailsTransformItem());
          }
        }
      });
  }

  /**
   * 侧栏搜索
   */
  function handleSearchChange(value: string) {
    detailState.search = value;
    handleChangePage(1);
  }

  /**
   * 选中实例
   */
  function handleClickItem(data: ResourceInstance) {
    router.replace({ params: {
      address: data.instance_address,
      clusterId: data.cluster_id,
    } });
    // 清空数据
    configState.data.conf_items = [];
    fetchInstDetails(data);
  }

  /**
   * 设置基础信息
   */
  const columns: InfoColumn[][] = [
    [{
      label: t('实例'),
      key: 'instance_address',
    }, {
      label: t('主机IP'),
      key: 'bk_host_innerip',
    }, {
      label: t('状态'),
      key: 'status',
      render: () => {
        const status = detailState.details.status as ClusterInstStatus;
        if (!status) return '--';

        const info = clusterInstStatus[status] || clusterInstStatus.unavailable;
        return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
      },
    }, {
      label: t('主域名'),
      key: 'master_domain',
      render: () => {
        const domain = detailState.details.master_domain;
        if (!domain) return '--';

        return (
          <div class="inline-item">
            <div class="text-overflow" v-overflow-tips>
              <a href="javascript:" onClick={handleToClusterDetails}>{domain}</a>
            </div>
            <i class="db-icon-link ml-4" />
          </div>
        );
      },
    }, {
      label: t('从域名'),
      key: 'slave_domain',
    }],
    [{
      label: t('部署架构'),
      key: 'cluster_type_display',
    }, {
      label: t('部署角色'),
      key: 'role',
    }, {
      label: t('云区域'),
      key: 'bk_cloud_name',
    }, {
      label: t('所在城市'),
      key: 'idc_city_name',
    }, {
      label: t('所在机房'),
      key: 'bk_idc_name',
    }],
    [{
      label: 'CPU',
      key: 'bk_cpu',
      render: () => {
        if (!Number.isFinite(detailState.details.bk_cpu)) {
          return '--';
        }
        return `${detailState.details.bk_cpu}${t('核')}`;
      },
    }, {
      label: t('内存'),
      key: 'bk_mem',
      render: () => {
        if (!Number.isFinite(detailState.details.bk_mem)) {
          return '--';
        }
        return `${detailState.details.bk_mem}MB`;
      },
    }, {
      label: t('磁盘'),
      key: 'bk_disk',
      render: () => {
        if (!Number.isFinite(detailState.details.bk_disk)) {
          return '--';
        }
        return `${detailState.details.bk_disk}GB`;
      },
    }, {
      label: t('部署时间'),
      key: 'create_at',
    }],
  ];

  /**
   * 查看集群详情
   */
  function handleToClusterDetails() {
    router.push({
      name: 'DatabaseTendbhaDetails',
      params: {
        id: detailState.details.cluster_id,
      },
    });
  }

  const configState = reactive({
    loading: false,
    data: {
      name: '',
      version: '',
      description: '',
      conf_items: [],
    } as ConfigBaseDetails,
    columns: [{
      label: t('参数项'),
      field: 'conf_name',
      render: ({ cell }: TableColumnRender) => <div class="text-overflow" v-overflow-tips>{cell}</div>,
    }, {
      label: t('参数值'),
      field: 'conf_value',
      render: ({ cell }: TableColumnRender) => <div class="text-overflow" v-overflow-tips>{cell}</div>,
    }, {
      label: t('描述'),
      field: 'description',
      render: ({ cell }: TableColumnRender) => <div class="text-overflow" v-overflow-tips>{cell || '--'}</div>,
    }, {
      label: t('重启实例生效'),
      field: 'need_restart',
      width: 200,
      render: ({ cell }: {cell: number}) => (cell === 1 ? t('是') : t('否')),
    }],
  });

  /**
   * 获取集群配置
   */
  function fetchClusterConfig() {
    configState.loading = true;
    getLevelConfig({
      bk_biz_id: globalBizsStore.currentBizId,
      level_value: detailState.details.cluster_id,
      meta_cluster_type: props.clusterType,
      level_name: 'cluster',
      conf_type: 'dbconf',
      version: detailState.details.db_version,
      level_info: {
        module: String(detailState.details.db_module_id),
      },
    })
      .then((res) => {
        configState.data = res;
      })
      .finally(() => {
        configState.loading = false;
      });
  }
</script>

<style lang="less" scoped>
  @import "@styles/mixins.less";

  .instance-details {
    height: 100%;
    background-color: #fff;

    &__main {
      height: 100%;
    }
  }

  :deep(.bk-table) {
    .sticky-table();
  }

  :deep(.inline-item) {
    color: @primary-color;
    cursor: pointer;
    .flex-center();
  }
</style>
