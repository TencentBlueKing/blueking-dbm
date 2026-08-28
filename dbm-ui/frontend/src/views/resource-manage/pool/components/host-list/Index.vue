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
    ref="pageRef"
    class="resource-pool-list-page">
    <div
      ref="searchBoxRef"
      class="mb-25">
      <SearchBox @change="handleSearch" />
    </div>
    <div class="action-box mb-16">
      <template v-if="type === ResourcePool.public">
        <AuthButton
          action-id="resource_pool_manage"
          :disabled="selectionHostIdList.length < 1"
          theme="primary"
          @click="handleShowBatchConvertToBusiness">
          {{ t('转入业务资源池') }}
        </AuthButton>
      </template>
      <template v-else>
        <BkDropdown
          :popover-options="{
            clickContentAutoHide: true,
            renderDirective: 'show',
          }"
          trigger="click">
          <BkButton :disabled="selectionHostIdList.length < 1">
            {{ t('批量操作') }}
            <DbIcon type="down-big" />
          </BkButton>
          <template #content>
            <BkDropdownMenu>
              <AuthTemplate action-id="resource_pool_manage">
                <BkDropdownItem @click="() => handleShowBatchAssign()">
                  {{ t('重新设置资源归属') }}
                </BkDropdownItem>
                <BkDropdownItem
                  :class="isSelectedGlobalResource || !isSelectedSameBiz ? 'disabled-cls' : ''"
                  @click="() => handleShowBatchAddTags()">
                  {{ t('添加资源标签') }}
                </BkDropdownItem>
                <BkDropdownItem
                  v-if="type === ResourcePool.business"
                  @click="handleShowBatchCovertToPublic">
                  {{ t('退回公共资源池') }}
                </BkDropdownItem>
                <BkDropdownItem @click="() => handleShowBatchSetting()"> {{ t('设置主机属性') }} </BkDropdownItem>
                <BkDropdownItem @click="() => handleShowBatchMoveToFaultPool()"> {{ t('转入故障池') }} </BkDropdownItem>
                <BkDropdownItem
                  v-if="type !== ResourcePool.business"
                  @click="handleShowBatchMoveToRecyclePool">
                  {{ t('转入待回收池') }}
                </BkDropdownItem>
                <BkDropdownItem @click="handleShowBatchUndoImport"> {{ t('撤销导入') }} </BkDropdownItem>
              </AuthTemplate>
            </BkDropdownMenu>
          </template>
        </BkDropdown>
      </template>
      <BkDropdown
        :popover-options="{
          clickContentAutoHide: true,
        }"
        trigger="click">
        <BkButton
          class="ml-8"
          style="width: 80px">
          {{ t('复制') }}
          <DbIcon type="down-big" />
        </BkButton>
        <template #content>
          <BkDropdownMenu>
            <BkDropdownItem @click="handleCopySelectHost">
              {{ t('已选 IP') }}
            </BkDropdownItem>
            <BkDropdownItem @click="handleCopyAllHost">
              {{ copyAllHostText }}
            </BkDropdownItem>
            <BkDropdownItem @click="handleCopyAllAbnormalHost">
              {{ t('所有异常 IP') }}
            </BkDropdownItem>
          </BkDropdownMenu>
        </template>
      </BkDropdown>
      <BkDropdown
        :popover-options="{
          clickContentAutoHide: true,
          renderDirective: 'show',
        }"
        trigger="click">
        <BkButton
          class="ml-8"
          style="width: 80px">
          {{ t('导出') }}
          <DbIcon type="down-big" />
        </BkButton>
        <template #content>
          <BkDropdownMenu>
            <AuthTemplate action-id="resource_pool_manage">
              <BkDropdownItem @click="handleExportAll">
                {{ isFilter ? t('导出所有（筛选后）') : t('导出所有（全量）') }}
              </BkDropdownItem>
              <BkDropdownItem
                :class="{ 'disabled-cls': selectionHostIdList.length === 0 }"
                @click="handleExportSelected">
                {{ t('导出已选') }}
              </BkDropdownItem>
            </AuthTemplate>
          </BkDropdownMenu>
        </template>
      </BkDropdown>
      <BkButton
        class="ml-8"
        @click="handleRefresh">
        <DbIcon
          class="mr-4"
          type="refresh" />
        {{ t('刷新数据') }}
      </BkButton>
      <RouterLink
        style="margin-left: auto"
        target="_blank"
        :to="{
          name: props.type === ResourcePool.global ? 'ticketPlatformManage' : 'bizTicketManage',
          query: {
            ticket_type_search: `ticket_type__in#${TicketTypes.RESOURCE_IMPORT}`,
            ticket_type__in: TicketTypes.RESOURCE_IMPORT,
          },
        }">
        <AuthButton action-id="resource_manage">
          <DbIcon type="history-2" />
          <span class="ml-4">{{ t('导入记录') }}</span>
        </AuthButton>
      </RouterLink>
    </div>
    <DbTable
      ref="tableRef"
      :bk-ui-settings="settings"
      class="db-instance-table"
      :container-height="tableContentHeight"
      :data-source="dataSource"
      releate-url-query
      row-class-name="my-row-cls"
      row-key="bk_host_id"
      selectable
      @bk-ui-settings-change="updateTableSettings"
      @selection="handleSelection">
      <TableColumn
        col-key="ip"
        fixed="left"
        :min-width="130"
        title="IP" />
      <TableColumn
        col-key="bk_cloud_name"
        :title="t('管控区域')"
        :width="100" />
      <TableColumn
        col-key="agent_status"
        :title="t('Agent 状态')"
        :width="100">
        <template #default="{ row }: { row: DbResourceModel }">
          <HostAgentStatus :data="row.agent_status" />
        </template>
      </TableColumn>
      <TableColumn
        col-key="status"
        :title="t('资源状态')"
        :width="100">
        <template #default="{ row }: { row: DbResourceModel }">
          {{ row.resourceStatusDisplay }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="resourceOwner"
        :title="t('资源归属')"
        :width="320">
        <template #default="{ row }: { row: DbResourceModel }">
          <BkPopover
            disable-outside-click
            placement="top"
            :popover-delay="[300, 0]"
            theme="light">
            <template #content>
              <div class="resource-owner-tips">
                <strong>{{ t('所属业务') }}：</strong>
                <div class="resource-owner-tips-values mb-10">
                  <BkTag :theme="row.for_biz.bk_biz_id === 0 || !row.for_biz.bk_biz_name ? 'success' : ''">
                    {{ row.forBizDisplay }}
                  </BkTag>
                </div>
                <strong>{{ t('所属DB') }}</strong>
                <div class="resource-owner-tips-values mb-10">
                  <BkTag :theme="!row.resource_type || row.resource_type === 'PUBLIC' ? 'success' : ''">
                    {{ row.resourceTypeDisplay }}
                  </BkTag>
                </div>
                <template v-if="row.labels.length > 0">
                  <strong>{{ t('资源标签') }}</strong>
                  <div class="resource-owner-tips-values mb-10">
                    <BkTag
                      v-for="item in row.labels"
                      :key="item.name">
                      {{ item.name }}
                    </BkTag>
                  </div>
                </template>
              </div>
            </template>
            <div class="resource-owner-wrapper">
              <div class="resource-owner">
                <BkTag :theme="row.for_biz.bk_biz_id === 0 || !row.for_biz.bk_biz_name ? 'success' : ''">
                  {{ t('所属业务') }} : {{ row.forBizDisplay }}
                </BkTag>
                <BkTag :theme="!row.resource_type || row.resource_type === 'PUBLIC' ? 'success' : ''">
                  {{ t('所属DB') }} : {{ row.resourceTypeDisplay }}
                </BkTag>
                <BkTag
                  v-for="item in row.labels"
                  :key="item.name">
                  {{ item.name }}
                </BkTag>
              </div>
              <AuthButton
                v-if="props.type !== ResourcePool.public"
                action-id="resource_pool_manage"
                :permission="row.permission.resource_pool_manage"
                text
                @click="() => handleEdit(row)">
                <DbIcon
                  class="operation-icon"
                  type="edit" />
              </AuthButton>
            </div>
          </BkPopover>
        </template>
      </TableColumn>
      <TableColumn
        col-key="city"
        :title="t('地域')"
        :width="80">
        <template #default="{ row }: { row: DbResourceModel }">{{ row.city || '--' }}</template>
      </TableColumn>
      <TableColumn
        col-key="sub_zone"
        :title="t('园区')"
        :width="90">
        <template #default="{ row }: { row: DbResourceModel }">{{ row.sub_zone || '--' }}</template>
      </TableColumn>
      <TableColumn
        col-key="rack_id"
        :title="t('机架')"
        :width="80">
        <template #default="{ row }: { row: DbResourceModel }">{{ row.rack_id || '--' }}</template>
      </TableColumn>
      <TableColumn
        col-key="same_svr_owner_count"
        sorter
        :title="t('同母机台数')"
        :width="100">
        <template #default="{ row }: { row: DbResourceModel }">
          <span>{{ row.sameHostCountDisplay }} </span>
          <BkButton
            v-if="row.bk_svr_owner_asset_id && row.same_svr_owner_count > 0"
            v-bk-tooltips="t('复制同母机 IP')"
            class="same-host-copy-icon ml-4"
            text
            theme="primary"
            @click="handleCopySameHost(row)">
            <DbIcon type="copy" />
          </BkButton>
        </template>
      </TableColumn>
      <!-- <TableColumn
        col-key="os_type"
        :title="t('操作系统类型')"
        :width="120">
        <template #default="{ row }: { row: DbResourceModel }">{{ row.os_type || '--' }}</template>
      </TableColumn> -->
      <TableColumn
        col-key="os_name"
        :title="t('操作系统名称')"
        :width="150">
        <template #default="{ row }: { row: DbResourceModel }">{{ row.os_name || '--' }}</template>
      </TableColumn>
      <TableColumn
        col-key="device_class"
        :min-width="130"
        :title="t('机型')">
        <template #default="{ row }: { row: DbResourceModel }">{{ row.device_class || '--' }}</template>
      </TableColumn>
      <TableColumn
        col-key="bk_cpu"
        :title="t('CPU（核）')" />
      <TableColumn
        col-key="bkMemText"
        :min-width="90"
        :title="t('内存（G）')" />
      <TableColumn
        col-key="total_data_storage_cap"
        :title="t('数据盘容量（G）')"
        :width="120">
        <template #default="{ row }: { row: DbResourceModel }">
          <DiskPopInfo
            :data="row.storage_device"
            trigger="click">
            <span style="line-height: 40px; color: #3a84ff; cursor: pointer">
              {{ row.total_data_storage_cap || 0 }}
            </span>
          </DiskPopInfo>
        </template>
      </TableColumn>
      <TableColumn
        col-key="createTimeDisplay"
        :title="t('转入时间')"
        :width="180" />
      <TableColumn
        col-key="operator"
        :title="t('转入人')"
        :width="120" />
    </DbTable>
    <BatchSetting
      v-model:is-show="isShowBatchSetting"
      :selected="selectionList"
      @success="handleRefresh" />
    <BatchCovertToPublic
      v-model:is-show="isShowBatchCovertToPublic"
      :selected="selectionList"
      @refresh="handleRefresh" />
    <BatchAddTags
      v-model:is-show="isShowBatchAddTags"
      :selected="selectionList"
      @refresh="handleRefresh" />
    <BatchMoveToRecyclePool
      v-model:is-show="isShowBatchMoveToRecyclePool"
      :selected="selectionList"
      @refresh="handleRefresh" />
    <BatchMoveToFaultPool
      v-model:is-show="isShowBatchMoveToFaultPool"
      :selected="selectionList"
      @refresh="handleRefresh" />
    <BatchUndoImport
      v-model:is-show="isShowBatchUndoImport"
      :selected="selectionList"
      @refresh="handleRefresh" />
    <BatchConvertToBusiness
      v-model:is-show="isShowBatchConvertToBusiness"
      :biz-id="currentBizId"
      :selected="selectionList"
      @refresh="handleRefresh" />
    <BatchAssign
      v-model:is-show="isShowBatchAssign"
      :selected="selectionList"
      @refresh="handleRefresh" />
    <UpdateAssign
      v-model:is-show="isShowUpdateAssign"
      :edit-data="curEditData"
      @refresh="handleRefresh" />
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import DbResourceModel from '@services/model/db-resource/DbResource';
  import { fetchList, fetchSameSvrOwnerIps, resourceExport } from '@services/source/dbresourceResource';

  import { useTableSettings } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { TicketTypes } from '@common/const';
  import { UserPersonalSettings } from '@common/const/userPersonalSettings';

  import DbIcon from '@components/db-icon';
  import DbTable from '@components/db-table/IndexNew.vue';
  import DiskPopInfo from '@components/disk-pop-info/DiskPopInfo.vue';
  import HostAgentStatus from '@components/host-agent-status/Index.vue';

  import { execCopy, messageWarn } from '@utils';

  import { useResizeObserver } from '@vueuse/core';

  import { ResourcePool } from '../../type';

  import BatchAddTags from './components/batch-add-tags/Index.vue';
  import BatchAssign from './components/batch-assign/Index.vue';
  import BatchConvertToBusiness from './components/batch-convert-to-business/Index.vue';
  import BatchCovertToPublic from './components/batch-covert-to-public/Index.vue';
  import BatchMoveToFaultPool from './components/batch-move-to-fault-pool/Index.vue';
  import BatchMoveToRecyclePool from './components/batch-move-to-recycle-pool/Index.vue';
  import BatchSetting from './components/batch-setting/Index.vue';
  import BatchUndoImport from './components/batch-undo-import/Index.vue';
  import { isValueEmpty } from './components/search-box/components/utils';
  import SearchBox from './components/search-box/Index.vue';
  import UpdateAssign from './components/update-assign/Index.vue';

  interface Props {
    type?: ResourcePool;
  }

  const props = withDefaults(defineProps<Props>(), {
    type: ResourcePool.global,
  });

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();
  const tableContentHeight = ref(window.innerHeight - 320);

  const { settings, updateTableSettings } = useTableSettings(UserPersonalSettings.RESOURCE_POOL_HOST_LIST_SETTINGS, {
    disabled: ['ip'],
  });

  const pageRef = useTemplateRef('pageRef');
  const searchBoxRef = useTemplateRef('searchBoxRef');
  const tableRef = useTemplateRef('tableRef');

  const isShowBatchSetting = ref(false);
  const isShowBatchCovertToPublic = ref(false);
  const isShowBatchMoveToRecyclePool = ref(false);
  const isShowBatchMoveToFaultPool = ref(false);
  const isShowBatchUndoImport = ref(false);
  const isShowBatchConvertToBusiness = ref(false);
  const isShowBatchAssign = ref(false);
  const isShowUpdateAssign = ref(false);
  const isShowBatchAddTags = ref(false);

  const selectionList = shallowRef<DbResourceModel[]>([]);
  const curEditData = shallowRef<DbResourceModel>({} as DbResourceModel);
  const searchParams = shallowRef<Record<string, any>>({});

  const selectionHostIdList = computed(() => selectionList.value.map((selectionItem) => selectionItem.bk_host_id));
  const isSelectedSameBiz = computed(
    () => new Set(selectionList.value.map((item) => item.for_biz.bk_biz_id)).size === 1,
  );
  const isSelectedGlobalResource = computed(() => selectionList.value.some((item) => item.for_biz.bk_biz_id === 0));
  const isFilter = computed(() => Object.values(searchParams.value).some((item) => !isValueEmpty(item)));

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

  const copyAllHostText = computed(() => {
    return `${t('所有 IP')}（${isFilter.value ? t('筛选后') : t('全量')}）`;
  });

  useResizeObserver(searchBoxRef, () => {
    const targetPageHeight = window.innerHeight - 200;
    const pageHeightDiff = pageRef.value!.getBoundingClientRect().height - targetPageHeight;
    tableContentHeight.value -= pageHeightDiff;
    tableRef.value?.updateTableHeight(tableContentHeight.value);
  });

  const dataSource = (params: ServiceParameters<typeof fetchList>) =>
    fetchList({
      for_biz: curBizId.value,
      ...params,
    });

  const fetchData = () => {
    tableRef.value!.fetchData(searchParams.value);
  };

  const handleSearch = (params: Record<string, any>) => {
    searchParams.value = params;
    fetchData();
  };

  // 批量设置
  const handleShowBatchSetting = () => {
    isShowBatchSetting.value = true;
  };

  // 复制所有主机
  const handleCopyAllHost = () => {
    fetchList({
      limit: -1,
      offset: 0,
      ...searchParams.value,
    }).then((data) => {
      if (!data.results.length) {
        messageWarn(t('暂无可复制 IP'));
        return;
      }
      const ipList = data.results.map((item) => item.ip);
      execCopy(ipList.join('\n'), t('复制成功，共n条', { n: ipList.length }));
    });
  };

  // 复制已选主机
  const handleCopySelectHost = () => {
    const ipList = selectionList.value.map((item) => item.ip);
    execCopy(ipList.join('\n'), t('复制成功，共n条', { n: ipList.length }));
  };

  // 复制所有异常主机
  const handleCopyAllAbnormalHost = () => {
    fetchList({
      limit: -1,
      offset: 0,
      ...searchParams.value,
    }).then((data) => {
      if (!data.results.length) {
        messageWarn(t('暂无可复制 IP'));
        return;
      }
      const ipList = data.results.reduce<string[]>((result, item) => {
        if (!item.agent_status) {
          result.push(item.ip);
        }
        return result;
      }, []);
      execCopy(ipList.join('\n'), t('复制成功，共n条', { n: ipList.length }));
    });
  };

  const handleExportAll = () => {
    if (isFilter.value) {
      resourceExport({
        ...searchParams.value,
        limit: -1,
        offset: 0,
      });
    } else {
      resourceExport({
        limit: -1,
        offset: 0,
      });
    }
  };

  const handleExportSelected = () => {
    if (selectionHostIdList.value.length === 0) {
      return;
    }
    resourceExport({
      hosts: selectionList.value.map((item) => item.ip).join(','),
      limit: -1,
      offset: 0,
    });
  };

  const handleSelection = (_keys: string[], list: DbResourceModel[]) => {
    selectionList.value = list;
  };

  const handleShowBatchCovertToPublic = () => {
    isShowBatchCovertToPublic.value = true;
  };

  const handleShowBatchMoveToRecyclePool = () => {
    isShowBatchMoveToRecyclePool.value = true;
  };

  const handleShowBatchMoveToFaultPool = () => {
    isShowBatchMoveToFaultPool.value = true;
  };

  const handleShowBatchUndoImport = () => {
    isShowBatchUndoImport.value = true;
  };

  const handleShowBatchConvertToBusiness = () => {
    isShowBatchConvertToBusiness.value = true;
  };

  const handleShowBatchAddTags = () => {
    if (isSelectedGlobalResource.value) {
      messageWarn(t('仅业务资源支持添加标签'));
      return;
    }
    if (!isSelectedSameBiz.value) {
      messageWarn(t('仅支持同业务的主机批量添加资源标签'));
      return;
    }
    isShowBatchAddTags.value = true;
  };

  const handleShowBatchAssign = () => {
    isShowBatchAssign.value = true;
  };

  const handleEdit = (data: DbResourceModel) => {
    isShowUpdateAssign.value = true;
    curEditData.value = data;
  };

  const handleRefresh = () => {
    // tableRef.value!.clearSelected();
    fetchData();
  };

  // 复制同母机 IP
  const handleCopySameHost = (row: DbResourceModel) => {
    fetchSameSvrOwnerIps({ bk_host_id: row.bk_host_id }).then((res) => {
      const ipList = res.ips;
      if (ipList.length === 0) {
        messageWarn(t('暂无可复制 IP'));
        return;
      }
      execCopy(ipList.join('\n'), t('复制成功，共n条', { n: ipList.length }));
    });
  };

  onMounted(() => {
    fetchData();
  });
</script>
<style lang="less">
  .resource-pool-list-page {
    .action-box {
      display: flex;
      align-items: center;

      .search-selector {
        width: 560px;
        height: 32px;
        margin-left: auto;
      }
    }

    .my-row-cls {
      .same-host-copy-icon {
        font-size: 14px;
        color: #3a84ff;
        cursor: pointer;
        visibility: hidden;
      }

      .resource-owner-wrapper {
        display: flex;
        align-items: center;

        .resource-owner {
          display: flex;
          align-items: center;
          overflow: hidden;
        }

        .operation-icon {
          margin-left: 7.5px;
          font-size: 12px;
          color: #3a84ff;
          cursor: pointer;
          visibility: hidden;
        }
      }

      &:hover {
        .operation-icon {
          display: block;
          visibility: visible;
        }

        .same-host-copy-icon {
          visibility: visible;
        }
      }
    }
  }

  .disabled-cls {
    color: #dcdee5 !important;
    cursor: not-allowed !important;
    background-color: #f9fafd !important;
  }

  .resource-owner-tips {
    min-width: 280px;
    padding: 9px 0 0;
    color: #63656e;

    .resource-owner-tips-values {
      margin: 6px 0;
    }
  }
</style>
