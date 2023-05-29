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
  <div
    v-if="props.data.length > 0"
    class="big-data-hdfs-host-table">
    <div class="search-box">
      <BkInput
        v-model="searchKey"
        clearable
        :placeholder="$t('请输入IP')"
        style="width: 320px; margin-left: auto;" />
    </div>
    <div>
      <div
        class="collapse-header"
        @click="handleToggleShowTable">
        <div class="header-text">
          <i class="db-icon-down-shape" />
          <span style="padding-left: 5px;">
            <span v-if="searchKey">{{ $t('已筛选') }}</span>
            {{ $t('共') }}
            <span class="ip-num">{{ serachList.length }}</span>
            {{ $t('台') }}
          </span>
        </div>
        <BkDropdown @click.stop>
          <div class="extends-action">
            <i class="db-icon-more" />
          </div>
          <template #content>
            <BkDropdownMenu>
              <BkDropdownItem @click="handleClearAll">
                {{ $t('清除所有') }}
              </BkDropdownItem>
              <BkDropdownItem @click="handleClearAbnormal">
                {{ $t('清除异常IP') }}
              </BkDropdownItem>
              <BkDropdownItem @click="handleCopyAll">
                {{ $t('复制所有IP') }}
              </BkDropdownItem>
              <BkDropdownItem @click="handleCopyAbnormal">
                {{ $t('复制异常IP') }}
              </BkDropdownItem>
            </BkDropdownMenu>
          </template>
        </BkDropdown>
      </div>
      <Transition mode="in-out">
        <BkLoading
          v-show="isShowTable"
          :loading="isLoading">
          <DbOriginalTable
            :columns="columns"
            :data="serachList"
            :is-searching="!!searchKey"
            :pagination="pagination"
            :settings="tableSetting"
            @clear-search="handleClearSearch"
            @page-limit-change="handlePaginationLimitChange"
            @page-value-change="handlePaginationCurrentChange" />
        </BkLoading>
      </Transition>
    </div>
  </div>
</template>
<script lang="tsx">
  import { useI18n } from 'vue-i18n';

  import type {
    HostDetails,
  } from '@services/types/ip';

  export type IHostTableData = HostDetails;
</script>
<script setup lang="tsx">
  import _ from 'lodash';
  import {
    computed,
    ref,
    shallowRef,
  } from 'vue';

  import { useCopy } from '@hooks';

  import DbStatus from '@components/db-status/index.vue';

  import tableSetting from './common/tableSetting';
  import useLocalPagination from './hook/useLocalPagination';

  import type { TableColumnRender } from '@/types/bkui-vue';

  interface Props {
    data: IHostTableData[],
  }

  interface Emits {
    (e: 'update:data', value: Array<IHostTableData>): void,
    (e: 'change', nameNode: Array<IHostTableData>, zookeeper: Array<IHostTableData>): void
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const copy = useCopy();
  const { t } = useI18n();

  const isLoading = ref(false);
  const localData = shallowRef(props.data);
  const isShowTable = ref(true);

  const nameNodeCheckedMap = shallowRef<Record<number, HostDetails>>({});
  const zookeeperCheckedMap = shallowRef<Record<number, HostDetails>>({});

  // 部署 NameNodes 最多2台
  const isNameNodeCheckDisabled = computed(() => Object.keys(nameNodeCheckedMap.value).length >= 2);
  // 部署 Zookeepers / JournalNodes最多3台
  const isZookeeperCheckDisabled = computed(() => Object.keys(zookeeperCheckedMap.value).length >= 3);

  const columns = [
    {
      label: t('主机ID'),
      field: 'host_id',
      render: ({ data }: TableColumnRender) => data.host_id || '--',
    },
    {
      label: 'IP',
      field: 'ip',
      render: ({ data }: {data: HostDetails}) => data.ip,
    },
    {
      label: t('部署NameNodes_2台'),
      width: '180px',
      render: ({ data }: {data: HostDetails}) => {
        const isDisabled = isNameNodeCheckDisabled.value && !nameNodeCheckedMap.value[data.host_id];
        const tooltipsOptions = {
          disabled: !isDisabled,
          content: t('最多只能选择两台'),
        };
        return (
          <span
            v-bk-tooltips={tooltipsOptions}
            key={data.host_id}>
            <bk-checkbox
              modelValue={Boolean(nameNodeCheckedMap.value[data.host_id])}
              disabled={isDisabled}
              onChange={(value: boolean) => handleNameNodesChange(value, data)} />
          </span>
        );
      },
    },
    {
      label: t('部署Zookeepers_JournalNodes_3台'),
      width: '250px',
      render: ({ data }: {data: HostDetails}) => {
        const isDisabled = isZookeeperCheckDisabled.value && !zookeeperCheckedMap.value[data.host_id];
        const tooltipsOptions = {
          disabled: !isDisabled,
          content: t('最多只能选择三台'),
        };
        return (
          <span
            v-bk-tooltips={tooltipsOptions}
            key={data.host_id}>
            <bk-checkbox
              modelValue={Boolean(zookeeperCheckedMap.value[data.host_id])}
              disabled={isDisabled}
              onChange={(value: boolean) => handleZookeeperChange(value, data)} />
          </span>
        );
      },
    },
    {
      label: t('机型'),
      field: 'cpu',
      render: ({ data }: TableColumnRender) => data.cpu || '--',
    },
    {
      label: t('机房'),
      field: 'bk_idc_name',
      render: ({ data }: TableColumnRender) => data.bk_idc_name || '--',
    },
    {
      label: t('主机名称'),
      field: 'host_name',
      render: ({ data }: TableColumnRender) => data.host_name || '--',
    },
    {
      label: t('Agent状态'),
      field: 'alive',
      render: ({ data }: TableColumnRender) => {
        const info = data.alive === 1 ? { theme: 'success', text: t('正常') } : { theme: 'danger', text: t('异常') };
        return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
      },
    },
    {
      label: t('云区域'),
      field: 'cloud_area',
      render: ({ data }: TableColumnRender) => data.cloud_area.name || '--',
    },
    {
      label: t('OS名称'),
      field: 'os_name',
      render: ({ data }: TableColumnRender) => data.os_name || '--',
    },
    {
      label: t('OS类型'),
      field: 'os_type',
      render: ({ data }: TableColumnRender) => data.os_type || '--',
    },
    {
      label: 'Agent ID',
      field: 'agent_id',
      render: ({ data }: TableColumnRender) => data.agent_id || '--',
    },
    {
      label: t('操作'),
      field: 'operation',
      width: 100,
      render: ({ index }: TableColumnRender) => (
        <bk-button
          text
          theme="primary"
          onClick={() => handleRemove(index)}>
          { t('删除') }
        </bk-button>
      ),
    },
  ];

  const triggerChange = () => {
    emits(
      'change',
      Object.values(nameNodeCheckedMap.value),
      Object.values(zookeeperCheckedMap.value),
    );
  };

  watch(() => props.data, () => {
    localData.value = props.data;

    const isEmpty = Object.keys(nameNodeCheckedMap.value).length < 1
      && Object.keys(zookeeperCheckedMap.value).length < 1;

    const nameNodeChecked = {} as Record<number, HostDetails>;
    const zookeeperChecked = {} as Record<number, HostDetails>;

    if (isEmpty) {
      _.forEach(props.data, (item) => {
        if (Object.keys(nameNodeChecked).length >= 2) {
          return;
        }
        nameNodeChecked[item.host_id] = item;
      });
      _.forEachRight(props.data, (item) => {
        if (Object.keys(zookeeperChecked).length >= 3) {
          return;
        }
        zookeeperChecked[item.host_id] = item;
      });
    } else {
      props.data.forEach((item) => {
        const hostId = item.host_id;
        if (nameNodeCheckedMap.value[hostId]) {
          nameNodeChecked[hostId] = nameNodeCheckedMap.value[hostId];
        }
        if (zookeeperCheckedMap.value[hostId]) {
          zookeeperChecked[hostId] = zookeeperCheckedMap.value[hostId];
        }
      });
    }
    nameNodeCheckedMap.value = nameNodeChecked;
    zookeeperCheckedMap.value = zookeeperChecked;
    triggerChange();
  }, {
    immediate: true,
  });

  const {
    searchKey,
    pagination,
    serachList,
    handlePaginationCurrentChange,
    handlePaginationLimitChange,
  } = useLocalPagination(localData);

  const handleClearSearch = () => {
    searchKey.value = '';
  };

  const handleToggleShowTable = () => {
    isShowTable.value = !isShowTable.value;
  };

  const handleNameNodesChange = (value: boolean, data: HostDetails) => {
    const checkedMap  = { ...nameNodeCheckedMap.value };
    if (value) {
      checkedMap[data.host_id] = data;
    } else {
      delete checkedMap[data.host_id];
    }
    nameNodeCheckedMap.value = checkedMap;
    triggerChange();
  };

  const handleZookeeperChange = (value: boolean, data: HostDetails) => {
    const checkedMap  = { ...zookeeperCheckedMap.value };
    if (value) {
      checkedMap[data.host_id] = data;
    } else {
      delete checkedMap[data.host_id];
    }
    zookeeperCheckedMap.value = checkedMap;
    triggerChange();
  };

  // 移除指定主机节点数
  const handleRemove = (index: number) => {
    const list = [...props.data];

    handleNameNodesChange(false, list[index]);
    handleZookeeperChange(false, list[index]);

    list.splice(index, 1);
    emits('update:data', list);
  };
  // 清空所有主机
  const handleClearAll = () => {
    nameNodeCheckedMap.value = {};
    zookeeperCheckedMap.value = {};
    triggerChange();
    emits('update:data', []);
  };
  // 清空异常主机
  const handleClearAbnormal = () => {
    const list = [...props.data];
    _.remove(list, _ => !_.alive);
    triggerChange();
  };

  // 复制所有主机IP
  const handleCopyAll = () => {
    const ipList = props.data.map(_ => _.ip);
    copy(ipList.join('\n'));
  };
  // 复制异常主机IP
  const handleCopyAbnormal = () => {
    const abnormalList = props.data.reduce((result, item) => {
      if (!item.alive) {
        result.push(item.ip);
      }
      return result;
    }, [] as Array<string>);
    copy(abnormalList.join('\n'));
  };
</script>
<style lang="less" scoped>
  .big-data-hdfs-host-table {
    display: block;

    .collapse-header {
      display: flex;
      height: 42px;
      padding-right: 12px;
      padding-left: 18px;
      font-size: 12px;
      color: #63656e;
      cursor: pointer;
      background: #f0f1f5;
      align-items: center;

      .header-text {
        margin-right: auto;
      }

      .ip-num {
        padding: 0 2px;
        font-weight: bold;
        color: #3a84ff;
      }

      .extends-action {
        display: flex;
        width: 20px;
        height: 20px;
        margin-left: auto;
        font-size: 20px;
        align-items: center;
        justify-content: center;
        border-radius: 2px;

        &:hover {
          color: #3a84ff;
          background: #e1ecff;
        }
      }
    }

    .search-box {
      display: flex;
      margin-top: -32px;
      margin-bottom: 16px;
      justify-content: flex-end;
    }

    :deep(.bk-table) {
      th {
        background-color: #f5f7fa !important;
      }
    }
  }
</style>
