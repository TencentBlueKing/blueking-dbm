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
  <div class="final-db-review">
    <RenderTable>
      <template #default>
        <RenderTableHeadColumn
          :min-width="120"
          :width="580">
          {{ t('备份DB名') }}
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="120"
          :required="false"
          :width="580">
          {{ t('忽略DB名') }}
        </RenderTableHeadColumn>
      </template>
      <template #data>
        <tr>
          <td style="padding: 0">
            <RenderDbName
              ref="backupDbsRef"
              :cluster-id="data.clusterId"
              :model-value="backupDbs"
              required
              @change="handleBackupDbsChange" />
          </td>
          <td style="padding: 0">
            <RenderDbName
              ref="ignoreDbsRef"
              :cluster-id="data.clusterId"
              :model-value="ignoreDbs"
              @change="handleIgnoreDbsChange" />
          </td>
        </tr>
      </template>
    </RenderTable>
    <template v-if="finalDbs">
      <div class="review-list-head mt-24">
        <span class="list-title">{{ t('最终DB') }}</span>
        <span class="list-num">（{{ t('共n个', [finalDbs.length]) }}）</span>
        <BkButton
          class="list-copy-button"
          text
          theme="primary"
          @click="handleCopy">
          <DbIcon
            class="mr-4 mt-2"
            type="copy" />
          {{ t('复制') }}
        </BkButton>
      </div>
      <div class="review-list mt-16">
        <div
          v-for="(item, index) in finalDbs"
          :key="index"
          class="review-list-item">
          {{ item }}
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getSqlserverDbs } from '@services/source/sqlserver'

  import { useCopy } from '@hooks';

  import RenderTableHeadColumn from '@components/render-table/HeadColumn.vue';
  import RenderTable from '@components/render-table/Index.vue';

  import RenderDbName from '../RenderData/RenderDbName.vue';

  interface Props {
    data: {
      clusterId: number;
      backupDbs: string[];
      ignoreDbs: string[];
    };
  }

  interface Emits {
    (e: 'change', backupDbs: string[], ignoreDbs: string[]): void;
  }

  interface Expose {
    submit(): Promise<any>;
    // cancel(): Promise<any>;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const copy = useCopy();

  const backupDbsRef = ref<InstanceType<typeof RenderDbName>>();
  const ignoreDbsRef = ref<InstanceType<typeof RenderDbName>>();
  const backupDbs = ref(_.cloneDeep(props.data.backupDbs));
  const ignoreDbs = ref(_.cloneDeep(props.data.ignoreDbs));

  const {
    data: finalDbs,
    run: getSqlserverDbsRun
  } = useRequest(getSqlserverDbs, {
    manual: true,
  })

  const getFinalDbsNew = (backupDbs: string[], ignoreDbs: string[]) => {
    getSqlserverDbsRun({
      cluster_id: props.data.clusterId,
      db_list: backupDbs,
      ignore_db_list: ignoreDbs
    })
  }
  getFinalDbsNew(props.data.backupDbs, props.data.ignoreDbs)

  const handleBackupDbsChange = (value: string[]) => {
    backupDbs.value = value;
    getFinalDbsNew(value, ignoreDbs.value)
  };

  const handleIgnoreDbsChange = (value: string[]) => {
    ignoreDbs.value = value;
    getFinalDbsNew(backupDbs.value, value)
  };

  const handleCopy = () => {
    copy((finalDbs?.value || []).join('\n'));
  };

  defineExpose<Expose>({
    submit() {
      return Promise.all([
        backupDbsRef.value!.getValue(),
        ignoreDbsRef.value!.getValue()
      ]).then(
        ([backupDbs, ignoreDbs]) => {
          emits('change', backupDbs, ignoreDbs);
        },
      );
    },
  });
</script>

<style lang="less">
  .final-db-review {
    padding: 20px 24px;

    .review-list-head {
      display: flex;

      .list-title {
        color: #313238;
      }

      .list-num {
        margin-left: 4px;
      }

      .list-copy-button {
        margin-left: auto;
        font-size: 12px;
      }
    }

    .review-list {
      display: flex;
      padding: 16px;
      background: #f5f7fa;
      border-radius: 2px;
      flex-wrap: wrap;

      .review-list-item {
        width: 33%;
        font-size: 12px;
        line-height: 24px;
      }
    }
  }
</style>
