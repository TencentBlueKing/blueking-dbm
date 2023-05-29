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
  <div class="empty-config">
    <div class="empty-config__content">
      <img
        src="@images/empty.png"
        width="220">
      <p>{{ $t('暂未绑定数据库相关配置') }}</p>
      <BkButton
        outline
        theme="primary"
        @click="handleModuleBind">
        {{ $t('立即绑定') }}
      </BkButton>
    </div>
  </div>
</template>

<script setup lang="ts">
  import type { ComputedRef } from 'vue';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import type { TreeData } from '../common/types';

  const router = useRouter();
  const route = useRoute();
  const globalBizsStore = useGlobalBizs();
  const treeNode = inject<ComputedRef<TreeData>>('treeNode');

  const handleModuleBind = () => {
    let { id, name } = treeNode!.value;
    const { parentId, levelType } = treeNode!.value;
    if (parentId && levelType === 'cluster') {
      const parentInfo = (parentId as string).split('-');
      [name] = parentInfo;
      id = Number(parentInfo[1]);
    }
    router.push({
      name: 'SelfServiceBindDbModule',
      params: {
        type: route.params.clusterType === ClusterTypes.TENDBSINGLE
          ? TicketTypes.MYSQL_SINGLE_APPLY : TicketTypes.MYSQL_HA_APPLY,
        bk_biz_id: globalBizsStore.currentBizId,
        db_module_id: id,
      },
      query: { module_name: name },
    });
  };
</script>

<style lang="less" scoped>
  .empty-config {
    position: relative;
    height: calc(100% - 42px);
    text-align: center;

    &__content {
      position: absolute;
      top: 40%;
      left: 50%;
      transform: translate(-50%, -50%);
    }

    p {
      padding: 4px 0 24px;
    }
  }

</style>
