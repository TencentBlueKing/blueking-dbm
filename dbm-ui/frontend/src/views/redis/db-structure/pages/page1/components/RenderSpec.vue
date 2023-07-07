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
  <BkLoading :loading="isLoading">
    <div
      class="render-spec-box"
      @mouseleave="handleMouseLeave"
      @mouseover="handleMouseOver">
      {{ data?.name }}

      <SpecPanel
        v-if="isShowEye"
        :data="data">
        <template #click>
          <span>
            <DbIcon
              class="eye"
              type="visible1" />
          </span>
        </template>
      </SpecPanel>

      <span
        v-if="!data"
        key="empty"
        style="color: #c4c6cc;">
        {{ $t('输入主机后自动生成') }}
      </span>
    </div>
  </BkLoading>
</template>
<script setup lang="ts">
  import SpecPanel from '@views/redis/common/spec-panel/Index.vue';

  import type { IDataRow } from './Row.vue';

  interface Props {
    data?: IDataRow['spec'];
    isLoading?: boolean;
  }

  const props = defineProps<Props>();
  const isShowEye = ref(false);

  const handleMouseOver = () => {
    if (props.data?.name) isShowEye.value = true;
  };

  const handleMouseLeave = () => {
    isShowEye.value = false;
  };

</script>
<style lang="less" scoped>
.render-spec-box {
  padding: 10px 16px;
  line-height: 20px;
  color: #63656e;
}

.eye {
  font-size: 15px;
  color: #3A84FF;

  &:hover {
    cursor: pointer;
  }
}
</style>
