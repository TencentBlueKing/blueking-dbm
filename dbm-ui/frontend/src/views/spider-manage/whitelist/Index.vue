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
  <div class="whitelist">
    <BkAlert
      closable
      theme="warning"
      :title="t('如果希望使用通配符授权一批IP_或者授权平台公共类IP_未注册到配置平台的IP_需要先录入到白名单中_才能对其授权')" />
    <div class="whitelist-operations">
      <div class="whitelist-operations__left">
        <BkButton
          theme="primary"
          @click="handleCreate">
          {{ t('新建') }}
        </BkButton>
        <span
          v-bk-tooltips="{
            disabled: hasSelected,
            content: t('请选择白名单组')
          }"
          class="inline-block">
          <BkButton
            :disabled="!hasSelected"
            @click="handleBatchDelete">
            {{ t('批量删除') }}
          </BkButton>
        </span>
      </div>
      <BkInput
        v-model="keyword"
        clearable
        :placeholder="t('请输入IP')"
        style="width: 500px;"
        type="search"
        @clear="fetchTableData"
        @enter="fetchTableData" />
    </div>
    <DbTable
      ref="tableRef"
      :columns="columns"
      :data-source="getWhitelist"
      :is-row-select-enable="setRowSelectable"
      @clear-search="handleClearSearch"
      @select="handleTableSelect"
      @select-all="handleTableSelectAll" />
  </div>
  <WhitelistOperation
    v-model="isShow"
    :biz-id="bizId"
    :data="operationData"
    :is-edit="isEdit"
    :title="operationTitle"
    @successed="fetchTableData" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import type { WhitelistItem } from '@services/types/whitelist';
  import {
    batchDeleteWhitelist,
    getWhitelist,
  } from '@services/whitelist';

  import {
    useCopy,
    useInfoWithIcon,
  } from '@hooks';

  import { ClusterTypes } from '@common/const';

  import RenderRow from '@components/render-row/index.vue';

  import { messageSuccess } from '@utils';

  import WhitelistOperation from './components/WhitelistOperation.vue';

  import { useGlobalBizs } from '@/stores';
  import type { TableProps } from '@/types/bkui-vue';

  interface TableRenderData {
    data: WhitelistItem
  }

  const { currentBizId } = useGlobalBizs();
  const route = useRoute();
  const copy = useCopy();
  const { t } = useI18n();
  const tableRef = ref();

  const keyword = ref('');
  const selectedMap = shallowRef<Record<number, WhitelistItem>>({});
  const isPlatform = computed(() => route.matched[0]?.name === 'Platform');
  const bizId = computed(() => (isPlatform.value ? 0 : currentBizId));
  const hasSelected = computed(() => Object.keys(selectedMap.value).length > 0);
  const disabledFunc = (_: any, row: WhitelistItem) => !(row.is_global && !isPlatform.value);
  const columns: TableProps['columns'] = [
    {
      type: 'selection',
      width: 48,
      label: '',
      showOverflowTooltip: {
        mode: 'static',
        content: t('全局白名单如需编辑请联系平台管理员'),
        disabled: disabledFunc as unknown as boolean | undefined,
      },
    },
    {
      label: t('IP或IP%'),
      field: 'ips',
      showOverflowTooltip: false,
      render: ({ data }: TableRenderData) => {
        const isRenderTag = data.is_global && !isPlatform.value;
        return (
          <>
            <RenderRow
              style={`max-width: calc(100% - ${isRenderTag ? '80px' : '20px'});`}
              data={data.ips} />
            {
              isRenderTag
              ? <bk-tag class="ml-4">{ t('全局') }</bk-tag>
              : null
            }
            <db-icon
              v-bk-tooltips={ t('复制') }
              type="copy copy-btn"
              onClick={ () => copy(data.ips.join('\n'))} />
          </>
        );
      },
    },
    {
      label: t('备注'),
      field: 'remark',
      width: 180,
    },
    {
      label: t('更新人'),
      field: 'updater',
      width: 180,
    },
    {
      label: t('更新时间'),
      field: 'update_at',
      width: 160,
      sort: true,
    },
    {
      label: t('操作'),
      field: 'operations',
      width: 100,
      render: ({ data }: TableRenderData) => {
        const isDisabled = data.is_global && !isPlatform.value;
        const tips = {
          disabled: !isDisabled,
          content: t('全局白名单如需编辑请联系平台管理员'),
        };

        return (
          <>
            <span class="inlink-block" v-bk-tooltips={tips}>
              <bk-button
                class="mr-8"
                text
                theme="primary"
                disabled={isDisabled}
                onClick={ () => handleEdit(data) }>
                {t('编辑')}
              </bk-button>
            </span>
            <span class="inlink-block" v-bk-tooltips={tips}>
              <bk-button
                text
                theme="primary"
                disabled={isDisabled}
                onClick={ () => handleDelete([data.id])}>
                {t('删除')}
              </bk-button>
            </span>
          </>
        );
      },
    },
  ];

  onMounted(() => {
    fetchTableData();
  });

  const setRowSelectable = ({ row }: { row: WhitelistItem }) => !(row.is_global && !isPlatform.value);

  function fetchTableData() {
    selectedMap.value = {};
    tableRef.value.fetchData({
      ip: keyword.value,
      db_type: ClusterTypes.TENDBCLUSTER,
    }, {
      bk_biz_id: bizId.value,
    });
  }

  function handleClearSearch() {
    keyword.value = '';
    fetchTableData();
  }

  function handleTableSelect({ checked, row }: { row: WhitelistItem, checked: boolean }) {
    const cloneSelectMap = { ...selectedMap.value };
    if (checked) {
      cloneSelectMap[row.id] = row;
    } else {
      delete cloneSelectMap[row.id];
    }
    selectedMap.value = cloneSelectMap;
  }

  function handleTableSelectAll({ checked }: { checked: boolean }) {
    let cloneSelectMap = { ...selectedMap.value };
    if (checked) {
      cloneSelectMap = (tableRef.value.getData() as WhitelistItem[])
        .filter(item => (isPlatform.value ? true : !item.is_global))
        .reduce((result, item) => ({
          ...result,
          [item.id]: item,
        }), {});
    } else {
      cloneSelectMap = {};
    }
    selectedMap.value = cloneSelectMap;
  }

  const isShow = ref(false);
  const isEdit = ref(false);
  const operationTitle = ref('');
  const operationData = ref({} as WhitelistItem);

  function handleCreate() {
    isShow.value = true;
    isEdit.value = false;
    operationTitle.value = t('新建白名单');
  }

  function handleEdit(data: WhitelistItem) {
    isShow.value = true;
    operationTitle.value = t('编辑白名单');
    isEdit.value = true;
    operationData.value = data;
  }

  function handleBatchDelete() {
    const ids = Object.values(selectedMap.value).map(item => item.id);
    handleDelete(ids);
  }

  const { run: batchDeleteWhitelistRun } = useRequest(batchDeleteWhitelist, {
    manual: true,
  });

  function handleDelete(ids: number[]) {
    const isSingle = ids.length === 1;
    useInfoWithIcon({
      type: 'warnning',
      title: isSingle ? t('确认删除该组白名单') : t('确认删除该组白名单', [ids.length]),
      content: t('白名单删除后_不会影响现已授权实例_新增授权时将无法再选择_请谨慎操作'),
      onConfirm: () => {
        try {
          batchDeleteWhitelistRun({ ids });
          messageSuccess(t('删除成功'));
          fetchTableData();
          return true;
        } catch (_) {
          return false;
        }
      },
    });
  }
</script>

<style lang="less" scoped>

.whitelist-operations {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 0;
}

.whitelist-operations__left {
  display: flex;
  align-items: center;

  .bk-button {
    min-width: 88px;
    margin-right: 8px;
  }

}

:deep(.bk-table) {
  tr:hover {
    .copy-btn {
      display: inline-block;
    }
  }

  .copy-btn {
    display: none;
    margin-left: 8px;
    color: @primary-color;
    cursor: pointer;
  }
}
</style>
