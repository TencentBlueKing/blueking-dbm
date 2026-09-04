<template>
  <!-- eslint-disable vue/space-unary-ops -->
  <div
    v-if="isSelector"
    class="user-selector"
    v-bind="$attrs"
    :style="{
      height: fixedHeight ? selectorHeight + 'px' : 'auto',
    }"
    @click="focus"
    @mousedown="shouldUpdate = false">
    <div class="user-selector-layout">
      <div
        ref="containerRef"
        class="user-selector-container"
        :class="{
          focus: isFocus,
          disabled: disabled,
          placeholder: !localValue.length && !isFocus,
          'is-fast-clear': fastClear,
          'has-avatar': tagType === 'avatar',
          'is-loading': loading,
          'is-flex-height': !fixedHeight,
        }"
        :data-placeholder="placeholder"
        :style="containerStyle"
        @mousewheel="handleContainerScroll">
        <template v-if="multiple || !isFocus">
          <span
            v-for="(user, index) in localValueUsers"
            :key="user.username"
            class="user-selector-selected"
            @click.stop
            @mousedown.left.stop="handleSelectedMousedown($event, index)"
            @mouseenter="handleSelectedMouseenter($event, user)"
            @mouseleave="handleSelectedMouseleave($event, user)"
            @mouseup.left.stop="handleSelectedMouseup($event, index)">
            <template v-if="renderTag">
              <RenderTag
                :index="index"
                :user="user"
                :username="user.username" />
            </template>

            <template v-else>
              <RenderAvatar
                v-if="tagType === 'avatar'"
                class="user-selector-selected-avatar"
                :url-method="avatarUrl"
                :user="user" />
              <span class="user-selector-selected-value">
                {{ getDisplayText(user) }}
              </span>
            </template>

            <i
              v-if="tagClearable && tagType === 'tag' && !disabled"
              class="user-selector-selected-clear bk-biz-components-icon bk-biz-icon-close"
              @click.stop.prevent="handleRemoveSelected(user, index)"
              @mousedown.left.stop="handleRemoveMouseDown"
              @mouseup.left.stop />
          </span>
        </template>
        <span
          v-show="isFocus"
          ref="inputRef"
          class="user-selector-input"
          contenteditable
          spellcheck="false"
          @blur="handleBlur"
          @click.stop
          @input="handleInput($event)"
          @keydown="handleKeydown($event)"
          @paste.prevent.stop="handlePaste($event)" />
      </div>
      <i
        v-if="fastClear && !disabled && localValue.length"
        class="user-selector-clear bk-dbm db-icon-close-circle-shape"
        @click.stop="handleFastClear" />
    </div>
  </div>
  <span
    v-else
    class="user-selector user-selector-info">
    {{ userInfo }}
  </span>
</template>

<script>
  /* eslint-disable @typescript-eslint/no-misused-promises, max-len, no-prototype-builtins, vue/space-infix-ops */
  import { throttle } from 'lodash';
  import Tippy from 'tippy.js';
  import {
    computed,
    createApp,
    defineComponent,
    getCurrentInstance,
    nextTick,
    onBeforeUnmount,
    onMounted,
    provide,
    ref,
    toRefs,
    watch,
  } from 'vue';

  import AlternateList from './alternate-list';
  import RenderAvatar from './render-avatar';
  import RenderTag from './render-tag';

  import 'tippy.js/dist/tippy.css';
  import 'tippy.js/themes/light.css';
  import '@icon-cool/bk-icon-bk-biz-components';
  export default defineComponent({
    name: 'BkUserSelector',
    components: {
      RenderTag,
      RenderAvatar,
    },
    props: {
      modelValue: {
        type: Array,
        default: () => [],
      },
      placeholder: {
        type: String,
        default: '请输入用户',
      },
      disabled: {
        type: Boolean,
        default: false,
      },
      multiple: {
        type: Boolean,
        default: true,
      },
      exclude: {
        type: Boolean,
        default: true,
      },
      focusRowLimit: {
        type: Number,
        default: 6,
      },
      defaultAlternate: {
        type: [String, Array, Function],
        validator(value) {
          return value === 'history' || typeof value === 'function' || value instanceof Array;
        },
      },
      searchFromDefaultAlternate: {
        type: Boolean,
        default: true,
      },
      historyKey: String,
      historyLabel: {
        type: String,
        default: '最近选择',
      },
      historyRecord: {
        type: Number,
        default: 5,
      },
      displayListTips: Boolean,
      fuzzySearchMethod: Function,
      exactSearchMethod: Function,
      emptyText: {
        type: String,
        default: '无匹配人员',
      },
      tagClearable: {
        type: Boolean,
        default: true,
      },
      fastClear: Boolean,
      renderList: Function,
      renderTag: Function,
      displayTagTips: Boolean,
      tagTipsContent: Function,
      tagTipsDelay: {
        type: Number,
        default: 300,
      },
      tagType: {
        type: String,
        default: 'tag',
        validator(value) {
          return ['tag', 'avatar'].includes(value);
        },
      },
      avatarUrl: {
        type: Function,
        default: () => null,
      },
      fixedHeight: {
        type: Boolean,
        default: true,
      },
      disabledUsers: {
        type: Array,
        default: () => [],
      },
      listScrollHeight: [Number, String],
      pasteFormatter: {
        type: Function,
        default(value) {
          return value.replace(/\(.*/, '');
        },
      },
      pasteValidator: Function,
      panelWidth: {
        type: [Number, String],
        validator(value) {
          const pixel = parseInt(value, 10);
          return pixel >= 190;
        },
      },
      displayDomain: {
        type: Boolean,
        default: true,
      },
      type: {
        type: String,
        default: 'selector',
        validator(value) {
          return ['selector', 'info'].includes(value);
        },
      },
    },
    emits: ['update:modelValue', 'change', 'remove-selected', 'select-user', 'keydown', 'focus', 'blur', 'clear'],
    setup(props, ctx) {
      const {
        modelValue,
        disabled,
        multiple,
        exclude,
        focusRowLimit,
        defaultAlternate,
        searchFromDefaultAlternate,
        historyKey,
        historyLabel,
        historyRecord,
        fuzzySearchMethod,
        exactSearchMethod,
        displayTagTips,
        tagTipsContent,
        tagTipsDelay,
        fixedHeight,
        disabledUsers,
        pasteFormatter,
        pasteValidator,
        displayDomain,
        type,
      } = toRefs(props);

      const search = async (value, next) => {
        if (isUnmounted) {
          return;
        }
        try {
          const popoverInstance = getPopoverInstance();
          getAlternateContent();
          popoverInstance.setContent(alternateContent.value.$refs.alternateListContainer);
          showPopover();
          alternateContent.value.loading = !!value;
          const { results: users, next: nextPage } = await new Promise((resolve, _reject) => {
            if (value) {
              const promise = [runFuzzySearch(value, next)];
              if (searchFromDefaultAlternate.value) {
                promise.push(getDefaultAlternateData(value));
              }
              Promise.all(promise).then(([fuzzySearchData, defaultAlternateData]) => {
                if (defaultAlternateData) {
                  fuzzySearchData.results.unshift(...defaultAlternateData.results);
                }
                resolve(fuzzySearchData);
              })
            } else {
              const defaultAlternateData = getDefaultAlternateData();
              resolve(defaultAlternateData);
            }
          });

          if (isUnmounted || !isFocus.value) {
            return;
          }
          const { matched, flattened } = filterUsers(users);
          if (!value && !flattened.length) {
            hidePopover();
            return;
          }

          matchedUsers.value = next ? [...matchedUsers.value, ...matched] : matched;
          flattenedUsers.value = next ? [...flattenedUsers.value, ...flattened] : flattened;
          highlightIndex.value = flattened.length && !!inputValue.value ? 0 : -1;

          alternateContent.value.next = nextPage;
          alternateContent.value.keyword = value;
          alternateContent.value.matchedUsers = matchedUsers.value;
        } catch (e) {
          if (e.type === 'reset') {
            return;
          }
          matchedUsers.value = [];
          flattenedUsers.value = [];
          console.error(e);
        } finally {
          // 无论成功、失败还是提前 return，都要收掉备选面板的 loading 遮罩
          if (alternateContent.value) {
            alternateContent.value.loading = false;
          }
        }
      };

      const containerRef = ref(null);
      const inputRef = ref(null);
      const { proxy } = getCurrentInstance();

      provide('parentSelector', proxy);

      const selectorHeight = ref(32);
      const singleRowHeight = ref(30);
      const inputValue = ref('');
      const inputIndex = ref(0);
      const highlightIndex = ref(-1);
      const shouldUpdate = ref(true);
      const isFocus = ref(false);
      const overflowTagIndex = ref(null);
      const currentUsers = ref([]);
      const matchedUsers = ref([]);
      const flattenedUsers = ref([]);
      const scheduleSearch = throttle(search, 800, { leading: false });
      const popoverInstance = ref(null);
      const alternateContent = ref(null);
      const selectedTipsTimer = ref({});
      const overflowTagNode = ref(null);
      const loading = ref(false);
      const isSelector = computed(() => type.value === 'selector');
      const containerStyle = computed(() => {
        const style = {};
        if (isFocus.value) {
          style.maxHeight = fixedHeight.value ? `${focusRowLimit.value * singleRowHeight.value}px` : 'auto';
        } else if (fixedHeight.value) {
          style.height = `${singleRowHeight.value}px`;
        }
        return style;
      });

      const localValue = ref([...modelValue.value]);
      let isIgnoreUpdateModelValue = false;
      let isUnmounted = false;
      // AlternateList 的独立 app 实例，卸载时需要手动 unmount
      let alternateContentApp = null;
      // 已选人员 tag 上创建的 Tippy 实例，卸载时需要逐个销毁
      const tagTipsInstances = [];

      const localValueUsers = computed(() =>
        localValue.value.map((username) => {
          const user = currentUsers.value.find((user) => user.username === username);
          return user || { username };
        }),
      );

      const userInfo = computed(() => localValueUsers.value.map((user) => getDisplayText(user)).join(';'));

      const getCurrentUsers = async () => {
        // 没有选中任何人时无需查询，否则每个实例挂载和清空都会发一次空条件请求
        if (!localValue.value.length) {
          currentUsers.value = [];
          return;
        }
        if (!exactSearchMethod.value) {
          console.warn('No exact search method has been set');
          return;
        }
        try {
          currentUsers.value = await exactSearchMethod.value(localValue.value);
        } catch (error) {
          console.error(error);
        }
      };
      const getDefaultAlternateData = async (keyword) => {
        let users = [];
        const isMatch = (user, keyword) => user.username.toLowerCase().indexOf(keyword.toString().toLowerCase()) > -1;
        if (defaultAlternate.value === 'history') {
          users = [{ display_name: historyLabel.value, children: getHistoryUsers() }];
        } else if (defaultAlternate.value instanceof Array) {
          users = defaultAlternate.value;
        } else if (typeof defaultAlternate.value === 'function') {
          users = await defaultAlternate.value();
        }
        if (keyword) {
          const filterResult = [];
          users.forEach((user) => {
            if (user.hasOwnProperty('children')) {
              const children = user.children.filter((child) => isMatch(child, keyword));
              if (children.length) {
                filterResult.push({
                  ...user,
                  children,
                });
              }
            } else if (isMatch(user, keyword)) {
              filterResult.push(user);
            }
          });
          users = filterResult;
        }
        return Promise.resolve({ results: users, next: false });
      };
      const filterUsers = (users) => {
        const matched = [];
        const flattened = [];
        users.forEach((user) => {
          if (user.hasOwnProperty('children')) {
            const children = user.children.filter(
              (child) => !flattened.some((flattenedUser) => flattenedUser.username === child.username),
            );
            // 用副本而不是改写入参，defaultAlternate 传进来的数组不应被组件修改
            if (multiple.value) {
              const unexistUser = children.filter((child) => !localValue.value.includes(child.username));
              if (unexistUser.length) {
                matched.push({ ...user, children: unexistUser });
                flattened.push(...unexistUser);
              }
            } else if (children.length) {
              matched.push({ ...user, children });
              flattened.push(...children);
            }
            return;
          }
          const exist = localValue.value.includes(user.username);
          const repeat = flattened.some((flattenedUser) => flattenedUser.username === user.username);
          if ((!multiple.value || !exist) && !repeat) {
            matched.push(user);
            flattened.push(user);
          }
        });
        return {
          matched,
          flattened,
        };
      };
      const runFuzzySearch = (value, next) => {
        if (!fuzzySearchMethod.value) {
          console.warn('No fuzzy search method has been set');
          return Promise.resolve({ next: false, results: [] });
        }
        return fuzzySearchMethod.value(value, next);
      };
      const getUserTips = async (instance, username) => {
        try {
          // 用 textContent 而非 innerHTML，避免用户名/组织名里的标签被当成 HTML 执行
          const contentElement = document.createElement('span');
          if (typeof tagTipsContent.value === 'function') {
            contentElement.textContent = await tagTipsContent.value(username);
          } else {
            const user = exactSearchMethod.value ? await exactSearchMethod.value(username) : null;
            contentElement.textContent = user ? user.category_name : 'Non existing user';
          }
          instance.setContent(contentElement);
        } catch (e) {
          console.error(e);
          instance.setContent(e.message);
        }
      };
      const getPopoverInstance = () => {
        if (!popoverInstance.value) {
          popoverInstance.value = Tippy(inputRef.value, {
            theme: 'light user-selector-popover',
            appendTo: document.body,
            trigger: 'manual',
            placement: 'bottom-start',
            offset: [0, 5],
            arrow: false,
            hideOnClick: false,
            content: '',
            interactive: true,
            onHide: () => {
              handlePopoverHide();
            },
            onShow: () => isFocus.value,
          });
        }
        return popoverInstance.value;
      };
      const getAlternateContent = () => {
        if (alternateContent.value) {
          return;
        }
        alternateContentApp = createApp(AlternateList);
        alternateContent.value = alternateContentApp.mount(document.createElement('div'));
        alternateContent.value.selector = proxy;
      };
      const getHistoryUsers = () => {
        try {
          if (historyKey.value) {
            const users = JSON.parse(window.localStorage.getItem(historyKey.value)) || [];
            return users.filter((user) => !disabledUsers.value.includes(user.username));
          }
          throw new Error('History key not provide');
        } catch (e) {
          console.error(e);
          return [];
        }
      };
      const updateHistoryUsers = (user) => {
        if (historyKey.value) {
          try {
            const histories = getHistoryUsers();
            const exist = histories.findIndex((history) => history.username === user.username);
            if (exist > -1) {
              histories.splice(exist, 1);
            }
            Array.isArray(user) ? histories.unshift(...user) : histories.unshift(user);
            const newHistories = histories
              .filter((history) => !disabledUsers.value.includes(history.username))
              .slice(0, historyRecord.value);
            window.localStorage.setItem(historyKey.value, JSON.stringify(newHistories));
          } catch (e) {
            console.error(e);
          }
        }
      };
      const updatePopover = () => {
        popoverInstance.value?.popperInstance?.update();
      };
      const showPopover = () => {
        updatePopover();
        popoverInstance.value?.show(0);
      };
      const hidePopover = () => {
        popoverInstance.value?.hide(0);
      };
      const handlePopoverHide = () => {
        nextTick(() => {
          matchedUsers.value = [];
          flattenedUsers.value = [];
          if (alternateContent.value) {
            alternateContent.value.matchedUsers = [];
          }
        });
      };
      const getDisplayText = (user) => {
        const isObject = typeof user === 'object';
        let displayText = isObject ? user.username : user;
        displayText = displayDomain.value ? displayText : displayText.replace(/@.*/, '');
        if (isObject && user.display_name) {
          displayText += `(${user.display_name})`;
        }
        return displayText;
      };
      const focus = () => {
        if (disabled.value) {
          return false;
        }
        clearOverflowTimer();
        inputIndex.value = localValue.value.length;
        if (!multiple.value && localValue.value.length) {
          inputValue.value = getDisplayText(localValue.value[0]);
          inputRef.value.innerHTML = inputValue.value;
          moveInput(0, { selectRange: true });
        } else {
          moveInput(0);
        }
      };
      const handleContainerScroll = (event) => {
        popoverInstance.value?.state.isVisible && event.preventDefault();
      };
      const handleSelectedMousedown = (_event, _index) => {
        if (disabled.value) {
          return false;
        }
        shouldUpdate.value = false;
      };
      const handleSelectedMouseup = (event, index) => {
        if (disabled.value) {
          return false;
        }
        if (multiple.value) {
          const $referenceTarget = event.target;
          const { offsetWidth } = $referenceTarget;
          const eventX = event.offsetX;
          inputIndex.value = eventX > offsetWidth / 2 ? index + 1 : index;
          moveInput(0);
        } else {
          inputValue.value = getDisplayText(localValue.value[0]);
          inputRef.value.innerHTML = inputValue.value;
          moveInput(0, { selectRange: true });
        }
      };
      const handleSelectedMouseenter = (event, { username }) => {
        if (!displayTagTips.value) {
          return false;
        }
        const target = event.currentTarget;
        if (target._user_tips_) {
          return false;
        }
        selectedTipsTimer.value[username] = setTimeout(() => {
          const instance = Tippy(target, {
            theme: 'light small-arrow user-selected-tips',
            offset: [0, 5],
            appendTo: document.body,
            arrow: true,
            content: 'loading...',
            placement: 'top',
            interactive: true,
            onShow: (tippyInstance) => {
              getUserTips(tippyInstance, username);
            },
          });
          target._user_tips_ = instance;
          tagTipsInstances.push(instance);
          instance.show();
          delete selectedTipsTimer.value[username];
        }, tagTipsDelay.value);
      };
      const handleSelectedMouseleave = (event, { username }) => {
        if (displayTagTips.value) {
          selectedTipsTimer.value[username] && clearTimeout(selectedTipsTimer.value[username]);
        }
      };
      const handleRemoveMouseDown = () => {
        shouldUpdate.value = false;
      };
      const handleRemoveSelected = ({ username }, index) => {
        if (disabled.value) {
          return false;
        }
        const lv = [...localValue.value];
        lv.splice(index, 1);
        localValue.value = lv;
        reset();
        if (isFocus.value) {
          moveInput(index >= inputIndex.value ? 0 : -1);
        } else {
          handleBlur();
        }
        ctx.emit('remove-selected', username);
      };
      const handleUserMousedown = (_user, _disabled) => {
        shouldUpdate.value = false;
      };
      const handleUserMouseup = (user, isUserDisabled) => {
        if (isUserDisabled || disabled.value) {
          moveInput(0);
          return false;
        }
        updateHistoryUsers(user);
        currentUsers.value.push(user);
        if (multiple.value) {
          const lv = [...localValue.value];
          lv.splice(inputIndex.value, 0, user.username);
          localValue.value = lv;
          setTimeout(() => {
            moveInput(1);
            setSelection({ reset: true });
            search();
          }, 0);
        } else {
          localValue.value = [user.username];
          reset();
          handleBlur();
        }
        ctx.emit('select-user', user);
      };
      const handleGroupMousedown = () => {
        shouldUpdate.value = false;
      };
      const handleGroupMouseup = () => {
        moveInput(0);
      };

      const setSelection = (option = {}) => {
        if (option.reset) {
          reset();
        }
        isFocus.value = true;
        shouldUpdate.value = true;
        nextTick(() => {
          const $input = inputRef.value;
          if (!$input) {
            return;
          }
          $input.focus();
          const range = window.getSelection();
          range.selectAllChildren($input);
          !option.selectRange && range.collapseToEnd();
        });
      };
      const handleKeydown = (event) => {
        if (loading.value) {
          event.preventDefault();
          event.stopPropagation();
          return;
        }
        const { key } = event;
        const keyMap = {
          Enter: handleEnter,
          Backspace: handleBackspace,
          Delete: handleBackspace,
          ArrowLeft: handleArrow,
          ArrowRight: handleArrow,
          ArrowUp: handleArrow,
          ArrowDown: handleArrow,
        };
        if (keyMap.hasOwnProperty(key)) {
          keyMap[key](event);
        }
        ctx.emit('keydown', event);
      };
      const handleEnter = (e) => {
        e.preventDefault();
        e.stopPropagation();
        shouldUpdate.value = false;
        if (highlightIndex.value !== -1) {
          const { username } = flattenedUsers.value[highlightIndex.value];
          if (disabledUsers.value.includes(username)) {
            return false;
          }
          if (multiple.value) {
            const lv = [...localValue.value];
            lv.splice(inputIndex.value, 0, username);
            localValue.value = lv;
            moveInput(1, { reset: true });
          } else {
            localValue.value = [username];
            reset();
            handleBlur();
          }
        } else if (inputValue.value) {
          if (!exclude.value && !localValue.value.includes(inputValue.value)) {
            if (multiple.value) {
              const lv = [...localValue.value];
              lv.splice(inputIndex.value, 0, inputValue.value);
              localValue.value = lv;
              moveInput(1, { reset: true });
            } else {
              localValue.value = [inputValue.value];
              reset();
              handleBlur();
            }
          } else {
            reset();
          }
        } else {
          reset();
          handleBlur();
        }
        hidePopover();
      };
      const handleBackspace = (_event) => {
        if (inputValue.value || !localValue.value.length || !inputIndex.value) {
          return true;
        }
        shouldUpdate.value = false;
        const lv = [...localValue.value];
        lv.splice(inputIndex.value - 1, 1);
        localValue.value = lv;
        moveInput(-1);
        search();
      };
      const handleArrow = (event) => {
        const arrow = event.key;
        if (['ArrowLeft', 'ArrowRight'].includes(arrow)) {
          if (inputValue.value || !localValue.value.length) {
            return true;
          }
          if (arrow === 'ArrowLeft' && inputIndex.value !== 0) {
            moveInput(-1);
          } else if (arrow === 'ArrowRight' && inputIndex.value !== localValue.value.length) {
            moveInput(1);
          }
        } else if (flattenedUsers.value.length) {
          event.preventDefault();
          if (arrow === 'ArrowDown') {
            if (highlightIndex.value < flattenedUsers.value.length - 1) {
              highlightIndex.value += 1;
            } else if (alternateContent.value.next) {
              alternateContent.value.$refs.alternateList.scrollTop += 32;
              alternateContent.value.handleScroll();
            } else {
              highlightIndex.value = 0;
            }
          } else if (arrow === 'ArrowUp' && highlightIndex.value !== -1) {
            highlightIndex.value -= 1;
          }
        }
      };
      const handleInput = (event) => {
        if (loading.value) {
          event.preventDefault();
          event.stopPropagation();
          return;
        }
        inputValue.value = inputRef.value.textContent.trim();
      };
      const handleBlur = () => {
        if (!shouldUpdate.value) {
          return true;
        }
        isFocus.value = false;
        hidePopover();
      };
      const getMatchedUser = (nameToMatch) => {
        const user = flattenedUsers.value.find((user) => {
          const enName = user.username;
          const cnName = user.display_name;
          const isMatch = [enName, cnName].some((name) => name.toLowerCase() === nameToMatch.toLowerCase());
          const isSelected = localValue.value.includes(enName);
          return isMatch && !isSelected;
        });
        return user;
      };
      const handlePaste = async (event) => {
        hidePopover();
        if (loading.value) {
          event.preventDefault();
          event.stopPropagation();
          return;
        }
        if (!pasteValidator.value) {
          console.warn('No paste validator has been set');
          return;
        }
        try {
          loading.value = true;
          const pasteStr = event.clipboardData.getData('text').replace(/[^\S\r\n]/g, '');
          const values = pasteStr
            .split(/\s*[｜|，,；;、\t/\s]\s*/g)
            .map((value) => pasteFormatter.value(value))
            .filter((value) => value.length);
          const uniqueValues = [...new Set(values)];
          if (!uniqueValues.length) {
            return;
          }
          const validValues = await pasteValidator.value(uniqueValues);

          const newValues = validValues.filter((value) => !localValue.value.includes(value));
          if (!validValues.length) {
            return;
          }
          let lv = [...localValue.value];
          if (props.multiple) {
            lv.splice(inputIndex.value, 0, ...newValues);
          } else {
            if (newValues.length > 0) {
              lv = [newValues[0]];
            }
          }
          localValue.value = lv;
          if (multiple.value) {
            isFocus.value && moveInput(newValues.length, { reset: true });
          } else {
            handleBlur();
          }
        } catch (error) {
          console.error(error);
        } finally {
          loading.value = false;
        }
      };

      const getSelectedDOM = () => Array.from(containerRef.value.querySelectorAll('.user-selector-selected'));

      const moveInput = (step, option = {}) => {
        inputIndex.value = inputIndex.value + step;
        nextTick(() => {
          const selected = getSelectedDOM();
          const $referenceTarget = selected[inputIndex.value] || null;
          if (props.multiple) {
            containerRef.value.insertBefore(inputRef.value, $referenceTarget);
          }
          setSelection(option);
          updatePopover();
        });
      };
      const updateScroller = () => {
        if (!alternateContent.value || !isSelector.value) {
          return false;
        }
        nextTick(() => {
          const { highlightIndex } = proxy;
          const $alternateList = alternateContent.value?.$refs.alternateList;
          if (!$alternateList) {
            return false;
          }
          if (highlightIndex !== -1) {
            const $alternateItem = alternateContent.value.alternateItem[highlightIndex]?.$el;
            if (!$alternateItem) {
              return false;
            }
            const listClientHeight = $alternateList.clientHeight;
            const listScrollTop = $alternateList.scrollTop;
            const itemOffsetTop = $alternateItem.offsetTop;
            const itemOffsetHeight = $alternateItem.offsetHeight;
            if (
              itemOffsetTop >= listScrollTop &&
              itemOffsetTop + itemOffsetHeight <= listScrollTop + listClientHeight
            ) {
              return false;
            }
            if (itemOffsetTop <= listScrollTop) {
              $alternateList.scrollTop = itemOffsetTop;
            } else if (itemOffsetTop + itemOffsetHeight > listScrollTop + listClientHeight) {
              $alternateList.scrollTop = itemOffsetTop + itemOffsetHeight - listClientHeight;
            }
          } else {
            $alternateList.scrollTop = 0;
          }
        });
      };
      const overflowTimer = ref(0);
      const calcOverflow = () => {
        if (!isSelector.value) {
          return false;
        }

        removeOverflowTagNode();

        if (!fixedHeight.value || isFocus.value || localValue.value.length < 2) {
          return false;
        }
        clearOverflowTimer();
        overflowTimer.value = setTimeout(() => {
          const selectedUsers = getSelectedDOM();
          const userIndexInSecondRow = selectedUsers.findIndex((currentUser, index) => {
            if (!index) {
              return false;
            }
            const previousUser = selectedUsers[index - 1];
            return previousUser.offsetTop !== currentUser.offsetTop;
          });
          if (userIndexInSecondRow > -1) {
            overflowTagIndex.value = userIndexInSecondRow;
          } else {
            overflowTagIndex.value = null;
          }
          containerRef.value.scrollTop = 0;
          insertOverflowTag();
        }, 0);
      };
      const clearOverflowTimer = () => {
        overflowTimer.value && clearTimeout(overflowTimer.value);
      };
      const insertOverflowTag = () => {
        if (!overflowTagIndex.value) {
          return;
        }
        getOverflowTagNode();

        const selectedUser = getSelectedDOM();
        const referenceUser = selectedUser[overflowTagIndex.value];
        if (referenceUser) {
          overflowTagNode.value.textContent = `+${localValue.value.length - overflowTagIndex.value}`;
          containerRef.value.insertBefore(overflowTagNode.value, referenceUser);
        } else {
          overflowTagIndex.value = null;
          return;
        }
        setTimeout(() => {
          const previousUser = selectedUser[overflowTagIndex.value - 1];
          if (overflowTagNode.value.offsetTop !== previousUser.offsetTop) {
            overflowTagIndex.value -= 1;
            containerRef.value.insertBefore(overflowTagNode.value, overflowTagNode.value.previousSibling);
            overflowTagNode.value.textContent = `+${localValue.value.length - overflowTagIndex.value}`;
          }
        }, 0);
      };
      const getOverflowTagNode = () => {
        if (overflowTagNode.value) {
          return overflowTagNode.value;
        }
        const node = document.createElement('span');
        node.className = 'user-selector-overflow-tag';
        overflowTagNode.value = node;
      };
      const removeOverflowTagNode = () => {
        if (overflowTagNode.value && overflowTagNode.value.parentNode === containerRef.value) {
          containerRef.value.removeChild(overflowTagNode.value);
        }
      };
      const handleFastClear = () => {
        localValue.value = [];
        ctx.emit('clear');
      };
      const reset = () => {
        shouldUpdate.value = true;
        highlightIndex.value = -1;
        inputValue.value = '';
        inputRef.value.innerHTML = '';
      };
      const isSameValue = (source, target) =>
        source.length === target.length && source.every((username, index) => username === target[index]);

      watch(inputValue, (value) => {
        if (value.length) {
          highlightIndex.value = -1;
          updateScroller();
          scheduleSearch(value);
        } else if (isFocus.value) {
          search();
        }
      });
      watch(isFocus, (isFocus) => {
        if (isFocus) {
          search();
          ctx.emit('focus');
        } else {
          reset();
          ctx.emit('blur');
        }
        calcOverflow();
      });
      watch(highlightIndex, () => {
        updateScroller();
      });

      // 外部回写与本地选择内容一致时不再同步，否则会二次触发 localValue，导致 change 与用户信息请求各发两次
      watch(modelValue, () => {
        if (isSameValue(modelValue.value, localValue.value)) {
          return;
        }
        isIgnoreUpdateModelValue = true;
        localValue.value = [...modelValue.value];
      });

      watch(localValue, (_localValue) => {
        if (isIgnoreUpdateModelValue) {
          isIgnoreUpdateModelValue = false;
        } else {
          ctx.emit('update:modelValue', _localValue);
        }
        ctx.emit('change', _localValue);
        calcOverflow();
        getCurrentUsers();
      });

      onMounted(() => {
        calcOverflow();
        getCurrentUsers();
      });

      onBeforeUnmount(() => {
        isUnmounted = true;
        scheduleSearch.cancel();
        clearOverflowTimer();
        Object.values(selectedTipsTimer.value).forEach((timer) => clearTimeout(timer));
        selectedTipsTimer.value = {};
        tagTipsInstances.forEach((instance) => instance.destroy());
        tagTipsInstances.length = 0;
        alternateContentApp?.unmount();
        alternateContentApp = null;
        alternateContent.value = null;
        popoverInstance.value?.destroy();
        popoverInstance.value = null;
      });

      return {
        selectorHeight,
        singleRowHeight,
        inputValue,
        inputIndex,
        highlightIndex,
        shouldUpdate,
        isFocus,
        overflowTagIndex,
        currentUsers,
        matchedUsers,
        flattenedUsers,
        scheduleSearch,
        popoverInstance,
        alternateContent,
        selectedTipsTimer,
        overflowTagNode,
        loading,
        isSelector,
        containerStyle,
        localValue,
        localValueUsers,
        userInfo,
        getCurrentUsers,
        search,
        getDefaultAlternateData,
        filterUsers,
        runFuzzySearch,
        getUserTips,
        getPopoverInstance,
        getAlternateContent,
        getHistoryUsers,
        updateHistoryUsers,
        updatePopover,
        showPopover,
        hidePopover,
        handlePopoverHide,
        getDisplayText,
        focus,
        handleContainerScroll,
        handleSelectedMousedown,
        handleSelectedMouseup,
        handleSelectedMouseenter,
        handleSelectedMouseleave,
        handleRemoveMouseDown,
        handleRemoveSelected,
        handleUserMousedown,
        handleUserMouseup,
        handleGroupMousedown,
        handleGroupMouseup,
        setSelection,
        handleKeydown,
        handleEnter,
        handleBackspace,
        handleArrow,
        handleInput,
        handleBlur,
        getMatchedUser,
        handlePaste,
        getSelectedDOM,
        moveInput,
        updateScroller,
        calcOverflow,
        clearOverflowTimer,
        insertOverflowTag,
        getOverflowTagNode,
        removeOverflowTagNode,
        handleFastClear,
        reset,
        containerRef,
        inputRef,
      };
    },
  });
</script>

<style lang="css">
  @import './style.css';
</style>
