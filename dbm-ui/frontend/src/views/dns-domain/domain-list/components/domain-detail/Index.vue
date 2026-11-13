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
  <DbSideslider
    ref="sideslider"
    v-model:is-show="isShow"
    class="dns-domain-detail"
    :show-footer="isShowFooter"
    :title="t('域名详情')"
    :width="960">
    <BkLoading :loading="isLoading">
      <BkTab
        v-model:active="activeTab"
        class="dns-domain-detail-tab"
        type="unborder-card">
        <BkTabPanel
          :label="t('详情')"
          name="detail"
          render-directive="show">
          <template v-if="detailData">
            <!-- 保存后用 key 重建表单：以返回值为新基线，并复位表单的已编辑状态 -->
            <DetailForm
              v-if="isSelfMaintain"
              :key="formKey"
              ref="detailForm"
              :data="detailData"
              @change="handleFormChange" />
            <DetailView
              v-else
              :data="detailData" />
          </template>
        </BkTabPanel>
        <BkTabPanel
          :label="t('操作日志')"
          name="audits"
          render-directive="show">
          <!-- 首次切到日志 Tab 才挂载，之后保留筛选与页码，关闭侧滑后随侧滑卸载 -->
          <AuditTable
            v-if="isAuditVisited"
            ref="auditTable"
            :domain="domain"
            scope="domain" />
        </BkTabPanel>
      </BkTab>
    </BkLoading>
    <template #footer>
      <BkButton
        class="w-88 mr-8"
        :disabled="!isTouched"
        :loading="isSubmitting"
        theme="primary"
        @click="handleSubmit">
        {{ t('保存') }}
      </BkButton>
      <BkButton
        class="w-88"
        :disabled="isSubmitting"
        @click="handleCancelClick">
        {{ t('取消') }}
      </BkButton>
    </template>
  </DbSideslider>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { type DnsDomainDetail, getDnsDomainDetail, updateDnsDomain } from '@services/source/dnsDomain';

  import AuditTable from '@views/dns-domain/components/audit-table/Index.vue';

  import { messageSuccess } from '@utils';

  import DetailForm from './components/DetailForm.vue';
  import DetailView from './components/DetailView.vue';

  interface Props {
    domain: string;
  }

  type Emits = {
    (e: 'success', value: DnsDomainDetail): void;
    // 详情加载失败（如域名已被删除），侧滑已关闭，列表需要刷新
    (e: 'fail'): void;
  };

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    required: true,
  });

  const { t } = useI18n();

  const sidesliderRef = useTemplateRef('sideslider');
  const detailFormRef = useTemplateRef('detailForm');
  const auditTableRef = useTemplateRef('auditTable');

  const activeTab = ref<'detail' | 'audits'>('detail');
  const detailData = shallowRef<DnsDomainDetail>();
  const isLoading = ref(false);
  const isSubmitting = ref(false);
  const isAuditVisited = ref(false);
  const formKey = ref(0);
  // 用户修改过即启用保存，改回原值仍保持启用
  const isTouched = ref(false);

  const isSelfMaintain = computed(() => detailData.value?.maintain_type === 'self');
  // 集群托管只读不展示底栏；日志 Tab 下也不展示
  const isShowFooter = computed(() => isSelfMaintain.value && activeTab.value === 'detail');

  const fetchDetail = () => {
    isLoading.value = true;
    getDnsDomainDetail({ domain: props.domain })
      .then((data) => {
        detailData.value = data;
      })
      .catch(() => {
        // 错误已由全局提示，关闭空白侧滑并通知列表刷新
        isShow.value = false;
        emits('fail');
      })
      .finally(() => {
        isLoading.value = false;
      });
  };

  // 每次打开都回到「详情」Tab，状态从头开始
  watch(isShow, () => {
    if (isShow.value) {
      activeTab.value = 'detail';
      detailData.value = undefined;
      isAuditVisited.value = false;
      isTouched.value = false;
      fetchDetail();
    }
  });

  watch(activeTab, () => {
    if (activeTab.value === 'audits') {
      isAuditVisited.value = true;
    }
  });

  const handleFormChange = () => {
    isTouched.value = true;
  };

  // 点取消按钮：内容编辑过先弹离开确认，确认离开后再关闭
  const handleCancelClick = async () => {
    if (await sidesliderRef.value!.beforeClose()) {
      isShow.value = false;
    }
  };

  const handleSubmit = () => {
    detailFormRef.value!.getValue().then((formValue) => {
      isSubmitting.value = true;
      updateDnsDomain({
        domain: props.domain,
        ...formValue,
      })
        .then((data) => {
          messageSuccess(t('保存成功'));
          // 保存后留在详情 Tab，以返回值回填；表单重建后回到未修改状态
          detailData.value = data;
          isTouched.value = false;
          formKey.value += 1;
          // 日志 Tab 已挂载时按当前筛选与页码刷新，切过去能看到本次保存的日志
          auditTableRef.value?.refresh();
          emits('success', data);
        })
        .finally(() => {
          isSubmitting.value = false;
        });
    });
  };
</script>
<style lang="less">
  .dns-domain-detail {
    .dns-domain-detail-tab {
      padding: 0 24px;

      .bk-tab-content {
        padding: 16px 0;
      }
    }
  }
</style>
