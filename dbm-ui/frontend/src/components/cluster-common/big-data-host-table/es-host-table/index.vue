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
    class="big-data-es-host-table">
    <div
      v-if="searchable"
      class="search-box">
      <BkInput
        v-model="searchKey"
        :placeholder="$t('请输入IP')"
        style="width: 320px; margin-left: auto;" />
    </div>
    <div>
      <slot name="header">
        <div
          class="collapse-header"
          @click="handleToggleShowTable">
          <div class="header-text">
            <i class="db-icon-down-shape" />
            <span style="padding-left: 5px;">
              <span v-if="searchKey">{{ $t('已筛选') }}</span>
              <span v-else>{{ $t('共') }}</span>
              <span class="ip-num">{{ props.data.length }}</span>
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
      </slot>
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
            :thead="tableHeadOption"
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

  import type { HostDetails } from '@services/types/ip';

  export interface IHostTableDataWithInstance extends HostDetails {
    instance_num: number;
  }
</script>
<script setup lang="tsx">
  import {
    ref,
    shallowRef,
    watch,
  } from 'vue';

  import { useCopy } from '@hooks';

  import DbStatus from '@components/db-status/index.vue';

  import { messageWarn } from '@utils';

  import tableSetting from '../common/tableSetting';
  import useLocalPagination from '../hook/useLocalPagination';

  import EditHostInstance from './components/EditHostInstance.vue';

  interface Props {
    data: Array<IHostTableDataWithInstance>,
    searchable?: boolean,
  }

  interface Emits {
    (e: 'update:data', value: Array<IHostTableDataWithInstance>): void
  }

  const props = withDefaults(defineProps<Props>(), {
    searchable: true,
  });
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const copy = useCopy();
  const isLoading = ref(false);
  const isShowTable = ref(true);
  const batchEditValue = ref(1);
  const localTableData = shallowRef<Array<IHostTableDataWithInstance>>([]);
  const isShowBatchEditPopover = ref(false);

  const columns = [
    {
      label: t('主机ID'),
      field: 'host_id',
      render: ({ data }: {data: IHostTableDataWithInstance}) => data.host_id || '--',
    },
    {
      label: 'IP',
      field: 'ip',
      width: 120,
      render: ({ data }: {data: HostDetails}) => data.ip,
    },
    {
      label: t('每台主机实例数'),
      width: 150,
      render: ({ data }: {data: IHostTableDataWithInstance}) => (
        <EditHostInstance
          modelValue={data.instance_num}
          key={data.instance_num}
          onChange={value => handleInstanceNumChange(value, data)} />
      ),
    },
    {
      label: t('机型'),
      field: 'cpu',
      render: ({ data }: {data: IHostTableDataWithInstance}) => data.cpu || '--',
    },
    {
      label: t('机房'),
      field: 'bk_idc_name',
      render: ({ data }: {data: IHostTableDataWithInstance}) => data.bk_idc_name || '--',
    },
    {
      label: t('主机名称'),
      field: 'host_name',
      render: ({ data }: {data: IHostTableDataWithInstance}) => data.host_name || '--',
    },
    {
      label: t('Agent状态'),
      field: 'alive',
      render: ({ data }: {data: IHostTableDataWithInstance}) => {
        const info = data.alive === 1 ? { theme: 'success', text: t('正常') } : { theme: 'danger', text: t('异常') };
        return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
      },
    },
    {
      label: t('管控区域'),
      field: 'cloud_area',
      render: ({ data }: {data: IHostTableDataWithInstance}) => data.cloud_area.name || '--',
    },
    {
      label: t('OS名称'),
      field: 'os_name',
      render: ({ data }: {data: IHostTableDataWithInstance}) => data.os_name || '--',
    },
    {
      label: t('OS类型'),
      field: 'os_type',
      render: ({ data }: {data: IHostTableDataWithInstance}) => data.os_type || '--',
    },
    {
      label: 'Agent ID',
      field: 'agent_id',
      render: ({ data }: {data: IHostTableDataWithInstance}) => data.agent_id || '--',
    },
    {
      label: t('操作'),
      field: 'operation',
      width: 100,
      render: ({ data }: {data: IHostTableDataWithInstance}) => (
        <bk-button
          text
          theme="primary"
          onClick={() => handleRemove(data)}>
          { t('删除') }
        </bk-button>
      ),
    },
  ];

  const tableHeadOption = {
    height: 40,
    isShow: true,
    cellFn: (data: {label: string}) => {
      if (data.label !== t('每台主机节点数')) {
        return data.label;
      }
      return (
        <bk-popover
          placement="bottom"
          theme="light"
          trigger="manual"
          isShow={isShowBatchEditPopover.value}
          width="316">
          {{
            default: () => (
              <span onClick={handleShowBatchEdit}>
                {data.label}
                <i
                  class="db-icon-bulk-edit"
                  style='color: #3A84FF; margin-left: 5px' />
              </span>
            ),
            content: () => (
              <div>
                <div style="font-size: 16px; color:#313238; line-height: 24px">
                  { t('批量设置每台主机节点数') }
                </div>
                <bk-input
                  type='number'
                  v-model={batchEditValue.value}
                  style="margin: 19px 0 17px;"
                  min={1} />
                <div style="text-align: right">
                  <bk-button
                    theme='primary'
                    onClick={handleSubmitBatchEditInstanceNum}>
                    { t('确定') }
                  </bk-button>
                  <bk-button
                    style="margin-left: 8px;"
                    onClick={handleCloseBatchEdit}>
                    { t('取消') }
                  </bk-button>
                </div>
              </div>
            ),
          }}
        </bk-popover>
      );
    },
  };

  let isInnerChange = false;
  watch(() => props.data, () => {
    if (isInnerChange) {
      isInnerChange = false;
      return;
    }
    localTableData.value = props.data;
  }, {
    immediate: true,
  });

  const {
    searchKey,
    pagination,
    serachList,
    handlePaginationCurrentChange,
    handlePaginationLimitChange,
  } = useLocalPagination(localTableData);

  const handleClearSearch = () => {
    searchKey.value = '';
  };

  const triggerChange = () => {
    isInnerChange = true;
    emits('update:data', localTableData.value);
  };

  const handleToggleShowTable = () => {
    isShowTable.value = !isShowTable.value;
  };

  // 显示批量编辑弹框
  const handleShowBatchEdit = () => {
    isShowBatchEditPopover.value = true;
  };

  // 隐藏批量编辑弹框
  const handleCloseBatchEdit = () => {
    isShowBatchEditPopover.value = false;
  };

  // 批量编辑每台主机节点数
  const handleSubmitBatchEditInstanceNum = () => {
    localTableData.value = localTableData.value.map(item => ({
      ...item,
      instance_num: batchEditValue.value,
    }));
    isShowBatchEditPopover.value = false;
    triggerChange();
  };
  // 标记指定主机节点数
  const handleInstanceNumChange = (value: number, hostData: IHostTableDataWithInstance) => {
    const list = [...localTableData.value];
    list.forEach((hostDataItem) => {
      if (hostDataItem.host_id === hostData.host_id) {
        // eslint-disable-next-line no-param-reassign
        hostDataItem.instance_num = value;
      }
    });
    localTableData.value = list;
    triggerChange();
  };
  // 移除指定主机节点数
  const handleRemove = (data: IHostTableDataWithInstance) => {
    const list = localTableData.value.reduce((result, item) => {
      if (item.host_id !== data.host_id) {
        result.push(item);
      }
      return result;
    }, [] as Array<IHostTableDataWithInstance>);
    localTableData.value = list;
    triggerChange();
  };
  // 清空所有主机
  const handleClearAll = () => {
    const searchHostIdMap = serachList.value.reduce((result, hostData) => ({
      ...result,
      [hostData.host_id]: true,
    }), {} as Record<number, boolean>);

    localTableData.value = props.data.reduce((result, hostData) => {
      if (!searchHostIdMap[hostData.host_id]) {
        result.push(hostData);
      }
      return result;
    }, [] as Array<IHostTableDataWithInstance>);
    triggerChange();
  };
  // 清空异常主机
  const handleClearAbnormal = () => {
    const searchHostIdMap = serachList.value.reduce((result, hostData) => {
      if (!hostData.alive) {
        return {
          ...result,
          [hostData.host_id]: true,
        };
      }
      return result;
    }, {} as Record<number, boolean>);

    localTableData.value = props.data.reduce((result, hostData) => {
      if (!searchHostIdMap[hostData.host_id]) {
        result.push(hostData);
      }
      return result;
    }, [] as Array<IHostTableDataWithInstance>);
    triggerChange();
  };

  // 复制所有主机IP
  const handleCopyAll = () => {
    const ipList = props.data.map(_ => _.ip);
    if (ipList.length < 1) {
      messageWarn(t('没有可以复制主机'));
      return;
    }
    copy(ipList.join('\n'));
  };
  // 复制异常主机IP
  const handleCopyAbnormal = () => {
    const abnormalList = serachList.value.reduce((result, item) => {
      if (!item.alive) {
        result.push(item.ip);
      }
      return result;
    }, [] as Array<string>);
    if (abnormalList.length < 1) {
      messageWarn(t('没有可复制异常主机'));
      return;
    }
    copy(abnormalList.join('\n'));
  };
</script>
<style lang="less" scoped>
  .big-data-es-host-table {
    display: block;
    margin-top: 15px;

    .search-box {
      display: flex;
      margin-top: -48px;
      margin-bottom: 16px;
    }

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

    :deep(.bk-table) {
      th {
        background-color: #f5f7fa !important;
      }
    }
  }
</style>
