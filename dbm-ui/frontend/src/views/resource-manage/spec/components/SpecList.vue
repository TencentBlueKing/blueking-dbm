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
      <AuthButton
        action-id="spec_create"
        class="w-88 mr-8"
        :resource="databaseType"
        theme="primary"
        @click="handleShowCreate">
        {{ t('新建') }}
      </AuthButton>
      <span
        v-bk-tooltips="{
          content: t('请选择xx', [t('规格')]),
          disabled: hasSelected
        }">
        <BkButton
          class="w-88 mr-8"
          :disabled="!hasSelected"
          @click="handleBacthDelete">
          {{ t('删除') }}
        </BkButton>
      </span>
      <span
        v-bk-tooltips="{
          content: t('请选择xx', [t('规格')]),
          disabled: hasSelected
        }"
        class="delete-button">
        <BkButton
          class="w-88 mr-8"
          :disabled="!hasSelected"
          @click="handleBacthEnable">
          {{ t('启用') }}
        </BkButton>
      </span>
      <BkInput
        v-model="searchKey"
        clearable
        :placeholder="t('请输入xx', [t('规格名称')])"
        style="width: 500px;"
        type="search"
        @enter="fetchData()" />
    </div>
    <DbTable
      ref="tableRef"
      :columns="columns"
      :data-source="getResourceSpecList"
      :disable-select-method="disableSelectMethod"
      primary-key="spec_id"
      :row-class="setRowClass"
      selectable
      :settings="settings"
      @clear-search="handleClearSearch"
      @selection="handleSelectionChange"
      @setting-change="updateTableSettings" />
  </div>

  <BkSideslider
    v-model:is-show="specOperationState.isShow"
    :before-close="handleBeforeClose"
    :width="960">
    <template #header>
      <template v-if="specOperationState.type === 'edit'">
        <span>{{ t('编辑规格') }} 【{{ specOperationState.data?.spec_name }}】</span>
      </template>
      <template v-else-if="specOperationState.type === 'clone'">
        <span>{{ t('克隆规格') }} 【{{ specOperationState.data?.spec_name }}】</span>
      </template>
      <template v-else>
        {{ t('新增规格') }}
      </template>
      <BkTag
        class="ml-4"
        theme="info">
        {{ clusterTypeLabel }}
      </BkTag>
    </template>
    <SpecCreate
      :cluster-type="clusterType"
      :data="specOperationState.data"
      :has-instance="hasInstance"
      :is-edit="isSpecOperationEdit && !!specOperationState.data?.is_refer"
      :machine-type="machineType"
      :machine-type-label="machineTypeLabel"
      :mode="specOperationState.type"
      @cancel="handleCloseSpecOperation"
      @successed="handleSubmitSuccessed" />
  </BkSideslider>
</template>

<script setup lang="tsx">
  import type { Column } from 'bkui-vue/lib/table/props';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import type ResourceSpecModel from '@services/model/resource-spec/resourceSpec';
  import {
    batchDeleteResourceSpec,
    getResourceSpecList,
    updateResourceSpecEnableStatus,
  } from '@services/source/dbresourceSpec';

  import {
    useBeforeClose,
    useDebouncedRef,
    useInfoWithIcon,
    useTableSettings,
  } from '@hooks';

  import {
    ClusterTypes,
    UserPersonalSettings,
  } from '@common/const';

  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

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
  const searchKey = useDebouncedRef('');

  const disableSelectMethod = (row: ResourceSpecModel) => (row.is_refer ? t('该规格已被使用_无法删除') : false);
  const setRowClass = (data: ResourceSpecModel) => (data.isRecentSeconds ? 'is-new-row' : '');

  const databaseTypeMap: Record<string, string> = {
    tendbsingle: 'mysql',
    tendbha: 'mysql',
    TwemproxyRedisInstance: 'redis',
    TwemproxyTendisSSDInstance: 'redis',
    PredixyTendisplusCluster: 'redis',
    es: 'es',
    hdfs: 'hdfs',
    kafka: 'kafka',
    influxdb: 'influxdb',
    pulsar: 'pulsar',
    tendbcluster: 'tendbcluster',
  };

  const databaseType = databaseTypeMap[props.clusterType];
  const tableRef = ref();

  const specOperationState = reactive({
    isShow: false,
    type: 'create' as SpecOperationType,
    data: null as ResourceSpecModel | null,
  });

  const selectedList = ref<ResourceSpecModel[]>([]);
  const hasSelected = computed(() => selectedList.value.length > 0);
  const isSpecOperationEdit = computed(() => specOperationState.type === 'edit');
  const hasInstance = [`${ClusterTypes.ES}_es_datanode`].includes(`${props.clusterType}_${props.machineType}`);
  const columns = computed(() => {
    const baseColumns: Column[] = [
      {
        label: t('规格名称'),
        field: 'spec_name',
        width: 180,
        render: ({ data }: { data: ResourceSpecModel }) => (
          <TextOverflowLayout>
            {{
              default: () => (
                <auth-button
                  action-id="spec_update"
                  resource={databaseType}
                  permission={data.permission.spec_update}
                  text
                  theme="primary"
                  onClick={() => handleShowUpdate(data)}>
                  {data.spec_name}
                </auth-button>
              ),
              append: () => data.isRecentSeconds && (
                <span
                  class="glob-new-tag ml-4"
                  data-text="NEW" />
              ),
            }}
          </TextOverflowLayout>
        ),
      },
      {
        label: () => props.machineTypeLabel,
        field: 'model',
        showOverflowTooltip: false,
        minWidth: 400,
        render: ({ data }: { data: ResourceSpecModel }) => (
          <bk-popover
            theme="light"
            placement="top"
            popover-delay={[300, 0]}
            disable-outside-click>
            {{
              default: () => (
                <div class="machine-info text-overflow">
                  <bk-tag class="machine-info-cpu">
                    CPU = {`${data.cpu.min} ~ ${data.cpu.max}`} {t('核')}
                  </bk-tag>
                  <bk-tag class="machine-info-condition" theme="info">
                    AND
                  </bk-tag>
                  <bk-tag class="machine-info-mem">
                    {t('内存')} = {`${data.mem.min} ~ ${data.mem.max}`} G
                  </bk-tag>
                  <bk-tag class="machine-info-condition" theme="info">
                    AND
                  </bk-tag>
                  <bk-tag class="machine-info-device">
                    {t('机型')} = {data.device_class.join(',') || t('无限制')}
                  </bk-tag>
                  <bk-tag class="machine-info-condition" theme="info">
                    AND
                </bk-tag>
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
                            <bk-tag>
                              {`(${t('挂载点')}: ${item.mount_point}, ${t('最小容量')}: ${item.size} G, ${item.type})`}
                            </bk-tag>
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
        label: t('是否启用'),
        field: 'enable',
        render: ({ data }: { data: ResourceSpecModel }) => (
          <bk-pop-confirm
            title={data.enable ? t('确认停用该规格？') : t('确认启用该规格？')}
            content={data.enable ? t('停用后，在资源规格选择时，将不可见，且不可使用') : t('启用后，在资源规格选择时，将开放选择')}
            width="308"
            trigger="click"
            placement="bottom"
            confirm-text={data.enable ? t('停用') : t('启用')}
            onConfirm={() => handleConfirmSwitch(data)}
          >
            <auth-switcher
              size="small"
              action-id="spec_update"
              permission={data.permission.spec_update}
              resource={databaseType}
              model-value={data.enable}
              theme="primary"
            />
          </bk-pop-confirm>
        ),
      },
      {
        label: t('更新时间'),
        field: 'update_at',
        sort: true,
        width: 180,
        render: ({ data }: { data: ResourceSpecModel }) => <span>{data.updateAtDisplay}</span>,
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
        fixed: 'right',
        render: ({ data }: { data: ResourceSpecModel }) => (
          <>
            <auth-button
              action-id="spec_update"
              resource={databaseType}
              permission={data.permission.spec_update}
              class="mr-8"
              theme="primary"
              text
              onClick={handleShowUpdate.bind(null, data)}>
              {t('编辑')}
            </auth-button>
            <auth-button
              action-id="spec_create"
              resource={databaseType}
              permission={data.permission.spec_create}
              class="mr-8"
              theme="primary"
              text
              onClick={handleShowClone.bind(null, data)}>
              {t('克隆')}
            </auth-button>
            {data.is_refer ? (
              <span class="inline-block;" v-bk-tooltips={t('该规格已被使用_无法删除')}>
                <auth-button
                  action-id="spec_delete"
                  resource={databaseType}
                  permission={data.permission.spec_delete}
                  theme="primary"
                  text
                  disabled>
                  {t('删除')}
                </auth-button>
              </span>
            ) : (
              <auth-button
                action-id="spec_delete"
                resource={databaseType}
                permission={data.permission.spec_delete}
                theme="primary"
                text
                onClick={() => handleDelete([data])}>
                {t('删除')}
              </auth-button>
            )}
          </>
        ),
      },
    ];
    if (hasInstance) {
      baseColumns.splice(3, 0, {
        label: t('每台主机实例数量'),
        field: 'instance_num',
        width: 140,
      });
    }
    return baseColumns;
  });

  // 设置用户个人表头信息
  const defaultSettings = {
    fields: columns.value.filter(item => item.field).map(item => ({
      label: item.label as string,
      field: item.field as string,
      disabled: ['spec_name', 'model'].includes(item.field as string),
    })),
    checked: columns.value.map(item => item.field).filter(key => !!key) as string[],
  };

  const {
    settings,
    updateTableSettings,
  } = useTableSettings(UserPersonalSettings.SPECIFICATION_TABLE_SETTINGS, defaultSettings);

  const { run: runUpdateResourceSpec } = useRequest(updateResourceSpecEnableStatus, {
    manual: true,
    onSuccess: () => {
      messageSuccess(t('操作成功'));
      fetchData();
    },
  });

  watch(() => [
    props.clusterType,
    props.machineType,
    searchKey,
  ], () => {
    fetchData();
  });


  const handleConfirmSwitch = (row: ResourceSpecModel) => {
    runUpdateResourceSpec({
      spec_ids: [row.spec_id],
      enable: !row.enable,
    });
  };

  const fetchData = () => {
    tableRef.value.fetchData({
      spec_name: searchKey.value,
    }, {
      spec_cluster_type: props.clusterType,
      spec_machine_type: props.machineType,
    });
  };

  const handleSelectionChange = (idList: number[], list: ResourceSpecModel[]) => {
    selectedList.value = list;
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
    handleDelete(selectedList.value);
  };

  const handleBacthEnable = () => {
    runUpdateResourceSpec({
      spec_ids: selectedList.value.map(item => item.spec_id),
      enable: true,
    });
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
            spec_ids: selectedList.value.map(item => item.spec_id),
          });
          messageSuccess(t('删除成功'));
          fetchData();
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

      .delete-button {
        margin-right: auto;
      }
    }

    :deep(.machine-info) {
      .bk-tag {
        &:hover {
          background-color: #f0f1f5;
        }

        &.bk-tag-info {
          background-color: #edf4ff;
        }
      }

      &:hover {
        background-color: #f0f1f5;
      }
    }
  }
</style>

<style lange="less">
.resource-machine-info-tips {
  min-width: 280px;
  padding: 9px 0 0;
  color: #63656e;

  .resource-machine-info__values {
    margin: 6px 0;
  }
}
</style>
