<template>
  <div class="dirty-machines-page">
    <BkAlert
      class="mb-16"
      closable
      theme="info"
      :title="t('集群部署等操作新主机的任务，如任务执行失败，相应的主机将会被挪到这里，等待人工确认')" />
    <div class="header-action mb-16">
      <span
        v-bk-tooltips="{content: $t('请选择主机'), disabled: selectedHosts.length > 0 }"
        class="inline-block">
        <BkButton
          :disabled="selectedHosts.length === 0"
          @click="transferHosts(selectedHosts)">
          {{ $t('移入待回收') }}
        </BkButton>
      </span>
      <span
        v-bk-tooltips="{content: $t('请选择主机'), disabled: selectedHosts.length > 0 }"
        class="inline-block">
        <BkButton
          class="ml-8"
          :disabled="selectedHosts.length === 0"
          @click="handleCopySelected">
          {{ $t('复制已选IP') }}
        </BkButton>
      </span>
      <DbSearchSelect
        v-model="searchValues"
        class="ml-8"
        :data="serachData"
        :placeholder="$t('请输入操作人或选择条件搜索')"
        style="width: 500px"
        unique-select
        :validate-values="serachValidateValues"
        value-split-code=","
        @change="handleSearch" />
    </div>
    <DbTable
      ref="tableRef"
      :columns="tableColumn"
      :data-source="dataSource"
      @clear-search="handleClearSearch"
      @select="handleSelect"
      @select-all="handleSelectAll" />
  </div>
</template>
<script setup lang="tsx">
  import _ from 'lodash';
  import {
    onMounted,
    ref,
  } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import DirtyMachinesModel from '@services/model/db-resource/dirtyMachines';
  import {
    getDirtyMachines,
    transferDirtyMachines,
  } from '@services/source/dbdirty';
  import { getTicketTypes } from '@services/source/ticket';

  import {
    useCopy,
    useInfoWithIcon,
  } from '@hooks';

  import { ipv4 } from '@common/regex';

  import {
    getSearchSelectorParams,
    messageSuccess,
  } from '@utils';

  const router = useRouter();
  const copy = useCopy();
  const { t } = useI18n();

  const dataSource = getDirtyMachines;

  const tableRef = ref();
  const searchValues = ref([]);
  const ticketTypes = ref<Array<{id: string, name: string}>>([]);
  const selectedTransferHostMap = shallowRef<Record<number, DirtyMachinesModel>>({});
  const selectedHosts = computed(() => Object.values(selectedTransferHostMap.value));

  const serachData = computed(() => [
    {
      name: 'IP',
      id: 'ip_list',
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
      name: t('单据类型'),
      id: 'ticket_types',
      multiple: true,
      children: ticketTypes.value,
    },
    {
      name: t('操作人'),
      id: 'operator',
    },
  ]);

  const tableColumn = [
    {
      type: 'selection',
      width: 48,
      label: '',
      fixed: 'left',
    },
    {
      label: 'IP',
      field: 'ip',
      fixed: true,
    },
    {
      label: t('管控区域'),
      field: 'bk_cloud_name',
    },
    {
      label: t('业务'),
      field: 'bk_biz_name',
    },
    {
      label: t('单据类型'),
      field: 'ticket_type_display',
    },
    {
      label: t('关联单据'),
      field: 'ticket_id',
      width: 170,
      render: ({ data }: {data: DirtyMachinesModel}) => (data.ticket_id
        ? <bk-button
            text
            theme="primary"
            onClick={() => handleGoTicketDetail(data)}>
            {data.ticket_id}
          </bk-button>
        : '--')
      ,
    },
    {
      label: t('关联任务'),
      field: 'task_id',
      render: ({ data }: {data: DirtyMachinesModel}) => (data.task_id
        ? <bk-button
            text
            theme="primary"
            onClick={() => handleGoTaskHistoryDetail(data)}>
            {data.task_id}
          </bk-button>
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
        <div>
          <bk-button theme="primary" text onClick={() => transferHosts([data])}>{t('移入待回收')}</bk-button>
        </div>
      ),
    },
  ];

  const serachValidateValues = (
    payload: Record<'id'|'name', string>,
    values: Array<Record<'id'|'name', string>>,
  ) => {
    if (payload.id === 'ip_list') {
      const [{ id }] = values;
      return Promise.resolve(_.every(id.split(','), item => ipv4.test(item)));
    }
    return Promise.resolve(true);
  };

  // 获取数据
  const fetchData = () => {
    const searchParams = getSearchSelectorParams(searchValues.value);
    tableRef.value.fetchData({
      ...searchParams,
    });
  };

  // 获取单据类型
  const fetchTicketTypes = () => getTicketTypes({
    is_apply: 1,
  }).then((res) => {
    ticketTypes.value = res.map(item => ({
      id: item.key,
      name: item.value,
    }));
    return ticketTypes.value;
  });

  // 搜索
  const handleSearch = () => {
    fetchData();
  };

  // 清空搜索条件
  const handleClearSearch = () => {
    searchValues.value = [];
    fetchData();
  };

  // 选择单台
  const handleSelect = (data: { checked: boolean, row: DirtyMachinesModel }) => {
    const selectedMap = { ...selectedTransferHostMap.value };
    if (data.checked) {
      selectedMap[data.row.bk_host_id] = data.row;
    } else {
      delete selectedMap[data.row.bk_host_id];
    }

    selectedTransferHostMap.value = selectedMap;
  };

  // 选择所有
  const handleSelectAll = (data:{checked: boolean}) => {
    let selectedMap = { ...selectedTransferHostMap.value };
    if (data.checked) {
      selectedMap = (tableRef.value.getData() as DirtyMachinesModel[]).reduce((result, item) => ({
        ...result,
        [item.bk_host_id]: item,
      }), {});
    } else {
      selectedMap = {};
    }
    selectedTransferHostMap.value = selectedMap;
  };

  const handleCopySelected = () => {
    copy(selectedHosts.value.map(item => item.ip).join(','));
  };

  const transferHosts = (data: DirtyMachinesModel[] = []) => {
    if (data.length === 0) return;

    useInfoWithIcon({
      width: 480,
      type: 'warnning',
      title: t('确认将以下主机转移至待回收模块'),
      content: () => (
        <div style="word-break: all;">
          {data.map(item => <p>{item.ip}</p>)}
        </div>
      ),
      onConfirm: () => transferDirtyMachines({
        bk_host_ids: data.map(item => item.bk_host_id),
      })
        .then(() => {
          messageSuccess(t('转移成功'));
          fetchData();
          selectedTransferHostMap.value = {};
          return true;
        })
        .catch(() => false),
    });
  };

  const handleGoTicketDetail = (data: DirtyMachinesModel) => {
    const { href } = router.resolve({
      name: 'SelfServiceMyTickets',
      query: {
        id: data.ticket_id,
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
    .header-action{
      display: flex;
    }
  }
</style>
