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
    <SearchBox
      ref="searchBoxRef"
      class="mb-25"
      @change="handleSearch" />
    <div class="action-box mt-24 mb-16">
      <ImportHostBtn
        class="w-88"
        @export-host="handleImportHost" />
      <BkButton
        class="ml-8"
        :disabled="selectionHostIdList.length < 1"
        @click="handleShowBatchSetting">
        {{ t('批量设置') }}
      </BkButton>
      <DbPopconfirm
        :confirm-handler="handleBatchRemove"
        :content="t('主机将被落到空闲机，如需要可再次导入')"
        :title="t('确认移除选中的主机')">
        <BkButton
          class="ml-8"
          :disabled="selectionHostIdList.length < 1">
          {{ t('批量移除') }}
        </BkButton>
      </DbPopconfirm>
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
      <BkButton
        class="quick-search-btn"
        @click="handleGoOperationRecord">
        <DbIcon type="history-2" />
      </BkButton>
    </div>
    <RenderTable
      ref="tableRef"
      :columns="tableColumn"
      :data-source="dataSource"
      primary-key="bk_host_id"
      releate-url-query
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
  </div>
</template>
<script setup lang="tsx">
  import BkButton from 'bkui-vue/lib/button';
  import { ref  } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import DbResourceModel from '@services/model/db-resource/DbResource';
  import {
    fetchList,
    removeResource,
  } from '@services/source/dbresourceResource';

  import HostAgentStatus from '@components/cluster-common/HostAgentStatus.vue';

  import {
    execCopy,
    messageSuccess,
  } from '@utils';

  import BatchSetting from './components/batch-setting/Index.vue';
  import DiskPopInfo from './components/DiskPopInfo.vue';
  import ImportHost from './components/import-host/Index.vue';
  import ImportHostBtn from './components/ImportHostBtn.vue';
  import RenderTable from './components/RenderTable.vue';
  import SearchBox from './components/search-box/Index.vue';
  import useTableSetting from './hooks/useTableSetting';

  const { t } = useI18n();
  const router = useRouter();

  const {
    setting: tableSetting,
    handleChange: handleSettingChange,
  } = useTableSetting();

  const dataSource = fetchList;

  const searchBoxRef = ref();
  const tableRef = ref();
  const isShowBatchSetting = ref(false);
  const selectionHostIdList = ref<number[]>([]);
  let selectionListWholeDataMemo: DbResourceModel[] = [];

  const tableColumn = [
    {
      label: 'IP',
      field: 'ip',
      fixed: 'left',
      with: 120,
    },
    {
      label: t('管控区域'),
      field: 'bk_cloud_name',
      with: 120,
    },
    {
      label: t('Agent 状态'),
      field: 'agent_status',
      with: 100,
      render: ({ data }: {data: DbResourceModel}) => <HostAgentStatus data={data.agent_status} />,
    },
    {
      label: t('专用业务'),
      field: 'for_bizs',
      width: 170,
      render: ({ data }: {data: DbResourceModel}) => {
        if (data.for_bizs.length < 1) {
          return t('无限制');
        }
        return data.for_bizs.map(item => item.bk_biz_name).join(',');
      },
    },
    {
      label: t('专用 DB'),
      field: 'resource_types',
      width: 150,
      render: ({ data }: {data: DbResourceModel}) => {
        if (data.resource_types.length < 1) {
          return t('无限制');
        }
        return data.resource_types.join(',');
      },
    },
    {
      label: t('机型'),
      field: 'device_class',
      render: ({ data }: {data: DbResourceModel}) => data.device_class || '--',
    },
    {
      label: t('地域'),
      field: 'city',
      render: ({ data }: {data: DbResourceModel}) => data.city || '--',
    },
    {
      label: t('园区'),
      field: 'sub_zone',
      render: ({ data }: {data: DbResourceModel}) => data.sub_zone || '--',
    },
    {
      label: t('CPU(核)'),
      field: 'bk_cpu',
    },
    {
      label: t('内存'),
      field: 'bkMemText',
      render: ({ data }: {data: DbResourceModel}) => data.bkMemText || '0 M',
    },
    {
      label: t('磁盘容量(G)'),
      field: 'bk_disk',
      minWidth: 120,
      render: ({ data }: {data: DbResourceModel}) => (
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
      width: 100,
      render: ({ data }: {data: DbResourceModel}) => (
        <db-popconfirm
          confirm-handler={() => handleRemove(data)}
          content={t('主机将被落到空闲机，如需要可再次导入')}
          title={t('确认移除选中的主机')}>
          <BkButton
            text
            theme="primary">
            {t('移除')}
          </BkButton>
        </db-popconfirm>
      ),
    },
  ];

  const isShowImportHost = ref(false);

  let searchParams = {};

  const fetchData = () => {
    tableRef.value.fetchData(searchParams);
  };

  // 搜索
  const handleSearch = (params: Record<string, any>) => {
    searchParams = params;
    fetchData();
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

  // 移除主机
  const handleRemove = (data: DbResourceModel) => removeResource({
    bk_host_ids: [data.bk_host_id],
  }).then(() => {
    fetchData();
    tableRef.value.removeSelectByKey(data.bk_host_id);
    messageSuccess(t('移除成功'));
  });

  // 批量移除
  const handleBatchRemove = () => removeResource({
    bk_host_ids: selectionHostIdList.value,
  }).then(() => {
    fetchData();
    Object.values(selectionHostIdList.value).forEach((hostId) => {
      tableRef.value.removeSelectByKey(hostId);
    });
    selectionHostIdList.value = [];
    messageSuccess(t('移除成功'));
  });

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

</script>
<style lang="less">
.resource-pool-list-page {
  .action-box {
    display: flex;

    .quick-search-btn {
      width: 32px;
      margin-left: auto;
    }
  }
}
</style>
