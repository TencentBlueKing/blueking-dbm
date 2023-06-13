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
  <BkLoading
    class="cluster-settings"
    :loading="isLoading">
    <template
      v-for="(xml,index) in xmls"
      :key="xml.name">
      <BkCollapsePanel :model-value="index === 0">
        <template #header>
          <div class="custom-collapse-header">
            <div class="custom-collapse-header__left">
              <DbIcon type="down-shape custom-collapse-header__icon" />
              <strong class="custom-collapse-header__name">{{ xml.name }}</strong>
            </div>
            <div class="custom-collapse-header__bar">
              <a
                class="mr-8"
                href="javascript:"
                @click.stop="copy(xml.value)">{{ $t('复制') }}</a>
              <a
                href="javascript:"
                @click.stop="handleDownload(xml)">{{ $t('下载') }}</a>
            </div>
          </div>
        </template>
        <template #content>
          <SettingsMonacoEditor :value="xml.value" />
        </template>
      </BkCollapsePanel>
    </template>
  </BkLoading>
</template>

<script setup lang="ts">
  import {
    getClusterXmls,
  } from '@services/hdfs';

  import { useGlobalBizs } from '@stores';

  import SettingsMonacoEditor from './SettingsMonacoEditor.vue';

  import { useCopy } from '@/hooks';

  interface XML {
    name: string,
    value: string
  }

  interface Props {
    clusterId: number
  }

  const props = defineProps<Props>();

  const { currentBizId } = useGlobalBizs();
  const copy = useCopy();

  const isLoading = ref(false);
  const xmlKeys = ['hdfs-site.xml', 'core-site.xml'];
  const xmls = shallowRef<XML[]>([]);

  const getXmls = () => {
    if (!props.clusterId) return;

    isLoading.value = true;
    getClusterXmls({
      bk_biz_id: currentBizId,
      cluster_id: props.clusterId,
    })
      .then((res) => {
        xmls.value = xmlKeys.map(key => ({
          name: key,
          value: res[key] ?? '',
        }));
      })
      .finally(() => {
        isLoading.value = false;
      });
  };

  watch(() => props.clusterId, () => {
    getXmls();
  }, { immediate: true });

  const handleDownload = (xml: XML) => {
    const a = document.createElement('a');
    const blob = new Blob([xml.value], { type: 'text/plain' });

    a.setAttribute('href', window.URL.createObjectURL(blob));
    a.setAttribute('download', xml.name);

    a.click();
  };
</script>

<style lang="less" scoped>
.cluster-settings {
  height: 100%;
  padding: 28px 40px;

  .custom-collapse-header {
    display: flex;
    height: 58px;
    font-size: 12px;
    line-height: 58px;
    align-items: center;
    justify-content: space-between;
    color: @title-color;
    cursor: pointer;

    &__icon {
      display: inline-block;
      font-size: 14px;
      color: @default-color;
      transform: rotateZ(-90deg);
      transition: all 0.2s;
    }

    &__name {
      margin: 0 4px 0 12px;
    }
  }

  :deep(.bk-collapse-item) {
    padding: 0 16px;
    margin-bottom: 16px;
    background-color: white;
    border: 1px solid #dcdee5;
    border-radius: 2px;

    &-active {
      .custom-collapse-header__icon {
        transform: rotate(0);
      }
    }
  }

  :deep(.bk-collapse-content) {
    padding: 0;
  }
}
</style>
