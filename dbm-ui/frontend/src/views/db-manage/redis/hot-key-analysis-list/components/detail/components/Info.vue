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
  <DbCard
    mode="collapse"
    :title="info.instace">
    <BkTable :data="info.infos">
      <BkTableColumn
        field="cmd_info"
        :label="t('执行命令')"
        :min-width="200">
      </BkTableColumn>
      <BkTableColumn
        field="key"
        label="Key"
        :min-width="200">
      </BkTableColumn>
      <BkTableColumn
        field="exec_count"
        :label="t('数量')"
        :width="200">
      </BkTableColumn>
      <BkTableColumn
        field="cpu"
        :label="t('执行占比')"
        :width="200">
        <template #default="{ data }: { data: Props['info']['infos'][number] }">
          <div class="detail-ratio">
            <BkProgress
              bg-color="#EAEBF0"
              class="mr-8"
              :color="getColor(Number(data.ratio))"
              :percent="Number(data.ratio)"
              :show-text="false"
              stroke-linecap="square"
              :stroke-width="14"
              type="circle"
              :width="20" />
            <span class="detail-ratio">{{ data.ratio }} %</span>
          </div>
        </template>
      </BkTableColumn>
    </BkTable>
  </DbCard>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { getAnalysisDetails } from '@services/source/redisAnalysis';

  interface Props {
    info: {
      infos: ServiceReturnType<typeof getAnalysisDetails>['string'];
      instace: string;
    };
  }

  defineProps<Props>();

  const { t } = useI18n();

  const getColor = (ratio: number) => {
    let color = '#2DCB56';

    if (ratio >= 90) {
      color = '#EA3636';
    } else if (ratio >= 70) {
      color = '#FF9C01';
    }
    return color;
  };
</script>

<style lang="less" scoped>
  .db-card {
    padding: 12px 24px;

    :deep(.db-card__content) {
      padding-top: 12px;
    }
  }

  .detail-ratio {
    display: flex;
    font-weight: bolder;
    color: #63656e;
  }
</style>
