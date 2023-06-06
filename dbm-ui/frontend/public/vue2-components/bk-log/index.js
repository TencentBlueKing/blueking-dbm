(function webpackUniversalModuleDefinition(root, factory) {
  if (typeof exports === 'object' && typeof module === 'object') module.exports = factory();
  else if (typeof define === 'function' && define.amd) define([], factory);
  else {
    const a = factory();
    for (const i in a) (typeof exports === 'object' ? exports : root)[i] = a[i];
  }
}(self, () =>
/******/ (() => { // webpackBootstrap
    /******/ 	const __webpack_modules__ = ({

      /***/ './node_modules/@blueking/log/dist/index.js':
      /*! **************************************************!*\
  !*** ./node_modules/@blueking/log/dist/index.js ***!
  \**************************************************/
      /***/ ((module) => {
        !(function (t, e) {
          true ? module.exports = e() : 0;
        }(window, (() => (function (t) {
          const e = {};function n(i) {
            if (e[i]) return e[i].exports;const r = e[i] = { i, l: !1, exports: {} };return t[i].call(r.exports, r, r.exports, n), r.l = !0, r.exports;
          } return n.m = t, n.c = e, n.d = function (t, e, i) {
            n.o(t, e) || Object.defineProperty(t, e, { enumerable: !0, get: i });
          }, n.r = function (t) {
            'undefined' !== typeof Symbol && Symbol.toStringTag && Object.defineProperty(t, Symbol.toStringTag, { value: 'Module' }), Object.defineProperty(t, '__esModule', { value: !0 });
          }, n.t = function (t, e) {
            if (1 & e && (t = n(t)), 8 & e) return t;if (4 & e && 'object' === typeof t && t && t.__esModule) return t;const i = Object.create(null);if (n.r(i), Object.defineProperty(i, 'default', { enumerable: !0, value: t }), 2 & e && 'string' !== typeof t) for (const r in t)n.d(i, r, (e => t[e]).bind(null, r));return i;
          }, n.n = function (t) {
            const e = t && t.__esModule ? function () {
              return t.default;
            } : function () {
              return t;
            };return n.d(e, 'a', e), e;
          }, n.o = function (t, e) {
            return Object.prototype.hasOwnProperty.call(t, e);
          }, n.p = '/', n(n.s = 101);
        }([function (t, e) {
          t.exports = function (t) {
            try {
              return !!t();
            } catch (t) {
              return !0;
            }
          };
        }, function (t, e, n) {
          (function (e) {
            const n = function (t) {
              return t && t.Math == Math && t;
            };t.exports = n('object' === typeof globalThis && globalThis) || n('object' === typeof window && window) || n('object' === typeof self && self) || n('object' === typeof e && e) || (function () {
              return this;
            }()) || Function('return this')();
          }).call(this, n(102));
        }, function (t, e, n) {
          const i = n(1); const r = n(39); const o = n(5); const A = n(69); const a = n(70); const s = n(106); const c = r('wks'); const l = i.Symbol; const u = s ? l : l && l.withoutSetter || A;t.exports = function (t) {
            return o(c, t) && (a || 'string' === typeof c[t]) || (a && o(l, t) ? c[t] = l[t] : c[t] = u(`Symbol.${t}`)), c[t];
          };
        }, function (t, e) {
          t.exports = function (t) {
            return 'object' === typeof t ? null !== t : 'function' === typeof t;
          };
        }, function (t, e, n) {
          const i = n(3);t.exports = function (t) {
            if (!i(t)) throw TypeError(`${String(t)} is not an object`);return t;
          };
        }, function (t, e, n) {
          const i = n(14); const r = {}.hasOwnProperty;t.exports = Object.hasOwn || function (t, e) {
            return r.call(i(t), e);
          };
        }, function (t, e, n) {
          'use strict';function i(t, e, n, i, r, o, A, a) {
            let s; const c = 'function' === typeof t ? t.options : t;if (e && (c.render = e, c.staticRenderFns = n, c._compiled = !0), i && (c.functional = !0), o && (c._scopeId = `data-v-${o}`), A ? (s = function (t) {
              (t = t || this.$vnode && this.$vnode.ssrContext || this.parent && this.parent.$vnode && this.parent.$vnode.ssrContext) || 'undefined' === typeof __VUE_SSR_CONTEXT__ || (t = __VUE_SSR_CONTEXT__), r && r.call(this, t), t && t._registeredComponents && t._registeredComponents.add(A);
            }, c._ssrRegister = s) : r && (s = a ? function () {
              r.call(this, (c.functional ? this.parent : this).$root.$options.shadowRoot);
            } : r), s) if (c.functional) {
              c._injectStyles = s;const l = c.render;c.render = function (t, e) {
                return s.call(e), l(t, e);
              };
            } else {
              const u = c.beforeCreate;c.beforeCreate = u ? [].concat(u, s) : [s];
            } return { exports: t, options: c };
          }n.d(e, 'a', (() => i));
        }, function (t, e) {
          t.exports = function (t) {
            return t && t.__esModule ? t : { default: t };
          }, t.exports.default = t.exports, t.exports.__esModule = !0;
        }, function (t, e, n) {
          const i = n(9); const r = n(10); const o = n(25);t.exports = i ? function (t, e, n) {
            return r.f(t, e, o(1, n));
          } : function (t, e, n) {
            return t[e] = n, t;
          };
        }, function (t, e, n) {
          const i = n(0);t.exports = !i((() => 7 != Object.defineProperty({}, 1, { get() {
 return 7; 
} })[1]));
        }, function (t, e, n) {
          const i = n(9); const r = n(67); const o = n(4); const A = n(24); const a = Object.defineProperty;e.f = i ? a : function (t, e, n) {
            if (o(t), e = A(e, !0), o(n), r) try {
              return a(t, e, n);
            } catch (t) {} if ('get' in n || 'set' in n) throw TypeError('Accessors not supported');return 'value' in n && (t[e] = n.value), t;
          };
        }, function (t, e) {
          t.exports = function (t) {
            if (null == t) throw TypeError(`Can't call method on ${t}`);return t;
          };
        }, function (t, e, n) {
          const i = n(1); const r = n(44).f; const o = n(8); const A = n(15); const a = n(42); const s = n(113); const c = n(50);t.exports = function (t, e) {
            let n; let l; let u; let g; let h; const f = t.target; const d = t.global; const p = t.stat;if (n = d ? i : p ? i[f] || a(f, {}) : (i[f] || {}).prototype) for (l in e) {
              if (g = e[l], u = t.noTargetGet ? (h = r(n, l)) && h.value : n[l], !c(d ? l : f + (p ? '.' : '#') + l, t.forced) && void 0 !== u) {
                if (typeof g === typeof u) continue;s(g, u);
              }(t.sham || u && u.sham) && o(g, 'sham', !0), A(n, l, g, t);
            }
          };
        }, function (t, e, n) {
          const i = n(20); const r = Math.min;t.exports = function (t) {
            return t > 0 ? r(i(t), 9007199254740991) : 0;
          };
        }, function (t, e, n) {
          const i = n(11);t.exports = function (t) {
            return Object(i(t));
          };
        }, function (t, e, n) {
          const i = n(1); const r = n(8); const o = n(5); const A = n(42); const a = n(74); const s = n(45); const c = s.get; const l = s.enforce; const u = String(String).split('String');(t.exports = function (t, e, n, a) {
            let s; const c = !!a && !!a.unsafe; let g = !!a && !!a.enumerable; const h = !!a && !!a.noTargetGet;'function' === typeof n && ('string' !== typeof e || o(n, 'name') || r(n, 'name', e), (s = l(n)).source || (s.source = u.join('string' === typeof e ? e : ''))), t !== i ? (c ? !h && t[e] && (g = !0) : delete t[e], g ? t[e] = n : r(t, e, n)) : g ? t[e] = n : A(e, n);
          })(Function.prototype, 'toString', (function () {
            return 'function' === typeof this && c(this).source || a(this);
          }));
        }, function (t, e, n) {
          'use strict';let i; const r = function () {
 return void 0 === i && (i = Boolean(window && document && document.all && !window.atob)), i; 
}; const o = (function () { var t = {};return function (e) { if (void 0 === t[e]) { var n = document.querySelector(e);if (window.HTMLIFrameElement && n instanceof window.HTMLIFrameElement) try { n = n.contentDocument.head } catch (t) { n = null }t[e] = n } return t[e] } }()); const A = [];function a(t) {
            for (var e = -1, n = 0;n < A.length;n++) if (A[n].identifier === t) {
              e = n;break;
            } return e;
          } function s(t, e) {
            for (var n = {}, i = [], r = 0;r < t.length;r++) {
              const o = t[r]; const s = e.base ? o[0] + e.base : o[0]; const c = n[s] || 0; const l = ''.concat(s, ' ').concat(c);n[s] = c + 1;const u = a(l); const g = { css: o[1], media: o[2], sourceMap: o[3] };-1 !== u ? (A[u].references++, A[u].updater(g)) : A.push({ identifier: l, updater: p(g, e), references: 1 }), i.push(l);
            } return i;
          } function c(t) {
            const e = document.createElement('style'); const i = t.attributes || {};if (void 0 === i.nonce) {
              const r = n.nc;r && (i.nonce = r);
            } if (Object.keys(i).forEach(((t) => {
              e.setAttribute(t, i[t]);
            })), 'function' === typeof t.insert)t.insert(e);else {
              const A = o(t.insert || 'head');if (!A) throw new Error('Couldn\'t find a style target. This probably means that the value for the \'insert\' parameter is invalid.');A.appendChild(e);
            } return e;
          } let l; const u = (l = [], function (t, e) {
            return l[t] = e, l.filter(Boolean).join('\n');
          });function g(t, e, n, i) {
            const r = n ? '' : i.media ? '@media '.concat(i.media, ' {').concat(i.css, '}') : i.css;if (t.styleSheet)t.styleSheet.cssText = u(e, r);else {
              const o = document.createTextNode(r); const A = t.childNodes;A[e] && t.removeChild(A[e]), A.length ? t.insertBefore(o, A[e]) : t.appendChild(o);
            }
          } function h(t, e, n) {
            let i = n.css; const r = n.media; const o = n.sourceMap;if (r ? t.setAttribute('media', r) : t.removeAttribute('media'), o && 'undefined' !== typeof btoa && (i += '\n/*# sourceMappingURL=data:application/json;base64,'.concat(btoa(unescape(encodeURIComponent(JSON.stringify(o)))), ' */')), t.styleSheet)t.styleSheet.cssText = i;else {
              for (;t.firstChild;)t.removeChild(t.firstChild);t.appendChild(document.createTextNode(i));
            }
          } let f = null; let d = 0;function p(t, e) {
            let n; let i; let r;if (e.singleton) {
              const o = d++;n = f || (f = c(e)), i = g.bind(null, n, o, !1), r = g.bind(null, n, o, !0);
            } else n = c(e), i = h.bind(null, n, e), r = function () {
              !(function (t) {
                if (null === t.parentNode) return !1;t.parentNode.removeChild(t);
              }(n));
            };return i(t), function (e) {
              if (e) {
                if (e.css === t.css && e.media === t.media && e.sourceMap === t.sourceMap) return;i(t = e);
              } else r();
            };
          }t.exports = function (t, e) {
            (e = e || {}).singleton || 'boolean' === typeof e.singleton || (e.singleton = r());let n = s(t = t || [], e);return function (t) {
              if (t = t || [], '[object Array]' === Object.prototype.toString.call(t)) {
                for (let i = 0;i < n.length;i++) {
                  const r = a(n[i]);A[r].references--;
                } for (var o = s(t, e), c = 0;c < n.length;c++) {
                  const l = a(n[c]);0 === A[l].references && (A[l].updater(), A.splice(l, 1));
                }n = o;
              }
            };
          };
        }, function (t, e, n) {
          'use strict';t.exports = function (t) {
            const e = [];return e.toString = function () {
              return this.map(((e) => {
                const n = (function (t, e) {
 let n = t[1] || ''; let i = t[3];if (!i) return n;if (e && 'function'===typeof btoa) {
 let r = (A = i, '/*# sourceMappingURL=data:application/json;charset=utf-8;base64,' + btoa(unescape(encodeURIComponent(JSON.stringify(A)))) + ' */'); let o = i.sources.map(((t) => "/*# sourceURL=" + i.sourceRoot + t + " */"));return [n].concat(o).concat([r])
                  .join('\n'); 
} let A;return [n].join('\n'); 
}(e, t));return e[2] ? `@media ${e[2]}{${n}}` : n;
              })).join('');
            }, e.i = function (t, n) {
              'string' === typeof t && (t = [[null, t, '']]);for (var i = {}, r = 0;r < this.length;r++) {
                const o = this[r][0];null != o && (i[o] = !0);
              } for (r = 0;r < t.length;r++) {
                const A = t[r];null != A[0] && i[A[0]] || (n && !A[2] ? A[2] = n : n && (A[2] = `(${A[2]}) and (${n})`), e.push(A));
              }
            }, e;
          };
        }, function (t, e, n) {
          const i = n(1); const r = n(63); const o = n(103); const A = n(8);for (const a in r) {
            const s = i[a]; const c = s && s.prototype;if (c && c.forEach !== o) try {
              A(c, 'forEach', o);
            } catch (t) {
              c.forEach = o;
            }
          }
        }, function (t, e) {
          const n = {}.toString;t.exports = function (t) {
            return n.call(t).slice(8, -1);
          };
        }, function (t, e) {
          const n = Math.ceil; const i = Math.floor;t.exports = function (t) {
            return isNaN(t = +t) ? 0 : (t > 0 ? i : n)(t);
          };
        }, function (t, e, n) {
          const i = n(38); const r = n(11);t.exports = function (t) {
            return i(r(t));
          };
        }, function (t, e, n) {
          'use strict';Object.defineProperty(e, '__esModule', { value: !0 }), e.default = void 0, n(87), n(18), n(55), n(91);const i = new class {
            constructor() {
              this.logData = {}, this.initSearchHook();
            }initLogHook(t) {
              Object.assign(this.logData, t);
            }initApiHook(t) {
              let e = arguments.length > 1 && void 0 !== arguments[1] ? arguments[1] : {}; const n = this.logData[t].apiHook;Object.keys(e).forEach(((t) => {
                let i = n[t];void 0 === i && (n[t] = i = {}), Object.assign(i, e[t]);
              }));
            }removeLogHook(t) {
              this.logData[t] = void 0;
            }initSearchHook() {
              let t = this;['changeExecute', 'showSearchLog', 'changeShowTime', 'changeSearchStr'].forEach(((e) => {
                t[e] = function (n) {
                  for (var i = arguments.length, r = new Array(i > 1 ? i - 1 : 0), o = 1;o < i;o++)r[o - 1] = arguments[o];const A = t.logData[n] || {};A[e] && A[e](...r);const a = A.apiHook || {};Object.keys(a).forEach(((t) => {
                    let n = a[t];n[e] && n[e](...r);
                  }));
                };
              }));
            }
          };e.default = i;
        }, function (t, e, n) {
          const i = n(19);t.exports = Array.isArray || function (t) {
            return 'Array' == i(t);
          };
        }, function (t, e, n) {
          const i = n(3);t.exports = function (t, e) {
            if (!i(t)) return t;let n; let r;if (e && 'function' === typeof(n = t.toString) && !i(r = n.call(t))) return r;if ('function' === typeof(n = t.valueOf) && !i(r = n.call(t))) return r;if (!e && 'function' === typeof(n = t.toString) && !i(r = n.call(t))) return r;throw TypeError('Can\'t convert object to primitive value');
          };
        }, function (t, e) {
          t.exports = function (t, e) {
            return { enumerable: !(1 & t), configurable: !(2 & t), writable: !(4 & t), value: e };
          };
        }, function (t, e, n) {
          const i = n(105); const r = n(1); const o = function (t) {
            return 'function' === typeof t ? t : void 0;
          };t.exports = function (t, e) {
            return arguments.length < 2 ? o(i[t]) || o(r[t]) : i[t] && i[t][e] || r[t] && r[t][e];
          };
        }, function (t, e, n) {
          'use strict';let i; let r; const o = n(53); const A = n(54); const a = n(39); const s = RegExp.prototype.exec; const c = a('native-string-replace', String.prototype.replace); let l = s; const u = (i = /a/, r = /b*/g, s.call(i, 'a'), s.call(r, 'a'), 0 !== i.lastIndex || 0 !== r.lastIndex); const g = A.UNSUPPORTED_Y || A.BROKEN_CARET; const h = void 0 !== /()??/.exec('')[1];(u || h || g) && (l = function (t) {
            let e; let n; let i; let r; const A = this; const a = g && A.sticky; let l = o.call(A); let f = A.source; let d = 0; let p = t;return a && (-1 === (l = l.replace('y', '')).indexOf('g') && (l += 'g'), p = String(t).slice(A.lastIndex), A.lastIndex > 0 && (!A.multiline || A.multiline && '\n' !== t[A.lastIndex - 1]) && (f = `(?: ${f})`, p = ` ${p}`, d++), n = new RegExp(`^(?:${f})`, l)), h && (n = new RegExp(`^${f}$(?!\\s)`, l)), u && (e = A.lastIndex), i = s.call(a ? n : A, p), a ? i ? (i.input = i.input.slice(d), i[0] = i[0].slice(d), i.index = A.lastIndex, A.lastIndex += i[0].length) : A.lastIndex = 0 : u && i && (A.lastIndex = A.global ? i.index + i[0].length : e), h && i && i.length > 1 && c.call(i[0], n, (function () {
              for (r = 1;r < arguments.length - 2;r++) void 0 === arguments[r] && (i[r] = void 0);
            })), i;
          }), t.exports = l;
        }, function (t, e, n) {
          'use strict';n.r(e);const i = n(29); const r = n.n(i);for (const o in i)['default'].indexOf(o) < 0 && (function (t) {
            n.d(e, t, (() => i[t]));
          }(o));e.default = r.a;
        }, function (t, e, n) {
          'use strict';const i = n(7);Object.defineProperty(e, '__esModule', { value: !0 }), e.default = void 0, n(18);const r = i(n(72)); const o = i(n(22)); const A = i(n(95)); const a = i(n(97)); const s = { name: 'bk-log', components: { logMain: r.default }, props: { searchId: { type: String, default: 'bk-log-search' }, extCls: String }, data: () => ({ worker: new A.default, dataWorker: new a.default }), created() {
            o.default.initLogHook({ [this.searchId]: { worker: this.worker, apiHook: {} } });
          }, mounted() {
            this.initAssistWorker(), this.initApiHook();
          }, beforeDestroy() {
            this.worker.terminate(), this.dataWorker.terminate();
          }, methods: { initApiHook() {
            let t = this; const e = ((o.default.logData[this.searchId] || {}).apiHook || {})['single-log'] || {};Object.keys(e).forEach(((n) => {
              let i = e[n];t[n] = i;
            }));
          }, initAssistWorker() {
            let t = new MessageChannel;this.dataWorker.postMessage({ type: 'init', dataPort: t.port1 }, [t.port1]), this.worker.postMessage({ type: 'initAssistWorker', dataPort: t.port2 }, [t.port2]), this.worker.postMessage({ type: 'initStatus', pluginList: ['single-log'] });
          }, tagChange(t) {
            this.$emit('tag-change', t);
          } } };e.default = s;
        }, function (t, e, n) {
          'use strict';n.r(e);const i = n(31); const r = n.n(i);for (const o in i)['default'].indexOf(o) < 0 && (function (t) {
            n.d(e, t, (() => i[t]));
          }(o));e.default = r.a;
        }, function (t, e, n) {
          'use strict';const i = n(7);Object.defineProperty(e, '__esModule', { value: !0 }), e.default = void 0, n(18);const r = i(n(110)); const o = i(n(22)); const A = { props: { id: String, worker: Worker, isMultiple: Boolean, searchId: String }, data: () => ({ curTag: '', tagList: [], tagOverFlow: !1, tagTransform: 0, maxDis: 0 }), computed: { showSubTag() {
            return this.tagList && this.tagList.length > 0 && this.$refs.scroll && this.$refs.scroll.hasCompleteInit;
          } }, watch: { showSubTag(t) {
            t && this.calSubWidth();
          } }, created() {
            o.default.initApiHook(this.searchId, { [this.id]: { setSubTag: this.setSubTag } });
          }, components: { logVirtualScroll: r.default }, methods: { transTag(t) {
            let e = this.tagTransform + t; const n = this.maxDis - 436;e >= 0 && (e = 0), e <= -n && (e = -n), this.tagTransform = e;
          }, setSubTag(t) {
            this.tagList = t, this.calSubWidth();
          }, calSubWidth() {
            let t = this;this.$nextTick((() => {
              let e = t.$refs.logTag;if (e) {
                let n = 0;e.forEach(((t) => {
                  n += t.offsetWidth + 32;
                })), t.tagOverFlow = n > 480, t.maxDis = n;
              }
            }));
          }, tagChange(t) {
            this.curTag !== t && (this.curTag = t, ((o.default.logData[this.searchId] || {}).apiHook || {})[this.id].changeExecute(), this.$emit('tag-change', t, this.id));
          } } };e.default = A;
        }, function (t, e, n) {
          'use strict';n.r(e);const i = n(33); const r = n.n(i);for (const o in i)['default'].indexOf(o) < 0 && (function (t) {
            n.d(e, t, (() => i[t]));
          }(o));e.default = r.a;
        }, function (t, e, n) {
          'use strict';const i = n(7);Object.defineProperty(e, '__esModule', { value: !0 }), e.default = void 0, n(111), n(116), n(79), n(125), n(129), n(131), n(133), n(87);const r = i(n(22)); const o = { filters: { timeFilter(t) {
            if (!t) return '';const e = new Date(t);return ''.concat(e.getFullYear(), '-').concat(String(e.getMonth() + 1).padStart(2, '0'), '-')
              .concat(String(e.getDate()).padStart(2, '0'), ' ')
              .concat(String(e.getHours()).padStart(2, '0'), ':')
              .concat(String(e.getMinutes()).padStart(2, '0'), ':')
              .concat(String(e.getSeconds()).padStart(2, '0'), ':')
              .concat(String(e.getMilliseconds()).padStart(3, '0'));
          } }, props: { itemHeight: { type: Number, default: 16 }, id: { required: !0, type: String }, worker: { type: Worker }, isMultiple: { type: Boolean, default: !1 }, searchId: String }, data: () => ({ ulHeight: 0, indexList: [], listData: [], totalHeight: 0, itemNumber: 0, totalNumber: 0, visHeight: 0, visWidth: 0, totalScrollHeight: 0, startMinMapMove: !1, tempVal: 0, minMapTop: 0, minNavTop: 0, navHeight: 0, mapHeight: 0, moveRate: 0, bottomScrollWidth: 1 / 0, bottomScrollDis: 0, indexWidth: 0, itemWidth: 0, isScrolling: !1, isBottomMove: !1, curHoverIndex: -1, hasCompleteInit: !1, errMessage: 'The log is empty', downPreDefault: !1, upPreDefault: !1, observer: {}, showTime: !1, searchStr: '', curSearchIndex: void 0, isCurSearch: !1 }), computed: { mainWidth() {
            return 89 * this.visWidth / 100 - this.indexWidth - 20;
          } }, created() {
            this.initHook();
          }, mounted() {
            this.setVisWidth(), this.initEvent(), this.initWorker();
          }, beforeDestroy() {
            document.removeEventListener('mousedown', this.clearSelection), document.removeEventListener('mousemove', this.minNavMove), document.removeEventListener('mouseup', this.moveEnd), window.removeEventListener('resize', this.resize), MutationObserver && this.observer.disconnect(), this.observer = {};
          }, methods: { initHook() {
            let t = this;r.default.initApiHook(this.searchId, { [this.id]: { changeExecute: this.resetData, showSearchLog: this.showSearchLog, changeShowTime(e) {
 return t.showTime = e; 
}, changeSearchStr(e) {
 return t.searchStr = e; 
}, addLogData: this.addLogData, handleApiErr: this.handleApiErr, scrollPageByIndex: this.scrollPageByIndex, setVisWidth: this.setVisWidth } });
          }, showSearchLog(t) {
            let e = t.index; const n = t.refId; const i = t.realIndex;this.isCurSearch = n === this.id, n === this.id && (this.curSearchIndex = i, (e -= 5) < 0 && (e = 0), this.$el.scrollIntoViewIfNeeded(), this.scrollPageByIndex(e));
          }, valuefilter(t) {
            for (var e = t.split(/<a[^>]+?href=["']?([^"']+)["']?[^>]*>([^<]+)<\/a>/gi), n = this.searchStr.replace(/\*|\.|\?|\+|\$|\^|\[|\]|\(|\)|\{|\}|\||\\|\//g, (t => '\\'.concat(t))), i = new RegExp('^'.concat(n, '$'), 'i'), r = function () {
                let t = arguments.length > 0 && void 0 !== arguments[0] ? arguments[0] : ''; let e = '\\s|<|>';'' !== n && (e += '|'.concat(n));const r = new RegExp(e, 'gi');return t.replace(r, (t => '<' === t ? '&lt;' : '>' === t ? '&gt;' : i.test(t) ? '<span class="search-str">'.concat(t, '</span>') : /\t/.test(t) ? '&nbsp;&nbsp;&nbsp;&nbsp;' : '&nbsp;'));
              }, o = '', A = 0;A < e.length;A += 3) if (void 0 !== e[A]) {
              let a = e[A]; const s = e[A + 1]; const c = e[A + 2];o += r(a), s && (o += '<a href=\''.concat(s, '\' target=\'_blank\'>').concat(r(c), '</a>'));
            } return `${o}<br class="selection-color">`; 
}, clearSelection() {
            window.getSelection().removeAllRanges();
          }, setVisWidth() {
            let t = document.querySelector('.id-'.concat(this.id));this.visWidth = t.offsetWidth;let e = t.parentElement.offsetHeight; const n = document.querySelector('.job-plugin-list-log');this.isMultiple && (e = (n.offsetHeight || 500) - 80), this.maxVisHeight = e;
          }, handleApiErr(t) {
            this.hasCompleteInit = !0, this.$bkMessage({ theme: 'error', message: t });
          }, resetData() {
            this.totalNumber = 0, this.hasCompleteInit = !1, this.indexList = [], this.listData = [], this.changeStatus(), this.worker.postMessage({ type: 'resetData', id: this.id });
          }, changeMinMap() {
            let t = event.offsetY - this.minMapTop - this.visHeight / 16; let e = this.minMapTop + 8 * t / (16 * (this.totalNumber - this.itemNumber)) * (this.mapHeight - this.visHeight / 8);e <= 0 || this.mapHeight <= this.visHeight / 8 ? e = 0 : e >= this.mapHeight - this.visHeight / 8 && (e = this.mapHeight - this.visHeight / 8), this.minMapTop = e, this.totalScrollHeight = this.minMapTop / (this.mapHeight - this.visHeight / 8) * (this.totalHeight - this.visHeight), this.minNavTop = this.minMapTop * (this.visHeight - this.navHeight) / (this.mapHeight - this.visHeight / 8), this.getListData(this.totalScrollHeight);
          }, foldListData(t, e) {
            if (e) {
              let n = { id: this.id, type: 'foldListData', startIndex: t };this.worker.postMessage(n);
            }
          }, changeStatus() {
            this.totalHeight = this.totalNumber * this.itemHeight;const t = this.totalHeight > this.maxVisHeight ? this.maxVisHeight : this.totalHeight;if (this.visHeight !== t) {
              this.visHeight = t;const e = window.devicePixelRatio || 1;this.$refs.minMap.width = this.visWidth / 10 * e, this.$refs.minMap.height = this.visHeight * e, this.$refs.minMap.getContext('2d').setTransform(e, 0, 0, e, 0, 0), this.$refs.minNav.width = this.visWidth / 100 * e, this.$refs.minNav.height = this.visHeight * e, this.$refs.minNav.getContext('2d').setTransform(e, 0, 0, e, 0, 0);
            } this.itemNumber = this.totalHeight > this.visHeight ? Math.ceil(this.visHeight / this.itemHeight) : this.totalNumber, this.ulHeight = this.totalHeight > 4e5 ? 1e6 : this.totalHeight;const n = this.visHeight / this.totalHeight; const i = n * this.visHeight;this.navHeight = n > 1 ? this.visHeight : i < 20 ? 20 : i;const r = this.totalNumber * this.itemHeight / 8;this.mapHeight = r < this.visHeight ? r : this.visHeight;
          }, initEvent() {
            document.addEventListener('mousedown', this.clearSelection), document.addEventListener('mousemove', this.minNavMove), document.addEventListener('mouseup', this.moveEnd), window.addEventListener('resize', this.resize), MutationObserver && (this.observer = new MutationObserver(this.resize), this.observer.observe(this.$el, { attributes: !0, attributeFilter: ['style'] }));
          }, resize(t) {
            let e = this;this.slowExec((() => {
              let t = e.visHeight;e.setVisWidth(), e.changeStatus(), e.minMapTop = e.visHeight / t * e.minMapTop, e.minNavTop = e.minMapTop * (e.visHeight - e.navHeight) / (e.mapHeight - e.visHeight / 8), e.totalScrollHeight = e.minMapTop / (e.mapHeight - e.visHeight / 8) * (e.totalHeight - e.visHeight), e.getListData();
            }));
          }, handleWheel(t) {
            let e = t.target.classList; const n = Math.max(-1, Math.min(1, t.wheelDeltaY || -t.detail));if (!(n < 0 ? this.downPreDefault : this.upPreDefault) || e && e.contains('no-scroll') || t.preventDefault(), !(this.isScrolling || e && e.contains('no-scroll') || this.itemHeight * this.totalNumber <= this.visHeight)) {
              let i = 0;t.wheelDelta && (i = -.2 * t.wheelDelta), t.detail && (i = t.detail);let r = -2 * n;0 === n && (i = 0, r = 0);const o = this.minMapTop + (i + r) * (this.mapHeight - this.visHeight / 8) / (this.totalHeight - this.itemHeight * this.itemNumber); let A = 0; let a = 0; let s = 0;o < 0 ? (A = 0, a = 0, s = 0) : o >= 0 && o <= this.mapHeight - this.visHeight / 8 ? (A = o * (this.totalHeight - this.itemHeight * this.itemNumber) / (this.mapHeight - this.visHeight / 8), a = o, s = this.minNavTop + (i + r) * (this.visHeight - this.navHeight) / (this.totalHeight - this.itemHeight * this.itemNumber)) : (A = this.totalHeight - this.visHeight, a = this.mapHeight - this.visHeight / 8, s = this.visHeight - this.navHeight), this.minMapTop = a, this.minNavTop = s, this.getListData(A), this.isScrolling = !0;
            }
          }, scrollPageByIndex(t) {
            let e = this.itemHeight * t;e <= 0 ? e = 0 : e >= this.totalHeight - this.visHeight && (e = this.totalHeight - this.visHeight), this.totalHeight <= this.visHeight && (e = 0);const n = this.totalHeight - this.visHeight || 1;this.minMapTop = e / n * (this.mapHeight - this.visHeight / 8), this.minNavTop = e / n * (this.visHeight - this.navHeight), this.getListData(e);
          }, getListData() {
            let t = arguments.length > 0 && void 0 !== arguments[0] ? arguments[0] : this.totalScrollHeight; const e = { type: arguments.length > 2 && void 0 !== arguments[2] ? arguments[2] : 'wheelGetData', totalScrollHeight: t, isResize: arguments.length > 1 && void 0 !== arguments[1] && arguments[1], totalHeight: this.totalHeight, itemHeight: this.itemHeight, itemNumber: this.itemNumber, canvasHeight: this.visHeight, canvasWidth: this.visWidth / 10, minMapTop: this.minMapTop, mapHeight: this.mapHeight, id: this.id };this.worker.postMessage(e);
          }, initWorker() {
            let t = this;this.worker.addEventListener('message', ((e) => {
              let n = e.data;if (n.id === t.id) switch (n.type) {
                case 'completeAdd':t.hasCompleteInit = !0;var i = t.indexList[t.indexList.length - 1] || { listIndex: 0 };t.totalNumber - i.listIndex <= 3 ? t.freshDataScrollBottom(n) : t.freshDataNoScroll(n), t.indexWidth = 7 * (Math.log10(t.totalNumber || 1) + 1);break;case 'wheelGetData':t.drawList(n), t.JudgeScrollDefault();break;case 'completeFold':t.freshDataNoScroll(n);
              }
            }));
          }, JudgeScrollDefault() {
            let t = this.indexList[0] || {}; const e = this.indexList[this.indexList.length - 1] || {};this.downPreDefault = e.listIndex + 1 < this.totalNumber, this.upPreDefault = t.listIndex > 0;
          }, freshDataScrollBottom(t) {
            this.totalNumber = t.number, this.changeStatus(), this.scrollPageByIndex(this.totalNumber - this.itemNumber + 1);
          }, freshDataNoScroll(t) {
            let e = this.totalNumber; const n = this.itemNumber; const i = this.mapHeight; const r = this.visHeight;this.totalNumber = t.number, this.changeStatus(), this.getNumberChangeList({ oldNumber: e, oldItemNumber: n, oldMapHeight: i, oldVisHeight: r });
          }, getNumberChangeList(t) {
            let e = t.oldNumber; const n = t.oldItemNumber; const i = t.oldMapHeight; const r = t.oldVisHeight; let o = this.minMapTop * (this.mapHeight - this.visHeight / 8) * (e - n) / (i - r / 8 || 1) / (this.totalNumber - this.itemNumber || 1); let A = o / (this.mapHeight - this.visHeight / 8 || 1) * (this.totalHeight - this.visHeight);o <= 0 ? (o = 0, A = 0) : o > this.mapHeight - this.visHeight / 8 && (o = this.mapHeight - this.visHeight / 8, A = this.totalHeight - this.visHeight), this.minMapTop = o, this.minNavTop = this.minMapTop * (this.visHeight - this.navHeight) / (this.mapHeight - this.visHeight / 8 || 1), this.getListData(A);
          }, drawList(t) {
            Object.assign(this, t);const e = t.minMapList || []; const n = this.$refs.minMap.getContext('2d');n.clearRect(0, 0, this.visWidth / 10, this.visHeight);for (let i = 0;i < e.length;i++) {
              let r = e[i]; const o = r.color || 'rgba(255,255,255,1)';r.color ? n.font = 'normal normal bold 2px Consolas' : n.font = 'normal normal normal 2px Consolas', n.fillStyle = o, n.fillText(r.message, 5, 2 * (i + 1));
            } this.isScrolling = !1;
          }, addLogData(t) {
            let e = { type: 'addListData', list: t, mainWidth: this.mainWidth, id: this.id };this.worker.postMessage(e);
          }, startBottomMove(t) {
            this.tempVal = t.screenX, this.startMinMapMove = !0, this.isBottomMove = !0;
          }, startNavMove(t) {
            this.moveRate = t, this.tempVal = event.screenY, this.startMinMapMove = !0;
          }, minNavMove() {
            let t = this;if (this.startMinMapMove) if (this.isBottomMove) {
              let e = event.screenX - this.tempVal; let n = this.bottomScrollDis + e;n <= 0 && (n = 0), n + this.bottomScrollWidth >= this.mainWidth && (n = this.mainWidth - this.bottomScrollWidth), this.bottomScrollDis = n, this.tempVal = event.screenX;
            } else {
              let i = event.screenY - this.tempVal; let r = this.minMapTop + i / this.moveRate * (this.mapHeight - this.visHeight / 8);r <= 0 && (r = 0), r >= this.mapHeight - this.visHeight / 8 && (r = this.mapHeight - this.visHeight / 8);const o = r / (this.mapHeight - this.visHeight / 8) * (this.totalHeight - this.visHeight);this.tempVal = event.screenY, this.minMapTop = r, this.minNavTop = r * (this.visHeight - this.navHeight) / (this.mapHeight - this.visHeight / 8), this.slowExec((() => {
                t.getListData(o);
              }));
            }
          }, slowExec(t) {
            let e = +new Date;e - (this.slowExec.lastTime || 0) >= 100 && (this.slowExec.lastTime = e, t()), window.clearTimeout(this.slowExec.timeId), this.slowExec.timeId = window.setTimeout((() => {
              t();
            }), 50);
          }, moveEnd() {
            event.preventDefault(), this.startMinMapMove = !1, this.isBottomMove = !1;
          } } };e.default = o;
        }, function (t, e, n) {
          'use strict';n.r(e);const i = n(35); const r = n.n(i);for (const o in i)['default'].indexOf(o) < 0 && (function (t) {
            n.d(e, t, (() => i[t]));
          }(o));e.default = r.a;
        }, function (t, e, n) {
          'use strict';const i = n(7);Object.defineProperty(e, '__esModule', { value: !0 }), e.default = void 0, n(148), n(55), n(91), n(149), n(150), n(18);const r = i(n(151)); const o = i(n(72)); const A = i(n(22)); const a = i(n(95)); const s = i(n(97)); const c = { name: 'bk-multiple-log', components: { logMain: o.default }, props: { logList: { type: Array }, searchId: { type: String, default: 'bk-log-search' }, extCls: String }, data: () => ({ curFoldList: {}, worker: new a.default, dataWorker: new s.default }), created() {
            A.default.initLogHook({ [this.searchId]: { worker: this.worker, changeExecute: this.changeExecute, showSearchLog: this.showSearchLog, apiHook: {} } });
          }, mounted() {
            this.initAssistWorker(), this.initApiHook();
          }, beforeDestroy() {
            this.worker.terminate(), this.dataWorker.terminate();
          }, methods: { initApiHook() {
            let t = this; const e = (A.default.logData[this.searchId] || {}).apiHook || {};['changeExecute', 'showSearchLog', 'changeShowTime', 'changeSearchStr', 'addLogData', 'handleApiErr', 'scrollPageByIndex', 'setSubTag'].forEach(((n) => {
              t[n] = function () {
                let t = [...arguments].reverse(); const i = (0, r.default)(t); const o = i[0]; const A = i.slice(1); const a = e[o] || {}; const s = a[n];s(...A);
              };
            }));
          }, initAssistWorker() {
            let t = new MessageChannel;this.dataWorker.postMessage({ type: 'init', dataPort: t.port1 }, [t.port1]), this.worker.postMessage({ type: 'initAssistWorker', dataPort: t.port2 }, [t.port2]), this.worker.postMessage({ type: 'initStatus', pluginList: this.logList.map((t => t.id)) });
          }, showSearchLog(t) {
            let e = t.refId;this.curFoldList[e] || (this.curFoldList[e] = !0);
          }, changeExecute() {
            this.foldAllPlugin();
          }, foldAllPlugin() {
            let t = this;Object.keys(this.curFoldList).forEach((e => t.curFoldList[e] = !1));
          }, expendLog(t) {
            let e = this; const n = t.id;this.$set(this.curFoldList, [n], !this.curFoldList[n]), this.curFoldList[n] ? this.$nextTick((() => {
              (((A.default.logData[e.searchId] || {}).apiHook || {})[n] || {}).setVisWidth(), e.$emit('open-log', t);
            })) : this.$emit('close-log', t);
          }, tagChange() {
            for (var t = arguments.length, e = new Array(t), n = 0;n < t;n++)e[n] = arguments[n];this.$emit('tag-change', ...e);
          } } };e.default = c;
        }, function (t, e, n) {
          'use strict';n.r(e);const i = n(37); const r = n.n(i);for (const o in i)['default'].indexOf(o) < 0 && (function (t) {
            n.d(e, t, (() => i[t]));
          }(o));e.default = r.a;
        }, function (t, e, n) {
          'use strict';const i = n(7);Object.defineProperty(e, '__esModule', { value: !0 }), e.default = void 0, n(79);const r = i(n(22)); const o = { name: 'bk-log-search', props: { executeCount: { type: Number, default: 0 }, searchId: { type: String, default: 'bk-log-search' }, extCls: String }, data() {
            return { currentExe: this.executeCount, isSearching: !1, showMore: !1, searchIndex: 0, realSearchIndex: 0, searchNum: 0, searchRes: [], worker: {}, inputStr: '', showTime: !1, showList: !1 };
          }, mounted() {
            let t = this;this.worker = r.default.logData[this.searchId].worker, this.worker.addEventListener('message', ((e) => {
              let n = e.data;switch (n.type) {
                case 'completeSearch':t.handleSearch(n.num, n.curSearchRes, n.noScroll, n.realSearchIndex);break;case 'completeGetSearchRes':t.handleSearchRes(n.searchRes, n.realSearchIndex);
              }
            })), document.addEventListener('click', this.handleSearchClick);
          }, beforeDestroy() {
            document.removeEventListener('click', this.handleSearchClick);
          }, methods: { handleSearchClick(t) {
            let e = t.target.classList;e && e.contains('log-show-option') ? this.showList = !this.showList : this.showList = !1, e && e.contains('log-show-more') ? this.showMore = !this.showMore : this.closeShowMore();
          }, changeSearchIndex(t) {
            if (!(this.searchRes.length <= 0)) {
              let e = this.searchIndex + t;e <= 0 && (e = this.searchNum), e > this.searchNum && (e = 1), this.searchIndex = e, this.worker.postMessage({ type: 'changeSearchIndex', index: this.searchIndex - 1 }), (e = this.realSearchIndex + t) < 0 && (e = this.searchRes.length - 1), e >= this.searchRes.length && (e = 0), e >= 480 && e <= 520 && this.worker.postMessage({ type: 'getSearchRes', index: this.searchIndex - 1 }), this.realSearchIndex = e, this.showSearchLog();
            }
          }, showSearchLog() {
            let t = this.searchRes[this.realSearchIndex];t.isInFold ? this.worker.postMessage({ type: 'foldListData', index: this.searchIndex - 1, startIndex: t.startIndex, id: t.refId }) : r.default.showSearchLog(this.searchId, t);
          }, clearSearch() {
            (this.$refs.inputMain || {}).value = '', this.inputStr = '', r.default.changeSearchStr(this.searchId, ''), this.worker.postMessage({ type: 'search', val: '' });
          }, startSearch(t) {
            let e = this;this.isSearching = !0, window.clearTimeout(this.startSearch.timeId), this.startSearch.timeId = window.setTimeout((() => {
              e.searchIndex = 1, e.realSearchIndex = 0;const n = (t.target || {}).value;e.inputStr = n, r.default.changeSearchStr(e.searchId, n), e.worker.postMessage({ type: 'search', val: n });
            }), 300);
          }, handleSearchRes() {
            let t = arguments.length > 0 && void 0 !== arguments[0] ? arguments[0] : []; const e = arguments.length > 1 ? arguments[1] : void 0;this.searchRes = t, this.realSearchIndex = e;
          }, handleSearch() {
            let t = arguments.length > 0 && void 0 !== arguments[0] ? arguments[0] : 0; const e = arguments.length > 1 ? arguments[1] : void 0; const n = arguments.length > 2 ? arguments[2] : void 0; const i = arguments.length > 3 ? arguments[3] : void 0;this.searchRes = e, this.isSearching = !1, this.searchNum = t, this.realSearchIndex = i, t <= 0 && (this.searchIndex = 0), t <= 0 || n || this.showSearchLog();
          }, showLogTime() {
            this.closeShowMore(), this.showTime = !this.showTime, r.default.changeShowTime(this.searchId, this.showTime);
          }, closeShowMore() {
            this.showMore = !1;
          }, changeExecute(t) {
            this.currentExe !== t && (this.currentExe = t, r.default.changeExecute(this.searchId, t), this.$emit('change-execute', t), this.clearSearch());
          } } };e.default = o;
        }, function (t, e, n) {
          const i = n(0); const r = n(19); const o = ''.split;t.exports = i((() => !Object('z').propertyIsEnumerable(0))) ? function (t) {
            return 'String' == r(t) ? o.call(t, '') : Object(t);
          } : Object;
        }, function (t, e, n) {
          const i = n(40); const r = n(41);(t.exports = function (t, e) {
            return r[t] || (r[t] = void 0 !== e ? e : {});
          })('versions', []).push({ version: '3.13.1', mode: i ? 'pure' : 'global', copyright: '© 2021 Denis Pushkarev (zloirock.ru)' });
        }, function (t, e) {
          t.exports = !1;
        }, function (t, e, n) {
          const i = n(1); const r = n(42); const o = i['__core-js_shared__'] || r('__core-js_shared__', {});t.exports = o;
        }, function (t, e, n) {
          const i = n(1); const r = n(8);t.exports = function (t, e) {
            try {
              r(i, t, e);
            } catch (n) {
              i[t] = e;
            } return e;
          };
        }, function (t, e, n) {
          let i; let r; const o = n(1); const A = n(71); const a = o.process; const s = a && a.versions; const c = s && s.v8;c ? r = (i = c.split('.'))[0] < 4 ? 1 : i[0] + i[1] : A && (!(i = A.match(/Edge\/(\d+)/)) || i[1] >= 74) && (i = A.match(/Chrome\/(\d+)/)) && (r = i[1]), t.exports = r && +r;
        }, function (t, e, n) {
          const i = n(9); const r = n(73); const o = n(25); const A = n(21); const a = n(24); const s = n(5); const c = n(67); const l = Object.getOwnPropertyDescriptor;e.f = i ? l : function (t, e) {
            if (t = A(t), e = a(e, !0), c) try {
              return l(t, e);
            } catch (t) {} if (s(t, e)) return o(!r.f.call(t, e), t[e]);
          };
        }, function (t, e, n) {
          let i; let r; let o; const A = n(112); const a = n(1); const s = n(3); const c = n(8); const l = n(5); const u = n(41); const g = n(46); const h = n(47); const f = a.WeakMap;if (A || u.state) {
            const d = u.state || (u.state = new f); const p = d.get; const I = d.has; const m = d.set;i = function (t, e) {
              if (I.call(d, t)) throw new TypeError('Object already initialized');return e.facade = t, m.call(d, t, e), e;
            }, r = function (t) {
              return p.call(d, t) || {};
            }, o = function (t) {
              return I.call(d, t);
            };
          } else {
            const v = g('state');h[v] = !0, i = function (t, e) {
              if (l(t, v)) throw new TypeError('Object already initialized');return e.facade = t, c(t, v, e), e;
            }, r = function (t) {
              return l(t, v) ? t[v] : {};
            }, o = function (t) {
              return l(t, v);
            };
          }t.exports = { set: i, get: r, has: o, enforce(t) {
            return o(t) ? r(t) : i(t, {});
          }, getterFor(t) {
            return function (e) {
              let n;if (!s(e) || (n = r(e)).type !== t) throw TypeError(`Incompatible receiver, ${t} required`);return n;
            };
          } };
        }, function (t, e, n) {
          const i = n(39); const r = n(69); const o = i('keys');t.exports = function (t) {
            return o[t] || (o[t] = r(t));
          };
        }, function (t, e) {
          t.exports = {};
        }, function (t, e, n) {
          const i = n(75); const r = n(49).concat('length', 'prototype');e.f = Object.getOwnPropertyNames || function (t) {
            return i(t, r);
          };
        }, function (t, e) {
          t.exports = ['constructor', 'hasOwnProperty', 'isPrototypeOf', 'propertyIsEnumerable', 'toLocaleString', 'toString', 'valueOf'];
        }, function (t, e, n) {
          const i = n(0); const r = /#|\.prototype\./; const o = function (t, e) {
 let n = a[A(t)];return n == c || n != s && ('function'===typeof e ? i(e) : !!e); 
}; var A = o.normalize = function (t) {
            return String(t).replace(r, '.')
              .toLowerCase();
          }; var a = o.data = {}; var s = o.NATIVE = 'N'; var c = o.POLYFILL = 'P';t.exports = o;
        }, function (t, e, n) {
          const i = n(0); const r = n(2); const o = n(43); const A = r('species');t.exports = function (t) {
            return o >= 51 || !i((() => {
              const e = [];return (e.constructor = {})[A] = function () {
                return { foo: 1 };
              }, 1 !== e[t](Boolean).foo;
            }));
          };
        }, function (t, e, n) {
          let i; const r = n(4); const o = n(121); const A = n(49); const a = n(47); const s = n(122); const c = n(68); const l = n(46); const u = l('IE_PROTO'); const g = function () {}; const h = function (t) {
 return '<script>' + t + '<\/script>' 
}; var f = function () {
            try {
              i = document.domain && new ActiveXObject('htmlfile');
            } catch (t) {} let t; let e;f = i ? (function (t) {
              t.write(h('')), t.close();const e = t.parentWindow.Object;return t = null, e;
            }(i)) : ((e = c('iframe')).style.display = 'none', s.appendChild(e), e.src = String('javascript:'), (t = e.contentWindow.document).open(), t.write(h('document.F=Object')), t.close(), t.F);for (let n = A.length;n--;) delete f.prototype[A[n]];return f();
          };a[u] = !0, t.exports = Object.create || function (t, e) {
            let n;return null !== t ? (g.prototype = r(t), n = new g, g.prototype = null, n[u] = t) : n = f(), void 0 === e ? n : o(n, e);
          };
        }, function (t, e, n) {
          'use strict';const i = n(4);t.exports = function () {
            const t = i(this); let e = '';return t.global && (e += 'g'), t.ignoreCase && (e += 'i'), t.multiline && (e += 'm'), t.dotAll && (e += 's'), t.unicode && (e += 'u'), t.sticky && (e += 'y'), e;
          };
        }, function (t, e, n) {
          'use strict';const i = n(0);function r(t, e) {
            return RegExp(t, e);
          }e.UNSUPPORTED_Y = i((() => {
            const t = r('a', 'y');return t.lastIndex = 2, null != t.exec('abcd');
          })), e.BROKEN_CARET = i((() => {
            const t = r('^r', 'gy');return t.lastIndex = 2, null != t.exec('str');
          }));
        }, function (t, e, n) {
          'use strict';const i = n(21); const r = n(135); const o = n(56); const A = n(45); const a = n(136); const s = A.set; const c = A.getterFor('Array Iterator');t.exports = a(Array, 'Array', (function (t, e) {
            s(this, { type: 'Array Iterator', target: i(t), index: 0, kind: e });
          }), (function () {
            const t = c(this); const e = t.target; const n = t.kind; const i = t.index++;return !e || i >= e.length ? (t.target = void 0, { value: void 0, done: !0 }) : 'keys' == n ? { value: i, done: !1 } : 'values' == n ? { value: e[i], done: !1 } : { value: [i, e[i]], done: !1 };
          }), 'values'), o.Arguments = o.Array, r('keys'), r('values'), r('entries');
        }, function (t, e) {
          t.exports = {};
        }, function (t, e, n) {
          'use strict';t.exports = function (t, e) {
            return 'string' !== typeof t ? t : (/^['"].*['"]$/.test(t) && (t = t.slice(1, -1)), /["'() \t\n]/.test(t) || e ? `"${t.replace(/"/g, '\\"').replace(/\n/g, '\\n')}"` : t);
          };
        }, function (t, e, n) {
          'use strict';n.d(e, 'a', (() => i)), n.d(e, 'b', (() => r));var i = function () {
            const t = this.$createElement;return (this._self._c || t)('log-main', { class: ['plugin-log', 'log-scroll', this.extCls], attrs: { id: 'single-log', worker: this.worker, 'search-id': this.searchId }, on: { 'tag-change': this.tagChange } });
          }; var r = [];i._withStripped = !0;
        }, function (t, e, n) {
          'use strict';n.d(e, 'a', (() => i)), n.d(e, 'b', (() => r));var i = function () {
            const t = this; const e = t.$createElement; const n = t._self._c || e;return n('section', { class: ['multiple-log', t.extCls] }, [n('ul', { staticClass: 'job-plugin-list-log' }, t._l(t.logList, (e => n('li', { key: e.id, staticClass: 'plugin-item' }, [n('span', { staticClass: 'item-head', on: { click(n) {
 return t.expendLog(e); 
} } }, [n('span', { class: [{ 'show-all': !!t.curFoldList[e.id] }, 'log-folder'] }), t._v(' '), t._t('default', [t._v(t._s(e.name))], { data: e })], 2), t._v(' '), n('log-main', { directives: [{ name: 'show', rawName: 'v-show', value: t.curFoldList[e.id], expression: 'curFoldList[log.id]' }], staticClass: 'log-scroll', attrs: { 'is-multiple': !0, id: e.id, worker: t.worker, 'search-id': t.searchId }, on: { 'tag-change': t.tagChange } })], 1))), 0)]);
          }; var r = [];i._withStripped = !0;
        }, function (t, e, n) {
          'use strict';n.d(e, 'a', (() => i)), n.d(e, 'b', (() => r));var i = function () {
            const t = this; const e = t.$createElement; const i = t._self._c || e;return i('p', { class: ['log-tools', t.extCls] }, [i('section', { staticClass: 'tool-search' }, [i('section', { staticClass: 'searct-input' }, [i('input', { ref: 'inputMain', attrs: { type: 'text', placeholder: 'Search' }, on: { input: t.startSearch, keyup(e) {
              return !e.type.indexOf('key') && t._k(e.keyCode, 'enter', 13, e.key, 'Enter') ? null : t.changeSearchIndex(1);
            } } }), t._v(' '), t.isSearching ? i('img', { staticClass: 'bk-select-loading search-icon', attrs: { src: n(161) } }) : [t.inputStr ? i('i', { staticClass: 'bk-log-icon log-icon-close-circle-shape search-icon', on: { click: t.clearSearch } }) : i('i', { staticClass: 'bk-log-icon log-icon-search search-icon' })]], 2), t._v(' '), i('i', { staticClass: 'bk-log-icon log-icon-angle-left icon-click', on: { click(e) {
              return t.changeSearchIndex(-1);
            } } }), t._v(' '), i('span', { staticClass: 'search-num' }, [t._v(t._s(`${t.searchIndex} / ${t.searchNum}`))]), t._v(' '), i('i', { staticClass: 'bk-log-icon log-icon-angle-right icon-click', on: { click(e) {
              return t.changeSearchIndex(1);
            } } })]), t._v(' '), [0, 1].includes(+t.executeCount) ? t._e() : i('section', { staticClass: 'log-execute bk-log-execute log-show-option' }, [i('span', { staticClass: 'log-show-option' }, [t._v(t._s(t.currentExe))]), t._v(' '), i('i', { class: ['bk-select-angle', 'bk-log-icon', 'log-icon-angle-down', 'log-show-option', { show: t.showList }] }), t._v(' '), t.showList ? i('ul', { staticClass: 'bk-log-option-list log-show-option' }, t._l(t.executeCount, (e => i('li', { key: e, staticClass: 'log-execute-option', on: { click(n) {
 return t.changeExecute(e); 
} } }, [t._v(t._s(e))]))), 0) : t._e()]), t._v(' '), i('section', { staticClass: 'tool-more' }, [i('i', { staticClass: 'bk-log-icon log-icon-more more-icon log-show-more' }), t._v(' '), t.showMore ? i('ul', { staticClass: 'more-list log-show-more' }, [i('li', { staticClass: 'more-button', on: { click: t.showLogTime } }, [t._v(t._s(t.showTime ? 'Hide Timestamp' : 'Show Timestamp'))]), t._v(' '), t._t('tool')], 2) : t._e()])]);
          }; var r = [];i._withStripped = !0;
        }, function (t, e, n) {
          'use strict';n.d(e, 'a', (() => i)), n.d(e, 'b', (() => r));var i = function () {
            const t = this; const e = t.$createElement; const n = t._self._c || e;return n('section', { staticClass: 'bk-log-main' }, [t.showSubTag ? n('ul', { class: ['bk-log-tag', { overflow: t.tagOverFlow }] }, [t._l(t.tagList, (e => n('li', { key: e.value, ref: 'logTag', refInFor: !0, class: [{ select: t.curTag === e.value }, 'bk-log-tag-item'], style: `transform: translateX(${  t.tagTransform  }px)`, on: { click(n) {
 return t.tagChange(e.value); 
} } }, [t._v(t._s(e.label))]))), t._v(' '), t.tagOverFlow ? [n('i', { class: ['bk-log-icon', 'log-icon-angle-double-left', { click: t.tagTransform < 0 }], on: { click(e) {
              return t.transTag(50);
            } } }), t._v(' '), n('i', { class: ['bk-log-icon', 'log-icon-angle-double-right', { click: t.tagTransform > 436 - t.maxDis }], on: { click(e) {
              return t.transTag(-50);
            } } })] : t._e()], 2) : t._e(), t._v(' '), n('log-virtual-scroll', t._b({ ref: 'scroll' }, 'log-virtual-scroll', t.$props, !1))], 1);
          }; var r = [];i._withStripped = !0;
        }, function (t, e, n) {
          'use strict';n.d(e, 'a', (() => i)), n.d(e, 'b', (() => r));var i = function () {
            const t = this; const e = t.$createElement; const n = t._self._c || e;return n('section', { class: ['scroll-home', `id-${t.id}`, { 'min-height': t.totalNumber <= 0, 'show-empty': t.hasCompleteInit }], style: t.visHeight > 0 && `height: ${t.visHeight}px`, on: { mousewheel: t.handleWheel, DOMMouseScroll: t.handleWheel } }, [n('ul', { staticClass: 'scroll-index scroll', style: `top: ${-t.totalScrollHeight}px; width: ${t.indexWidth}px; height: ${t.ulHeight}px` }, t._l(t.indexList, (e => n('li', { key: e.index, staticClass: 'scroll-item', style: `height: ${  t.itemHeight  }px; top: ${  e.top  }px` }, [t._v(`\n            ${t._s(e.isNewLine ? '' : e.value)}\n            `), e.isFold ? n('span', { class: [{ 'show-all': e.hasFolded }, 'log-folder'], on: { click(n) {
 return t.foldListData(e.index, e.isFold); 
} } }) : t._e()]))), 0), t._v(' '), n('ul', { staticClass: 'scroll scroll-main', style: `height: ${t.ulHeight}px; top: ${-t.totalScrollHeight}px ;width: ${t.mainWidth}px; left: ${t.indexWidth}px` }, t._l(t.listData, (e => n('li', { key: e.top + e.value, class: [{ pointer: e.isFold, hover: e.showIndex === t.curHoverIndex }, 'scroll-item'], style: `height: ${  t.itemHeight  }px; top: ${  e.top  }px; left: ${  -t.bottomScrollDis * (t.itemWidth - t.mainWidth) / (t.mainWidth - t.bottomScrollWidth)  }px;`, on: { mouseenter(n) {
 t.curHoverIndex = e.showIndex; 
}, mouseleave(e) {
 t.curHoverIndex = -1; 
}, click(n) {
 return t.foldListData(e.index, e.isFold); 
} } }, [n('span', { staticClass: 'item-txt selection-color' }, [t.showTime ? n('span', { staticClass: 'item-time selection-color' }, [t._v(t._s(t._f('timeFilter')(e.isNewLine ? '' : e.timestamp)))]) : t._e(), t._v(' '), n('span', { class: ['selection-color', { 'cur-search': t.isCurSearch && t.curSearchIndex === e.index }], style: `color: ${  e.color  };font-weight: ${  e.fontWeight}`, domProps: { innerHTML: t._s(t.valuefilter(e.value)) } })])]))), 0), t._v(' '), t.itemHeight * t.totalNumber > t.visHeight ? n('span', { staticClass: 'min-nav min-map', style: `height: ${t.visHeight}px; right: ${11 * t.visWidth / 100}px` }) : t._e(), t._v(' '), n('canvas', { directives: [{ name: 'show', rawName: 'v-show', value: t.itemHeight * t.totalNumber > t.visHeight, expression: 'itemHeight * totalNumber > visHeight' }], ref: 'minMap', staticClass: 'min-nav no-scroll', style: `height: ${t.visHeight}px; width: ${t.visWidth / 10}px;right: ${t.visWidth / 100}px`, on: { click: t.changeMinMap } }), t._v(' '), t.itemHeight * t.totalNumber > t.visHeight ? n('span', { staticClass: 'min-nav-slide no-scroll', style: `height: ${t.visHeight / 8}px; width: ${t.visWidth / 10}px; top: ${t.minMapTop}px;right: ${t.visWidth / 100}px`, on: { mousedown(e) {
              return t.startNavMove(t.mapHeight - t.visHeight / 8);
            } } }) : t._e(), t._v(' '), n('canvas', { ref: 'minNav', staticClass: 'min-nav', style: `height: ${t.visHeight}px; width: ${t.visWidth / 100}px` }), t._v(' '), t.navHeight < t.visHeight ? n('span', { staticClass: 'min-nav-slide nav-show', style: `height: ${t.navHeight}px; width: ${t.visWidth / 100}px; top: ${t.minNavTop}px`, on: { mousedown(e) {
              return t.startNavMove(t.visHeight - t.navHeight);
            } } }) : t._e(), t._v(' '), t.bottomScrollWidth < t.mainWidth ? n('span', { staticClass: 'min-nav-slide bottom-scroll', style: `left: ${t.indexWidth + t.bottomScrollDis + 20}px; width: ${t.bottomScrollWidth}px`, on: { mousedown: t.startBottomMove } }) : t._e(), t._v(' '), t.hasCompleteInit && t.totalNumber <= 0 ? n('p', { staticClass: 'list-empty' }, [t._v(t._s(t.errMessage))]) : t._e(), t._v(' '), t.hasCompleteInit ? t._e() : n('section', { staticClass: 'log-loading' }, [t._m(0)])]);
          }; var r = [function () {
            const t = this.$createElement; const e = this._self._c || t;return e('div', { staticClass: 'lds-ring' }, [e('div'), e('div'), e('div'), e('div')]);
          }];i._withStripped = !0;
        }, function (t, e) {
          t.exports = { CSSRuleList: 0, CSSStyleDeclaration: 0, CSSValueList: 0, ClientRectList: 0, DOMRectList: 0, DOMStringList: 0, DOMTokenList: 1, DataTransferItemList: 0, FileList: 0, HTMLAllCollection: 0, HTMLCollection: 0, HTMLFormElement: 0, HTMLSelectElement: 0, MediaList: 0, MimeTypeArray: 0, NamedNodeMap: 0, NodeList: 1, PaintRequestList: 0, Plugin: 0, PluginArray: 0, SVGLengthList: 0, SVGNumberList: 0, SVGPathSegList: 0, SVGPointList: 0, SVGStringList: 0, SVGTransformList: 0, SourceBufferList: 0, StyleSheetList: 0, TextTrackCueList: 0, TextTrackList: 0, TouchList: 0 };
        }, function (t, e, n) {
          const i = n(104); const r = n(38); const o = n(14); const A = n(13); const a = n(66); const s = [].push; const c = function (t) {
            let e = 1 == t; const n = 2 == t; const c = 3 == t; const l = 4 == t; const u = 6 == t; const g = 7 == t; const h = 5 == t || u;return function (f, d, p, I) {
              for (var m, v, b = o(f), x = r(b), M = i(d, p, 3), w = A(x.length), y = 0, C = I || a, S = e ? C(f, w) : n || g ? C(f, 0) : void 0;w > y;y++) if ((h || y in x) && (v = M(m = x[y], y, b), t)) if (e)S[y] = v;else if (v) switch (t) {
                case 3:return !0;case 5:return m;case 6:return y;case 2:s.call(S, m);
              } else switch (t) {
                case 4:return !1;case 7:s.call(S, m);
              } return u ? -1 : c || l ? l : S;
            };
          };t.exports = { forEach: c(0), map: c(1), filter: c(2), some: c(3), every: c(4), find: c(5), findIndex: c(6), filterOut: c(7) };
        }, function (t, e) {
          t.exports = function (t) {
            if ('function' !== typeof t) throw TypeError(`${String(t)} is not a function`);return t;
          };
        }, function (t, e, n) {
          const i = n(3); const r = n(23); const o = n(2)('species');t.exports = function (t, e) {
            let n;return r(t) && ('function' !== typeof(n = t.constructor) || n !== Array && !r(n.prototype) ? i(n) && null === (n = n[o]) && (n = void 0) : n = void 0), new(void 0 === n ? Array : n)(0 === e ? 0 : e);
          };
        }, function (t, e, n) {
          const i = n(9); const r = n(0); const o = n(68);t.exports = !i && !r((() => 7 != Object.defineProperty(o('div'), 'a', { get() {
 return 7; 
} }).a));
        }, function (t, e, n) {
          const i = n(1); const r = n(3); const o = i.document; const A = r(o) && r(o.createElement);t.exports = function (t) {
            return A ? o.createElement(t) : {};
          };
        }, function (t, e) {
          let n = 0; const i = Math.random();t.exports = function (t) {
            return `Symbol(${String(void 0 === t ? '' : t)})_${(++n + i).toString(36)}`;
          };
        }, function (t, e, n) {
          const i = n(43); const r = n(0);t.exports = !!Object.getOwnPropertySymbols && !r((() => {
            const t = Symbol();return !String(t) || !(Object(t) instanceof Symbol) || !Symbol.sham && i && i < 41;
          }));
        }, function (t, e, n) {
          const i = n(26);t.exports = i('navigator', 'userAgent') || '';
        }, function (t, e, n) {
          'use strict';n.r(e);const i = n(61); const r = n(30);for (const o in r)['default'].indexOf(o) < 0 && (function (t) {
            n.d(e, t, (() => r[t]));
          }(o));n(142);const A = n(6); const a = Object(A.a)(r.default, i.a, i.b, !1, null, '7aea2c36', null);a.options.__file = 'src/assets/log-main.vue', e.default = a.exports;
        }, function (t, e, n) {
          'use strict';const i = {}.propertyIsEnumerable; const r = Object.getOwnPropertyDescriptor; const o = r && !i.call({ 1: 2 }, 1);e.f = o ? function (t) {
            const e = r(this, t);return !!e && e.enumerable;
          } : i;
        }, function (t, e, n) {
          const i = n(41); const r = Function.toString;'function' !== typeof i.inspectSource && (i.inspectSource = function (t) {
            return r.call(t);
          }), t.exports = i.inspectSource;
        }, function (t, e, n) {
          const i = n(5); const r = n(21); const o = n(115).indexOf; const A = n(47);t.exports = function (t, e) {
            let n; const a = r(t); let s = 0; const c = [];for (n in a)!i(A, n) && i(a, n) && c.push(n);for (;e.length > s;)i(a, n = e[s++]) && (~o(c, n) || c.push(n));return c;
          };
        }, function (t, e, n) {
          const i = n(20); const r = Math.max; const o = Math.min;t.exports = function (t, e) {
            const n = i(t);return n < 0 ? r(n + e, 0) : o(n, e);
          };
        }, function (t, e) {
          e.f = Object.getOwnPropertySymbols;
        }, function (t, e, n) {
          'use strict';const i = n(24); const r = n(10); const o = n(25);t.exports = function (t, e, n) {
            const A = i(e);A in t ? r.f(t, A, o(0, n)) : t[A] = n;
          };
        }, function (t, e, n) {
          'use strict';const i = n(9); const r = n(1); const o = n(50); const A = n(15); const a = n(5); const s = n(19); const c = n(80); const l = n(24); const u = n(0); const g = n(52); const h = n(48).f; const { f } = n(44); const d = n(10).f; const p = n(123).trim; const I = r.Number; const m = I.prototype; const v = 'Number' == s(g(m)); const b = function (t) {
            let e; let n; let i; let r; let o; let A; let a; let s; let c = l(t, !1);if ('string' === typeof c && c.length > 2) if (43 === (e = (c = p(c)).charCodeAt(0)) || 45 === e) {
              if (88 === (n = c.charCodeAt(2)) || 120 === n) return NaN;
            } else if (48 === e) {
              switch (c.charCodeAt(1)) {
                case 66:case 98:i = 2, r = 49;break;case 79:case 111:i = 8, r = 55;break;default:return +c;
              } for (A = (o = c.slice(2)).length, a = 0;a < A;a++) if ((s = o.charCodeAt(a)) < 48 || s > r) return NaN;return parseInt(o, i);
            } return +c;
          };if (o('Number', !I(' 0o1') || !I('0b1') || I('+0x1'))) {
            for (var x, M = function (t) {
                const e = arguments.length < 1 ? 0 : t; const n = this;return n instanceof M && (v ? u((() => {
                  m.valueOf.call(n);
                })) : 'Number' != s(n)) ? c(new I(b(e)), n, M) : b(e);
              }, w = i ? h(I) : 'MAX_VALUE,MIN_VALUE,NaN,NEGATIVE_INFINITY,POSITIVE_INFINITY,EPSILON,isFinite,isInteger,isNaN,isSafeInteger,MAX_SAFE_INTEGER,MIN_SAFE_INTEGER,parseFloat,parseInt,isInteger,fromString,range'.split(','), y = 0;w.length > y;y++)a(I, x = w[y]) && !a(M, x) && d(M, x, f(I, x));M.prototype = m, m.constructor = M, A(r, 'Number', M);
          }
        }, function (t, e, n) {
          const i = n(3); const r = n(81);t.exports = function (t, e, n) {
            let o; let A;return r && 'function' === typeof(o = e.constructor) && o !== n && i(A = o.prototype) && A !== n.prototype && r(t, A), t;
          };
        }, function (t, e, n) {
          const i = n(4); const r = n(120);t.exports = Object.setPrototypeOf || ('__proto__' in {} ? (function () {
            let t; let e = !1; const n = {};try {
              (t = Object.getOwnPropertyDescriptor(Object.prototype, '__proto__').set).call(n, []), e = n instanceof Array;
            } catch (t) {} return function (n, o) {
              return i(n), r(o), e ? t.call(n, o) : n.__proto__ = o, n;
            };
          }()) : void 0);
        }, function (t, e, n) {
          const i = n(75); const r = n(49);t.exports = Object.keys || function (t) {
            return i(t, r);
          };
        }, function (t, e, n) {
          'use strict';n(126);const i = n(15); const r = n(27); const o = n(0); const A = n(2); const a = n(8); const s = A('species'); const c = RegExp.prototype; const l = !o((() => {
 let t = /./;return t.exec = function () {
 let t = [];return t.groups = { a: '7' }, t; 
}, '7' !== ''.replace(t, '$<a>'); 
})); const u = '$0' === 'a'.replace(/./, '$0'); const g = A('replace'); const h = !!/./[g] && '' === /./[g]('a', '$0'); const f = !o((() => {
            let t = /(?:)/; const e = t.exec;t.exec = function () {
              return e.apply(this, arguments);
            };const n = 'ab'.split(t);return 2 !== n.length || 'a' !== n[0] || 'b' !== n[1];
          }));t.exports = function (t, e, n, g) {
            const d = A(t); const p = !o((() => {
 let e = {};return e[d] = function () {
 return 7; 
}, 7 != ''[t](e); 
})); const I = p && !o((() => {
              let e = !1; let n = /a/;return 'split' === t && ((n = {}).constructor = {}, n.constructor[s] = function () {
                return n;
              }, n.flags = '', n[d] = /./[d]), n.exec = function () {
                return e = !0, null;
              }, n[d](''), !e;
            }));if (!p || !I || 'replace' === t && (!l || !u || h) || 'split' === t && !f) {
              const m = /./[d]; const v = n(d, ''[t], ((t, e, n, i, o) => {
 let A = e.exec;return A === r || A === c.exec ? p && !o ? { done: !0, value: m.call(e, n, i) } : { done: !0, value: t.call(n, e, i) } : { done: !1 }; 
}), { REPLACE_KEEPS_$0: u, REGEXP_REPLACE_SUBSTITUTES_UNDEFINED_CAPTURE: h }); const b = v[0]; const x = v[1];i(String.prototype, t, b), i(c, d, 2 == e ? function (t, e) {
                return x.call(t, this, e);
              } : function (t) {
                return x.call(t, this);
              });
            }g && a(c[d], 'sham', !0);
          };
        }, function (t, e, n) {
          const i = n(3); const r = n(19); const o = n(2)('match');t.exports = function (t) {
            let e;return i(t) && (void 0 !== (e = t[o]) ? !!e : 'RegExp' == r(t));
          };
        }, function (t, e, n) {
          'use strict';const i = n(128).charAt;t.exports = function (t, e, n) {
            return e + (n ? i(t, e).length : 1);
          };
        }, function (t, e, n) {
          const i = n(19); const r = n(27);t.exports = function (t, e) {
            const n = t.exec;if ('function' === typeof n) {
              const o = n.call(t, e);if ('object' !== typeof o) throw TypeError('RegExp exec method returned something other than an Object or null');return o;
            } if ('RegExp' !== i(t)) throw TypeError('RegExp#exec called on incompatible receiver');return r.call(t, e);
          };
        }, function (t, e, n) {
          const i = n(12); const r = n(134);i({ target: 'Object', stat: !0, forced: Object.assign !== r }, { assign: r });
        }, function (t, e, n) {
          'use strict';let i; let r; let o; const A = n(0); const a = n(89); const s = n(8); const c = n(5); const l = n(2); const u = n(40); const g = l('iterator'); let h = !1;[].keys && ('next' in (o = [].keys()) ? (r = a(a(o))) !== Object.prototype && (i = r) : h = !0);const f = null == i || A((() => {
            let t = {};return i[g].call(t) !== t;
          }));f && (i = {}), u && !f || c(i, g) || s(i, g, (function () {
            return this;
          })), t.exports = { IteratorPrototype: i, BUGGY_SAFARI_ITERATORS: h };
        }, function (t, e, n) {
          const i = n(5); const r = n(14); const o = n(46); const A = n(138); const a = o('IE_PROTO'); const s = Object.prototype;t.exports = A ? Object.getPrototypeOf : function (t) {
            return t = r(t), i(t, a) ? t[a] : 'function' === typeof t.constructor && t instanceof t.constructor ? t.constructor.prototype : t instanceof Object ? s : null;
          };
        }, function (t, e, n) {
          const i = n(10).f; const r = n(5); const o = n(2)('toStringTag');t.exports = function (t, e, n) {
            t && !r(t = n ? t : t.prototype, o) && i(t, o, { configurable: !0, value: e });
          };
        }, function (t, e, n) {
          const i = n(1); const r = n(63); const o = n(55); const A = n(8); const a = n(2); const s = a('iterator'); const c = a('toStringTag'); const l = o.values;for (const u in r) {
            const g = i[u]; const h = g && g.prototype;if (h) {
              if (h[s] !== l) try {
                A(h, s, l);
              } catch (t) {
                h[s] = l;
              } if (h[c] || A(h, c, u), r[u]) for (const f in o) if (h[f] !== o[f]) try {
                A(h, f, o[f]);
              } catch (t) {
                h[f] = o[f];
              }
            }
          }
        }, function (t, e, n) {
          const i = n(16); let r = n(140);'string' === typeof(r = r.__esModule ? r.default : r) && (r = [[t.i, r, '']]);const o = { insert: 'head', singleton: !1 };i(r, o);t.exports = r.locals || {};
        }, function (t, e) {
          t.exports = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABmJLR0QA/wD/AP+gvaeTAAAAqElEQVQ4je2NMQrCQBBF/1hsYbPTeYg9gEhs0lpqWg/gBVLpJbT3BoIgNjZbTUiR41iYgV1sFDSwgmiZ1w389wbo+S91XY++3QxejxDCXkRWKVlEyhjjNhkgogJAISJlV66qakNEU2vt8s3pDpumGbZtewJwzLJs9/i8BjBm5oVzTj8GnhFVPccYD0RkAUyYed6VkwEA8N6zMeYC4KaqszzPr6ltz4/cAelAOoycaO5KAAAAAElFTkSuQmCC';
        }, function (t, e, n) {
          const i = n(16); let r = n(143);'string' === typeof(r = r.__esModule ? r.default : r) && (r = [[t.i, r, '']]);const o = { insert: 'head', singleton: !1 };i(r, o);t.exports = r.locals || {};
        }, function (t, e, n) {
          'use strict';t.exports = function () {
            return n(96)('!function(e){var t={};function n(s){if(t[s])return t[s].exports;var a=t[s]={i:s,l:!1,exports:{}};return e[s].call(a.exports,a,a.exports,n),a.l=!0,a.exports}n.m=e,n.c=t,n.d=function(e,t,s){n.o(e,t)||Object.defineProperty(e,t,{enumerable:!0,get:s})},n.r=function(e){"undefined"!=typeof Symbol&&Symbol.toStringTag&&Object.defineProperty(e,Symbol.toStringTag,{value:"Module"}),Object.defineProperty(e,"__esModule",{value:!0})},n.t=function(e,t){if(1&t&&(e=n(e)),8&t)return e;if(4&t&&"object"==typeof e&&e&&e.__esModule)return e;var s=Object.create(null);if(n.r(s),Object.defineProperty(s,"default",{enumerable:!0,value:e}),2&t&&"string"!=typeof e)for(var a in e)n.d(s,a,function(t){return e[t]}.bind(null,a));return s},n.n=function(e){var t=e&&e.__esModule?function(){return e.default}:function(){return e};return n.d(t,"a",t),t},n.o=function(e,t){return Object.prototype.hasOwnProperty.call(e,t)},n.p="/",n(n.s=0)}([function(e,t){const n={};let s=[];const a={},r={index:0,val:""};let o,i,l;function c(e){if(i=[],""!==e){const t=Object.keys(n)||[];e=e.replace(/\\*|\\.|\\?|\\+|\\$|\\^|\\[|\\]|\\(|\\)|\\{|\\}|\\||\\\\|\\//g,e=>"\\\\"+e);const s=new RegExp(e,"i");t.forEach(e=>{(n[e]||[]).forEach(({message:t,realIndex:n,children:a},r)=>{const o={index:r,realIndex:n,refId:e};s.test(t)&&i.push(o),a&&a.length>0&&a.forEach(({message:t,realIndex:a})=>{if(s.test(t)){const t={index:r,startIndex:n,realIndex:a,refId:e,isInFold:!0};i.push(t)}})})})}}function d(e){let t=[];const n=e-500,s=e+500;let a=e;return i.length<=1500?t=i:(t=[...i.slice(e,s),...i.slice(n,e)],n<0&&(t=[...i.slice(e,s),...i.slice(n),...i.slice(0,e)]),s>i.length&&(t=[...i.slice(e),...i.slice(0,s-i.length),...i.slice(n,e)]),a=0),[t,a]}onmessage=function(e){const t=e.data,h=t.type;let p;switch(o=t.id,s=n[o],h){case"initStatus":(t.pluginList||[]).forEach(e=>{n[e]=[],a[e]=[]});break;case"initAssistWorker":!function(e){l=e.dataPort,l.onmessage=e=>{const t=e.data;switch(t.type){case"complateHandleData":const e=t.curId;t.list.forEach(t=>{if(t.message.startsWith("##[group]")&&(t.message=t.message.replace("##[group]",""),a[e].push(t)),t.message.startsWith("##[endgroup]")&&a[e].length){t.message=t.message.replace("##[endgroup]","");const n=a[e].pop();n.endIndex=t.realIndex,n.children=[]}n[e].push(t)}),postMessage({type:"completeAdd",number:n[e].length,id:e})}}}(t);break;case"addListData":l.postMessage({type:"addListData",list:t.list,mainWidth:t.mainWidth,curId:o});break;case"wheelGetData":!function({totalScrollHeight:e,itemHeight:t,itemNumber:n,canvasHeight:a,minMapTop:r,totalHeight:i,mapHeight:l,type:c}){const d=r/(l-a/8||1)*(i-a);let h=Math.floor(d/t);const p=h+n;h=h>0?h-1:0;const u=[],f=[],g=Math.floor(h*t/5e5);for(let e=h;e<=p;e++){const n=e*t-5e5*g,a=s[e];void 0!==a&&(f.push({top:n,value:a.showIndex,isNewLine:a.isNewLine,index:a.realIndex,listIndex:e,isFold:void 0!==a.endIndex,hasFolded:(a.children||[]).length>0}),u.push({top:n,isNewLine:a.isNewLine,value:a.message,color:a.color,index:a.realIndex,showIndex:a.showIndex,fontWeight:a.fontWeight,isFold:void 0!==a.endIndex,timestamp:a.timestamp}))}e-=5e5*g;let x=h-Math.floor(8*n*r/a);x<0&&(x=0);const m=x+8*n,I=[];for(let e=x;e<=m;e++){const t=s[e];void 0!==t&&I.push(t)}postMessage({type:c,indexList:f,listData:u,totalScrollHeight:e,minMapList:I,id:o})}(t);break;case"foldListData":!function({startIndex:e}){const t=s.findIndex(t=>t.realIndex===e),n=s[t];if(!n||!n.children)return;if(n.children.length){for(let e=0;e<n.children.length;){const a=n.children.slice(e,e+1e4);s.splice(t+1+e,0,...a),e+=1e4}n.children=[]}else{let a=n.endIndex-e;for(;a>0;){let e;a>1e4?(e=1e4,a-=1e4):(e=a,a=0);const r=s.splice(t+1,e);n.children=n.children.concat(r)}}}(t),postMessage({type:"completeFold",number:s.length,id:o}),c(r.val);const e=void 0===t.index;p=d(t.index||r.index),postMessage({type:"completeSearch",num:i.length,curSearchRes:p[0],realSearchIndex:p[1],noScroll:e});break;case"search":c(t.val),p=d(0),postMessage({type:"completeSearch",num:i.length,curSearchRes:p[0],realSearchIndex:p[1]}),r.index=0,r.val=t.val;break;case"getSearchRes":p=d(t.index),postMessage({type:"completeGetSearchRes",searchRes:p[0],realSearchIndex:p[1]});break;case"changeSearchIndex":r.index=t.index;break;case"resetData":n[o]=[],a[o]=[],l.postMessage({type:"resetData",curId:o})}}}]);', `${n.p}4c1671fb31bc56a24089.worker.js`);
          };
        }, function (t, e, n) {
          'use strict';const i = window.URL || window.webkitURL;t.exports = function (t, e) {
            try {
              try {
                let n;try {
                  (n = new(window.BlobBuilder || window.WebKitBlobBuilder || window.MozBlobBuilder || window.MSBlobBuilder)).append(t), n = n.getBlob();
                } catch (e) {
                  n = new Blob([t]);
                } return new Worker(i.createObjectURL(n));
              } catch (e) {
                return new Worker(`data:application/javascript,${encodeURIComponent(t)}`);
              }
            } catch (t) {
              if (!e) throw Error('Inline worker is not supported');return new Worker(e);
            }
          };
        }, function (t, e, n) {
          'use strict';t.exports = function () {
            return n(96)('!function(t){var e={};function n(r){if(e[r])return e[r].exports;var o=e[r]={i:r,l:!1,exports:{}};return t[r].call(o.exports,o,o.exports,n),o.l=!0,o.exports}n.m=t,n.c=e,n.d=function(t,e,r){n.o(t,e)||Object.defineProperty(t,e,{enumerable:!0,get:r})},n.r=function(t){"undefined"!=typeof Symbol&&Symbol.toStringTag&&Object.defineProperty(t,Symbol.toStringTag,{value:"Module"}),Object.defineProperty(t,"__esModule",{value:!0})},n.t=function(t,e){if(1&e&&(t=n(t)),8&e)return t;if(4&e&&"object"==typeof t&&t&&t.__esModule)return t;var r=Object.create(null);if(n.r(r),Object.defineProperty(r,"default",{enumerable:!0,value:t}),2&e&&"string"!=typeof t)for(var o in t)n.d(r,o,function(e){return t[e]}.bind(null,o));return r},n.n=function(t){var e=t&&t.__esModule?function(){return t.default}:function(){return t};return n.d(e,"a",e),e},n.o=function(t,e){return Object.prototype.hasOwnProperty.call(t,e)},n.p="/",n(n.s=9)}([function(t,e,n){(function(e){var n=function(t){return t&&t.Math==Math&&t};t.exports=n("object"==typeof globalThis&&globalThis)||n("object"==typeof window&&window)||n("object"==typeof self&&self)||n("object"==typeof e&&e)||function(){return this}()||Function("return this")()}).call(this,n(11))},function(t,e){t.exports=function(t){try{return!!t()}catch(t){return!0}}},function(t,e){t.exports=function(t){return"object"==typeof t?null!==t:"function"==typeof t}},function(t,e,n){var r=n(1);t.exports=!r((function(){return 7!=Object.defineProperty({},1,{get:function(){return 7}})[1]}))},function(t,e){var n={}.toString;t.exports=function(t){return n.call(t).slice(8,-1)}},function(t,e,n){var r=n(18);t.exports=function(t){return Object(r(t))}},function(t,e,n){var r=n(3),o=n(28),u=n(33);t.exports=r?function(t,e,n){return o.f(t,e,u(1,n))}:function(t,e,n){return t[e]=n,t}},function(t,e,n){var r=n(36),o=n(1);t.exports=!!Object.getOwnPropertySymbols&&!o((function(){var t=Symbol();return!String(t)||!(Object(t)instanceof Symbol)||!Symbol.sham&&r&&r<41}))},function(t,e,n){"use strict";function r(t){for(var e,n,o=null,u=null,i="",c=[],a=[],s={},f=0;f<t.length;f++)null===o?null===u?""===t[f]?o=t[f]:"\\b"===t[f]?(e=void 0,n=void 0,i.length?i=i.substr(0,i.length-1):a.length&&(e=a.length-1,1===(n=a[e].message).length?a.pop():a[e].message=n.substr(0,n.length-1))):i+=t[f]:";"===t[f]?(c.push(u),u=""):"m"===t[f]?(c.push(u),u=null,i="",c.forEach((function(t){r.foregroundColors[t]?s.color=r.foregroundColors[t]:r.backgroundColors[t]?s.backgroundColor=r.backgroundColors[t]:39===t?delete s.color:49===t?delete s.backgroundColor:r.styles[t]?s[r.styles[t]]=!0:22===t?s.bold=!1:23===t?s.italic=!1:24===t&&(s.underline=!1)})),c=[]):u+=t[f]:""===o&&"["===t[f]?(i&&(s.message=i,a.push(s),s={},i=""),o=null,u=""):(i+=o+t[f],o=null);return i&&(s.message=i+(o||""),a.push(s)),a}Object.defineProperty(e,"__esModule",{value:!0}),e.default=void 0,n(10),r.foregroundColors={30:"rgba(0,0,0,1)",31:"rgba(247,49,49,1)",32:"rgba(127,202,84,1)",33:"rgba(246,222,84,1)",34:"rgba(0,0,255,1)",35:"rgba(255,0,255,1)",36:"rgba(0,255,255,1)",37:"rgba(255,255,255,1)",90:"rgba(128,128,128,1)"},r.backgroundColors={40:"rgba(0,0,0,1)",41:"rgba(247,49,49,1)",42:"rgba(127,202,84,1)",43:"rgba(246,222,84,1)",44:"rgba(0,0,255,1)",45:"rgba(255,0,255,1)",46:"rgba(0,255,255,1)",47:"rgba(255,255,255,1)"},r.styles={1:"bold",3:"italic",4:"underline"};var o=r;e.default=o},function(t,e,n){"use strict";n.r(e);var r=n(8),o=n.n(r);let u,i,c,a=[],s={},f={},l={},p={},g=8;if(self.OffscreenCanvas){const t=new OffscreenCanvas(100,1).getContext("2d");t.font=\'normal 12px Consolas, "Courier New", monospace\',g=t.measureText("a").width;const e=t.measureText("我").width;c=t=>{const n=t.match(/[\\u3010\\u3011\\u4e00-\\u9fa5\\u3002\\uff1f\\uff01\\uff0c\\u3001\\uff1b\\uff1a\\u201c\\u201d\\u2018\\u2019\\uff08\\uff09\\u300a\\u300b\\u3008\\u3009\\u3010\\u3011\\u300e\\u300f\\u300c\\u300d\\ufe43\\ufe44\\u3014\\u3015\\u2026\\u2014\\uff5e\\ufe4f\\uffe5]/g),r=n?n.length:0,o=t.match(/\\t/g),u=o?o.length:0;return r*e+(t.length-r-u)*g+25*u+20}}else c=t=>{const e=t.match(/[\\u3010\\u3011\\u4e00-\\u9fa5\\u3002\\uff1f\\uff01\\uff0c\\u3001\\uff1b\\uff1a\\u201c\\u201d\\u2018\\u2019\\uff08\\uff09\\u300a\\u300b\\u3008\\u3009\\u3010\\u3011\\u300e\\u300f\\u300c\\u300d\\ufe43\\ufe44\\u3014\\u3015\\u2026\\u2014\\uff5e\\ufe4f\\uffe5]/g),n=e?e.length:0,r=t.match(/\\t/g),o=r?r.length:0,u=t.length-n-o;return 12*n+8*u+28*o-u+1+20};const h=[{key:"##[command]",color:"rgba(146,166,202,1)"},{key:"##[info]",color:"rgba(127,202,84,1)"},{key:"##[warning]",color:"rgba(246,222,84,1)"},{key:"##[error]",color:"rgba(247,49,49,1)"},{key:"##[debug]",color:"rgba(99,176,106,1)"}],d=(()=>{const t=h.map(t=>{let e=t.key;return e=e.replace(/\\[|\\]/gi,"\\\\$&"),`(${e})`});return new RegExp(""+t.join("|"),"gi")})();function b(t){let e=t.slice(0,p[i]);t=t.slice(p[i]);let n=c(e);for(;l[i]-n>15&&""!==t;)e+=t.slice(0,1),t=t.slice(1),n=c(e);for(;n>l[i];)t=`${e.slice(-1)}${t}`,e=e.slice(0,-1),n=c(e);return e}onmessage=t=>{const e=t.data;switch(e.type){case"init":!function(t){u=t.dataPort,u.onmessage=t=>{const e=t.data,n=e.type;switch(i=e.curId,n){case"addListData":!function({list:t,mainWidth:e}){l[i]=e-90,p[i]=Math.floor(l[i]/g),a=[],void 0===f[i]&&(f[i]=0,s[i]=-1);t.forEach(t=>{(t.message||"").split(/\\r\\n|\\n/).forEach(e=>{const{message:n,color:r}=function(t){const e=o()(t)||[{message:""}],n={message:""};e.forEach(t=>{n.message+=t.message,!n.color&&t.color&&(n.color=t.color)});const r=h.find(e=>String(t).startsWith(e.key));return r&&(n.color=r.color,n.message=String(n.message).replace(d,"")),n.color&&(n.fontWeight=600),n}(e||""),c=/<a[^>]+?href=["\']?([^"\']+)["\']?[^>]*>([^<]+)<\\/a>/gi,l=[];let p=null;for(;null!=(p=c.exec(n));)l.push({content:p[0],href:p[1],text:p[2],startIndex:p.index});!function t(e,n,r,o,c,a,l){let p="",g=0;do{p=b(e),e=e.slice(p.length),r.forEach(t=>{if(t.startIndex<=o+p.length&&t.startIndex>=o){const n=t.startIndex-o,r=t.text.length,u=n+r-p.length,i=p.slice(n);u>0&&n>0?(e=i+e,p=p.slice(0,n)):(u>0&&(p+=e.slice(0,u),e=e.slice(u)),p=p.slice(0,n)+t.content+p.slice(n+r))}});const t=f[i],h={message:p,color:c,isNewLine:l>0&&(s[i]++,!0),showIndex:t-s[i],realIndex:t,timestamp:a};n.push(h),f[i]++,n.length>2e4&&u.postMessage({type:"complateHandleData",list:n.splice(0,2e4),curId:i}),o+=p.length,g++,l++}while(g<1e4&&e.length>0);e.length>0&&t(e,n,r,o,c,a,l)}(l.length?n.replace(c,"$2"):n,a,l,0,r,t.timestamp,0)})}),u.postMessage({type:"complateHandleData",list:a.splice(0,a.length),curId:i})}(e);break;case"resetData":s[i]=-1,f[i]=0,l[i]=0,p[i]=0}}}(e)}}},function(t,e,n){var r=n(0),o=n(12),u=n(13),i=n(6);for(var c in o){var a=r[c],s=a&&a.prototype;if(s&&s.forEach!==u)try{i(s,"forEach",u)}catch(t){s.forEach=u}}},function(t,e){var n;n=function(){return this}();try{n=n||new Function("return this")()}catch(t){"object"==typeof window&&(n=window)}t.exports=n},function(t,e){t.exports={CSSRuleList:0,CSSStyleDeclaration:0,CSSValueList:0,ClientRectList:0,DOMRectList:0,DOMStringList:0,DOMTokenList:1,DataTransferItemList:0,FileList:0,HTMLAllCollection:0,HTMLCollection:0,HTMLFormElement:0,HTMLSelectElement:0,MediaList:0,MimeTypeArray:0,NamedNodeMap:0,NodeList:1,PaintRequestList:0,Plugin:0,PluginArray:0,SVGLengthList:0,SVGNumberList:0,SVGPathSegList:0,SVGPointList:0,SVGStringList:0,SVGTransformList:0,SourceBufferList:0,StyleSheetList:0,TextTrackCueList:0,TextTrackList:0,TouchList:0}},function(t,e,n){"use strict";var r=n(14).forEach,o=n(41)("forEach");t.exports=o?[].forEach:function(t){return r(this,t,arguments.length>1?arguments[1]:void 0)}},function(t,e,n){var r=n(15),o=n(17),u=n(5),i=n(19),c=n(21),a=[].push,s=function(t){var e=1==t,n=2==t,s=3==t,f=4==t,l=6==t,p=7==t,g=5==t||l;return function(h,d,b,v){for(var y,m,x=u(h),S=o(x),w=r(d,b,3),j=i(S.length),L=0,O=v||c,E=e?O(h,j):n||p?O(h,0):void 0;j>L;L++)if((g||L in S)&&(m=w(y=S[L],L,x),t))if(e)E[L]=m;else if(m)switch(t){case 3:return!0;case 5:return y;case 6:return L;case 2:a.call(E,y)}else switch(t){case 4:return!1;case 7:a.call(E,y)}return l?-1:s||f?f:E}};t.exports={forEach:s(0),map:s(1),filter:s(2),some:s(3),every:s(4),find:s(5),findIndex:s(6),filterOut:s(7)}},function(t,e,n){var r=n(16);t.exports=function(t,e,n){if(r(t),void 0===e)return t;switch(n){case 0:return function(){return t.call(e)};case 1:return function(n){return t.call(e,n)};case 2:return function(n,r){return t.call(e,n,r)};case 3:return function(n,r,o){return t.call(e,n,r,o)}}return function(){return t.apply(e,arguments)}}},function(t,e){t.exports=function(t){if("function"!=typeof t)throw TypeError(String(t)+" is not a function");return t}},function(t,e,n){var r=n(1),o=n(4),u="".split;t.exports=r((function(){return!Object("z").propertyIsEnumerable(0)}))?function(t){return"String"==o(t)?u.call(t,""):Object(t)}:Object},function(t,e){t.exports=function(t){if(null==t)throw TypeError("Can\'t call method on "+t);return t}},function(t,e,n){var r=n(20),o=Math.min;t.exports=function(t){return t>0?o(r(t),9007199254740991):0}},function(t,e){var n=Math.ceil,r=Math.floor;t.exports=function(t){return isNaN(t=+t)?0:(t>0?r:n)(t)}},function(t,e,n){var r=n(2),o=n(22),u=n(23)("species");t.exports=function(t,e){var n;return o(t)&&("function"!=typeof(n=t.constructor)||n!==Array&&!o(n.prototype)?r(n)&&null===(n=n[u])&&(n=void 0):n=void 0),new(void 0===n?Array:n)(0===e?0:e)}},function(t,e,n){var r=n(4);t.exports=Array.isArray||function(t){return"Array"==r(t)}},function(t,e,n){var r=n(0),o=n(24),u=n(34),i=n(35),c=n(7),a=n(40),s=o("wks"),f=r.Symbol,l=a?f:f&&f.withoutSetter||i;t.exports=function(t){return u(s,t)&&(c||"string"==typeof s[t])||(c&&u(f,t)?s[t]=f[t]:s[t]=l("Symbol."+t)),s[t]}},function(t,e,n){var r=n(25),o=n(26);(t.exports=function(t,e){return o[t]||(o[t]=void 0!==e?e:{})})("versions",[]).push({version:"3.13.1",mode:r?"pure":"global",copyright:"© 2021 Denis Pushkarev (zloirock.ru)"})},function(t,e){t.exports=!1},function(t,e,n){var r=n(0),o=n(27),u=r["__core-js_shared__"]||o("__core-js_shared__",{});t.exports=u},function(t,e,n){var r=n(0),o=n(6);t.exports=function(t,e){try{o(r,t,e)}catch(n){r[t]=e}return e}},function(t,e,n){var r=n(3),o=n(29),u=n(31),i=n(32),c=Object.defineProperty;e.f=r?c:function(t,e,n){if(u(t),e=i(e,!0),u(n),o)try{return c(t,e,n)}catch(t){}if("get"in n||"set"in n)throw TypeError("Accessors not supported");return"value"in n&&(t[e]=n.value),t}},function(t,e,n){var r=n(3),o=n(1),u=n(30);t.exports=!r&&!o((function(){return 7!=Object.defineProperty(u("div"),"a",{get:function(){return 7}}).a}))},function(t,e,n){var r=n(0),o=n(2),u=r.document,i=o(u)&&o(u.createElement);t.exports=function(t){return i?u.createElement(t):{}}},function(t,e,n){var r=n(2);t.exports=function(t){if(!r(t))throw TypeError(String(t)+" is not an object");return t}},function(t,e,n){var r=n(2);t.exports=function(t,e){if(!r(t))return t;var n,o;if(e&&"function"==typeof(n=t.toString)&&!r(o=n.call(t)))return o;if("function"==typeof(n=t.valueOf)&&!r(o=n.call(t)))return o;if(!e&&"function"==typeof(n=t.toString)&&!r(o=n.call(t)))return o;throw TypeError("Can\'t convert object to primitive value")}},function(t,e){t.exports=function(t,e){return{enumerable:!(1&t),configurable:!(2&t),writable:!(4&t),value:e}}},function(t,e,n){var r=n(5),o={}.hasOwnProperty;t.exports=Object.hasOwn||function(t,e){return o.call(r(t),e)}},function(t,e){var n=0,r=Math.random();t.exports=function(t){return"Symbol("+String(void 0===t?"":t)+")_"+(++n+r).toString(36)}},function(t,e,n){var r,o,u=n(0),i=n(37),c=u.process,a=c&&c.versions,s=a&&a.v8;s?o=(r=s.split("."))[0]<4?1:r[0]+r[1]:i&&(!(r=i.match(/Edge\\/(\\d+)/))||r[1]>=74)&&(r=i.match(/Chrome\\/(\\d+)/))&&(o=r[1]),t.exports=o&&+o},function(t,e,n){var r=n(38);t.exports=r("navigator","userAgent")||""},function(t,e,n){var r=n(39),o=n(0),u=function(t){return"function"==typeof t?t:void 0};t.exports=function(t,e){return arguments.length<2?u(r[t])||u(o[t]):r[t]&&r[t][e]||o[t]&&o[t][e]}},function(t,e,n){var r=n(0);t.exports=r},function(t,e,n){var r=n(7);t.exports=r&&!Symbol.sham&&"symbol"==typeof Symbol.iterator},function(t,e,n){"use strict";var r=n(1);t.exports=function(t,e){var n=[][t];return!!n&&r((function(){n.call(null,e||function(){throw 1},1)}))}}]);', `${n.p}281c3f7947400611205e.worker.js`);
          };
        }, function (t, e, n) {
          const i = n(16); let r = n(145);'string' === typeof(r = r.__esModule ? r.default : r) && (r = [[t.i, r, '']]);const o = { insert: 'head', singleton: !1 };i(r, o);t.exports = r.locals || {};
        }, function (t, e, n) {
          const i = n(16); let r = n(158);'string' === typeof(r = r.__esModule ? r.default : r) && (r = [[t.i, r, '']]);const o = { insert: 'head', singleton: !1 };i(r, o);t.exports = r.locals || {};
        }, function (t, e, n) {
          const i = n(16); let r = n(163);'string' === typeof(r = r.__esModule ? r.default : r) && (r = [[t.i, r, '']]);const o = { insert: 'head', singleton: !1 };i(r, o);t.exports = r.locals || {};
        }, function (t, e, n) {
          'use strict';const i = n(7);Object.defineProperty(e, '__esModule', { value: !0 }), Object.defineProperty(e, 'bkLog', { enumerable: !0, get() {
            return r.default;
          } }), Object.defineProperty(e, 'bkMultipleLog', { enumerable: !0, get() {
            return o.default;
          } }), Object.defineProperty(e, 'bkLogSearch', { enumerable: !0, get() {
            return A.default;
          } }), e.default = void 0, n(18);var r = i(n(108)); var o = i(n(146)); var A = i(n(159));n(164);const a = [r.default, o.default, A.default]; const s = function (t) {
            a.forEach(((e) => {
              t.component(e.name, e);
            }));
          };'undefined' !== typeof window && window.Vue && s(window.Vue);const c = { install: s, bkLog: r.default, bkMultipleLog: o.default, bkLogSearch: A.default };e.default = c;
        }, function (t, e) {
          let n;n = (function () {
            return this;
          }());try {
            n = n || new Function('return this')();
          } catch (t) {
            'object' === typeof window && (n = window);
          }t.exports = n;
        }, function (t, e, n) {
          'use strict';const i = n(64).forEach; const r = n(107)('forEach');t.exports = r ? [].forEach : function (t) {
            return i(this, t, arguments.length > 1 ? arguments[1] : void 0);
          };
        }, function (t, e, n) {
          const i = n(65);t.exports = function (t, e, n) {
            if (i(t), void 0 === e) return t;switch (n) {
              case 0:return function () {
                return t.call(e);
              };case 1:return function (n) {
                return t.call(e, n);
              };case 2:return function (n, i) {
                return t.call(e, n, i);
              };case 3:return function (n, i, r) {
                return t.call(e, n, i, r);
              };
            } return function () {
              return t.apply(e, arguments);
            };
          };
        }, function (t, e, n) {
          const i = n(1);t.exports = i;
        }, function (t, e, n) {
          const i = n(70);t.exports = i && !Symbol.sham && 'symbol' === typeof Symbol.iterator;
        }, function (t, e, n) {
          'use strict';const i = n(0);t.exports = function (t, e) {
            const n = [][t];return !!n && i((() => {
              n.call(null, e || (() => {
                throw 1;
              }), 1);
            }));
          };
        }, function (t, e, n) {
          'use strict';const i = n(7);Object.defineProperty(e, '__esModule', { value: !0 }), e.default = void 0;const r = i(n(109));r.default.install = function (t) {
            t.component(r.default.name, r.default);
          };const o = r.default;e.default = o;
        }, function (t, e, n) {
          'use strict';n.r(e);const i = n(58); const r = n(28);for (const o in r)['default'].indexOf(o) < 0 && (function (t) {
            n.d(e, t, (() => r[t]));
          }(o));n(144);const A = n(6); const a = Object(A.a)(r.default, i.a, i.b, !1, null, '4749c4a0', null);a.options.__file = 'src/log/log.vue', e.default = a.exports;
        }, function (t, e, n) {
          'use strict';n.r(e);const i = n(62); const r = n(32);for (const o in r)['default'].indexOf(o) < 0 && (function (t) {
            n.d(e, t, (() => r[t]));
          }(o));n(139);const A = n(6); const a = Object(A.a)(r.default, i.a, i.b, !1, null, 'a536c00a', null);a.options.__file = 'src/assets/log-virtual-scroll.vue', e.default = a.exports;
        }, function (t, e, n) {
          'use strict';const i = n(12); const r = n(0); const o = n(23); const A = n(3); const a = n(14); const s = n(13); const c = n(78); const l = n(66); const u = n(51); const g = n(2); const h = n(43); const f = g('isConcatSpreadable'); const d = h >= 51 || !r((() => {
 let t = [];return t[f] = !1, t.concat()[0] !== t; 
})); const p = u('concat'); const I = function (t) {
            if (!A(t)) return !1;const e = t[f];return void 0 !== e ? !!e : o(t);
          };i({ target: 'Array', proto: !0, forced: !d || !p }, { concat(t) {
            let e; let n; let i; let r; let o; const A = a(this); const u = l(A, 0); let g = 0;for (e = -1, i = arguments.length;e < i;e++) if (I(o = -1 === e ? A : arguments[e])) {
              if (g + (r = s(o.length)) > 9007199254740991) throw TypeError('Maximum allowed index exceeded');for (n = 0;n < r;n++, g++)n in o && c(u, g, o[n]);
            } else {
              if (g >= 9007199254740991) throw TypeError('Maximum allowed index exceeded');c(u, g++, o);
            } return u.length = g, u;
          } });
        }, function (t, e, n) {
          const i = n(1); const r = n(74); const o = i.WeakMap;t.exports = 'function' === typeof o && /native code/.test(r(o));
        }, function (t, e, n) {
          const i = n(5); const r = n(114); const o = n(44); const A = n(10);t.exports = function (t, e) {
            for (let n = r(e), a = A.f, s = o.f, c = 0;c < n.length;c++) {
              const l = n[c];i(t, l) || a(t, l, s(e, l));
            }
          };
        }, function (t, e, n) {
          const i = n(26); const r = n(48); const o = n(77); const A = n(4);t.exports = i('Reflect', 'ownKeys') || function (t) {
            const e = r.f(A(t)); const n = o.f;return n ? e.concat(n(t)) : e;
          };
        }, function (t, e, n) {
          const i = n(21); const r = n(13); const o = n(76); const A = function (t) {
            return function (e, n, A) {
              let a; const s = i(e); const c = r(s.length); let l = o(A, c);if (t && n != n) {
                for (;c > l;) if ((a = s[l++]) != a) return !0;
              } else for (;c > l;l++) if ((t || l in s) && s[l] === n) return t || l || 0;return !t && -1;
            };
          };t.exports = { includes: A(!0), indexOf: A(!1) };
        }, function (t, e, n) {
          'use strict';const i = n(12); const r = n(117).start;i({ target: 'String', proto: !0, forced: n(119) }, { padStart(t) {
            return r(this, t, arguments.length > 1 ? arguments[1] : void 0);
          } });
        }, function (t, e, n) {
          const i = n(13); const r = n(118); const o = n(11); const A = Math.ceil; const a = function (t) {
            return function (e, n, a) {
              let s; let c; const l = String(o(e)); const u = l.length; const g = void 0 === a ? " " : String(a); const h = i(n);return h <= u || '' == g ? l : (s = h - u, (c = r.call(g, A(s / g.length))).length > s && (c = c.slice(0, s)), t ? l + c : c + l);
            };
          };t.exports = { start: a(!1), end: a(!0) };
        }, function (t, e, n) {
          'use strict';const i = n(20); const r = n(11);t.exports = function (t) {
            let e = String(r(this)); let n = ''; let o = i(t);if (o < 0 || o == 1 / 0) throw RangeError('Wrong number of repetitions');for (;o > 0;(o >>>= 1) && (e += e))1 & o && (n += e);return n;
          };
        }, function (t, e, n) {
          const i = n(71);t.exports = /Version\/10(?:\.\d+){1,2}(?: [\w./]+)?(?: Mobile\/\w+)? Safari\//.test(i);
        }, function (t, e, n) {
          const i = n(3);t.exports = function (t) {
            if (!i(t) && null !== t) throw TypeError(`Can't set ${String(t)} as a prototype`);return t;
          };
        }, function (t, e, n) {
          const i = n(9); const r = n(10); const o = n(4); const A = n(82);t.exports = i ? Object.defineProperties : function (t, e) {
            o(t);for (var n, i = A(e), a = i.length, s = 0;a > s;)r.f(t, n = i[s++], e[n]);return t;
          };
        }, function (t, e, n) {
          const i = n(26);t.exports = i('document', 'documentElement');
        }, function (t, e, n) {
          const i = n(11); const r = '[' + n(124) + ']'; const o = RegExp(`^${r  }${r  }*`); const A = RegExp(`${r + r}*$`); const a = function (t) {
            return function (e) {
              let n = String(i(e));return 1 & t && (n = n.replace(o, '')), 2 & t && (n = n.replace(A, '')), n;
            };
          };t.exports = { start: a(1), end: a(2), trim: a(3) };
        }, function (t, e) {
          t.exports = '\t\n\v\f\r                　\u2028\u2029\ufeff';
        }, function (t, e, n) {
          'use strict';const i = n(83); const r = n(84); const o = n(4); const A = n(11); const a = n(127); const s = n(85); const c = n(13); const l = n(86); const u = n(27); const g = n(54).UNSUPPORTED_Y; const h = [].push; const f = Math.min;i('split', 2, ((t, e, n) => {
            let i;return i = 'c' == 'abbc'.split(/(b)*/)[1] || 4 != 'test'.split(/(?:)/, -1).length || 2 != 'ab'.split(/(?:ab)*/).length || 4 != '.'.split(/(.?)(.?)/).length || '.'.split(/()()/).length > 1 || ''.split(/.?/).length ? function (t, n) {
              const i = String(A(this)); const o = void 0 === n ? 4294967295 : n >>> 0;if (0 === o) return [];if (void 0 === t) return [i];if (!r(t)) return e.call(i, t, o);for (var a, s, c, l = [], g = (t.ignoreCase ? 'i' : '') + (t.multiline ? 'm' : '') + (t.unicode ? 'u' : '') + (t.sticky ? 'y' : ''), f = 0, d = new RegExp(t.source, `${g}g`);(a = u.call(d, i)) && !((s = d.lastIndex) > f && (l.push(i.slice(f, a.index)), a.length > 1 && a.index < i.length && h.apply(l, a.slice(1)), c = a[0].length, f = s, l.length >= o));)d.lastIndex === a.index && d.lastIndex++;return f === i.length ? !c && d.test('') || l.push('') : l.push(i.slice(f)), l.length > o ? l.slice(0, o) : l;
            } : '0'.split(void 0, 0).length ? function (t, n) {
              return void 0 === t && 0 === n ? [] : e.call(this, t, n);
            } : e, [function (e, n) {
              const r = A(this); const o = null == e ? void 0 : e[t];return void 0 !== o ? o.call(e, r, n) : i.call(String(r), e, n);
            }, function (t, r) {
              const A = n(i, t, this, r, i !== e);if (A.done) return A.value;const u = o(t); const h = String(this); const d = a(u, RegExp); const p = u.unicode; const I = (u.ignoreCase ? 'i' : '') + (u.multiline ? 'm' : '') + (u.unicode ? 'u' : '') + (g ? 'g' : 'y'); const m = new d(g ? '^(?:' + u.source + ')' : u, I); const v = void 0 === r ? 4294967295 : r >>> 0;if (0 === v) return [];if (0 === h.length) return null === l(m, h) ? [h] : [];for (var b = 0, x = 0, M = [];x < h.length;) {
                m.lastIndex = g ? 0 : x;var w; const y = l(m, g ? h.slice(x) : h);if (null === y || (w = f(c(m.lastIndex + (g ? x : 0)), h.length)) === b)x = s(h, x, p);else {
                  if (M.push(h.slice(b, x)), M.length === v) return M;for (let C = 1;C <= y.length - 1;C++) if (M.push(y[C]), M.length === v) return M;x = b = w;
                }
              } return M.push(h.slice(b)), M;
            }];
          }), g);
        }, function (t, e, n) {
          'use strict';const i = n(12); const r = n(27);i({ target: 'RegExp', proto: !0, forced: /./.exec !== r }, { exec: r });
        }, function (t, e, n) {
          const i = n(4); const r = n(65); const o = n(2)('species');t.exports = function (t, e) {
            let n; const A = i(t).constructor;return void 0 === A || null == (n = i(A)[o]) ? e : r(n);
          };
        }, function (t, e, n) {
          const i = n(20); const r = n(11); const o = function (t) {
            return function (e, n) {
              let o; let A; const a = String(r(e)); const s = i(n); const c = a.length;return s < 0 || s >= c ? t ? '' : void 0 : (o = a.charCodeAt(s)) < 55296 || o > 56319 || s + 1 === c || (A = a.charCodeAt(s + 1)) < 56320 || A > 57343 ? t ? a.charAt(s) : o : t ? a.slice(s, s + 2) : A - 56320 + (o - 55296 << 10) + 65536;
            };
          };t.exports = { codeAt: o(!1), charAt: o(!0) };
        }, function (t, e, n) {
          'use strict';const i = n(83); const r = n(4); const o = n(13); const A = n(20); const a = n(11); const s = n(85); const c = n(130); const l = n(86); const u = Math.max; const g = Math.min;i('replace', 2, ((t, e, n, i) => {
            const h = i.REGEXP_REPLACE_SUBSTITUTES_UNDEFINED_CAPTURE; const f = i.REPLACE_KEEPS_$0; const d = h ? '$' : '$0';return [function (n, i) {
              const r = a(this); const o = null == n ? void 0 : n[t];return void 0 !== o ? o.call(n, r, i) : e.call(String(r), n, i);
            }, function (t, i) {
              if (!h && f || 'string' === typeof i && -1 === i.indexOf(d)) {
                const a = n(e, t, this, i);if (a.done) return a.value;
              } const p = r(t); const I = String(this); const m = 'function' === typeof i;m || (i = String(i));const v = p.global;if (v) {
                var b = p.unicode;p.lastIndex = 0;
              } for (var x = [];;) {
                var M = l(p, I);if (null === M) break;if (x.push(M), !v) break;'' === String(M[0]) && (p.lastIndex = s(I, o(p.lastIndex), b));
              } for (var w, y = '', C = 0, S = 0;S < x.length;S++) {
                M = x[S];for (var N = String(M[0]), D = u(g(A(M.index), I.length), 0), j = [], E = 1;E < M.length;E++)j.push(void 0 === (w = M[E]) ? w : String(w));const B = M.groups;if (m) {
                  const z = [N].concat(j, D, I);void 0 !== B && z.push(B);var k = String(i.apply(void 0, z));
                } else k = c(N, I, D, j, B, i);D >= C && (y += I.slice(C, D) + k, C = D + N.length);
              } return y + I.slice(C);
            }];
          }));
        }, function (t, e, n) {
          const i = n(14); const r = Math.floor; const o = ''.replace; const A = /\$([$&'`]|\d{1,2}|<[^>]*>)/g; const a = /\$([$&'`]|\d{1,2})/g;t.exports = function (t, e, n, s, c, l) {
            const u = n + t.length; const g = s.length; let h = a;return void 0 !== c && (c = i(c), h = A), o.call(l, h, ((i, o) => {
              let A;switch (o.charAt(0)) {
                case '$':return '$';case '&':return t;case '`':return e.slice(0, n);case '\'':return e.slice(u);case '<':A = c[o.slice(1, -1)];break;default:var a = +o;if (0 === a) return i;if (a > g) {
                  const l = r(a / 10);return 0 === l ? i : l <= g ? void 0 === s[l - 1] ? o.charAt(1) : s[l - 1] + o.charAt(1) : i;
                }A = s[a - 1];
              } return void 0 === A ? '' : A;
            }));
          };
        }, function (t, e, n) {
          const i = n(9); const r = n(1); const o = n(50); const A = n(80); const a = n(10).f; const s = n(48).f; const c = n(84); const l = n(53); const u = n(54); const g = n(15); const h = n(0); const f = n(45).enforce; const d = n(132); const p = n(2)('match'); const I = r.RegExp; const m = I.prototype; const v = /a/g; const b = /a/g; const x = new I(v) !== v; const M = u.UNSUPPORTED_Y;if (i && o('RegExp', !x || M || h((() => (b[p] = !1, I(v) != v || I(b) == b || '/a/i' != I(v, 'i')))))) {
            for (var w = function (t, e) {
                let n; const i = this instanceof w; const r = c(t); const o = void 0 === e;if (!i && r && t.constructor === w && o) return t;x ? r && !o && (t = t.source) : t instanceof w && (o && (e = l.call(t)), t = t.source), M && (n = !!e && e.indexOf('y') > -1) && (e = e.replace(/y/g, ''));const a = A(x ? new I(t, e) : I(t, e), i ? this : m, w);M && n && (f(a).sticky = !0);return a;
              }, y = function (t) {
                t in w || a(w, t, { configurable: !0, get() {
                  return I[t];
                }, set(e) {
                  I[t] = e;
                } });
              }, C = s(I), S = 0;C.length > S;)y(C[S++]);m.constructor = w, w.prototype = m, g(r, 'RegExp', w);
          }d('RegExp');
        }, function (t, e, n) {
          'use strict';const i = n(26); const r = n(10); const o = n(2); const A = n(9); const a = o('species');t.exports = function (t) {
            const e = i(t); const n = r.f;A && e && !e[a] && n(e, a, { configurable: !0, get() {
              return this;
            } });
          };
        }, function (t, e, n) {
          'use strict';const i = n(15); const r = n(4); const o = n(0); const A = n(53); const a = RegExp.prototype; const s = a.toString; const c = o((() => "/a/b" != s.call({ source: "a", flags: "b" }))); const l = 'toString' != s.name;(c || l) && i(RegExp.prototype, 'toString', (function () {
            const t = r(this); const e = String(t.source); const n = t.flags;return `/${e}/${String(void 0 === n && t instanceof RegExp && !('flags' in a) ? A.call(t) : n)}`;
          }), { unsafe: !0 });
        }, function (t, e, n) {
          'use strict';const i = n(9); const r = n(0); const o = n(82); const A = n(77); const a = n(73); const s = n(14); const c = n(38); const l = Object.assign; const u = Object.defineProperty;t.exports = !l || r((() => {
            if (i && 1 !== l({ b: 1 }, l(u({}, 'a', { enumerable: !0, get() {
              u(this, 'b', { value: 3, enumerable: !1 });
            } }), { b: 2 })).b) return !0;const t = {}; const e = {}; const n = Symbol();return t[n] = 7, 'abcdefghijklmnopqrst'.split('').forEach(((t) => {
              e[t] = t;
            })), 7 != l({}, t)[n] || 'abcdefghijklmnopqrst' != o(l({}, e)).join('');
          })) ? function (t, e) {
              for (var n = s(t), r = arguments.length, l = 1, u = A.f, g = a.f;r > l;) for (var h, f = c(arguments[l++]), d = u ? o(f).concat(u(f)) : o(f), p = d.length, I = 0;p > I;)h = d[I++], i && !g.call(f, h) || (n[h] = f[h]);return n;
            } : l;
        }, function (t, e, n) {
          const i = n(2); const r = n(52); const o = n(10); const A = i('unscopables'); const a = Array.prototype;null == a[A] && o.f(a, A, { configurable: !0, value: r(null) }), t.exports = function (t) {
            a[A][t] = !0;
          };
        }, function (t, e, n) {
          'use strict';const i = n(12); const r = n(137); const o = n(89); const A = n(81); const a = n(90); const s = n(8); const c = n(15); const l = n(2); const u = n(40); const g = n(56); const h = n(88); const f = h.IteratorPrototype; const d = h.BUGGY_SAFARI_ITERATORS; const p = l('iterator'); const I = function () {
            return this;
          };t.exports = function (t, e, n, l, h, m, v) {
            r(n, e, l);let b; let x; let M; const w = function (t) {
 if (t === h && D) return D;if (!d && t in S) return S[t];switch (t) {
 case 'keys':case 'values':case 'entries':return function () {
 return new n(this, t); 
}; 
} return function () {
 return new n(this); 
}; 
}; const y = `${e  } Iterator`; let C = !1; var S = t.prototype; const N = S[p] || S['@@iterator'] || h && S[h]; var D = !d && N || w(h); const j = 'Array' == e && S.entries || N;if (j && (b = o(j.call(new t)), f !== Object.prototype && b.next && (u || o(b) === f || (A ? A(b, f) : 'function' !== typeof b[p] && s(b, p, I)), a(b, y, !0, !0), u && (g[y] = I))), 'values' == h && N && 'values' !== N.name && (C = !0, D = function () {
              return N.call(this);
            }), u && !v || S[p] === D || s(S, p, D), g[e] = D, h) if (x = { values: w('values'), keys: m ? D : w('keys'), entries: w('entries') }, v) for (M in x)(d || C || !(M in S)) && c(S, M, x[M]);else i({ target: e, proto: !0, forced: d || C }, x);return x;
          };
        }, function (t, e, n) {
          'use strict';const i = n(88).IteratorPrototype; const r = n(52); const o = n(25); const A = n(90); const a = n(56); const s = function () {
            return this;
          };t.exports = function (t, e, n) {
            const c = `${e} Iterator`;return t.prototype = r(i, { next: o(1, n) }), A(t, c, !1, !0), a[c] = s, t;
          };
        }, function (t, e, n) {
          const i = n(0);t.exports = !i((() => {
            function t() {} return t.prototype.constructor = null, Object.getPrototypeOf(new t) !== t.prototype;
          }));
        }, function (t, e, n) {
          'use strict';n(92);
        }, function (t, e, n) {
          e = t.exports = n(17)(!1);const i = n(57); const r = i(n(141)); const o = i(n(93));e.push([t.i, `\n.item-txt[data-v-a536c00a] {\n    position: relative;\n    padding: 0 5px;\n}\n.item-txt .cur-search[data-v-a536c00a] .search-str {\n    color: rgb(255, 255, 255);\n    background: rgb(33, 136, 255);\n    outline: rgb(121, 184, 255) solid 1px;\n}\n.item-txt[data-v-a536c00a] .search-str {\n    color: rgb(36, 41, 46);\n    background: rgb(255, 223, 93);\n    outline: rgb(255, 223, 93) solid 1px;\n}\n.item-time[data-v-a536c00a] {\n    display: inline-block;\n    min-width: 166px;\n    color: #959da5;\n    font-weight: 400;\n    padding-right: 5px;\n}\n[data-v-a536c00a] a {\n    color: #3c96ff;\n    text-decoration: underline;\n}\n[data-v-a536c00a] a:active,[data-v-a536c00a] a:visited,[data-v-a536c00a] a:hover {\n    color: #3c96ff;\n}\n[data-v-a536c00a] a::selection,[data-v-a536c00a] .selection-color::selection {\n    background-color: rgba(70, 146, 222, 0.54);\n}\n.log-loading[data-v-a536c00a] {\n    position: absolute;\n    top: 50%;\n    transform: translateY(-50%);\n    width: 100%;\n    background: #1e1e1e;\n    z-index: 100;\n}\n.log-loading .lds-ring[data-v-a536c00a] {\n    display: inline-block;\n    position: relative;\n    width: 80px;\n    height: 80px;\n    left: 50%;\n    transform: translateX(-50%);\n}\n.log-loading .lds-ring div[data-v-a536c00a] {\n    box-sizing: border-box;\n    display: block;\n    position: absolute;\n    width: 37px;\n    height: 37px;\n    border: 3px solid #fff;\n    border-radius: 50%;\n    animation: lds-ring-data-v-a536c00a 1.2s cubic-bezier(0.5, 0, 0.5, 1) infinite;\n    border-color: #fff transparent transparent transparent;\n}\n.log-loading .lds-ring div[data-v-a536c00a]:nth-child(1) {\n    animation-delay: -0.45s;\n}\n.log-loading .lds-ring div[data-v-a536c00a]:nth-child(2) {\n    animation-delay: -0.3s;\n}\n.log-loading .lds-ring div[data-v-a536c00a]:nth-child(3) {\n    animation-delay: -0.15s;\n}\n@keyframes lds-ring-data-v-a536c00a {\n0% {\n        transform: rotate(0deg);\n}\n100% {\n        transform: rotate(360deg);\n}\n}\nul[data-v-a536c00a], li[data-v-a536c00a] {\n    margin: 0;\n    padding: 0;\n    list-style: none;\n}\n.scroll-home[data-v-a536c00a] {\n    position: relative;\n    height: 100%;\n    overflow-y: hidden;\n}\n.scroll-home.min-height[data-v-a536c00a] {\n    min-height: 20px;\n}\n.scroll-home.min-height.show-empty[data-v-a536c00a] {\n    min-height: 110px;\n}\n.scroll-home .list-empty[data-v-a536c00a] {\n    position: absolute;\n    background: url(${r}) center no-repeat;\n    background-size: contain;\n    height: 80px;\n    width: 220px;\n    box-sizing: border-box;\n    transform: translate(-50%, -50%);\n    text-align: center;\n    top: 45%;\n    left: 50%;\n    padding-top: 80px;\n    line-height: 21px;\n}\n.scroll-home .scroll-index[data-v-a536c00a] {\n    text-align: right;\n    user-select: none;\n}\n.scroll-home .scroll-index li[data-v-a536c00a] {\n    width: 100%;\n    color: rgba(166, 166, 166, 1)\n}\n.scroll-home .scroll-main[data-v-a536c00a] {\n    overflow: hidden;\n    margin-left: 20px;\n}\n.scroll-home .scroll-main .pointer[data-v-a536c00a] {\n    cursor: pointer;\n}\n.scroll-home .scroll-main .scroll-item[data-v-a536c00a] {\n    min-width: 100%;\n}\n.scroll-home .scroll-main .scroll-item.hover[data-v-a536c00a] {\n    background: #333030;\n}\n.scroll-home .scroll[data-v-a536c00a] {\n    position: absolute;\n    will-change: transform;\n    cursor: default;\n}\n.scroll-home .scroll .scroll-item[data-v-a536c00a] {\n    box-sizing: border-box;\n    position: absolute;\n}\n.scroll-item .log-folder[data-v-a536c00a] {\n    background-image: url(${o});\n    display: inline-block;\n    height: 16px;\n    width: 16px;\n    position: absolute;\n    cursor: pointer;\n    transform: rotate(0deg);\n    transition: transform 200ms;\n    top: 0;\n    right: -20px;\n}\n.scroll-item .log-folder.show-all[data-v-a536c00a] {\n    transform: rotate(-90deg);\n}\n.scroll-home .bottom-scroll[data-v-a536c00a] {\n    bottom: 0;\n    height: 15px;\n    background: rgba(121, 121, 121, 0.4);\n}\n.scroll-home .min-nav[data-v-a536c00a] {\n    position: absolute;\n    right: 0;\n    cursor: default;\n    user-select: none;\n}\n.scroll-home .min-nav:hover + span[data-v-a536c00a] {\n    background: rgba(121, 121, 121, 0.4);\n}\n.scroll-home .min-map[data-v-a536c00a] {\n    width: 6px;\n    box-shadow: #000000 -6px 0 6px -6px inset;\n}\n.scroll-home .min-nav-slide[data-v-a536c00a] {\n    position: absolute;\n    transition: opacity .1s linear;\n    will-change: transform;\n    cursor: default;\n    user-select: none;\n    right: 0;\n}\n.scroll-home .min-nav-slide.nav-show[data-v-a536c00a] {\n    background: rgba(121, 121, 121, 0.4);\n}\n.scroll-home .min-nav-slide[data-v-a536c00a]:hover {\n    background: rgba(121, 121, 121, 0.5);\n}\n.scroll-home .min-nav-slide[data-v-a536c00a]:active {\n    background: rgba(121, 121, 121, 0.55);\n}\n`, '']);
        }, function (t, e) {
          t.exports = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIAAAACACAMAAAD04JH5AAAAk1BMVEUAAADm5ubl5eXj4+Pm5ubn5+fn5+fn5+fm5ubn5+fm5ubm5ubm5ubl5eXm5ubj4+Pn5+fm5ubm5ubm5ubn5+fm5ubn5+fn5+fm5ubn5+fn5+fm5ubn5+fl5eXm5ubm5ubm5ubm5ubm5ubt7e3m5ubn5+fn5+fm5ubl5eXn5+fn5+fm5ubn5+fn5+fl5eXm5ubm5ubc4dUEAAAAMHRSTlMAv4BApCfdx2ZQmYh2Ny8HGOGOenBVSvPttagUoF5HzZ1ZMxz75pSEYiDV0g+7bD2PcXtrAAAC0UlEQVR42u3b2XKiQACF4QMKCALihvsYNYtmmTnv/3STgARkCEVjdzEX/d2mkvovToNWAJoi8da2TXQnWPDTGp15ZiJAVxwmBujKkgkfHdkwNa/4UXCCegFTIcp8kgaUOzD1jpIXfplANZOJMUqGTF2gWJ8JA7cmvAqgmMOEV744ZDZQKT+FUxQ9MDOEalWnsM9MH8qN+cXeILdmZgv1fvPLuXQw82God9hzPUABM88QcIl9szHUWpGC16DovF1SxMMINUzB/Y9mNkV9WKhh8JOJhtw9W7B/4WeWv/J2aGjGdh4HkMJlay+SbubtbUe4V/TK3N5ogEWGJeNenuq7GzRRNcX2oidemWhI6hTzE4DG5E7RYMoVDujzW3+EtiKmHiAc0BvImGLM1KFFAOIxM+OaKb6Hc38XoNqZqahNAEKH3wb412U+9Yxx7eeiKRNvaBWA9zVrPvkNFyww664CRssAYPLzFG3eeJIfUL6TORYKerxlKwqAuyxMsSZgqyoAx33lFE+8sYiVBWCzqpyix4J+AHUBwDO/rUfI+A4XrytvuutZI0BewKLie5BfnmKZzAC76pvgfJGft1+KA5zKS1vwWpii2gDvOusjbkTFKSoNmPOHX/KKU1QXkB9wFyXT4hTVBeTX/xlKdo+FKaoLsJa8+pjFFxT9sZkx1AXAZC31AVh3HQCj6wAMuw6A2XUAjl7HAYDlOx0F5EZR2CvbtgqQyNQBOkAH6AAdoAN0gA7QATpAB+gAHaADdIAO0AE6QAfoAB2gA3SADtABOkDkb06Z2EOiCRMrNDFQ8A6EI/IYh8uUC2kipnZowpL/FoTPVCj2f3gTkoRM2cJP1UoyFnxK9bSkzBmEY17FAocmaz5EuMsoNlu8WhOy4M24xyNzARqbUQFT7NIp3QpCdpRsCEFzSnWGsHCypCzeEW2cfIcSvL0c0ZrlDqbmPQZuCO2/9xdS5wlVk/kXiwAAAABJRU5ErkJggg==';
        }, function (t, e, n) {
          'use strict';n(94);
        }, function (t, e, n) {
          (t.exports = n(17)(!1)).push([t.i, '\n.bk-log-main[data-v-7aea2c36] {\n    position: relative;\n}\n.bk-log-tag[data-v-7aea2c36] {\n    display: flex;\n    align-items: center;\n    position: absolute;\n    top: 0;\n    left: 50%;\n    transform: translateX(-50%);\n    z-index: 10;\n    opacity: 0.8;\n    background: #252935;\n    border-radius: 3px;\n    color: #949595;\n    max-width: 480px;\n    overflow: hidden;\n}\n.bk-log-tag.overflow[data-v-7aea2c36] {\n    padding: 0 20px;\n}\n.bk-log-tag .bk-log-icon[data-v-7aea2c36] {\n    position: absolute;\n    line-height: 28px;\n    font-size: 22px;\n    background: #2e3342;\n    cursor: default;\n}\n.log-icon-angle-double-left[data-v-7aea2c36] {\n    left: 0;\n    top: 0;\n    border-radius: 3px 0 0 3px;\n}\n.log-icon-angle-double-right[data-v-7aea2c36] {\n    right: 0;\n    top: 0;\n    border-radius: 0 3px 3px 0;\n}\n.bk-log-tag[data-v-7aea2c36]:hover {\n    opacity: 1\n}\n.bk-log-tag-item[data-v-7aea2c36] {\n    margin: 3px 16px;\n    padding: 3px 9px;\n    line-height: 16px;\n    list-style: none;\n    transition: transform 200ms;\n}\n.bk-log-tag-item.select[data-v-7aea2c36] {\n    background: #2e3342;\n    border-radius: 11px;\n}\n.bk-log-tag-item[data-v-7aea2c36]:hover, .bk-log-icon.click[data-v-7aea2c36]:hover {\n    cursor: pointer;\n    color: #ffffff;\n}\n', '']);
        }, function (t, e, n) {
          'use strict';n(98);
        }, function (t, e, n) {
          (t.exports = n(17)(!1)).push([t.i, '\n.log-scroll[data-v-4749c4a0] {\n    flex: 1;\n    color: #ffffff;\n    font-family: Consolas, "Courier New", monospace;\n    font-weight: normal;\n    cursor: text;\n    white-space: nowrap;\n    letter-spacing: 0px;\n    font-size: 12px;\n    line-height: 16px;\n    margin-left: 10px;\n    margin-top: 5px;\n}\n', '']);
        }, function (t, e, n) {
          'use strict';const i = n(7);Object.defineProperty(e, '__esModule', { value: !0 }), e.default = void 0;const r = i(n(147));r.default.install = function (t) {
            t.component(r.default.name, r.default);
          };const o = r.default;e.default = o;
        }, function (t, e, n) {
          'use strict';n.r(e);const i = n(59); const r = n(34);for (const o in r)['default'].indexOf(o) < 0 && (function (t) {
            n.d(e, t, (() => r[t]));
          }(o));n(157);const A = n(6); const a = Object(A.a)(r.default, i.a, i.b, !1, null, '7e72b2fb', null);a.options.__file = 'src/multipleLog/multiple-log.vue', e.default = a.exports;
        }, function (t, e, n) {
          'use strict';const i = n(12); const r = n(23); const o = [].reverse; const A = [1, 2];i({ target: 'Array', proto: !0, forced: String(A) === String(A.reverse()) }, { reverse() {
            return r(this) && (this.length = this.length), o.call(this);
          } });
        }, function (t, e, n) {
          'use strict';const i = n(12); const r = n(3); const o = n(23); const A = n(76); const a = n(13); const s = n(21); const c = n(78); const l = n(2); const u = n(51)('slice'); const g = l('species'); const h = [].slice; const f = Math.max;i({ target: 'Array', proto: !0, forced: !u }, { slice(t, e) {
            let n; let i; let l; const u = s(this); const d = a(u.length); let p = A(t, d); const I = A(void 0 === e ? d : e, d);if (o(u) && ('function' !== typeof(n = u.constructor) || n !== Array && !o(n.prototype) ? r(n) && null === (n = n[g]) && (n = void 0) : n = void 0, n === Array || void 0 === n)) return h.call(u, p, I);for (i = new(void 0 === n ? Array : n)(f(I - p, 0)), l = 0;p < I;p++, l++)p in u && c(i, l, u[p]);return i.length = l, i;
          } });
        }, function (t, e, n) {
          'use strict';const i = n(12); const r = n(64).map;i({ target: 'Array', proto: !0, forced: !n(51)('map') }, { map(t) {
            return r(this, t, arguments.length > 1 ? arguments[1] : void 0);
          } });
        }, function (t, e, n) {
          const i = n(152); const r = n(153); const o = n(154); const A = n(156);t.exports = function (t) {
            return i(t) || r(t) || o(t) || A();
          }, t.exports.default = t.exports, t.exports.__esModule = !0;
        }, function (t, e) {
          t.exports = function (t) {
            if (Array.isArray(t)) return t;
          }, t.exports.default = t.exports, t.exports.__esModule = !0;
        }, function (t, e) {
          t.exports = function (t) {
            if ('undefined' !== typeof Symbol && null != t[Symbol.iterator] || null != t['@@iterator']) return Array.from(t);
          }, t.exports.default = t.exports, t.exports.__esModule = !0;
        }, function (t, e, n) {
          const i = n(155);t.exports = function (t, e) {
            if (t) {
              if ('string' === typeof t) return i(t, e);let n = Object.prototype.toString.call(t).slice(8, -1);return 'Object' === n && t.constructor && (n = t.constructor.name), 'Map' === n || 'Set' === n ? Array.from(t) : 'Arguments' === n || /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(n) ? i(t, e) : void 0;
            }
          }, t.exports.default = t.exports, t.exports.__esModule = !0;
        }, function (t, e) {
          t.exports = function (t, e) {
            (null == e || e > t.length) && (e = t.length);for (var n = 0, i = new Array(e);n < e;n++)i[n] = t[n];return i;
          }, t.exports.default = t.exports, t.exports.__esModule = !0;
        }, function (t, e) {
          t.exports = function () {
            throw new TypeError('Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.');
          }, t.exports.default = t.exports, t.exports.__esModule = !0;
        }, function (t, e, n) {
          'use strict';n(99);
        }, function (t, e, n) {
          e = t.exports = n(17)(!1);const i = n(57)(n(93));e.push([t.i, `\n.multiple-log[data-v-7e72b2fb] {\n    height: 100%;\n    background: #1e1e1e;\n}\n.job-plugin-list-log[data-v-7e72b2fb] {\n    height: 100%;\n    overflow: auto;\n}\n[data-v-7e72b2fb] .log-loading .lds-ring {\n    height: 15px;\n    width: 15px;\n}\n[data-v-7e72b2fb] .log-loading .lds-ring div {\n    height: 16px;\n    width: 16px;\n}\n.job-plugin-list-log .log-scroll[data-v-7e72b2fb] {\n    margin: 0 20px;\n}\n.plugin-item[data-v-7e72b2fb] {\n    color: #ffffff;\n    font-family: Consolas, "Courier New", monospace;\n    font-weight: normal;\n    font-size: 12px;\n    line-height: 16px;\n}\n.plugin-item .item-head[data-v-7e72b2fb] {\n    display: flex;\n    justify-items: center;\n    cursor: pointer;\n    padding: 8px;\n}\n.plugin-item .log-folder[data-v-7e72b2fb] {\n    background-image: url(${i});\n    display: inline-block;\n    height: 16px;\n    width: 16px;\n    cursor: pointer;\n    transform: rotate(-90deg);\n    transition: transform 200ms;\n}\n.plugin-item .log-folder.show-all[data-v-7e72b2fb] {\n    transform: rotate(0deg);\n}\n[data-v-7e72b2fb] .log-status {\n    width: 14px;\n    height: 15px;\n    margin: 0 9px;\n    padding: 1px 0;\n}\n[data-v-7e72b2fb] .log-status svg {\n    width: 14px;\n    height: 14px;\n}\n[data-v-7e72b2fb] .log-status i:before {\n    top: -13px;\n    left: 1px;\n    position: absolute;\n}\n.log-scroll[data-v-7e72b2fb] {\n    flex: 1;\n    color: #ffffff;\n    font-family: Consolas, "Courier New", monospace;\n    font-weight: normal;\n    cursor: text;\n    white-space: nowrap;\n    letter-spacing: 0px;\n    font-size: 12px;\n    line-height: 16px;\n}\n`, '']);
        }, function (t, e, n) {
          'use strict';const i = n(7);Object.defineProperty(e, '__esModule', { value: !0 }), e.default = void 0;const r = i(n(160));r.default.install = function (t) {
            t.component(r.default.name, r.default);
          };const o = r.default;e.default = o;
        }, function (t, e, n) {
          'use strict';n.r(e);const i = n(60); const r = n(36);for (const o in r)['default'].indexOf(o) < 0 && (function (t) {
            n.d(e, t, (() => r[t]));
          }(o));n(162);const A = n(6); const a = Object(A.a)(r.default, i.a, i.b, !1, null, '4f9684e6', null);a.options.__file = 'src/logSearch/log-search.vue', e.default = a.exports;
        }, function (t, e) {
          t.exports = 'data:image/svg+xml;base64,PHN2ZyBjbGFzcz0ibGRzLXNwaW4iIHdpZHRoPSI4MHB4IiBoZWlnaHQ9IjgwcHgiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIgeG1sbnM6eGxpbms9Imh0dHA6Ly93d3cudzMub3JnLzE5OTkveGxpbmsiIHZpZXdCb3g9IjAgMCAxMDAgMTAwIiBwcmVzZXJ2ZUFzcGVjdFJhdGlvPSJ4TWlkWU1pZCI+DQogIDxnIHRyYW5zZm9ybT0idHJhbnNsYXRlKDgwLDUwKSI+DQogICAgPGcgdHJhbnNmb3JtPSJyb3RhdGUoMCkiPg0KICAgICAgPGNpcmNsZSBjeD0iMCIgY3k9IjAiIHI9IjUiIGZpbGw9IiMzYTg0ZmYiIGZpbGwtb3BhY2l0eT0iMSIgdHJhbnNmb3JtPSJzY2FsZSgxLjA3NjY3IDEuMDc2NjcpIj4NCiAgICAgICAgPGFuaW1hdGVUcmFuc2Zvcm0gYXR0cmlidXRlTmFtZT0idHJhbnNmb3JtIiB0eXBlPSJzY2FsZSIgYmVnaW49Ii0wLjkxNjY2NjY2NjY2NjY2NjZzIiB2YWx1ZXM9IjEuMiAxLjI7MSAxIiBrZXlUaW1lcz0iMDsxIiBkdXI9IjFzIiByZXBlYXRDb3VudD0iaW5kZWZpbml0ZSI+PC9hbmltYXRlVHJhbnNmb3JtPg0KICAgICAgICA8YW5pbWF0ZSBhdHRyaWJ1dGVOYW1lPSJmaWxsLW9wYWNpdHkiIGtleVRpbWVzPSIwOzEiIGR1cj0iMXMiIHJlcGVhdENvdW50PSJpbmRlZmluaXRlIiB2YWx1ZXM9IjE7MCIgYmVnaW49Ii0wLjkxNjY2NjY2NjY2NjY2NjZzIj48L2FuaW1hdGU+DQogICAgICA8L2NpcmNsZT4NCiAgICA8L2c+DQogIDwvZz4NCiAgPGcgdHJhbnNmb3JtPSJ0cmFuc2xhdGUoNzUuOTgwNzYyMTEzNTMzMTYsNjUpIj4NCiAgICA8ZyB0cmFuc2Zvcm09InJvdGF0ZSgyOS45OTk5OTk5OTk5OTk5OTYpIj4NCiAgICAgIDxjaXJjbGUgY3g9IjAiIGN5PSIwIiByPSI1IiBmaWxsPSIjM2E4NGZmIiBmaWxsLW9wYWNpdHk9IjAuOTE2NjY2NjY2NjY2NjY2NiIgdHJhbnNmb3JtPSJzY2FsZSgxLjA5MzMzIDEuMDkzMzMpIj4NCiAgICAgICAgPGFuaW1hdGVUcmFuc2Zvcm0gYXR0cmlidXRlTmFtZT0idHJhbnNmb3JtIiB0eXBlPSJzY2FsZSIgYmVnaW49Ii0wLjgzMzMzMzMzMzMzMzMzMzRzIiB2YWx1ZXM9IjEuMiAxLjI7MSAxIiBrZXlUaW1lcz0iMDsxIiBkdXI9IjFzIiByZXBlYXRDb3VudD0iaW5kZWZpbml0ZSI+PC9hbmltYXRlVHJhbnNmb3JtPg0KICAgICAgICA8YW5pbWF0ZSBhdHRyaWJ1dGVOYW1lPSJmaWxsLW9wYWNpdHkiIGtleVRpbWVzPSIwOzEiIGR1cj0iMXMiIHJlcGVhdENvdW50PSJpbmRlZmluaXRlIiB2YWx1ZXM9IjE7MCIgYmVnaW49Ii0wLjgzMzMzMzMzMzMzMzMzMzRzIj48L2FuaW1hdGU+DQogICAgICA8L2NpcmNsZT4NCiAgICA8L2c+DQogIDwvZz4NCiAgPGcgdHJhbnNmb3JtPSJ0cmFuc2xhdGUoNjUsNzUuOTgwNzYyMTEzNTMzMTYpIj4NCiAgICA8ZyB0cmFuc2Zvcm09InJvdGF0ZSg1OS45OTk5OTk5OTk5OTk5OSkiPg0KICAgICAgPGNpcmNsZSBjeD0iMCIgY3k9IjAiIHI9IjUiIGZpbGw9IiMzYTg0ZmYiIGZpbGwtb3BhY2l0eT0iMC44MzMzMzMzMzMzMzMzMzM0IiB0cmFuc2Zvcm09InNjYWxlKDEuMTEgMS4xMSkiPg0KICAgICAgICA8YW5pbWF0ZVRyYW5zZm9ybSBhdHRyaWJ1dGVOYW1lPSJ0cmFuc2Zvcm0iIHR5cGU9InNjYWxlIiBiZWdpbj0iLTAuNzVzIiB2YWx1ZXM9IjEuMiAxLjI7MSAxIiBrZXlUaW1lcz0iMDsxIiBkdXI9IjFzIiByZXBlYXRDb3VudD0iaW5kZWZpbml0ZSI+PC9hbmltYXRlVHJhbnNmb3JtPg0KICAgICAgICA8YW5pbWF0ZSBhdHRyaWJ1dGVOYW1lPSJmaWxsLW9wYWNpdHkiIGtleVRpbWVzPSIwOzEiIGR1cj0iMXMiIHJlcGVhdENvdW50PSJpbmRlZmluaXRlIiB2YWx1ZXM9IjE7MCIgYmVnaW49Ii0wLjc1cyI+PC9hbmltYXRlPg0KICAgICAgPC9jaXJjbGU+DQogICAgPC9nPg0KICA8L2c+DQogIDxnIHRyYW5zZm9ybT0idHJhbnNsYXRlKDUwLDgwKSI+DQogICAgPGcgdHJhbnNmb3JtPSJyb3RhdGUoOTApIj4NCiAgICAgIDxjaXJjbGUgY3g9IjAiIGN5PSIwIiByPSI1IiBmaWxsPSIjM2E4NGZmIiBmaWxsLW9wYWNpdHk9IjAuNzUiIHRyYW5zZm9ybT0ic2NhbGUoMS4xMjY2NyAxLjEyNjY3KSI+DQogICAgICAgIDxhbmltYXRlVHJhbnNmb3JtIGF0dHJpYnV0ZU5hbWU9InRyYW5zZm9ybSIgdHlwZT0ic2NhbGUiIGJlZ2luPSItMC42NjY2NjY2NjY2NjY2NjY2cyIgdmFsdWVzPSIxLjIgMS4yOzEgMSIga2V5VGltZXM9IjA7MSIgZHVyPSIxcyIgcmVwZWF0Q291bnQ9ImluZGVmaW5pdGUiPjwvYW5pbWF0ZVRyYW5zZm9ybT4NCiAgICAgICAgPGFuaW1hdGUgYXR0cmlidXRlTmFtZT0iZmlsbC1vcGFjaXR5IiBrZXlUaW1lcz0iMDsxIiBkdXI9IjFzIiByZXBlYXRDb3VudD0iaW5kZWZpbml0ZSIgdmFsdWVzPSIxOzAiIGJlZ2luPSItMC42NjY2NjY2NjY2NjY2NjY2cyI+PC9hbmltYXRlPg0KICAgICAgPC9jaXJjbGU+DQogICAgPC9nPg0KICA8L2c+DQogIDxnIHRyYW5zZm9ybT0idHJhbnNsYXRlKDM1LjAwMDAwMDAwMDAwMDAxLDc1Ljk4MDc2MjExMzUzMzE2KSI+DQogICAgPGcgdHJhbnNmb3JtPSJyb3RhdGUoMTE5Ljk5OTk5OTk5OTk5OTk5KSI+DQogICAgICA8Y2lyY2xlIGN4PSIwIiBjeT0iMCIgcj0iNSIgZmlsbD0iIzNhODRmZiIgZmlsbC1vcGFjaXR5PSIwLjY2NjY2NjY2NjY2NjY2NjYiIHRyYW5zZm9ybT0ic2NhbGUoMS4xNDMzMyAxLjE0MzMzKSI+DQogICAgICAgIDxhbmltYXRlVHJhbnNmb3JtIGF0dHJpYnV0ZU5hbWU9InRyYW5zZm9ybSIgdHlwZT0ic2NhbGUiIGJlZ2luPSItMC41ODMzMzMzMzMzMzMzMzM0cyIgdmFsdWVzPSIxLjIgMS4yOzEgMSIga2V5VGltZXM9IjA7MSIgZHVyPSIxcyIgcmVwZWF0Q291bnQ9ImluZGVmaW5pdGUiPjwvYW5pbWF0ZVRyYW5zZm9ybT4NCiAgICAgICAgPGFuaW1hdGUgYXR0cmlidXRlTmFtZT0iZmlsbC1vcGFjaXR5IiBrZXlUaW1lcz0iMDsxIiBkdXI9IjFzIiByZXBlYXRDb3VudD0iaW5kZWZpbml0ZSIgdmFsdWVzPSIxOzAiIGJlZ2luPSItMC41ODMzMzMzMzMzMzMzMzM0cyI+PC9hbmltYXRlPg0KICAgICAgPC9jaXJjbGU+DQogICAgPC9nPg0KICA8L2c+DQogIDxnIHRyYW5zZm9ybT0idHJhbnNsYXRlKDI0LjAxOTIzNzg4NjQ2Njg0LDY1KSI+DQogICAgPGcgdHJhbnNmb3JtPSJyb3RhdGUoMTUwLjAwMDAwMDAwMDAwMDAzKSI+DQogICAgICA8Y2lyY2xlIGN4PSIwIiBjeT0iMCIgcj0iNSIgZmlsbD0iIzNhODRmZiIgZmlsbC1vcGFjaXR5PSIwLjU4MzMzMzMzMzMzMzMzMzQiIHRyYW5zZm9ybT0ic2NhbGUoMS4xNiAxLjE2KSI+DQogICAgICAgIDxhbmltYXRlVHJhbnNmb3JtIGF0dHJpYnV0ZU5hbWU9InRyYW5zZm9ybSIgdHlwZT0ic2NhbGUiIGJlZ2luPSItMC41cyIgdmFsdWVzPSIxLjIgMS4yOzEgMSIga2V5VGltZXM9IjA7MSIgZHVyPSIxcyIgcmVwZWF0Q291bnQ9ImluZGVmaW5pdGUiPjwvYW5pbWF0ZVRyYW5zZm9ybT4NCiAgICAgICAgPGFuaW1hdGUgYXR0cmlidXRlTmFtZT0iZmlsbC1vcGFjaXR5IiBrZXlUaW1lcz0iMDsxIiBkdXI9IjFzIiByZXBlYXRDb3VudD0iaW5kZWZpbml0ZSIgdmFsdWVzPSIxOzAiIGJlZ2luPSItMC41cyI+PC9hbmltYXRlPg0KICAgICAgPC9jaXJjbGU+DQogICAgPC9nPg0KICA8L2c+DQogIDxnIHRyYW5zZm9ybT0idHJhbnNsYXRlKDIwLDUwLjAwMDAwMDAwMDAwMDAxKSI+DQogICAgPGcgdHJhbnNmb3JtPSJyb3RhdGUoMTgwKSI+DQogICAgICA8Y2lyY2xlIGN4PSIwIiBjeT0iMCIgcj0iNSIgZmlsbD0iIzNhODRmZiIgZmlsbC1vcGFjaXR5PSIwLjUiIHRyYW5zZm9ybT0ic2NhbGUoMS4xNzY2NyAxLjE3NjY3KSI+DQogICAgICAgIDxhbmltYXRlVHJhbnNmb3JtIGF0dHJpYnV0ZU5hbWU9InRyYW5zZm9ybSIgdHlwZT0ic2NhbGUiIGJlZ2luPSItMC40MTY2NjY2NjY2NjY2NjY3cyIgdmFsdWVzPSIxLjIgMS4yOzEgMSIga2V5VGltZXM9IjA7MSIgZHVyPSIxcyIgcmVwZWF0Q291bnQ9ImluZGVmaW5pdGUiPjwvYW5pbWF0ZVRyYW5zZm9ybT4NCiAgICAgICAgPGFuaW1hdGUgYXR0cmlidXRlTmFtZT0iZmlsbC1vcGFjaXR5IiBrZXlUaW1lcz0iMDsxIiBkdXI9IjFzIiByZXBlYXRDb3VudD0iaW5kZWZpbml0ZSIgdmFsdWVzPSIxOzAiIGJlZ2luPSItMC40MTY2NjY2NjY2NjY2NjY3cyI+PC9hbmltYXRlPg0KICAgICAgPC9jaXJjbGU+DQogICAgPC9nPg0KICA8L2c+DQogIDxnIHRyYW5zZm9ybT0idHJhbnNsYXRlKDI0LjAxOTIzNzg4NjQ2NjgzNiwzNS4wMDAwMDAwMDAwMDAwMSkiPg0KICAgIDxnIHRyYW5zZm9ybT0icm90YXRlKDIwOS45OTk5OTk5OTk5OTk5NykiPg0KICAgICAgPGNpcmNsZSBjeD0iMCIgY3k9IjAiIHI9IjUiIGZpbGw9IiMzYTg0ZmYiIGZpbGwtb3BhY2l0eT0iMC40MTY2NjY2NjY2NjY2NjY3IiB0cmFuc2Zvcm09InNjYWxlKDEuMTkzMzMgMS4xOTMzMykiPg0KICAgICAgICA8YW5pbWF0ZVRyYW5zZm9ybSBhdHRyaWJ1dGVOYW1lPSJ0cmFuc2Zvcm0iIHR5cGU9InNjYWxlIiBiZWdpbj0iLTAuMzMzMzMzMzMzMzMzMzMzM3MiIHZhbHVlcz0iMS4yIDEuMjsxIDEiIGtleVRpbWVzPSIwOzEiIGR1cj0iMXMiIHJlcGVhdENvdW50PSJpbmRlZmluaXRlIj48L2FuaW1hdGVUcmFuc2Zvcm0+DQogICAgICAgIDxhbmltYXRlIGF0dHJpYnV0ZU5hbWU9ImZpbGwtb3BhY2l0eSIga2V5VGltZXM9IjA7MSIgZHVyPSIxcyIgcmVwZWF0Q291bnQ9ImluZGVmaW5pdGUiIHZhbHVlcz0iMTswIiBiZWdpbj0iLTAuMzMzMzMzMzMzMzMzMzMzM3MiPjwvYW5pbWF0ZT4NCiAgICAgIDwvY2lyY2xlPg0KICAgIDwvZz4NCiAgPC9nPg0KICA8ZyB0cmFuc2Zvcm09InRyYW5zbGF0ZSgzNC45OTk5OTk5OTk5OTk5ODYsMjQuMDE5MjM3ODg2NDY2ODQ3KSI+DQogICAgPGcgdHJhbnNmb3JtPSJyb3RhdGUoMjM5Ljk5OTk5OTk5OTk5OTk3KSI+DQogICAgICA8Y2lyY2xlIGN4PSIwIiBjeT0iMCIgcj0iNSIgZmlsbD0iIzNhODRmZiIgZmlsbC1vcGFjaXR5PSIwLjMzMzMzMzMzMzMzMzMzMzMiIHRyYW5zZm9ybT0ic2NhbGUoMS4wMSAxLjAxKSI+DQogICAgICAgIDxhbmltYXRlVHJhbnNmb3JtIGF0dHJpYnV0ZU5hbWU9InRyYW5zZm9ybSIgdHlwZT0ic2NhbGUiIGJlZ2luPSItMC4yNXMiIHZhbHVlcz0iMS4yIDEuMjsxIDEiIGtleVRpbWVzPSIwOzEiIGR1cj0iMXMiIHJlcGVhdENvdW50PSJpbmRlZmluaXRlIj48L2FuaW1hdGVUcmFuc2Zvcm0+DQogICAgICAgIDxhbmltYXRlIGF0dHJpYnV0ZU5hbWU9ImZpbGwtb3BhY2l0eSIga2V5VGltZXM9IjA7MSIgZHVyPSIxcyIgcmVwZWF0Q291bnQ9ImluZGVmaW5pdGUiIHZhbHVlcz0iMTswIiBiZWdpbj0iLTAuMjVzIj48L2FuaW1hdGU+DQogICAgICA8L2NpcmNsZT4NCiAgICA8L2c+DQogIDwvZz4NCiAgPGcgdHJhbnNmb3JtPSJ0cmFuc2xhdGUoNDkuOTk5OTk5OTk5OTk5OTksMjApIj4NCiAgICA8ZyB0cmFuc2Zvcm09InJvdGF0ZSgyNzApIj4NCiAgICAgIDxjaXJjbGUgY3g9IjAiIGN5PSIwIiByPSI1IiBmaWxsPSIjM2E4NGZmIiBmaWxsLW9wYWNpdHk9IjAuMjUiIHRyYW5zZm9ybT0ic2NhbGUoMS4wMjY2NyAxLjAyNjY3KSI+DQogICAgICAgIDxhbmltYXRlVHJhbnNmb3JtIGF0dHJpYnV0ZU5hbWU9InRyYW5zZm9ybSIgdHlwZT0ic2NhbGUiIGJlZ2luPSItMC4xNjY2NjY2NjY2NjY2NjY2NnMiIHZhbHVlcz0iMS4yIDEuMjsxIDEiIGtleVRpbWVzPSIwOzEiIGR1cj0iMXMiIHJlcGVhdENvdW50PSJpbmRlZmluaXRlIj48L2FuaW1hdGVUcmFuc2Zvcm0+DQogICAgICAgIDxhbmltYXRlIGF0dHJpYnV0ZU5hbWU9ImZpbGwtb3BhY2l0eSIga2V5VGltZXM9IjA7MSIgZHVyPSIxcyIgcmVwZWF0Q291bnQ9ImluZGVmaW5pdGUiIHZhbHVlcz0iMTswIiBiZWdpbj0iLTAuMTY2NjY2NjY2NjY2NjY2NjZzIj48L2FuaW1hdGU+DQogICAgICA8L2NpcmNsZT4NCiAgICA8L2c+DQogIDwvZz4NCiAgPGcgdHJhbnNmb3JtPSJ0cmFuc2xhdGUoNjUsMjQuMDE5MjM3ODg2NDY2ODQzKSI+DQogICAgPGcgdHJhbnNmb3JtPSJyb3RhdGUoMzAwLjAwMDAwMDAwMDAwMDA2KSI+DQogICAgICA8Y2lyY2xlIGN4PSIwIiBjeT0iMCIgcj0iNSIgZmlsbD0iIzNhODRmZiIgZmlsbC1vcGFjaXR5PSIwLjE2NjY2NjY2NjY2NjY2NjY2IiB0cmFuc2Zvcm09InNjYWxlKDEuMDQzMzMgMS4wNDMzMykiPg0KICAgICAgICA8YW5pbWF0ZVRyYW5zZm9ybSBhdHRyaWJ1dGVOYW1lPSJ0cmFuc2Zvcm0iIHR5cGU9InNjYWxlIiBiZWdpbj0iLTAuMDgzMzMzMzMzMzMzMzMzMzNzIiB2YWx1ZXM9IjEuMiAxLjI7MSAxIiBrZXlUaW1lcz0iMDsxIiBkdXI9IjFzIiByZXBlYXRDb3VudD0iaW5kZWZpbml0ZSI+PC9hbmltYXRlVHJhbnNmb3JtPg0KICAgICAgICA8YW5pbWF0ZSBhdHRyaWJ1dGVOYW1lPSJmaWxsLW9wYWNpdHkiIGtleVRpbWVzPSIwOzEiIGR1cj0iMXMiIHJlcGVhdENvdW50PSJpbmRlZmluaXRlIiB2YWx1ZXM9IjE7MCIgYmVnaW49Ii0wLjA4MzMzMzMzMzMzMzMzMzMzcyI+PC9hbmltYXRlPg0KICAgICAgPC9jaXJjbGU+DQogICAgPC9nPg0KICA8L2c+DQogIDxnIHRyYW5zZm9ybT0idHJhbnNsYXRlKDc1Ljk4MDc2MjExMzUzMzE2LDM0Ljk5OTk5OTk5OTk5OTk4NikiPg0KICAgIDxnIHRyYW5zZm9ybT0icm90YXRlKDMyOS45OTk5OTk5OTk5OTk5NCkiPg0KICAgICAgPGNpcmNsZSBjeD0iMCIgY3k9IjAiIHI9IjUiIGZpbGw9IiMzYTg0ZmYiIGZpbGwtb3BhY2l0eT0iMC4wODMzMzMzMzMzMzMzMzMzMyIgdHJhbnNmb3JtPSJzY2FsZSgxLjA2IDEuMDYpIj4NCiAgICAgICAgPGFuaW1hdGVUcmFuc2Zvcm0gYXR0cmlidXRlTmFtZT0idHJhbnNmb3JtIiB0eXBlPSJzY2FsZSIgYmVnaW49IjBzIiB2YWx1ZXM9IjEuMiAxLjI7MSAxIiBrZXlUaW1lcz0iMDsxIiBkdXI9IjFzIiByZXBlYXRDb3VudD0iaW5kZWZpbml0ZSI+PC9hbmltYXRlVHJhbnNmb3JtPg0KICAgICAgICA8YW5pbWF0ZSBhdHRyaWJ1dGVOYW1lPSJmaWxsLW9wYWNpdHkiIGtleVRpbWVzPSIwOzEiIGR1cj0iMXMiIHJlcGVhdENvdW50PSJpbmRlZmluaXRlIiB2YWx1ZXM9IjE7MCIgYmVnaW49IjBzIj48L2FuaW1hdGU+DQogICAgICA8L2NpcmNsZT4NCiAgICA8L2c+DQogIDwvZz4NCjwvc3ZnPg==';
        }, function (t, e, n) {
          'use strict';n(100);
        }, function (t, e, n) {
          (t.exports = n(17)(!1)).push([t.i, '\n.log-tools[data-v-4f9684e6] {\n    display: inline-flex;\n    align-items: center;\n    line-height: 30px;\n    user-select: none;\n    padding: 0;\n    margin: 0;\n    background: #1e1e1e;\n    position: relative;\n    z-index: 2;\n}\n.log-tools .tool-search[data-v-4f9684e6] {\n    font-size: 12px;\n    display: inline-flex;\n    height: 30px;\n    align-items: center;\n    justify-content: space-around;\n}\n.log-tools .tool-search .searct-input[data-v-4f9684e6] {\n    position: relative;\n    height: 26px;\n    margin-right: 5px;\n}\n.log-tools .tool-search .searct-input input[data-v-4f9684e6] {\n    vertical-align: super;\n    border: 0;\n    box-shadow: none;\n    outline: none;\n    width: 150px;\n    padding: 0 30px 0 8px;\n    line-height: 26px;\n    border-radius: 3px;\n    color: #f6f8fa;\n    background-color: hsla(0,0%,100%,.125);\n}\n.log-tools .tool-search .searct-input .log-icon-search.search-icon[data-v-4f9684e6] {\n    font-size: 14px;\n    top: 7px;\n}\n.log-tools .tool-search .searct-input .search-icon[data-v-4f9684e6] {\n    position: absolute;\n    height: 20px;\n    width: 20px;\n    top: 4px;\n    right: 5px;\n}\n.log-tools .tool-search .searct-input .search-icon.log-icon-search[data-v-4f9684e6] {\n    font-size: 16px;\n    top: 6px;\n}\n.log-tools .tool-search .searct-input .search-icon.log-icon-close-circle-shape[data-v-4f9684e6] {\n    cursor: pointer;\n    font-size: 14px;\n    top: 7px;\n}\n.log-tools .tool-search .searct-input .search-icon.log-icon-close-circle-shape[data-v-4f9684e6]:hover {\n    color: #979ba5;\n}\n.log-tools .tool-search .search-num[data-v-4f9684e6] {\n    color: #fff;\n}\n.log-tools .tool-search .icon-click[data-v-4f9684e6] {\n    cursor: pointer;\n    width: 25px;\n    height: 25px;\n    font-size: 25px;\n    color: #fff;\n}\n.log-tools .tool-search .icon-click[data-v-4f9684e6]:hover {\n    background-color: #2f363d;\n}\n.tool-more[data-v-4f9684e6] {\n    position: relative;\n    height: 32px;\n    width: 15px;\n}\n.tool-more .more-icon[data-v-4f9684e6] {\n    cursor: pointer;\n    transform: rotate(90deg);\n    font-size: 24px;\n    line-height: 32px;\n    color: #fff;\n}\n.tool-more .more-list[data-v-4f9684e6] {\n    position: absolute;\n    top: 100%;\n    right: -6px;\n    left: auto;\n    width: 180px;\n    color: #fff;\n    background: #2f363d;\n    border-color: #444d56;\n    box-shadow: 0 1px 15px rgba(27,31,35,.15);\n    border: 1px solid #444d56;\n    border-radius: 4px;\n    margin: 5px 0;\n    z-index: 101;\n}\n.tool-more .more-list[data-v-4f9684e6]:before {\n    position: absolute;\n    display: inline-block;\n    content: "";\n    border: 8px solid transparent;\n    top: -16px;\n    right: 0;\n    left: auto;\n    border-bottom-color: #444d56;\n}\n.tool-more .more-list .more-button[data-v-4f9684e6] {\n    cursor: pointer;\n    color: #fff;\n    width: 100%;\n    text-align: left;\n    display: block;\n    padding: 4px 8px 4px 22px;\n    overflow: hidden;\n    text-overflow: ellipsis;\n    white-space: nowrap;\n    font-size: 12px;\n    line-height: 26px;\n}\n.tool-more .more-list .more-button[data-v-4f9684e6]:hover {\n    background: #0366d6;\n}\n.tool-more .more-list .more-button[data-v-4f9684e6]:not(:last-child) {\n    border-bottom: 1px solid #444D56;\n}\n.log-execute[data-v-4f9684e6] {\n    width: 100px;\n    margin-right: 10px;\n    color: #c2cade;\n    font-size: 14px;\n}\n.log-execute[data-v-4f9684e6]:hover {\n    color: #fff;\n    background: #292c2d;\n}\n.bk-log-execute[data-v-4f9684e6] {\n    color: #c2cade;\n    background: #222529;\n    height: 30px;\n    text-indent: 8px;\n    cursor: pointer;\n    border: 1px solid #444d56;\n    border-radius: 2px;\n    position: relative;\n}\n.log-execute-option[data-v-4f9684e6] {\n    height: 30px;\n    text-indent: 8px;\n    cursor: pointer;\n    background: #222529;\n}\n.log-execute-option[data-v-4f9684e6]:hover {\n    background: #0366d6;\n    color: #c2cade;\n}\n.bk-log-option-list[data-v-4f9684e6] {\n    border: 1px solid #444d56;\n    border-radius: 2px;\n    text-indent: 14px;\n}\n.bk-select-angle[data-v-4f9684e6] {\n    font-size: 22px;\n    position: absolute;\n    right: 2px;\n    top: 4px;\n    text-indent: 0;\n    transition: transform .3s cubic-bezier(.4,0,.2,1);\n}\n.bk-select-angle.show[data-v-4f9684e6] {\n    transform: rotate(-180deg);\n}\n', '']);
        }, function (t, e, n) {
          const i = n(16); let r = n(165);'string' === typeof(r = r.__esModule ? r.default : r) && (r = [[t.i, r, '']]);const o = { insert: 'head', singleton: !1 };i(r, o);t.exports = r.locals || {};
        }, function (t, e, n) {
          e = t.exports = n(17)(!1);const i = n(57); const r = i(`${n(166)}#iconcool`); const o = i(n(167)); const A = i(n(168)); const a = i(`${n(169)}?#iefix`);e.push([t.i, `@font-face {\n\tfont-family: "bk-log";\n\tsrc: url(${r}) format("svg"),\nurl(${o}) format("truetype"),\nurl(${A}) format("woff"),\nurl(${a}) format("embedded-opentype");\n    font-weight: normal;\n    font-style: normal;\n}\n\n.bk-log-icon {\n  /* use !important to prevent issues with browser extensions that change fonts */\n  font-family: 'bk-log' !important;\n  speak: none;\n  font-style: normal;\n  font-weight: normal;\n  font-variant: normal;\n  text-transform: none;\n  line-height: 1;\n  text-align: center;\n  /* Better Font Rendering =========== */\n  -webkit-font-smoothing: antialiased;\n  -moz-osx-font-smoothing: grayscale;\n}\n\n.log-icon-more:before {\n\tcontent: "\\e101";\n}\n.log-icon-angle-down:before {\n\tcontent: "\\e102";\n}\n.log-icon-angle-right:before {\n\tcontent: "\\e103";\n}\n.log-icon-angle-left:before {\n\tcontent: "\\e104";\n}\n.log-icon-angle-double-left:before {\n\tcontent: "\\e105";\n}\n.log-icon-search:before {\n\tcontent: "\\e106";\n}\n.log-icon-close-circle-shape:before {\n\tcontent: "\\e107";\n}\n.log-icon-angle-double-right:before {\n\tcontent: "\\2342";\n}\n`, '']);
        }, function (t, e) {
          t.exports = 'data:image/svg+xml;base64,PD94bWwgdmVyc2lvbj0iMS4wIiBzdGFuZGFsb25lPSJubyI/PgogIDwhRE9DVFlQRSBzdmcgUFVCTElDICItLy9XM0MvL0RURCBTVkcgMS4xLy9FTiIgImh0dHA6Ly93d3cudzMub3JnL0dyYXBoaWNzL1NWRy8xLjEvRFREL3N2ZzExLmR0ZCIgPgogIDxzdmc+CiAgPG1ldGFkYXRhPgogIENyZWF0ZWQgYnkgZm9udC1jYXJyaWVyCiAgPC9tZXRhZGF0YT4KICA8ZGVmcz4KICA8Zm9udCBpZD0iaWNvbmZvbnQiIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiA+CiAgICA8Zm9udC1mYWNlCiAgICAgIAogICAgICBmb250LWZhbWlseT0iaWNvbmZvbnQiCiAgICAgIAogICAgICBmb250LXdlaWdodD0iNDAwIgogICAgICAKICAgICAgZm9udC1zdHJldGNoPSJub3JtYWwiCiAgICAgIAogICAgICB1bml0cy1wZXItZW09IjEwMjQiCiAgICAgIAogICAgICBhc2NlbnQ9IjgxMiIKICAgICAgCiAgICAgIGRlc2NlbnQ9Ii0yMTIiCiAgICAgIAogICAgLz4KICAgICAgPG1pc3NpbmctZ2x5cGggLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0ieCIgdW5pY29kZT0iJiN4Nzg7IiBob3Jpei1hZHYteD0iMTAwIgogICAgICAgIGQ9Ik0yMCAyMCBMNTAgMjAgTDUwIC0yMCBaIiAvPgogICAgICAKCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTEwMSIgdW5pY29kZT0iJiN4RTEwMTsiIGQ9Ik00NDggNTU2QzQ0OCA1OTEuMiA0NzYuOCA2MjAgNTEyIDYyMFM1NzYgNTkxLjIgNTc2IDU1NkM1NzYgNTIwLjggNTQ3LjIgNDkyIDUxMiA0OTJTNDQ4IDUyMC44IDQ0OCA1NTZaTTUxMiAzNjRDNDc2LjggMzY0IDQ0OCAzMzUuMiA0NDggMzAwUzQ3Ni44IDIzNiA1MTIgMjM2IDU3NiAyNjQuOCA1NzYgMzAwQzU3NiAzMzUuMiA1NDcuMiAzNjQgNTEyIDM2NFpNNTEyIDEwOEM0NzYuOCAxMDggNDQ4IDc5LjIgNDQ4IDQ0UzQ3Ni44LTIwIDUxMi0yMCA1NzYgOC44IDU3NiA0NEM1NzYgNzkuMiA1NDcuMiAxMDggNTEyIDEwOFoiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxMDIiIHVuaWNvZGU9IiYjeEUxMDI7IiBkPSJNMjg4IDM2NEwzMzYgNDEyIDUxMiAyMzYgNjg4IDQxMiA3MzYgMzY0IDUxMiAxNDBaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMTAzIiB1bmljb2RlPSImI3hFMTAzOyIgZD0iTTQyNCA4NEwzNzYgMTMyIDU1MiAzMDggMzc2IDQ4NCA0MjQgNTMyIDY0OCAzMDggNDI0IDg0WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTEwNCIgdW5pY29kZT0iJiN4RTEwNDsiIGQ9Ik0zNzYgMzA4TDYwMCA1MzIgNjQ4IDQ4NCA0NzIgMzA4IDY0OCAxMzIgNjAwIDg0IDM3NiAzMDhaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMTA1IiB1bmljb2RlPSImI3hFMTA1OyIgZD0iTTY5Ny42IDUzMC40TDc0NS42IDQ4Mi40IDU2OS42IDMwNi40IDc0NS42IDEzMC40IDY5Ny42IDgyLjQgNDczLjYgMzA2LjQgNjk3LjYgNTMwLjRaTTUwNS42IDUzMC40TDU1My42IDQ4Mi40IDM3Ny42IDMwNi40IDU1My42IDEzMC40IDUwNS42IDgyLjQgMjgxLjYgMzA2LjQgNTA1LjYgNTMwLjRaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMTA2IiB1bmljb2RlPSImI3hFMTA2OyIgZD0iTTg4MS45Mi0yLjA4TDc1My45MiAxMjUuOTIgNzUwLjg4IDEyOC40OEEzNTIgMzUyIDAgMSAxIDY4NS42IDU4LjcyTDY4NS42IDU4LjcyIDgxMy42LTY5LjI4QTQ4IDQ4IDAgMSAxIDg4MS40NC0xLjQ0Wk00NjQgNDRBMjg4IDI4OCAwIDEgMCA3NTIgMzMyIDI4OCAyODggMCAwIDAgNDY0IDQ0WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTEwNyIgdW5pY29kZT0iJiN4RTEwNzsiIGQ9Ik01MTIgNzQ4QzI2NCA3NDggNjQgNTQ4IDY0IDMwMFMyNjQtMTQ4IDUxMi0xNDggOTYwIDUyIDk2MCAzMDAgNzYwIDc0OCA1MTIgNzQ4Wk02OTIuOCAxNjRMNjQ4IDExOS4yIDUxMiAyNTUuMiAzNzYgMTE5LjIgMzMxLjIgMTY0IDQ2Ny4yIDMwMCAzMzEuMiA0MzYgMzc2IDQ4MC44IDUxMiAzNDQuOCA2NDggNDgwLjggNjkyLjggNDM2IDU1Ni44IDMwMCA2OTIuOCAxNjRaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmkyMzQyIiB1bmljb2RlPSImI3gyMzQyOyIgZD0iTTM1OC40IDgyLjRMMzEwLjQgMTMwLjQgNDg2LjQgMzA2LjQgMzEwLjQgNDgyLjQgMzU4LjQgNTMwLjQgNTgyLjQgMzA2LjQgMzU4LjQgODIuNFpNNTUwLjQgODIuNEw1MDIuNCAxMzAuNCA2NzguNCAzMDYuNCA1MDIuNCA0ODIuNCA1NTAuNCA1MzAuNCA3NzQuNCAzMDYuNCA1NTAuNCA4Mi40WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAoKICA8L2ZvbnQ+CiAgPC9kZWZzPgo8L3N2Zz4=';
        }, function (t, e) {
          t.exports = 'data:font/ttf;base64,AAEAAAALAIAAAwAwR1NVQrD+s+0AAAE4AAAAQk9TLzJW7kH1AAABfAAAAFZjbWFwBxKfUAAAAfwAAAHwZ2x5ZgG0ZLUAAAQEAAACLGhlYWQaqj+xAAAA4AAAADZoaGVhB4oDNwAAALwAAAAkaG10eCRkAAAAAAHUAAAAKGxvY2ECqgIeAAAD7AAAABZtYXhwARcALwAAARgAAAAgbmFtZZAIaAsAAAYwAAAChXBvc3RlizwTAAAIuAAAAHsAAQAAAyz/LABcBAAAAAAABAAAAQAAAAAAAAAAAAAAAAAAAAoAAQAAAAEAAL0CVr1fDzz1AAsEAAAAAADbxX4uAAAAANvFfi4AAP9sBAAC7AAAAAgAAgAAAAAAAAABAAAACgAjAAMAAAAAAAIAAAAKAAoAAAD/AAAAAAAAAAEAAAAKAB4ALAABREZMVAAIAAQAAAAAAAAAAQAAAAFsaWdhAAgAAAABAAAAAQAEAAQAAAABAAgAAQAGAAAAAQAAAAAAAQOkAZAABQAIAokCzAAAAI8CiQLMAAAB6wAyAQgAAAIABQMAAAAAAAAAAAAAAAAAAAAAAAAAAAAAUGZFZABAAHjhBwMs/ywAXAMsANQAAAABAAAAAAAABAAAAABkAAAEAAAABAAAAAQAAAAEAAAABAAAAAQAAAAEAAAABAAAAAAAAAUAAAADAAAALAAAAAQAAAF0AAEAAAAAAG4AAwABAAAALAADAAoAAAF0AAQAQgAAAAgACAACAAAAeCNC4Qf//wAAAHgjQuEB//8AAAAAAAAAAQAIAAgACAAAAAEACQACAAMABAAFAAYABwAIAAABBgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAMAAAAAAB8AAAAAAAAAAkAAAB4AAAAeAAAAAEAACNCAAAjQgAAAAkAAOEBAADhAQAAAAIAAOECAADhAgAAAAMAAOEDAADhAwAAAAQAAOEEAADhBAAAAAUAAOEFAADhBQAAAAYAAOEGAADhBgAAAAcAAOEHAADhBwAAAAgAAAAAAAwAOgBMAF4AcACMAMwA+gEWAAAAAQAA/+wAMgAUAAIAADczFRQeFCgAAAAAAwAA/+wCQAJsAAgAEQAaAAABPgEyFhQGIiYXDgEUFjI2NCYHDgEUFjI2NCYBwAEkNiQkNiQ/GyQkNiQkGxskJDYkJAIsGyQkNiQkpQEkNiQkNiT/ASQ2JCQ2JAABAAAAAALgAZwABQAAATcXNxcHASAwsLAw4AFsMLCwMOAAAAABAAAAAAKIAhQABQAAJSc3JzcXAagwsLAw4FQwsLAw4AAAAAABAAAAAAKIAhQABQAAATcXBxcHAXjgMLCwMAE04DCwsDAAAAACAAAAAALqAhMABQALAAABFwcXByc3FwcXBycCujCwsDDgIDCwsDDgAhIwsLAw4OAwsLAw4AAAAAIAAP+pA4MCtQAWACIAAAUvATYCJyYEBwYCFxYENxceAT4CJiclLgEnPgE3HgEXDgEDcoADTyRscP70Y18BX2QBC3GACRkaEgYHCv5feqMDA6N6eqMDA6MCgAJ2AQpdVxJmav70amYTWIAKBwYTGhgKLQOjenqjAwOjenqjAAAAAgAA/2wDwALsAAsAFwAAAQ4BBx4BFz4BNy4BAwcnByc3JzcXNxcHAgC//AUF/L+//AUF/AotiIgtiIgtiIgtiALsBfy/v/wFBfy/v/z9vS2IiC2IiC2IiC2IAAACAAAAAAMHAhMABQALAAAlJzcnNxcHJzcnNxcBZjCwsDDgIDCwsDDgUjCwsDDg4DCwsDDgAAAAAAAAEgDeAAEAAAAAAAAAHQAAAAEAAAAAAAEACAAdAAEAAAAAAAIABwAlAAEAAAAAAAMACAAsAAEAAAAAAAQACAA0AAEAAAAAAAUACwA8AAEAAAAAAAYACABHAAEAAAAAAAoAKwBPAAEAAAAAAAsAEwB6AAMAAQQJAAAAOgCNAAMAAQQJAAEAEADHAAMAAQQJAAIADgDXAAMAAQQJAAMAEADlAAMAAQQJAAQAEAD1AAMAAQQJAAUAFgEFAAMAAQQJAAYAEAEbAAMAAQQJAAoAVgErAAMAAQQJAAsAJgGBCiAgQ3JlYXRlZCBieSBmb250LWNhcnJpZXIKICBpY29uZm9udFJlZ3VsYXJpY29uZm9udGljb25mb250VmVyc2lvbiAxLjBpY29uZm9udEdlbmVyYXRlZCBieSBzdmcydHRmIGZyb20gRm9udGVsbG8gcHJvamVjdC5odHRwOi8vZm9udGVsbG8uY29tAAoAIAAgAEMAcgBlAGEAdABlAGQAIABiAHkAIABmAG8AbgB0AC0AYwBhAHIAcgBpAGUAcgAKACAAIABpAGMAbwBuAGYAbwBuAHQAUgBlAGcAdQBsAGEAcgBpAGMAbwBuAGYAbwBuAHQAaQBjAG8AbgBmAG8AbgB0AFYAZQByAHMAaQBvAG4AIAAxAC4AMABpAGMAbwBuAGYAbwBuAHQARwBlAG4AZQByAGEAdABlAGQAIABiAHkAIABzAHYAZwAyAHQAdABmACAAZgByAG8AbQAgAEYAbwBuAHQAZQBsAGwAbwAgAHAAcgBvAGoAZQBjAHQALgBoAHQAdABwADoALwAvAGYAbwBuAHQAZQBsAGwAbwAuAGMAbwBtAAAAAAIAAAAAAAAACgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACgECAQMBBAEFAQYBBwEIAQkBCgELAAF4B3VuaUUxMDEHdW5pRTEwMgd1bmlFMTAzB3VuaUUxMDQHdW5pRTEwNQd1bmlFMTA2B3VuaUUxMDcHdW5pMjM0MgAAAA==';
        }, function (t, e) {
          t.exports = 'data:font/woff;base64,d09GRgABAAAAAAWoAAsAAAAACTQAAQAAAAAAAAAAAAAAAAAAAAAAAAAAAABHU1VCAAABCAAAADMAAABCsP6z7U9TLzIAAAE8AAAARAAAAFZW7kH1Y21hcAAAAYAAAACCAAAB8AcSn1BnbHlmAAACBAAAAWkAAAIsAbRktWhlYWQAAANwAAAALwAAADYaqj+xaGhlYQAAA6AAAAAcAAAAJAeKAzdobXR4AAADvAAAABIAAAAoJGQAAGxvY2EAAAPQAAAAFgAAABYCqgIebWF4cAAAA+gAAAAdAAAAIAEXAC9uYW1lAAAECAAAAVcAAAKFkAhoC3Bvc3QAAAVgAAAARgAAAHtlizwTeJxjYGRgYOBikGPQYWB0cfMJYeBgYGGAAJAMY05meiJQDMoDyrGAaQ4gZoOIAgCKIwNPAHicY2BkXsI4gYGVgYOpk+kMAwNDP4RmfM1gxMjBwMDEwMrMgBUEpLmmMDgwVDxkZ9b5r8MQw6zDcAUozAiSAwD9CgtyeJzFkbERhDAMBE9vwIahC9KvwgURfUDwzaoSOIlLqIDzrC3dyGOPBGAEUMiXDID9YAjtdC39giX9AZ154/rwPLbu9TwVWUYhy4qW0czKwnsjJtTwbMJrsveefmrN/a9sJofgF7d+E77bTfTbRczKRczLRczRBbsNF+w7XKBdA94Y8wAAeJxVULFKw1AUvfe+Jk9TKNjGRFsoUtLGwdZSS7NV/0AQQRfpoHQoGdRBxCng0o9wK4JuXVwEaT8ls3TsWFtvXhJoH49zwjsn5753AAFWM2iBCQTgneyaZfMQeInonM7Ihy3YgSIAdrFlmXqlZufQtFqddk2mHzhFp+PwPi1F6JRioqOY3xN1lTBgNIBCfAONcz3bsyUeNMfjZoi+IpZjz5DMyFN1Pdez8UOJl6ll08M5knOew0jGtqJIVp5fKrAny67I5CqrS98qKZ5MeUVhGs7/rT7FK32BBRUA7Rg75NYyUifbynh2GbtUc6sNdLvolZE7EY+BOHf8++X8toe9O8w+BNv7xbwujWXvZSTE6EUhBfSExs1Vvj9Yzgf9wnVgSL1Q3DPqqYMxme+LKc341jbfO4eSx/CwBgrpSlUIP4NgstC0xUShUR8O002z9JTx72dNSToRMu0kbjeOxP5aJxeblfwDDZqBcgAAAHicY2BkYGAA4r1MYXvj+W2+MnCzMIDA7aN1egj6fw4LA9MbIJeDgQkkCgAoLQqCAHicY2BkYGDW+a/DEMPCAAJAkpEBFXABADNgAct4nGNhAIIUBgYWBvwYABC0AIkAAAAAAAAADAA6AEwAXgBwAIwAzAD6ARYAAHicY2BkYGDgYlBmYGYAASYwjwtI/gfzGQANCAFHAAAAeJxlkbtuwkAURMc88gApQomUJoq0TdIQzEOpUDokKCNR0BuzBiO/tF6QSJcPyHflE9Klyyekz2CuG8cr7547M3d9JQO4xjccnJ57vid2cMHqxDWc40G4Tv1JuEF+Fm6ijRfhM+oz4Ra6eBVu4wZvvMFpXLIa40PYQQefwjVc4Uu4Tv1HuEH+FW7i1mkKn6Hj3Am3sHC6wm08Ou8tpSZGe1av1PKggjSxPd8zJtSGTuinyVGa6/Uu8kxZludCmzxMEzV0B6U004k25W35fj2yNlCBSWM1paujKFWZSbfat+7G2mzc7weiu34aczzFNYGBhgfLfcV6iQP3ACkSaj349AxXSN9IT0j16JepOb01doiKbNWt1ovippz6sVYYwsXgX2rGVFIkq7Pl2PNrI6qW6eOshj0xaSq9mpNEZIWs8LZUfOouNkVXxp/d5woqebeYIf4D2J1ywQB4nG3FQRJAMBAEwJkEifUZ2QQv8BgXN1Wer5Q56ksj4GP4ZwyM7NhzYGLmSOME3uk6j73MRbuuuulFr3p799oceACa5RI0AAA=';
        }, function (t, e) {
          t.exports = 'data:application/vnd.ms-fontobject;base64,3AkAADQJAAABAAIAAAAAAAIABQMAAAAAAAABAJABAAAAAExQAAAAAAAAAAAAAAAAAAAAAAEAAAAAAAAAvVYCvQAAAAAAAAAAAAAAAAAAAAAAABAAaQBjAG8AbgBmAG8AbgB0AAAADgBSAGUAZwB1AGwAYQByAAAAFgBWAGUAcgBzAGkAbwBuACAAMQAuADAAAAAQAGkAYwBvAG4AZgBvAG4AdAAAAAAAAAEAAAALAIAAAwAwR1NVQrD+s+0AAAE4AAAAQk9TLzJW7kH1AAABfAAAAFZjbWFwBxKfUAAAAfwAAAHwZ2x5ZgG0ZLUAAAQEAAACLGhlYWQaqj+xAAAA4AAAADZoaGVhB4oDNwAAALwAAAAkaG10eCRkAAAAAAHUAAAAKGxvY2ECqgIeAAAD7AAAABZtYXhwARcALwAAARgAAAAgbmFtZZAIaAsAAAYwAAAChXBvc3RlizwTAAAIuAAAAHsAAQAAAyz/LABcBAAAAAAABAAAAQAAAAAAAAAAAAAAAAAAAAoAAQAAAAEAAL0CVr1fDzz1AAsEAAAAAADbxX4uAAAAANvFfi4AAP9sBAAC7AAAAAgAAgAAAAAAAAABAAAACgAjAAMAAAAAAAIAAAAKAAoAAAD/AAAAAAAAAAEAAAAKAB4ALAABREZMVAAIAAQAAAAAAAAAAQAAAAFsaWdhAAgAAAABAAAAAQAEAAQAAAABAAgAAQAGAAAAAQAAAAAAAQOkAZAABQAIAokCzAAAAI8CiQLMAAAB6wAyAQgAAAIABQMAAAAAAAAAAAAAAAAAAAAAAAAAAAAAUGZFZABAAHjhBwMs/ywAXAMsANQAAAABAAAAAAAABAAAAABkAAAEAAAABAAAAAQAAAAEAAAABAAAAAQAAAAEAAAABAAAAAAAAAUAAAADAAAALAAAAAQAAAF0AAEAAAAAAG4AAwABAAAALAADAAoAAAF0AAQAQgAAAAgACAACAAAAeCNC4Qf//wAAAHgjQuEB//8AAAAAAAAAAQAIAAgACAAAAAEACQACAAMABAAFAAYABwAIAAABBgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAMAAAAAAB8AAAAAAAAAAkAAAB4AAAAeAAAAAEAACNCAAAjQgAAAAkAAOEBAADhAQAAAAIAAOECAADhAgAAAAMAAOEDAADhAwAAAAQAAOEEAADhBAAAAAUAAOEFAADhBQAAAAYAAOEGAADhBgAAAAcAAOEHAADhBwAAAAgAAAAAAAwAOgBMAF4AcACMAMwA+gEWAAAAAQAA/+wAMgAUAAIAADczFRQeFCgAAAAAAwAA/+wCQAJsAAgAEQAaAAABPgEyFhQGIiYXDgEUFjI2NCYHDgEUFjI2NCYBwAEkNiQkNiQ/GyQkNiQkGxskJDYkJAIsGyQkNiQkpQEkNiQkNiT/ASQ2JCQ2JAABAAAAAALgAZwABQAAATcXNxcHASAwsLAw4AFsMLCwMOAAAAABAAAAAAKIAhQABQAAJSc3JzcXAagwsLAw4FQwsLAw4AAAAAABAAAAAAKIAhQABQAAATcXBxcHAXjgMLCwMAE04DCwsDAAAAACAAAAAALqAhMABQALAAABFwcXByc3FwcXBycCujCwsDDgIDCwsDDgAhIwsLAw4OAwsLAw4AAAAAIAAP+pA4MCtQAWACIAAAUvATYCJyYEBwYCFxYENxceAT4CJiclLgEnPgE3HgEXDgEDcoADTyRscP70Y18BX2QBC3GACRkaEgYHCv5feqMDA6N6eqMDA6MCgAJ2AQpdVxJmav70amYTWIAKBwYTGhgKLQOjenqjAwOjenqjAAAAAgAA/2wDwALsAAsAFwAAAQ4BBx4BFz4BNy4BAwcnByc3JzcXNxcHAgC//AUF/L+//AUF/AotiIgtiIgtiIgtiALsBfy/v/wFBfy/v/z9vS2IiC2IiC2IiC2IAAACAAAAAAMHAhMABQALAAAlJzcnNxcHJzcnNxcBZjCwsDDgIDCwsDDgUjCwsDDg4DCwsDDgAAAAAAAAEgDeAAEAAAAAAAAAHQAAAAEAAAAAAAEACAAdAAEAAAAAAAIABwAlAAEAAAAAAAMACAAsAAEAAAAAAAQACAA0AAEAAAAAAAUACwA8AAEAAAAAAAYACABHAAEAAAAAAAoAKwBPAAEAAAAAAAsAEwB6AAMAAQQJAAAAOgCNAAMAAQQJAAEAEADHAAMAAQQJAAIADgDXAAMAAQQJAAMAEADlAAMAAQQJAAQAEAD1AAMAAQQJAAUAFgEFAAMAAQQJAAYAEAEbAAMAAQQJAAoAVgErAAMAAQQJAAsAJgGBCiAgQ3JlYXRlZCBieSBmb250LWNhcnJpZXIKICBpY29uZm9udFJlZ3VsYXJpY29uZm9udGljb25mb250VmVyc2lvbiAxLjBpY29uZm9udEdlbmVyYXRlZCBieSBzdmcydHRmIGZyb20gRm9udGVsbG8gcHJvamVjdC5odHRwOi8vZm9udGVsbG8uY29tAAoAIAAgAEMAcgBlAGEAdABlAGQAIABiAHkAIABmAG8AbgB0AC0AYwBhAHIAcgBpAGUAcgAKACAAIABpAGMAbwBuAGYAbwBuAHQAUgBlAGcAdQBsAGEAcgBpAGMAbwBuAGYAbwBuAHQAaQBjAG8AbgBmAG8AbgB0AFYAZQByAHMAaQBvAG4AIAAxAC4AMABpAGMAbwBuAGYAbwBuAHQARwBlAG4AZQByAGEAdABlAGQAIABiAHkAIABzAHYAZwAyAHQAdABmACAAZgByAG8AbQAgAEYAbwBuAHQAZQBsAGwAbwAgAHAAcgBvAGoAZQBjAHQALgBoAHQAdABwADoALwAvAGYAbwBuAHQAZQBsAGwAbwAuAGMAbwBtAAAAAAIAAAAAAAAACgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACgECAQMBBAEFAQYBBwEIAQkBCgELAAF4B3VuaUUxMDEHdW5pRTEwMgd1bmlFMTAzB3VuaUUxMDQHdW5pRTEwNQd1bmlFMTA2B3VuaUUxMDcHdW5pMjM0MgAAAA==';
        }])))));
        /***/ }),

      /***/ './node_modules/vue/dist/vue.runtime.esm.js':
      /*! **************************************************!*\
  !*** ./node_modules/vue/dist/vue.runtime.esm.js ***!
  \**************************************************/
      /***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {
        'use strict';
        __webpack_require__.r(__webpack_exports__);
        /* harmony export */ __webpack_require__.d(__webpack_exports__, {
          /* harmony export */   default: () => (__WEBPACK_DEFAULT_EXPORT__)
          /* harmony export */ });
        /*!
 * Vue.js v2.6.14
 * (c) 2014-2021 Evan You
 * Released under the MIT License.
 */
        /*  */

        const emptyObject = Object.freeze({});

        // These helpers produce better VM code in JS engines due to their
        // explicitness and function inlining.
        function isUndef(v) {
          return v === undefined || v === null;
        }

        function isDef(v) {
          return v !== undefined && v !== null;
        }

        function isTrue(v) {
          return v === true;
        }

        function isFalse(v) {
          return v === false;
        }

        /**
 * Check if value is primitive.
 */
        function isPrimitive(value) {
          return (
            typeof value === 'string'
    || typeof value === 'number'
    // $flow-disable-line
    || typeof value === 'symbol'
    || typeof value === 'boolean'
          );
        }

        /**
 * Quick object check - this is primarily used to tell
 * Objects from primitive values when we know the value
 * is a JSON-compliant type.
 */
        function isObject(obj) {
          return obj !== null && typeof obj === 'object';
        }

        /**
 * Get the raw type string of a value, e.g., [object Object].
 */
        const _toString = Object.prototype.toString;

        function toRawType(value) {
          return _toString.call(value).slice(8, -1);
        }

        /**
 * Strict object type check. Only returns true
 * for plain JavaScript objects.
 */
        function isPlainObject(obj) {
          return _toString.call(obj) === '[object Object]';
        }

        function isRegExp(v) {
          return _toString.call(v) === '[object RegExp]';
        }

        /**
 * Check if val is a valid array index.
 */
        function isValidArrayIndex(val) {
          const n = parseFloat(String(val));
          return n >= 0 && Math.floor(n) === n && isFinite(val);
        }

        function isPromise(val) {
          return (
            isDef(val)
    && typeof val.then === 'function'
    && typeof val.catch === 'function'
          );
        }

        /**
 * Convert a value to a string that is actually rendered.
 */
        function toString(val) {
          return val == null
            ? ''
            : Array.isArray(val) || (isPlainObject(val) && val.toString === _toString)
              ? JSON.stringify(val, null, 2)
              : String(val);
        }

        /**
 * Convert an input value to a number for persistence.
 * If the conversion fails, return original string.
 */
        function toNumber(val) {
          const n = parseFloat(val);
          return isNaN(n) ? val : n;
        }

        /**
 * Make a map and return a function for checking if a key
 * is in that map.
 */
        function makeMap(
          str,
          expectsLowerCase
        ) {
          const map = Object.create(null);
          const list = str.split(',');
          for (let i = 0; i < list.length; i++) {
            map[list[i]] = true;
          }
          return expectsLowerCase
            ? function (val) {
              return map[val.toLowerCase()];
            }
            : function (val) {
              return map[val];
            };
        }

        /**
 * Check if a tag is a built-in tag.
 */
        const isBuiltInTag = makeMap('slot,component', true);

        /**
 * Check if an attribute is a reserved attribute.
 */
        const isReservedAttribute = makeMap('key,ref,slot,slot-scope,is');

        /**
 * Remove an item from an array.
 */
        function remove(arr, item) {
          if (arr.length) {
            const index = arr.indexOf(item);
            if (index > -1) {
              return arr.splice(index, 1);
            }
          }
        }

        /**
 * Check whether an object has the property.
 */
        const { hasOwnProperty } = Object.prototype;
        function hasOwn(obj, key) {
          return hasOwnProperty.call(obj, key);
        }

        /**
 * Create a cached version of a pure function.
 */
        function cached(fn) {
          const cache = Object.create(null);
          return (function cachedFn(str) {
            const hit = cache[str];
            return hit || (cache[str] = fn(str));
          });
        }

        /**
 * Camelize a hyphen-delimited string.
 */
        const camelizeRE = /-(\w)/g;
        const camelize = cached(str => str.replace(camelizeRE, (_, c) => (c ? c.toUpperCase() : '')));

        /**
 * Capitalize a string.
 */
        const capitalize = cached(str => str.charAt(0).toUpperCase() + str.slice(1));

        /**
 * Hyphenate a camelCase string.
 */
        const hyphenateRE = /\B([A-Z])/g;
        const hyphenate = cached(str => str.replace(hyphenateRE, '-$1').toLowerCase());

        /**
 * Simple bind polyfill for environments that do not support it,
 * e.g., PhantomJS 1.x. Technically, we don't need this anymore
 * since native bind is now performant enough in most browsers.
 * But removing it would mean breaking code that was able to run in
 * PhantomJS 1.x, so this must be kept for backward compatibility.
 */

        /* istanbul ignore next */
        function polyfillBind(fn, ctx) {
          function boundFn(a) {
            const l = arguments.length;
            return l
              ? l > 1
                ? fn.apply(ctx, arguments)
                : fn.call(ctx, a)
              : fn.call(ctx);
          }

          boundFn._length = fn.length;
          return boundFn;
        }

        function nativeBind(fn, ctx) {
          return fn.bind(ctx);
        }

        const bind = Function.prototype.bind
          ? nativeBind
          : polyfillBind;

        /**
 * Convert an Array-like object to a real Array.
 */
        function toArray(list, start) {
          start = start || 0;
          let i = list.length - start;
          const ret = new Array(i);
          while (i--) {
            ret[i] = list[i + start];
          }
          return ret;
        }

        /**
 * Mix properties into target object.
 */
        function extend(to, _from) {
          for (const key in _from) {
            to[key] = _from[key];
          }
          return to;
        }

        /**
 * Merge an Array of Objects into a single Object.
 */
        function toObject(arr) {
          const res = {};
          for (let i = 0; i < arr.length; i++) {
            if (arr[i]) {
              extend(res, arr[i]);
            }
          }
          return res;
        }

        /* eslint-disable no-unused-vars */

        /**
 * Perform no operation.
 * Stubbing args to make Flow happy without leaving useless transpiled code
 * with ...rest (https://flow.org/blog/2017/05/07/Strict-Function-Call-Arity/).
 */
        function noop(a, b, c) {}

        /**
 * Always return false.
 */
        const no = function (a, b, c) {
          return false;
        };

        /* eslint-enable no-unused-vars */

        /**
 * Return the same value.
 */
        const identity = function (_) {
          return _;
        };

        /**
 * Check if two values are loosely equal - that is,
 * if they are plain objects, do they have the same shape?
 */
        function looseEqual(a, b) {
          if (a === b) {
            return true;
          }
          const isObjectA = isObject(a);
          const isObjectB = isObject(b);
          if (isObjectA && isObjectB) {
            try {
              const isArrayA = Array.isArray(a);
              const isArrayB = Array.isArray(b);
              if (isArrayA && isArrayB) {
                return a.length === b.length && a.every((e, i) => looseEqual(e, b[i]));
              } if (a instanceof Date && b instanceof Date) {
                return a.getTime() === b.getTime();
              } if (!isArrayA && !isArrayB) {
                const keysA = Object.keys(a);
                const keysB = Object.keys(b);
                return keysA.length === keysB.length && keysA.every(key => looseEqual(a[key], b[key]));
              }
              /* istanbul ignore next */
              return false;
            } catch (e) {
              /* istanbul ignore next */
              return false;
            }
          } else if (!isObjectA && !isObjectB) {
            return String(a) === String(b);
          } else {
            return false;
          }
        }

        /**
 * Return the first index at which a loosely equal value can be
 * found in the array (if value is a plain object, the array must
 * contain an object of the same shape), or -1 if it is not present.
 */
        function looseIndexOf(arr, val) {
          for (let i = 0; i < arr.length; i++) {
            if (looseEqual(arr[i], val)) {
              return i;
            }
          }
          return -1;
        }

        /**
 * Ensure a function is called only once.
 */
        function once(fn) {
          let called = false;
          return function () {
            if (!called) {
              called = true;
              fn.apply(this, arguments);
            }
          };
        }

        const SSR_ATTR = 'data-server-rendered';

        const ASSET_TYPES = [
          'component',
          'directive',
          'filter'
        ];

        const LIFECYCLE_HOOKS = [
          'beforeCreate',
          'created',
          'beforeMount',
          'mounted',
          'beforeUpdate',
          'updated',
          'beforeDestroy',
          'destroyed',
          'activated',
          'deactivated',
          'errorCaptured',
          'serverPrefetch'
        ];

        /*  */


        const config = ({
          /**
   * Option merge strategies (used in core/util/options)
   */
          // $flow-disable-line
          optionMergeStrategies: Object.create(null),

          /**
   * Whether to suppress warnings.
   */
          silent: false,

          /**
   * Show production mode tip message on boot?
   */
          productionTip: 'development' !== 'production',

          /**
   * Whether to enable devtools
   */
          devtools: 'development' !== 'production',

          /**
   * Whether to record perf
   */
          performance: false,

          /**
   * Error handler for watcher errors
   */
          errorHandler: null,

          /**
   * Warn handler for watcher warns
   */
          warnHandler: null,

          /**
   * Ignore certain custom elements
   */
          ignoredElements: [],

          /**
   * Custom user key aliases for v-on
   */
          // $flow-disable-line
          keyCodes: Object.create(null),

          /**
   * Check if a tag is reserved so that it cannot be registered as a
   * component. This is platform-dependent and may be overwritten.
   */
          isReservedTag: no,

          /**
   * Check if an attribute is reserved so that it cannot be used as a component
   * prop. This is platform-dependent and may be overwritten.
   */
          isReservedAttr: no,

          /**
   * Check if a tag is an unknown element.
   * Platform-dependent.
   */
          isUnknownElement: no,

          /**
   * Get the namespace of an element
   */
          getTagNamespace: noop,

          /**
   * Parse the real tag name for the specific platform.
   */
          parsePlatformTagName: identity,

          /**
   * Check if an attribute must be bound using property, e.g. value
   * Platform-dependent.
   */
          mustUseProp: no,

          /**
   * Perform updates asynchronously. Intended to be used by Vue Test Utils
   * This will significantly reduce performance if set to false.
   */
          async: true,

          /**
   * Exposed for legacy reasons
   */
          _lifecycleHooks: LIFECYCLE_HOOKS
        });

        /*  */

        /**
 * unicode letters used for parsing html tags, component names and property paths.
 * using https://www.w3.org/TR/html53/semantics-scripting.html#potentialcustomelementname
 * skipping \u10000-\uEFFFF due to it freezing up PhantomJS
 */
        const unicodeRegExp = /a-zA-Z\u00B7\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u037D\u037F-\u1FFF\u200C-\u200D\u203F-\u2040\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD/;

        /**
 * Check if a string starts with $ or _
 */
        function isReserved(str) {
          const c = (`${str}`).charCodeAt(0);
          return c === 0x24 || c === 0x5F;
        }

        /**
 * Define a property.
 */
        function def(obj, key, val, enumerable) {
          Object.defineProperty(obj, key, {
            value: val,
            enumerable: !!enumerable,
            writable: true,
            configurable: true
          });
        }

        /**
 * Parse simple path.
 */
        const bailRE = new RegExp((`[^${unicodeRegExp.source}.$_\\d]`));
        function parsePath(path) {
          if (bailRE.test(path)) {
            return;
          }
          const segments = path.split('.');
          return function (obj) {
            for (let i = 0; i < segments.length; i++) {
              if (!obj) {
                return;
              }
              obj = obj[segments[i]];
            }
            return obj;
          };
        }

        /*  */

        // can we use __proto__?
        const hasProto = '__proto__' in {};

        // Browser environment sniffing
        const inBrowser = typeof window !== 'undefined';
        const inWeex = typeof WXEnvironment !== 'undefined' && !!WXEnvironment.platform;
        const weexPlatform = inWeex && WXEnvironment.platform.toLowerCase();
        const UA = inBrowser && window.navigator.userAgent.toLowerCase();
        const isIE = UA && /msie|trident/.test(UA);
        const isIE9 = UA && UA.indexOf('msie 9.0') > 0;
        const isEdge = UA && UA.indexOf('edge/') > 0;
        const isAndroid = (UA && UA.indexOf('android') > 0) || (weexPlatform === 'android');
        const isIOS = (UA && /iphone|ipad|ipod|ios/.test(UA)) || (weexPlatform === 'ios');
        const isChrome = UA && /chrome\/\d+/.test(UA) && !isEdge;
        const isPhantomJS = UA && /phantomjs/.test(UA);
        const isFF = UA && UA.match(/firefox\/(\d+)/);

        // Firefox has a "watch" function on Object.prototype...
        const nativeWatch = ({}).watch;

        let supportsPassive = false;
        if (inBrowser) {
          try {
            const opts = {};
            Object.defineProperty(opts, 'passive', ({
              get: function get() {
                /* istanbul ignore next */
                supportsPassive = true;
              }
            })); // https://github.com/facebook/flow/issues/285
            window.addEventListener('test-passive', null, opts);
          } catch (e) {}
        }

        // this needs to be lazy-evaled because vue may be required before
        // vue-server-renderer can set VUE_ENV
        let _isServer;
        const isServerRendering = function () {
          if (_isServer === undefined) {
            /* istanbul ignore if */
            if (!inBrowser && !inWeex && typeof global !== 'undefined') {
              // detect presence of vue-server-renderer and avoid
              // Webpack shimming the process
              _isServer = global.process && global.process.env.VUE_ENV === 'server';
            } else {
              _isServer = false;
            }
          }
          return _isServer;
        };

        // detect devtools
        const devtools = inBrowser && window.__VUE_DEVTOOLS_GLOBAL_HOOK__;

        /* istanbul ignore next */
        function isNative(Ctor) {
          return typeof Ctor === 'function' && /native code/.test(Ctor.toString());
        }

        const hasSymbol =  typeof Symbol !== 'undefined' && isNative(Symbol)
  && typeof Reflect !== 'undefined' && isNative(Reflect.ownKeys);

        let _Set;
        /* istanbul ignore if */ // $flow-disable-line
        if (typeof Set !== 'undefined' && isNative(Set)) {
          // use native Set when available.
          _Set = Set;
        } else {
          // a non-standard Set polyfill that only works with primitive keys.
          _Set = /* @__PURE__*/(function () {
            function Set() {
              this.set = Object.create(null);
            }
            Set.prototype.has = function has(key) {
              return this.set[key] === true;
            };
            Set.prototype.add = function add(key) {
              this.set[key] = true;
            };
            Set.prototype.clear = function clear() {
              this.set = Object.create(null);
            };

            return Set;
          }());
        }

        /*  */

        let warn = noop;
        let tip = noop;
        let generateComponentTrace = (noop); // work around flow check
        let formatComponentName = (noop);

        if (true) {
          const hasConsole = typeof console !== 'undefined';
          const classifyRE = /(?:^|[-_])(\w)/g;
          const classify = function (str) {
            return str
              .replace(classifyRE, c => c.toUpperCase())
              .replace(/[-_]/g, '');
          };

          warn = function (msg, vm) {
            const trace = vm ? generateComponentTrace(vm) : '';

            if (config.warnHandler) {
              config.warnHandler.call(null, msg, vm, trace);
            } else if (hasConsole && (!config.silent)) {
              console.error((`[Vue warn]: ${msg}${trace}`));
            }
          };

          tip = function (msg, vm) {
            if (hasConsole && (!config.silent)) {
              console.warn(`[Vue tip]: ${msg
              }${vm ? generateComponentTrace(vm) : ''}`);
            }
          };

          formatComponentName = function (vm, includeFile) {
            if (vm.$root === vm) {
              return '<Root>';
            }
            const options = typeof vm === 'function' && vm.cid != null
              ? vm.options
              : vm._isVue
                ? vm.$options || vm.constructor.options
                : vm;
            let name = options.name || options._componentTag;
            const file = options.__file;
            if (!name && file) {
              const match = file.match(/([^/\\]+)\.vue$/);
              name = match && match[1];
            }

            return (
              (name ? (`<${classify(name)}>`) : '<Anonymous>')
      + (file && includeFile !== false ? (` at ${file}`) : '')
            );
          };

          const repeat = function (str, n) {
            let res = '';
            while (n) {
              if (n % 2 === 1) {
                res += str;
              }
              if (n > 1) {
                str += str;
              }
              n >>= 1;
            }
            return res;
          };

          generateComponentTrace = function (vm) {
            if (vm._isVue && vm.$parent) {
              const tree = [];
              let currentRecursiveSequence = 0;
              while (vm) {
                if (tree.length > 0) {
                  const last = tree[tree.length - 1];
                  if (last.constructor === vm.constructor) {
                    currentRecursiveSequence++;
                    vm = vm.$parent;
                    continue;
                  } else if (currentRecursiveSequence > 0) {
                    tree[tree.length - 1] = [last, currentRecursiveSequence];
                    currentRecursiveSequence = 0;
                  }
                }
                tree.push(vm);
                vm = vm.$parent;
              }
              return `\n\nfound in\n\n${tree
                .map((vm, i) => (`${i === 0 ? '---> ' : repeat(' ', 5 + i * 2)}${Array.isArray(vm)
                  ? (`${formatComponentName(vm[0])}... (${vm[1]} recursive calls)`)
                  : formatComponentName(vm)}`))
                .join('\n')}`;
            }
            return (`\n\n(found in ${formatComponentName(vm)})`);
          };
        }

        /*  */

        let uid = 0;

        /**
 * A dep is an observable that can have multiple
 * directives subscribing to it.
 */
        const Dep = function Dep() {
          this.id = uid++;
          this.subs = [];
        };

        Dep.prototype.addSub = function addSub(sub) {
          this.subs.push(sub);
        };

        Dep.prototype.removeSub = function removeSub(sub) {
          remove(this.subs, sub);
        };

        Dep.prototype.depend = function depend() {
          if (Dep.target) {
            Dep.target.addDep(this);
          }
        };

        Dep.prototype.notify = function notify() {
          // stabilize the subscriber list first
          const subs = this.subs.slice();
          if (true && !config.async) {
            // subs aren't sorted in scheduler if not running async
            // we need to sort them now to make sure they fire in correct
            // order
            subs.sort((a, b) => a.id - b.id);
          }
          for (let i = 0, l = subs.length; i < l; i++) {
            subs[i].update();
          }
        };

        // The current target watcher being evaluated.
        // This is globally unique because only one watcher
        // can be evaluated at a time.
        Dep.target = null;
        const targetStack = [];

        function pushTarget(target) {
          targetStack.push(target);
          Dep.target = target;
        }

        function popTarget() {
          targetStack.pop();
          Dep.target = targetStack[targetStack.length - 1];
        }

        /*  */

        const VNode = function VNode(
          tag,
          data,
          children,
          text,
          elm,
          context,
          componentOptions,
          asyncFactory
        ) {
          this.tag = tag;
          this.data = data;
          this.children = children;
          this.text = text;
          this.elm = elm;
          this.ns = undefined;
          this.context = context;
          this.fnContext = undefined;
          this.fnOptions = undefined;
          this.fnScopeId = undefined;
          this.key = data && data.key;
          this.componentOptions = componentOptions;
          this.componentInstance = undefined;
          this.parent = undefined;
          this.raw = false;
          this.isStatic = false;
          this.isRootInsert = true;
          this.isComment = false;
          this.isCloned = false;
          this.isOnce = false;
          this.asyncFactory = asyncFactory;
          this.asyncMeta = undefined;
          this.isAsyncPlaceholder = false;
        };

        const prototypeAccessors = { child: { configurable: true } };

        // DEPRECATED: alias for componentInstance for backwards compat.
        /* istanbul ignore next */
        prototypeAccessors.child.get = function () {
          return this.componentInstance;
        };

        Object.defineProperties(VNode.prototype, prototypeAccessors);

        const createEmptyVNode = function (text) {
          if (text === void 0) text = '';

          const node = new VNode();
          node.text = text;
          node.isComment = true;
          return node;
        };

        function createTextVNode(val) {
          return new VNode(undefined, undefined, undefined, String(val));
        }

        // optimized shallow clone
        // used for static nodes and slot nodes because they may be reused across
        // multiple renders, cloning them avoids errors when DOM manipulations rely
        // on their elm reference.
        function cloneVNode(vnode) {
          const cloned = new VNode(
            vnode.tag,
            vnode.data,
            // #7975
            // clone children array to avoid mutating original in case of cloning
            // a child.
            vnode.children && vnode.children.slice(),
            vnode.text,
            vnode.elm,
            vnode.context,
            vnode.componentOptions,
            vnode.asyncFactory
          );
          cloned.ns = vnode.ns;
          cloned.isStatic = vnode.isStatic;
          cloned.key = vnode.key;
          cloned.isComment = vnode.isComment;
          cloned.fnContext = vnode.fnContext;
          cloned.fnOptions = vnode.fnOptions;
          cloned.fnScopeId = vnode.fnScopeId;
          cloned.asyncMeta = vnode.asyncMeta;
          cloned.isCloned = true;
          return cloned;
        }

        /*
 * not type checking this file because flow doesn't play well with
 * dynamically accessing methods on Array prototype
 */

        const arrayProto = Array.prototype;
        const arrayMethods = Object.create(arrayProto);

        const methodsToPatch = [
          'push',
          'pop',
          'shift',
          'unshift',
          'splice',
          'sort',
          'reverse'
        ];

        /**
 * Intercept mutating methods and emit events
 */
        methodsToPatch.forEach((method) => {
          // cache original method
          const original = arrayProto[method];
          def(arrayMethods, method, function mutator() {
            const args = []; let len = arguments.length;
            while (len--) args[len] = arguments[len];

            const result = original.apply(this, args);
            const ob = this.__ob__;
            let inserted;
            switch (method) {
              case 'push':
              case 'unshift':
                inserted = args;
                break;
              case 'splice':
                inserted = args.slice(2);
                break;
            }
            if (inserted) {
              ob.observeArray(inserted);
            }
            // notify change
            ob.dep.notify();
            return result;
          });
        });

        /*  */

        const arrayKeys = Object.getOwnPropertyNames(arrayMethods);

        /**
 * In some cases we may want to disable observation inside a component's
 * update computation.
 */
        let shouldObserve = true;

        function toggleObserving(value) {
          shouldObserve = value;
        }

        /**
 * Observer class that is attached to each observed
 * object. Once attached, the observer converts the target
 * object's property keys into getter/setters that
 * collect dependencies and dispatch updates.
 */
        const Observer = function Observer(value) {
          this.value = value;
          this.dep = new Dep();
          this.vmCount = 0;
          def(value, '__ob__', this);
          if (Array.isArray(value)) {
            if (hasProto) {
              protoAugment(value, arrayMethods);
            } else {
              copyAugment(value, arrayMethods, arrayKeys);
            }
            this.observeArray(value);
          } else {
            this.walk(value);
          }
        };

        /**
 * Walk through all properties and convert them into
 * getter/setters. This method should only be called when
 * value type is Object.
 */
        Observer.prototype.walk = function walk(obj) {
          const keys = Object.keys(obj);
          for (let i = 0; i < keys.length; i++) {
            defineReactive$$1(obj, keys[i]);
          }
        };

        /**
 * Observe a list of Array items.
 */
        Observer.prototype.observeArray = function observeArray(items) {
          for (let i = 0, l = items.length; i < l; i++) {
            observe(items[i]);
          }
        };

        // helpers

        /**
 * Augment a target Object or Array by intercepting
 * the prototype chain using __proto__
 */
        function protoAugment(target, src) {
          /* eslint-disable no-proto */
          target.__proto__ = src;
          /* eslint-enable no-proto */
        }

        /**
 * Augment a target Object or Array by defining
 * hidden properties.
 */
        /* istanbul ignore next */
        function copyAugment(target, src, keys) {
          for (let i = 0, l = keys.length; i < l; i++) {
            const key = keys[i];
            def(target, key, src[key]);
          }
        }

        /**
 * Attempt to create an observer instance for a value,
 * returns the new observer if successfully observed,
 * or the existing observer if the value already has one.
 */
        function observe(value, asRootData) {
          if (!isObject(value) || value instanceof VNode) {
            return;
          }
          let ob;
          if (hasOwn(value, '__ob__') && value.__ob__ instanceof Observer) {
            ob = value.__ob__;
          } else if (
            shouldObserve
    && !isServerRendering()
    && (Array.isArray(value) || isPlainObject(value))
    && Object.isExtensible(value)
    && !value._isVue
          ) {
            ob = new Observer(value);
          }
          if (asRootData && ob) {
            ob.vmCount++;
          }
          return ob;
        }

        /**
 * Define a reactive property on an Object.
 */
        function defineReactive$$1(
          obj,
          key,
          val,
          customSetter,
          shallow
        ) {
          const dep = new Dep();

          const property = Object.getOwnPropertyDescriptor(obj, key);
          if (property && property.configurable === false) {
            return;
          }

          // cater for pre-defined getter/setters
          const getter = property && property.get;
          const setter = property && property.set;
          if ((!getter || setter) && arguments.length === 2) {
            val = obj[key];
          }

          let childOb = !shallow && observe(val);
          Object.defineProperty(obj, key, {
            enumerable: true,
            configurable: true,
            get: function reactiveGetter() {
              const value = getter ? getter.call(obj) : val;
              if (Dep.target) {
                dep.depend();
                if (childOb) {
                  childOb.dep.depend();
                  if (Array.isArray(value)) {
                    dependArray(value);
                  }
                }
              }
              return value;
            },
            set: function reactiveSetter(newVal) {
              const value = getter ? getter.call(obj) : val;
              /* eslint-disable no-self-compare */
              if (newVal === value || (newVal !== newVal && value !== value)) {
                return;
              }
              /* eslint-enable no-self-compare */
              if (true && customSetter) {
                customSetter();
              }
              // #7981: for accessor properties without setter
              if (getter && !setter) {
                return;
              }
              if (setter) {
                setter.call(obj, newVal);
              } else {
                val = newVal;
              }
              childOb = !shallow && observe(newVal);
              dep.notify();
            }
          });
        }

        /**
 * Set a property on an object. Adds the new property and
 * triggers change notification if the property doesn't
 * already exist.
 */
        function set(target, key, val) {
          if (true
    && (isUndef(target) || isPrimitive(target))
          ) {
            warn((`Cannot set reactive property on undefined, null, or primitive value: ${target}`));
          }
          if (Array.isArray(target) && isValidArrayIndex(key)) {
            target.length = Math.max(target.length, key);
            target.splice(key, 1, val);
            return val;
          }
          if (key in target && !(key in Object.prototype)) {
            target[key] = val;
            return val;
          }
          const ob = (target).__ob__;
          if (target._isVue || (ob && ob.vmCount)) {
            true && warn('Avoid adding reactive properties to a Vue instance or its root $data '
      + 'at runtime - declare it upfront in the data option.');
            return val;
          }
          if (!ob) {
            target[key] = val;
            return val;
          }
          defineReactive$$1(ob.value, key, val);
          ob.dep.notify();
          return val;
        }

        /**
 * Delete a property and trigger change if necessary.
 */
        function del(target, key) {
          if (true
    && (isUndef(target) || isPrimitive(target))
          ) {
            warn((`Cannot delete reactive property on undefined, null, or primitive value: ${target}`));
          }
          if (Array.isArray(target) && isValidArrayIndex(key)) {
            target.splice(key, 1);
            return;
          }
          const ob = (target).__ob__;
          if (target._isVue || (ob && ob.vmCount)) {
            true && warn('Avoid deleting properties on a Vue instance or its root $data '
      + '- just set it to null.');
            return;
          }
          if (!hasOwn(target, key)) {
            return;
          }
          delete target[key];
          if (!ob) {
            return;
          }
          ob.dep.notify();
        }

        /**
 * Collect dependencies on array elements when the array is touched, since
 * we cannot intercept array element access like property getters.
 */
        function dependArray(value) {
          for (let e = (void 0), i = 0, l = value.length; i < l; i++) {
            e = value[i];
            e && e.__ob__ && e.__ob__.dep.depend();
            if (Array.isArray(e)) {
              dependArray(e);
            }
          }
        }

        /*  */

        /**
 * Option overwriting strategies are functions that handle
 * how to merge a parent option value and a child option
 * value into the final value.
 */
        const strats = config.optionMergeStrategies;

        /**
 * Options with restrictions
 */
        if (true) {
          strats.el = strats.propsData = function (parent, child, vm, key) {
            if (!vm) {
              warn(`option "${key}" can only be used during instance `
        + 'creation with the `new` keyword.');
            }
            return defaultStrat(parent, child);
          };
        }

        /**
 * Helper that recursively merges two data objects together.
 */
        function mergeData(to, from) {
          if (!from) {
            return to;
          }
          let key; let toVal; let fromVal;

          const keys = hasSymbol
            ? Reflect.ownKeys(from)
            : Object.keys(from);

          for (let i = 0; i < keys.length; i++) {
            key = keys[i];
            // in case the object is already observed...
            if (key === '__ob__') {
              continue;
            }
            toVal = to[key];
            fromVal = from[key];
            if (!hasOwn(to, key)) {
              set(to, key, fromVal);
            } else if (
              toVal !== fromVal
      && isPlainObject(toVal)
      && isPlainObject(fromVal)
            ) {
              mergeData(toVal, fromVal);
            }
          }
          return to;
        }

        /**
 * Data
 */
        function mergeDataOrFn(
          parentVal,
          childVal,
          vm
        ) {
          if (!vm) {
            // in a Vue.extend merge, both should be functions
            if (!childVal) {
              return parentVal;
            }
            if (!parentVal) {
              return childVal;
            }
            // when parentVal & childVal are both present,
            // we need to return a function that returns the
            // merged result of both functions... no need to
            // check if parentVal is a function here because
            // it has to be a function to pass previous merges.
            return function mergedDataFn() {
              return mergeData(
                typeof childVal === 'function' ? childVal.call(this, this) : childVal,
                typeof parentVal === 'function' ? parentVal.call(this, this) : parentVal
              );
            };
          }
          return function mergedInstanceDataFn() {
            // instance merge
            const instanceData = typeof childVal === 'function'
              ? childVal.call(vm, vm)
              : childVal;
            const defaultData = typeof parentVal === 'function'
              ? parentVal.call(vm, vm)
              : parentVal;
            if (instanceData) {
              return mergeData(instanceData, defaultData);
            }
            return defaultData;
          };
        }

        strats.data = function (
          parentVal,
          childVal,
          vm
        ) {
          if (!vm) {
            if (childVal && typeof childVal !== 'function') {
              true && warn(
                'The "data" option should be a function '
        + 'that returns a per-instance value in component '
        + 'definitions.',
                vm
              );

              return parentVal;
            }
            return mergeDataOrFn(parentVal, childVal);
          }

          return mergeDataOrFn(parentVal, childVal, vm);
        };

        /**
 * Hooks and props are merged as arrays.
 */
        function mergeHook(
          parentVal,
          childVal
        ) {
          const res = childVal
            ? parentVal
              ? parentVal.concat(childVal)
              : Array.isArray(childVal)
                ? childVal
                : [childVal]
            : parentVal;
          return res
            ? dedupeHooks(res)
            : res;
        }

        function dedupeHooks(hooks) {
          const res = [];
          for (let i = 0; i < hooks.length; i++) {
            if (res.indexOf(hooks[i]) === -1) {
              res.push(hooks[i]);
            }
          }
          return res;
        }

        LIFECYCLE_HOOKS.forEach((hook) => {
          strats[hook] = mergeHook;
        });

        /**
 * Assets
 *
 * When a vm is present (instance creation), we need to do
 * a three-way merge between constructor options, instance
 * options and parent options.
 */
        function mergeAssets(
          parentVal,
          childVal,
          vm,
          key
        ) {
          const res = Object.create(parentVal || null);
          if (childVal) {
            true && assertObjectType(key, childVal, vm);
            return extend(res, childVal);
          }
          return res;
        }

        ASSET_TYPES.forEach((type) => {
          strats[`${type}s`] = mergeAssets;
        });

        /**
 * Watchers.
 *
 * Watchers hashes should not overwrite one
 * another, so we merge them as arrays.
 */
        strats.watch = function (
          parentVal,
          childVal,
          vm,
          key
        ) {
          // work around Firefox's Object.prototype.watch...
          if (parentVal === nativeWatch) {
            parentVal = undefined;
          }
          if (childVal === nativeWatch) {
            childVal = undefined;
          }
          /* istanbul ignore if */
          if (!childVal) {
            return Object.create(parentVal || null);
          }
          if (true) {
            assertObjectType(key, childVal, vm);
          }
          if (!parentVal) {
            return childVal;
          }
          const ret = {};
          extend(ret, parentVal);
          for (const key$1 in childVal) {
            let parent = ret[key$1];
            const child = childVal[key$1];
            if (parent && !Array.isArray(parent)) {
              parent = [parent];
            }
            ret[key$1] = parent
              ? parent.concat(child)
              : Array.isArray(child) ? child : [child];
          }
          return ret;
        };

        /**
 * Other object hashes.
 */
        strats.props = strats.methods = strats.inject = strats.computed = function (
          parentVal,
          childVal,
          vm,
          key
        ) {
          if (childVal && 'development' !== 'production') {
            assertObjectType(key, childVal, vm);
          }
          if (!parentVal) {
            return childVal;
          }
          const ret = Object.create(null);
          extend(ret, parentVal);
          if (childVal) {
            extend(ret, childVal);
          }
          return ret;
        };
        strats.provide = mergeDataOrFn;

        /**
 * Default strategy.
 */
        var defaultStrat = function (parentVal, childVal) {
          return childVal === undefined
            ? parentVal
            : childVal;
        };

        /**
 * Validate component names
 */
        function checkComponents(options) {
          for (const key in options.components) {
            validateComponentName(key);
          }
        }

        function validateComponentName(name) {
          if (!new RegExp((`^[a-zA-Z][\\-\\.0-9_${unicodeRegExp.source}]*$`)).test(name)) {
            warn(`Invalid component name: "${name}". Component names `
      + 'should conform to valid custom element name in html5 specification.');
          }
          if (isBuiltInTag(name) || config.isReservedTag(name)) {
            warn('Do not use built-in or reserved HTML elements as component '
      + `id: ${name}`);
          }
        }

        /**
 * Ensure all props option syntax are normalized into the
 * Object-based format.
 */
        function normalizeProps(options, vm) {
          const { props } = options;
          if (!props) {
            return;
          }
          const res = {};
          let i; let val; let name;
          if (Array.isArray(props)) {
            i = props.length;
            while (i--) {
              val = props[i];
              if (typeof val === 'string') {
                name = camelize(val);
                res[name] = { type: null };
              } else if (true) {
                warn('props must be strings when using array syntax.');
              }
            }
          } else if (isPlainObject(props)) {
            for (const key in props) {
              val = props[key];
              name = camelize(key);
              res[name] = isPlainObject(val)
                ? val
                : { type: val };
            }
          } else if (true) {
            warn(
              'Invalid value for option "props": expected an Array or an Object, '
      + `but got ${toRawType(props)}.`,
              vm
            );
          }
          options.props = res;
        }

        /**
 * Normalize all injections into Object-based format
 */
        function normalizeInject(options, vm) {
          const { inject } = options;
          if (!inject) {
            return;
          }
          const normalized = options.inject = {};
          if (Array.isArray(inject)) {
            for (let i = 0; i < inject.length; i++) {
              normalized[inject[i]] = { from: inject[i] };
            }
          } else if (isPlainObject(inject)) {
            for (const key in inject) {
              const val = inject[key];
              normalized[key] = isPlainObject(val)
                ? extend({ from: key }, val)
                : { from: val };
            }
          } else if (true) {
            warn(
              'Invalid value for option "inject": expected an Array or an Object, '
      + `but got ${toRawType(inject)}.`,
              vm
            );
          }
        }

        /**
 * Normalize raw function directives into object format.
 */
        function normalizeDirectives(options) {
          const dirs = options.directives;
          if (dirs) {
            for (const key in dirs) {
              const def$$1 = dirs[key];
              if (typeof def$$1 === 'function') {
                dirs[key] = { bind: def$$1, update: def$$1 };
              }
            }
          }
        }

        function assertObjectType(name, value, vm) {
          if (!isPlainObject(value)) {
            warn(
              `Invalid value for option "${name}": expected an Object, `
      + `but got ${toRawType(value)}.`,
              vm
            );
          }
        }

        /**
 * Merge two option objects into a new one.
 * Core utility used in both instantiation and inheritance.
 */
        function mergeOptions(
          parent,
          child,
          vm
        ) {
          if (true) {
            checkComponents(child);
          }

          if (typeof child === 'function') {
            child = child.options;
          }

          normalizeProps(child, vm);
          normalizeInject(child, vm);
          normalizeDirectives(child);

          // Apply extends and mixins on the child options,
          // but only if it is a raw options object that isn't
          // the result of another mergeOptions call.
          // Only merged options has the _base property.
          if (!child._base) {
            if (child.extends) {
              parent = mergeOptions(parent, child.extends, vm);
            }
            if (child.mixins) {
              for (let i = 0, l = child.mixins.length; i < l; i++) {
                parent = mergeOptions(parent, child.mixins[i], vm);
              }
            }
          }

          const options = {};
          let key;
          for (key in parent) {
            mergeField(key);
          }
          for (key in child) {
            if (!hasOwn(parent, key)) {
              mergeField(key);
            }
          }
          function mergeField(key) {
            const strat = strats[key] || defaultStrat;
            options[key] = strat(parent[key], child[key], vm, key);
          }
          return options;
        }

        /**
 * Resolve an asset.
 * This function is used because child instances need access
 * to assets defined in its ancestor chain.
 */
        function resolveAsset(
          options,
          type,
          id,
          warnMissing
        ) {
          /* istanbul ignore if */
          if (typeof id !== 'string') {
            return;
          }
          const assets = options[type];
          // check local registration variations first
          if (hasOwn(assets, id)) {
            return assets[id];
          }
          const camelizedId = camelize(id);
          if (hasOwn(assets, camelizedId)) {
            return assets[camelizedId];
          }
          const PascalCaseId = capitalize(camelizedId);
          if (hasOwn(assets, PascalCaseId)) {
            return assets[PascalCaseId];
          }
          // fallback to prototype chain
          const res = assets[id] || assets[camelizedId] || assets[PascalCaseId];
          if (true && warnMissing && !res) {
            warn(
              `Failed to resolve ${type.slice(0, -1)}: ${id}`,
              options
            );
          }
          return res;
        }

        /*  */


        function validateProp(
          key,
          propOptions,
          propsData,
          vm
        ) {
          const prop = propOptions[key];
          const absent = !hasOwn(propsData, key);
          let value = propsData[key];
          // boolean casting
          const booleanIndex = getTypeIndex(Boolean, prop.type);
          if (booleanIndex > -1) {
            if (absent && !hasOwn(prop, 'default')) {
              value = false;
            } else if (value === '' || value === hyphenate(key)) {
              // only cast empty string / same name to boolean if
              // boolean has higher priority
              const stringIndex = getTypeIndex(String, prop.type);
              if (stringIndex < 0 || booleanIndex < stringIndex) {
                value = true;
              }
            }
          }
          // check default value
          if (value === undefined) {
            value = getPropDefaultValue(vm, prop, key);
            // since the default value is a fresh copy,
            // make sure to observe it.
            const prevShouldObserve = shouldObserve;
            toggleObserving(true);
            observe(value);
            toggleObserving(prevShouldObserve);
          }
          if (
            true
          ) {
            assertProp(prop, key, value, vm, absent);
          }
          return value;
        }

        /**
 * Get the default value of a prop.
 */
        function getPropDefaultValue(vm, prop, key) {
          // no default, return undefined
          if (!hasOwn(prop, 'default')) {
            return undefined;
          }
          const def = prop.default;
          // warn against non-factory defaults for Object & Array
          if (true && isObject(def)) {
            warn(
              `Invalid default value for prop "${key}": `
      + 'Props with type Object/Array must use a factory function '
      + 'to return the default value.',
              vm
            );
          }
          // the raw prop value was also undefined from previous render,
          // return previous default value to avoid unnecessary watcher trigger
          if (vm && vm.$options.propsData
    && vm.$options.propsData[key] === undefined
    && vm._props[key] !== undefined
          ) {
            return vm._props[key];
          }
          // call factory function for non-Function types
          // a value is Function if its prototype is function even across different execution context
          return typeof def === 'function' && getType(prop.type) !== 'Function'
            ? def.call(vm)
            : def;
        }

        /**
 * Assert whether a prop is valid.
 */
        function assertProp(
          prop,
          name,
          value,
          vm,
          absent
        ) {
          if (prop.required && absent) {
            warn(
              `Missing required prop: "${name}"`,
              vm
            );
            return;
          }
          if (value == null && !prop.required) {
            return;
          }
          let { type } = prop;
          let valid = !type || type === true;
          const expectedTypes = [];
          if (type) {
            if (!Array.isArray(type)) {
              type = [type];
            }
            for (let i = 0; i < type.length && !valid; i++) {
              const assertedType = assertType(value, type[i], vm);
              expectedTypes.push(assertedType.expectedType || '');
              valid = assertedType.valid;
            }
          }

          const haveExpectedTypes = expectedTypes.some(t => t);
          if (!valid && haveExpectedTypes) {
            warn(
              getInvalidTypeMessage(name, value, expectedTypes),
              vm
            );
            return;
          }
          const { validator } = prop;
          if (validator) {
            if (!validator(value)) {
              warn(
                `Invalid prop: custom validator check failed for prop "${name}".`,
                vm
              );
            }
          }
        }

        const simpleCheckRE = /^(String|Number|Boolean|Function|Symbol|BigInt)$/;

        function assertType(value, type, vm) {
          let valid;
          const expectedType = getType(type);
          if (simpleCheckRE.test(expectedType)) {
            const t = typeof value;
            valid = t === expectedType.toLowerCase();
            // for primitive wrapper objects
            if (!valid && t === 'object') {
              valid = value instanceof type;
            }
          } else if (expectedType === 'Object') {
            valid = isPlainObject(value);
          } else if (expectedType === 'Array') {
            valid = Array.isArray(value);
          } else {
            try {
              valid = value instanceof type;
            } catch (e) {
              warn(`Invalid prop type: "${String(type)}" is not a constructor`, vm);
              valid = false;
            }
          }
          return {
            valid,
            expectedType
          };
        }

        const functionTypeCheckRE = /^\s*function (\w+)/;

        /**
 * Use function string name to check built-in types,
 * because a simple equality check will fail when running
 * across different vms / iframes.
 */
        function getType(fn) {
          const match = fn && fn.toString().match(functionTypeCheckRE);
          return match ? match[1] : '';
        }

        function isSameType(a, b) {
          return getType(a) === getType(b);
        }

        function getTypeIndex(type, expectedTypes) {
          if (!Array.isArray(expectedTypes)) {
            return isSameType(expectedTypes, type) ? 0 : -1;
          }
          for (let i = 0, len = expectedTypes.length; i < len; i++) {
            if (isSameType(expectedTypes[i], type)) {
              return i;
            }
          }
          return -1;
        }

        function getInvalidTypeMessage(name, value, expectedTypes) {
          let message = `Invalid prop: type check failed for prop "${name}".`
    + ` Expected ${expectedTypes.map(capitalize).join(', ')}`;
          const expectedType = expectedTypes[0];
          const receivedType = toRawType(value);
          // check if we need to specify expected value
          if (
            expectedTypes.length === 1
    && isExplicable(expectedType)
    && isExplicable(typeof value)
    && !isBoolean(expectedType, receivedType)
          ) {
            message += ` with value ${styleValue(value, expectedType)}`;
          }
          message += `, got ${receivedType} `;
          // check if we need to specify received value
          if (isExplicable(receivedType)) {
            message += `with value ${styleValue(value, receivedType)}.`;
          }
          return message;
        }

        function styleValue(value, type) {
          if (type === 'String') {
            return (`"${value}"`);
          } if (type === 'Number') {
            return (`${Number(value)}`);
          }
          return (`${value}`);
        }

        const EXPLICABLE_TYPES = ['string', 'number', 'boolean'];
        function isExplicable(value) {
          return EXPLICABLE_TYPES.some(elem => value.toLowerCase() === elem);
        }

        function isBoolean() {
          const args = []; let len = arguments.length;
          while (len--) args[len] = arguments[len];

          return args.some(elem => elem.toLowerCase() === 'boolean');
        }

        /*  */

        function handleError(err, vm, info) {
          // Deactivate deps tracking while processing error handler to avoid possible infinite rendering.
          // See: https://github.com/vuejs/vuex/issues/1505
          pushTarget();
          try {
            if (vm) {
              let cur = vm;
              while ((cur = cur.$parent)) {
                const hooks = cur.$options.errorCaptured;
                if (hooks) {
                  for (let i = 0; i < hooks.length; i++) {
                    try {
                      const capture = hooks[i].call(cur, err, vm, info) === false;
                      if (capture) {
                        return;
                      }
                    } catch (e) {
                      globalHandleError(e, cur, 'errorCaptured hook');
                    }
                  }
                }
              }
            }
            globalHandleError(err, vm, info);
          } finally {
            popTarget();
          }
        }

        function invokeWithErrorHandling(
          handler,
          context,
          args,
          vm,
          info
        ) {
          let res;
          try {
            res = args ? handler.apply(context, args) : handler.call(context);
            if (res && !res._isVue && isPromise(res) && !res._handled) {
              res.catch(e => handleError(e, vm, `${info} (Promise/async)`));
              // issue #9511
              // avoid catch triggering multiple times when nested calls
              res._handled = true;
            }
          } catch (e) {
            handleError(e, vm, info);
          }
          return res;
        }

        function globalHandleError(err, vm, info) {
          if (config.errorHandler) {
            try {
              return config.errorHandler.call(null, err, vm, info);
            } catch (e) {
              // if the user intentionally throws the original error in the handler,
              // do not log it twice
              if (e !== err) {
                logError(e, null, 'config.errorHandler');
              }
            }
          }
          logError(err, vm, info);
        }

        function logError(err, vm, info) {
          if (true) {
            warn((`Error in ${info}: "${err.toString()}"`), vm);
          }
          /* istanbul ignore else */
          if ((inBrowser || inWeex) && typeof console !== 'undefined') {
            console.error(err);
          } else {
            throw err;
          }
        }

        /*  */

        let isUsingMicroTask = false;

        const callbacks = [];
        let pending = false;

        function flushCallbacks() {
          pending = false;
          const copies = callbacks.slice(0);
          callbacks.length = 0;
          for (let i = 0; i < copies.length; i++) {
            copies[i]();
          }
        }

        // Here we have async deferring wrappers using microtasks.
        // In 2.5 we used (macro) tasks (in combination with microtasks).
        // However, it has subtle problems when state is changed right before repaint
        // (e.g. #6813, out-in transitions).
        // Also, using (macro) tasks in event handler would cause some weird behaviors
        // that cannot be circumvented (e.g. #7109, #7153, #7546, #7834, #8109).
        // So we now use microtasks everywhere, again.
        // A major drawback of this tradeoff is that there are some scenarios
        // where microtasks have too high a priority and fire in between supposedly
        // sequential events (e.g. #4521, #6690, which have workarounds)
        // or even between bubbling of the same event (#6566).
        let timerFunc;

        // The nextTick behavior leverages the microtask queue, which can be accessed
        // via either native Promise.then or MutationObserver.
        // MutationObserver has wider support, however it is seriously bugged in
        // UIWebView in iOS >= 9.3.3 when triggered in touch event handlers. It
        // completely stops working after triggering a few times... so, if native
        // Promise is available, we will use it:
        /* istanbul ignore next, $flow-disable-line */
        if (typeof Promise !== 'undefined' && isNative(Promise)) {
          const p = Promise.resolve();
          timerFunc = function () {
            p.then(flushCallbacks);
            // In problematic UIWebViews, Promise.then doesn't completely break, but
            // it can get stuck in a weird state where callbacks are pushed into the
            // microtask queue but the queue isn't being flushed, until the browser
            // needs to do some other work, e.g. handle a timer. Therefore we can
            // "force" the microtask queue to be flushed by adding an empty timer.
            if (isIOS) {
              setTimeout(noop);
            }
          };
          isUsingMicroTask = true;
        } else if (!isIE && typeof MutationObserver !== 'undefined' && (
          isNative(MutationObserver)
  // PhantomJS and iOS 7.x
  || MutationObserver.toString() === '[object MutationObserverConstructor]'
        )) {
          // Use MutationObserver where native Promise is not available,
          // e.g. PhantomJS, iOS7, Android 4.4
          // (#6466 MutationObserver is unreliable in IE11)
          let counter = 1;
          const observer = new MutationObserver(flushCallbacks);
          const textNode = document.createTextNode(String(counter));
          observer.observe(textNode, {
            characterData: true
          });
          timerFunc = function () {
            counter = (counter + 1) % 2;
            textNode.data = String(counter);
          };
          isUsingMicroTask = true;
        } else if (typeof setImmediate !== 'undefined' && isNative(setImmediate)) {
          // Fallback to setImmediate.
          // Technically it leverages the (macro) task queue,
          // but it is still a better choice than setTimeout.
          timerFunc = function () {
            setImmediate(flushCallbacks);
          };
        } else {
          // Fallback to setTimeout.
          timerFunc = function () {
            setTimeout(flushCallbacks, 0);
          };
        }

        function nextTick(cb, ctx) {
          let _resolve;
          callbacks.push(() => {
            if (cb) {
              try {
                cb.call(ctx);
              } catch (e) {
                handleError(e, ctx, 'nextTick');
              }
            } else if (_resolve) {
              _resolve(ctx);
            }
          });
          if (!pending) {
            pending = true;
            timerFunc();
          }
          // $flow-disable-line
          if (!cb && typeof Promise !== 'undefined') {
            return new Promise((resolve) => {
              _resolve = resolve;
            });
          }
        }

        /*  */

        /* not type checking this file because flow doesn't play well with Proxy */

        let initProxy;

        if (true) {
          const allowedGlobals = makeMap('Infinity,undefined,NaN,isFinite,isNaN,'
    + 'parseFloat,parseInt,decodeURI,decodeURIComponent,encodeURI,encodeURIComponent,'
    + 'Math,Number,Date,Array,Object,Boolean,String,RegExp,Map,Set,JSON,Intl,BigInt,'
    + 'require' // for Webpack/Browserify
          );

          const warnNonPresent = function (target, key) {
            warn(
              `Property or method "${key}" is not defined on the instance but `
      + 'referenced during render. Make sure that this property is reactive, '
      + 'either in the data option, or for class-based components, by '
      + 'initializing the property. '
      + 'See: https://vuejs.org/v2/guide/reactivity.html#Declaring-Reactive-Properties.',
              target
            );
          };

          const warnReservedPrefix = function (target, key) {
            warn(
              `Property "${key}" must be accessed with "$data.${key}" because `
      + 'properties starting with "$" or "_" are not proxied in the Vue instance to '
      + 'prevent conflicts with Vue internals. '
      + 'See: https://vuejs.org/v2/api/#data',
              target
            );
          };

          const hasProxy =    typeof Proxy !== 'undefined' && isNative(Proxy);

          if (hasProxy) {
            const isBuiltInModifier = makeMap('stop,prevent,self,ctrl,shift,alt,meta,exact');
            config.keyCodes = new Proxy(config.keyCodes, {
              set: function set(target, key, value) {
                if (isBuiltInModifier(key)) {
                  warn((`Avoid overwriting built-in modifier in config.keyCodes: .${key}`));
                  return false;
                }
                target[key] = value;
                return true;
              }
            });
          }

          const hasHandler = {
            has: function has(target, key) {
              const has = key in target;
              const isAllowed = allowedGlobals(key)
        || (typeof key === 'string' && key.charAt(0) === '_' && !(key in target.$data));
              if (!has && !isAllowed) {
                if (key in target.$data) {
                  warnReservedPrefix(target, key);
                } else {
                  warnNonPresent(target, key);
                }
              }
              return has || !isAllowed;
            }
          };

          const getHandler = {
            get: function get(target, key) {
              if (typeof key === 'string' && !(key in target)) {
                if (key in target.$data) {
                  warnReservedPrefix(target, key);
                } else {
                  warnNonPresent(target, key);
                }
              }
              return target[key];
            }
          };

          initProxy = function initProxy(vm) {
            if (hasProxy) {
              // determine which proxy handler to use
              const options = vm.$options;
              const handlers = options.render && options.render._withStripped
                ? getHandler
                : hasHandler;
              vm._renderProxy = new Proxy(vm, handlers);
            } else {
              vm._renderProxy = vm;
            }
          };
        }

        /*  */

        const seenObjects = new _Set();

        /**
 * Recursively traverse an object to evoke all converted
 * getters, so that every nested property inside the object
 * is collected as a "deep" dependency.
 */
        function traverse(val) {
          _traverse(val, seenObjects);
          seenObjects.clear();
        }

        function _traverse(val, seen) {
          let i; let keys;
          const isA = Array.isArray(val);
          if ((!isA && !isObject(val)) || Object.isFrozen(val) || val instanceof VNode) {
            return;
          }
          if (val.__ob__) {
            const depId = val.__ob__.dep.id;
            if (seen.has(depId)) {
              return;
            }
            seen.add(depId);
          }
          if (isA) {
            i = val.length;
            while (i--) {
              _traverse(val[i], seen);
            }
          } else {
            keys = Object.keys(val);
            i = keys.length;
            while (i--) {
              _traverse(val[keys[i]], seen);
            }
          }
        }

        let mark;
        let measure;

        if (true) {
          const perf = inBrowser && window.performance;
          /* istanbul ignore if */
          if (
            perf
    && perf.mark
    && perf.measure
    && perf.clearMarks
    && perf.clearMeasures
          ) {
            mark = function (tag) {
              return perf.mark(tag);
            };
            measure = function (name, startTag, endTag) {
              perf.measure(name, startTag, endTag);
              perf.clearMarks(startTag);
              perf.clearMarks(endTag);
              // perf.clearMeasures(name)
            };
          }
        }

        /*  */

        const normalizeEvent = cached((name) => {
          const passive = name.charAt(0) === '&';
          name = passive ? name.slice(1) : name;
          const once$$1 = name.charAt(0) === '~'; // Prefixed last, checked first
          name = once$$1 ? name.slice(1) : name;
          const capture = name.charAt(0) === '!';
          name = capture ? name.slice(1) : name;
          return {
            name,
            once: once$$1,
            capture,
            passive
          };
        });

        function createFnInvoker(fns, vm) {
          function invoker() {
            const arguments$1 = arguments;

            const { fns } = invoker;
            if (Array.isArray(fns)) {
              const cloned = fns.slice();
              for (let i = 0; i < cloned.length; i++) {
                invokeWithErrorHandling(cloned[i], null, arguments$1, vm, 'v-on handler');
              }
            } else {
              // return handler return value for single handlers
              return invokeWithErrorHandling(fns, null, arguments, vm, 'v-on handler');
            }
          }
          invoker.fns = fns;
          return invoker;
        }

        function updateListeners(
          on,
          oldOn,
          add,
          remove$$1,
          createOnceHandler,
          vm
        ) {
          let name; let def$$1; let cur; let old; let event;
          for (name in on) {
            def$$1 = cur = on[name];
            old = oldOn[name];
            event = normalizeEvent(name);
            if (isUndef(cur)) {
              true && warn(
                `Invalid handler for event "${event.name}": got ${String(cur)}`,
                vm
              );
            } else if (isUndef(old)) {
              if (isUndef(cur.fns)) {
                cur = on[name] = createFnInvoker(cur, vm);
              }
              if (isTrue(event.once)) {
                cur = on[name] = createOnceHandler(event.name, cur, event.capture);
              }
              add(event.name, cur, event.capture, event.passive, event.params);
            } else if (cur !== old) {
              old.fns = cur;
              on[name] = old;
            }
          }
          for (name in oldOn) {
            if (isUndef(on[name])) {
              event = normalizeEvent(name);
              remove$$1(event.name, oldOn[name], event.capture);
            }
          }
        }

        /*  */

        function mergeVNodeHook(def, hookKey, hook) {
          if (def instanceof VNode) {
            def = def.data.hook || (def.data.hook = {});
          }
          let invoker;
          const oldHook = def[hookKey];

          function wrappedHook() {
            hook.apply(this, arguments);
            // important: remove merged hook to ensure it's called only once
            // and prevent memory leak
            remove(invoker.fns, wrappedHook);
          }

          if (isUndef(oldHook)) {
            // no existing hook
            invoker = createFnInvoker([wrappedHook]);
          } else {
            /* istanbul ignore if */
            if (isDef(oldHook.fns) && isTrue(oldHook.merged)) {
              // already a merged invoker
              invoker = oldHook;
              invoker.fns.push(wrappedHook);
            } else {
              // existing plain hook
              invoker = createFnInvoker([oldHook, wrappedHook]);
            }
          }

          invoker.merged = true;
          def[hookKey] = invoker;
        }

        /*  */

        function extractPropsFromVNodeData(
          data,
          Ctor,
          tag
        ) {
          // we are only extracting raw values here.
          // validation and default values are handled in the child
          // component itself.
          const propOptions = Ctor.options.props;
          if (isUndef(propOptions)) {
            return;
          }
          const res = {};
          const { attrs } = data;
          const { props } = data;
          if (isDef(attrs) || isDef(props)) {
            for (const key in propOptions) {
              const altKey = hyphenate(key);
              if (true) {
                const keyInLowerCase = key.toLowerCase();
                if (
                  key !== keyInLowerCase
          && attrs && hasOwn(attrs, keyInLowerCase)
                ) {
                  tip(`Prop "${keyInLowerCase}" is passed to component ${
                    formatComponentName(tag || Ctor)}, but the declared prop name is`
            + ` "${key}". `
            + 'Note that HTML attributes are case-insensitive and camelCased '
            + 'props need to use their kebab-case equivalents when using in-DOM '
            + `templates. You should probably use "${altKey}" instead of "${key}".`);
                }
              }
              checkProp(res, props, key, altKey, true)
      || checkProp(res, attrs, key, altKey, false);
            }
          }
          return res;
        }

        function checkProp(
          res,
          hash,
          key,
          altKey,
          preserve
        ) {
          if (isDef(hash)) {
            if (hasOwn(hash, key)) {
              res[key] = hash[key];
              if (!preserve) {
                delete hash[key];
              }
              return true;
            } if (hasOwn(hash, altKey)) {
              res[key] = hash[altKey];
              if (!preserve) {
                delete hash[altKey];
              }
              return true;
            }
          }
          return false;
        }

        /*  */

        // The template compiler attempts to minimize the need for normalization by
        // statically analyzing the template at compile time.
        //
        // For plain HTML markup, normalization can be completely skipped because the
        // generated render function is guaranteed to return Array<VNode>. There are
        // two cases where extra normalization is needed:

        // 1. When the children contains components - because a functional component
        // may return an Array instead of a single root. In this case, just a simple
        // normalization is needed - if any child is an Array, we flatten the whole
        // thing with Array.prototype.concat. It is guaranteed to be only 1-level deep
        // because functional components already normalize their own children.
        function simpleNormalizeChildren(children) {
          for (let i = 0; i < children.length; i++) {
            if (Array.isArray(children[i])) {
              return Array.prototype.concat.apply([], children);
            }
          }
          return children;
        }

        // 2. When the children contains constructs that always generated nested Arrays,
        // e.g. <template>, <slot>, v-for, or when the children is provided by user
        // with hand-written render functions / JSX. In such cases a full normalization
        // is needed to cater to all possible types of children values.
        function normalizeChildren(children) {
          return isPrimitive(children)
            ? [createTextVNode(children)]
            : Array.isArray(children)
              ? normalizeArrayChildren(children)
              : undefined;
        }

        function isTextNode(node) {
          return isDef(node) && isDef(node.text) && isFalse(node.isComment);
        }

        function normalizeArrayChildren(children, nestedIndex) {
          const res = [];
          let i; let c; let lastIndex; let last;
          for (i = 0; i < children.length; i++) {
            c = children[i];
            if (isUndef(c) || typeof c === 'boolean') {
              continue;
            }
            lastIndex = res.length - 1;
            last = res[lastIndex];
            //  nested
            if (Array.isArray(c)) {
              if (c.length > 0) {
                c = normalizeArrayChildren(c, (`${nestedIndex || ''}_${i}`));
                // merge adjacent text nodes
                if (isTextNode(c[0]) && isTextNode(last)) {
                  res[lastIndex] = createTextVNode(last.text + (c[0]).text);
                  c.shift();
                }
                res.push.apply(res, c);
              }
            } else if (isPrimitive(c)) {
              if (isTextNode(last)) {
                // merge adjacent text nodes
                // this is necessary for SSR hydration because text nodes are
                // essentially merged when rendered to HTML strings
                res[lastIndex] = createTextVNode(last.text + c);
              } else if (c !== '') {
                // convert primitive to vnode
                res.push(createTextVNode(c));
              }
            } else {
              if (isTextNode(c) && isTextNode(last)) {
                // merge adjacent text nodes
                res[lastIndex] = createTextVNode(last.text + c.text);
              } else {
                // default key for nested array children (likely generated by v-for)
                if (isTrue(children._isVList)
          && isDef(c.tag)
          && isUndef(c.key)
          && isDef(nestedIndex)) {
                  c.key = `__vlist${nestedIndex}_${i}__`;
                }
                res.push(c);
              }
            }
          }
          return res;
        }

        /*  */

        function initProvide(vm) {
          const { provide } = vm.$options;
          if (provide) {
            vm._provided = typeof provide === 'function'
              ? provide.call(vm)
              : provide;
          }
        }

        function initInjections(vm) {
          const result = resolveInject(vm.$options.inject, vm);
          if (result) {
            toggleObserving(false);
            Object.keys(result).forEach((key) => {
              /* istanbul ignore else */
              if (true) {
                defineReactive$$1(vm, key, result[key], () => {
                  warn(
                    'Avoid mutating an injected value directly since the changes will be '
            + 'overwritten whenever the provided component re-renders. '
            + `injection being mutated: "${key}"`,
                    vm
                  );
                });
              } else {}
            });
            toggleObserving(true);
          }
        }

        function resolveInject(inject, vm) {
          if (inject) {
            // inject is :any because flow is not smart enough to figure out cached
            const result = Object.create(null);
            const keys = hasSymbol
              ? Reflect.ownKeys(inject)
              : Object.keys(inject);

            for (let i = 0; i < keys.length; i++) {
              const key = keys[i];
              // #6574 in case the inject object is observed...
              if (key === '__ob__') {
                continue;
              }
              const provideKey = inject[key].from;
              let source = vm;
              while (source) {
                if (source._provided && hasOwn(source._provided, provideKey)) {
                  result[key] = source._provided[provideKey];
                  break;
                }
                source = source.$parent;
              }
              if (!source) {
                if ('default' in inject[key]) {
                  const provideDefault = inject[key].default;
                  result[key] = typeof provideDefault === 'function'
                    ? provideDefault.call(vm)
                    : provideDefault;
                } else if (true) {
                  warn((`Injection "${key}" not found`), vm);
                }
              }
            }
            return result;
          }
        }

        /*  */


        /**
 * Runtime helper for resolving raw children VNodes into a slot object.
 */
        function resolveSlots(
          children,
          context
        ) {
          if (!children || !children.length) {
            return {};
          }
          const slots = {};
          for (let i = 0, l = children.length; i < l; i++) {
            const child = children[i];
            const { data } = child;
            // remove slot attribute if the node is resolved as a Vue slot node
            if (data && data.attrs && data.attrs.slot) {
              delete data.attrs.slot;
            }
            // named slots should only be respected if the vnode was rendered in the
            // same context.
            if ((child.context === context || child.fnContext === context)
      && data && data.slot != null
            ) {
              const name = data.slot;
              const slot = (slots[name] || (slots[name] = []));
              if (child.tag === 'template') {
                slot.push.apply(slot, child.children || []);
              } else {
                slot.push(child);
              }
            } else {
              (slots.default || (slots.default = [])).push(child);
            }
          }
          // ignore slots that contains only whitespace
          for (const name$1 in slots) {
            if (slots[name$1].every(isWhitespace)) {
              delete slots[name$1];
            }
          }
          return slots;
        }

        function isWhitespace(node) {
          return (node.isComment && !node.asyncFactory) || node.text === ' ';
        }

        /*  */

        function isAsyncPlaceholder(node) {
          return node.isComment && node.asyncFactory;
        }

        /*  */

        function normalizeScopedSlots(
          slots,
          normalSlots,
          prevSlots
        ) {
          let res;
          const hasNormalSlots = Object.keys(normalSlots).length > 0;
          const isStable = slots ? !!slots.$stable : !hasNormalSlots;
          const key = slots && slots.$key;
          if (!slots) {
            res = {};
          } else if (slots._normalized) {
            // fast path 1: child component re-render only, parent did not change
            return slots._normalized;
          } else if (
            isStable
    && prevSlots
    && prevSlots !== emptyObject
    && key === prevSlots.$key
    && !hasNormalSlots
    && !prevSlots.$hasNormal
          ) {
            // fast path 2: stable scoped slots w/ no normal slots to proxy,
            // only need to normalize once
            return prevSlots;
          } else {
            res = {};
            for (const key$1 in slots) {
              if (slots[key$1] && key$1[0] !== '$') {
                res[key$1] = normalizeScopedSlot(normalSlots, key$1, slots[key$1]);
              }
            }
          }
          // expose normal slots on scopedSlots
          for (const key$2 in normalSlots) {
            if (!(key$2 in res)) {
              res[key$2] = proxyNormalSlot(normalSlots, key$2);
            }
          }
          // avoriaz seems to mock a non-extensible $scopedSlots object
          // and when that is passed down this would cause an error
          if (slots && Object.isExtensible(slots)) {
            (slots)._normalized = res;
          }
          def(res, '$stable', isStable);
          def(res, '$key', key);
          def(res, '$hasNormal', hasNormalSlots);
          return res;
        }

        function normalizeScopedSlot(normalSlots, key, fn) {
          const normalized = function () {
            let res = arguments.length ? fn.apply(null, arguments) : fn({});
            res = res && typeof res === 'object' && !Array.isArray(res)
              ? [res] // single vnode
              : normalizeChildren(res);
            const vnode = res && res[0];
            return res && (
              !vnode
      || (res.length === 1 && vnode.isComment && !isAsyncPlaceholder(vnode)) // #9658, #10391
            ) ? undefined
              : res;
          };
          // this is a slot using the new v-slot syntax without scope. although it is
          // compiled as a scoped slot, render fn users would expect it to be present
          // on this.$slots because the usage is semantically a normal slot.
          if (fn.proxy) {
            Object.defineProperty(normalSlots, key, {
              get: normalized,
              enumerable: true,
              configurable: true
            });
          }
          return normalized;
        }

        function proxyNormalSlot(slots, key) {
          return function () {
            return slots[key];
          };
        }

        /*  */

        /**
 * Runtime helper for rendering v-for lists.
 */
        function renderList(
          val,
          render
        ) {
          let ret; let i; let l; let keys; let key;
          if (Array.isArray(val) || typeof val === 'string') {
            ret = new Array(val.length);
            for (i = 0, l = val.length; i < l; i++) {
              ret[i] = render(val[i], i);
            }
          } else if (typeof val === 'number') {
            ret = new Array(val);
            for (i = 0; i < val; i++) {
              ret[i] = render(i + 1, i);
            }
          } else if (isObject(val)) {
            if (hasSymbol && val[Symbol.iterator]) {
              ret = [];
              const iterator = val[Symbol.iterator]();
              let result = iterator.next();
              while (!result.done) {
                ret.push(render(result.value, ret.length));
                result = iterator.next();
              }
            } else {
              keys = Object.keys(val);
              ret = new Array(keys.length);
              for (i = 0, l = keys.length; i < l; i++) {
                key = keys[i];
                ret[i] = render(val[key], key, i);
              }
            }
          }
          if (!isDef(ret)) {
            ret = [];
          }
          (ret)._isVList = true;
          return ret;
        }

        /*  */

        /**
 * Runtime helper for rendering <slot>
 */
        function renderSlot(
          name,
          fallbackRender,
          props,
          bindObject
        ) {
          const scopedSlotFn = this.$scopedSlots[name];
          let nodes;
          if (scopedSlotFn) {
            // scoped slot
            props = props || {};
            if (bindObject) {
              if (true && !isObject(bindObject)) {
                warn('slot v-bind without argument expects an Object', this);
              }
              props = extend(extend({}, bindObject), props);
            }
            nodes =      scopedSlotFn(props)
      || (typeof fallbackRender === 'function' ? fallbackRender() : fallbackRender);
          } else {
            nodes =      this.$slots[name]
      || (typeof fallbackRender === 'function' ? fallbackRender() : fallbackRender);
          }

          const target = props && props.slot;
          if (target) {
            return this.$createElement('template', { slot: target }, nodes);
          }
          return nodes;
        }

        /*  */

        /**
 * Runtime helper for resolving filters
 */
        function resolveFilter(id) {
          return resolveAsset(this.$options, 'filters', id, true) || identity;
        }

        /*  */

        function isKeyNotMatch(expect, actual) {
          if (Array.isArray(expect)) {
            return expect.indexOf(actual) === -1;
          }
          return expect !== actual;
        }

        /**
 * Runtime helper for checking keyCodes from config.
 * exposed as Vue.prototype._k
 * passing in eventKeyName as last argument separately for backwards compat
 */
        function checkKeyCodes(
          eventKeyCode,
          key,
          builtInKeyCode,
          eventKeyName,
          builtInKeyName
        ) {
          const mappedKeyCode = config.keyCodes[key] || builtInKeyCode;
          if (builtInKeyName && eventKeyName && !config.keyCodes[key]) {
            return isKeyNotMatch(builtInKeyName, eventKeyName);
          } if (mappedKeyCode) {
            return isKeyNotMatch(mappedKeyCode, eventKeyCode);
          } if (eventKeyName) {
            return hyphenate(eventKeyName) !== key;
          }
          return eventKeyCode === undefined;
        }

        /*  */

        /**
 * Runtime helper for merging v-bind="object" into a VNode's data.
 */
        function bindObjectProps(
          data,
          tag,
          value,
          asProp,
          isSync
        ) {
          if (value) {
            if (!isObject(value)) {
              true && warn(
                'v-bind without argument expects an Object or Array value',
                this
              );
            } else {
              if (Array.isArray(value)) {
                value = toObject(value);
              }
              let hash;
              const loop = function (key) {
                if (
                  key === 'class'
          || key === 'style'
          || isReservedAttribute(key)
                ) {
                  hash = data;
                } else {
                  const type = data.attrs && data.attrs.type;
                  hash = asProp || config.mustUseProp(tag, type, key)
                    ? data.domProps || (data.domProps = {})
                    : data.attrs || (data.attrs = {});
                }
                const camelizedKey = camelize(key);
                const hyphenatedKey = hyphenate(key);
                if (!(camelizedKey in hash) && !(hyphenatedKey in hash)) {
                  hash[key] = value[key];

                  if (isSync) {
                    const on = data.on || (data.on = {});
                    on[(`update:${key}`)] = function ($event) {
                      value[key] = $event;
                    };
                  }
                }
              };

              for (const key in value) loop(key);
            }
          }
          return data;
        }

        /*  */

        /**
 * Runtime helper for rendering static trees.
 */
        function renderStatic(
          index,
          isInFor
        ) {
          const cached = this._staticTrees || (this._staticTrees = []);
          let tree = cached[index];
          // if has already-rendered static tree and not inside v-for,
          // we can reuse the same tree.
          if (tree && !isInFor) {
            return tree;
          }
          // otherwise, render a fresh tree.
          tree = cached[index] = this.$options.staticRenderFns[index].call(
            this._renderProxy,
            null,
            this // for render fns generated for functional component templates
          );
          markStatic(tree, (`__static__${index}`), false);
          return tree;
        }

        /**
 * Runtime helper for v-once.
 * Effectively it means marking the node as static with a unique key.
 */
        function markOnce(
          tree,
          index,
          key
        ) {
          markStatic(tree, (`__once__${index}${key ? (`_${key}`) : ''}`), true);
          return tree;
        }

        function markStatic(
          tree,
          key,
          isOnce
        ) {
          if (Array.isArray(tree)) {
            for (let i = 0; i < tree.length; i++) {
              if (tree[i] && typeof tree[i] !== 'string') {
                markStaticNode(tree[i], (`${key}_${i}`), isOnce);
              }
            }
          } else {
            markStaticNode(tree, key, isOnce);
          }
        }

        function markStaticNode(node, key, isOnce) {
          node.isStatic = true;
          node.key = key;
          node.isOnce = isOnce;
        }

        /*  */

        function bindObjectListeners(data, value) {
          if (value) {
            if (!isPlainObject(value)) {
              true && warn(
                'v-on without argument expects an Object value',
                this
              );
            } else {
              const on = data.on = data.on ? extend({}, data.on) : {};
              for (const key in value) {
                const existing = on[key];
                const ours = value[key];
                on[key] = existing ? [].concat(existing, ours) : ours;
              }
            }
          }
          return data;
        }

        /*  */

        function resolveScopedSlots(
          fns, // see flow/vnode
          res,
          // the following are added in 2.6
          hasDynamicKeys,
          contentHashKey
        ) {
          res = res || { $stable: !hasDynamicKeys };
          for (let i = 0; i < fns.length; i++) {
            const slot = fns[i];
            if (Array.isArray(slot)) {
              resolveScopedSlots(slot, res, hasDynamicKeys);
            } else if (slot) {
              // marker for reverse proxying v-slot without scope on this.$slots
              if (slot.proxy) {
                slot.fn.proxy = true;
              }
              res[slot.key] = slot.fn;
            }
          }
          if (contentHashKey) {
            (res).$key = contentHashKey;
          }
          return res;
        }

        /*  */

        function bindDynamicKeys(baseObj, values) {
          for (let i = 0; i < values.length; i += 2) {
            const key = values[i];
            if (typeof key === 'string' && key) {
              baseObj[values[i]] = values[i + 1];
            } else if (true && key !== '' && key !== null) {
              // null is a special value for explicitly removing a binding
              warn(
                (`Invalid value for dynamic directive argument (expected string or null): ${key}`),
                this
              );
            }
          }
          return baseObj;
        }

        // helper to dynamically append modifier runtime markers to event names.
        // ensure only append when value is already string, otherwise it will be cast
        // to string and cause the type check to miss.
        function prependModifier(value, symbol) {
          return typeof value === 'string' ? symbol + value : value;
        }

        /*  */

        function installRenderHelpers(target) {
          target._o = markOnce;
          target._n = toNumber;
          target._s = toString;
          target._l = renderList;
          target._t = renderSlot;
          target._q = looseEqual;
          target._i = looseIndexOf;
          target._m = renderStatic;
          target._f = resolveFilter;
          target._k = checkKeyCodes;
          target._b = bindObjectProps;
          target._v = createTextVNode;
          target._e = createEmptyVNode;
          target._u = resolveScopedSlots;
          target._g = bindObjectListeners;
          target._d = bindDynamicKeys;
          target._p = prependModifier;
        }

        /*  */

        function FunctionalRenderContext(
          data,
          props,
          children,
          parent,
          Ctor
        ) {
          const this$1 = this;

          const { options } = Ctor;
          // ensure the createElement function in functional components
          // gets a unique context - this is necessary for correct named slot check
          let contextVm;
          if (hasOwn(parent, '_uid')) {
            contextVm = Object.create(parent);
            // $flow-disable-line
            contextVm._original = parent;
          } else {
            // the context vm passed in is a functional context as well.
            // in this case we want to make sure we are able to get a hold to the
            // real context instance.
            contextVm = parent;
            // $flow-disable-line
            parent = parent._original;
          }
          const isCompiled = isTrue(options._compiled);
          const needNormalization = !isCompiled;

          this.data = data;
          this.props = props;
          this.children = children;
          this.parent = parent;
          this.listeners = data.on || emptyObject;
          this.injections = resolveInject(options.inject, parent);
          this.slots = function () {
            if (!this$1.$slots) {
              normalizeScopedSlots(
                data.scopedSlots,
                this$1.$slots = resolveSlots(children, parent)
              );
            }
            return this$1.$slots;
          };

          Object.defineProperty(this, 'scopedSlots', ({
            enumerable: true,
            get: function get() {
              return normalizeScopedSlots(data.scopedSlots, this.slots());
            }
          }));

          // support for compiled functional template
          if (isCompiled) {
            // exposing $options for renderStatic()
            this.$options = options;
            // pre-resolve slots for renderSlot()
            this.$slots = this.slots();
            this.$scopedSlots = normalizeScopedSlots(data.scopedSlots, this.$slots);
          }

          if (options._scopeId) {
            this._c = function (a, b, c, d) {
              const vnode = createElement(contextVm, a, b, c, d, needNormalization);
              if (vnode && !Array.isArray(vnode)) {
                vnode.fnScopeId = options._scopeId;
                vnode.fnContext = parent;
              }
              return vnode;
            };
          } else {
            this._c = function (a, b, c, d) {
              return createElement(contextVm, a, b, c, d, needNormalization);
            };
          }
        }

        installRenderHelpers(FunctionalRenderContext.prototype);

        function createFunctionalComponent(
          Ctor,
          propsData,
          data,
          contextVm,
          children
        ) {
          const { options } = Ctor;
          const props = {};
          const propOptions = options.props;
          if (isDef(propOptions)) {
            for (const key in propOptions) {
              props[key] = validateProp(key, propOptions, propsData || emptyObject);
            }
          } else {
            if (isDef(data.attrs)) {
              mergeProps(props, data.attrs);
            }
            if (isDef(data.props)) {
              mergeProps(props, data.props);
            }
          }

          const renderContext = new FunctionalRenderContext(
            data,
            props,
            children,
            contextVm,
            Ctor
          );

          const vnode = options.render.call(null, renderContext._c, renderContext);

          if (vnode instanceof VNode) {
            return cloneAndMarkFunctionalResult(vnode, data, renderContext.parent, options, renderContext);
          } if (Array.isArray(vnode)) {
            const vnodes = normalizeChildren(vnode) || [];
            const res = new Array(vnodes.length);
            for (let i = 0; i < vnodes.length; i++) {
              res[i] = cloneAndMarkFunctionalResult(vnodes[i], data, renderContext.parent, options, renderContext);
            }
            return res;
          }
        }

        function cloneAndMarkFunctionalResult(vnode, data, contextVm, options, renderContext) {
          // #7817 clone node before setting fnContext, otherwise if the node is reused
          // (e.g. it was from a cached normal slot) the fnContext causes named slots
          // that should not be matched to match.
          const clone = cloneVNode(vnode);
          clone.fnContext = contextVm;
          clone.fnOptions = options;
          if (true) {
            (clone.devtoolsMeta = clone.devtoolsMeta || {}).renderContext = renderContext;
          }
          if (data.slot) {
            (clone.data || (clone.data = {})).slot = data.slot;
          }
          return clone;
        }

        function mergeProps(to, from) {
          for (const key in from) {
            to[camelize(key)] = from[key];
          }
        }

        /*  */

        /*  */

        /*  */

        /*  */

        // inline hooks to be invoked on component VNodes during patch
        var componentVNodeHooks = {
          init: function init(vnode, hydrating) {
            if (
              vnode.componentInstance
      && !vnode.componentInstance._isDestroyed
      && vnode.data.keepAlive
            ) {
              // kept-alive components, treat as a patch
              const mountedNode = vnode; // work around flow
              componentVNodeHooks.prepatch(mountedNode, mountedNode);
            } else {
              const child = vnode.componentInstance = createComponentInstanceForVnode(
                vnode,
                activeInstance
              );
              child.$mount(hydrating ? vnode.elm : undefined, hydrating);
            }
          },

          prepatch: function prepatch(oldVnode, vnode) {
            const options = vnode.componentOptions;
            const child = vnode.componentInstance = oldVnode.componentInstance;
            updateChildComponent(
              child,
              options.propsData, // updated props
              options.listeners, // updated listeners
              vnode, // new parent vnode
              options.children // new children
            );
          },

          insert: function insert(vnode) {
            const { context } = vnode;
            const { componentInstance } = vnode;
            if (!componentInstance._isMounted) {
              componentInstance._isMounted = true;
              callHook(componentInstance, 'mounted');
            }
            if (vnode.data.keepAlive) {
              if (context._isMounted) {
                // vue-router#1212
                // During updates, a kept-alive component's child components may
                // change, so directly walking the tree here may call activated hooks
                // on incorrect children. Instead we push them into a queue which will
                // be processed after the whole patch process ended.
                queueActivatedComponent(componentInstance);
              } else {
                activateChildComponent(componentInstance, true /* direct */);
              }
            }
          },

          destroy: function destroy(vnode) {
            const { componentInstance } = vnode;
            if (!componentInstance._isDestroyed) {
              if (!vnode.data.keepAlive) {
                componentInstance.$destroy();
              } else {
                deactivateChildComponent(componentInstance, true /* direct */);
              }
            }
          }
        };

        const hooksToMerge = Object.keys(componentVNodeHooks);

        function createComponent(
          Ctor,
          data,
          context,
          children,
          tag
        ) {
          if (isUndef(Ctor)) {
            return;
          }

          const baseCtor = context.$options._base;

          // plain options object: turn it into a constructor
          if (isObject(Ctor)) {
            Ctor = baseCtor.extend(Ctor);
          }

          // if at this stage it's not a constructor or an async component factory,
          // reject.
          if (typeof Ctor !== 'function') {
            if (true) {
              warn((`Invalid Component definition: ${String(Ctor)}`), context);
            }
            return;
          }

          // async component
          let asyncFactory;
          if (isUndef(Ctor.cid)) {
            asyncFactory = Ctor;
            Ctor = resolveAsyncComponent(asyncFactory, baseCtor);
            if (Ctor === undefined) {
              // return a placeholder node for async component, which is rendered
              // as a comment node but preserves all the raw information for the node.
              // the information will be used for async server-rendering and hydration.
              return createAsyncPlaceholder(
                asyncFactory,
                data,
                context,
                children,
                tag
              );
            }
          }

          data = data || {};

          // resolve constructor options in case global mixins are applied after
          // component constructor creation
          resolveConstructorOptions(Ctor);

          // transform component v-model data into props & events
          if (isDef(data.model)) {
            transformModel(Ctor.options, data);
          }

          // extract props
          const propsData = extractPropsFromVNodeData(data, Ctor, tag);

          // functional component
          if (isTrue(Ctor.options.functional)) {
            return createFunctionalComponent(Ctor, propsData, data, context, children);
          }

          // extract listeners, since these needs to be treated as
          // child component listeners instead of DOM listeners
          const listeners = data.on;
          // replace with listeners with .native modifier
          // so it gets processed during parent component patch.
          data.on = data.nativeOn;

          if (isTrue(Ctor.options.abstract)) {
            // abstract components do not keep anything
            // other than props & listeners & slot

            // work around flow
            const { slot } = data;
            data = {};
            if (slot) {
              data.slot = slot;
            }
          }

          // install component management hooks onto the placeholder node
          installComponentHooks(data);

          // return a placeholder vnode
          const name = Ctor.options.name || tag;
          const vnode = new VNode(
            (`vue-component-${Ctor.cid}${name ? (`-${name}`) : ''}`),
            data, undefined, undefined, undefined, context,
            { Ctor, propsData, listeners, tag, children },
            asyncFactory
          );

          return vnode;
        }

        function createComponentInstanceForVnode(
          // we know it's MountedComponentVNode but flow doesn't
          vnode,
          // activeInstance in lifecycle state
          parent
        ) {
          const options = {
            _isComponent: true,
            _parentVnode: vnode,
            parent
          };
          // check inline-template render functions
          const { inlineTemplate } = vnode.data;
          if (isDef(inlineTemplate)) {
            options.render = inlineTemplate.render;
            options.staticRenderFns = inlineTemplate.staticRenderFns;
          }
          return new vnode.componentOptions.Ctor(options);
        }

        function installComponentHooks(data) {
          const hooks = data.hook || (data.hook = {});
          for (let i = 0; i < hooksToMerge.length; i++) {
            const key = hooksToMerge[i];
            const existing = hooks[key];
            const toMerge = componentVNodeHooks[key];
            if (existing !== toMerge && !(existing && existing._merged)) {
              hooks[key] = existing ? mergeHook$1(toMerge, existing) : toMerge;
            }
          }
        }

        function mergeHook$1(f1, f2) {
          const merged = function (a, b) {
            // flow complains about extra args which is why we use any
            f1(a, b);
            f2(a, b);
          };
          merged._merged = true;
          return merged;
        }

        // transform component v-model info (value and callback) into
        // prop and event handler respectively.
        function transformModel(options, data) {
          const prop = (options.model && options.model.prop) || 'value';
          const event = (options.model && options.model.event) || 'input'
  ;(data.attrs || (data.attrs = {}))[prop] = data.model.value;
          const on = data.on || (data.on = {});
          const existing = on[event];
          const { callback } = data.model;
          if (isDef(existing)) {
            if (
              Array.isArray(existing)
                ? existing.indexOf(callback) === -1
                : existing !== callback
            ) {
              on[event] = [callback].concat(existing);
            }
          } else {
            on[event] = callback;
          }
        }

        /*  */

        const SIMPLE_NORMALIZE = 1;
        const ALWAYS_NORMALIZE = 2;

        // wrapper function for providing a more flexible interface
        // without getting yelled at by flow
        function createElement(
          context,
          tag,
          data,
          children,
          normalizationType,
          alwaysNormalize
        ) {
          if (Array.isArray(data) || isPrimitive(data)) {
            normalizationType = children;
            children = data;
            data = undefined;
          }
          if (isTrue(alwaysNormalize)) {
            normalizationType = ALWAYS_NORMALIZE;
          }
          return _createElement(context, tag, data, children, normalizationType);
        }

        function _createElement(
          context,
          tag,
          data,
          children,
          normalizationType
        ) {
          if (isDef(data) && isDef((data).__ob__)) {
            true && warn(
              `Avoid using observed data object as vnode data: ${JSON.stringify(data)}\n`
      + 'Always create fresh vnode data objects in each render!',
              context
            );
            return createEmptyVNode();
          }
          // object syntax in v-bind
          if (isDef(data) && isDef(data.is)) {
            tag = data.is;
          }
          if (!tag) {
            // in case of component :is set to falsy value
            return createEmptyVNode();
          }
          // warn against non-primitive key
          if (true
    && isDef(data) && isDef(data.key) && !isPrimitive(data.key)
          ) {
            {
              warn(
                'Avoid using non-primitive value as key, '
        + 'use string/number value instead.',
                context
              );
            }
          }
          // support single function children as default scoped slot
          if (Array.isArray(children)
    && typeof children[0] === 'function'
          ) {
            data = data || {};
            data.scopedSlots = { default: children[0] };
            children.length = 0;
          }
          if (normalizationType === ALWAYS_NORMALIZE) {
            children = normalizeChildren(children);
          } else if (normalizationType === SIMPLE_NORMALIZE) {
            children = simpleNormalizeChildren(children);
          }
          let vnode; let ns;
          if (typeof tag === 'string') {
            let Ctor;
            ns = (context.$vnode && context.$vnode.ns) || config.getTagNamespace(tag);
            if (config.isReservedTag(tag)) {
              // platform built-in elements
              if (true && isDef(data) && isDef(data.nativeOn) && data.tag !== 'component') {
                warn(
                  (`The .native modifier for v-on is only valid on components but it was used on <${tag}>.`),
                  context
                );
              }
              vnode = new VNode(
                config.parsePlatformTagName(tag), data, children,
                undefined, undefined, context
              );
            } else if ((!data || !data.pre) && isDef(Ctor = resolveAsset(context.$options, 'components', tag))) {
              // component
              vnode = createComponent(Ctor, data, context, children, tag);
            } else {
              // unknown or unlisted namespaced elements
              // check at runtime because it may get assigned a namespace when its
              // parent normalizes children
              vnode = new VNode(
                tag, data, children,
                undefined, undefined, context
              );
            }
          } else {
            // direct component options / constructor
            vnode = createComponent(tag, data, context, children);
          }
          if (Array.isArray(vnode)) {
            return vnode;
          } if (isDef(vnode)) {
            if (isDef(ns)) {
              applyNS(vnode, ns);
            }
            if (isDef(data)) {
              registerDeepBindings(data);
            }
            return vnode;
          }
          return createEmptyVNode();
        }

        function applyNS(vnode, ns, force) {
          vnode.ns = ns;
          if (vnode.tag === 'foreignObject') {
            // use default namespace inside foreignObject
            ns = undefined;
            force = true;
          }
          if (isDef(vnode.children)) {
            for (let i = 0, l = vnode.children.length; i < l; i++) {
              const child = vnode.children[i];
              if (isDef(child.tag) && (
                isUndef(child.ns) || (isTrue(force) && child.tag !== 'svg'))) {
                applyNS(child, ns, force);
              }
            }
          }
        }

        // ref #5318
        // necessary to ensure parent re-render when deep bindings like :style and
        // :class are used on slot nodes
        function registerDeepBindings(data) {
          if (isObject(data.style)) {
            traverse(data.style);
          }
          if (isObject(data.class)) {
            traverse(data.class);
          }
        }

        /*  */

        function initRender(vm) {
          vm._vnode = null; // the root of the child tree
          vm._staticTrees = null; // v-once cached trees
          const options = vm.$options;
          const parentVnode = vm.$vnode = options._parentVnode; // the placeholder node in parent tree
          const renderContext = parentVnode && parentVnode.context;
          vm.$slots = resolveSlots(options._renderChildren, renderContext);
          vm.$scopedSlots = emptyObject;
          // bind the createElement fn to this instance
          // so that we get proper render context inside it.
          // args order: tag, data, children, normalizationType, alwaysNormalize
          // internal version is used by render functions compiled from templates
          vm._c = function (a, b, c, d) {
            return createElement(vm, a, b, c, d, false);
          };
          // normalization is always applied for the public version, used in
          // user-written render functions.
          vm.$createElement = function (a, b, c, d) {
            return createElement(vm, a, b, c, d, true);
          };

          // $attrs & $listeners are exposed for easier HOC creation.
          // they need to be reactive so that HOCs using them are always updated
          const parentData = parentVnode && parentVnode.data;

          /* istanbul ignore else */
          if (true) {
            defineReactive$$1(vm, '$attrs', parentData && parentData.attrs || emptyObject, () => {
              !isUpdatingChildComponent && warn('$attrs is readonly.', vm);
            }, true);
            defineReactive$$1(vm, '$listeners', options._parentListeners || emptyObject, () => {
              !isUpdatingChildComponent && warn('$listeners is readonly.', vm);
            }, true);
          } else {}
        }

        let currentRenderingInstance = null;

        function renderMixin(Vue) {
          // install runtime convenience helpers
          installRenderHelpers(Vue.prototype);

          Vue.prototype.$nextTick = function (fn) {
            return nextTick(fn, this);
          };

          Vue.prototype._render = function () {
            const vm = this;
            const ref = vm.$options;
            const { render } = ref;
            const { _parentVnode } = ref;

            if (_parentVnode) {
              vm.$scopedSlots = normalizeScopedSlots(
                _parentVnode.data.scopedSlots,
                vm.$slots,
                vm.$scopedSlots
              );
            }

            // set parent vnode. this allows render functions to have access
            // to the data on the placeholder node.
            vm.$vnode = _parentVnode;
            // render self
            let vnode;
            try {
              // There's no need to maintain a stack because all render fns are called
              // separately from one another. Nested component's render fns are called
              // when parent component is patched.
              currentRenderingInstance = vm;
              vnode = render.call(vm._renderProxy, vm.$createElement);
            } catch (e) {
              handleError(e, vm, 'render');
              // return error render result,
              // or previous vnode to prevent render error causing blank component
              /* istanbul ignore else */
              if (true && vm.$options.renderError) {
                try {
                  vnode = vm.$options.renderError.call(vm._renderProxy, vm.$createElement, e);
                } catch (e) {
                  handleError(e, vm, 'renderError');
                  vnode = vm._vnode;
                }
              } else {
                vnode = vm._vnode;
              }
            } finally {
              currentRenderingInstance = null;
            }
            // if the returned array contains only a single node, allow it
            if (Array.isArray(vnode) && vnode.length === 1) {
              vnode = vnode[0];
            }
            // return empty vnode in case the render function errored out
            if (!(vnode instanceof VNode)) {
              if (true && Array.isArray(vnode)) {
                warn(
                  'Multiple root nodes returned from render function. Render function '
          + 'should return a single root node.',
                  vm
                );
              }
              vnode = createEmptyVNode();
            }
            // set parent
            vnode.parent = _parentVnode;
            return vnode;
          };
        }

        /*  */

        function ensureCtor(comp, base) {
          if (
            comp.__esModule
    || (hasSymbol && comp[Symbol.toStringTag] === 'Module')
          ) {
            comp = comp.default;
          }
          return isObject(comp)
            ? base.extend(comp)
            : comp;
        }

        function createAsyncPlaceholder(
          factory,
          data,
          context,
          children,
          tag
        ) {
          const node = createEmptyVNode();
          node.asyncFactory = factory;
          node.asyncMeta = { data, context, children, tag };
          return node;
        }

        function resolveAsyncComponent(
          factory,
          baseCtor
        ) {
          if (isTrue(factory.error) && isDef(factory.errorComp)) {
            return factory.errorComp;
          }

          if (isDef(factory.resolved)) {
            return factory.resolved;
          }

          const owner = currentRenderingInstance;
          if (owner && isDef(factory.owners) && factory.owners.indexOf(owner) === -1) {
            // already pending
            factory.owners.push(owner);
          }

          if (isTrue(factory.loading) && isDef(factory.loadingComp)) {
            return factory.loadingComp;
          }

          if (owner && !isDef(factory.owners)) {
            const owners = factory.owners = [owner];
            let sync = true;
            let timerLoading = null;
            let timerTimeout = null

    ;(owner).$on('hook:destroyed', () => remove(owners, owner));

            const forceRender = function (renderCompleted) {
              for (let i = 0, l = owners.length; i < l; i++) {
                (owners[i]).$forceUpdate();
              }

              if (renderCompleted) {
                owners.length = 0;
                if (timerLoading !== null) {
                  clearTimeout(timerLoading);
                  timerLoading = null;
                }
                if (timerTimeout !== null) {
                  clearTimeout(timerTimeout);
                  timerTimeout = null;
                }
              }
            };

            const resolve = once((res) => {
              // cache resolved
              factory.resolved = ensureCtor(res, baseCtor);
              // invoke callbacks only if this is not a synchronous resolve
              // (async resolves are shimmed as synchronous during SSR)
              if (!sync) {
                forceRender(true);
              } else {
                owners.length = 0;
              }
            });

            const reject = once((reason) => {
              true && warn(`Failed to resolve async component: ${String(factory)
              }${reason ? (`\nReason: ${reason}`) : ''}`);
              if (isDef(factory.errorComp)) {
                factory.error = true;
                forceRender(true);
              }
            });

            const res = factory(resolve, reject);

            if (isObject(res)) {
              if (isPromise(res)) {
                // () => Promise
                if (isUndef(factory.resolved)) {
                  res.then(resolve, reject);
                }
              } else if (isPromise(res.component)) {
                res.component.then(resolve, reject);

                if (isDef(res.error)) {
                  factory.errorComp = ensureCtor(res.error, baseCtor);
                }

                if (isDef(res.loading)) {
                  factory.loadingComp = ensureCtor(res.loading, baseCtor);
                  if (res.delay === 0) {
                    factory.loading = true;
                  } else {
                    timerLoading = setTimeout(() => {
                      timerLoading = null;
                      if (isUndef(factory.resolved) && isUndef(factory.error)) {
                        factory.loading = true;
                        forceRender(false);
                      }
                    }, res.delay || 200);
                  }
                }

                if (isDef(res.timeout)) {
                  timerTimeout = setTimeout(() => {
                    timerTimeout = null;
                    if (isUndef(factory.resolved)) {
                      reject(true
                        ? (`timeout (${res.timeout}ms)`)
                        : 0);
                    }
                  }, res.timeout);
                }
              }
            }

            sync = false;
            // return in case resolved synchronously
            return factory.loading
              ? factory.loadingComp
              : factory.resolved;
          }
        }

        /*  */

        function getFirstComponentChild(children) {
          if (Array.isArray(children)) {
            for (let i = 0; i < children.length; i++) {
              const c = children[i];
              if (isDef(c) && (isDef(c.componentOptions) || isAsyncPlaceholder(c))) {
                return c;
              }
            }
          }
        }

        /*  */

        /*  */

        function initEvents(vm) {
          vm._events = Object.create(null);
          vm._hasHookEvent = false;
          // init parent attached events
          const listeners = vm.$options._parentListeners;
          if (listeners) {
            updateComponentListeners(vm, listeners);
          }
        }

        let target;

        function add(event, fn) {
          target.$on(event, fn);
        }

        function remove$1(event, fn) {
          target.$off(event, fn);
        }

        function createOnceHandler(event, fn) {
          const _target = target;
          return function onceHandler() {
            const res = fn.apply(null, arguments);
            if (res !== null) {
              _target.$off(event, onceHandler);
            }
          };
        }

        function updateComponentListeners(
          vm,
          listeners,
          oldListeners
        ) {
          target = vm;
          updateListeners(listeners, oldListeners || {}, add, remove$1, createOnceHandler, vm);
          target = undefined;
        }

        function eventsMixin(Vue) {
          const hookRE = /^hook:/;
          Vue.prototype.$on = function (event, fn) {
            const vm = this;
            if (Array.isArray(event)) {
              for (let i = 0, l = event.length; i < l; i++) {
                vm.$on(event[i], fn);
              }
            } else {
              (vm._events[event] || (vm._events[event] = [])).push(fn);
              // optimize hook:event cost by using a boolean flag marked at registration
              // instead of a hash lookup
              if (hookRE.test(event)) {
                vm._hasHookEvent = true;
              }
            }
            return vm;
          };

          Vue.prototype.$once = function (event, fn) {
            const vm = this;
            function on() {
              vm.$off(event, on);
              fn.apply(vm, arguments);
            }
            on.fn = fn;
            vm.$on(event, on);
            return vm;
          };

          Vue.prototype.$off = function (event, fn) {
            const vm = this;
            // all
            if (!arguments.length) {
              vm._events = Object.create(null);
              return vm;
            }
            // array of events
            if (Array.isArray(event)) {
              for (let i$1 = 0, l = event.length; i$1 < l; i$1++) {
                vm.$off(event[i$1], fn);
              }
              return vm;
            }
            // specific event
            const cbs = vm._events[event];
            if (!cbs) {
              return vm;
            }
            if (!fn) {
              vm._events[event] = null;
              return vm;
            }
            // specific handler
            let cb;
            let i = cbs.length;
            while (i--) {
              cb = cbs[i];
              if (cb === fn || cb.fn === fn) {
                cbs.splice(i, 1);
                break;
              }
            }
            return vm;
          };

          Vue.prototype.$emit = function (event) {
            const vm = this;
            if (true) {
              const lowerCaseEvent = event.toLowerCase();
              if (lowerCaseEvent !== event && vm._events[lowerCaseEvent]) {
                tip(`Event "${lowerCaseEvent}" is emitted in component ${
                  formatComponentName(vm)} but the handler is registered for "${event}". `
          + 'Note that HTML attributes are case-insensitive and you cannot use '
          + 'v-on to listen to camelCase events when using in-DOM templates. '
          + `You should probably use "${hyphenate(event)}" instead of "${event}".`);
              }
            }
            let cbs = vm._events[event];
            if (cbs) {
              cbs = cbs.length > 1 ? toArray(cbs) : cbs;
              const args = toArray(arguments, 1);
              const info = `event handler for "${event}"`;
              for (let i = 0, l = cbs.length; i < l; i++) {
                invokeWithErrorHandling(cbs[i], vm, args, vm, info);
              }
            }
            return vm;
          };
        }

        /*  */

        var activeInstance = null;
        var isUpdatingChildComponent = false;

        function setActiveInstance(vm) {
          const prevActiveInstance = activeInstance;
          activeInstance = vm;
          return function () {
            activeInstance = prevActiveInstance;
          };
        }

        function initLifecycle(vm) {
          const options = vm.$options;

          // locate first non-abstract parent
          let { parent } = options;
          if (parent && !options.abstract) {
            while (parent.$options.abstract && parent.$parent) {
              parent = parent.$parent;
            }
            parent.$children.push(vm);
          }

          vm.$parent = parent;
          vm.$root = parent ? parent.$root : vm;

          vm.$children = [];
          vm.$refs = {};

          vm._watcher = null;
          vm._inactive = null;
          vm._directInactive = false;
          vm._isMounted = false;
          vm._isDestroyed = false;
          vm._isBeingDestroyed = false;
        }

        function lifecycleMixin(Vue) {
          Vue.prototype._update = function (vnode, hydrating) {
            const vm = this;
            const prevEl = vm.$el;
            const prevVnode = vm._vnode;
            const restoreActiveInstance = setActiveInstance(vm);
            vm._vnode = vnode;
            // Vue.prototype.__patch__ is injected in entry points
            // based on the rendering backend used.
            if (!prevVnode) {
              // initial render
              vm.$el = vm.__patch__(vm.$el, vnode, hydrating, false /* removeOnly */);
            } else {
              // updates
              vm.$el = vm.__patch__(prevVnode, vnode);
            }
            restoreActiveInstance();
            // update __vue__ reference
            if (prevEl) {
              prevEl.__vue__ = null;
            }
            if (vm.$el) {
              vm.$el.__vue__ = vm;
            }
            // if parent is an HOC, update its $el as well
            if (vm.$vnode && vm.$parent && vm.$vnode === vm.$parent._vnode) {
              vm.$parent.$el = vm.$el;
            }
            // updated hook is called by the scheduler to ensure that children are
            // updated in a parent's updated hook.
          };

          Vue.prototype.$forceUpdate = function () {
            const vm = this;
            if (vm._watcher) {
              vm._watcher.update();
            }
          };

          Vue.prototype.$destroy = function () {
            const vm = this;
            if (vm._isBeingDestroyed) {
              return;
            }
            callHook(vm, 'beforeDestroy');
            vm._isBeingDestroyed = true;
            // remove self from parent
            const parent = vm.$parent;
            if (parent && !parent._isBeingDestroyed && !vm.$options.abstract) {
              remove(parent.$children, vm);
            }
            // teardown watchers
            if (vm._watcher) {
              vm._watcher.teardown();
            }
            let i = vm._watchers.length;
            while (i--) {
              vm._watchers[i].teardown();
            }
            // remove reference from data ob
            // frozen object may not have observer.
            if (vm._data.__ob__) {
              vm._data.__ob__.vmCount--;
            }
            // call the last hook...
            vm._isDestroyed = true;
            // invoke destroy hooks on current rendered tree
            vm.__patch__(vm._vnode, null);
            // fire destroyed hook
            callHook(vm, 'destroyed');
            // turn off all instance listeners.
            vm.$off();
            // remove __vue__ reference
            if (vm.$el) {
              vm.$el.__vue__ = null;
            }
            // release circular reference (#6759)
            if (vm.$vnode) {
              vm.$vnode.parent = null;
            }
          };
        }

        function mountComponent(
          vm,
          el,
          hydrating
        ) {
          vm.$el = el;
          if (!vm.$options.render) {
            vm.$options.render = createEmptyVNode;
            if (true) {
              /* istanbul ignore if */
              if ((vm.$options.template && vm.$options.template.charAt(0) !== '#')
        || vm.$options.el || el) {
                warn(
                  'You are using the runtime-only build of Vue where the template '
          + 'compiler is not available. Either pre-compile the templates into '
          + 'render functions, or use the compiler-included build.',
                  vm
                );
              } else {
                warn(
                  'Failed to mount component: template or render function not defined.',
                  vm
                );
              }
            }
          }
          callHook(vm, 'beforeMount');

          let updateComponent;
          /* istanbul ignore if */
          if (true && config.performance && mark) {
            updateComponent = function () {
              const name = vm._name;
              const id = vm._uid;
              const startTag = `vue-perf-start:${id}`;
              const endTag = `vue-perf-end:${id}`;

              mark(startTag);
              const vnode = vm._render();
              mark(endTag);
              measure((`vue ${name} render`), startTag, endTag);

              mark(startTag);
              vm._update(vnode, hydrating);
              mark(endTag);
              measure((`vue ${name} patch`), startTag, endTag);
            };
          } else {
            updateComponent = function () {
              vm._update(vm._render(), hydrating);
            };
          }

          // we set this to vm._watcher inside the watcher's constructor
          // since the watcher's initial patch may call $forceUpdate (e.g. inside child
          // component's mounted hook), which relies on vm._watcher being already defined
          new Watcher(vm, updateComponent, noop, {
            before: function before() {
              if (vm._isMounted && !vm._isDestroyed) {
                callHook(vm, 'beforeUpdate');
              }
            }
          }, true /* isRenderWatcher */);
          hydrating = false;

          // manually mounted instance, call mounted on self
          // mounted is called for render-created child components in its inserted hook
          if (vm.$vnode == null) {
            vm._isMounted = true;
            callHook(vm, 'mounted');
          }
          return vm;
        }

        function updateChildComponent(
          vm,
          propsData,
          listeners,
          parentVnode,
          renderChildren
        ) {
          if (true) {
            isUpdatingChildComponent = true;
          }

          // determine whether component has slot children
          // we need to do this before overwriting $options._renderChildren.

          // check if there are dynamic scopedSlots (hand-written or compiled but with
          // dynamic slot names). Static scoped slots compiled from template has the
          // "$stable" marker.
          const newScopedSlots = parentVnode.data.scopedSlots;
          const oldScopedSlots = vm.$scopedSlots;
          const hasDynamicScopedSlot = !!(
            (newScopedSlots && !newScopedSlots.$stable)
    || (oldScopedSlots !== emptyObject && !oldScopedSlots.$stable)
    || (newScopedSlots && vm.$scopedSlots.$key !== newScopedSlots.$key)
    || (!newScopedSlots && vm.$scopedSlots.$key)
          );

          // Any static slot children from the parent may have changed during parent's
          // update. Dynamic scoped slots may also have changed. In such cases, a forced
          // update is necessary to ensure correctness.
          const needsForceUpdate = !!(
            renderChildren               // has new static slots
    || vm.$options._renderChildren  // has old static slots
    || hasDynamicScopedSlot
          );

          vm.$options._parentVnode = parentVnode;
          vm.$vnode = parentVnode; // update vm's placeholder node without re-render

          if (vm._vnode) { // update child tree's parent
            vm._vnode.parent = parentVnode;
          }
          vm.$options._renderChildren = renderChildren;

          // update $attrs and $listeners hash
          // these are also reactive so they may trigger child update if the child
          // used them during render
          vm.$attrs = parentVnode.data.attrs || emptyObject;
          vm.$listeners = listeners || emptyObject;

          // update props
          if (propsData && vm.$options.props) {
            toggleObserving(false);
            const props = vm._props;
            const propKeys = vm.$options._propKeys || [];
            for (let i = 0; i < propKeys.length; i++) {
              const key = propKeys[i];
              const propOptions = vm.$options.props; // wtf flow?
              props[key] = validateProp(key, propOptions, propsData, vm);
            }
            toggleObserving(true);
            // keep a copy of raw propsData
            vm.$options.propsData = propsData;
          }

          // update listeners
          listeners = listeners || emptyObject;
          const oldListeners = vm.$options._parentListeners;
          vm.$options._parentListeners = listeners;
          updateComponentListeners(vm, listeners, oldListeners);

          // resolve slots + force update if has children
          if (needsForceUpdate) {
            vm.$slots = resolveSlots(renderChildren, parentVnode.context);
            vm.$forceUpdate();
          }

          if (true) {
            isUpdatingChildComponent = false;
          }
        }

        function isInInactiveTree(vm) {
          while (vm && (vm = vm.$parent)) {
            if (vm._inactive) {
              return true;
            }
          }
          return false;
        }

        function activateChildComponent(vm, direct) {
          if (direct) {
            vm._directInactive = false;
            if (isInInactiveTree(vm)) {
              return;
            }
          } else if (vm._directInactive) {
            return;
          }
          if (vm._inactive || vm._inactive === null) {
            vm._inactive = false;
            for (let i = 0; i < vm.$children.length; i++) {
              activateChildComponent(vm.$children[i]);
            }
            callHook(vm, 'activated');
          }
        }

        function deactivateChildComponent(vm, direct) {
          if (direct) {
            vm._directInactive = true;
            if (isInInactiveTree(vm)) {
              return;
            }
          }
          if (!vm._inactive) {
            vm._inactive = true;
            for (let i = 0; i < vm.$children.length; i++) {
              deactivateChildComponent(vm.$children[i]);
            }
            callHook(vm, 'deactivated');
          }
        }

        function callHook(vm, hook) {
          // #7573 disable dep collection when invoking lifecycle hooks
          pushTarget();
          const handlers = vm.$options[hook];
          const info = `${hook} hook`;
          if (handlers) {
            for (let i = 0, j = handlers.length; i < j; i++) {
              invokeWithErrorHandling(handlers[i], vm, null, vm, info);
            }
          }
          if (vm._hasHookEvent) {
            vm.$emit(`hook:${hook}`);
          }
          popTarget();
        }

        /*  */

        const MAX_UPDATE_COUNT = 100;

        const queue = [];
        const activatedChildren = [];
        let has = {};
        let circular = {};
        let waiting = false;
        let flushing = false;
        let index = 0;

        /**
 * Reset the scheduler's state.
 */
        function resetSchedulerState() {
          index = queue.length = activatedChildren.length = 0;
          has = {};
          if (true) {
            circular = {};
          }
          waiting = flushing = false;
        }

        // Async edge case #6566 requires saving the timestamp when event listeners are
        // attached. However, calling performance.now() has a perf overhead especially
        // if the page has thousands of event listeners. Instead, we take a timestamp
        // every time the scheduler flushes and use that for all event listeners
        // attached during that flush.
        let currentFlushTimestamp = 0;

        // Async edge case fix requires storing an event listener's attach timestamp.
        let getNow = Date.now;

        // Determine what event timestamp the browser is using. Annoyingly, the
        // timestamp can either be hi-res (relative to page load) or low-res
        // (relative to UNIX epoch), so in order to compare time we have to use the
        // same timestamp type when saving the flush timestamp.
        // All IE versions use low-res event timestamps, and have problematic clock
        // implementations (#9632)
        if (inBrowser && !isIE) {
          const { performance } = window;
          if (
            performance
    && typeof performance.now === 'function'
    && getNow() > document.createEvent('Event').timeStamp
          ) {
            // if the event timestamp, although evaluated AFTER the Date.now(), is
            // smaller than it, it means the event is using a hi-res timestamp,
            // and we need to use the hi-res version for event listener timestamps as
            // well.
            getNow = function () {
              return performance.now();
            };
          }
        }

        /**
 * Flush both queues and run the watchers.
 */
        function flushSchedulerQueue() {
          currentFlushTimestamp = getNow();
          flushing = true;
          let watcher; let id;

          // Sort queue before flush.
          // This ensures that:
          // 1. Components are updated from parent to child. (because parent is always
          //    created before the child)
          // 2. A component's user watchers are run before its render watcher (because
          //    user watchers are created before the render watcher)
          // 3. If a component is destroyed during a parent component's watcher run,
          //    its watchers can be skipped.
          queue.sort((a, b) => a.id - b.id);

          // do not cache length because more watchers might be pushed
          // as we run existing watchers
          for (index = 0; index < queue.length; index++) {
            watcher = queue[index];
            if (watcher.before) {
              watcher.before();
            }
            id = watcher.id;
            has[id] = null;
            watcher.run();
            // in dev build, check and stop circular updates.
            if (true && has[id] != null) {
              circular[id] = (circular[id] || 0) + 1;
              if (circular[id] > MAX_UPDATE_COUNT) {
                warn(
                  `You may have an infinite update loop ${
                    watcher.user
                      ? (`in watcher with expression "${watcher.expression}"`)
                      : 'in a component render function.'}`,
                  watcher.vm
                );
                break;
              }
            }
          }

          // keep copies of post queues before resetting state
          const activatedQueue = activatedChildren.slice();
          const updatedQueue = queue.slice();

          resetSchedulerState();

          // call component updated and activated hooks
          callActivatedHooks(activatedQueue);
          callUpdatedHooks(updatedQueue);

          // devtool hook
          /* istanbul ignore if */
          if (devtools && config.devtools) {
            devtools.emit('flush');
          }
        }

        function callUpdatedHooks(queue) {
          let i = queue.length;
          while (i--) {
            const watcher = queue[i];
            const { vm } = watcher;
            if (vm._watcher === watcher && vm._isMounted && !vm._isDestroyed) {
              callHook(vm, 'updated');
            }
          }
        }

        /**
 * Queue a kept-alive component that was activated during patch.
 * The queue will be processed after the entire tree has been patched.
 */
        function queueActivatedComponent(vm) {
          // setting _inactive to false here so that a render function can
          // rely on checking whether it's in an inactive tree (e.g. router-view)
          vm._inactive = false;
          activatedChildren.push(vm);
        }

        function callActivatedHooks(queue) {
          for (let i = 0; i < queue.length; i++) {
            queue[i]._inactive = true;
            activateChildComponent(queue[i], true /* true */);
          }
        }

        /**
 * Push a watcher into the watcher queue.
 * Jobs with duplicate IDs will be skipped unless it's
 * pushed when the queue is being flushed.
 */
        function queueWatcher(watcher) {
          const { id } = watcher;
          if (has[id] == null) {
            has[id] = true;
            if (!flushing) {
              queue.push(watcher);
            } else {
              // if already flushing, splice the watcher based on its id
              // if already past its id, it will be run next immediately.
              let i = queue.length - 1;
              while (i > index && queue[i].id > watcher.id) {
                i--;
              }
              queue.splice(i + 1, 0, watcher);
            }
            // queue the flush
            if (!waiting) {
              waiting = true;

              if (true && !config.async) {
                flushSchedulerQueue();
                return;
              }
              nextTick(flushSchedulerQueue);
            }
          }
        }

        /*  */


        let uid$2 = 0;

        /**
 * A watcher parses an expression, collects dependencies,
 * and fires callback when the expression value changes.
 * This is used for both the $watch() api and directives.
 */
        var Watcher = function Watcher(
          vm,
          expOrFn,
          cb,
          options,
          isRenderWatcher
        ) {
          this.vm = vm;
          if (isRenderWatcher) {
            vm._watcher = this;
          }
          vm._watchers.push(this);
          // options
          if (options) {
            this.deep = !!options.deep;
            this.user = !!options.user;
            this.lazy = !!options.lazy;
            this.sync = !!options.sync;
            this.before = options.before;
          } else {
            this.deep = this.user = this.lazy = this.sync = false;
          }
          this.cb = cb;
          this.id = ++uid$2; // uid for batching
          this.active = true;
          this.dirty = this.lazy; // for lazy watchers
          this.deps = [];
          this.newDeps = [];
          this.depIds = new _Set();
          this.newDepIds = new _Set();
          this.expression =  true
            ? expOrFn.toString()
            : 0;
          // parse expression for getter
          if (typeof expOrFn === 'function') {
            this.getter = expOrFn;
          } else {
            this.getter = parsePath(expOrFn);
            if (!this.getter) {
              this.getter = noop;
              true && warn(
                `Failed watching path: "${expOrFn}" `
        + 'Watcher only accepts simple dot-delimited paths. '
        + 'For full control, use a function instead.',
                vm
              );
            }
          }
          this.value = this.lazy
            ? undefined
            : this.get();
        };

        /**
 * Evaluate the getter, and re-collect dependencies.
 */
        Watcher.prototype.get = function get() {
          pushTarget(this);
          let value;
          const { vm } = this;
          try {
            value = this.getter.call(vm, vm);
          } catch (e) {
            if (this.user) {
              handleError(e, vm, (`getter for watcher "${this.expression}"`));
            } else {
              throw e;
            }
          } finally {
            // "touch" every property so they are all tracked as
            // dependencies for deep watching
            if (this.deep) {
              traverse(value);
            }
            popTarget();
            this.cleanupDeps();
          }
          return value;
        };

        /**
 * Add a dependency to this directive.
 */
        Watcher.prototype.addDep = function addDep(dep) {
          const { id } = dep;
          if (!this.newDepIds.has(id)) {
            this.newDepIds.add(id);
            this.newDeps.push(dep);
            if (!this.depIds.has(id)) {
              dep.addSub(this);
            }
          }
        };

        /**
 * Clean up for dependency collection.
 */
        Watcher.prototype.cleanupDeps = function cleanupDeps() {
          let i = this.deps.length;
          while (i--) {
            const dep = this.deps[i];
            if (!this.newDepIds.has(dep.id)) {
              dep.removeSub(this);
            }
          }
          let tmp = this.depIds;
          this.depIds = this.newDepIds;
          this.newDepIds = tmp;
          this.newDepIds.clear();
          tmp = this.deps;
          this.deps = this.newDeps;
          this.newDeps = tmp;
          this.newDeps.length = 0;
        };

        /**
 * Subscriber interface.
 * Will be called when a dependency changes.
 */
        Watcher.prototype.update = function update() {
          /* istanbul ignore else */
          if (this.lazy) {
            this.dirty = true;
          } else if (this.sync) {
            this.run();
          } else {
            queueWatcher(this);
          }
        };

        /**
 * Scheduler job interface.
 * Will be called by the scheduler.
 */
        Watcher.prototype.run = function run() {
          if (this.active) {
            const value = this.get();
            if (
              value !== this.value
      // Deep watchers and watchers on Object/Arrays should fire even
      // when the value is the same, because the value may
      // have mutated.
      || isObject(value)
      || this.deep
            ) {
              // set new value
              const oldValue = this.value;
              this.value = value;
              if (this.user) {
                const info = `callback for watcher "${this.expression}"`;
                invokeWithErrorHandling(this.cb, this.vm, [value, oldValue], this.vm, info);
              } else {
                this.cb.call(this.vm, value, oldValue);
              }
            }
          }
        };

        /**
 * Evaluate the value of the watcher.
 * This only gets called for lazy watchers.
 */
        Watcher.prototype.evaluate = function evaluate() {
          this.value = this.get();
          this.dirty = false;
        };

        /**
 * Depend on all deps collected by this watcher.
 */
        Watcher.prototype.depend = function depend() {
          let i = this.deps.length;
          while (i--) {
            this.deps[i].depend();
          }
        };

        /**
 * Remove self from all dependencies' subscriber list.
 */
        Watcher.prototype.teardown = function teardown() {
          if (this.active) {
            // remove self from vm's watcher list
            // this is a somewhat expensive operation so we skip it
            // if the vm is being destroyed.
            if (!this.vm._isBeingDestroyed) {
              remove(this.vm._watchers, this);
            }
            let i = this.deps.length;
            while (i--) {
              this.deps[i].removeSub(this);
            }
            this.active = false;
          }
        };

        /*  */

        const sharedPropertyDefinition = {
          enumerable: true,
          configurable: true,
          get: noop,
          set: noop
        };

        function proxy(target, sourceKey, key) {
          sharedPropertyDefinition.get = function proxyGetter() {
            return this[sourceKey][key];
          };
          sharedPropertyDefinition.set = function proxySetter(val) {
            this[sourceKey][key] = val;
          };
          Object.defineProperty(target, key, sharedPropertyDefinition);
        }

        function initState(vm) {
          vm._watchers = [];
          const opts = vm.$options;
          if (opts.props) {
            initProps(vm, opts.props);
          }
          if (opts.methods) {
            initMethods(vm, opts.methods);
          }
          if (opts.data) {
            initData(vm);
          } else {
            observe(vm._data = {}, true /* asRootData */);
          }
          if (opts.computed) {
            initComputed(vm, opts.computed);
          }
          if (opts.watch && opts.watch !== nativeWatch) {
            initWatch(vm, opts.watch);
          }
        }

        function initProps(vm, propsOptions) {
          const propsData = vm.$options.propsData || {};
          const props = vm._props = {};
          // cache prop keys so that future props updates can iterate using Array
          // instead of dynamic object key enumeration.
          const keys = vm.$options._propKeys = [];
          const isRoot = !vm.$parent;
          // root instance props should be converted
          if (!isRoot) {
            toggleObserving(false);
          }
          const loop = function (key) {
            keys.push(key);
            const value = validateProp(key, propsOptions, propsData, vm);
            /* istanbul ignore else */
            if (true) {
              const hyphenatedKey = hyphenate(key);
              if (isReservedAttribute(hyphenatedKey)
          || config.isReservedAttr(hyphenatedKey)) {
                warn(
                  (`"${hyphenatedKey}" is a reserved attribute and cannot be used as component prop.`),
                  vm
                );
              }
              defineReactive$$1(props, key, value, () => {
                if (!isRoot && !isUpdatingChildComponent) {
                  warn(
                    'Avoid mutating a prop directly since the value will be '
            + 'overwritten whenever the parent component re-renders. '
            + 'Instead, use a data or computed property based on the prop\'s '
            + `value. Prop being mutated: "${key}"`,
                    vm
                  );
                }
              });
            } else {}
            // static props are already proxied on the component's prototype
            // during Vue.extend(). We only need to proxy props defined at
            // instantiation here.
            if (!(key in vm)) {
              proxy(vm, '_props', key);
            }
          };

          for (const key in propsOptions) loop(key);
          toggleObserving(true);
        }

        function initData(vm) {
          let { data } = vm.$options;
          data = vm._data = typeof data === 'function'
            ? getData(data, vm)
            : data || {};
          if (!isPlainObject(data)) {
            data = {};
            true && warn(
              'data functions should return an object:\n'
      + 'https://vuejs.org/v2/guide/components.html#data-Must-Be-a-Function',
              vm
            );
          }
          // proxy data on instance
          const keys = Object.keys(data);
          const { props } = vm.$options;
          const { methods } = vm.$options;
          let i = keys.length;
          while (i--) {
            const key = keys[i];
            if (true) {
              if (methods && hasOwn(methods, key)) {
                warn(
                  (`Method "${key}" has already been defined as a data property.`),
                  vm
                );
              }
            }
            if (props && hasOwn(props, key)) {
              true && warn(
                `The data property "${key}" is already declared as a prop. `
        + 'Use prop default value instead.',
                vm
              );
            } else if (!isReserved(key)) {
              proxy(vm, '_data', key);
            }
          }
          // observe data
          observe(data, true /* asRootData */);
        }

        function getData(data, vm) {
          // #7573 disable dep collection when invoking data getters
          pushTarget();
          try {
            return data.call(vm, vm);
          } catch (e) {
            handleError(e, vm, 'data()');
            return {};
          } finally {
            popTarget();
          }
        }

        const computedWatcherOptions = { lazy: true };

        function initComputed(vm, computed) {
          // $flow-disable-line
          const watchers = vm._computedWatchers = Object.create(null);
          // computed properties are just getters during SSR
          const isSSR = isServerRendering();

          for (const key in computed) {
            const userDef = computed[key];
            const getter = typeof userDef === 'function' ? userDef : userDef.get;
            if (true && getter == null) {
              warn(
                (`Getter is missing for computed property "${key}".`),
                vm
              );
            }

            if (!isSSR) {
              // create internal watcher for the computed property.
              watchers[key] = new Watcher(
                vm,
                getter || noop,
                noop,
                computedWatcherOptions
              );
            }

            // component-defined computed properties are already defined on the
            // component prototype. We only need to define computed properties defined
            // at instantiation here.
            if (!(key in vm)) {
              defineComputed(vm, key, userDef);
            } else if (true) {
              if (key in vm.$data) {
                warn((`The computed property "${key}" is already defined in data.`), vm);
              } else if (vm.$options.props && key in vm.$options.props) {
                warn((`The computed property "${key}" is already defined as a prop.`), vm);
              } else if (vm.$options.methods && key in vm.$options.methods) {
                warn((`The computed property "${key}" is already defined as a method.`), vm);
              }
            }
          }
        }

        function defineComputed(
          target,
          key,
          userDef
        ) {
          const shouldCache = !isServerRendering();
          if (typeof userDef === 'function') {
            sharedPropertyDefinition.get = shouldCache
              ? createComputedGetter(key)
              : createGetterInvoker(userDef);
            sharedPropertyDefinition.set = noop;
          } else {
            sharedPropertyDefinition.get = userDef.get
              ? shouldCache && userDef.cache !== false
                ? createComputedGetter(key)
                : createGetterInvoker(userDef.get)
              : noop;
            sharedPropertyDefinition.set = userDef.set || noop;
          }
          if (true
      && sharedPropertyDefinition.set === noop) {
            sharedPropertyDefinition.set = function () {
              warn(
                (`Computed property "${key}" was assigned to but it has no setter.`),
                this
              );
            };
          }
          Object.defineProperty(target, key, sharedPropertyDefinition);
        }

        function createComputedGetter(key) {
          return function computedGetter() {
            const watcher = this._computedWatchers && this._computedWatchers[key];
            if (watcher) {
              if (watcher.dirty) {
                watcher.evaluate();
              }
              if (Dep.target) {
                watcher.depend();
              }
              return watcher.value;
            }
          };
        }

        function createGetterInvoker(fn) {
          return function computedGetter() {
            return fn.call(this, this);
          };
        }

        function initMethods(vm, methods) {
          const { props } = vm.$options;
          for (const key in methods) {
            if (true) {
              if (typeof methods[key] !== 'function') {
                warn(
                  `Method "${key}" has type "${typeof methods[key]}" in the component definition. `
          + 'Did you reference the function correctly?',
                  vm
                );
              }
              if (props && hasOwn(props, key)) {
                warn(
                  (`Method "${key}" has already been defined as a prop.`),
                  vm
                );
              }
              if ((key in vm) && isReserved(key)) {
                warn(`Method "${key}" conflicts with an existing Vue instance method. `
          + 'Avoid defining component methods that start with _ or $.');
              }
            }
            vm[key] = typeof methods[key] !== 'function' ? noop : bind(methods[key], vm);
          }
        }

        function initWatch(vm, watch) {
          for (const key in watch) {
            const handler = watch[key];
            if (Array.isArray(handler)) {
              for (let i = 0; i < handler.length; i++) {
                createWatcher(vm, key, handler[i]);
              }
            } else {
              createWatcher(vm, key, handler);
            }
          }
        }

        function createWatcher(
          vm,
          expOrFn,
          handler,
          options
        ) {
          if (isPlainObject(handler)) {
            options = handler;
            handler = handler.handler;
          }
          if (typeof handler === 'string') {
            handler = vm[handler];
          }
          return vm.$watch(expOrFn, handler, options);
        }

        function stateMixin(Vue) {
          // flow somehow has problems with directly declared definition object
          // when using Object.defineProperty, so we have to procedurally build up
          // the object here.
          const dataDef = {};
          dataDef.get = function () {
            return this._data;
          };
          const propsDef = {};
          propsDef.get = function () {
            return this._props;
          };
          if (true) {
            dataDef.set = function () {
              warn(
                'Avoid replacing instance root $data. '
        + 'Use nested data properties instead.',
                this
              );
            };
            propsDef.set = function () {
              warn('$props is readonly.', this);
            };
          }
          Object.defineProperty(Vue.prototype, '$data', dataDef);
          Object.defineProperty(Vue.prototype, '$props', propsDef);

          Vue.prototype.$set = set;
          Vue.prototype.$delete = del;

          Vue.prototype.$watch = function (
            expOrFn,
            cb,
            options
          ) {
            const vm = this;
            if (isPlainObject(cb)) {
              return createWatcher(vm, expOrFn, cb, options);
            }
            options = options || {};
            options.user = true;
            const watcher = new Watcher(vm, expOrFn, cb, options);
            if (options.immediate) {
              const info = `callback for immediate watcher "${watcher.expression}"`;
              pushTarget();
              invokeWithErrorHandling(cb, vm, [watcher.value], vm, info);
              popTarget();
            }
            return function unwatchFn() {
              watcher.teardown();
            };
          };
        }

        /*  */

        let uid$3 = 0;

        function initMixin(Vue) {
          Vue.prototype._init = function (options) {
            const vm = this;
            // a uid
            vm._uid = uid$3++;

            let startTag; let endTag;
            /* istanbul ignore if */
            if (true && config.performance && mark) {
              startTag = `vue-perf-start:${vm._uid}`;
              endTag = `vue-perf-end:${vm._uid}`;
              mark(startTag);
            }

            // a flag to avoid this being observed
            vm._isVue = true;
            // merge options
            if (options && options._isComponent) {
              // optimize internal component instantiation
              // since dynamic options merging is pretty slow, and none of the
              // internal component options needs special treatment.
              initInternalComponent(vm, options);
            } else {
              vm.$options = mergeOptions(
                resolveConstructorOptions(vm.constructor),
                options || {},
                vm
              );
            }
            /* istanbul ignore else */
            if (true) {
              initProxy(vm);
            } else {}
            // expose real self
            vm._self = vm;
            initLifecycle(vm);
            initEvents(vm);
            initRender(vm);
            callHook(vm, 'beforeCreate');
            initInjections(vm); // resolve injections before data/props
            initState(vm);
            initProvide(vm); // resolve provide after data/props
            callHook(vm, 'created');

            /* istanbul ignore if */
            if (true && config.performance && mark) {
              vm._name = formatComponentName(vm, false);
              mark(endTag);
              measure((`vue ${vm._name} init`), startTag, endTag);
            }

            if (vm.$options.el) {
              vm.$mount(vm.$options.el);
            }
          };
        }

        function initInternalComponent(vm, options) {
          const opts = vm.$options = Object.create(vm.constructor.options);
          // doing this because it's faster than dynamic enumeration.
          const parentVnode = options._parentVnode;
          opts.parent = options.parent;
          opts._parentVnode = parentVnode;

          const vnodeComponentOptions = parentVnode.componentOptions;
          opts.propsData = vnodeComponentOptions.propsData;
          opts._parentListeners = vnodeComponentOptions.listeners;
          opts._renderChildren = vnodeComponentOptions.children;
          opts._componentTag = vnodeComponentOptions.tag;

          if (options.render) {
            opts.render = options.render;
            opts.staticRenderFns = options.staticRenderFns;
          }
        }

        function resolveConstructorOptions(Ctor) {
          let { options } = Ctor;
          if (Ctor.super) {
            const superOptions = resolveConstructorOptions(Ctor.super);
            const cachedSuperOptions = Ctor.superOptions;
            if (superOptions !== cachedSuperOptions) {
              // super option changed,
              // need to resolve new options.
              Ctor.superOptions = superOptions;
              // check if there are any late-modified/attached options (#4976)
              const modifiedOptions = resolveModifiedOptions(Ctor);
              // update base extend options
              if (modifiedOptions) {
                extend(Ctor.extendOptions, modifiedOptions);
              }
              options = Ctor.options = mergeOptions(superOptions, Ctor.extendOptions);
              if (options.name) {
                options.components[options.name] = Ctor;
              }
            }
          }
          return options;
        }

        function resolveModifiedOptions(Ctor) {
          let modified;
          const latest = Ctor.options;
          const sealed = Ctor.sealedOptions;
          for (const key in latest) {
            if (latest[key] !== sealed[key]) {
              if (!modified) {
                modified = {};
              }
              modified[key] = latest[key];
            }
          }
          return modified;
        }

        function Vue(options) {
          if (true
    && !(this instanceof Vue)
          ) {
            warn('Vue is a constructor and should be called with the `new` keyword');
          }
          this._init(options);
        }

        initMixin(Vue);
        stateMixin(Vue);
        eventsMixin(Vue);
        lifecycleMixin(Vue);
        renderMixin(Vue);

        /*  */

        function initUse(Vue) {
          Vue.use = function (plugin) {
            const installedPlugins = (this._installedPlugins || (this._installedPlugins = []));
            if (installedPlugins.indexOf(plugin) > -1) {
              return this;
            }

            // additional parameters
            const args = toArray(arguments, 1);
            args.unshift(this);
            if (typeof plugin.install === 'function') {
              plugin.install.apply(plugin, args);
            } else if (typeof plugin === 'function') {
              plugin.apply(null, args);
            }
            installedPlugins.push(plugin);
            return this;
          };
        }

        /*  */

        function initMixin$1(Vue) {
          Vue.mixin = function (mixin) {
            this.options = mergeOptions(this.options, mixin);
            return this;
          };
        }

        /*  */

        function initExtend(Vue) {
          /**
   * Each instance constructor, including Vue, has a unique
   * cid. This enables us to create wrapped "child
   * constructors" for prototypal inheritance and cache them.
   */
          Vue.cid = 0;
          let cid = 1;

          /**
   * Class inheritance
   */
          Vue.extend = function (extendOptions) {
            extendOptions = extendOptions || {};
            const Super = this;
            const SuperId = Super.cid;
            const cachedCtors = extendOptions._Ctor || (extendOptions._Ctor = {});
            if (cachedCtors[SuperId]) {
              return cachedCtors[SuperId];
            }

            const name = extendOptions.name || Super.options.name;
            if (true && name) {
              validateComponentName(name);
            }

            const Sub = function VueComponent(options) {
              this._init(options);
            };
            Sub.prototype = Object.create(Super.prototype);
            Sub.prototype.constructor = Sub;
            Sub.cid = cid++;
            Sub.options = mergeOptions(
              Super.options,
              extendOptions
            );
            Sub.super = Super;

            // For props and computed properties, we define the proxy getters on
            // the Vue instances at extension time, on the extended prototype. This
            // avoids Object.defineProperty calls for each instance created.
            if (Sub.options.props) {
              initProps$1(Sub);
            }
            if (Sub.options.computed) {
              initComputed$1(Sub);
            }

            // allow further extension/mixin/plugin usage
            Sub.extend = Super.extend;
            Sub.mixin = Super.mixin;
            Sub.use = Super.use;

            // create asset registers, so extended classes
            // can have their private assets too.
            ASSET_TYPES.forEach((type) => {
              Sub[type] = Super[type];
            });
            // enable recursive self-lookup
            if (name) {
              Sub.options.components[name] = Sub;
            }

            // keep a reference to the super options at extension time.
            // later at instantiation we can check if Super's options have
            // been updated.
            Sub.superOptions = Super.options;
            Sub.extendOptions = extendOptions;
            Sub.sealedOptions = extend({}, Sub.options);

            // cache constructor
            cachedCtors[SuperId] = Sub;
            return Sub;
          };
        }

        function initProps$1(Comp) {
          const { props } = Comp.options;
          for (const key in props) {
            proxy(Comp.prototype, '_props', key);
          }
        }

        function initComputed$1(Comp) {
          const { computed } = Comp.options;
          for (const key in computed) {
            defineComputed(Comp.prototype, key, computed[key]);
          }
        }

        /*  */

        function initAssetRegisters(Vue) {
          /**
   * Create asset registration methods.
   */
          ASSET_TYPES.forEach((type) => {
            Vue[type] = function (
              id,
              definition
            ) {
              if (!definition) {
                return this.options[`${type}s`][id];
              }
              /* istanbul ignore if */
              if (true && type === 'component') {
                validateComponentName(id);
              }
              if (type === 'component' && isPlainObject(definition)) {
                definition.name = definition.name || id;
                definition = this.options._base.extend(definition);
              }
              if (type === 'directive' && typeof definition === 'function') {
                definition = { bind: definition, update: definition };
              }
              this.options[`${type}s`][id] = definition;
              return definition;
            };
          });
        }

        /*  */


        function getComponentName(opts) {
          return opts && (opts.Ctor.options.name || opts.tag);
        }

        function matches(pattern, name) {
          if (Array.isArray(pattern)) {
            return pattern.indexOf(name) > -1;
          } if (typeof pattern === 'string') {
            return pattern.split(',').indexOf(name) > -1;
          } if (isRegExp(pattern)) {
            return pattern.test(name);
          }
          /* istanbul ignore next */
          return false;
        }

        function pruneCache(keepAliveInstance, filter) {
          const { cache } = keepAliveInstance;
          const { keys } = keepAliveInstance;
          const { _vnode } = keepAliveInstance;
          for (const key in cache) {
            const entry = cache[key];
            if (entry) {
              const { name } = entry;
              if (name && !filter(name)) {
                pruneCacheEntry(cache, key, keys, _vnode);
              }
            }
          }
        }

        function pruneCacheEntry(
          cache,
          key,
          keys,
          current
        ) {
          const entry = cache[key];
          if (entry && (!current || entry.tag !== current.tag)) {
            entry.componentInstance.$destroy();
          }
          cache[key] = null;
          remove(keys, key);
        }

        const patternTypes = [String, RegExp, Array];

        const KeepAlive = {
          name: 'keep-alive',
          abstract: true,

          props: {
            include: patternTypes,
            exclude: patternTypes,
            max: [String, Number]
          },

          methods: {
            cacheVNode: function cacheVNode() {
              const ref = this;
              const { cache } = ref;
              const { keys } = ref;
              const { vnodeToCache } = ref;
              const { keyToCache } = ref;
              if (vnodeToCache) {
                const { tag } = vnodeToCache;
                const { componentInstance } = vnodeToCache;
                const { componentOptions } = vnodeToCache;
                cache[keyToCache] = {
                  name: getComponentName(componentOptions),
                  tag,
                  componentInstance,
                };
                keys.push(keyToCache);
                // prune oldest entry
                if (this.max && keys.length > parseInt(this.max)) {
                  pruneCacheEntry(cache, keys[0], keys, this._vnode);
                }
                this.vnodeToCache = null;
              }
            }
          },

          created: function created() {
            this.cache = Object.create(null);
            this.keys = [];
          },

          destroyed: function destroyed() {
            for (const key in this.cache) {
              pruneCacheEntry(this.cache, key, this.keys);
            }
          },

          mounted: function mounted() {
            const this$1 = this;

            this.cacheVNode();
            this.$watch('include', (val) => {
              pruneCache(this$1, name => matches(val, name));
            });
            this.$watch('exclude', (val) => {
              pruneCache(this$1, name => !matches(val, name));
            });
          },

          updated: function updated() {
            this.cacheVNode();
          },

          render: function render() {
            const slot = this.$slots.default;
            const vnode = getFirstComponentChild(slot);
            const componentOptions = vnode && vnode.componentOptions;
            if (componentOptions) {
              // check pattern
              const name = getComponentName(componentOptions);
              const ref = this;
              const { include } = ref;
              const { exclude } = ref;
              if (
              // not included
                (include && (!name || !matches(include, name)))
        // excluded
        || (exclude && name && matches(exclude, name))
              ) {
                return vnode;
              }

              const ref$1 = this;
              const { cache } = ref$1;
              const { keys } = ref$1;
              const key = vnode.key == null
              // same constructor may get registered as different local components
              // so cid alone is not enough (#3269)
                ? componentOptions.Ctor.cid + (componentOptions.tag ? (`::${componentOptions.tag}`) : '')
                : vnode.key;
              if (cache[key]) {
                vnode.componentInstance = cache[key].componentInstance;
                // make current key freshest
                remove(keys, key);
                keys.push(key);
              } else {
                // delay setting the cache until update
                this.vnodeToCache = vnode;
                this.keyToCache = key;
              }

              vnode.data.keepAlive = true;
            }
            return vnode || (slot && slot[0]);
          }
        };

        const builtInComponents = {
          KeepAlive
        };

        /*  */

        function initGlobalAPI(Vue) {
          // config
          const configDef = {};
          configDef.get = function () {
            return config;
          };
          if (true) {
            configDef.set = function () {
              warn('Do not replace the Vue.config object, set individual fields instead.');
            };
          }
          Object.defineProperty(Vue, 'config', configDef);

          // exposed util methods.
          // NOTE: these are not considered part of the public API - avoid relying on
          // them unless you are aware of the risk.
          Vue.util = {
            warn,
            extend,
            mergeOptions,
            defineReactive: defineReactive$$1
          };

          Vue.set = set;
          Vue.delete = del;
          Vue.nextTick = nextTick;

          // 2.6 explicit observable API
          Vue.observable = function (obj) {
            observe(obj);
            return obj;
          };

          Vue.options = Object.create(null);
          ASSET_TYPES.forEach((type) => {
            Vue.options[`${type}s`] = Object.create(null);
          });

          // this is used to identify the "base" constructor to extend all plain-object
          // components with in Weex's multi-instance scenarios.
          Vue.options._base = Vue;

          extend(Vue.options.components, builtInComponents);

          initUse(Vue);
          initMixin$1(Vue);
          initExtend(Vue);
          initAssetRegisters(Vue);
        }

        initGlobalAPI(Vue);

        Object.defineProperty(Vue.prototype, '$isServer', {
          get: isServerRendering
        });

        Object.defineProperty(Vue.prototype, '$ssrContext', {
          get: function get() {
            /* istanbul ignore next */
            return this.$vnode && this.$vnode.ssrContext;
          }
        });

        // expose FunctionalRenderContext for ssr runtime helper installation
        Object.defineProperty(Vue, 'FunctionalRenderContext', {
          value: FunctionalRenderContext
        });

        Vue.version = '2.6.14';

        /*  */

        // these are reserved for web because they are directly compiled away
        // during template compilation
        const isReservedAttr = makeMap('style,class');

        // attributes that should be using props for binding
        const acceptValue = makeMap('input,textarea,option,select,progress');
        const mustUseProp = function (tag, type, attr) {
          return (
            (attr === 'value' && acceptValue(tag)) && type !== 'button'
    || (attr === 'selected' && tag === 'option')
    || (attr === 'checked' && tag === 'input')
    || (attr === 'muted' && tag === 'video')
          );
        };

        const isEnumeratedAttr = makeMap('contenteditable,draggable,spellcheck');

        const isValidContentEditableValue = makeMap('events,caret,typing,plaintext-only');

        const convertEnumeratedValue = function (key, value) {
          return isFalsyAttrValue(value) || value === 'false'
            ? 'false'
          // allow arbitrary string value for contenteditable
            : key === 'contenteditable' && isValidContentEditableValue(value)
              ? value
              : 'true';
        };

        const isBooleanAttr = makeMap('allowfullscreen,async,autofocus,autoplay,checked,compact,controls,declare,'
  + 'default,defaultchecked,defaultmuted,defaultselected,defer,disabled,'
  + 'enabled,formnovalidate,hidden,indeterminate,inert,ismap,itemscope,loop,multiple,'
  + 'muted,nohref,noresize,noshade,novalidate,nowrap,open,pauseonexit,readonly,'
  + 'required,reversed,scoped,seamless,selected,sortable,'
  + 'truespeed,typemustmatch,visible');

        const xlinkNS = 'http://www.w3.org/1999/xlink';

        const isXlink = function (name) {
          return name.charAt(5) === ':' && name.slice(0, 5) === 'xlink';
        };

        const getXlinkProp = function (name) {
          return isXlink(name) ? name.slice(6, name.length) : '';
        };

        var isFalsyAttrValue = function (val) {
          return val == null || val === false;
        };

        /*  */

        function genClassForVnode(vnode) {
          let { data } = vnode;
          let parentNode = vnode;
          let childNode = vnode;
          while (isDef(childNode.componentInstance)) {
            childNode = childNode.componentInstance._vnode;
            if (childNode && childNode.data) {
              data = mergeClassData(childNode.data, data);
            }
          }
          while (isDef(parentNode = parentNode.parent)) {
            if (parentNode && parentNode.data) {
              data = mergeClassData(data, parentNode.data);
            }
          }
          return renderClass(data.staticClass, data.class);
        }

        function mergeClassData(child, parent) {
          return {
            staticClass: concat(child.staticClass, parent.staticClass),
            class: isDef(child.class)
              ? [child.class, parent.class]
              : parent.class
          };
        }

        function renderClass(
          staticClass,
          dynamicClass
        ) {
          if (isDef(staticClass) || isDef(dynamicClass)) {
            return concat(staticClass, stringifyClass(dynamicClass));
          }
          /* istanbul ignore next */
          return '';
        }

        function concat(a, b) {
          return a ? b ? (`${a} ${b}`) : a : (b || '');
        }

        function stringifyClass(value) {
          if (Array.isArray(value)) {
            return stringifyArray(value);
          }
          if (isObject(value)) {
            return stringifyObject(value);
          }
          if (typeof value === 'string') {
            return value;
          }
          /* istanbul ignore next */
          return '';
        }

        function stringifyArray(value) {
          let res = '';
          let stringified;
          for (let i = 0, l = value.length; i < l; i++) {
            if (isDef(stringified = stringifyClass(value[i])) && stringified !== '') {
              if (res) {
                res += ' ';
              }
              res += stringified;
            }
          }
          return res;
        }

        function stringifyObject(value) {
          let res = '';
          for (const key in value) {
            if (value[key]) {
              if (res) {
                res += ' ';
              }
              res += key;
            }
          }
          return res;
        }

        /*  */

        const namespaceMap = {
          svg: 'http://www.w3.org/2000/svg',
          math: 'http://www.w3.org/1998/Math/MathML'
        };

        const isHTMLTag = makeMap('html,body,base,head,link,meta,style,title,'
  + 'address,article,aside,footer,header,h1,h2,h3,h4,h5,h6,hgroup,nav,section,'
  + 'div,dd,dl,dt,figcaption,figure,picture,hr,img,li,main,ol,p,pre,ul,'
  + 'a,b,abbr,bdi,bdo,br,cite,code,data,dfn,em,i,kbd,mark,q,rp,rt,rtc,ruby,'
  + 's,samp,small,span,strong,sub,sup,time,u,var,wbr,area,audio,map,track,video,'
  + 'embed,object,param,source,canvas,script,noscript,del,ins,'
  + 'caption,col,colgroup,table,thead,tbody,td,th,tr,'
  + 'button,datalist,fieldset,form,input,label,legend,meter,optgroup,option,'
  + 'output,progress,select,textarea,'
  + 'details,dialog,menu,menuitem,summary,'
  + 'content,element,shadow,template,blockquote,iframe,tfoot');

        // this map is intentionally selective, only covering SVG elements that may
        // contain child elements.
        const isSVG = makeMap(
          'svg,animate,circle,clippath,cursor,defs,desc,ellipse,filter,font-face,'
  + 'foreignobject,g,glyph,image,line,marker,mask,missing-glyph,path,pattern,'
  + 'polygon,polyline,rect,switch,symbol,text,textpath,tspan,use,view',
          true
        );

        const isReservedTag = function (tag) {
          return isHTMLTag(tag) || isSVG(tag);
        };

        function getTagNamespace(tag) {
          if (isSVG(tag)) {
            return 'svg';
          }
          // basic support for MathML
          // note it doesn't support other MathML elements being component roots
          if (tag === 'math') {
            return 'math';
          }
        }

        const unknownElementCache = Object.create(null);
        function isUnknownElement(tag) {
          /* istanbul ignore if */
          if (!inBrowser) {
            return true;
          }
          if (isReservedTag(tag)) {
            return false;
          }
          tag = tag.toLowerCase();
          /* istanbul ignore if */
          if (unknownElementCache[tag] != null) {
            return unknownElementCache[tag];
          }
          const el = document.createElement(tag);
          if (tag.indexOf('-') > -1) {
            // http://stackoverflow.com/a/28210364/1070244
            return (unknownElementCache[tag] = (
              el.constructor === window.HTMLUnknownElement
      || el.constructor === window.HTMLElement
            ));
          }
          return (unknownElementCache[tag] = /HTMLUnknownElement/.test(el.toString()));
        }

        const isTextInputType = makeMap('text,number,password,search,email,tel,url');

        /*  */

        /**
 * Query an element selector if it's not an element already.
 */
        function query(el) {
          if (typeof el === 'string') {
            const selected = document.querySelector(el);
            if (!selected) {
              true && warn(`Cannot find element: ${el}`);
              return document.createElement('div');
            }
            return selected;
          }
          return el;
        }

        /*  */

        function createElement$1(tagName, vnode) {
          const elm = document.createElement(tagName);
          if (tagName !== 'select') {
            return elm;
          }
          // false or null will remove the attribute but undefined will not
          if (vnode.data && vnode.data.attrs && vnode.data.attrs.multiple !== undefined) {
            elm.setAttribute('multiple', 'multiple');
          }
          return elm;
        }

        function createElementNS(namespace, tagName) {
          return document.createElementNS(namespaceMap[namespace], tagName);
        }

        function createTextNode(text) {
          return document.createTextNode(text);
        }

        function createComment(text) {
          return document.createComment(text);
        }

        function insertBefore(parentNode, newNode, referenceNode) {
          parentNode.insertBefore(newNode, referenceNode);
        }

        function removeChild(node, child) {
          node.removeChild(child);
        }

        function appendChild(node, child) {
          node.appendChild(child);
        }

        function parentNode(node) {
          return node.parentNode;
        }

        function nextSibling(node) {
          return node.nextSibling;
        }

        function tagName(node) {
          return node.tagName;
        }

        function setTextContent(node, text) {
          node.textContent = text;
        }

        function setStyleScope(node, scopeId) {
          node.setAttribute(scopeId, '');
        }

        const nodeOps = /* #__PURE__*/Object.freeze({
          createElement: createElement$1,
          createElementNS,
          createTextNode,
          createComment,
          insertBefore,
          removeChild,
          appendChild,
          parentNode,
          nextSibling,
          tagName,
          setTextContent,
          setStyleScope
        });

        /*  */

        const ref = {
          create: function create(_, vnode) {
            registerRef(vnode);
          },
          update: function update(oldVnode, vnode) {
            if (oldVnode.data.ref !== vnode.data.ref) {
              registerRef(oldVnode, true);
              registerRef(vnode);
            }
          },
          destroy: function destroy(vnode) {
            registerRef(vnode, true);
          }
        };

        function registerRef(vnode, isRemoval) {
          const key = vnode.data.ref;
          if (!isDef(key)) {
            return;
          }

          const vm = vnode.context;
          const ref = vnode.componentInstance || vnode.elm;
          const refs = vm.$refs;
          if (isRemoval) {
            if (Array.isArray(refs[key])) {
              remove(refs[key], ref);
            } else if (refs[key] === ref) {
              refs[key] = undefined;
            }
          } else {
            if (vnode.data.refInFor) {
              if (!Array.isArray(refs[key])) {
                refs[key] = [ref];
              } else if (refs[key].indexOf(ref) < 0) {
                // $flow-disable-line
                refs[key].push(ref);
              }
            } else {
              refs[key] = ref;
            }
          }
        }

        /**
 * Virtual DOM patching algorithm based on Snabbdom by
 * Simon Friis Vindum (@paldepind)
 * Licensed under the MIT License
 * https://github.com/paldepind/snabbdom/blob/master/LICENSE
 *
 * modified by Evan You (@yyx990803)
 *
 * Not type-checking this because this file is perf-critical and the cost
 * of making flow understand it is not worth it.
 */

        const emptyNode = new VNode('', {}, []);

        const hooks = ['create', 'activate', 'update', 'remove', 'destroy'];

        function sameVnode(a, b) {
          return (
            a.key === b.key
    && a.asyncFactory === b.asyncFactory && (
              (
                a.tag === b.tag
        && a.isComment === b.isComment
        && isDef(a.data) === isDef(b.data)
        && sameInputType(a, b)
              ) || (
                isTrue(a.isAsyncPlaceholder)
        && isUndef(b.asyncFactory.error)
              )
            )
          );
        }

        function sameInputType(a, b) {
          if (a.tag !== 'input') {
            return true;
          }
          let i;
          const typeA = isDef(i = a.data) && isDef(i = i.attrs) && i.type;
          const typeB = isDef(i = b.data) && isDef(i = i.attrs) && i.type;
          return typeA === typeB || isTextInputType(typeA) && isTextInputType(typeB);
        }

        function createKeyToOldIdx(children, beginIdx, endIdx) {
          let i; let key;
          const map = {};
          for (i = beginIdx; i <= endIdx; ++i) {
            key = children[i].key;
            if (isDef(key)) {
              map[key] = i;
            }
          }
          return map;
        }

        function createPatchFunction(backend) {
          let i; let j;
          const cbs = {};

          const { modules } = backend;
          const { nodeOps } = backend;

          for (i = 0; i < hooks.length; ++i) {
            cbs[hooks[i]] = [];
            for (j = 0; j < modules.length; ++j) {
              if (isDef(modules[j][hooks[i]])) {
                cbs[hooks[i]].push(modules[j][hooks[i]]);
              }
            }
          }

          function emptyNodeAt(elm) {
            return new VNode(nodeOps.tagName(elm).toLowerCase(), {}, [], undefined, elm);
          }

          function createRmCb(childElm, listeners) {
            function remove$$1() {
              if (--remove$$1.listeners === 0) {
                removeNode(childElm);
              }
            }
            remove$$1.listeners = listeners;
            return remove$$1;
          }

          function removeNode(el) {
            const parent = nodeOps.parentNode(el);
            // element may have already been removed due to v-html / v-text
            if (isDef(parent)) {
              nodeOps.removeChild(parent, el);
            }
          }

          function isUnknownElement$$1(vnode, inVPre) {
            return (
              !inVPre
      && !vnode.ns
      && !(
        config.ignoredElements.length
        && config.ignoredElements.some(ignore => (isRegExp(ignore)
          ? ignore.test(vnode.tag)
          : ignore === vnode.tag))
      )
      && config.isUnknownElement(vnode.tag)
            );
          }

          let creatingElmInVPre = 0;

          function createElm(
            vnode,
            insertedVnodeQueue,
            parentElm,
            refElm,
            nested,
            ownerArray,
            index
          ) {
            if (isDef(vnode.elm) && isDef(ownerArray)) {
              // This vnode was used in a previous render!
              // now it's used as a new node, overwriting its elm would cause
              // potential patch errors down the road when it's used as an insertion
              // reference node. Instead, we clone the node on-demand before creating
              // associated DOM element for it.
              vnode = ownerArray[index] = cloneVNode(vnode);
            }

            vnode.isRootInsert = !nested; // for transition enter check
            if (createComponent(vnode, insertedVnodeQueue, parentElm, refElm)) {
              return;
            }

            const { data } = vnode;
            const { children } = vnode;
            const { tag } = vnode;
            if (isDef(tag)) {
              if (true) {
                if (data && data.pre) {
                  creatingElmInVPre++;
                }
                if (isUnknownElement$$1(vnode, creatingElmInVPre)) {
                  warn(
                    `Unknown custom element: <${tag}> - did you `
            + 'register the component correctly? For recursive components, '
            + 'make sure to provide the "name" option.',
                    vnode.context
                  );
                }
              }

              vnode.elm = vnode.ns
                ? nodeOps.createElementNS(vnode.ns, tag)
                : nodeOps.createElement(tag, vnode);
              setScope(vnode);

              /* istanbul ignore if */
              {
                createChildren(vnode, children, insertedVnodeQueue);
                if (isDef(data)) {
                  invokeCreateHooks(vnode, insertedVnodeQueue);
                }
                insert(parentElm, vnode.elm, refElm);
              }

              if (true && data && data.pre) {
                creatingElmInVPre--;
              }
            } else if (isTrue(vnode.isComment)) {
              vnode.elm = nodeOps.createComment(vnode.text);
              insert(parentElm, vnode.elm, refElm);
            } else {
              vnode.elm = nodeOps.createTextNode(vnode.text);
              insert(parentElm, vnode.elm, refElm);
            }
          }

          function createComponent(vnode, insertedVnodeQueue, parentElm, refElm) {
            let i = vnode.data;
            if (isDef(i)) {
              const isReactivated = isDef(vnode.componentInstance) && i.keepAlive;
              if (isDef(i = i.hook) && isDef(i = i.init)) {
                i(vnode, false /* hydrating */);
              }
              // after calling the init hook, if the vnode is a child component
              // it should've created a child instance and mounted it. the child
              // component also has set the placeholder vnode's elm.
              // in that case we can just return the element and be done.
              if (isDef(vnode.componentInstance)) {
                initComponent(vnode, insertedVnodeQueue);
                insert(parentElm, vnode.elm, refElm);
                if (isTrue(isReactivated)) {
                  reactivateComponent(vnode, insertedVnodeQueue, parentElm, refElm);
                }
                return true;
              }
            }
          }

          function initComponent(vnode, insertedVnodeQueue) {
            if (isDef(vnode.data.pendingInsert)) {
              insertedVnodeQueue.push.apply(insertedVnodeQueue, vnode.data.pendingInsert);
              vnode.data.pendingInsert = null;
            }
            vnode.elm = vnode.componentInstance.$el;
            if (isPatchable(vnode)) {
              invokeCreateHooks(vnode, insertedVnodeQueue);
              setScope(vnode);
            } else {
              // empty component root.
              // skip all element-related modules except for ref (#3455)
              registerRef(vnode);
              // make sure to invoke the insert hook
              insertedVnodeQueue.push(vnode);
            }
          }

          function reactivateComponent(vnode, insertedVnodeQueue, parentElm, refElm) {
            let i;
            // hack for #4339: a reactivated component with inner transition
            // does not trigger because the inner node's created hooks are not called
            // again. It's not ideal to involve module-specific logic in here but
            // there doesn't seem to be a better way to do it.
            let innerNode = vnode;
            while (innerNode.componentInstance) {
              innerNode = innerNode.componentInstance._vnode;
              if (isDef(i = innerNode.data) && isDef(i = i.transition)) {
                for (i = 0; i < cbs.activate.length; ++i) {
                  cbs.activate[i](emptyNode, innerNode);
                }
                insertedVnodeQueue.push(innerNode);
                break;
              }
            }
            // unlike a newly created component,
            // a reactivated keep-alive component doesn't insert itself
            insert(parentElm, vnode.elm, refElm);
          }

          function insert(parent, elm, ref$$1) {
            if (isDef(parent)) {
              if (isDef(ref$$1)) {
                if (nodeOps.parentNode(ref$$1) === parent) {
                  nodeOps.insertBefore(parent, elm, ref$$1);
                }
              } else {
                nodeOps.appendChild(parent, elm);
              }
            }
          }

          function createChildren(vnode, children, insertedVnodeQueue) {
            if (Array.isArray(children)) {
              if (true) {
                checkDuplicateKeys(children);
              }
              for (let i = 0; i < children.length; ++i) {
                createElm(children[i], insertedVnodeQueue, vnode.elm, null, true, children, i);
              }
            } else if (isPrimitive(vnode.text)) {
              nodeOps.appendChild(vnode.elm, nodeOps.createTextNode(String(vnode.text)));
            }
          }

          function isPatchable(vnode) {
            while (vnode.componentInstance) {
              vnode = vnode.componentInstance._vnode;
            }
            return isDef(vnode.tag);
          }

          function invokeCreateHooks(vnode, insertedVnodeQueue) {
            for (let i$1 = 0; i$1 < cbs.create.length; ++i$1) {
              cbs.create[i$1](emptyNode, vnode);
            }
            i = vnode.data.hook; // Reuse variable
            if (isDef(i)) {
              if (isDef(i.create)) {
                i.create(emptyNode, vnode);
              }
              if (isDef(i.insert)) {
                insertedVnodeQueue.push(vnode);
              }
            }
          }

          // set scope id attribute for scoped CSS.
          // this is implemented as a special case to avoid the overhead
          // of going through the normal attribute patching process.
          function setScope(vnode) {
            let i;
            if (isDef(i = vnode.fnScopeId)) {
              nodeOps.setStyleScope(vnode.elm, i);
            } else {
              let ancestor = vnode;
              while (ancestor) {
                if (isDef(i = ancestor.context) && isDef(i = i.$options._scopeId)) {
                  nodeOps.setStyleScope(vnode.elm, i);
                }
                ancestor = ancestor.parent;
              }
            }
            // for slot content they should also get the scopeId from the host instance.
            if (isDef(i = activeInstance)
      && i !== vnode.context
      && i !== vnode.fnContext
      && isDef(i = i.$options._scopeId)
            ) {
              nodeOps.setStyleScope(vnode.elm, i);
            }
          }

          function addVnodes(parentElm, refElm, vnodes, startIdx, endIdx, insertedVnodeQueue) {
            for (; startIdx <= endIdx; ++startIdx) {
              createElm(vnodes[startIdx], insertedVnodeQueue, parentElm, refElm, false, vnodes, startIdx);
            }
          }

          function invokeDestroyHook(vnode) {
            let i; let j;
            const { data } = vnode;
            if (isDef(data)) {
              if (isDef(i = data.hook) && isDef(i = i.destroy)) {
                i(vnode);
              }
              for (i = 0; i < cbs.destroy.length; ++i) {
                cbs.destroy[i](vnode);
              }
            }
            if (isDef(i = vnode.children)) {
              for (j = 0; j < vnode.children.length; ++j) {
                invokeDestroyHook(vnode.children[j]);
              }
            }
          }

          function removeVnodes(vnodes, startIdx, endIdx) {
            for (; startIdx <= endIdx; ++startIdx) {
              const ch = vnodes[startIdx];
              if (isDef(ch)) {
                if (isDef(ch.tag)) {
                  removeAndInvokeRemoveHook(ch);
                  invokeDestroyHook(ch);
                } else { // Text node
                  removeNode(ch.elm);
                }
              }
            }
          }

          function removeAndInvokeRemoveHook(vnode, rm) {
            if (isDef(rm) || isDef(vnode.data)) {
              let i;
              const listeners = cbs.remove.length + 1;
              if (isDef(rm)) {
                // we have a recursively passed down rm callback
                // increase the listeners count
                rm.listeners += listeners;
              } else {
                // directly removing
                rm = createRmCb(vnode.elm, listeners);
              }
              // recursively invoke hooks on child component root node
              if (isDef(i = vnode.componentInstance) && isDef(i = i._vnode) && isDef(i.data)) {
                removeAndInvokeRemoveHook(i, rm);
              }
              for (i = 0; i < cbs.remove.length; ++i) {
                cbs.remove[i](vnode, rm);
              }
              if (isDef(i = vnode.data.hook) && isDef(i = i.remove)) {
                i(vnode, rm);
              } else {
                rm();
              }
            } else {
              removeNode(vnode.elm);
            }
          }

          function updateChildren(parentElm, oldCh, newCh, insertedVnodeQueue, removeOnly) {
            let oldStartIdx = 0;
            let newStartIdx = 0;
            let oldEndIdx = oldCh.length - 1;
            let oldStartVnode = oldCh[0];
            let oldEndVnode = oldCh[oldEndIdx];
            let newEndIdx = newCh.length - 1;
            let newStartVnode = newCh[0];
            let newEndVnode = newCh[newEndIdx];
            let oldKeyToIdx; let idxInOld; let vnodeToMove; let refElm;

            // removeOnly is a special flag used only by <transition-group>
            // to ensure removed elements stay in correct relative positions
            // during leaving transitions
            const canMove = !removeOnly;

            if (true) {
              checkDuplicateKeys(newCh);
            }

            while (oldStartIdx <= oldEndIdx && newStartIdx <= newEndIdx) {
              if (isUndef(oldStartVnode)) {
                oldStartVnode = oldCh[++oldStartIdx]; // Vnode has been moved left
              } else if (isUndef(oldEndVnode)) {
                oldEndVnode = oldCh[--oldEndIdx];
              } else if (sameVnode(oldStartVnode, newStartVnode)) {
                patchVnode(oldStartVnode, newStartVnode, insertedVnodeQueue, newCh, newStartIdx);
                oldStartVnode = oldCh[++oldStartIdx];
                newStartVnode = newCh[++newStartIdx];
              } else if (sameVnode(oldEndVnode, newEndVnode)) {
                patchVnode(oldEndVnode, newEndVnode, insertedVnodeQueue, newCh, newEndIdx);
                oldEndVnode = oldCh[--oldEndIdx];
                newEndVnode = newCh[--newEndIdx];
              } else if (sameVnode(oldStartVnode, newEndVnode)) { // Vnode moved right
                patchVnode(oldStartVnode, newEndVnode, insertedVnodeQueue, newCh, newEndIdx);
                canMove && nodeOps.insertBefore(parentElm, oldStartVnode.elm, nodeOps.nextSibling(oldEndVnode.elm));
                oldStartVnode = oldCh[++oldStartIdx];
                newEndVnode = newCh[--newEndIdx];
              } else if (sameVnode(oldEndVnode, newStartVnode)) { // Vnode moved left
                patchVnode(oldEndVnode, newStartVnode, insertedVnodeQueue, newCh, newStartIdx);
                canMove && nodeOps.insertBefore(parentElm, oldEndVnode.elm, oldStartVnode.elm);
                oldEndVnode = oldCh[--oldEndIdx];
                newStartVnode = newCh[++newStartIdx];
              } else {
                if (isUndef(oldKeyToIdx)) {
                  oldKeyToIdx = createKeyToOldIdx(oldCh, oldStartIdx, oldEndIdx);
                }
                idxInOld = isDef(newStartVnode.key)
                  ? oldKeyToIdx[newStartVnode.key]
                  : findIdxInOld(newStartVnode, oldCh, oldStartIdx, oldEndIdx);
                if (isUndef(idxInOld)) { // New element
                  createElm(newStartVnode, insertedVnodeQueue, parentElm, oldStartVnode.elm, false, newCh, newStartIdx);
                } else {
                  vnodeToMove = oldCh[idxInOld];
                  if (sameVnode(vnodeToMove, newStartVnode)) {
                    patchVnode(vnodeToMove, newStartVnode, insertedVnodeQueue, newCh, newStartIdx);
                    oldCh[idxInOld] = undefined;
                    canMove && nodeOps.insertBefore(parentElm, vnodeToMove.elm, oldStartVnode.elm);
                  } else {
                    // same key but different element. treat as new element
                    createElm(newStartVnode, insertedVnodeQueue, parentElm, oldStartVnode.elm, false, newCh, newStartIdx);
                  }
                }
                newStartVnode = newCh[++newStartIdx];
              }
            }
            if (oldStartIdx > oldEndIdx) {
              refElm = isUndef(newCh[newEndIdx + 1]) ? null : newCh[newEndIdx + 1].elm;
              addVnodes(parentElm, refElm, newCh, newStartIdx, newEndIdx, insertedVnodeQueue);
            } else if (newStartIdx > newEndIdx) {
              removeVnodes(oldCh, oldStartIdx, oldEndIdx);
            }
          }

          function checkDuplicateKeys(children) {
            const seenKeys = {};
            for (let i = 0; i < children.length; i++) {
              const vnode = children[i];
              const { key } = vnode;
              if (isDef(key)) {
                if (seenKeys[key]) {
                  warn(
                    (`Duplicate keys detected: '${key}'. This may cause an update error.`),
                    vnode.context
                  );
                } else {
                  seenKeys[key] = true;
                }
              }
            }
          }

          function findIdxInOld(node, oldCh, start, end) {
            for (let i = start; i < end; i++) {
              const c = oldCh[i];
              if (isDef(c) && sameVnode(node, c)) {
                return i;
              }
            }
          }

          function patchVnode(
            oldVnode,
            vnode,
            insertedVnodeQueue,
            ownerArray,
            index,
            removeOnly
          ) {
            if (oldVnode === vnode) {
              return;
            }

            if (isDef(vnode.elm) && isDef(ownerArray)) {
              // clone reused vnode
              vnode = ownerArray[index] = cloneVNode(vnode);
            }

            const elm = vnode.elm = oldVnode.elm;

            if (isTrue(oldVnode.isAsyncPlaceholder)) {
              if (isDef(vnode.asyncFactory.resolved)) {
                hydrate(oldVnode.elm, vnode, insertedVnodeQueue);
              } else {
                vnode.isAsyncPlaceholder = true;
              }
              return;
            }

            // reuse element for static trees.
            // note we only do this if the vnode is cloned -
            // if the new node is not cloned it means the render functions have been
            // reset by the hot-reload-api and we need to do a proper re-render.
            if (isTrue(vnode.isStatic)
      && isTrue(oldVnode.isStatic)
      && vnode.key === oldVnode.key
      && (isTrue(vnode.isCloned) || isTrue(vnode.isOnce))
            ) {
              vnode.componentInstance = oldVnode.componentInstance;
              return;
            }

            let i;
            const { data } = vnode;
            if (isDef(data) && isDef(i = data.hook) && isDef(i = i.prepatch)) {
              i(oldVnode, vnode);
            }

            const oldCh = oldVnode.children;
            const ch = vnode.children;
            if (isDef(data) && isPatchable(vnode)) {
              for (i = 0; i < cbs.update.length; ++i) {
                cbs.update[i](oldVnode, vnode);
              }
              if (isDef(i = data.hook) && isDef(i = i.update)) {
                i(oldVnode, vnode);
              }
            }
            if (isUndef(vnode.text)) {
              if (isDef(oldCh) && isDef(ch)) {
                if (oldCh !== ch) {
                  updateChildren(elm, oldCh, ch, insertedVnodeQueue, removeOnly);
                }
              } else if (isDef(ch)) {
                if (true) {
                  checkDuplicateKeys(ch);
                }
                if (isDef(oldVnode.text)) {
                  nodeOps.setTextContent(elm, '');
                }
                addVnodes(elm, null, ch, 0, ch.length - 1, insertedVnodeQueue);
              } else if (isDef(oldCh)) {
                removeVnodes(oldCh, 0, oldCh.length - 1);
              } else if (isDef(oldVnode.text)) {
                nodeOps.setTextContent(elm, '');
              }
            } else if (oldVnode.text !== vnode.text) {
              nodeOps.setTextContent(elm, vnode.text);
            }
            if (isDef(data)) {
              if (isDef(i = data.hook) && isDef(i = i.postpatch)) {
                i(oldVnode, vnode);
              }
            }
          }

          function invokeInsertHook(vnode, queue, initial) {
            // delay insert hooks for component root nodes, invoke them after the
            // element is really inserted
            if (isTrue(initial) && isDef(vnode.parent)) {
              vnode.parent.data.pendingInsert = queue;
            } else {
              for (let i = 0; i < queue.length; ++i) {
                queue[i].data.hook.insert(queue[i]);
              }
            }
          }

          let hydrationBailed = false;
          // list of modules that can skip create hook during hydration because they
          // are already rendered on the client or has no need for initialization
          // Note: style is excluded because it relies on initial clone for future
          // deep updates (#7063).
          const isRenderedModule = makeMap('attrs,class,staticClass,staticStyle,key');

          // Note: this is a browser-only function so we can assume elms are DOM nodes.
          function hydrate(elm, vnode, insertedVnodeQueue, inVPre) {
            let i;
            const { tag } = vnode;
            const { data } = vnode;
            const { children } = vnode;
            inVPre = inVPre || (data && data.pre);
            vnode.elm = elm;

            if (isTrue(vnode.isComment) && isDef(vnode.asyncFactory)) {
              vnode.isAsyncPlaceholder = true;
              return true;
            }
            // assert node match
            if (true) {
              if (!assertNodeMatch(elm, vnode, inVPre)) {
                return false;
              }
            }
            if (isDef(data)) {
              if (isDef(i = data.hook) && isDef(i = i.init)) {
                i(vnode, true /* hydrating */);
              }
              if (isDef(i = vnode.componentInstance)) {
                // child component. it should have hydrated its own tree.
                initComponent(vnode, insertedVnodeQueue);
                return true;
              }
            }
            if (isDef(tag)) {
              if (isDef(children)) {
                // empty element, allow client to pick up and populate children
                if (!elm.hasChildNodes()) {
                  createChildren(vnode, children, insertedVnodeQueue);
                } else {
                  // v-html and domProps: innerHTML
                  if (isDef(i = data) && isDef(i = i.domProps) && isDef(i = i.innerHTML)) {
                    if (i !== elm.innerHTML) {
                      /* istanbul ignore if */
                      if (true
                && typeof console !== 'undefined'
                && !hydrationBailed
                      ) {
                        hydrationBailed = true;
                        console.warn('Parent: ', elm);
                        console.warn('server innerHTML: ', i);
                        console.warn('client innerHTML: ', elm.innerHTML);
                      }
                      return false;
                    }
                  } else {
                    // iterate and compare children lists
                    let childrenMatch = true;
                    let childNode = elm.firstChild;
                    for (let i$1 = 0; i$1 < children.length; i$1++) {
                      if (!childNode || !hydrate(childNode, children[i$1], insertedVnodeQueue, inVPre)) {
                        childrenMatch = false;
                        break;
                      }
                      childNode = childNode.nextSibling;
                    }
                    // if childNode is not null, it means the actual childNodes list is
                    // longer than the virtual children list.
                    if (!childrenMatch || childNode) {
                      /* istanbul ignore if */
                      if (true
                && typeof console !== 'undefined'
                && !hydrationBailed
                      ) {
                        hydrationBailed = true;
                        console.warn('Parent: ', elm);
                        console.warn('Mismatching childNodes vs. VNodes: ', elm.childNodes, children);
                      }
                      return false;
                    }
                  }
                }
              }
              if (isDef(data)) {
                let fullInvoke = false;
                for (const key in data) {
                  if (!isRenderedModule(key)) {
                    fullInvoke = true;
                    invokeCreateHooks(vnode, insertedVnodeQueue);
                    break;
                  }
                }
                if (!fullInvoke && data.class) {
                  // ensure collecting deps for deep class bindings for future updates
                  traverse(data.class);
                }
              }
            } else if (elm.data !== vnode.text) {
              elm.data = vnode.text;
            }
            return true;
          }

          function assertNodeMatch(node, vnode, inVPre) {
            if (isDef(vnode.tag)) {
              return vnode.tag.indexOf('vue-component') === 0 || (
                !isUnknownElement$$1(vnode, inVPre)
        && vnode.tag.toLowerCase() === (node.tagName && node.tagName.toLowerCase())
              );
            }
            return node.nodeType === (vnode.isComment ? 8 : 3);
          }

          return function patch(oldVnode, vnode, hydrating, removeOnly) {
            if (isUndef(vnode)) {
              if (isDef(oldVnode)) {
                invokeDestroyHook(oldVnode);
              }
              return;
            }

            let isInitialPatch = false;
            const insertedVnodeQueue = [];

            if (isUndef(oldVnode)) {
              // empty mount (likely as component), create new root element
              isInitialPatch = true;
              createElm(vnode, insertedVnodeQueue);
            } else {
              const isRealElement = isDef(oldVnode.nodeType);
              if (!isRealElement && sameVnode(oldVnode, vnode)) {
                // patch existing root node
                patchVnode(oldVnode, vnode, insertedVnodeQueue, null, null, removeOnly);
              } else {
                if (isRealElement) {
                  // mounting to a real element
                  // check if this is server-rendered content and if we can perform
                  // a successful hydration.
                  if (oldVnode.nodeType === 1 && oldVnode.hasAttribute(SSR_ATTR)) {
                    oldVnode.removeAttribute(SSR_ATTR);
                    hydrating = true;
                  }
                  if (isTrue(hydrating)) {
                    if (hydrate(oldVnode, vnode, insertedVnodeQueue)) {
                      invokeInsertHook(vnode, insertedVnodeQueue, true);
                      return oldVnode;
                    } if (true) {
                      warn('The client-side rendered virtual DOM tree is not matching '
                + 'server-rendered content. This is likely caused by incorrect '
                + 'HTML markup, for example nesting block-level elements inside '
                + '<p>, or missing <tbody>. Bailing hydration and performing '
                + 'full client-side render.');
                    }
                  }
                  // either not server-rendered, or hydration failed.
                  // create an empty node and replace it
                  oldVnode = emptyNodeAt(oldVnode);
                }

                // replacing existing element
                const oldElm = oldVnode.elm;
                const parentElm = nodeOps.parentNode(oldElm);

                // create new node
                createElm(
                  vnode,
                  insertedVnodeQueue,
                  // extremely rare edge case: do not insert if old element is in a
                  // leaving transition. Only happens when combining transition +
                  // keep-alive + HOCs. (#4590)
                  oldElm._leaveCb ? null : parentElm,
                  nodeOps.nextSibling(oldElm)
                );

                // update parent placeholder node element, recursively
                if (isDef(vnode.parent)) {
                  let ancestor = vnode.parent;
                  const patchable = isPatchable(vnode);
                  while (ancestor) {
                    for (let i = 0; i < cbs.destroy.length; ++i) {
                      cbs.destroy[i](ancestor);
                    }
                    ancestor.elm = vnode.elm;
                    if (patchable) {
                      for (let i$1 = 0; i$1 < cbs.create.length; ++i$1) {
                        cbs.create[i$1](emptyNode, ancestor);
                      }
                      // #6513
                      // invoke insert hooks that may have been merged by create hooks.
                      // e.g. for directives that uses the "inserted" hook.
                      const { insert } = ancestor.data.hook;
                      if (insert.merged) {
                        // start at index 1 to avoid re-invoking component mounted hook
                        for (let i$2 = 1; i$2 < insert.fns.length; i$2++) {
                          insert.fns[i$2]();
                        }
                      }
                    } else {
                      registerRef(ancestor);
                    }
                    ancestor = ancestor.parent;
                  }
                }

                // destroy old node
                if (isDef(parentElm)) {
                  removeVnodes([oldVnode], 0, 0);
                } else if (isDef(oldVnode.tag)) {
                  invokeDestroyHook(oldVnode);
                }
              }
            }

            invokeInsertHook(vnode, insertedVnodeQueue, isInitialPatch);
            return vnode.elm;
          };
        }

        /*  */

        const directives = {
          create: updateDirectives,
          update: updateDirectives,
          destroy: function unbindDirectives(vnode) {
            updateDirectives(vnode, emptyNode);
          }
        };

        function updateDirectives(oldVnode, vnode) {
          if (oldVnode.data.directives || vnode.data.directives) {
            _update(oldVnode, vnode);
          }
        }

        function _update(oldVnode, vnode) {
          const isCreate = oldVnode === emptyNode;
          const isDestroy = vnode === emptyNode;
          const oldDirs = normalizeDirectives$1(oldVnode.data.directives, oldVnode.context);
          const newDirs = normalizeDirectives$1(vnode.data.directives, vnode.context);

          const dirsWithInsert = [];
          const dirsWithPostpatch = [];

          let key; let oldDir; let dir;
          for (key in newDirs) {
            oldDir = oldDirs[key];
            dir = newDirs[key];
            if (!oldDir) {
              // new directive, bind
              callHook$1(dir, 'bind', vnode, oldVnode);
              if (dir.def && dir.def.inserted) {
                dirsWithInsert.push(dir);
              }
            } else {
              // existing directive, update
              dir.oldValue = oldDir.value;
              dir.oldArg = oldDir.arg;
              callHook$1(dir, 'update', vnode, oldVnode);
              if (dir.def && dir.def.componentUpdated) {
                dirsWithPostpatch.push(dir);
              }
            }
          }

          if (dirsWithInsert.length) {
            const callInsert = function () {
              for (let i = 0; i < dirsWithInsert.length; i++) {
                callHook$1(dirsWithInsert[i], 'inserted', vnode, oldVnode);
              }
            };
            if (isCreate) {
              mergeVNodeHook(vnode, 'insert', callInsert);
            } else {
              callInsert();
            }
          }

          if (dirsWithPostpatch.length) {
            mergeVNodeHook(vnode, 'postpatch', () => {
              for (let i = 0; i < dirsWithPostpatch.length; i++) {
                callHook$1(dirsWithPostpatch[i], 'componentUpdated', vnode, oldVnode);
              }
            });
          }

          if (!isCreate) {
            for (key in oldDirs) {
              if (!newDirs[key]) {
                // no longer present, unbind
                callHook$1(oldDirs[key], 'unbind', oldVnode, oldVnode, isDestroy);
              }
            }
          }
        }

        const emptyModifiers = Object.create(null);

        function normalizeDirectives$1(
          dirs,
          vm
        ) {
          const res = Object.create(null);
          if (!dirs) {
            // $flow-disable-line
            return res;
          }
          let i; let dir;
          for (i = 0; i < dirs.length; i++) {
            dir = dirs[i];
            if (!dir.modifiers) {
              // $flow-disable-line
              dir.modifiers = emptyModifiers;
            }
            res[getRawDirName(dir)] = dir;
            dir.def = resolveAsset(vm.$options, 'directives', dir.name, true);
          }
          // $flow-disable-line
          return res;
        }

        function getRawDirName(dir) {
          return dir.rawName || (`${dir.name}.${Object.keys(dir.modifiers || {}).join('.')}`);
        }

        function callHook$1(dir, hook, vnode, oldVnode, isDestroy) {
          const fn = dir.def && dir.def[hook];
          if (fn) {
            try {
              fn(vnode.elm, dir, vnode, oldVnode, isDestroy);
            } catch (e) {
              handleError(e, vnode.context, (`directive ${dir.name} ${hook} hook`));
            }
          }
        }

        const baseModules = [
          ref,
          directives
        ];

        /*  */

        function updateAttrs(oldVnode, vnode) {
          const opts = vnode.componentOptions;
          if (isDef(opts) && opts.Ctor.options.inheritAttrs === false) {
            return;
          }
          if (isUndef(oldVnode.data.attrs) && isUndef(vnode.data.attrs)) {
            return;
          }
          let key; let cur; let old;
          const { elm } = vnode;
          const oldAttrs = oldVnode.data.attrs || {};
          let attrs = vnode.data.attrs || {};
          // clone observed objects, as the user probably wants to mutate it
          if (isDef(attrs.__ob__)) {
            attrs = vnode.data.attrs = extend({}, attrs);
          }

          for (key in attrs) {
            cur = attrs[key];
            old = oldAttrs[key];
            if (old !== cur) {
              setAttr(elm, key, cur, vnode.data.pre);
            }
          }
          // #4391: in IE9, setting type can reset value for input[type=radio]
          // #6666: IE/Edge forces progress value down to 1 before setting a max
          /* istanbul ignore if */
          if ((isIE || isEdge) && attrs.value !== oldAttrs.value) {
            setAttr(elm, 'value', attrs.value);
          }
          for (key in oldAttrs) {
            if (isUndef(attrs[key])) {
              if (isXlink(key)) {
                elm.removeAttributeNS(xlinkNS, getXlinkProp(key));
              } else if (!isEnumeratedAttr(key)) {
                elm.removeAttribute(key);
              }
            }
          }
        }

        function setAttr(el, key, value, isInPre) {
          if (isInPre || el.tagName.indexOf('-') > -1) {
            baseSetAttr(el, key, value);
          } else if (isBooleanAttr(key)) {
            // set attribute for blank value
            // e.g. <option disabled>Select one</option>
            if (isFalsyAttrValue(value)) {
              el.removeAttribute(key);
            } else {
              // technically allowfullscreen is a boolean attribute for <iframe>,
              // but Flash expects a value of "true" when used on <embed> tag
              value = key === 'allowfullscreen' && el.tagName === 'EMBED'
                ? 'true'
                : key;
              el.setAttribute(key, value);
            }
          } else if (isEnumeratedAttr(key)) {
            el.setAttribute(key, convertEnumeratedValue(key, value));
          } else if (isXlink(key)) {
            if (isFalsyAttrValue(value)) {
              el.removeAttributeNS(xlinkNS, getXlinkProp(key));
            } else {
              el.setAttributeNS(xlinkNS, key, value);
            }
          } else {
            baseSetAttr(el, key, value);
          }
        }

        function baseSetAttr(el, key, value) {
          if (isFalsyAttrValue(value)) {
            el.removeAttribute(key);
          } else {
            // #7138: IE10 & 11 fires input event when setting placeholder on
            // <textarea>... block the first input event and remove the blocker
            // immediately.
            /* istanbul ignore if */
            if (
              isIE && !isIE9
      && el.tagName === 'TEXTAREA'
      && key === 'placeholder' && value !== '' && !el.__ieph
            ) {
              var blocker = function (e) {
                e.stopImmediatePropagation();
                el.removeEventListener('input', blocker);
              };
              el.addEventListener('input', blocker);
              // $flow-disable-line
              el.__ieph = true; /* IE placeholder patched */
            }
            el.setAttribute(key, value);
          }
        }

        const attrs = {
          create: updateAttrs,
          update: updateAttrs
        };

        /*  */

        function updateClass(oldVnode, vnode) {
          const el = vnode.elm;
          const { data } = vnode;
          const oldData = oldVnode.data;
          if (
            isUndef(data.staticClass)
    && isUndef(data.class) && (
              isUndef(oldData) || (
                isUndef(oldData.staticClass)
        && isUndef(oldData.class)
              )
            )
          ) {
            return;
          }

          let cls = genClassForVnode(vnode);

          // handle transition classes
          const transitionClass = el._transitionClasses;
          if (isDef(transitionClass)) {
            cls = concat(cls, stringifyClass(transitionClass));
          }

          // set the class
          if (cls !== el._prevClass) {
            el.setAttribute('class', cls);
            el._prevClass = cls;
          }
        }

        const klass = {
          create: updateClass,
          update: updateClass
        };

        /*  */

        /*  */

        /*  */

        /*  */

        // in some cases, the event used has to be determined at runtime
        // so we used some reserved tokens during compile.
        const RANGE_TOKEN = '__r';
        const CHECKBOX_RADIO_TOKEN = '__c';

        /*  */

        // normalize v-model event tokens that can only be determined at runtime.
        // it's important to place the event as the first in the array because
        // the whole point is ensuring the v-model callback gets called before
        // user-attached handlers.
        function normalizeEvents(on) {
          /* istanbul ignore if */
          if (isDef(on[RANGE_TOKEN])) {
            // IE input[type=range] only supports `change` event
            const event = isIE ? 'change' : 'input';
            on[event] = [].concat(on[RANGE_TOKEN], on[event] || []);
            delete on[RANGE_TOKEN];
          }
          // This was originally intended to fix #4521 but no longer necessary
          // after 2.5. Keeping it for backwards compat with generated code from < 2.4
          /* istanbul ignore if */
          if (isDef(on[CHECKBOX_RADIO_TOKEN])) {
            on.change = [].concat(on[CHECKBOX_RADIO_TOKEN], on.change || []);
            delete on[CHECKBOX_RADIO_TOKEN];
          }
        }

        let target$1;

        function createOnceHandler$1(event, handler, capture) {
          const _target = target$1; // save current target element in closure
          return function onceHandler() {
            const res = handler.apply(null, arguments);
            if (res !== null) {
              remove$2(event, onceHandler, capture, _target);
            }
          };
        }

        // #9446: Firefox <= 53 (in particular, ESR 52) has incorrect Event.timeStamp
        // implementation and does not fire microtasks in between event propagation, so
        // safe to exclude.
        const useMicrotaskFix = isUsingMicroTask && !(isFF && Number(isFF[1]) <= 53);

        function add$1(
          name,
          handler,
          capture,
          passive
        ) {
          // async edge case #6566: inner click event triggers patch, event handler
          // attached to outer element during patch, and triggered again. This
          // happens because browsers fire microtask ticks between event propagation.
          // the solution is simple: we save the timestamp when a handler is attached,
          // and the handler would only fire if the event passed to it was fired
          // AFTER it was attached.
          if (useMicrotaskFix) {
            const attachedTimestamp = currentFlushTimestamp;
            const original = handler;
            handler = original._wrapper = function (e) {
              if (
              // no bubbling, should always fire.
              // this is just a safety net in case event.timeStamp is unreliable in
              // certain weird environments...
                e.target === e.currentTarget
        // event is fired after handler attachment
        || e.timeStamp >= attachedTimestamp
        // bail for environments that have buggy event.timeStamp implementations
        // #9462 iOS 9 bug: event.timeStamp is 0 after history.pushState
        // #9681 QtWebEngine event.timeStamp is negative value
        || e.timeStamp <= 0
        // #9448 bail if event is fired in another document in a multi-page
        // electron/nw.js app, since event.timeStamp will be using a different
        // starting reference
        || e.target.ownerDocument !== document
              ) {
                return original.apply(this, arguments);
              }
            };
          }
          target$1.addEventListener(
            name,
            handler,
            supportsPassive
              ? { capture, passive }
              : capture
          );
        }

        function remove$2(
          name,
          handler,
          capture,
          _target
        ) {
          (_target || target$1).removeEventListener(
            name,
            handler._wrapper || handler,
            capture
          );
        }

        function updateDOMListeners(oldVnode, vnode) {
          if (isUndef(oldVnode.data.on) && isUndef(vnode.data.on)) {
            return;
          }
          const on = vnode.data.on || {};
          const oldOn = oldVnode.data.on || {};
          target$1 = vnode.elm;
          normalizeEvents(on);
          updateListeners(on, oldOn, add$1, remove$2, createOnceHandler$1, vnode.context);
          target$1 = undefined;
        }

        const events = {
          create: updateDOMListeners,
          update: updateDOMListeners
        };

        /*  */

        let svgContainer;

        function updateDOMProps(oldVnode, vnode) {
          if (isUndef(oldVnode.data.domProps) && isUndef(vnode.data.domProps)) {
            return;
          }
          let key; let cur;
          const { elm } = vnode;
          const oldProps = oldVnode.data.domProps || {};
          let props = vnode.data.domProps || {};
          // clone observed objects, as the user probably wants to mutate it
          if (isDef(props.__ob__)) {
            props = vnode.data.domProps = extend({}, props);
          }

          for (key in oldProps) {
            if (!(key in props)) {
              elm[key] = '';
            }
          }

          for (key in props) {
            cur = props[key];
            // ignore children if the node has textContent or innerHTML,
            // as these will throw away existing DOM nodes and cause removal errors
            // on subsequent patches (#3360)
            if (key === 'textContent' || key === 'innerHTML') {
              if (vnode.children) {
                vnode.children.length = 0;
              }
              if (cur === oldProps[key]) {
                continue;
              }
              // #6601 work around Chrome version <= 55 bug where single textNode
              // replaced by innerHTML/textContent retains its parentNode property
              if (elm.childNodes.length === 1) {
                elm.removeChild(elm.childNodes[0]);
              }
            }

            if (key === 'value' && elm.tagName !== 'PROGRESS') {
              // store value as _value as well since
              // non-string values will be stringified
              elm._value = cur;
              // avoid resetting cursor position when value is the same
              const strCur = isUndef(cur) ? '' : String(cur);
              if (shouldUpdateValue(elm, strCur)) {
                elm.value = strCur;
              }
            } else if (key === 'innerHTML' && isSVG(elm.tagName) && isUndef(elm.innerHTML)) {
              // IE doesn't support innerHTML for SVG elements
              svgContainer = svgContainer || document.createElement('div');
              svgContainer.innerHTML = `<svg>${cur}</svg>`;
              const svg = svgContainer.firstChild;
              while (elm.firstChild) {
                elm.removeChild(elm.firstChild);
              }
              while (svg.firstChild) {
                elm.appendChild(svg.firstChild);
              }
            } else if (
            // skip the update if old and new VDOM state is the same.
            // `value` is handled separately because the DOM value may be temporarily
            // out of sync with VDOM state due to focus, composition and modifiers.
            // This  #4521 by skipping the unnecessary `checked` update.
              cur !== oldProps[key]
            ) {
              // some property updates can throw
              // e.g. `value` on <progress> w/ non-finite value
              try {
                elm[key] = cur;
              } catch (e) {}
            }
          }
        }

        // check platforms/web/util/attrs.js acceptValue


        function shouldUpdateValue(elm, checkVal) {
          return (!elm.composing && (
            elm.tagName === 'OPTION'
    || isNotInFocusAndDirty(elm, checkVal)
    || isDirtyWithModifiers(elm, checkVal)
          ));
        }

        function isNotInFocusAndDirty(elm, checkVal) {
          // return true when textbox (.number and .trim) loses focus and its value is
          // not equal to the updated value
          let notInFocus = true;
          // #6157
          // work around IE bug when accessing document.activeElement in an iframe
          try {
            notInFocus = document.activeElement !== elm;
          } catch (e) {}
          return notInFocus && elm.value !== checkVal;
        }

        function isDirtyWithModifiers(elm, newVal) {
          const { value } = elm;
          const modifiers = elm._vModifiers; // injected by v-model runtime
          if (isDef(modifiers)) {
            if (modifiers.number) {
              return toNumber(value) !== toNumber(newVal);
            }
            if (modifiers.trim) {
              return value.trim() !== newVal.trim();
            }
          }
          return value !== newVal;
        }

        const domProps = {
          create: updateDOMProps,
          update: updateDOMProps
        };

        /*  */

        const parseStyleText = cached((cssText) => {
          const res = {};
          const listDelimiter = /;(?![^(]*\))/g;
          const propertyDelimiter = /:(.+)/;
          cssText.split(listDelimiter).forEach((item) => {
            if (item) {
              const tmp = item.split(propertyDelimiter);
              tmp.length > 1 && (res[tmp[0].trim()] = tmp[1].trim());
            }
          });
          return res;
        });

        // merge static and dynamic style data on the same vnode
        function normalizeStyleData(data) {
          const style = normalizeStyleBinding(data.style);
          // static style is pre-processed into an object during compilation
          // and is always a fresh object, so it's safe to merge into it
          return data.staticStyle
            ? extend(data.staticStyle, style)
            : style;
        }

        // normalize possible array / string values into Object
        function normalizeStyleBinding(bindingStyle) {
          if (Array.isArray(bindingStyle)) {
            return toObject(bindingStyle);
          }
          if (typeof bindingStyle === 'string') {
            return parseStyleText(bindingStyle);
          }
          return bindingStyle;
        }

        /**
 * parent component style should be after child's
 * so that parent component's style could override it
 */
        function getStyle(vnode, checkChild) {
          const res = {};
          let styleData;

          if (checkChild) {
            let childNode = vnode;
            while (childNode.componentInstance) {
              childNode = childNode.componentInstance._vnode;
              if (
                childNode && childNode.data
        && (styleData = normalizeStyleData(childNode.data))
              ) {
                extend(res, styleData);
              }
            }
          }

          if ((styleData = normalizeStyleData(vnode.data))) {
            extend(res, styleData);
          }

          let parentNode = vnode;
          while ((parentNode = parentNode.parent)) {
            if (parentNode.data && (styleData = normalizeStyleData(parentNode.data))) {
              extend(res, styleData);
            }
          }
          return res;
        }

        /*  */

        const cssVarRE = /^--/;
        const importantRE = /\s*!important$/;
        const setProp = function (el, name, val) {
          /* istanbul ignore if */
          if (cssVarRE.test(name)) {
            el.style.setProperty(name, val);
          } else if (importantRE.test(val)) {
            el.style.setProperty(hyphenate(name), val.replace(importantRE, ''), 'important');
          } else {
            const normalizedName = normalize(name);
            if (Array.isArray(val)) {
              // Support values array created by autoprefixer, e.g.
              // {display: ["-webkit-box", "-ms-flexbox", "flex"]}
              // Set them one by one, and the browser will only set those it can recognize
              for (let i = 0, len = val.length; i < len; i++) {
                el.style[normalizedName] = val[i];
              }
            } else {
              el.style[normalizedName] = val;
            }
          }
        };

        const vendorNames = ['Webkit', 'Moz', 'ms'];

        let emptyStyle;
        var normalize = cached((prop) => {
          emptyStyle = emptyStyle || document.createElement('div').style;
          prop = camelize(prop);
          if (prop !== 'filter' && (prop in emptyStyle)) {
            return prop;
          }
          const capName = prop.charAt(0).toUpperCase() + prop.slice(1);
          for (let i = 0; i < vendorNames.length; i++) {
            const name = vendorNames[i] + capName;
            if (name in emptyStyle) {
              return name;
            }
          }
        });

        function updateStyle(oldVnode, vnode) {
          const { data } = vnode;
          const oldData = oldVnode.data;

          if (isUndef(data.staticStyle) && isUndef(data.style)
    && isUndef(oldData.staticStyle) && isUndef(oldData.style)
          ) {
            return;
          }

          let cur; let name;
          const el = vnode.elm;
          const oldStaticStyle = oldData.staticStyle;
          const oldStyleBinding = oldData.normalizedStyle || oldData.style || {};

          // if static style exists, stylebinding already merged into it when doing normalizeStyleData
          const oldStyle = oldStaticStyle || oldStyleBinding;

          const style = normalizeStyleBinding(vnode.data.style) || {};

          // store normalized style under a different key for next diff
          // make sure to clone it if it's reactive, since the user likely wants
          // to mutate it.
          vnode.data.normalizedStyle = isDef(style.__ob__)
            ? extend({}, style)
            : style;

          const newStyle = getStyle(vnode, true);

          for (name in oldStyle) {
            if (isUndef(newStyle[name])) {
              setProp(el, name, '');
            }
          }
          for (name in newStyle) {
            cur = newStyle[name];
            if (cur !== oldStyle[name]) {
              // ie9 setting to null has no effect, must use empty string
              setProp(el, name, cur == null ? '' : cur);
            }
          }
        }

        const style = {
          create: updateStyle,
          update: updateStyle
        };

        /*  */

        const whitespaceRE = /\s+/;

        /**
 * Add class with compatibility for SVG since classList is not supported on
 * SVG elements in IE
 */
        function addClass(el, cls) {
          /* istanbul ignore if */
          if (!cls || !(cls = cls.trim())) {
            return;
          }

          /* istanbul ignore else */
          if (el.classList) {
            if (cls.indexOf(' ') > -1) {
              cls.split(whitespaceRE).forEach(c => el.classList.add(c));
            } else {
              el.classList.add(cls);
            }
          } else {
            const cur = ` ${el.getAttribute('class') || ''} `;
            if (cur.indexOf(` ${cls} `) < 0) {
              el.setAttribute('class', (cur + cls).trim());
            }
          }
        }

        /**
 * Remove class with compatibility for SVG since classList is not supported on
 * SVG elements in IE
 */
        function removeClass(el, cls) {
          /* istanbul ignore if */
          if (!cls || !(cls = cls.trim())) {
            return;
          }

          /* istanbul ignore else */
          if (el.classList) {
            if (cls.indexOf(' ') > -1) {
              cls.split(whitespaceRE).forEach(c => el.classList.remove(c));
            } else {
              el.classList.remove(cls);
            }
            if (!el.classList.length) {
              el.removeAttribute('class');
            }
          } else {
            let cur = ` ${el.getAttribute('class') || ''} `;
            const tar = ` ${cls} `;
            while (cur.indexOf(tar) >= 0) {
              cur = cur.replace(tar, ' ');
            }
            cur = cur.trim();
            if (cur) {
              el.setAttribute('class', cur);
            } else {
              el.removeAttribute('class');
            }
          }
        }

        /*  */

        function resolveTransition(def$$1) {
          if (!def$$1) {
            return;
          }
          /* istanbul ignore else */
          if (typeof def$$1 === 'object') {
            const res = {};
            if (def$$1.css !== false) {
              extend(res, autoCssTransition(def$$1.name || 'v'));
            }
            extend(res, def$$1);
            return res;
          } if (typeof def$$1 === 'string') {
            return autoCssTransition(def$$1);
          }
        }

        var autoCssTransition = cached(name => ({
          enterClass: (`${name}-enter`),
          enterToClass: (`${name}-enter-to`),
          enterActiveClass: (`${name}-enter-active`),
          leaveClass: (`${name}-leave`),
          leaveToClass: (`${name}-leave-to`),
          leaveActiveClass: (`${name}-leave-active`)
        }));

        const hasTransition = inBrowser && !isIE9;
        const TRANSITION = 'transition';
        const ANIMATION = 'animation';

        // Transition property/event sniffing
        let transitionProp = 'transition';
        let transitionEndEvent = 'transitionend';
        let animationProp = 'animation';
        let animationEndEvent = 'animationend';
        if (hasTransition) {
          /* istanbul ignore if */
          if (window.ontransitionend === undefined
    && window.onwebkittransitionend !== undefined
          ) {
            transitionProp = 'WebkitTransition';
            transitionEndEvent = 'webkitTransitionEnd';
          }
          if (window.onanimationend === undefined
    && window.onwebkitanimationend !== undefined
          ) {
            animationProp = 'WebkitAnimation';
            animationEndEvent = 'webkitAnimationEnd';
          }
        }

        // binding to window is necessary to make hot reload work in IE in strict mode
        const raf = inBrowser
          ? window.requestAnimationFrame
            ? window.requestAnimationFrame.bind(window)
            : setTimeout
          : /* istanbul ignore next */ function (fn) {
            return fn();
          };

        function nextFrame(fn) {
          raf(() => {
            raf(fn);
          });
        }

        function addTransitionClass(el, cls) {
          const transitionClasses = el._transitionClasses || (el._transitionClasses = []);
          if (transitionClasses.indexOf(cls) < 0) {
            transitionClasses.push(cls);
            addClass(el, cls);
          }
        }

        function removeTransitionClass(el, cls) {
          if (el._transitionClasses) {
            remove(el._transitionClasses, cls);
          }
          removeClass(el, cls);
        }

        function whenTransitionEnds(
          el,
          expectedType,
          cb
        ) {
          const ref = getTransitionInfo(el, expectedType);
          const { type } = ref;
          const { timeout } = ref;
          const { propCount } = ref;
          if (!type) {
            return cb();
          }
          const event = type === TRANSITION ? transitionEndEvent : animationEndEvent;
          let ended = 0;
          const end = function () {
            el.removeEventListener(event, onEnd);
            cb();
          };
          var onEnd = function (e) {
            if (e.target === el) {
              if (++ended >= propCount) {
                end();
              }
            }
          };
          setTimeout(() => {
            if (ended < propCount) {
              end();
            }
          }, timeout + 1);
          el.addEventListener(event, onEnd);
        }

        const transformRE = /\b(transform|all)(,|$)/;

        function getTransitionInfo(el, expectedType) {
          const styles = window.getComputedStyle(el);
          // JSDOM may return undefined for transition properties
          const transitionDelays = (styles[`${transitionProp}Delay`] || '').split(', ');
          const transitionDurations = (styles[`${transitionProp}Duration`] || '').split(', ');
          const transitionTimeout = getTimeout(transitionDelays, transitionDurations);
          const animationDelays = (styles[`${animationProp}Delay`] || '').split(', ');
          const animationDurations = (styles[`${animationProp}Duration`] || '').split(', ');
          const animationTimeout = getTimeout(animationDelays, animationDurations);

          let type;
          let timeout = 0;
          let propCount = 0;
          /* istanbul ignore if */
          if (expectedType === TRANSITION) {
            if (transitionTimeout > 0) {
              type = TRANSITION;
              timeout = transitionTimeout;
              propCount = transitionDurations.length;
            }
          } else if (expectedType === ANIMATION) {
            if (animationTimeout > 0) {
              type = ANIMATION;
              timeout = animationTimeout;
              propCount = animationDurations.length;
            }
          } else {
            timeout = Math.max(transitionTimeout, animationTimeout);
            type = timeout > 0
              ? transitionTimeout > animationTimeout
                ? TRANSITION
                : ANIMATION
              : null;
            propCount = type
              ? type === TRANSITION
                ? transitionDurations.length
                : animationDurations.length
              : 0;
          }
          const hasTransform =    type === TRANSITION
    && transformRE.test(styles[`${transitionProp}Property`]);
          return {
            type,
            timeout,
            propCount,
            hasTransform
          };
        }

        function getTimeout(delays, durations) {
          /* istanbul ignore next */
          while (delays.length < durations.length) {
            delays = delays.concat(delays);
          }

          return Math.max.apply(null, durations.map((d, i) => toMs(d) + toMs(delays[i])));
        }

        // Old versions of Chromium (below 61.0.3163.100) formats floating pointer numbers
        // in a locale-dependent way, using a comma instead of a dot.
        // If comma is not replaced with a dot, the input will be rounded down (i.e. acting
        // as a floor function) causing unexpected behaviors
        function toMs(s) {
          return Number(s.slice(0, -1).replace(',', '.')) * 1000;
        }

        /*  */

        function enter(vnode, toggleDisplay) {
          const el = vnode.elm;

          // call leave callback now
          if (isDef(el._leaveCb)) {
            el._leaveCb.cancelled = true;
            el._leaveCb();
          }

          const data = resolveTransition(vnode.data.transition);
          if (isUndef(data)) {
            return;
          }

          /* istanbul ignore if */
          if (isDef(el._enterCb) || el.nodeType !== 1) {
            return;
          }

          const { css } = data;
          const { type } = data;
          const { enterClass } = data;
          const { enterToClass } = data;
          const { enterActiveClass } = data;
          const { appearClass } = data;
          const { appearToClass } = data;
          const { appearActiveClass } = data;
          const { beforeEnter } = data;
          const { enter } = data;
          const { afterEnter } = data;
          const { enterCancelled } = data;
          const { beforeAppear } = data;
          const { appear } = data;
          const { afterAppear } = data;
          const { appearCancelled } = data;
          const { duration } = data;

          // activeInstance will always be the <transition> component managing this
          // transition. One edge case to check is when the <transition> is placed
          // as the root node of a child component. In that case we need to check
          // <transition>'s parent for appear check.
          let context = activeInstance;
          let transitionNode = activeInstance.$vnode;
          while (transitionNode && transitionNode.parent) {
            context = transitionNode.context;
            transitionNode = transitionNode.parent;
          }

          const isAppear = !context._isMounted || !vnode.isRootInsert;

          if (isAppear && !appear && appear !== '') {
            return;
          }

          const startClass = isAppear && appearClass
            ? appearClass
            : enterClass;
          const activeClass = isAppear && appearActiveClass
            ? appearActiveClass
            : enterActiveClass;
          const toClass = isAppear && appearToClass
            ? appearToClass
            : enterToClass;

          const beforeEnterHook = isAppear
            ? (beforeAppear || beforeEnter)
            : beforeEnter;
          const enterHook = isAppear
            ? (typeof appear === 'function' ? appear : enter)
            : enter;
          const afterEnterHook = isAppear
            ? (afterAppear || afterEnter)
            : afterEnter;
          const enterCancelledHook = isAppear
            ? (appearCancelled || enterCancelled)
            : enterCancelled;

          const explicitEnterDuration = toNumber(isObject(duration)
            ? duration.enter
            : duration);

          if (true && explicitEnterDuration != null) {
            checkDuration(explicitEnterDuration, 'enter', vnode);
          }

          const expectsCSS = css !== false && !isIE9;
          const userWantsControl = getHookArgumentsLength(enterHook);

          var cb = el._enterCb = once(() => {
            if (expectsCSS) {
              removeTransitionClass(el, toClass);
              removeTransitionClass(el, activeClass);
            }
            if (cb.cancelled) {
              if (expectsCSS) {
                removeTransitionClass(el, startClass);
              }
              enterCancelledHook && enterCancelledHook(el);
            } else {
              afterEnterHook && afterEnterHook(el);
            }
            el._enterCb = null;
          });

          if (!vnode.data.show) {
            // remove pending leave element on enter by injecting an insert hook
            mergeVNodeHook(vnode, 'insert', () => {
              const parent = el.parentNode;
              const pendingNode = parent && parent._pending && parent._pending[vnode.key];
              if (pendingNode
        && pendingNode.tag === vnode.tag
        && pendingNode.elm._leaveCb
              ) {
                pendingNode.elm._leaveCb();
              }
              enterHook && enterHook(el, cb);
            });
          }

          // start enter transition
          beforeEnterHook && beforeEnterHook(el);
          if (expectsCSS) {
            addTransitionClass(el, startClass);
            addTransitionClass(el, activeClass);
            nextFrame(() => {
              removeTransitionClass(el, startClass);
              if (!cb.cancelled) {
                addTransitionClass(el, toClass);
                if (!userWantsControl) {
                  if (isValidDuration(explicitEnterDuration)) {
                    setTimeout(cb, explicitEnterDuration);
                  } else {
                    whenTransitionEnds(el, type, cb);
                  }
                }
              }
            });
          }

          if (vnode.data.show) {
            toggleDisplay && toggleDisplay();
            enterHook && enterHook(el, cb);
          }

          if (!expectsCSS && !userWantsControl) {
            cb();
          }
        }

        function leave(vnode, rm) {
          const el = vnode.elm;

          // call enter callback now
          if (isDef(el._enterCb)) {
            el._enterCb.cancelled = true;
            el._enterCb();
          }

          const data = resolveTransition(vnode.data.transition);
          if (isUndef(data) || el.nodeType !== 1) {
            return rm();
          }

          /* istanbul ignore if */
          if (isDef(el._leaveCb)) {
            return;
          }

          const { css } = data;
          const { type } = data;
          const { leaveClass } = data;
          const { leaveToClass } = data;
          const { leaveActiveClass } = data;
          const { beforeLeave } = data;
          const { leave } = data;
          const { afterLeave } = data;
          const { leaveCancelled } = data;
          const { delayLeave } = data;
          const { duration } = data;

          const expectsCSS = css !== false && !isIE9;
          const userWantsControl = getHookArgumentsLength(leave);

          const explicitLeaveDuration = toNumber(isObject(duration)
            ? duration.leave
            : duration);

          if (true && isDef(explicitLeaveDuration)) {
            checkDuration(explicitLeaveDuration, 'leave', vnode);
          }

          var cb = el._leaveCb = once(() => {
            if (el.parentNode && el.parentNode._pending) {
              el.parentNode._pending[vnode.key] = null;
            }
            if (expectsCSS) {
              removeTransitionClass(el, leaveToClass);
              removeTransitionClass(el, leaveActiveClass);
            }
            if (cb.cancelled) {
              if (expectsCSS) {
                removeTransitionClass(el, leaveClass);
              }
              leaveCancelled && leaveCancelled(el);
            } else {
              rm();
              afterLeave && afterLeave(el);
            }
            el._leaveCb = null;
          });

          if (delayLeave) {
            delayLeave(performLeave);
          } else {
            performLeave();
          }

          function performLeave() {
            // the delayed leave may have already been cancelled
            if (cb.cancelled) {
              return;
            }
            // record leaving element
            if (!vnode.data.show && el.parentNode) {
              (el.parentNode._pending || (el.parentNode._pending = {}))[(vnode.key)] = vnode;
            }
            beforeLeave && beforeLeave(el);
            if (expectsCSS) {
              addTransitionClass(el, leaveClass);
              addTransitionClass(el, leaveActiveClass);
              nextFrame(() => {
                removeTransitionClass(el, leaveClass);
                if (!cb.cancelled) {
                  addTransitionClass(el, leaveToClass);
                  if (!userWantsControl) {
                    if (isValidDuration(explicitLeaveDuration)) {
                      setTimeout(cb, explicitLeaveDuration);
                    } else {
                      whenTransitionEnds(el, type, cb);
                    }
                  }
                }
              });
            }
            leave && leave(el, cb);
            if (!expectsCSS && !userWantsControl) {
              cb();
            }
          }
        }

        // only used in dev mode
        function checkDuration(val, name, vnode) {
          if (typeof val !== 'number') {
            warn(
              `<transition> explicit ${name} duration is not a valid number - `
      + `got ${JSON.stringify(val)}.`,
              vnode.context
            );
          } else if (isNaN(val)) {
            warn(
              `<transition> explicit ${name} duration is NaN - `
      + 'the duration expression might be incorrect.',
              vnode.context
            );
          }
        }

        function isValidDuration(val) {
          return typeof val === 'number' && !isNaN(val);
        }

        /**
 * Normalize a transition hook's argument length. The hook may be:
 * - a merged hook (invoker) with the original in .fns
 * - a wrapped component method (check ._length)
 * - a plain function (.length)
 */
        function getHookArgumentsLength(fn) {
          if (isUndef(fn)) {
            return false;
          }
          const invokerFns = fn.fns;
          if (isDef(invokerFns)) {
            // invoker
            return getHookArgumentsLength(Array.isArray(invokerFns)
              ? invokerFns[0]
              : invokerFns);
          }
          return (fn._length || fn.length) > 1;
        }

        function _enter(_, vnode) {
          if (vnode.data.show !== true) {
            enter(vnode);
          }
        }

        const transition = inBrowser ? {
          create: _enter,
          activate: _enter,
          remove: function remove$$1(vnode, rm) {
            /* istanbul ignore else */
            if (vnode.data.show !== true) {
              leave(vnode, rm);
            } else {
              rm();
            }
          }
        } : {};

        const platformModules = [
          attrs,
          klass,
          events,
          domProps,
          style,
          transition
        ];

        /*  */

        // the directive module should be applied last, after all
        // built-in modules have been applied.
        const modules = platformModules.concat(baseModules);

        const patch = createPatchFunction({ nodeOps, modules });

        /**
 * Not type checking this file because flow doesn't like attaching
 * properties to Elements.
 */

        /* istanbul ignore if */
        if (isIE9) {
          // http://www.matts411.com/post/internet-explorer-9-oninput/
          document.addEventListener('selectionchange', () => {
            const el = document.activeElement;
            if (el && el.vmodel) {
              trigger(el, 'input');
            }
          });
        }

        var directive = {
          inserted: function inserted(el, binding, vnode, oldVnode) {
            if (vnode.tag === 'select') {
              // #6903
              if (oldVnode.elm && !oldVnode.elm._vOptions) {
                mergeVNodeHook(vnode, 'postpatch', () => {
                  directive.componentUpdated(el, binding, vnode);
                });
              } else {
                setSelected(el, binding, vnode.context);
              }
              el._vOptions = [].map.call(el.options, getValue);
            } else if (vnode.tag === 'textarea' || isTextInputType(el.type)) {
              el._vModifiers = binding.modifiers;
              if (!binding.modifiers.lazy) {
                el.addEventListener('compositionstart', onCompositionStart);
                el.addEventListener('compositionend', onCompositionEnd);
                // Safari < 10.2 & UIWebView doesn't fire compositionend when
                // switching focus before confirming composition choice
                // this also fixes the issue where some browsers e.g. iOS Chrome
                // fires "change" instead of "input" on autocomplete.
                el.addEventListener('change', onCompositionEnd);
                /* istanbul ignore if */
                if (isIE9) {
                  el.vmodel = true;
                }
              }
            }
          },

          componentUpdated: function componentUpdated(el, binding, vnode) {
            if (vnode.tag === 'select') {
              setSelected(el, binding, vnode.context);
              // in case the options rendered by v-for have changed,
              // it's possible that the value is out-of-sync with the rendered options.
              // detect such cases and filter out values that no longer has a matching
              // option in the DOM.
              const prevOptions = el._vOptions;
              const curOptions = el._vOptions = [].map.call(el.options, getValue);
              if (curOptions.some((o, i) => !looseEqual(o, prevOptions[i]))) {
                // trigger change event if
                // no matching option found for at least one value
                const needReset = el.multiple
                  ? binding.value.some(v => hasNoMatchingOption(v, curOptions))
                  : binding.value !== binding.oldValue && hasNoMatchingOption(binding.value, curOptions);
                if (needReset) {
                  trigger(el, 'change');
                }
              }
            }
          }
        };

        function setSelected(el, binding, vm) {
          actuallySetSelected(el, binding, vm);
          /* istanbul ignore if */
          if (isIE || isEdge) {
            setTimeout(() => {
              actuallySetSelected(el, binding, vm);
            }, 0);
          }
        }

        function actuallySetSelected(el, binding, vm) {
          const { value } = binding;
          const isMultiple = el.multiple;
          if (isMultiple && !Array.isArray(value)) {
            true && warn(
              `<select multiple v-model="${binding.expression}"> `
      + `expects an Array value for its binding, but got ${Object.prototype.toString.call(value).slice(8, -1)}`,
              vm
            );
            return;
          }
          let selected; let option;
          for (let i = 0, l = el.options.length; i < l; i++) {
            option = el.options[i];
            if (isMultiple) {
              selected = looseIndexOf(value, getValue(option)) > -1;
              if (option.selected !== selected) {
                option.selected = selected;
              }
            } else {
              if (looseEqual(getValue(option), value)) {
                if (el.selectedIndex !== i) {
                  el.selectedIndex = i;
                }
                return;
              }
            }
          }
          if (!isMultiple) {
            el.selectedIndex = -1;
          }
        }

        function hasNoMatchingOption(value, options) {
          return options.every(o => !looseEqual(o, value));
        }

        function getValue(option) {
          return '_value' in option
            ? option._value
            : option.value;
        }

        function onCompositionStart(e) {
          e.target.composing = true;
        }

        function onCompositionEnd(e) {
          // prevent triggering an input event for no reason
          if (!e.target.composing) {
            return;
          }
          e.target.composing = false;
          trigger(e.target, 'input');
        }

        function trigger(el, type) {
          const e = document.createEvent('HTMLEvents');
          e.initEvent(type, true, true);
          el.dispatchEvent(e);
        }

        /*  */

        // recursively search for possible transition defined inside the component root
        function locateNode(vnode) {
          return vnode.componentInstance && (!vnode.data || !vnode.data.transition)
            ? locateNode(vnode.componentInstance._vnode)
            : vnode;
        }

        const show = {
          bind: function bind(el, ref, vnode) {
            const { value } = ref;

            vnode = locateNode(vnode);
            const transition$$1 = vnode.data && vnode.data.transition;
            const originalDisplay = el.__vOriginalDisplay =      el.style.display === 'none' ? '' : el.style.display;
            if (value && transition$$1) {
              vnode.data.show = true;
              enter(vnode, () => {
                el.style.display = originalDisplay;
              });
            } else {
              el.style.display = value ? originalDisplay : 'none';
            }
          },

          update: function update(el, ref, vnode) {
            const { value } = ref;
            const { oldValue } = ref;

            /* istanbul ignore if */
            if (!value === !oldValue) {
              return;
            }
            vnode = locateNode(vnode);
            const transition$$1 = vnode.data && vnode.data.transition;
            if (transition$$1) {
              vnode.data.show = true;
              if (value) {
                enter(vnode, () => {
                  el.style.display = el.__vOriginalDisplay;
                });
              } else {
                leave(vnode, () => {
                  el.style.display = 'none';
                });
              }
            } else {
              el.style.display = value ? el.__vOriginalDisplay : 'none';
            }
          },

          unbind: function unbind(
            el,
            binding,
            vnode,
            oldVnode,
            isDestroy
          ) {
            if (!isDestroy) {
              el.style.display = el.__vOriginalDisplay;
            }
          }
        };

        const platformDirectives = {
          model: directive,
          show
        };

        /*  */

        const transitionProps = {
          name: String,
          appear: Boolean,
          css: Boolean,
          mode: String,
          type: String,
          enterClass: String,
          leaveClass: String,
          enterToClass: String,
          leaveToClass: String,
          enterActiveClass: String,
          leaveActiveClass: String,
          appearClass: String,
          appearActiveClass: String,
          appearToClass: String,
          duration: [Number, String, Object]
        };

        // in case the child is also an abstract component, e.g. <keep-alive>
        // we want to recursively retrieve the real component to be rendered
        function getRealChild(vnode) {
          const compOptions = vnode && vnode.componentOptions;
          if (compOptions && compOptions.Ctor.options.abstract) {
            return getRealChild(getFirstComponentChild(compOptions.children));
          }
          return vnode;
        }

        function extractTransitionData(comp) {
          const data = {};
          const options = comp.$options;
          // props
          for (const key in options.propsData) {
            data[key] = comp[key];
          }
          // events.
          // extract listeners and pass them directly to the transition methods
          const listeners = options._parentListeners;
          for (const key$1 in listeners) {
            data[camelize(key$1)] = listeners[key$1];
          }
          return data;
        }

        function placeholder(h, rawChild) {
          if (/\d-keep-alive$/.test(rawChild.tag)) {
            return h('keep-alive', {
              props: rawChild.componentOptions.propsData
            });
          }
        }

        function hasParentTransition(vnode) {
          while ((vnode = vnode.parent)) {
            if (vnode.data.transition) {
              return true;
            }
          }
        }

        function isSameChild(child, oldChild) {
          return oldChild.key === child.key && oldChild.tag === child.tag;
        }

        const isNotTextNode = function (c) {
          return c.tag || isAsyncPlaceholder(c);
        };

        const isVShowDirective = function (d) {
          return d.name === 'show';
        };

        const Transition = {
          name: 'transition',
          props: transitionProps,
          abstract: true,

          render: function render(h) {
            const this$1 = this;

            let children = this.$slots.default;
            if (!children) {
              return;
            }

            // filter out text nodes (possible whitespaces)
            children = children.filter(isNotTextNode);
            /* istanbul ignore if */
            if (!children.length) {
              return;
            }

            // warn multiple elements
            if (true && children.length > 1) {
              warn(
                '<transition> can only be used on a single element. Use '
        + '<transition-group> for lists.',
                this.$parent
              );
            }

            const { mode } = this;

            // warn invalid mode
            if (true
      && mode && mode !== 'in-out' && mode !== 'out-in'
            ) {
              warn(
                `invalid <transition> mode: ${mode}`,
                this.$parent
              );
            }

            const rawChild = children[0];

            // if this is a component root node and the component's
            // parent container node also has transition, skip.
            if (hasParentTransition(this.$vnode)) {
              return rawChild;
            }

            // apply transition data to child
            // use getRealChild() to ignore abstract components e.g. keep-alive
            const child = getRealChild(rawChild);
            /* istanbul ignore if */
            if (!child) {
              return rawChild;
            }

            if (this._leaving) {
              return placeholder(h, rawChild);
            }

            // ensure a key that is unique to the vnode type and to this transition
            // component instance. This key will be used to remove pending leaving nodes
            // during entering.
            const id = `__transition-${this._uid}-`;
            child.key = child.key == null
              ? child.isComment
                ? `${id}comment`
                : id + child.tag
              : isPrimitive(child.key)
                ? (String(child.key).indexOf(id) === 0 ? child.key : id + child.key)
                : child.key;

            const data = (child.data || (child.data = {})).transition = extractTransitionData(this);
            const oldRawChild = this._vnode;
            const oldChild = getRealChild(oldRawChild);

            // mark v-show
            // so that the transition module can hand over the control to the directive
            if (child.data.directives && child.data.directives.some(isVShowDirective)) {
              child.data.show = true;
            }

            if (
              oldChild
      && oldChild.data
      && !isSameChild(child, oldChild)
      && !isAsyncPlaceholder(oldChild)
      // #6687 component root is a comment node
      && !(oldChild.componentInstance && oldChild.componentInstance._vnode.isComment)
            ) {
              // replace old child transition data with fresh one
              // important for dynamic transitions!
              const oldData = oldChild.data.transition = extend({}, data);
              // handle transition mode
              if (mode === 'out-in') {
                // return placeholder node and queue update when leave finishes
                this._leaving = true;
                mergeVNodeHook(oldData, 'afterLeave', () => {
                  this$1._leaving = false;
                  this$1.$forceUpdate();
                });
                return placeholder(h, rawChild);
              } if (mode === 'in-out') {
                if (isAsyncPlaceholder(child)) {
                  return oldRawChild;
                }
                let delayedLeave;
                const performLeave = function () {
                  delayedLeave();
                };
                mergeVNodeHook(data, 'afterEnter', performLeave);
                mergeVNodeHook(data, 'enterCancelled', performLeave);
                mergeVNodeHook(oldData, 'delayLeave', (leave) => {
                  delayedLeave = leave;
                });
              }
            }

            return rawChild;
          }
        };

        /*  */

        const props = extend({
          tag: String,
          moveClass: String
        }, transitionProps);

        delete props.mode;

        const TransitionGroup = {
          props,

          beforeMount: function beforeMount() {
            const this$1 = this;

            const update = this._update;
            this._update = function (vnode, hydrating) {
              const restoreActiveInstance = setActiveInstance(this$1);
              // force removing pass
              this$1.__patch__(
                this$1._vnode,
                this$1.kept,
                false, // hydrating
                true // removeOnly (!important, avoids unnecessary moves)
              );
              this$1._vnode = this$1.kept;
              restoreActiveInstance();
              update.call(this$1, vnode, hydrating);
            };
          },

          render: function render(h) {
            const tag = this.tag || this.$vnode.data.tag || 'span';
            const map = Object.create(null);
            const prevChildren = this.prevChildren = this.children;
            const rawChildren = this.$slots.default || [];
            const children = this.children = [];
            const transitionData = extractTransitionData(this);

            for (let i = 0; i < rawChildren.length; i++) {
              const c = rawChildren[i];
              if (c.tag) {
                if (c.key != null && String(c.key).indexOf('__vlist') !== 0) {
                  children.push(c);
                  map[c.key] = c
                  ;(c.data || (c.data = {})).transition = transitionData;
                } else if (true) {
                  const opts = c.componentOptions;
                  const name = opts ? (opts.Ctor.options.name || opts.tag || '') : c.tag;
                  warn((`<transition-group> children must be keyed: <${name}>`));
                }
              }
            }

            if (prevChildren) {
              const kept = [];
              const removed = [];
              for (let i$1 = 0; i$1 < prevChildren.length; i$1++) {
                const c$1 = prevChildren[i$1];
                c$1.data.transition = transitionData;
                c$1.data.pos = c$1.elm.getBoundingClientRect();
                if (map[c$1.key]) {
                  kept.push(c$1);
                } else {
                  removed.push(c$1);
                }
              }
              this.kept = h(tag, null, kept);
              this.removed = removed;
            }

            return h(tag, null, children);
          },

          updated: function updated() {
            const children = this.prevChildren;
            const moveClass = this.moveClass || (`${this.name || 'v'}-move`);
            if (!children.length || !this.hasMove(children[0].elm, moveClass)) {
              return;
            }

            // we divide the work into three loops to avoid mixing DOM reads and writes
            // in each iteration - which helps prevent layout thrashing.
            children.forEach(callPendingCbs);
            children.forEach(recordPosition);
            children.forEach(applyTranslation);

            // force reflow to put everything in position
            // assign to this to avoid being removed in tree-shaking
            // $flow-disable-line
            this._reflow = document.body.offsetHeight;

            children.forEach((c) => {
              if (c.data.moved) {
                const el = c.elm;
                const s = el.style;
                addTransitionClass(el, moveClass);
                s.transform = s.WebkitTransform = s.transitionDuration = '';
                el.addEventListener(transitionEndEvent, el._moveCb = function cb(e) {
                  if (e && e.target !== el) {
                    return;
                  }
                  if (!e || /transform$/.test(e.propertyName)) {
                    el.removeEventListener(transitionEndEvent, cb);
                    el._moveCb = null;
                    removeTransitionClass(el, moveClass);
                  }
                });
              }
            });
          },

          methods: {
            hasMove: function hasMove(el, moveClass) {
              /* istanbul ignore if */
              if (!hasTransition) {
                return false;
              }
              /* istanbul ignore if */
              if (this._hasMove) {
                return this._hasMove;
              }
              // Detect whether an element with the move class applied has
              // CSS transitions. Since the element may be inside an entering
              // transition at this very moment, we make a clone of it and remove
              // all other transition classes applied to ensure only the move class
              // is applied.
              const clone = el.cloneNode();
              if (el._transitionClasses) {
                el._transitionClasses.forEach((cls) => {
                  removeClass(clone, cls);
                });
              }
              addClass(clone, moveClass);
              clone.style.display = 'none';
              this.$el.appendChild(clone);
              const info = getTransitionInfo(clone);
              this.$el.removeChild(clone);
              return (this._hasMove = info.hasTransform);
            }
          }
        };

        function callPendingCbs(c) {
          /* istanbul ignore if */
          if (c.elm._moveCb) {
            c.elm._moveCb();
          }
          /* istanbul ignore if */
          if (c.elm._enterCb) {
            c.elm._enterCb();
          }
        }

        function recordPosition(c) {
          c.data.newPos = c.elm.getBoundingClientRect();
        }

        function applyTranslation(c) {
          const oldPos = c.data.pos;
          const { newPos } = c.data;
          const dx = oldPos.left - newPos.left;
          const dy = oldPos.top - newPos.top;
          if (dx || dy) {
            c.data.moved = true;
            const s = c.elm.style;
            s.transform = s.WebkitTransform = `translate(${dx}px,${dy}px)`;
            s.transitionDuration = '0s';
          }
        }

        const platformComponents = {
          Transition,
          TransitionGroup
        };

        /*  */

        // install platform specific utils
        Vue.config.mustUseProp = mustUseProp;
        Vue.config.isReservedTag = isReservedTag;
        Vue.config.isReservedAttr = isReservedAttr;
        Vue.config.getTagNamespace = getTagNamespace;
        Vue.config.isUnknownElement = isUnknownElement;

        // install platform runtime directives & components
        extend(Vue.options.directives, platformDirectives);
        extend(Vue.options.components, platformComponents);

        // install platform patch function
        Vue.prototype.__patch__ = inBrowser ? patch : noop;

        // public mount method
        Vue.prototype.$mount = function (
          el,
          hydrating
        ) {
          el = el && inBrowser ? query(el) : undefined;
          return mountComponent(this, el, hydrating);
        };

        // devtools global hook
        /* istanbul ignore next */
        if (inBrowser) {
          setTimeout(() => {
            if (config.devtools) {
              if (devtools) {
                devtools.emit('init', Vue);
              } else if (
                true
              ) {
                console[console.info ? 'info' : 'log']('Download the Vue Devtools extension for a better development experience:\n'
          + 'https://github.com/vuejs/vue-devtools');
              }
            }
            if (true
      && config.productionTip !== false
      && typeof console !== 'undefined'
            ) {
              console[console.info ? 'info' : 'log']('You are running Vue in development mode.\n'
        + 'Make sure to turn on production mode when deploying for production.\n'
        + 'See more tips at https://vuejs.org/guide/deployment.html');
            }
          }, 0);
        }

        /*  */

        /* harmony default export */ const __WEBPACK_DEFAULT_EXPORT__ = (Vue);
        /***/ })

      /******/ 	});
    /************************************************************************/
    /******/ 	// The module cache
    /******/ 	const __webpack_module_cache__ = {};
    /******/
    /******/ 	// The require function
    /******/ 	function __webpack_require__(moduleId) {
      /******/ 		// Check if module is in cache
      /******/ 		const cachedModule = __webpack_module_cache__[moduleId];
      /******/ 		if (cachedModule !== undefined) {
        /******/ 			return cachedModule.exports;
        /******/ 		}
      /******/ 		// Create a new module (and put it into the cache)
      /******/ 		const module = __webpack_module_cache__[moduleId] = {
        /******/ 			// no module.id needed
        /******/ 			// no module.loaded needed
        /******/ 			exports: {}
        /******/ 		};
      /******/
      /******/ 		// Execute the module function
      /******/ 		__webpack_modules__[moduleId](module, module.exports, __webpack_require__);
      /******/
      /******/ 		// Return the exports of the module
      /******/ 		return module.exports;
      /******/ 	}
    /******/
    /************************************************************************/
    /******/ 	/* webpack/runtime/compat get default export */
    /******/ 	(() => {
      /******/ 		// getDefaultExport function for compatibility with non-harmony modules
      /******/ 		__webpack_require__.n = (module) => {
        /******/ 			const getter = module && module.__esModule
        /******/ 				? () => (module.default)
        /******/ 				: () => (module);
        /******/ 			__webpack_require__.d(getter, { a: getter });
        /******/ 			return getter;
        /******/ 		};
      /******/ 	})();
    /******/
    /******/ 	/* webpack/runtime/define property getters */
    /******/ 	(() => {
      /******/ 		// define getter functions for harmony exports
      /******/ 		__webpack_require__.d = (exports, definition) => {
        /******/ 			for (const key in definition) {
          /******/ 				if (__webpack_require__.o(definition, key) && !__webpack_require__.o(exports, key)) {
            /******/ 					Object.defineProperty(exports, key, { enumerable: true, get: definition[key] });
            /******/ 				}
          /******/ 			}
        /******/ 		};
      /******/ 	})();
    /******/
    /******/ 	/* webpack/runtime/hasOwnProperty shorthand */
    /******/ 	(() => {
      /******/ 		__webpack_require__.o = (obj, prop) => (Object.prototype.hasOwnProperty.call(obj, prop));
      /******/ 	})();
    /******/
    /******/ 	/* webpack/runtime/make namespace object */
    /******/ 	(() => {
      /******/ 		// define __esModule on exports
      /******/ 		__webpack_require__.r = (exports) => {
        /******/ 			if (typeof Symbol !== 'undefined' && Symbol.toStringTag) {
          /******/ 				Object.defineProperty(exports, Symbol.toStringTag, { value: 'Module' });
          /******/ 			}
        /******/ 			Object.defineProperty(exports, '__esModule', { value: true });
        /******/ 		};
      /******/ 	})();
    /******/
    /************************************************************************/
    const __webpack_exports__ = {};
    // This entry need to be wrapped in an IIFE because it need to be in strict mode.
    (() => {
      'use strict';
      /*! **********************!*\
  !*** ./src/index.ts ***!
  \**********************/
      __webpack_require__.r(__webpack_exports__);
      /* harmony export */ __webpack_require__.d(__webpack_exports__, {
        /* harmony export */   default: () => (__WEBPACK_DEFAULT_EXPORT__)
        /* harmony export */ });
      /* harmony import */ const _blueking_log__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! @blueking/log */ './node_modules/@blueking/log/dist/index.js');
      /* harmony import */ const _blueking_log__WEBPACK_IMPORTED_MODULE_0___default = /* #__PURE__*/__webpack_require__.n(_blueking_log__WEBPACK_IMPORTED_MODULE_0__);
      /* harmony import */ const vue__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! vue */ './node_modules/vue/dist/vue.runtime.esm.js');
      /*
  * Tencent is pleased to support the open source community by making
  * 蓝鲸智云PaaS平台社区版 (BlueKing PaaS Community Edition) available.
  *
  * Copyright (C) 2021 THL A29 Limited, a Tencent company.  All rights reserved.
  *
  * 蓝鲸智云PaaS平台社区版 (BlueKing PaaS Community Edition) is licensed under the MIT License.
  *
  * License for 蓝鲸智云PaaS平台社区版 (BlueKing PaaS Community Edition):
  *
  * ---------------------------------------------------
  * Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
  * documentation files (the "Software"), to deal in the Software without restriction, including without limitation
  * the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and
  * to permit persons to whom the Software is furnished to do so, subject to the following conditions:
  *
  * The above copyright notice and this permission notice shall be included in all copies or substantial portions of
  * the Software.
  *
  * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
  * THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
  * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
  * CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
  * IN THE SOFTWARE.
  */


      /* harmony default export */ const __WEBPACK_DEFAULT_EXPORT__ = ({
        Vue2: vue__WEBPACK_IMPORTED_MODULE_1__.default,
        Log: (_blueking_log__WEBPACK_IMPORTED_MODULE_0___default())
      });
    })();

    /******/ 	return __webpack_exports__;
    /******/ })()));
// # sourceMappingURL=index.js.map
