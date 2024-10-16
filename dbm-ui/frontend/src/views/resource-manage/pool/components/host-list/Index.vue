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
  <div class="resource-pool-list-page">
    <div class="action-box mb-16">
      <template v-if="props.type === ResourcePool.public">
        <BkButton
          :disabled="selectionHostIdList.length < 1"
          theme="primary"
          @click="handleShowBatchConvertToBusiness"
          >{{ t('转入业务资源池') }}</BkButton
        >
      </template>
      <template v-else>
        <ImportHostBtn
          class="w-88"
          @export-host="handleImportHost" />
        <BkDropdown trigger="click">
          <BkButton
            class="ml-8"
            :disabled="selectionHostIdList.length < 1">
            {{ t('批量操作') }}
            <DbIcon type="down-big" />
          </BkButton>
          <template #content>
            <BkDropdownMenu>
              <BkDropdownItem @click="handleShowBatchSetting"> {{ t('设置属性') }} </BkDropdownItem>
              <BkDropdownItem @click="handleShowBatchSetting"> {{ t('添加资源归属') }} </BkDropdownItem>
              <BkDropdownItem @click="handleShowBatchCovertToPublic"> {{ t('转为公共资源') }} </BkDropdownItem>
              <BkDropdownItem @click="handleShowBatchMoveToRecyclePool"> {{ t('移入待回收池') }} </BkDropdownItem>
              <BkDropdownItem @click="handleShowBatchMoveToFaultPool"> {{ t('移入故障池') }} </BkDropdownItem>
              <BkDropdownItem @click="handleShowBatchUndoImport"> {{ t('撤销导入') }} </BkDropdownItem>
            </BkDropdownMenu>
          </template>
        </BkDropdown>
      </template>

      <BkDropdown trigger="click">
        <BkButton
          class="ml-8"
          style="width: 80px">
          {{ t('复制') }}
          <DbIcon type="down-big" />
        </BkButton>
        <template #content>
          <BkDropdownMenu>
            <BkDropdownItem @click="handleCopyAllHost">
              {{ t('所有主机') }}
            </BkDropdownItem>
            <BkDropdownItem @click="handleCopySelectHost">
              {{ t('已选主机') }}
            </BkDropdownItem>
            <BkDropdownItem @click="handleCopyAllAbnormalHost">
              {{ t('所有异常主机') }}
            </BkDropdownItem>
          </BkDropdownMenu>
        </template>
      </BkDropdown>
      <BkSearchSelect class="search-selector" />
      <BkSelect
        :filterable="false"
        multiple
        selected-style="checkbox">
        <template #trigger>
          <BkButton class="ml-8">
            <DbIcon
              class="mr-6"
              type="tag-3" />
            {{ t('标签搜索') }}
          </BkButton>
        </template>
        <BkOption
          label="标签1"
          value="tag1" />
      </BkSelect>
      <AuthButton
        action-id="resource_operation_view"
        class="quick-search-btn"
        @click="handleGoOperationRecord">
        <DbIcon type="history-2" />
      </AuthButton>
    </div>
    <RenderTable
      ref="tableRef"
      :columns="tableColumn"
      :data-source="dataSource"
      primary-key="bk_host_id"
      releate-url-query
      row-cls="my-row-cls"
      selectable
      :settings="tableSetting"
      @clear-search="handleClearSearch"
      @selection="handleSelection"
      @setting-change="handleSettingChange" />
    <ImportHost
      v-model:is-show="isShowImportHost"
      @change="handleImportHostChange" />
    <BatchSetting
      v-model:is-show="isShowBatchSetting"
      :data="selectionHostIdList"
      @change="handleBatchSettingChange" />

    <BatchCovertToPublic
      v-model:is-show="isShowBatchCovertToPublic"
      :refresh="fetchData"
      :selected="selectionListWholeDataMemo" />

    <BatchMoveToRecyclePool
      v-model:is-show="isShowBatchMoveToRecyclePool"
      :refresh="fetchData"
      :selected="selectionListWholeDataMemo" />

    <BatchMoveToFaultPool
      v-model:is-show="isShowBatchMoveToFaultPool"
      :refresh="fetchData"
      :selected="selectionListWholeDataMemo" />

    <BatchUndoImport
      v-model:is-show="isShowBatchUndoImport"
      :refresh="fetchData"
      :selected="selectionListWholeDataMemo" />

    <BatchConvertToBusiness
      v-model:is-show="isShowBatchConvertToBusiness"
      :biz-id="(currentBizId as number)"
      :refresh="fetchData"
      :selected="selectionListWholeDataMemo" />
  </div>
</template>
<script setup lang="tsx">
  import { Tag } from 'bkui-vue';
  import BkButton from 'bkui-vue/lib/button';
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import DbResourceModel from '@services/model/db-resource/DbResource';
  import {
    fetchList,
  } from '@services/source/dbresourceResource';

  import DiskPopInfo from '@components/disk-pop-info/DiskPopInfo.vue';
  import HostAgentStatus from '@components/host-agent-status/Index.vue';

  import BatchConvertToBusiness from '@views/resource-manage/pool/components/host-list/components/batch-convert-to-business/Index.vue';
  import BatchCovertToPublic from '@views/resource-manage/pool/components/host-list/components/batch-covert-to-public/Index.vue';
  import BatchMoveToFaultPool from '@views/resource-manage/pool/components/host-list/components/batch-move-to-fault-pool/Index.vue';
  import BatchMoveToRecyclePool from '@views/resource-manage/pool/components/host-list/components/batch-move-to-recycle-pool/Index.vue';
  import BatchUndoImport from '@views/resource-manage/pool/components/host-list/components/batch-undo-import/Index.vue';
  import HostOperationBtn from '@views/resource-manage/pool/components/host-list/components/HostOperationBtn.vue';

  import {
    execCopy,
  } from '@utils';

  import { ResourcePool } from '../../type';

  import BatchSetting from './components/batch-setting/Index.vue';
  import ImportHost from './components/import-host/Index.vue';
  import ImportHostBtn from './components/ImportHostBtn.vue';
  import RenderTable from './components/RenderTable.vue';
  import useTableSetting from './hooks/useTableSetting';

  import DbIcon from '@/components/db-icon';
  import { useGlobalBizs } from '@/stores';

  interface Props {
    type: ResourcePool;
  }

  const props = withDefaults(defineProps<Props>(), {
    type: ResourcePool.global,
  });

  const { t } = useI18n();
  const router = useRouter();
  const { currentBizId } = useGlobalBizs();

  const {
    setting: tableSetting,
    handleChange: handleSettingChange,
  } = useTableSetting();

  const searchBoxRef = ref();
  const tableRef = ref();
  const selectionHostIdList = ref<number[]>([]);
  const isShowBatchSetting = ref(false);
  const isShowImportHost = ref(false);
  const isShowBatchCovertToPublic = ref(false);
  const isShowBatchMoveToRecyclePool = ref(false);
  const isShowBatchMoveToFaultPool = ref(false);
  const isShowBatchUndoImport = ref(false);
  const isShowBatchConvertToBusiness = ref(false);

  const curBizId = computed(() => {
    let bizId = undefined;
    switch (props.type) {
      case ResourcePool.business:
        bizId = currentBizId;
        break;
      case ResourcePool.public:
        bizId = 0;
        break;
    }
    return bizId;
  });

  const searchParams = {};
  let selectionListWholeDataMemo: DbResourceModel[] = [];
  const tableColumn = [
    {
      label: 'IP',
      field: 'ip',
      fixed: 'left',
      width: 150,
    },
    {
      label: t('管控区域'),
      field: 'bk_cloud_name',
      width: 120,
    },
    {
      label: t('Agent 状态'),
      field: 'agent_status',
      width: 100,
      render: ({ data }: { data: DbResourceModel }) => <HostAgentStatus data={data.agent_status} />,
    },
    {
      label: t('资源归属'),
      field: 'resourceOwner',
      width: 320,
      render: ({ data }: { data: DbResourceModel }) => (
        <div class={'resource-owner'}>
          <Tag theme={[t('公共资源池')].includes(data.forBizDisplay) ? 'success' : undefined}>{t('所属业务')} : {data.forBizDisplay}</Tag>
          <Tag theme={[t('通用')].includes(data.resourceTypeDisplay) ? 'success' : undefined}>{t('所属DB')} : {data.resourceTypeDisplay}</Tag>
          {/* <Tag>{data.tag}</Tag> */}
          <DbIcon type="edit" class='operation-icon' />
        </div>
      ),
    },
    {
      label: t('机架'),
      field: 'rack_id',
      render: ({ data }: { data: DbResourceModel }) => data.rack_id || '--',
    },
    {
      label: t('机型'),
      field: 'device_class',
      render: ({ data }: { data: DbResourceModel }) => data.device_class || '--',
    },
    {
      label: t('操作系统类型'),
      width: 120,
      field: 'os_type',
      render: ({ data }: { data: DbResourceModel }) => data.os_type || '--',
    },
    {
      label: t('地域'),
      field: 'city',
      render: ({ data }: { data: DbResourceModel }) => data.city || '--',
    },
    {
      label: t('园区'),
      field: 'sub_zone',
      render: ({ data }: { data: DbResourceModel }) => data.sub_zone || '--',
    },
    {
      label: t('CPU(核)'),
      field: 'bk_cpu',
    },
    {
      label: t('内存'),
      field: 'bkMemText',
      render: ({ data }: { data: DbResourceModel }) => data.bkMemText || '0 M',
    },
    {
      label: t('磁盘容量(G)'),
      field: 'bk_disk',
      minWidth: 120,
      render: ({ data }: { data: DbResourceModel }) => (
        <DiskPopInfo data={data.storage_device}>
          <span style="line-height: 40px; color: #3a84ff;">
            {data.bk_disk}
          </span>
        </DiskPopInfo>
      ),
    },
    {
      label: t('操作'),
      field: 'id',
      width: 300,
      render: ({ data }: { data: DbResourceModel }) => (
        props.type === ResourcePool.public ? (
          <HostOperationBtn
            data={data}
            buttonText={t('转入业务资源池')}
            type="public"
            onRefresh={fetchData}
            tip='213'
            title='213123'
          />
        ) : (
          <>
            <HostOperationBtn
              data={data}
              title={t('确认转入待回收池？')}
              tip={t('确认后，主机将标记为待回收，等待处理')}
              buttonText={t('移入待回收池')}
              type='to_recycle'
              refresh={fetchData} />
            <HostOperationBtn
              data={data}
              btnCls='ml-16'
              title={t('确认转入待故障池？')}
              tip={t('确认后，主机将标记为故障，等待处理')}
              buttonText={t('移入故障池')}
              type='to_fault'
              refresh={fetchData} />
            <HostOperationBtn
              data={data}
              btnCls='ml-16'
              title={t('确认撤销导入？')}
              tip={t('确认后，主机将从资源池移回原有模块')}
              buttonText={t('撤销导入')}
              type='undo_import'
              refresh={fetchData} />
          </>
        )

      ),
    },
  ];

  watch(
    () => props.type,
    () => {
      fetchData();
    }
  );

  const fetchData = () => {
    tableRef.value.fetchData(searchParams);
  };

  // 导入主机
  const handleImportHost = () => {
    isShowImportHost.value = true;
  };

  // 导入主机成功需要刷新列表
  const handleImportHostChange = () => {
    fetchData();
  };

  // 批量设置
  const handleShowBatchSetting = () => {
    isShowBatchSetting.value = true;
  };

  // 复制所有主机
  const handleCopyAllHost = () => {
    fetchList({
      offset: 0,
      limit: -1,
    }).then((data) => {
      const ipList = data.results.map(item => item.ip);
      execCopy(ipList.join('\n'), `${t('复制成功n个IP', { n: ipList.length })}\n`);
    });
  };

  // 复制已选主机
  const handleCopySelectHost = () => {
    const ipList = selectionListWholeDataMemo.map(item => item.ip);
    execCopy(ipList.join('\n'), `${t('复制成功n个IP', { n: ipList.length })}\n`);
  };

  // 复制所有异常主机
  const handleCopyAllAbnormalHost = () => {
    fetchList({
      offset: 0,
      limit: -1,
    }).then((data) => {
      const ipList = data.results.reduce((result, item) => {
        if (!item.agent_status) {
          result.push(item.ip);
        }
        return result;
      }, [] as string[]);
      execCopy(ipList.join('\n'), `${t('复制成功n个IP', { n: ipList.length })}\n`);
    });
  };

  // 批量编辑后刷新列表
  const handleBatchSettingChange = () => {
    fetchData();
    Object.values(selectionHostIdList.value).forEach((hostId) => {
      tableRef.value.removeSelectByKey(hostId);
    });
    selectionHostIdList.value = [];
  };

  // 跳转操作记录
  const handleGoOperationRecord = () => {
    router.push({
      name: 'resourcePoolOperationRecord',
    });
  };

  const handleSelection = (list: number[], selectionListWholeData: DbResourceModel[]) => {
    selectionHostIdList.value = list;
    selectionListWholeDataMemo = selectionListWholeData;
  };

  const handleClearSearch = () => {
    searchBoxRef.value.clearValue();
  };

  const handleShowBatchCovertToPublic = () => {
    isShowBatchCovertToPublic.value = true;
  }

  const handleShowBatchMoveToRecyclePool = () => {
    isShowBatchMoveToRecyclePool.value = true;
  };

  const handleShowBatchMoveToFaultPool = () => {
    isShowBatchMoveToFaultPool.value = true;
  }

  const handleShowBatchUndoImport = () => {
    isShowBatchUndoImport.value = true;
  };

  const handleShowBatchConvertToBusiness = () => {
    isShowBatchConvertToBusiness.value = true;
  }

  const dataSource = async (params: ServiceParameters<typeof fetchList>) => {
    console.log('params', params);
    return await fetchList({
      ...params,
      for_biz: curBizId.value,
    });
  }

  onMounted(() => {
    fetchData();
  });
</script>
<style lang="less">
  .resource-pool-list-page {
    .action-box {
      display: flex;
      align-items: center;

      .quick-search-btn {
        width: 32px;
        margin-left: 8px;
      }

      .search-selector {
        margin-left: auto;
        width: 560px;
        height: 32px;
      }
    }

    .my-row-cls {
      background-color: #3a84ff;

      .resource-owner {
        display: flex;
        align-items: center;

        .operation-icon {
          color: #3a84ff;
          cursor: pointer;
          margin-left: 7.5px;
          font-size: 12px;
          visibility: hidden;
        }
      }

      &:hover {
        .operation-icon {
          visibility: visible;
          display: block;
        }
      }
    }
  }
</style>
