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
  <BkSideslider
    v-model:is-show="isShow"
    quick-close
    render-directive="if"
    :width="960">
    <template #header>
      <div class="available-resource-preview-header">
        <I18nT
          keypath="预览可用资源(n台)"
          tag="p">
          <strong>{{ machineNum }}</strong>
        </I18nT>
        <div class="sub-title">
          <template v-if="params?.city">
            <div class="sub-title-label">{{ t('地域') }}:</div>
            <div class="sub-title-value">{{ params?.city || '--' }}</div>
          </template>
          <template v-if="params?.subzones">
            <div class="sub-title-label">{{ t('园区') }}:</div>
            <div class="sub-title-value">{{ params?.subzones || '--' }}</div>
          </template>
          <div class="sub-title-label">{{ t('规格') }}:</div>
          <div class="sub-title-value">{{ specInfo?.spec_name || '--' }}</div>
          <div class="sub-title-label">{{ t('资源标签') }}:</div>
          <div class="sub-title-value">
            <BkTag
              v-if="noLimitTag"
              theme="success">
              {{ t('通用无标签') }}
            </BkTag>
            <template v-else>
              <BkTag
                v-for="item in filterTagList.slice(0, MAX_TAG_NUM)"
                :key="item.id">
                {{ item.value }}
              </BkTag>
              <BkTag v-if="filterTagList.length > MAX_TAG_NUM"> +{{ filterTagList.slice(MAX_TAG_NUM).length }} </BkTag>
            </template>
          </div>
        </div>
      </div>
    </template>
    <div class="available-resource-preview">
      <BkAlert
        class="mb-20"
        closable
        :title="t('资源预览仅反映此刻资源的匹配状况，并不代表最终的匹配结果')" />
      <DbTable
        ref="table"
        :container-height="contentHeight"
        :data-source="dataSource"
        :filter-value="columnFilterValue"
        row-key="ip"
        @filter-change="handleFilterChange">
        <TableColumn
          col-key="ip"
          fixed="left"
          :min-width="150"
          title="IP" />
        <TableColumn
          col-key="bk_cloud_name"
          :min-width="120"
          :title="t('管控区域')" />
        <TableColumn
          col-key="agent_status"
          :min-width="120"
          :title="t('Agent 状态')">
          <template #default="{ row }: { row: DbResourceModel }">
            <HostAgentStatus :data="row.agent_status" />
          </template>
        </TableColumn>
        <TableColumn
          col-key="bk_cpu"
          :min-width="300"
          :title="t('资源归属')">
          <template #default="{ row }: { row: DbResourceModel }">
            <ResourceHostOwner :data="row" />
          </template>
        </TableColumn>
        <TableColumn
          col-key="city"
          :filter="filterOption['city']"
          :min-width="120"
          :title="t('地域')" />
        <TableColumn
          col-key="sub_zone"
          :filter="filterOption['suz_zone']"
          :min-width="120"
          :title="t('园区')" />
        <TableColumn
          col-key="rack_id"
          :min-width="120"
          :title="t('机架')" />
        <TableColumn
          col-key="os_name"
          :filter="filterOption['os_name']"
          :min-width="180"
          :title="t('操作系统名称')" />
        <TableColumn
          col-key="device_class"
          :filter="filterOption['device_class']"
          :min-width="120"
          :title="t('机型')" />
      </DbTable>
    </div>
  </BkSideslider>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import DbResourceModel from '@services/model/db-resource/DbResource';
  import { fetchList } from '@services/source/dbresourceResource';
  import { getResourceSpec } from '@services/source/dbresourceSpec';
  import { listTag } from '@services/source/tag';
  import type { HostInfo } from '@services/types';

  import DbTable from '@components/db-table/IndexNew.vue';
  import HostAgentStatus from '@components/host-agent-status/Index.vue';
  import ResourceHostOwner from '@components/resource-host-owner/Index.vue';

  import useSearchSelectData from './hooks/use-search-select-data';

  interface Props {
    bizId?: number;
    params: {
      bk_cloud_ids?: string;
      city?: string;
      for_biz?: number;
      for_bizs?: number[];
      hosts?: HostInfo[];
      label_names?: string;
      labels?: string;
      os_names?: string[];
      os_type?: string;
      resource_type?: string;
      resource_types?: string[];
      spec_id?: number;
      subzone_ids?: string;
      subzones?: string;
    };
  }

  const props = withDefaults(defineProps<Props>(), {
    bizId: window.PROJECT_CONFIG.BIZ_ID,
  });

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const contentHeight = window.innerHeight * 0.8;

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');
  const filterOption = useSearchSelectData();

  const columnFilterValue = ref<Record<string, string>>({});
  const machineNum = ref(0);
  const tagList = ref<ServiceReturnType<typeof listTag>['results']>([]);
  // 通用无标签
  const noLimitTag = ref(true);
  const MAX_TAG_NUM = 4;

  const filterTagList = computed(() => {
    const tagIds = (props.params.labels || '').split(',').map((id) => Number(id));
    return tagList.value.filter((item) => tagIds.includes(item.id));
  });

  const { data: specInfo, run: queryResourceSpec } = useRequest(getResourceSpec, {
    manual: true,
  });

  const { run: runListTag } = useRequest(listTag, {
    manual: true,
    onSuccess: (data) => {
      tagList.value = data.results || [];
    },
  });

  const dataSource = async (params: ServiceParameters<typeof fetchList>) => {
    // 过滤掉通用无标签选项
    const labels = (props.params.labels || '')
      ?.split(',')
      .filter((item) => item !== '0')
      .join(',');
    noLimitTag.value = !labels;
    const dataList = await fetchList({
      ...params,
      ...props.params,
      bk_biz_id: undefined, // 资源池参数用for_biz,把db-table内置的bk_biz_id去掉
      city: props.params.city || undefined,
      labels: labels || undefined, // 不传即为不限制（即通用无标签）
      spec_id: props.params.spec_id ? String(props.params.spec_id) : undefined,
      subzone_ids: props.params.subzone_ids || undefined,
      subzones: props.params.subzones || undefined,
    });

    machineNum.value = dataList.count;
    return dataList;
  };

  const fetchData = () => {
    tableRef.value!.fetchData(Object.assign({}, columnFilterValue.value));
  };

  const handleFilterChange = (filterValue: Record<string, string>) => {
    columnFilterValue.value = filterValue;
    fetchData();
  };

  watch(
    () => props.bizId,
    () => {
      runListTag({
        bk_biz_ids: [props.bizId, 0].join(','), // 0 表示公共资源池
        type: 'resource',
      });
    },
    {
      immediate: true,
    },
  );

  watch(isShow, () => {
    if (isShow.value) {
      setTimeout(() => {
        if (props.params.spec_id) {
          queryResourceSpec({
            spec_id: props.params.spec_id,
          });
        }
        fetchData();
      }, 100);
    }
  });
</script>
<style lang="less" scoped>
  .available-resource-preview-header {
    display: flex;
    align-items: center;

    .sub-title {
      position: relative;
      display: flex;
      height: 22px;
      padding-left: 9px;
      margin-left: 16px;
      font-family: MicrosoftYaHei, sans-serif;
      font-size: 14px;
      line-height: 22px;
      letter-spacing: 0;
      color: #979ba5;

      &::before {
        position: absolute;
        top: 4px;
        left: 0;
        width: 1px;
        height: 14px;
        background-color: #979ba580;
        content: '';
      }

      .sub-title-label {
        margin-right: 8px;
      }

      .sub-title-value {
        margin-right: 20px;
      }
    }
  }

  .available-resource-preview {
    margin: 18px 24px;
  }
</style>
