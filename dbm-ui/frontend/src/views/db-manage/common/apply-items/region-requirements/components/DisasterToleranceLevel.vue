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
  <BkFormItem
    class="apply-item-disaster-tolerance-level"
    :label="t('容灾要求')"
    property="details.disaster_tolerance_level"
    required>
    <BkRadioGroup v-model="modelValue">
      <BkRadio
        v-for="item in radioDataList"
        :key="item.value"
        :label="item.value">
        <span
          v-bk-tooltips="item.description"
          class="disaster-tolerance-level-description">
          {{ item.label }}
        </span>
      </BkRadio>
    </BkRadioGroup>
  </BkFormItem>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { useSystemEnviron } from '@stores';

  import { Affinity, affinityMap } from '@common/const';

  interface Props {
    /**
     *   -common:  默认情况
     *   -bigdata: 尽量分散 + 无容灾
     *   -single： mysql、sqlserver 的单节点只有无容灾
     */
    type?: 'common' | 'bigdata' | 'single';
  }

  const props = withDefaults(defineProps<Props>(), {
    type: 'common',
  });

  const modelValue = defineModel<string>({
    required: true,
  });

  const { AFFINITY: systemAffinityList } = useSystemEnviron().urls;

  const { t } = useI18n();

  const descriptionMap: Record<string, string[]> = {
    [Affinity.CROS_SUBZONE]: [t('主从必须分布在不同园区'), t('接入层每 2 个一组，同一组的主机必须分布在不同园区')],
    [Affinity.CROSS_RACK]: [
      t('不限制主机所在园区'),
      t('主从必须分布在不同机架'),
      t('接入层每 2 个一组，同一组的主机必须分布在不同机架'),
    ],
    [Affinity.MAX_EACH_ZONE_EQUAL]: [t('优先保障资源分配，在资源充足情况下尽量让相同角色的主机跨园区/机架分布')],
    [Affinity.NONE]: [t('主机分布无任何约束')],
    [Affinity.SAME_SUBZONE_CROSS_SWTICH]: [
      t('主机必须部署在指定园区内'),
      t('主从必须分布在不同机架'),
      t('接入层每 2 个一组，同一组的主机必须分布在不同机架'),
    ],
  };

  const getAffinityItem = (key: string) => {
    const descriptionList = descriptionMap[key];
    return {
      description:
        descriptionList.length > 1
          ? descriptionList.map((descriptionItem) => `• ${descriptionItem}`).join('\n')
          : descriptionList[0],
      label: affinityMap[key as Affinity],
      value: key,
    };
  };

  let radioDataList: ReturnType<typeof getAffinityItem>[] = [];

  if (props.type === 'single') {
    radioDataList = [Affinity.NONE].map((key) => getAffinityItem(key));
  } else {
    const defaultAffinityList =
      props.type === 'bigdata'
        ? [Affinity.MAX_EACH_ZONE_EQUAL]
        : [Affinity.CROS_SUBZONE, Affinity.SAME_SUBZONE_CROSS_SWTICH, Affinity.CROSS_RACK];
    const radioAffinityList = systemAffinityList.some(
      (systemAffinityItem) => systemAffinityItem.value === Affinity.NONE,
    )
      ? [...defaultAffinityList, Affinity.NONE]
      : defaultAffinityList;
    radioDataList = radioAffinityList.map((key) => getAffinityItem(key));
  }
</script>

<style lang="less">
  .apply-item-disaster-tolerance-level {
    .disaster-tolerance-level-description {
      cursor: pointer;
      border-bottom: 1px dashed #979ba5;
    }
  }
</style>
