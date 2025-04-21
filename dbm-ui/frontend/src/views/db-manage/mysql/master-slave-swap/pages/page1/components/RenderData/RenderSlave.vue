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
  <div class="render-slave-box">
    <RenderText
      ref="editRef"
      :data="localValue"
      :is-loading="isLoading"
      :placeholder="t('选择主库主机后自动生成')"
      :rules="rules" />
  </div>
</template>
<script lang="ts">
  const singleHostSelectMemo: { [key: string]: Record<string, boolean> } = {};
</script>
<script setup lang="ts">
  import { ref, watch } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { getIntersectedSlaveMachinesFromClusters } from '@services/source/mysqlCluster';

  import { useGlobalBizs } from '@stores';

  import RenderText from '@components/render-table/columns/text-plain/index.vue';

  import { random } from '@utils';

  import type { IDataRow } from './Row.vue';

  interface Props {
    clusterList: number[];
    data: IDataRow['slaveData'];
  }

  interface Exposes {
    getValue: () => Promise<{ slave_ip: ISlaveHost }>;
  }

  interface ISlaveHost {
    bk_biz_id: number;
    bk_cloud_id: number;
    bk_host_id: number;
    ip: string;
  }

  const props = defineProps<Props>();

  const genHostKey = (hostData: any) => `${hostData.ip}`;

  const instanceKey = `render_slave_${random()}`;
  singleHostSelectMemo[instanceKey] = {};

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();

  const editRef = ref();
  const localValue = ref('');
  const slaveData = reactive({
    bk_biz_id: currentBizId,
    bk_cloud_id: 0,
    bk_host_id: 0,
    ip: '',
  });
  const isLoading = ref(false);

  const rules = [
    {
      message: t('目标从库不能为空'),
      validator: (value: string) => Boolean(value),
    },
  ];

  watch(
    () => props.clusterList,
    () => {
      if (props.data) {
        localValue.value = genHostKey(props.data);
      } else {
        localValue.value = '';
      }

      if (props.clusterList.length > 0) {
        isLoading.value = true;
        getIntersectedSlaveMachinesFromClusters({
          bk_biz_id: currentBizId,
          cluster_ids: props.clusterList,
          is_stand_by: true,
        })
          .then((data) => {
            const [slave] = data;
            if (slave) {
              localValue.value = genHostKey(slave);
              Object.assign(slaveData, slave);
            }
          })
          .finally(() => {
            isLoading.value = false;
          });
      }
    },
    {
      immediate: true,
    },
  );

  defineExpose<Exposes>({
    getValue() {
      return editRef.value
        .getValue()
        .then(() => {
          return {
            slave_ip: slaveData,
          };
        })
        .catch(() =>
          Promise.reject({
            slave_ip: undefined,
          }),
        );
    },
  });
</script>
<style lang="less" scoped>
  .render-slave-box {
    position: relative;
  }
</style>
