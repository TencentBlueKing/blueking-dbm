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
  <div class="result-panel-main">
    <BkTab
      v-model:active="currentPanel"
      type="unborder-card">
      <BkTabPanel
        :label="t('查询提示')"
        name="tip"
        :num="tipCount"
        num-display-type="elliptic">
        <Tips :data="tipList" />
      </BkTabPanel>
      <BkTabPanel
        :label="t('查询结果')"
        name="result"
        num-display-type="elliptic">
        <Result
          :data="data"
          :db-type="dbType"
          :query-seconds="querySeconds" />
      </BkTabPanel>
    </BkTab>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { DBTypes } from '@common/const';

  import type { DbConsoleResults } from '../../Index.vue';

  import Result from './components/result/Index.vue';
  import Tips from './components/tips/Index.vue';

  interface Props {
    data?: DbConsoleResults;
    dbType?: DBTypes;
    querySeconds?: number;
  }

  const props = withDefaults(defineProps<Props>(), {
    data: () => [],
    dbType: DBTypes.MYSQL,
    querySeconds: 0,
  });

  const { t } = useI18n();

  const currentPanel = ref('tip');
  const tipList = ref<string[]>([]);
  const tipCount = ref<undefined | number>();
  const resultPanels = ref<
    {
      label: string;
      name: string;
      num?: number;
    }[]
  >([
    {
      label: t('查询提示'),
      name: 'tip',
    },
    {
      label: t('查询结果'),
      name: 'result',
    },
  ]);

  watch(
    () => props.data,
    () => {
      if (props.data) {
        tipList.value = props.data.filter((item) => !!item.error_msg).map((item) => item.error_msg);
        if (tipList.value.length) {
          resultPanels.value[0].num = tipList.value.length;
        } else {
          delete resultPanels.value[0].num;
        }

        if (tipList.value.length < props.data.length) {
          currentPanel.value = 'result';
        } else {
          currentPanel.value = 'tip';
        }
      }
    },
  );
</script>
<style lang="less" scoped>
  .result-panel-main {
    height: 100%;
    background: #fff;

    :deep(.bk-tab--top) {
      height: 100%;
      border: 1px solid #dcdee5;
    }

    :deep(.bk-tab-header--has-num-elliptic) {
      color: #fff;
      background: #3a84ff;
    }

    :deep(.bk-tab-content) {
      padding: 0;
    }
  }
</style>
