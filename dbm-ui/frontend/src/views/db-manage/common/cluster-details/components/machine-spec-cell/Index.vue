<template>
  <template v-if="groups.length">
    <template v-if="mode === 'list'">
      <div
        v-for="group in groups"
        :key="group.machineType"
        class="machine-spec-cell-line">
        <span class="machine-spec-cell-role">{{ group.machineType }}</span>
        <span>：</span>
        <MachineSpecItem :spec="group.representative" />
        <BkPopover
          v-if="group.specs.length > 1"
          ext-cls="machine-spec-cell-popover-wrapper"
          theme="light"
          trigger="click">
          <span class="machine-spec-cell-more">({{ t('共 n 个', [group.specs.length]) }})</span>
          <template #content>
            <div class="machine-spec-cell-popover">
              <div class="popover-header">{{ t('共 n 个', [group.specs.length]) }}</div>
              <div
                v-for="(spec, specIndex) in group.specs"
                :key="specIndex"
                class="machine-spec-cell-tooltip-line">
                <MachineSpecItem :spec="spec" />
              </div>
            </div>
          </template>
        </BkPopover>
      </div>
    </template>
    <template v-else>
      <div
        v-for="group in groups"
        :key="group.machineType"
        class="machine-spec-cell-line">
        <span class="machine-spec-cell-role">{{ group.machineType }}</span>
        <span>：</span>
        <template
          v-for="(spec, specIndex) in group.specs"
          :key="specIndex">
          <span v-if="specIndex > 0">，</span>
          <MachineSpecItem :spec="spec" />
        </template>
      </div>
    </template>
  </template>
  <span v-else>--</span>
</template>

<script setup lang="ts">
  import BkPopover from 'bkui-vue/lib/popover';
  import { useI18n } from 'vue-i18n';

  import type { MachineSpec } from '@services/types';

  import { groupMachineSpecs } from '@views/db-manage/common/machineSpecs';

  import MachineSpecItem from '../machine-spec-item/Index.vue';

  type SpecCellMode = 'list' | 'detail';

  interface Props {
    mode?: SpecCellMode;
    specs: MachineSpec[];
  }

  const props = withDefaults(defineProps<Props>(), {
    mode: 'list',
  });

  const { t } = useI18n();

  const groups = computed(() => groupMachineSpecs(props.specs || []));
</script>
<style lang="less">
  .machine-spec-cell-line {
    white-space: nowrap;
  }

  .machine-spec-cell-role {
    font-weight: 600;
    color: #313238;
  }

  .machine-spec-cell-more {
    margin-left: 4px;
    color: #3a84ff;
    cursor: pointer;
  }

  .machine-spec-cell-popover-wrapper {
    .machine-spec-cell-tooltip-line {
      line-height: 20px;
    }

    .machine-spec-cell-popover {
      .popover-header {
        padding-bottom: 4px;
        font-size: 14px;
        font-weight: bolder;
        color: #313238;
        // border-bottom: 1px solid #dcdee5;
      }

      // .popover-line {
      //   padding-top: 6px;
      // }
    }
  }
</style>
