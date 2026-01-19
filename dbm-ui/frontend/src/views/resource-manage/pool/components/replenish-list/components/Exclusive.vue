<template>
  <div>
    <BkAlert
      v-if="isShowAlert"
      theme="warning">
      <I18nT
        keypath="统计说明：操作系统为空 ( a 台 ) 、园区为空 ( b 台 )、地域为 default ( c 台 ) 的主机均不计入参考水位统计，且机型空的规格不参与补货 ( d 个 ) ，"
        tag="span">
        <template #a>
          <strong>{{ dataSource.empty_os.length }}</strong>
        </template>
        <template #b>
          <strong>{{ dataSource.empty_subzone.length }}</strong>
        </template>
        <template #c>
          <strong>{{ dataSource.empty_city.length }}</strong>
        </template>
        <template #d>
          <strong>{{ dataSource.exclusive_spec.length }}</strong>
        </template>
      </I18nT>
      <BkButton
        text
        theme="primary"
        @click="handleShowDetails">
        {{ t('查看详情') }}
      </BkButton>
    </BkAlert>
    <BkSideslider
      :is-show="isShowSlider"
      :title="t('统计说明')"
      :width="960"
      @closed="handleClose">
      <div class="replenish-exclusive">
        <div class="replenish-exclusive-desc mb-12">
          <I18nT
            keypath="操作系统为空 ( a 台 ) 、园区为空 ( b 台 ) 、地域为 default ( c 台 ) 的主机均不计入待补货的量，且规格空的主机不参与补货 ( d 个 )"
            tag="span">
            <template #a>
              <strong>{{ dataSource.empty_os.length }}</strong>
            </template>
            <template #b>
              <strong>{{ dataSource.empty_subzone.length }}</strong>
            </template>
            <template #c>
              <strong>{{ dataSource.empty_city.length }}</strong>
            </template>
            <template #d>
              <strong>{{ dataSource.exclusive_spec.length }}</strong>
            </template>
          </I18nT>
        </div>
        <BkTab
          v-model:active="active"
          type="unborder-card">
          <BkTabPanel
            :label="t('操作系统为空 ( n )', { n: dataSource.empty_os.length })"
            name="empty_os">
            <TicketInfoTable
              :data="dataSource.empty_os"
              row-key="ip">
              <TicketInfoTableColumn
                col-key="ip"
                :get-copy-value="(row: { ip: string }) => row.ip"
                :min-width="120"
                title="IP" />
            </TicketInfoTable>
          </BkTabPanel>
          <BkTabPanel
            :label="t('园区为空 ( n )', { n: dataSource.empty_subzone.length })"
            name="empty_subzone">
            <TicketInfoTable
              :data="dataSource.empty_subzone"
              row-key="ip">
              <TicketInfoTableColumn
                col-key="ip"
                :get-copy-value="(row: { ip: string }) => row.ip"
                :min-width="120"
                title="IP" />
            </TicketInfoTable>
          </BkTabPanel>
          <BkTabPanel
            :label="t('地域为 default ( n )', { n: dataSource.empty_city.length })"
            name="empty_city">
            <TicketInfoTable
              :data="dataSource.empty_city"
              row-key="ip">
              <TicketInfoTableColumn
                col-key="ip"
                :get-copy-value="(row: { ip: string }) => row.ip"
                :min-width="120"
                title="IP" />
            </TicketInfoTable>
          </BkTabPanel>
          <BkTabPanel
            :label="t('规格为空 ( n )', { n: dataSource.exclusive_spec.length })"
            name="exclusive_spec">
            <TicketInfoTable
              :data="dataSource.exclusive_spec"
              row-key="spec_id">
              <TicketInfoTableColumn
                col-key="spec_id"
                :get-copy-value="(row: { spec_id: number }) => `${row.spec_id}`"
                :min-width="120"
                :title="t('规格 ID')" />
              <TicketInfoTableColumn
                col-key="spec_name"
                :get-copy-value="(row: { spec_name: string }) => row.spec_name"
                :min-width="120"
                :title="t('规格名称')" />
            </TicketInfoTable>
          </BkTabPanel>
        </BkTab>
      </div>
    </BkSideslider>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { ResourceWaterLevel } from '../hooks/use-fetch-data';

  interface Props {
    data: ResourceWaterLevel;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const isShowSlider = ref(false);
  const active = ref('empty_os');

  const dataSource = computed(() => {
    return {
      empty_city: props.data?.exclusive_machine.empty_city.map((item) => ({ ip: item })),
      empty_os: props.data?.exclusive_machine.empty_os.map((item) => ({ ip: item })),
      empty_subzone: props.data?.exclusive_machine.empty_subzone.map((item) => ({ ip: item })),
      exclusive_spec: props.data?.exclusive_spec,
    };
  });

  const isShowAlert = computed(() => {
    return (
      props.data?.exclusive_machine.empty_os.length > 0 ||
      props.data?.exclusive_machine.empty_subzone.length > 0 ||
      props.data?.exclusive_machine.empty_city.length > 0 ||
      props.data?.exclusive_spec.length > 0
    );
  });

  const handleShowDetails = () => {
    isShowSlider.value = true;
  };

  const handleClose = () => {
    isShowSlider.value = false;
  };
</script>

<style lang="less" scoped>
  .replenish-exclusive {
    padding: 18px 24px;

    .replenish-exclusive-desc {
      width: 100%;
      height: 48px;
      background: #f5f7fa;
      border-radius: 2px;
      padding: 16px;
    }
  }
</style>
