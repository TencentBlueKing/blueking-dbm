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
        :resource="dbType"
        theme="primary"
        @click="handleShowCreate">
        {{ t('新建') }}
      </AuthButton>
      <span
        v-bk-tooltips="{
          content: t('请选择xx', [t('规格')]),
          disabled: hasSelected,
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
          disabled: hasSelected,
        }"
        class="delete-button">
        <BkButton
          class="w-88 mr-8"
          :disabled="!hasSelected"
          @click="handleBacthEnable">
          {{ t('启用') }}
        </BkButton>
      </span>
      <div class="enable-checkbox">
        <BkCheckbox
          v-model="isEnableSpec"
          class="mr-6"
          @change="fetchData" />
        {{ t('仅显示已启用的规格') }}
      </div>
      <BkInput
        v-model="searchKey"
        clearable
        :placeholder="t('请输入xx', [t('规格名称')])"
        style="width: 500px"
        type="search"
        @enter="fetchData" />
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
    render-directive="if"
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
        {{ dbTypeLabel }}
      </BkTag>
    </template>
    <SpecCreate
      :key="specOperationState.data?.spec_id"
      :data="specOperationState.data"
      :db-type="dbType"
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
  import { InfoBox } from 'bkui-vue';
  import type { Column } from 'bkui-vue/lib/table/props';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import type ResourceSpecModel from '@services/model/resource-spec/resourceSpec';
  import {
    batchDeleteResourceSpec,
    getResourceSpecList,
    updateResourceSpecEnableStatus,
  } from '@services/source/dbresourceSpec';

  import { useBeforeClose, useDebouncedRef, useTableSettings } from '@hooks';

  import { DBTypes, UserPersonalSettings } from '@common/const';

  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { messageSuccess } from '@utils';

  import { useHasQPS } from '../hooks/useHasQPS';

  import SpecCreate from './SpecCreate.vue';

  type SpecOperationType = 'create' | 'edit' | 'clone';

  interface Props {
    dbType: DBTypes;
    dbTypeLabel: string;
    machineType: string;
    machineTypeLabel: string;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const { hasQPS } = useHasQPS(props);
  const handleBeforeClose = useBeforeClose();
  const searchKey = useDebouncedRef('');

  const disableSelectMethod = (row: ResourceSpecModel) => (row.is_refer ? t('该规格已被使用_无法删除') : false);
  const setRowClass = (data: ResourceSpecModel) => (data.isRecentSeconds ? 'is-new-row' : '');

  const tableRef = ref();
  const isEnableSpec = ref(true);

  const specOperationState = reactive({
    data: null as ResourceSpecModel | null,
    isShow: false,
    type: 'create' as SpecOperationType,
  });

  const selectedList = ref<ResourceSpecModel[]>([]);
  const hasSelected = computed(() => selectedList.value.length > 0);
  const isSpecOperationEdit = computed(() => specOperationState.type === 'edit');
  const hasInstance = computed(() => [`${DBTypes.ES}_es_datanode`].includes(`${props.dbType}_${props.machineType}`));
  const columns = computed(() => {
    const baseColumns: Column[] = [
      {
        field: 'spec_name',
        label: t('规格名称'),
        render: ({ data }: { data: ResourceSpecModel }) => (
          <TextOverflowLayout>
            {{
              append: () =>
                data.isRecentSeconds && (
                  <span
                    class='glob-new-tag ml-4'
                    data-text='NEW'
                  />
                ),
              default: () => (
                <auth-button
                  action-id='spec_update'
                  permission={data.permission.spec_update}
                  resource={props.dbType}
                  theme='primary'
                  text
                  onClick={() => handleShowUpdate(data)}>
                  {data.spec_name}
                </auth-button>
              ),
            }}
          </TextOverflowLayout>
        ),
        width: 180,
      },
      {
        field: 'model',
        label: () => props.machineTypeLabel,
        minWidth: 400,
        render: ({ data }: { data: ResourceSpecModel }) => (
          <bk-popover
            placement='top'
            popover-delay={[300, 0]}
            theme='light'
            disable-outside-click>
            {{
              content: () => (
                <div class='resource-machine-info-tips'>
                  {data.cpu.min > 0 && data.device_class.length === 0 && (
                    <>
                      <strong>CPU: </strong>
                      <div class='resource-machine-info__values mb-10'>
                        <bk-tag>
                          {`${data.cpu.min} ~ ${data.cpu.max}`} {t('核')}
                        </bk-tag>
                      </div>
                      <strong>{t('内存')}: </strong>
                      <div class='resource-machine-info__values mb-10'>
                        <bk-tag>{`${data.mem.min} ~ ${data.mem.max}`} G</bk-tag>
                      </div>
                    </>
                  )}
                  {data.device_class.length > 0 && (
                    <>
                      <strong>{t('机型')}: </strong>
                      <div class='resource-machine-info__values mb-10'>
                        {data.device_class.map((item) => (
                          <bk-tag>{item}</bk-tag>
                        ))}
                      </div>
                    </>
                  )}
                  <strong>{t('磁盘')}: </strong>
                  <div class='resource-machine-info__values'>
                    {data.storage_spec.length > 0
                      ? data.storage_spec.map((item) => (
                          <p>
                            <bk-tag>
                              {`(${t('挂载点')}: ${item.mount_point}, ${t('最小容量')}: ${item.size} G, ${item.type})`}
                            </bk-tag>
                          </p>
                        ))
                      : '--'}
                  </div>
                </div>
              ),
              default: () => (
                <div class='machine-info text-overflow'>
                  {data.cpu.min > 0 && data.device_class.length === 0 && (
                    <>
                      <bk-tag class='machine-info-cpu'>
                        CPU = {`${data.cpu.min} ~ ${data.cpu.max}`} {t('核')}
                      </bk-tag>
                      <bk-tag
                        class='machine-info-condition'
                        theme='info'>
                        AND
                      </bk-tag>
                      <bk-tag class='machine-info-mem'>
                        {t('内存')} = {`${data.mem.min} ~ ${data.mem.max}`} G
                      </bk-tag>
                      <bk-tag
                        class='machine-info-condition'
                        theme='info'>
                        AND
                      </bk-tag>
                    </>
                  )}
                  {data.device_class.length > 0 && (
                    <>
                      <bk-tag class='machine-info-device'>
                        {t('机型')} = {data.device_class.join(',')}
                      </bk-tag>
                      <bk-tag
                        class='machine-info-condition'
                        theme='info'>
                        AND
                      </bk-tag>
                    </>
                  )}
                  <bk-tag class='machine-info-storage'>
                    {t('磁盘')} ={' '}
                    {data.storage_spec.length > 0
                      ? data.storage_spec.map(
                          (item) =>
                            `(${t('挂载点')}: ${item.mount_point}, ${t('最小容量')}: ${item.size} G, ${item.type})`,
                        )
                      : '--'}
                  </bk-tag>
                </div>
              ),
            }}
          </bk-popover>
        ),
        showOverflowTooltip: false,
      },
      {
        field: 'desc',
        label: t('描述'),
      },
      {
        field: 'enable',
        label: t('是否启用'),
        render: ({ data }: { data: ResourceSpecModel }) => (
          <bk-pop-confirm
            content={
              data.enable
                ? t('停用后，在资源规格选择时，将不可见，且不可使用')
                : t('启用后，在资源规格选择时，将开放选择')
            }
            confirm-text={data.enable ? t('停用') : t('启用')}
            placement='bottom'
            title={data.enable ? t('确认停用该规格？') : t('确认启用该规格？')}
            trigger='click'
            width='308'
            onConfirm={() => handleConfirmSwitch(data)}>
            <auth-switcher
              action-id='spec_update'
              model-value={data.enable}
              permission={data.permission.spec_update}
              resource={props.dbType}
              size='small'
              theme='primary'
            />
          </bk-pop-confirm>
        ),
        width: 120,
      },
      {
        field: 'update_at',
        label: t('更新时间'),
        render: ({ data }: { data: ResourceSpecModel }) => data.updateAtDisplay,
        sort: true,
        width: 250,
      },
      {
        field: 'updater',
        label: t('更新人'),
        render: ({ data }: { data: ResourceSpecModel }) => data.updater || '--',
        width: 120,
      },
      {
        field: '',
        fixed: 'right',
        label: t('操作'),
        render: ({ data }: { data: ResourceSpecModel }) => (
          <>
            <auth-button
              action-id='spec_update'
              class='mr-8'
              permission={data.permission.spec_update}
              resource={props.dbType}
              theme='primary'
              text
              onClick={handleShowUpdate.bind(null, data)}>
              {t('编辑')}
            </auth-button>
            <auth-button
              action-id='spec_create'
              class='mr-8'
              permission={data.permission.spec_create}
              resource={props.dbType}
              theme='primary'
              text
              onClick={handleShowClone.bind(null, data)}>
              {t('克隆')}
            </auth-button>
            {data.is_refer ? (
              <span
                v-bk-tooltips={t('该规格已被使用_无法删除')}
                class='inline-block;'>
                <auth-button
                  action-id='spec_delete'
                  permission={data.permission.spec_delete}
                  resource={props.dbType}
                  theme='primary'
                  disabled
                  text>
                  {t('删除')}
                </auth-button>
              </span>
            ) : (
              <auth-button
                action-id='spec_delete'
                permission={data.permission.spec_delete}
                resource={props.dbType}
                theme='primary'
                text
                onClick={() => handleDelete([data], false)}>
                {t('删除')}
              </auth-button>
            )}
          </>
        ),
        width: 180,
      },
    ];
    if (hasInstance.value) {
      baseColumns.splice(3, 0, {
        field: 'instance_num',
        label: t('每台主机实例数量'),
        width: 140,
      });
    }
    if (hasQPS.value) {
      baseColumns.splice(3, 0, {
        field: 'qpsText',
        label: t('单机QPS'),
        width: 140,
      });
    }
    return baseColumns;
  });

  // 设置用户个人表头信息
  const defaultSettings = {
    checked: columns.value.map((item) => item.field).filter((key) => !!key) as string[],
    fields: columns.value
      .filter((item) => item.field)
      .map((item) => ({
        disabled: ['model', 'spec_name'].includes(item.field as string),
        field: item.field as string,
        label: item.label as string,
      })),
    trigger: 'manual' as const,
  };

  const { settings, updateTableSettings } = useTableSettings(
    UserPersonalSettings.SPECIFICATION_TABLE_SETTINGS,
    defaultSettings,
  );

  const { run: runUpdateResourceSpec } = useRequest(updateResourceSpecEnableStatus, {
    manual: true,
    onSuccess: () => {
      messageSuccess(t('操作成功'));
      fetchData();
    },
  });

  watch(
    () => [props.dbType, props.machineType, searchKey.value],
    () => {
      tableRef.value!.clearSelected();
      fetchData();
    },
  );

  const handleConfirmSwitch = (row: ResourceSpecModel) => {
    runUpdateResourceSpec({
      enable: !row.enable,
      spec_ids: [row.spec_id],
    });
  };

  const fetchData = () => {
    const params = {
      spec_cluster_type: props.dbType,
      spec_machine_type: props.machineType,
    };
    if (isEnableSpec.value) {
      Object.assign(params, { enable: isEnableSpec.value });
    }
    tableRef.value.fetchData(
      {
        spec_name: searchKey.value,
      },
      params,
    );
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
      enable: true,
      spec_ids: selectedList.value.map((item) => item.spec_id),
    });
  };

  const handleDelete = (list: ResourceSpecModel[], isBatch = true) => {
    InfoBox({
      content: () => (
        <>
          {list.map((item) => (
            <p>{item.spec_name}</p>
          ))}
        </>
      ),
      onConfirm: async () => {
        try {
          await batchDeleteResourceSpec({
            spec_ids: isBatch ? selectedList.value.map((item) => item.spec_id) : list.map((item) => item.spec_id),
          });
          messageSuccess(t('删除成功'));
          fetchData();
          return true;
        } catch {
          return false;
        }
      },
      title: t('确认删除以下规格'),
      type: 'warning',
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

      .enable-checkbox {
        display: flex;
        margin-right: 16px;
        font-size: 12px;
        color: #4d4f56;
        align-items: center;
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
