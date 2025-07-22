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
  <BkTable
    :data="hosts"
    :merge-cells="mergeCells">
    <BkTableColumn
      field="ip"
      fixed="left"
      label="IP"
      :min-width="150">
      <template #header>
        <div class="ip-header">
          IP
          <DbIcon
            type="copy"
            @click="copyAllIp" />
        </div>
      </template>
    </BkTableColumn>
    <BkTableColumn
      field=""
      :label="t('所属业务')"
      :min-width="120">
      <template #default>
        {{
          ticketDetails.details.for_biz === 0
            ? t('公共资源池')
            : globalBizsStore.bizIdMap.get(ticketDetails.details.for_biz)?.name
        }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      field=""
      :label="t('所属 DB 类型')"
      :min-width="120">
      <template #default>
        {{ resourceTypeDisplay() }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      field=""
      :label="t('资源标签')"
      :min-width="120">
      <template #default>
        <TagBlock :data="ticketDetails.details.label_names" />
      </template>
    </BkTableColumn>
  </BkTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Common } from '@services/model/ticket/ticket';

  import { useGlobalBizs } from '@stores';

  import { DBTypeInfos, DBTypes, TicketTypes } from '@common/const';

  import TagBlock from '@components/tag-block/Index.vue';

  import { execCopy } from '@utils';

  interface Props {
    ticketDetails: TicketModel<Common.ImportResource>;
  }

  defineOptions({
    name: TicketTypes.RESOURCE_IMPORT,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();
  const globalBizsStore = useGlobalBizs();

  const { hosts } = props.ticketDetails.details;
  const rowspan = hosts.length;
  const mergeCells = Array.from({ length: 3 }, (_item, index) => ({ col: index + 1, colspan: 1, row: 0, rowspan }));

  const resourceTypeDisplay = () => {
    const { resource_type: resourceType } = props.ticketDetails.details;
    if (!resourceType || resourceType === 'PUBLIC') {
      return t('通用');
    }
    if (resourceType === 'vm') {
      return 'Vm';
    }
    return DBTypeInfos[resourceType as DBTypes]?.name;
  };

  const copyAllIp = () => {
    const ips = hosts.map((item) => item.ip);
    if (ips.length > 0) {
      execCopy(ips.join('\n'), t('复制成功，共n条', { n: ips.length }));
    }
  };
</script>
<style lang="less" scoped>
  .ip-header {
    &:hover {
      [class*='db-icon'] {
        display: inline !important;
      }
    }

    [class*='db-icon'] {
      display: none;
      margin-top: 1px;
      margin-left: 4px;
      color: @primary-color;
      cursor: pointer;
    }
  }
</style>
