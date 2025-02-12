<template>
  <div class="dirty-machines-page">
    <BkAlert
      class="mb-16"
      closable
      theme="info"
      :title="t('集群部署等操作新主机的任务，如任务执行失败，相应的主机将会被挪到这里，等待人工确认')" />
    <div class="header-action mb-16">
      <span
        v-bk-tooltips="{
          content: t('只能选择“移入待回收的主机”'),
          disabled: enableWaitForRecycle,
        }"
        class="inline-block">
        <BkButton
          :disabled="!enableWaitForRecycle"
          @click="batchTransferHosts">
          {{ t('移入待回收') }}
        </BkButton>
      </span>
      <span
        v-bk-tooltips="{
          content: enableMarkProcess ? t('标记为已处理的 IP，将会删除记录') : t('只能选择“标记为处理的主机”'),
        }"
        class="inline-block">
        <BkButton
          class="ml-8"
          :disabled="!enableMarkProcess"
          @click="batchMarkProcessHosts">
          {{ t('标记为已处理') }}
        </BkButton>
      </span>
      <span
        v-bk-tooltips="{
          content: t('请选择主机'),
          disabled: selectedHosts.length > 0,
        }"
        class="inline-block">
        <BkButton
          class="ml-8"
          :disabled="selectedHosts.length === 0"
          @click="handleCopySelected">
          {{ t('复制已选IP') }}
        </BkButton>
      </span>
      <DbSearchSelect
        class="ml-8"
        :data="searchSelectData"
        :get-menu-list="getMenuList"
        :model-value="searchValue"
        :placeholder="t('请输入或选择条件搜索')"
        style="width: 500px"
        unique-select
        :validate-values="validateSearchValues"
        @change="handleSearchValueChange" />
    </div>
    <!-- <DbTable
      ref="tableRef"
      :columns="tableColumn"
      :data-source="dataSource"
      selectable
      @clear-search="clearSearchValue"
      @column-filter="columnFilterChange"
      @column-sort="columnSortChange"
      @select="handleSelect"
      @select-all="handleSelectAll" /> -->
    <DbTable
      ref="tableRef"
      :columns="tableColumn"
      :data-source="dataSource"
      primary-key="bk_host_id"
      selectable
      @clear-search="clearSearchValue"
      @column-filter="columnFilterChange"
      @column-sort="columnSortChange"
      @selection="handleSelection" />
  </div>
</template>
<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import type { ISearchItem } from 'bkui-vue/lib/search-select/utils';
  import {
    onMounted,
    ref,
  } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import DirtyMachinesModel from '@services/model/db-resource/dirtyMachines';
  import {
    deleteDirtyRecords,
    getDirtyMachines,
    transferDirtyMachines,
  } from '@services/source/dbdirty';
  import { getTicketTypes } from '@services/source/ticket';
  import { getUserList } from '@services/source/user';

  import { useLinkQueryColumnSerach } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import {
    execCopy,
    getMenuListSearch,
    getSearchSelectorParams,
    messageSuccess
  } from '@utils';

  const router = useRouter();
  const { t } = useI18n();
  const useGlobalBizsStore = useGlobalBizs();

  const {
    columnAttrs,
    searchAttrs,
    searchValue,
    columnCheckedMap,
    columnFilterChange,
    columnSortChange,
    clearSearchValue,
    validateSearchValues,
    handleSearchValueChange,
  } = useLinkQueryColumnSerach({
    searchType: 'spotty_host',
    attrs: [],
    fetchDataFn: () => fetchData(),
    defaultSearchItem: {
      id: 'ip',
      name: 'IP'
    },
    isDiscardNondefault: true,
  });

  const dataSource = getDirtyMachines;

  const tableRef = ref();
  const ticketTypes = ref<Array<{id: string, name: string}>>([]);

  const selectedTransferHostMap = shallowRef<Record<number, DirtyMachinesModel>>({});

  const selectedHosts = computed(() => Object.values(selectedTransferHostMap.value));

  const enableWaitForRecycle = computed(() => selectedHosts.value.length > 0 && selectedHosts.value.every(item => item.is_dirty));
  const enableMarkProcess = computed(() => selectedHosts.value.length > 0 && selectedHosts.value.every(item => !item.is_dirty));

  const searchSelectData = computed(() => [
    {
      name: 'IP',
      id: 'ip',
      multiple: true,
      async: false,
    },
    {
      name: t('管控区域'),
      id: 'bk_cloud_id',
      multiple: true,
      children: searchAttrs.value.bk_cloud_id,
    },
    {
      name: t('业务'),
      id: 'bk_biz_id',
      multiple: true,
      children: searchAttrs.value.bk_biz_ids,
    },
    {
      name: t('单据类型'),
      id: 'ticket_types',
      multiple: true,
      children: searchAttrs.value.ticket_types,
    },
    {
      name: t('关联单据'),
      id: 'ticket_ids',
    },
    {
      name: t('关联任务'),
      id: 'task_ids',
    },
    {
      name: t('操作人'),
      id: 'operator',
    },
  ]);

  const bizName = useGlobalBizsStore.currentBizInfo?.name;

  const tableColumn = computed(() => [
    {
      label: 'IP',
      field: 'ip',
      fixed: 'left',
      render: ({ data }: {data: DirtyMachinesModel}) => (
        <TextOverflowLayout>
          {{
            default: () => data.ip,
            append: () => !data.is_dirty && (
              <db-icon
                type="attention"
                class="mark-tip-icon"
                v-bk-tooltips={t('主机已经被移动至 “x模块”，可以标记为已处理', { x: data.bk_module_infos.map(item => item.bk_module_name).join(' , ')})} />
            )
          }}
        </TextOverflowLayout>
      )
    },
    {
      label: t('管控区域'),
      field: 'bk_cloud_id',
      filter: {
        list: columnAttrs.value.bk_cloud_id,
        checked: columnCheckedMap.value.bk_cloud_id,
      },
      render: ({ data }: {data: DirtyMachinesModel}) => <span>{data.bk_cloud_name || '--'}</span>,
    },
    {
      label: t('业务'),
      field: 'bk_biz_id',
      filter: {
        list: columnAttrs.value.bk_biz_ids,
        checked: columnCheckedMap.value.bk_biz_id,
      },
      render: ({ data }: {data: DirtyMachinesModel}) => <span>{data.bk_biz_name || '--'}</span>,
    },
    {
      label: t('单据类型'),
      field: 'ticket_types',
      filter: {
        list: columnAttrs.value.ticket_types,
        checked: columnCheckedMap.value.ticket_types,
      },
      render: ({ data }: {data: DirtyMachinesModel}) => <span>{data.ticket_type_display || '--'}</span>,
    },
    {
      label: t('关联单据'),
      field: 'ticket_id',
      width: 170,
      render: ({ data }: {data: DirtyMachinesModel}) => (data.ticket_id
        ? <auth-button
            action-id="ticket_view"
            resource={data.ticket_id}
            permission={data.permission.ticket_view}
            text
            theme="primary"
            onClick={() => handleGoTicketDetail(data)}>
            {data.ticket_id}
          </auth-button>
        : '--')
      ,
    },
    {
      label: t('关联任务'),
      field: 'task_id',
      render: ({ data }: {data: DirtyMachinesModel}) => (data.task_id
        ? <auth-button
            action-id="flow_detail"
            resource={data.task_id}
            permission={data.permission.flow_detail}
            text
            theme="primary"
            onClick={() => handleGoTaskHistoryDetail(data)}>
            {data.task_id}
          </auth-button>
        : '--'),
    },
    {
      label: t('操作人'),
      field: 'operator',
    },
    {
      label: t('操作'),
      field: 'operations',
      width: 150,
      flexd: 'right',
      render: ({ data }: {data: DirtyMachinesModel}) => (
        data.is_dirty ?
          <bk-pop-confirm
            title={t('确认移入待回收机池？')}
            content={
              <span>
                <div>{data.ip}</div>
                <div>{t('主机将移入“x业务下的空闲机池”', { x: bizName})}</div>
              </span>
            }
            width={280}
            trigger="click"
            onConfirm={() => transferHosts(data)}>
            <auth-button
              action-id="dirty_pool_manage"
              permission={data.permission.dirty_pool_manage}
              theme="primary"
              text>
              {t('移入待回收')}
            </auth-button>
          </bk-pop-confirm>
          :
          <bk-pop-confirm
            title={t('确认标记为已经处理？')}
            content={
              <span>
                <div>{data.ip}</div>
                <div>{t('将会删除该条主机记录')}</div>
              </span>
            }
            width={280}
            trigger="click"
            onConfirm={() => markProcessHosts(data)}>
            <auth-button
              action-id="dirty_pool_manage"
              permission={data.permission.dirty_pool_manage}
              theme="primary"
              text>
              {t('标记为已处理')}
            </auth-button>
          </bk-pop-confirm>
      ),
    },
  ]);

  // const serachValidateValues = (
  //   payload: Record<'id'|'name', string>,
  //   values: Array<Record<'id'|'name', string>>,
  // ) => {
  //   if (payload.id === 'ip_list') {
  //     const [{ id }] = values;
  //     return Promise.resolve(_.every(id.split(','), item => ipv4.test(item)));
  //   }
  //   return Promise.resolve(true);
  // };

  // 获取数据
  const fetchData = () => {
    const searchParams = getSearchSelectorParams(searchValue.value);
    tableRef.value.fetchData({
      ...searchParams,
    });
  };

  const getMenuList = async (item: ISearchItem | undefined, keyword: string) => {
    if (item?.id !== 'operator' && keyword) {
      return getMenuListSearch(item, keyword, searchSelectData.value, searchValue.value);
    }

    // 没有选中过滤标签
    if (!item) {
      // 过滤掉已经选过的标签
      const selected = (searchValue.value || []).map(value => value.id);
      return searchSelectData.value.filter(item => !selected.includes(item.id));
    }

    // 远程加载执行人
    if (item.id === 'operator') {
      if (!keyword) {
        return [];
      }
      return getUserList({
        fuzzy_lookups: keyword,
      }).then(res => res.results.map(item => ({
        id: item.username,
        name: item.username,
      })));
    }

    // 不需要远层加载
    return searchSelectData.value.find(set => set.id === item.id)?.children || [];
  };

  // 获取单据类型
  const fetchTicketTypes = () => getTicketTypes({
    is_apply: 1,
  }).then((res) => {
    ticketTypes.value = res.map(item => ({
      id: item.key,
      name: item.value,
    }));
  });

  const handleSelection = (data: DirtyMachinesModel, list: DirtyMachinesModel[]) => {
    selectedTransferHostMap.value = list.reduce((result, item) => ({
      ...result,
      [item.bk_host_id]: item,
    }), {});
  };

  // 选择单台
  // const handleSelect = (data: { checked: boolean, row: DirtyMachinesModel }) => {
  //   const selectedMap = { ...selectedTransferHostMap.value };
  //   if (data.checked) {
  //     selectedMap[data.row.bk_host_id] = data.row;
  //   } else {
  //     delete selectedMap[data.row.bk_host_id];
  //   }

  //   selectedTransferHostMap.value = selectedMap;
  // };

  // 选择所有
  // const handleSelectAll = (data:{checked: boolean}) => {
  //   let selectedMap = { ...selectedTransferHostMap.value };
  //   if (data.checked) {
  //     selectedMap = (tableRef.value.getData() as DirtyMachinesModel[]).reduce((result, item) => ({
  //       ...result,
  //       [item.bk_host_id]: item,
  //     }), {});
  //   } else {
  //     selectedMap = {};
  //   }

  //   selectedTransferHostMap.value = selectedMap;
  // };

  const handleCopySelected = () => {
    const ipList = selectedHosts.value.map(item => item.ip)
    execCopy(ipList.join(','), t('复制成功，共n条', { n: ipList.length }));
  };

  // 转移单台主机
  const transferHosts = (data: DirtyMachinesModel) => {
    transferDirtyMachines({
      bk_host_ids: [data.bk_host_id],
    })
      .then(() => {
        messageSuccess(t('转移成功'));
        fetchData();
        selectedTransferHostMap.value = {};
      })
  };

  // 批量转移主机
  const batchTransferHosts = () => {
    InfoBox({
      width: 400,
      title: t('确认将n台主机移入待回收机池？', { n: selectedHosts.value.length }),
      cancelText: t('取消'),
      content: () => (
        <div class="dirty-machine-operation-infobox">
          <div class="tip-title">{t('主机将移入“x业务下的空闲机池”', { x: bizName})}</div>
          <div class="ip-list">
            {selectedHosts.value.map(item => <p>{item.ip}</p>)}
          </div>
        </div>
      ),
      onConfirm: () => transferDirtyMachines({
        bk_host_ids: selectedHosts.value.map(item => item.bk_host_id),
      })
        .then(() => {
          messageSuccess(t('转移成功'));
          fetchData();
          selectedTransferHostMap.value = {};
          return true;
        })
    });
  };

  // 标记单台为已处理
  const markProcessHosts = (data: DirtyMachinesModel) => {
    deleteDirtyRecords({
      bk_host_ids: [data.bk_host_id],
    })
      .then(() => {
        messageSuccess(t('标记成功'));
        fetchData();
        selectedTransferHostMap.value = {};
      })
  };

  // 批量标记单台为已处理
  const batchMarkProcessHosts = () => {
    InfoBox({
      width: 400,
      title: t('确认将n台主机标记为已处理？', { n: selectedHosts.value.length }),
      cancelText: t('取消'),
      content: () => (
        <div class="dirty-machine-operation-infobox">
          <div class="tip-title">{t('将会删除n条主机记录', { n: selectedHosts.value.length })}</div>
          <div class="ip-list">
            {selectedHosts.value.map(item => <p>{item.ip}</p>)}
          </div>
        </div>
      ),
      onConfirm: () => deleteDirtyRecords({
        bk_host_ids: selectedHosts.value.map(item => item.bk_host_id),
      })
        .then(() => {
          messageSuccess(t('标记成功'));
          fetchData();
          selectedTransferHostMap.value = {};
          return true;
        })
    });
  };

  const handleGoTicketDetail = (data: DirtyMachinesModel) => {
    const { href } = router.resolve({
      name: 'bizTicketManage',
      params: {
        ticketId: data.ticket_id,
      },
    });
    window.open(href.replace(/(\d)+/, `${data.bk_biz_id}`));
  };

  const handleGoTaskHistoryDetail = (data: DirtyMachinesModel) => {
    const { href } = router.resolve({
      name: 'taskHistoryDetail',
      params: {
        root_id: data.task_id,
      },
    });
    window.open(href.replace(/(\d)+/, `${data.bk_biz_id}`));
  };

  onMounted(() => {
    fetchTicketTypes();
  });
</script>

<style lang="less" scoped>
  .dirty-machines-page {
    .header-action {
      display: flex;
    }
  }
</style>

<style lang="less">
  .dirty-machine-operation-infobox {
    display: flex;
    width: 100%;
    flex-direction: column;
    justify-content: center;

    .tip-title {
      margin-bottom: 12px;
      font-size: 14px;
    }

    .ip-list {
      display: flex;
      padding: 12px 16px;
      background: #f5f7fa;
      flex-wrap: wrap;

      p {
        width: 33.33%;
        line-height: 20px;
      }
    }
  }

  .mark-tip-icon {
    display: inline-block;
    margin-left: 6px;
    font-size: 14px;
    color: #ff9c01;
    cursor: pointer;
  }
</style>
