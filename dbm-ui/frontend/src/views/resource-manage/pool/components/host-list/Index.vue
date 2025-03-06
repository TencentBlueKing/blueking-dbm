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
    <div class="action-box mb-16">
      <template v-if="type === ResourcePool.public">
        <BkButton
          :disabled="selectionHostIdList.length < 1"
          theme="primary"
          @click="handleShowBatchConvertToBusiness">
          {{ t('转入业务资源池') }}
        </BkButton>
      </template>
      <template v-else>
        <BkDropdown :disabled="selectionHostIdList.length < 1">
          <BkButton
            class="ml-8"
            :disabled="selectionHostIdList.length < 1">
            {{ t('批量操作') }}
            <DbIcon type="down-big" />
          </BkButton>
          <template #content>
            <BkDropdownMenu>
              <BkDropdownItem @click="() => handleShowBatchAssign()">
                {{ t('重新设置资源归属') }}
              </BkDropdownItem>
              <BkDropdownItem
                v-bk-tooltips="{
                  content: t('仅支持同业务的主机'),
                  disabled: isSelectedSameBiz,
                }"
                :class="isSelectedSameBiz ? undefined : 'disabled-cls'"
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
      <AuthButton
        action-id="resource_operation_view"
        class="quick-search-btn"
        @click="handleGoTaskHistory">
        <DbIcon type="history-2" />
        <span class="ml-4">{{ t('导入记录') }}</span>
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
    <BatchSetting
      v-model:is-show="isShowBatchSetting"
      :data="operatHostList"
      @change="handleBatchSettingChange" />
    <BatchCovertToPublic
      v-model:is-show="isShowBatchCovertToPublic"
      :selected="selectionListWholeDataMemo"
      @refresh="handleRefresh" />
    <BatchAddTags
      v-model:is-show="isShowBatchAddTags"
      :selected="operatHostList"
      @refresh="handleRefresh" />
    <BatchMoveToRecyclePool
      v-model:is-show="isShowBatchMoveToRecyclePool"
      :selected="selectionListWholeDataMemo"
      @refresh="handleRefresh" />
    <BatchMoveToFaultPool
      v-model:is-show="isShowBatchMoveToFaultPool"
      :selected="operatHostList"
      @refresh="handleRefresh" />
    <BatchUndoImport
      v-model:is-show="isShowBatchUndoImport"
      :selected="selectionListWholeDataMemo"
      @refresh="handleRefresh" />
    <BatchConvertToBusiness
      v-model:is-show="isShowBatchConvertToBusiness"
      :biz-id="(currentBizId as number)"
      :selected="selectionListWholeDataMemo"
      @refresh="handleRefresh" />
    <BatchAssign
      v-model:is-show="isShowBatchAssign"
      :selected="operatHostList"
      @refresh="handleRefresh" />
    <UpdateAssign
      v-model:is-show="isShowUpdateAssign"
      :edit-data="(curEditData as DbResourceModel)"
      @refresh="handleRefresh" />
  </div>
</template>
<script setup lang="tsx">
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import DbResourceModel from '@services/model/db-resource/DbResource';
  import { fetchList } from '@services/source/dbresourceResource';

  import { useGlobalBizs } from '@stores';

  import DbIcon from '@components/db-icon';
  import DiskPopInfo from '@components/disk-pop-info/DiskPopInfo.vue';
  import HostAgentStatus from '@components/host-agent-status/Index.vue';

  // import MoreActionExtend from '@components/more-action-extend/Index.vue';
  import { execCopy } from '@utils';

  import { ResourcePool } from '../../type';
  // import HostOperationTip from './components/HostOperationTip.vue';
  import { useImportResourcePoolTooltip } from '../hooks/useImportResourcePoolTip';

  import BatchAddTags from './components/batch-add-tags/Index.vue';
  import BatchAssign from './components/batch-assign/Index.vue';
  import BatchConvertToBusiness from './components/batch-convert-to-business/Index.vue';
  import BatchCovertToPublic from './components/batch-covert-to-public/Index.vue';
  import BatchMoveToFaultPool from './components/batch-move-to-fault-pool/Index.vue';
  import BatchMoveToRecyclePool from './components/batch-move-to-recycle-pool/Index.vue';
  import BatchSetting from './components/batch-setting/Index.vue';
  import BatchUndoImport from './components/batch-undo-import/Index.vue';
  import RenderTable from './components/RenderTable.vue';
  import SearchBox from './components/search-box/Index.vue';
  import UpdateAssign from './components/update-assign/Index.vue';
  import useTableSetting from './hooks/useTableSetting';

  interface Props {
    type: ResourcePool;
  }

  const props = withDefaults(defineProps<Props>(), {
    type: ResourcePool.global,
  });

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

  const { handleChange: handleSettingChange, setting: tableSetting } = useTableSetting();
  const { taskHistoryListHref } = useImportResourcePoolTooltip();

  const searchBoxRef = ref();
  const tableRef = ref();
  const selectionHostIdList = ref<number[]>([]);
  const isShowBatchSetting = ref(false);
  const isShowBatchCovertToPublic = ref(false);
  const isShowBatchMoveToRecyclePool = ref(false);
  const isShowBatchMoveToFaultPool = ref(false);
  const isShowBatchUndoImport = ref(false);
  const isShowBatchConvertToBusiness = ref(false);
  const isShowBatchAssign = ref(false);
  const isShowUpdateAssign = ref(false);
  const isShowBatchAddTags = ref(false);
  const curEditData = ref<DbResourceModel>({} as DbResourceModel);
  const isSelectedSameBiz = ref(false);

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

  const dataSource = (params: ServiceParameters<typeof fetchList>) =>
    fetchList({
      for_biz: curBizId.value,
      ...params,
    });

  let searchParams: Record<string, any> = {};
  let selectionListWholeDataMemo: DbResourceModel[] = [];
  let operatHostList: DbResourceModel[] = [];

  const tableColumn = computed(() => [
    {
      field: 'ip',
      fixed: 'left',
      label: 'IP',
      minWidth: 110,
    },
    {
      field: 'bk_cloud_name',
      label: t('管控区域'),
      minWidth: 80,
    },
    {
      field: 'agent_status',
      label: t('Agent 状态'),
      minWidth: 100,
      render: ({ data }: { data: DbResourceModel }) => <HostAgentStatus data={data.agent_status} />,
    },
    {
      field: 'resourceOwner',
      label: t('资源归属'),
      render: ({ data }: { data: DbResourceModel }) => (
        <bk-popover
          placement='top'
          popover-delay={[300, 0]}
          theme='light'
          disable-outside-click>
          {{
            content: () => (
              <div class='resource-owner-tips'>
                <strong>{t('所属业务')}：</strong>
                <div class='resource-owner-tips-values mb-10'>
                  <bk-tag theme={data.for_biz.bk_biz_id === 0 || !data.for_biz.bk_biz_name ? 'success' : ''}>
                    {data.forBizDisplay}
                  </bk-tag>
                </div>
                <strong>{t('所属DB')}</strong>
                <div class='resource-owner-tips-values mb-10'>
                  <bk-tag theme={!data.resource_type || data.resource_type === 'PUBLIC' ? 'success' : ''}>
                    {data.resourceTypeDisplay}
                  </bk-tag>
                </div>
                {!!data.labels.length && (
                  <>
                    <strong>{t('资源标签')}</strong>
                    <div class='resource-owner-tips-values mb-10'>
                      {data.labels.map((item) => (
                        <bk-tag>{item.name}</bk-tag>
                      ))}
                    </div>
                  </>
                )}
              </div>
            ),
            default: () => (
              <div class='resource-owner-wrapper'>
                <div class='resource-owner'>
                  <bk-tag theme={data.for_biz.bk_biz_id === 0 || !data.for_biz.bk_biz_name ? 'success' : ''}>
                    {t('所属业务')} : {data.forBizDisplay}
                  </bk-tag>
                  <bk-tag theme={!data.resource_type || data.resource_type === 'PUBLIC' ? 'success' : ''}>
                    {t('所属DB')} : {data.resourceTypeDisplay}
                  </bk-tag>
                  {data.labels && Array.isArray(data.labels) && data.labels.map((item) => <bk-tag>{item.name}</bk-tag>)}
                </div>
                {props.type !== ResourcePool.public && (
                  <DbIcon
                    class='operation-icon'
                    type='edit'
                    onClick={() => handleEdit(data)}
                  />
                )}
              </div>
            ),
          }}
        </bk-popover>
      ),
      width: 320,
    },
    {
      field: 'city',
      label: t('地域'),
      render: ({ data }: { data: DbResourceModel }) => data.city || '--',
    },
    {
      field: 'sub_zone',
      label: t('园区'),
      render: ({ data }: { data: DbResourceModel }) => data.sub_zone || '--',
    },
    {
      field: 'rack_id',
      label: t('机架'),
      render: ({ data }: { data: DbResourceModel }) => data.rack_id || '--',
    },
    {
      field: 'os_type',
      label: t('操作系统类型'),
      render: ({ data }: { data: DbResourceModel }) => data.os_type || '--',
      width: 120,
    },
    {
      field: 'os_name',
      label: t('操作系统名称'),
      render: ({ data }: { data: DbResourceModel }) => data.os_name || '--',
      width: 120,
    },
    {
      field: 'device_class',
      label: t('机型'),
      render: ({ data }: { data: DbResourceModel }) => data.device_class || '--',
    },
    {
      field: 'bk_cpu',
      label: t('CPU(核)'),
    },
    {
      field: 'bkMemText',
      label: t('内存'),
      render: ({ data }: { data: DbResourceModel }) => data.bkMemText || '0 M',
    },
    {
      field: 'bk_disk',
      label: t('磁盘容量(G)'),
      minWidth: 120,
      render: ({ data }: { data: DbResourceModel }) => (
        <DiskPopInfo
          data={data.storage_device}
          trigger='click'>
          <span style='line-height: 40px; color: #3a84ff;cursor: pointer'>{data.bk_disk}</span>
        </DiskPopInfo>
      ),
    },
    {
      field: 'updateAtDisplay',
      label: t('转入时间'),
    },
    {
      field: 'updater',
      label: t('转入人'),
      render: ({ data }: { data: DbResourceModel }) => data.updater || '--',
      width: 180,
    },
    // {
    //   field: 'id',
    //   fixed: 'right',
    //   label: t('操作'),
    //   render: ({ data }: { data: DbResourceModel }) => (
    //     <>
    //       {props.type === ResourcePool.public && (
    //         <HostOperationTip
    //           data={data}
    //           tip={t('确认后，主机将标记为业务专属')}
    //           title={t('确认转入业务资源池？')}
    //           type='to_biz'
    //           onRefresh={fetchData}>
    //           <bk-button
    //             theme='primary'
    //             text>
    //             {t('转入业务资源池')}
    //           </bk-button>
    //         </HostOperationTip>
    //       )}
    //       {[ResourcePool.business, ResourcePool.global].includes(props.type) && (
    //         <>
    //           <bk-button
    //             theme='primary'
    //             text
    //             onClick={() => handleShowBatchAssign(data)}>
    //             {t('重新设置资源归属')}
    //           </bk-button>
    //           <bk-button
    //             class='ml-16'
    //             theme='primary'
    //             text
    //             onClick={() => handleShowBatchAddTags(data)}>
    //             {t('添加资源标签')}
    //           </bk-button>
    //           {props.type === ResourcePool.business ? (
    //             <HostOperationTip
    //               data={data}
    //               tip={t('确认后，主机不再归属当前业务')}
    //               title={t('确认退回公共资源池？')}
    //               type='to_public'
    //               onRefresh={fetchData}>
    //               <bk-button
    //                 class='ml-16'
    //                 theme='primary'
    //                 text>
    //                 {t('退回公共资源池')}
    //               </bk-button>
    //             </HostOperationTip>
    //           ) : (
    //             <bk-button
    //               class='ml-16'
    //               theme='primary'
    //               text
    //               onClick={() => handleShowBatchSetting(data)}>
    //               {t('设置主机属性')}
    //             </bk-button>
    //           )}
    //           <MoreActionExtend class='ml-16'>
    //             {props.type === ResourcePool.business && (
    //               <Bk-Dropdown-Item onClick={() => handleShowBatchSetting(data)}>
    //                 <bk-button
    //                   theme='primary'
    //                   text>
    //                   {t('设置主机属性')}
    //                 </bk-button>
    //               </Bk-Dropdown-Item>
    //             )}
    //             <Bk-Dropdown-Item onClick={() => handleShowBatchMoveToFaultPool(data)}>
    //               <bk-button
    //                 theme='primary'
    //                 text>
    //                 {t('转入故障池')}
    //               </bk-button>
    //             </Bk-Dropdown-Item>
    //             {props.type !== ResourcePool.business && (
    //               <Bk-Dropdown-Item>
    //                 <HostOperationTip
    //                   data={data}
    //                   tip={t('确认后，主机将标记为待回收，等待处理')}
    //                   title={t('确认转入待回收池？')}
    //                   type='to_recycle'
    //                   onRefresh={fetchData}>
    //                   <bk-button
    //                     theme='primary'
    //                     text>
    //                     {t('转入待回收池')}
    //                   </bk-button>
    //                 </HostOperationTip>
    //               </Bk-Dropdown-Item>
    //             )}
    //             <Bk-Dropdown-Item>
    //               <HostOperationTip
    //                 data={data}
    //                 tip={t('确认后，主机将从资源池移回原有模块')}
    //                 title={t('确认撤销导入？')}
    //                 type='undo_import'
    //                 onRefresh={fetchData}>
    //                 <bk-button
    //                   theme='primary'
    //                   text>
    //                   {t('撤销导入')}
    //                 </bk-button>
    //               </HostOperationTip>
    //             </Bk-Dropdown-Item>
    //           </MoreActionExtend>
    //         </>
    //       )}
    //     </>
    //   ),
    //   width: props.type === ResourcePool.public ? 120 : 380,
    // },
  ]);

  const fetchData = () => {
    tableRef.value.fetchData(searchParams);
  };

  const handleSearch = (params: Record<string, any>) => {
    searchParams = params;
    tableRef.value.fetchData(params);
  };

  // 批量设置
  const handleShowBatchSetting = (data?: DbResourceModel) => {
    operatHostList = data ? [data] : selectionListWholeDataMemo;
    isShowBatchSetting.value = true;
  };

  // 复制所有主机
  const handleCopyAllHost = () => {
    fetchList({
      limit: -1,
      offset: 0,
    }).then((data) => {
      const ipList = data.results.map((item) => item.ip);
      execCopy(ipList.join('\n'), `${t('复制成功n个IP', { n: ipList.length })}\n`);
    });
  };

  // 复制已选主机
  const handleCopySelectHost = () => {
    const ipList = selectionListWholeDataMemo.map((item) => item.ip);
    execCopy(ipList.join('\n'), `${t('复制成功n个IP', { n: ipList.length })}\n`);
  };

  // 复制所有异常主机
  const handleCopyAllAbnormalHost = () => {
    fetchList({
      limit: -1,
      offset: 0,
    }).then((data) => {
      const ipList = data.results.reduce<string[]>((result, item) => {
        if (!item.agent_status) {
          result.push(item.ip);
        }
        return result;
      }, []);
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

  // 跳转历史任务
  const handleGoTaskHistory = () => {
    window.open(taskHistoryListHref);
  };

  const handleSelection = (list: number[], selectionListWholeData: DbResourceModel[]) => {
    selectionHostIdList.value = list;
    selectionListWholeDataMemo = selectionListWholeData;
    isSelectedSameBiz.value = new Set(selectionListWholeData.map((item) => item.for_biz.bk_biz_id)).size === 1;
  };

  const handleClearSearch = () => {
    searchBoxRef.value.clearValue();
  };

  const handleShowBatchCovertToPublic = () => {
    isShowBatchCovertToPublic.value = true;
  };

  const handleShowBatchMoveToRecyclePool = () => {
    isShowBatchMoveToRecyclePool.value = true;
  };

  const handleShowBatchMoveToFaultPool = (data?: DbResourceModel) => {
    operatHostList = data ? [data] : selectionListWholeDataMemo;
    isShowBatchMoveToFaultPool.value = true;
  };

  const handleShowBatchUndoImport = () => {
    isShowBatchUndoImport.value = true;
  };

  const handleShowBatchConvertToBusiness = () => {
    isShowBatchConvertToBusiness.value = true;
  };

  const handleShowBatchAddTags = (data?: DbResourceModel) => {
    operatHostList = data ? [data] : selectionListWholeDataMemo;
    isShowBatchAddTags.value = true;
  };

  const handleShowBatchAssign = (data?: DbResourceModel) => {
    operatHostList = data ? [data] : selectionListWholeDataMemo;
    isShowBatchAssign.value = true;
  };

  const handleEdit = (data: DbResourceModel) => {
    isShowUpdateAssign.value = true;
    curEditData.value = data;
  };

  const handleRefresh = () => {
    fetchData();
    Object.values(selectionHostIdList.value).forEach((hostId) => {
      tableRef.value.removeSelectByKey(hostId);
    });
    selectionListWholeDataMemo = [];
    operatHostList = [];
    selectionHostIdList.value = [];
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

      .quick-search-btn {
        margin-left: auto;
      }

      .search-selector {
        width: 560px;
        height: 32px;
        margin-left: auto;
      }
    }

    .my-row-cls {
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
