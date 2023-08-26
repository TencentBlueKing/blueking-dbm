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
      v-if="!data"
      @click="handleClickSelect">
      <TableEditSelect
        ref="selectRef"
        disabled
        :list="[]"
        :placeholder="t('请选择')"
        :rules="rules" />
    </div>

    <div
      v-else
      class="capacity-box"
      @click="handleClickSelect">
      <div
        class="content">
        <!-- <span style="margin-right: 5px;">{{ t('磁盘') }}:</span>
        <BkProgress
          color="#2DCB56"
          :percent="percent"
          :show-text="false"
          size="small"
          :stroke-width="18"
          type="circle"
          :width="20" /> -->
        <!-- <span class="percent">{{ percent > 100 ? 100 : percent }}%</span> -->
        <!-- <span class="spec">{{ `(${data.used}G/${data.total}G)` }}</span> -->
        <span class="spec">{{ `${data.total}G` }}</span>
        <!-- <span
          class="scale-percent"
          :style="{color: data.total > data.current ?
            '#EA3636' : '#2DCB56'}">{{ `(${changeObj.rate}%, ${changeObj.num}G)` }}</span> -->
        <span
          class="scale-percent"
          :style="{color: data.total > data.current ?
            '#EA3636' : '#2DCB56'}">{{ `(${changeObj.num}G)` }}</span>
      </div>
    </div>
  </BkLoading>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TableEditSelect from '@views/redis/common/edit/Select.vue';

  import type { IDataRow } from './Row.vue';

  interface Props {
    data?: IDataRow['targetCapacity'];
    isLoading?: boolean;
  }

  interface Emits {
    (e: 'click-select'): void
  }


  interface Exposes {
    getValue: () => Promise<boolean>
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const selectRef = ref();

  // const percent = computed(() => {
  //   if (props.data) return Number(((props.data.used / props.data.total) * 100).toFixed(2));
  //   return 0;
  // });

  const changeObj = computed(() => {
    if (props.data) {
      const diff = props.data.total - props.data.current;
      const rate = ((diff / props.data.current) * 100).toFixed(2);
      if (diff < 0) {
        return {
          rate,
          num: diff,
        };
      }
      return {
        rate: `+${rate}`,
        num: `+${diff}`,
      };
    }
    return {
      rate: 0,
      num: 0,
    };
  });

  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('请选择目标容量'),
    },
  ];

  const handleClickSelect  = () => {
    emits('click-select');
  };

  defineExpose<Exposes>({
    getValue() {
      if (!props.data) {
        return selectRef.value
          .getValue()
          .then(() => true);
      }
      return Promise.resolve(true);
    },
  });

</script>
<style lang="less" scoped>
.capacity-box {
  padding: 10px 16px;
  overflow: hidden;
  line-height: 20px;
  color: #63656e;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
  border: 1px solid transparent;

  &:hover {
    background-color: #fafbfd;
    border-color: #a3c5fd;
  }

  .content {
    display: flex;
    align-items: center;
    font-size: 12px;
    color: #63656E;

    .percent {
      margin-left: 4px;
      font-size: 12px;
      font-weight: bold;
      color: #313238;
    }

    .spec {
      margin-left: 2px;
      font-size: 12px;
      color: #979BA5;
    }

    .scale-percent {
      margin-left: 5px;
      font-size: 12px;
      font-weight: bold;
    }
  }
}
</style>
