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
        :placeholder="t('请输入IP')"
        style="width: 320px; margin-left: auto" />
    </div>
    <div>
      <slot name="header">
        <div
          class="collapse-header"
          @click="handleToggleShowTable">
          <div class="header-text">
            <i class="db-icon-down-shape" />
            <span style="padding-left: 5px">
              <span v-if="searchKey">{{ t('已筛选') }}</span>
              <span v-else>{{ t('共') }}</span>
              <span class="ip-num">{{ props.data.length }}</span>
              {{ t('台') }}
            </span>
          </div>
          <BkDropdown
            :popover-options="{
              clickContentAutoHide: true,
            }"
            trigger="click"
            @click.stop>
            <div class="extends-action">
              <i class="db-icon-more" />
            </div>
            <template #content>
              <BkDropdownMenu>
                <BkDropdownItem @click="handleClearAll">
                  {{ t('清除所有') }}
                </BkDropdownItem>
                <BkDropdownItem @click="handleClearAbnormal">
                  {{ t('清除异常IP') }}
                </BkDropdownItem>
                <BkDropdownItem @click="handleCopyAll">
                  {{ t('复制所有IP') }}
                </BkDropdownItem>
                <BkDropdownItem @click="handleCopyAbnormal">
                  {{ t('复制异常IP') }}
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
          <PrimaryTable
            :bk-ui-settings="tableSetting"
            :data="data"
            row-key="host_id">
            <TableColumn
              col-key="host_id"
              :title="t('主机ID')">
              <template #default="{ row }">
                {{ row.host_id || '--' }}
              </template>
            </TableColumn>
            <TableColumn
              col-key="ip"
              title="IP"
              :width="120" />
            <TableColumn
              col-key="instance_num"
              :title="t('每台主机实例数')"
              :width="150">
              <template #title>
                <BkPopover
                  :is-show="isShowBatchEditPopover"
                  placement="bottom"
                  theme="light"
                  trigger="manual"
                  :width="316">
                  <span @click="handleShowBatchEdit">
                    {{ t('每台主机实例数') }}
                    <i
                      class="db-icon-bulk-edit"
                      style="color: #3a84ff; margin-left: 5px" />
                  </span>
                  <template #content>
                    <div>
                      <div style="font-size: 16px; color: #313238; line-height: 24px">
                        {{ t('批量设置每台主机节点数') }}
                      </div>
                      <BkInput
                        v-model="batchEditValue"
                        :min="1"
                        style="margin: 19px 0 17px"
                        type="number" />
                      <div style="text-align: right">
                        <BkButton
                          theme="primary"
                          @click="handleSubmitBatchEditInstanceNum">
                          {{ t('确定') }}
                        </BkButton>
                        <BkButton
                          style="margin-left: 8px"
                          @click="handleCloseBatchEdit">
                          {{ t('取消') }}
                        </BkButton>
                      </div>
                    </div>
                  </template>
                </BkPopover>
              </template>
              <template #default="{ row }">
                <EditHostInstance
                  :key="row.instance_num"
                  :model-value="row.instance_num"
                  @change="handleInstanceNumChange($event, row)" />
              </template>
            </TableColumn>
            <TableColumn
              col-key="bk_cpu"
              :title="t('机型')">
              <template #default="{ row }">
                {{ row.bk_cpu || '--' }}
              </template>
            </TableColumn>
            <TableColumn
              col-key="bk_idc_name"
              :title="t('机房')">
              <template #default="{ row }">
                {{ row.bk_idc_name || '--' }}
              </template>
            </TableColumn>
            <TableColumn
              col-key="host_name"
              :title="t('主机名称')">
              <template #default="{ row }">
                {{ row.host_name || '--' }}
              </template>
            </TableColumn>
            <TableColumn
              col-key="alive"
              :title="t('Agent状态')">
              <template #default="{ row }">
                <DbStatus :theme="row.alive === 1 ? 'success' : 'danger'">
                  {{ row.alive === 1 ? t('正常') : t('异常') }}
                </DbStatus>
              </template>
            </TableColumn>
            <TableColumn
              col-key="cloud_area"
              :title="t('管控区域')">
              <template #default="{ row }">
                {{ row.cloud_area.name || '--' }}
              </template>
            </TableColumn>
            <TableColumn
              col-key="os_name"
              :title="t('OS名称')">
              <template #default="{ row }">
                {{ row.os_name || '--' }}
              </template>
            </TableColumn>
            <TableColumn
              col-key="os_type"
              :title="t('OS类型')">
              <template #default="{ row }">
                {{ row.os_type || '--' }}
              </template>
            </TableColumn>
            <TableColumn
              col-key="agent_id"
              title="Agent ID">
              <template #default="{ row }">
                {{ row.agent_id || '--' }}
              </template>
            </TableColumn>
            <TableColumn
              col-key="row-operation"
              :title="t('操作')"
              :width="100">
              <template #default="{ row }">
                <BkButton
                  text
                  theme="primary"
                  @click="handleRemove(row)">
                  {{ t('删除') }}
                </BkButton>
              </template>
            </TableColumn>
            <template #empty>
              <EmptyStatus
                :is-anomalies="false"
                :is-searching="!!searchKey"
                @clear-search="handleClearSearch" />
            </template>
          </PrimaryTable>
          <div class="table-footer">
            <BkPagination
              v-bind="pagination"
              :layout="['total', 'limit', 'list']"
              :model-value="pagination.current"
              @change="handlePaginationCurrentChange"
              @limit-change="handlePaginationLimitChange" />
          </div>
        </BkLoading>
      </Transition>
    </div>
  </div>
</template>
<script lang="tsx">
  import { useI18n } from 'vue-i18n';

  import type { HostInfo } from '@services/types';

  interface Props {
    data: Array<IHostTableDataWithInstance>;
    searchable?: boolean;
  }

  type Emits = (e: 'update:data', value: Array<IHostTableDataWithInstance>) => void;

  export interface IHostTableDataWithInstance extends HostInfo {
    instance_num: number;
  }
</script>
<script setup lang="tsx">
  import { ref, shallowRef, watch } from 'vue';

  import DbStatus from '@components/db-status/index.vue';
  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';

  import { execCopy, messageWarn } from '@utils';

  import tableSetting from '../common/tableSetting';
  import useLocalPagination from '../hook/useLocalPagination';

  import EditHostInstance from './components/EditHostInstance.vue';

  const props = withDefaults(defineProps<Props>(), {
    searchable: true,
  });
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const isLoading = ref(false);
  const isShowTable = ref(true);
  const batchEditValue = ref(1);
  const localTableData = shallowRef<Array<IHostTableDataWithInstance>>([]);
  const isShowBatchEditPopover = ref(false);

  let isInnerChange = false;
  watch(
    () => props.data,
    () => {
      if (isInnerChange) {
        isInnerChange = false;
        return;
      }
      localTableData.value = props.data;
    },
    {
      immediate: true,
    },
  );

  const { data, handlePaginationCurrentChange, handlePaginationLimitChange, pagination, searchKey, serachList } =
    useLocalPagination(localTableData);

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
    localTableData.value = localTableData.value.map((item) => ({
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
    const searchHostIdMap = serachList.value.reduce(
      (result, hostData) => ({
        ...result,
        [hostData.host_id]: true,
      }),
      {} as Record<number, boolean>,
    );

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
    const searchHostIdMap = serachList.value.reduce(
      (result, hostData) => {
        if (!hostData.alive) {
          return {
            ...result,
            [hostData.host_id]: true,
          };
        }
        return result;
      },
      {} as Record<number, boolean>,
    );

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
    const ipList = props.data.map((_) => _.ip);
    if (ipList.length < 1) {
      messageWarn(t('没有可以复制主机'));
      return;
    }
    execCopy(ipList.join('\n'), t('复制成功，共n条', { n: ipList.length }));
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
    execCopy(abnormalList.join('\n'), t('复制成功，共n条', { n: abnormalList.length }));
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

    :deep(.t-table__header) {
      th {
        background-color: #f5f7fa;
      }
    }

    .table-footer {
      display: flex;
      justify-content: flex-end;
      margin-top: 12px;
    }
  }
</style>
