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
  <div class="resource-spce-list">
    <div class="resource-spce-operations">
      <div>
        <BkButton
          class="w88 mr-8"
          theme="primary"
          @click="handleShowCreate">
          {{ $t('新建') }}
        </BkButton>
        <span
          v-bk-tooltips="{
            content: $t('请选择xx', [$t('规格')]),
            disabled: hasSelected
          }"
          class="inline-block">
          <BkButton
            class="w88 mr-8"
            :disabled="!hasSelected"
            @click="handleBacthDelete">
            {{ $t('删除') }}
          </BkButton>
        </span>
      </div>
      <BkInput
        v-model="searchKey"
        clearable
        :placeholder="$t('请输入xx', [$t('规格名称')])"
        style="width: 500px;"
        type="search"
        @enter="fetchData()" />
    </div>
    <DbTable
      ref="tableRef"
      :columns="columns"
      :data-source="getResourceSpecList"
      :settings="settings"
      @clear-search="handleClearSearch"
      @select="handleSelect"
      @select-all="handleSelectAll"
      @setting-change="updateTableSettings" />
  </div>

  <BkSideslider
    v-model:is-show="specOperationState.isShow"
    :before-close="handleBeforeClose"
    :width="960">
    <template #header>
      <template v-if="specOperationState.type === 'edit'">
        <span>{{ $t('编辑规格') }} 【{{ specOperationState.data?.spec_name }}】</span>
      </template>
      <template v-else-if="specOperationState.type === 'clone'">
        <span>{{ $t('克隆规格') }} 【{{ specOperationState.data?.spec_name }}】</span>
      </template>
      <template v-else>
        {{ $t('新增规格') }}
      </template>
      <BkTag theme="info">
        {{ clusterTypeLabel }}
      </BkTag>
    </template>
    <SpecCreate
      :cluster-type="clusterType"
      :data="specOperationState.data"
      :has-instance="hasInstance"
      :is-edit="isSpecOperationEdit"
      :machine-type="machineType"
      @cancel="handleCloseSpecOperation"
      @successed="handleSubmitSuccessed" />
  </BkSideslider>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import type ResourceSpecModel from '@services/model/resource-spec/resourceSpec';
  import { batchDeleteResourceSpec, getResourceSpecList } from '@services/resourceSpec';

  import { useBeforeClose, useDebouncedRef, useInfoWithIcon, useTableSettings } from '@hooks';

  import { ClusterTypes, UserPersonalSettings } from '@common/const';

  import { messageSuccess } from '@utils';

  import SpecCreate from './SpecCreate.vue';

  type SpecOperationType = 'create' | 'edit' | 'clone'

  interface Props {
    clusterType: string,
    clusterTypeLabel: string,
    machineType: string,
    machineTypeLabel: string,
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const handleBeforeClose = useBeforeClose();

  const tableRef = ref();
  const searchKey = useDebouncedRef('');
  const specOperationState = reactive({
    isShow: false,
    type: 'create' as SpecOperationType,
    data: null as ResourceSpecModel | null,
  });
  const batchSelected = shallowRef<Record<number, ResourceSpecModel>>({});
  const hasSelected = computed(() => Object.values(batchSelected.value).length > 0);
  const isSpecOperationEdit = computed(() => specOperationState.type === 'edit');
  const hasInstanceSpecs = [`${ClusterTypes.ES}_es_datanode`];
  const hasInstance = computed(() => hasInstanceSpecs.includes(`${props.clusterType}_${props.machineType}`));
  const columns = computed(() => {
    const baseColumns = [
      {
        type: 'selection',
        width: 48,
        label: '',
        fixed: 'left',
      },
      {
        label: t('规格名称'),
        field: 'spec_name',
        width: 180,
        render: ({ data }: { data: ResourceSpecModel }) => <a href="javascript:" onClick={handleShowUpdate.bind(null, data)}>{data.spec_name}</a>,
      },
      {
        label: () => props.machineTypeLabel,
        field: 'model',
        showOverflowTooltip: false,
        render: ({ data }: { data: ResourceSpecModel }) => (
        <bk-popover theme="light" popover-delay={[300, 0]}>
          {{
            default: () => (
              <div class="machine-info text-overflow">
                <bk-tag class="machine-info-cpu">CPU = {`${data.cpu.min} ~ ${data.cpu.max}`} {t('核')}</bk-tag>
                <bk-tag class="machine-info-condition" theme="info">AND</bk-tag>
                <bk-tag class="machine-info-mem">{t('内存')} = {`${data.mem.min} ~ ${data.mem.max}`} G</bk-tag>
                <bk-tag class="machine-info-condition" theme="info">AND</bk-tag>
                <bk-tag class="machine-info-device">{t('机型')} = {data.device_class.join(',') || t('无限制')}</bk-tag>
                <bk-tag class="machine-info-condition" theme="info">AND</bk-tag>
                <bk-tag class="machine-info-storage">
                  {t('磁盘')} = {
                    data.storage_spec.length > 0
                      ? data.storage_spec.map(item => `(${t('挂载点')}: ${item.mount_point}, ${t('最小容量')}: ${item.size} G, ${item.type})`)
                      : '--'
                  }
                </bk-tag>
              </div>
            ),
            content: () => (
              <div class="resource-machine-info-tips">
                <strong>CPU: </strong>
                <div class="resource-machine-info__values mb-10">
                  <bk-tag>{`${data.cpu.min} ~ ${data.cpu.max}`} {t('核')}</bk-tag>
                </div>
                <strong>{t('内存')}: </strong>
                <div class="resource-machine-info__values mb-10">
                  <bk-tag>{`${data.mem.min} ~ ${data.mem.max}`} G</bk-tag>
                </div>
                <strong>{t('机型')}: </strong>
                <div class="resource-machine-info__values mb-10">
                  {
                    data.device_class.length
                      ? data.device_class.map(item => <bk-tag>{item}</bk-tag>)
                      : <bk-tag>{t('无限制')}</bk-tag>
                  }
                </div>
                <strong>{t('磁盘')}: </strong>
                <div class="resource-machine-info__values">
                  {
                    data.storage_spec.length > 0
                      ? data.storage_spec.map(item => (
                        <p>
                          <bk-tag>{`(${t('挂载点')}: ${item.mount_point}, ${t('最小容量')}: ${item.size} G, ${item.type})`}</bk-tag>
                        </p>
                      ))
                      : '--'
                  }
                </div>
              </div>
            ),
          }}
        </bk-popover>
      ),
      },
      {
        label: t('描述'),
        field: 'desc',
      },
      {
        label: t('更新时间'),
        field: 'update_at',
        sort: true,
        width: 180,
      },
      {
        label: t('更新人'),
        field: 'updater',
        width: 120,
      },
      {
        label: t('操作'),
        field: '',
        width: 180,
        render: ({ data }: { data: ResourceSpecModel }) => (
          <>
            <bk-button class="mr-8" theme="primary" text onClick={handleShowUpdate.bind(null, data)}>{t('编辑')}</bk-button>
            <bk-button class="mr-8" theme="primary" text onClick={handleShowClone.bind(null, data)}>{t('克隆')}</bk-button>
            <bk-button theme="primary" text onClick={handleDelete.bind(null, [data])}>{t('删除')}</bk-button>
          </>
        ),
      },
    ];
    if (hasInstance.value) {
      baseColumns.splice(3, 0, {
        label: t('每台主机实例数量'),
        field: 'instance_num',
        width: 140,
      });
    }
    return baseColumns;
  });

  // 设置用户个人表头信息
  const disabledFields = ['spec_name', 'model'];
  const defaultSettings = {
    fields: columns.value.filter(item => item.field).map(item => ({
      label: item.label as string,
      field: item.field as string,
      disabled: disabledFields.includes(item.field as string),
    })),
    checked: columns.value.map(item => item.field).filter(key => !!key) as string[],
  };
  const {
    settings,
    updateTableSettings,
  } = useTableSettings(UserPersonalSettings.SPECIFICATION_TABLE_SETTINGS, defaultSettings);

  const fetchData = () => {
    tableRef.value.fetchData({
      spec_name: searchKey.value,
    }, {
      spec_cluster_type: props.clusterType,
      spec_machine_type: props.machineType,
    });
  };

  watch(() => [props.clusterType, props.machineType], () => {
    fetchData();
  });

  watch(searchKey, () => {
    fetchData();
  });

  // 选择单台
  const handleSelect = (data: { checked: boolean, row: ResourceSpecModel }) => {
    const selectedMap = { ...batchSelected.value };
    if (data.checked) {
      selectedMap[data.row.spec_id] = data.row;
    } else {
      delete selectedMap[data.row.spec_id];
    }

    batchSelected.value = selectedMap;
  };

  // 选择所有
  const handleSelectAll = (data:{checked: boolean}) => {
    let selectedMap = { ...batchSelected.value };
    if (data.checked) {
      selectedMap = (tableRef.value.getData() as ResourceSpecModel[]).reduce((result, item) => ({
        ...result,
        [item.spec_id]: item,
      }), {});
    } else {
      selectedMap = {};
    }
    batchSelected.value = selectedMap;
  };

  const handleShowCreate = () => {
    specOperationState.isShow = true;
    specOperationState.type = 'create';
    specOperationState.data = null;
  };

  const handleShowUpdate = (data: ResourceSpecModel) => {
    specOperationState.isShow = true;
    specOperationState.type = 'edit';
    specOperationState.data = data;
  };

  const handleShowClone = (data: ResourceSpecModel) => {
    specOperationState.isShow = true;
    specOperationState.type = 'clone';
    specOperationState.data = data;
  };

  const handleSubmitSuccessed = () => {
    specOperationState.isShow = false;
    fetchData();
  };

  const handleCloseSpecOperation = async () => {
    const allowClose = await handleBeforeClose();
    if (allowClose) {
      specOperationState.isShow = false;
    }
  };

  const handleClearSearch = () => {
    searchKey.value = '';
  };

  const handleBacthDelete = () => {
    const list = Object.values(batchSelected.value);
    handleDelete(list);
  };

  const handleDelete = (list: ResourceSpecModel[]) => {
    useInfoWithIcon({
      type: 'warnning',
      title: t('确认删除以下规格'),
      content: () => (
        <>
          {list.map(item => <p>{item.spec_name}</p>)}
        </>
      ),
      onConfirm: async () => {
        try {
          await batchDeleteResourceSpec({
            spec_ids: list.map(item => item.spec_id),
          });
          messageSuccess(t('删除成功'));
          fetchData();
          batchSelected.value = {};
          return true;
        } catch (_) {
          return false;
        }
      },
    });
  };
</script>

<style lang="less" scoped>
  .resource-spce-list {
    padding: 16px 24px 0;
    background-color: white;

    .resource-spce-operations {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding-bottom: 16px;
    }
  }
</style>

<style lange="less">
.resource-machine-info-tips {
  min-width: 280px;
  padding: 9px 0 0;

  .resource-machine-info__values {
    margin: 6px 0;
  }
}
</style>
