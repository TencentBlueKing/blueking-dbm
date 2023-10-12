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
  <BkSelect
    v-model="selectedValue"
    :clearable="false"
    multiple
    :scroll-height="0"
    style="width: 250px;"
    @click="togglePanel">
    <BkOption
      v-for="(item, index) in 31"
      :key="index"
      :label="item"
      :value="item" />
    <template #extension>
      <div class="panel">
        <div
          v-for="(item, index) in selectList"
          :key="index"
          class="num"
          :class="{
            'num-today': item.isToday,
            'num-choosed': item.choosed,
            'num-active': item.active,
            'num-choosed-min': item.choosed && item.isStart,
            'num-choosed-max': item.choosed && item.isEnd,
          }"
          @click="() => handleClickNum(index)">
          {{ item.value }}
        </div>
      </div>
    </template>
  </BkSelect>
</template>
<script setup lang="ts">

  interface ListItem {
    value: number,
    active: boolean,
    choosed: boolean,
    isStart: boolean,
    isEnd: boolean,
    isToday: boolean,
  }

  interface Emits {
    (e: 'change', value: number[]): void
  }

  const emits = defineEmits<Emits>();

  function generateList() {
    return new Array(31).fill(0)
      .reduce((results, item, index) => {
        const date = index + 1;
        const isToday = date === todayDate;
        const obj = {
          value: date,
          active: false,
          choosed: false,
          isStart: false,
          isEnd: false,
          isToday,
        };
        results.push(obj);
        return results;
      }, []) as ListItem[];
  }

  const showPanel = ref(false);

  let choosedIndexArr: number[] = [];

  const todayDate = new Date().getDate();

  const selectList = ref(generateList());

  const selectedValue = computed(() => selectList.value.filter(item => item.choosed || item.active)
    .map(item => item.value));

  watch(selectedValue, (list) => {
    emits('change', list);
  }, {
    immediate: true,
  });

  const handleClickNum = (index: number) => {
    if (choosedIndexArr.length === 2) {
      choosedIndexArr.length = 0;
      const selects = generateList();
      selectList.value = selects;
    }
    choosedIndexArr.push(index);
    selectList.value[index].choosed = true;

    if (choosedIndexArr.length === 2) {
      // 连起来
      if (choosedIndexArr[0] === choosedIndexArr[1]) {
        return;
      }
      const min = Math.min(...choosedIndexArr);
      const max = Math.max(...choosedIndexArr);
      choosedIndexArr = [min, max];
      const selects = generateList();
      selects[min].choosed = true;
      selects[min].isStart = true;
      selects[max].choosed = true;
      selects[max].isEnd = true;
      for (let i = min + 1; i < max; i++) {
        selects[i].active = true;
      }
      selectList.value = selects;
    }
  };

  const togglePanel = () => {
    showPanel.value = !showPanel.value;
  };


</script>
<style lang="less">
.bk-select-extension {
  .panel {
    position: absolute;
    bottom: -180px;
    display: flex;
    width: 250px;
    height: 220px;
    padding: 12px;
    cursor: pointer;
    background: #FFF;
    border: 1px solid #DCDEE5;
    border-radius: 2px;
    box-shadow: 0 2px 6px 0 #0000001a;
    flex-wrap: wrap;

    .num {
      width: 32px;
      height: 32px;
      line-height: 32px;
      color: #63656E;
      text-align: center;
      border-radius: 2px;

      &:hover {
        color: #63656E;
        background-color: #E1ECFF;
      }
    }

    .num-today {
      color: #3A84FF;
      border: 1px solid #A3C5FD;
      border-radius: 2px;
    }

    .num-active {
      background-color: #E1ECFF;
      border-radius: 0;
    }

    .num-choosed {
      color: #fff;
      background-color: #3A84FF;
    }

    .num-choosed-min {
      border-radius: 2px 0 0 2px;
    }

    .num-choosed-max {
      border-radius: 0 2px 2px 0;
    }
  }
}
</style>
