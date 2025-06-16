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
          :disabled="selectionHostIdList.length < 1"
          :popover-options="{
            renderDirective: 'show',
            hideIgnoreReference: true,
          }">
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
          hideIgnoreReference: true,
        }">
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
            ticket_type__in: TicketTypes.RESOURCE_IMPORT,
          },
        }">
        <AuthButton action-id="resource_manage">
          <DbIcon type="history-2" />
          <span class="ml-4">{{ t('导入记录') }}</span>
        </AuthButton>
      </RouterLink>
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
      :data="selectionHostIdList"
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
      :biz-id="(currentBizId as number)"
      :selected="selectionList"
      @refresh="handleRefresh" />
    <BatchAssign
      v-model:is-show="isShowBatchAssign"
      :selected="selectionList"
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

  import { TicketTypes } from '@common/const';

  import DbIcon from '@components/db-icon';
  import DiskPopInfo from '@components/disk-pop-info/DiskPopInfo.vue';
  import HostAgentStatus from '@components/host-agent-status/Index.vue';

  import { execCopy, messageWarn } from '@utils';

  import { ResourcePool } from '../../type';

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
    type?: ResourcePool;
  }

  const props = withDefaults(defineProps<Props>(), {
    type: ResourcePool.global,
  });

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

  const { handleChange: handleSettingChange, setting: tableSetting } = useTableSetting();

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
  // 是否选中同一业务的主机
  const isSelectedSameBiz = ref(false);
  // 是否选中公共资源池主机
  const isSelectedGlobalResource = ref(false);

  const selectionList = shallowRef<DbResourceModel[]>([]);
  const curEditData = shallowRef<DbResourceModel>({} as DbResourceModel);
  const searchParams = shallowRef<Record<string, any>>({});

  const selectionHostIdList = computed(() => selectionList.value.map((selectionItem) => selectionItem.bk_host_id));

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
    const isFilter = Object.keys(searchParams.value).length > 0;
    return `${t('所有 IP')}（${isFilter ? t('筛选后') : t('全量')}）`;
  });

  const dataSource = (params: ServiceParameters<typeof fetchList>) =>
    fetchList({
      for_biz: curBizId.value,
      ...params,
    });

  const tableColumn = computed(() => [
    {
      field: 'ip',
      fixed: 'left',
      label: 'IP',
      minWidth: 130,
    },
    {
      field: 'bk_cloud_name',
      label: t('管控区域'),
      minWidth: 100,
    },
    {
      field: 'agent_status',
      label: t('Agent 状态'),
      render: ({ data }: { data: DbResourceModel }) => <HostAgentStatus data={data.agent_status} />,
      width: 100,
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
                  <auth-button
                    action-id='resource_pool_manage'
                    permission={data.permission.resource_pool_manage}
                    text
                    onClick={() => handleEdit(data)}>
                    <DbIcon
                      class='operation-icon'
                      type='edit'
                    />
                  </auth-button>
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
      showOverflow: true,
      width: 80,
    },
    {
      field: 'sub_zone',
      label: t('园区'),
      render: ({ data }: { data: DbResourceModel }) => data.sub_zone || '--',
      showOverflow: true,
      width: 90,
    },
    {
      field: 'rack_id',
      label: t('机架'),
      render: ({ data }: { data: DbResourceModel }) => data.rack_id || '--',
      showOverflow: true,
      width: 80,
    },
    {
      field: 'os_type',
      label: t('操作系统类型'),
      render: ({ data }: { data: DbResourceModel }) => data.os_type || '--',
      showOverflow: true,
      width: 120,
    },
    {
      field: 'os_name',
      label: t('操作系统名称'),
      render: ({ data }: { data: DbResourceModel }) => data.os_name || '--',
      showOverflow: true,
      width: 150,
    },
    {
      field: 'device_class',
      label: t('机型'),
      minWidth: 130,
      render: ({ data }: { data: DbResourceModel }) => data.device_class || '--',
      showOverflow: true,
    },
    {
      field: 'bk_cpu',
      label: t('CPU(核)'),
    },
    {
      field: 'bkMemText',
      label: t('内存'),
      minWidth: 90,
      render: ({ data }: { data: DbResourceModel }) => data.bkMemText || '0 M',
      showOverflow: true,
    },
    {
      field: 'bk_disk',
      label: t('磁盘容量(G)'),
      render: ({ data }: { data: DbResourceModel }) => (
        <DiskPopInfo
          data={data.storage_device}
          trigger='click'>
          <span style='line-height: 40px; color: #3a84ff;cursor: pointer'>{data.bk_disk}</span>
        </DiskPopInfo>
      ),
      width: 100,
    },
    {
      field: 'updateAtDisplay',
      label: t('转入时间'),
      width: 180,
    },
    {
      field: 'operator',
      label: t('转入人'),
      showOverflow: true,
      width: 120,
    },
  ]);

  const fetchData = () => {
    tableRef.value!.fetchData(searchParams.value, {});
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

  const handleSelection = (list: number[], selectionListWholeData: DbResourceModel[]) => {
    selectionList.value = selectionListWholeData;
    isSelectedSameBiz.value = new Set(selectionListWholeData.map((item) => item.for_biz.bk_biz_id)).size === 1;
    isSelectedGlobalResource.value = selectionListWholeData.some((item) => item.for_biz.bk_biz_id === 0);
  };

  const handleClearSearch = () => {
    searchBoxRef.value!.clearValue();
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
    tableRef.value!.clearSelected();
    fetchData();
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
