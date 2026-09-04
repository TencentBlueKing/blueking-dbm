// @ts-nocheck
import { computed, defineComponent, toRefs, withModifiers } from 'vue';

import RenderAvatar from './render-avatar';
import RenderList from './render-list';
import tooltips from './tooltips';

export default defineComponent({
  name: 'AlternateItem',
  directives: {
    tooltips,
  },
  props: {
    selector: {
      type: Object,
    },
    user: {
      type: Object,
    },
    keyword: {
      type: String,
    },
    index: {
      type: Number,
    },
  },
  setup(props) {
    const { selector, user, keyword } = toRefs(props);
    const disabled = computed(() => selector.value.disabledUsers.includes(user.value.username));
    // 按子串切分做高亮，不走正则也不拼 HTML：既避免关键字里的正则元字符报错，也避免用户名被当成 HTML 执行
    const highlightKeyword = (text: string) => {
      if (!keyword.value) {
        return [text];
      }
      const nodes: unknown[] = [];
      text.split(keyword.value).forEach((segment, index) => {
        if (index > 0) {
          nodes.push(<span>{keyword.value}</span>);
        }
        nodes.push(segment);
      });
      return nodes;
    };
    const getItemContent = () => {
      const [nameWithoutDomain, domain] = user.value.username.split('@');
      const nodes = highlightKeyword(nameWithoutDomain);
      if (selector.value.displayDomain && domain) {
        nodes.push(`@${domain}`);
      }
      if (user.value.display_name) {
        nodes.push(`(${user.value.display_name})`);
      }
      return nodes;
    };
    const getTitle = () => selector.value.getDisplayText(user.value);

    return {
      disabled,
      getItemContent,
      getTitle,
    };
  },
  render() {
    return (
      <li
        class={[
          'alternate-item',
          this.index === this.selector.highlightIndex ? 'highlight' : '',
          this.disabled && !this.selector.renderList ? 'disabled' : '',
        ]}
        onClick={e => e.stopPropagation()}
        onMousedown={withModifiers(() => this.selector.handleUserMousedown(this.user, this.disabled), ['left', 'stop'])}
        onMouseup={withModifiers(() => this.selector.handleUserMouseup(this.user, this.disabled), ['left', 'stop'])}>
        {
          this.selector.renderList
            ? <>
              <RenderList
                selector={this.selector}
                keyword={this.keyword}
                user={this.user}
                disabled={this.disabled}
              >
              </RenderList>
            </>
            : <>
              {
                this.selector.tagType === 'avatar'
                  ? <>
                    <RenderAvatar
                      class="item-avatar"
                      user={this.user}
                      urlMethod={this.selector.avatarUrl}>
                    </RenderAvatar>
                  </>
                  : null
              }
              {
                this.selector.displayListTips && this.user.category_name
                  ? <>
                    <span
                      class="item-folder"
                      v-tooltips={{
                        placement: 'right',
                        interactive: true,
                        theme: 'light list-item-tips',
                        content: this.user.category_name,
                        offset: [0, 18],
                      }}>
                      { this.user.category_name }
                    </span>
                  </>
                  : null
              }
              <span
                class="item-name"
                title={this.getTitle()}>
                { this.getItemContent() }
              </span>
            </>
        }
      </li>
    );
  },
});
