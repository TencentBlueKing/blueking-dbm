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
          <div class="sub-title-label">{{ t('地域') }}:</div>
          <div class="sub-title-value">{{ params?.city || '--' }}</div>
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
        :height="contentHeight"
        @column-filter="handleFilter">
        <BkTableColumn
          field="ip"
          fixed="left"
          label="IP"
          :min-width="150" />
        <BkTableColumn
          field="bk_cloud_name"
          :label="t('管控区域')"
          :min-width="120" />
        <BkTableColumn
          field="agent_status"
          :label="t('Agent 状态')"
          :min-width="120">
          <template #default="{ data }">
            <HostAgentStatus :data="data.agent_status" />
          </template>
        </BkTableColumn>
        <BkTableColumn
          field="bk_cpu"
          :label="t('资源归属')"
          :min-width="300">
          <template #default="{ data }">
            <ResourceHostOwner :data="data" />
          </template>
        </BkTableColumn>
        <BkTableColumn
          field="city"
          :filter="filterOption.city"
          :label="t('地域')"
          :min-width="120" />
        <BkTableColumn
          field="sub_zone"
          :filter="filterOption.sub_zone"
          :label="t('园区')"
          :min-width="120" />
        <BkTableColumn
          field="rack_id"
          :label="t('机架')"
          :min-width="120" />
        <BkTableColumn
          field="os_name"
          :filter="filterOption.os_name"
          :label="t('操作系统名称')"
          :min-width="180" />
        <BkTableColumn
          field="device_class"
          :filter="filterOption.device_class"
          :label="t('机型')"
          :min-width="120" />
      </DbTable>
    </div>
  </BkSideslider>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { fetchList } from '@services/source/dbresourceResource';
  import { getResourceSpec } from '@services/source/dbresourceSpec';
  import { listTag } from '@services/source/tag';
  import type { HostInfo } from '@services/types';

  import HostAgentStatus from '@components/host-agent-status/Index.vue';
  import ResourceHostOwner from '@components/resource-host-owner/Index.vue';
  import useSearchSelectData from '@components/resource-host-selector/hooks/use-search-select-data';

  interface Props {
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

  const props = defineProps<Props>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const contentHeight = window.innerHeight * 0.8;

  const { t } = useI18n();
  const dbTableRef = useTemplateRef('table');
  const { columnFilterValue, filterOption, handleFilter } = useSearchSelectData(props);

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

  useRequest(listTag, {
    defaultParams: [
      {
        bk_biz_ids: [window.PROJECT_CONFIG.BIZ_ID, 0].join(','), // 0 表示公共资源池
        type: 'resource',
      },
    ],
    onSuccess: (data) => {
      tagList.value = data.results || [];
    },
  });

  const dataSource = (params: ServiceParameters<typeof fetchList>) => {
    // 过滤掉通用无标签选项
    const labels = (props.params.labels || '')
      ?.split(',')
      .filter((item) => item !== '0')
      .join(',');
    noLimitTag.value = !labels;
    return fetchList({
      ...params,
      ...props.params,
      bk_biz_id: undefined, // 资源池参数用for_biz,把db-table内置的bk_biz_id去掉
      city: props.params.city || undefined,
      labels: labels || undefined, // 不传即为不限制（即通用无标签）
      spec_id: props.params.spec_id || undefined,
      subzones: props.params.subzones || undefined,
    });
  };

  watch(columnFilterValue, () => {
    dbTableRef.value?.fetchData({
      ...columnFilterValue,
    });
  });

  watch(isShow, () => {
    if (isShow.value) {
      setTimeout(() => {
        if (props.params.spec_id) {
          queryResourceSpec({
            spec_id: props.params.spec_id,
          });
        }
        dbTableRef.value?.getAllData().then((res: unknown[]) => {
          machineNum.value = res.length;
        });
        dbTableRef.value?.fetchData();
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
