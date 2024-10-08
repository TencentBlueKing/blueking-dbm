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
              <BkDropdownItem @click="handleShowBatchAssign">
                {{ t('重新设置资源归属') }}
              </BkDropdownItem>
              <BkDropdownItem
                v-bk-tooltips="{
                  content: t('仅支持同业务的主机'),
                  disabled: isSelectedSameBiz,
                }"
                :class="isSelectedSameBiz ? undefined : 'disabled-cls'"
                @click="handleShowBatchAddTags">
                {{ t('添加资源标签') }}
              </BkDropdownItem>
              <BkDropdownItem
                v-if="type === 'business'"
                @click="handleShowBatchCovertToPublic">
                {{ t('退回公共资源池') }}
              </BkDropdownItem>
              <BkDropdownItem @click="handleShowBatchSetting"> {{ t('设置主机属性') }} </BkDropdownItem>
              <BkDropdownItem @click="handleShowBatchMoveToFaultPool"> {{ t('转入故障池') }} </BkDropdownItem>
              <BkDropdownItem
                v-if="type !== 'business'"
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
    <BatchSetting
      v-model:is-show="isShowBatchSetting"
      :data="selectionHostIdList"
      @change="handleBatchSettingChange" />
    <BatchCovertToPublic
      v-model:is-show="isShowBatchCovertToPublic"
      :selected="selectionListWholeDataMemo"
      @refresh="handleRefresh" />
    <BatchAddTags
      v-model:is-show="isShowBatchAddTags"
      :selected="selectionListWholeDataMemo"
      @refresh="handleRefresh" />
    <BatchMoveToRecyclePool
      v-model:is-show="isShowBatchMoveToRecyclePool"
      :selected="selectionListWholeDataMemo"
      @refresh="handleRefresh" />
    <BatchMoveToFaultPool
      v-model:is-show="isShowBatchMoveToFaultPool"
      :selected="selectionListWholeDataMemo"
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
      :selected="selectionListWholeDataMemo"
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
  import { useRouter } from 'vue-router';

  import DbResourceModel from '@services/model/db-resource/DbResource';
  import { fetchList } from '@services/source/dbresourceResource';

  import { useGlobalBizs } from '@stores';

  import DbIcon from '@components/db-icon';
  import DiskPopInfo from '@components/disk-pop-info/DiskPopInfo.vue';
  import HostAgentStatus from '@components/host-agent-status/Index.vue';

  import { execCopy } from '@utils';

  import { ResourcePool } from '../../type';

  import BatchAddTags from './components/batch-add-tags/Index.vue';
  import BatchAssign from './components/batch-assign/Index.vue';
  import BatchConvertToBusiness from './components/batch-convert-to-business/Index.vue';
  import BatchCovertToPublic from './components/batch-covert-to-public/Index.vue';
  import BatchMoveToFaultPool from './components/batch-move-to-fault-pool/Index.vue';
  import BatchMoveToRecyclePool from './components/batch-move-to-recycle-pool/Index.vue';
  import BatchSetting from './components/batch-setting/Index.vue';
  import BatchUndoImport from './components/batch-undo-import/Index.vue';
  import HostOperationTip from './components/HostOperationTip.vue';
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

  const dataSource = (params: ServiceParameters<typeof fetchList>) => fetchList({
    for_biz: curBizId.value,
    ...params,
  });

  let searchParams: Record<string, any> = {};
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
        <bk-popover
          theme="light"
          placement="top"
          popover-delay={[300, 0]}
          disable-outside-click>
          {{
            default: () => (
              <div class='resource-owner-wrapper'>
                <div class='resource-owner'>
                  <bk-tag
                    theme={
                      (data.for_biz.bk_biz_id === 0 || !data.for_biz.bk_biz_name)
                        ? 'success'
                        : ''
                    }
                  >
                    {t('所属业务')} : {data.forBizDisplay}
                  </bk-tag>
                  <bk-tag
                    theme={
                      (!data.resource_type || data.resource_type === 'PUBLIC')
                        ? 'success'
                        : ''
                    }
                  >
                    {t('所属DB')} : {data.resourceTypeDisplay}
                  </bk-tag>
                  {
                    data.labels && Array.isArray(data.labels) && (
                      data.labels.map(item => (<bk-tag>{item.name}</bk-tag>))
                    )}
                </div>
                {
                  props.type !== ResourcePool.public && (
                    <DbIcon
                      type="edit"
                      class='operation-icon'
                      onClick={() => handleEdit(data)}
                    />
                  )
                }
              </div>
            ),
            content: () => (
              <div class='resource-owner-tips'>
                <strong>{t('所属业务')}：</strong>
                <div class='resource-owner-tips-values mb-10'>
                  <bk-tag
                    theme={
                      (data.for_biz.bk_biz_id === 0 || !data.for_biz.bk_biz_name)
                        ? 'success'
                        : ''
                    }
                  >
                    {data.forBizDisplay}
                  </bk-tag>
                </div>
                <strong>{t('所属DB')}</strong>
                <div class='resource-owner-tips-values mb-10'>
                  <bk-tag
                    theme={
                      (!data.resource_type || data.resource_type === 'PUBLIC')
                        ? 'success'
                        : ''
                    }
                  >
                    {data.resourceTypeDisplay}
                  </bk-tag>
                </div>
                {
                  !!data.labels.length && (
                    <>
                      <strong>{t('资源标签')}</strong>
                      <div class='resource-owner-tips-values mb-10'>
                        {
                          data.labels.map(item => (<bk-tag>{item.name}</bk-tag>))
                        }
                      </div>
                    </>
                  )
                }

              </div>
            )
          }}
        </bk-popover>
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
        <DiskPopInfo data={data.storage_device} trigger='click'>
          <span style="line-height: 40px; color: #3a84ff;cursor: pointer">
            {data.bk_disk}
          </span>
        </DiskPopInfo>
      ),
    },
    {
      label: t('操作'),
      field: 'id',
      width: 300,
      fixed: 'right',
      render: ({ data }: { data: DbResourceModel }) => (
        <>
          {props.type === ResourcePool.public && (
            <HostOperationTip
              data={data}
              type="to_biz"
              onRefresh={fetchData}
              tip={t('确认后，主机将标记为业务专属')}
              title={t('确认转入业务资源池？')}
            >
              <bk-button
                text
                theme="primary">
                {t('转入业务资源池')}
              </bk-button>
            </HostOperationTip>
          )}
          {
            [ResourcePool.business, ResourcePool.global].includes(props.type) && <>
              {
                props.type === ResourcePool.business ? (
                  <HostOperationTip
                    data={data}
                    title={t('确认退回公共资源池？')}
                    tip={t('确认后，主机不再归属当前业务')}
                    type='to_public'
                    onRefresh={fetchData} >
                    <bk-button
                      text
                      theme="primary">
                      {t('退回公共资源池')}
                    </bk-button>
                  </HostOperationTip>
                ) : (
                  <HostOperationTip
                    data={data}
                    title={t('确认转入待回收池？')}
                    tip={t('确认后，主机将标记为待回收，等待处理')}
                    type='to_recycle'
                    onRefresh={fetchData} >
                    <bk-button
                      text
                      theme="primary">
                      {t('转入待回收池')}
                    </bk-button>
                  </HostOperationTip>
                )
              }
              <HostOperationTip
                data={data}
                title={t('确认转入待故障池？')}
                tip={t('确认后，主机将标记为故障，等待处理')}
                type='to_fault'
                onRefresh={fetchData} >
                <bk-button
                  text
                  class='ml-16'
                  theme="primary">
                  {t('转入故障池')}
                </bk-button>
              </HostOperationTip>
              <HostOperationTip
                data={data}
                title={t('确认撤销导入？')}
                tip={t('确认后，主机将从资源池移回原有模块')}
                type='undo_import'
                onRefresh={fetchData}>
                <bk-button
                  text
                  class='ml-16'
                  theme="primary">
                  {t('撤销导入')}
                </bk-button>
              </HostOperationTip>
            </>
          }
        </>
      ),
    },
  ];

  const fetchData = () => {
    tableRef.value.fetchData(searchParams);
  };

  const handleSearch = (params: Record<string, any>) => {
    searchParams = params;
    tableRef.value.fetchData(params);
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

  // 跳转操作记录
  const handleGoOperationRecord = () => {
    router.push({
      name: 'resourcePoolOperationRecord',
    });
  };

  const handleSelection = (list: number[], selectionListWholeData: DbResourceModel[]) => {
    selectionHostIdList.value = list;
    selectionListWholeDataMemo = selectionListWholeData;
    isSelectedSameBiz.value = (new Set(selectionListWholeData.map(item => item.for_biz.bk_biz_id))).size === 1;
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

  const handleShowBatchAddTags = () => {
    isShowBatchAddTags.value = true;
  }

  const handleShowBatchAssign = () => {
    isShowBatchAssign.value = true;
  }

  const handleEdit = (data: DbResourceModel) => {
    isShowUpdateAssign.value = true;
    curEditData.value = data;
  }

  const handleRefresh = () => {
    fetchData();
    Object.values(selectionHostIdList.value).forEach((hostId) => {
      tableRef.value.removeSelectByKey(hostId);
    });
    selectionListWholeDataMemo = [];
    selectionHostIdList.value = [];
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
