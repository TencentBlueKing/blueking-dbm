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

      /***/ './node_modules/bk-magic-vue/lib/locale/index.js':
      /*! *******************************************************!*\
  !*** ./node_modules/bk-magic-vue/lib/locale/index.js ***!
  \*******************************************************/
      /***/ (function (__unused_webpack_module, exports, __webpack_require__) {
        (function (global, factory) {
          true ? factory(exports, __webpack_require__(/*! vue */ './node_modules/vue/dist/vue.runtime.esm.js'), __webpack_require__(/*! bk-magic-vue/lib/locale/lang */ './node_modules/bk-magic-vue/lib/locale/lang/index.js'))
            : 0;
        }(this, (exports, Vue, bkLang) => {
          'use strict';

          Vue = Vue && Vue.hasOwnProperty('default') ? Vue.default : Vue;
          bkLang = bkLang && bkLang.hasOwnProperty('default') ? bkLang.default : bkLang;

          const _defined = function (it) {
            if (it == undefined) throw TypeError(`Can't call method on  ${it}`);
            return it;
          };

          const _toObject = function (it) {
            return Object(_defined(it));
          };

          const { hasOwnProperty } = {};
          const _has = function (it, key) {
            return hasOwnProperty.call(it, key);
          };

          const { toString } = {};
          const _cof = function (it) {
            return toString.call(it).slice(8, -1);
          };

          const _iobject = Object('z').propertyIsEnumerable(0) ? Object : function (it) {
            return _cof(it) == 'String' ? it.split('') : Object(it);
          };

          const _toIobject = function (it) {
            return _iobject(_defined(it));
          };

          const { ceil } = Math;
          const { floor } = Math;
          const _toInteger = function (it) {
            return isNaN(it = +it) ? 0 : (it > 0 ? floor : ceil)(it);
          };

          const { min } = Math;
          const _toLength = function (it) {
            return it > 0 ? min(_toInteger(it), 0x1fffffffffffff) : 0;
          };

          const { max } = Math;
          const min$1 = Math.min;
          const _toAbsoluteIndex = function (index, length) {
            index = _toInteger(index);
            return index < 0 ? max(index + length, 0) : min$1(index, length);
          };

          const _arrayIncludes = function (IS_INCLUDES) {
            return function ($this, el, fromIndex) {
              const O = _toIobject($this);
              const length = _toLength(O.length);
              let index = _toAbsoluteIndex(fromIndex, length);
              let value;
              if (IS_INCLUDES && el != el) while (length > index) {
                value = O[index++];
                if (value != value) return true;
              } else for (;length > index; index++) if (IS_INCLUDES || index in O) {
                if (O[index] === el) return IS_INCLUDES || index || 0;
              } return !IS_INCLUDES && -1;
            };
          };

          function createCommonjsModule(fn, module) {
  	return module = { exports: {} }, fn(module, module.exports), module.exports;
          }

          const _core = createCommonjsModule((module) => {
            const core = module.exports = { version: '2.6.12' };
            if (typeof __e === 'number') __e = core;
          });
          const _core_1 = _core.version;

          const _global = createCommonjsModule((module) => {
            const global = module.exports = typeof window !== 'undefined' && window.Math == Math
              ? window : typeof self !== 'undefined' && self.Math == Math ? self
              : Function('return this')();
            if (typeof __g === 'number') __g = global;
          });

          const _library = true;

          const _shared = createCommonjsModule((module) => {
            const SHARED = '__core-js_shared__';
            const store = _global[SHARED] || (_global[SHARED] = {});
            (module.exports = function (key, value) {
              return store[key] || (store[key] = value !== undefined ? value : {});
            })('versions', []).push({
              version: _core.version,
              mode: 'pure',
              copyright: '© 2020 Denis Pushkarev (zloirock.ru)'
            });
          });

          let id = 0;
          const px = Math.random();
          const _uid = function (key) {
            return 'Symbol('.concat(key === undefined ? '' : key, ')_', (++id + px).toString(36));
          };

          const shared = _shared('keys');
          const _sharedKey = function (key) {
            return shared[key] || (shared[key] = _uid(key));
          };

          const arrayIndexOf = _arrayIncludes(false);
          const IE_PROTO = _sharedKey('IE_PROTO');
          const _objectKeysInternal = function (object, names) {
            const O = _toIobject(object);
            let i = 0;
            const result = [];
            let key;
            for (key in O) if (key != IE_PROTO) _has(O, key) && result.push(key);
            while (names.length > i) if (_has(O, key = names[i++])) {
              ~arrayIndexOf(result, key) || result.push(key);
            }
            return result;
          };

          const _enumBugKeys = (
            'constructor,hasOwnProperty,isPrototypeOf,propertyIsEnumerable,toLocaleString,toString,valueOf'
          ).split(',');

          const _objectKeys = Object.keys || function keys(O) {
            return _objectKeysInternal(O, _enumBugKeys);
          };

          const _aFunction = function (it) {
            if (typeof it !== 'function') throw TypeError(`${it} is not a function!`);
            return it;
          };

          const _ctx = function (fn, that, length) {
            _aFunction(fn);
            if (that === undefined) return fn;
            switch (length) {
              case 1: return function (a) {
                return fn.call(that, a);
              };
              case 2: return function (a, b) {
                return fn.call(that, a, b);
              };
              case 3: return function (a, b, c) {
                return fn.call(that, a, b, c);
              };
            }
            return function () {
              return fn.apply(that, arguments);
            };
          };

          const _isObject = function (it) {
            return typeof it === 'object' ? it !== null : typeof it === 'function';
          };

          const _anObject = function (it) {
            if (!_isObject(it)) throw TypeError(`${it} is not an object!`);
            return it;
          };

          const _fails = function (exec) {
            try {
              return !!exec();
            } catch (e) {
              return true;
            }
          };

          const _descriptors = !_fails(() => Object.defineProperty({}, 'a', { get() {
            return 7;
          } }).a != 7);

          const { document } = _global;
          const is = _isObject(document) && _isObject(document.createElement);
          const _domCreate = function (it) {
            return is ? document.createElement(it) : {};
          };

          const _ie8DomDefine = !_descriptors && !_fails(() => Object.defineProperty(_domCreate('div'), 'a', { get() {
            return 7;
          } }).a != 7);

          const _toPrimitive = function (it, S) {
            if (!_isObject(it)) return it;
            let fn; let val;
            if (S && typeof (fn = it.toString) === 'function' && !_isObject(val = fn.call(it))) return val;
            if (typeof (fn = it.valueOf) === 'function' && !_isObject(val = fn.call(it))) return val;
            if (!S && typeof (fn = it.toString) === 'function' && !_isObject(val = fn.call(it))) return val;
            throw TypeError('Can\'t convert object to primitive value');
          };

          const dP = Object.defineProperty;
          const f = _descriptors ? Object.defineProperty : function defineProperty(O, P, Attributes) {
            _anObject(O);
            P = _toPrimitive(P, true);
            _anObject(Attributes);
            if (_ie8DomDefine) try {
              return dP(O, P, Attributes);
            } catch (e) {  }
            if ('get' in Attributes || 'set' in Attributes) throw TypeError('Accessors not supported!');
            if ('value' in Attributes) O[P] = Attributes.value;
            return O;
          };
          const _objectDp = {
  	f
          };

          const _propertyDesc = function (bitmap, value) {
            return {
              enumerable: !(bitmap & 1),
              configurable: !(bitmap & 2),
              writable: !(bitmap & 4),
              value
            };
          };

          const _hide = _descriptors ? function (object, key, value) {
            return _objectDp.f(object, key, _propertyDesc(1, value));
          } : function (object, key, value) {
            object[key] = value;
            return object;
          };

          const PROTOTYPE = 'prototype';
          var $export = function (type, name, source) {
            const IS_FORCED = type & $export.F;
            const IS_GLOBAL = type & $export.G;
            const IS_STATIC = type & $export.S;
            const IS_PROTO = type & $export.P;
            const IS_BIND = type & $export.B;
            const IS_WRAP = type & $export.W;
            const exports = IS_GLOBAL ? _core : _core[name] || (_core[name] = {});
            const expProto = exports[PROTOTYPE];
            const target = IS_GLOBAL ? _global : IS_STATIC ? _global[name] : (_global[name] || {})[PROTOTYPE];
            let key; let own; let out;
            if (IS_GLOBAL) source = name;
            for (key in source) {
              own = !IS_FORCED && target && target[key] !== undefined;
              if (own && _has(exports, key)) continue;
              out = own ? target[key] : source[key];
              exports[key] = IS_GLOBAL && typeof target[key] !== 'function' ? source[key]
                : IS_BIND && own ? _ctx(out, _global)
                : IS_WRAP && target[key] == out ? (function (C) {
                  const F = function (a, b, c) {
                    if (this instanceof C) {
                      switch (arguments.length) {
                        case 0: return new C();
                        case 1: return new C(a);
                        case 2: return new C(a, b);
                      } return new C(a, b, c);
                    } return C.apply(this, arguments);
                  };
                  F[PROTOTYPE] = C[PROTOTYPE];
                  return F;
                }(out)) : IS_PROTO && typeof out === 'function' ? _ctx(Function.call, out) : out;
              if (IS_PROTO) {
                (exports.virtual || (exports.virtual = {}))[key] = out;
                if (type & $export.R && expProto && !expProto[key]) _hide(expProto, key, out);
              }
            }
          };
          $export.F = 1;
          $export.G = 2;
          $export.S = 4;
          $export.P = 8;
          $export.B = 16;
          $export.W = 32;
          $export.U = 64;
          $export.R = 128;
          const _export = $export;

          const _objectSap = function (KEY, exec) {
            const fn = (_core.Object || {})[KEY] || Object[KEY];
            const exp = {};
            exp[KEY] = exec(fn);
            _export(_export.S + _export.F * _fails(() => {
              fn(1);
            }), 'Object', exp);
          };

          _objectSap('keys', () => function keys(it) {
            return _objectKeys(_toObject(it));
          });

          const { keys } = _core.Object;

          const keys$1 = keys;

          const IE_PROTO$1 = _sharedKey('IE_PROTO');
          const ObjectProto = Object.prototype;
          const _objectGpo = Object.getPrototypeOf || function (O) {
            O = _toObject(O);
            if (_has(O, IE_PROTO$1)) return O[IE_PROTO$1];
            if (typeof O.constructor === 'function' && O instanceof O.constructor) {
              return O.constructor.prototype;
            } return O instanceof Object ? ObjectProto : null;
          };

          _objectSap('getPrototypeOf', () => function getPrototypeOf(it) {
            return _objectGpo(_toObject(it));
          });

          const { getPrototypeOf } = _core.Object;

          const getPrototypeOf$1 = getPrototypeOf;

          const _redefine = _hide;

          const _meta = createCommonjsModule((module) => {
            const META = _uid('meta');
            const setDesc = _objectDp.f;
            let id = 0;
            const isExtensible = Object.isExtensible || function () {
              return true;
            };
            const FREEZE = !_fails(() => isExtensible(Object.preventExtensions({})));
            const setMeta = function (it) {
              setDesc(it, META, { value: {
                i: `O${++id}`,
                w: {}
              } });
            };
            const fastKey = function (it, create) {
              if (!_isObject(it)) return typeof it === 'symbol' ? it : (typeof it === 'string' ? 'S' : 'P') + it;
              if (!_has(it, META)) {
                if (!isExtensible(it)) return 'F';
                if (!create) return 'E';
                setMeta(it);
              } return it[META].i;
            };
            const getWeak = function (it, create) {
              if (!_has(it, META)) {
                if (!isExtensible(it)) return true;
                if (!create) return false;
                setMeta(it);
              } return it[META].w;
            };
            const onFreeze = function (it) {
              if (FREEZE && meta.NEED && isExtensible(it) && !_has(it, META)) setMeta(it);
              return it;
            };
            var meta = module.exports = {
              KEY: META,
              NEED: false,
              fastKey,
              getWeak,
              onFreeze
            };
          });
          const _meta_1 = _meta.KEY;
          const _meta_2 = _meta.NEED;
          const _meta_3 = _meta.fastKey;
          const _meta_4 = _meta.getWeak;
          const _meta_5 = _meta.onFreeze;

          const _wks = createCommonjsModule((module) => {
            const store = _shared('wks');
            const { Symbol } = _global;
            const USE_SYMBOL = typeof Symbol === 'function';
            const $exports = module.exports = function (name) {
              return store[name] || (store[name] =      USE_SYMBOL && Symbol[name] || (USE_SYMBOL ? Symbol : _uid)(`Symbol.${name}`));
            };
            $exports.store = store;
          });

          const def = _objectDp.f;
          const TAG = _wks('toStringTag');
          const _setToStringTag = function (it, tag, stat) {
            if (it && !_has(it = stat ? it : it.prototype, TAG)) def(it, TAG, { configurable: true, value: tag });
          };

          const f$1 = _wks;
          const _wksExt = {
  	f: f$1
          };

          const defineProperty = _objectDp.f;
          const _wksDefine = function (name) {
            const $Symbol = _core.Symbol || (_core.Symbol =  {});
            if (name.charAt(0) != '_' && !(name in $Symbol)) defineProperty($Symbol, name, { value: _wksExt.f(name) });
          };

          const f$2 = Object.getOwnPropertySymbols;
          const _objectGops = {
  	f: f$2
          };

          const f$3 = {}.propertyIsEnumerable;
          const _objectPie = {
  	f: f$3
          };

          const _enumKeys = function (it) {
            const result = _objectKeys(it);
            const getSymbols = _objectGops.f;
            if (getSymbols) {
              const symbols = getSymbols(it);
              const isEnum = _objectPie.f;
              let i = 0;
              let key;
              while (symbols.length > i) if (isEnum.call(it, key = symbols[i++])) result.push(key);
            } return result;
          };

          const _isArray = Array.isArray || function isArray(arg) {
            return _cof(arg) == 'Array';
          };

          const _objectDps = _descriptors ? Object.defineProperties : function defineProperties(O, Properties) {
            _anObject(O);
            const keys = _objectKeys(Properties);
            const { length } = keys;
            let i = 0;
            let P;
            while (length > i) _objectDp.f(O, P = keys[i++], Properties[P]);
            return O;
          };

          const document$1 = _global.document;
          const _html = document$1 && document$1.documentElement;

          const IE_PROTO$2 = _sharedKey('IE_PROTO');
          const Empty = function () {  };
          const PROTOTYPE$1 = 'prototype';
          var createDict = function () {
            const iframe = _domCreate('iframe');
            let i = _enumBugKeys.length;
            const lt = '<';
            const gt = '>';
            let iframeDocument;
            iframe.style.display = 'none';
            _html.appendChild(iframe);
            iframe.src = 'javascript:';
            iframeDocument = iframe.contentWindow.document;
            iframeDocument.open();
            iframeDocument.write(`${lt}script${gt}document.F=Object${lt}/script${gt}`);
            iframeDocument.close();
            createDict = iframeDocument.F;
            while (i--) delete createDict[PROTOTYPE$1][_enumBugKeys[i]];
            return createDict();
          };
          const _objectCreate = Object.create || function create(O, Properties) {
            let result;
            if (O !== null) {
              Empty[PROTOTYPE$1] = _anObject(O);
              result = new Empty();
              Empty[PROTOTYPE$1] = null;
              result[IE_PROTO$2] = O;
            } else result = createDict();
            return Properties === undefined ? result : _objectDps(result, Properties);
          };

          const hiddenKeys = _enumBugKeys.concat('length', 'prototype');
          const f$4 = Object.getOwnPropertyNames || function getOwnPropertyNames(O) {
            return _objectKeysInternal(O, hiddenKeys);
          };
          const _objectGopn = {
  	f: f$4
          };

          const gOPN = _objectGopn.f;
          const toString$1 = {}.toString;
          const windowNames = typeof window === 'object' && window && Object.getOwnPropertyNames
            ? Object.getOwnPropertyNames(window) : [];
          const getWindowNames = function (it) {
            try {
              return gOPN(it);
            } catch (e) {
              return windowNames.slice();
            }
          };
          const f$5 = function getOwnPropertyNames(it) {
            return windowNames && toString$1.call(it) == '[object Window]' ? getWindowNames(it) : gOPN(_toIobject(it));
          };
          const _objectGopnExt = {
  	f: f$5
          };

          const gOPD = Object.getOwnPropertyDescriptor;
          const f$6 = _descriptors ? gOPD : function getOwnPropertyDescriptor(O, P) {
            O = _toIobject(O);
            P = _toPrimitive(P, true);
            if (_ie8DomDefine) try {
              return gOPD(O, P);
            } catch (e) {  }
            if (_has(O, P)) return _propertyDesc(!_objectPie.f.call(O, P), O[P]);
          };
          const _objectGopd = {
  	f: f$6
          };

          const META = _meta.KEY;
          const gOPD$1 = _objectGopd.f;
          const dP$1 = _objectDp.f;
          const gOPN$1 = _objectGopnExt.f;
          let $Symbol = _global.Symbol;
          const $JSON = _global.JSON;
          const _stringify = $JSON && $JSON.stringify;
          const PROTOTYPE$2 = 'prototype';
          const HIDDEN = _wks('_hidden');
          const TO_PRIMITIVE = _wks('toPrimitive');
          const isEnum = {}.propertyIsEnumerable;
          const SymbolRegistry = _shared('symbol-registry');
          const AllSymbols = _shared('symbols');
          const OPSymbols = _shared('op-symbols');
          const ObjectProto$1 = Object[PROTOTYPE$2];
          const USE_NATIVE = typeof $Symbol === 'function' && !!_objectGops.f;
          const { QObject } = _global;
          let setter = !QObject || !QObject[PROTOTYPE$2] || !QObject[PROTOTYPE$2].findChild;
          const setSymbolDesc = _descriptors && _fails(() => _objectCreate(dP$1({}, 'a', {
            get() {
              return dP$1(this, 'a', { value: 7 }).a;
            }
          })).a != 7) ? function (it, key, D) {
              const protoDesc = gOPD$1(ObjectProto$1, key);
              if (protoDesc) delete ObjectProto$1[key];
              dP$1(it, key, D);
              if (protoDesc && it !== ObjectProto$1) dP$1(ObjectProto$1, key, protoDesc);
            } : dP$1;
          const wrap = function (tag) {
            const sym = AllSymbols[tag] = _objectCreate($Symbol[PROTOTYPE$2]);
            sym._k = tag;
            return sym;
          };
          const isSymbol = USE_NATIVE && typeof $Symbol.iterator === 'symbol' ? function (it) {
            return typeof it === 'symbol';
          } : function (it) {
            return it instanceof $Symbol;
          };
          var $defineProperty = function defineProperty(it, key, D) {
            if (it === ObjectProto$1) $defineProperty(OPSymbols, key, D);
            _anObject(it);
            key = _toPrimitive(key, true);
            _anObject(D);
            if (_has(AllSymbols, key)) {
              if (!D.enumerable) {
                if (!_has(it, HIDDEN)) dP$1(it, HIDDEN, _propertyDesc(1, {}));
                it[HIDDEN][key] = true;
              } else {
                if (_has(it, HIDDEN) && it[HIDDEN][key]) it[HIDDEN][key] = false;
                D = _objectCreate(D, { enumerable: _propertyDesc(0, false) });
              } return setSymbolDesc(it, key, D);
            } return dP$1(it, key, D);
          };
          const $defineProperties = function defineProperties(it, P) {
            _anObject(it);
            const keys = _enumKeys(P = _toIobject(P));
            let i = 0;
            const l = keys.length;
            let key;
            while (l > i) $defineProperty(it, key = keys[i++], P[key]);
            return it;
          };
          const $create = function create(it, P) {
            return P === undefined ? _objectCreate(it) : $defineProperties(_objectCreate(it), P);
          };
          const $propertyIsEnumerable = function propertyIsEnumerable(key) {
            const E = isEnum.call(this, key = _toPrimitive(key, true));
            if (this === ObjectProto$1 && _has(AllSymbols, key) && !_has(OPSymbols, key)) return false;
            return E || !_has(this, key) || !_has(AllSymbols, key) || _has(this, HIDDEN) && this[HIDDEN][key] ? E : true;
          };
          const $getOwnPropertyDescriptor = function getOwnPropertyDescriptor(it, key) {
            it = _toIobject(it);
            key = _toPrimitive(key, true);
            if (it === ObjectProto$1 && _has(AllSymbols, key) && !_has(OPSymbols, key)) return;
            const D = gOPD$1(it, key);
            if (D && _has(AllSymbols, key) && !(_has(it, HIDDEN) && it[HIDDEN][key])) D.enumerable = true;
            return D;
          };
          const $getOwnPropertyNames = function getOwnPropertyNames(it) {
            const names = gOPN$1(_toIobject(it));
            const result = [];
            let i = 0;
            let key;
            while (names.length > i) {
              if (!_has(AllSymbols, key = names[i++]) && key != HIDDEN && key != META) result.push(key);
            } return result;
          };
          const $getOwnPropertySymbols = function getOwnPropertySymbols(it) {
            const IS_OP = it === ObjectProto$1;
            const names = gOPN$1(IS_OP ? OPSymbols : _toIobject(it));
            const result = [];
            let i = 0;
            let key;
            while (names.length > i) {
              if (_has(AllSymbols, key = names[i++]) && (IS_OP ? _has(ObjectProto$1, key) : true)) result.push(AllSymbols[key]);
            } return result;
          };
          if (!USE_NATIVE) {
            $Symbol = function Symbol() {
              if (this instanceof $Symbol) throw TypeError('Symbol is not a constructor!');
              const tag = _uid(arguments.length > 0 ? arguments[0] : undefined);
              var $set = function (value) {
                if (this === ObjectProto$1) $set.call(OPSymbols, value);
                if (_has(this, HIDDEN) && _has(this[HIDDEN], tag)) this[HIDDEN][tag] = false;
                setSymbolDesc(this, tag, _propertyDesc(1, value));
              };
              if (_descriptors && setter) setSymbolDesc(ObjectProto$1, tag, { configurable: true, set: $set });
              return wrap(tag);
            };
            _redefine($Symbol[PROTOTYPE$2], 'toString', function toString() {
              return this._k;
            });
            _objectGopd.f = $getOwnPropertyDescriptor;
            _objectDp.f = $defineProperty;
            _objectGopn.f = _objectGopnExt.f = $getOwnPropertyNames;
            _objectPie.f = $propertyIsEnumerable;
            _objectGops.f = $getOwnPropertySymbols;
            if (_descriptors && !_library) {
              _redefine(ObjectProto$1, 'propertyIsEnumerable', $propertyIsEnumerable, true);
            }
            _wksExt.f = function (name) {
              return wrap(_wks(name));
            };
          }
          _export(_export.G + _export.W + _export.F * !USE_NATIVE, { Symbol: $Symbol });
          for (let es6Symbols = (
              'hasInstance,isConcatSpreadable,iterator,match,replace,search,species,split,toPrimitive,toStringTag,unscopables'
            ).split(','), j = 0; es6Symbols.length > j;)_wks(es6Symbols[j++]);
          for (let wellKnownSymbols = _objectKeys(_wks.store), k = 0; wellKnownSymbols.length > k;) _wksDefine(wellKnownSymbols[k++]);
          _export(_export.S + _export.F * !USE_NATIVE, 'Symbol', {
            for(key) {
              return _has(SymbolRegistry, key += '')
                ? SymbolRegistry[key]
                : SymbolRegistry[key] = $Symbol(key);
            },
            keyFor: function keyFor(sym) {
              if (!isSymbol(sym)) throw TypeError(`${sym} is not a symbol!`);
              for (const key in SymbolRegistry) if (SymbolRegistry[key] === sym) return key;
            },
            useSetter() {
              setter = true;
            },
            useSimple() {
              setter = false;
            }
          });
          _export(_export.S + _export.F * !USE_NATIVE, 'Object', {
            create: $create,
            defineProperty: $defineProperty,
            defineProperties: $defineProperties,
            getOwnPropertyDescriptor: $getOwnPropertyDescriptor,
            getOwnPropertyNames: $getOwnPropertyNames,
            getOwnPropertySymbols: $getOwnPropertySymbols
          });
          const FAILS_ON_PRIMITIVES = _fails(() => {
            _objectGops.f(1);
          });
          _export(_export.S + _export.F * FAILS_ON_PRIMITIVES, 'Object', {
            getOwnPropertySymbols: function getOwnPropertySymbols(it) {
              return _objectGops.f(_toObject(it));
            }
          });
          $JSON && _export(_export.S + _export.F * (!USE_NATIVE || _fails(() => {
            const S = $Symbol();
            return _stringify([S]) != '[null]' || _stringify({ a: S }) != '{}' || _stringify(Object(S)) != '{}';
          })), 'JSON', {
            stringify: function stringify(it) {
              const args = [it];
              let i = 1;
              let replacer; let $replacer;
              while (arguments.length > i) args.push(arguments[i++]);
              $replacer = replacer = args[1];
              if (!_isObject(replacer) && it === undefined || isSymbol(it)) return;
              if (!_isArray(replacer)) replacer = function (key, value) {
                if (typeof $replacer === 'function') value = $replacer.call(this, key, value);
                if (!isSymbol(value)) return value;
              };
              args[1] = replacer;
              return _stringify.apply($JSON, args);
            }
          });
          $Symbol[PROTOTYPE$2][TO_PRIMITIVE] || _hide($Symbol[PROTOTYPE$2], TO_PRIMITIVE, $Symbol[PROTOTYPE$2].valueOf);
          _setToStringTag($Symbol, 'Symbol');
          _setToStringTag(Math, 'Math', true);
          _setToStringTag(_global.JSON, 'JSON', true);

          const { getOwnPropertySymbols } = _core.Object;

          const getOwnPropertySymbols$1 = getOwnPropertySymbols;

          _export(_export.S, 'Array', { isArray: _isArray });

          const { isArray } = _core.Array;

          const isArray$1 = isArray;

          function _typeof(obj) {
            '@babel/helpers - typeof';

            return _typeof = 'function' === typeof Symbol && 'symbol' === typeof Symbol.iterator ? function (obj) {
              return typeof obj;
            } : function (obj) {
              return obj && 'function' === typeof Symbol && obj.constructor === Symbol && obj !== Symbol.prototype ? 'symbol' : typeof obj;
            }, _typeof(obj);
          }

          const _for = _core.Symbol.for;

          const _for$1 = _for;

          _wksDefine('asyncIterator');

          _wksDefine('observable');

          const symbol = _core.Symbol;

          const symbol$1 = symbol;

          const canUseSymbol = typeof symbol$1 === 'function' && _for$1;
          const REACT_ELEMENT_TYPE = canUseSymbol ? _for$1('react.element') : 0xeac7;
          function isReactElement(value) {
            return value.$$typeof === REACT_ELEMENT_TYPE;
          }
          function isNonNullObject(value) {
            return !!value && _typeof(value) === 'object';
          }
          function isSpecial(value) {
            const stringValue = Object.prototype.toString.call(value);
            return stringValue === '[object RegExp]' || stringValue === '[object Date]' || isReactElement(value);
          }
          function defaultIsMergeableObject(value) {
            return isNonNullObject(value) && !isSpecial(value);
          }

          function emptyTarget(val) {
            return isArray$1(val) ? [] : {};
          }
          function cloneUnlessOtherwiseSpecified(value, options) {
            return !!options.clone !== false && options.isMergeableObject(value) ? deepmerge(emptyTarget(value), value, options) : value;
          }
          function defaultArrayMerge(target, source, options) {
            return target.concat(source).map(element => cloneUnlessOtherwiseSpecified(element, options));
          }
          function getMergeFunction(key, options) {
            if (!options.customMerge) {
              return deepmerge;
            }
            const customMerge = options.customMerge(key);
            return typeof customMerge === 'function' ? customMerge : deepmerge;
          }
          function getEnumerableOwnPropertySymbols(target) {
            return getOwnPropertySymbols$1 ? getOwnPropertySymbols$1(target).filter(symbol => target.propertyIsEnumerable(symbol)) : [];
          }
          function getKeys(target) {
            return keys$1(target).concat(getEnumerableOwnPropertySymbols(target));
          }
          function propertyIsOnObject(object, property) {
            try {
              return property in object;
            } catch (_) {
              return false;
            }
          }
          function propertyIsUnsafe(target, key) {
            return propertyIsOnObject(target, key)
    && !(Object.hasOwnProperty.call(target, key)
    && Object.propertyIsEnumerable.call(target, key));
          }
          function mergeObject(target, source, options) {
            const destination = {};
            if (options.isMergeableObject(target)) {
              getKeys(target).forEach((key) => {
                destination[key] = cloneUnlessOtherwiseSpecified(target[key], options);
              });
            }
            getKeys(source).forEach((key) => {
              if (propertyIsUnsafe(target, key)) {
                return;
              }
              if (propertyIsOnObject(target, key) && options.isMergeableObject(source[key])) {
                destination[key] = getMergeFunction(key, options)(target[key], source[key], options);
              } else {
                destination[key] = cloneUnlessOtherwiseSpecified(source[key], options);
              }
            });
            return destination;
          }
          function deepmerge(target, source, options) {
            options = options || {};
            options.arrayMerge = options.arrayMerge || defaultArrayMerge;
            options.isMergeableObject = options.isMergeableObject || defaultIsMergeableObject;
            options.cloneUnlessOtherwiseSpecified = cloneUnlessOtherwiseSpecified;
            const sourceIsArray = isArray$1(source);
            const targetIsArray = isArray$1(target);
            const sourceAndTargetTypesMatch = sourceIsArray === targetIsArray;
            if (!sourceAndTargetTypesMatch) {
              return cloneUnlessOtherwiseSpecified(source, options);
            } if (sourceIsArray) {
              return options.arrayMerge(target, source, options);
            }
            return mergeObject(target, source, options);
          }
          deepmerge.all = function deepmergeAll(array, options) {
            if (!isArray$1(array)) {
              throw new Error('first argument should be an array');
            }
            return array.reduce((prev, next) => deepmerge(prev, next, options), {});
          };

          let curLang = bkLang.zhCN;
          let merged = false;
          let i18nHandler = function i18nHandler() {
            const i18n = getPrototypeOf$1(this || Vue).$t;
            if (typeof i18n === 'function' && !!Vue.locale) {
              if (!merged) {
                merged = true;
                Vue.locale(Vue.config.lang, deepmerge(curLang, Vue.locale(Vue.config.lang) || {}, {
                  clone: true
                }));
              }
              return i18n.apply(this, arguments);
            }
          };
          const escape = function escape(str) {
            return String(str).replace(/([.*+?^=!:${}()|[\]\/\\])/g, '\\$1');
          };
          const _t = function t(path, data) {
            let value = i18nHandler.apply(this, arguments);
            if (value !== null && typeof value !== 'undefined') {
              return value;
            }
            const arr = path.split('.');
            let current = curLang;
            const len = arr.length;
            for (let i = 0; i < len; i++) {
              value = current[arr[i]];
              if (i === len - 1) {
                if (data && typeof value === 'string') {
                  return value.replace(/\{(?=\w+)/g, '').replace(/(\w+)\}/g, '$1')
                    .replace(new RegExp(keys$1(data).map(escape)
                      .join('|'), 'g'), $0 => data[$0]);
                }
                return value;
              }
              if (!value) {
                return '';
              }
              current = value;
            }
            return '';
          };
          const use = function use(l) {
            if (l) {
              curLang = deepmerge(curLang, l);
            }
          };
          const i18n = function i18n(fn) {
            i18nHandler = fn || i18nHandler;
          };
          const getCurLang = function getCurLang() {
            return curLang;
          };
          const mixin = {
            methods: {
              t: function t() {
                for (var _len = arguments.length, args = new Array(_len), _key = 0; _key < _len; _key++) {
                  args[_key] = arguments[_key];
                }
                return _t.apply(this, args);
              }
            }
          };
          Vue.prototype.bkLocale = {
            use,
            t: _t,
            i18n,
            getCurLang,
            lang: bkLang,
            mixin
          };
          const index = {
            use,
            t: _t,
            i18n,
            getCurLang,
            lang: bkLang,
            mixin
          };

          exports.default = index;
          exports.escape = escape;
          exports.getCurLang = getCurLang;
          exports.i18n = i18n;
          exports.t = _t;
          exports.use = use;

          Object.defineProperty(exports, '__esModule', { value: true });
        }));
        /***/ }),

      /***/ './node_modules/bk-magic-vue/lib/locale/lang/en-US.js':
      /*! ************************************************************!*\
  !*** ./node_modules/bk-magic-vue/lib/locale/lang/en-US.js ***!
  \************************************************************/
      /***/ (function (__unused_webpack_module, exports) {
        (function (global, factory) {
          true ? factory(exports)
            : 0;
        }(this, (exports) => {
          'use strict';

          const enUS = {
            bk: {
              lang: 'en-US',
              datePicker: {
                selectDate: 'Select Date',
                selectTime: 'Select Time',
                clear: 'Clear',
                ok: 'OK',
                weekdays: {
                  sun: 'Sun',
                  mon: 'Mon',
                  tue: 'Tue',
                  wed: 'Wed',
                  thu: 'Thu',
                  fri: 'Fri',
                  sat: 'Sat'
                },
                hour: 'Hour',
                min: 'Minute',
                sec: 'Second',
                toNow: 'Now'
              },
              dialog: {
                ok: 'OK',
                cancel: 'CANCEL'
              },
              exception: {
                403: 'Forbidden',
                404: 'Not Found',
                500: 'Internal Server Error',
                building: 'Building',
                empty: 'No Data',
                searchEmpty: 'Search Is Empty',
                login: 'Please log in to Blueking'
              },
              form: {
                validPath: 'Please configure a valid path'
              },
              input: {
                input: 'Please input'
              },
              imageViewer: {
                loadFailed: 'Picture failed to load.',
                quitTips: 'ESC Can Exit fullscreen'
              },
              notify: {
                showMore: 'Show more'
              },
              select: {
                selectAll: 'Select All',
                pleaseselect: 'Please select',
                searchPlaceholder: 'Input keyword to search',
                dataEmpty: 'No options',
                searchEmpty: 'No matched data'
              },
              sideslider: {
                title: 'Title'
              },
              tagInput: {
                placeholder: 'Please input and press ENTER to finish'
              },
              transfer: {
                left: 'Left',
                total: ' (Total {total})',
                addAll: 'Add All',
                emptyContent: 'No Data',
                right: 'Right',
                removeAll: 'Remove All',
                emptySelected: 'No Selected',
                searchPlaceholder: 'Input keyword to search'
              },
              tree: {
                emptyText: 'No Data'
              },
              steps: {
                step1: 'Step1',
                step2: 'Step2',
                step3: 'Step3'
              },
              uploadFile: {
                drag: 'Try dragging an file here or',
                click: 'click to upload',
                uploadDone: 'Upload finished',
                uploading: 'uploading',
                reupload: 'reupload',
                replace: 'replace',
                uploadFailed: 'upload failed',
                fileExceedMsg: '{fileName} cannot exceed {size} MB',
                invalidFileName: 'FileName is not valid',
                invalidImageFormat: 'Only upload JPG | PNG | JPEG',
                imageExceedMsg: 'Image Size cannot exceed {imgSize} MB',
                uploadLabel: 'Upload Files'
              },
              navigation: {
                headerTitle: 'Program name'
              },
              searchSelect: {
                placeholder: 'Please enter',
                emptyText: 'Included key worth filtering query must have a value',
                condition: 'Or',
                remoteEmptyText: 'Query no data',
                remoteLoadingText: 'Loading...',
                tips: 'multiple keywords separate by |',
                ok: 'OK',
                cancel: 'Cancel'
              },
              table: {
                emptyText: 'No Data',
                sumText: 'Summary',
                setting: {
                  title: 'Table Settings',
                  fields: {
                    title: 'Displaying Fields Setting',
                    subtitle: '（{max} fiels most）',
                    selectAll: 'All'
                  },
                  lineHeight: {
                    title: 'Table Line Height',
                    small: 'small',
                    medium: 'medium',
                    large: 'large'
                  },
                  options: {
                    ok: 'OK',
                    cancel: 'Cancel'
                  }
                },
                confirm: 'Confirm',
                reset: 'Reset',
                all: 'All',
                filter: {
                  placeholder: 'Please input keyword',
                  empty: 'No matched data'
                }
              },
              bigTree: {
                emptyText: 'No Data'
              },
              message: {
                copy: 'copy',
                copied: 'copied'
              },
              image: {
                zoomIn: 'zoom in',
                zoomOut: 'zoom out',
                rotateLeft: 'anticlockwise',
                rotateRight: 'clockwise rotation',
                fullScreen: 'full screen',
                original: 'original size',
                prev: 'prev',
                next: 'next'
              }
            }
          };

          exports.default = enUS;

          Object.defineProperty(exports, '__esModule', { value: true });
        }));
        /***/ }),

      /***/ './node_modules/bk-magic-vue/lib/locale/lang/index.js':
      /*! ************************************************************!*\
  !*** ./node_modules/bk-magic-vue/lib/locale/lang/index.js ***!
  \************************************************************/
      /***/ (function (__unused_webpack_module, exports, __webpack_require__) {
        (function (global, factory) {
	 true ? factory(exports, __webpack_require__(/*! bk-magic-vue/lib/locale/lang/en-US */ './node_modules/bk-magic-vue/lib/locale/lang/en-US.js'), __webpack_require__(/*! bk-magic-vue/lib/locale/lang/zh-CN */ './node_modules/bk-magic-vue/lib/locale/lang/zh-CN.js'))
            : 0;
        }(this, (exports, enUS, zhCN) => {
          'use strict';

          enUS = enUS && enUS.hasOwnProperty('default') ? enUS.default : enUS;
          zhCN = zhCN && zhCN.hasOwnProperty('default') ? zhCN.default : zhCN;

          const index = {
	  enUS,
	  zhCN
          };

          exports.default = index;

          Object.defineProperty(exports, '__esModule', { value: true });
        }));
        /***/ }),

      /***/ './node_modules/bk-magic-vue/lib/locale/lang/zh-CN.js':
      /*! ************************************************************!*\
  !*** ./node_modules/bk-magic-vue/lib/locale/lang/zh-CN.js ***!
  \************************************************************/
      /***/ (function (__unused_webpack_module, exports) {
        (function (global, factory) {
          true ? factory(exports)
            : 0;
        }(this, (exports) => {
          'use strict';

          const zhCN = {
            bk: {
              lang: 'zh-CN',
              datePicker: {
                selectDate: '选择日期',
                selectTime: '选择时间',
                clear: '清除',
                ok: '确定',
                weekdays: {
                  sun: '日',
                  mon: '一',
                  tue: '二',
                  wed: '三',
                  thu: '四',
                  fri: '五',
                  sat: '六'
                },
                hour: '时',
                min: '分',
                sec: '秒',
                toNow: '至今'
              },
              dialog: {
                ok: '确定',
                cancel: '取消'
              },
              exception: {
                403: '无业务权限',
                404: '页面不存在',
                500: '服务维护中',
                building: '功能建设中',
                empty: '没有数据',
                searchEmpty: '搜索为空',
                login: '请登入蓝鲸'
              },
              form: {
                validPath: '请配置合法的路径'
              },
              input: {
                input: '请输入'
              },
              imageViewer: {
                loadFailed: '抱歉，图片加载失败',
                quitTips: 'ESC 可以退出全屏'
              },
              notify: {
                showMore: '查看更多'
              },
              select: {
                selectAll: '全选',
                pleaseselect: '请选择',
                searchPlaceholder: '输入关键字搜索',
                dataEmpty: '暂无选项',
                searchEmpty: '无匹配数据'
              },
              sideslider: {
                title: '标题'
              },
              tagInput: {
                placeholder: '请输入并按Enter结束'
              },
              transfer: {
                left: '左侧列表',
                total: '（共{total}条）',
                addAll: '全部添加',
                emptyContent: '无数据',
                right: '右侧列表',
                removeAll: '清空',
                emptySelected: '未选择任何项',
                searchPlaceholder: '请输入搜索关键字'
              },
              tree: {
                emptyText: '暂无数据'
              },
              steps: {
                step1: '步骤1',
                step2: '步骤2',
                step3: '步骤3'
              },
              uploadFile: {
                drag: '将文件拖到此处或',
                click: '点击上传',
                uploadDone: '上传完毕',
                uploading: '正在上传',
                reupload: '重新上传',
                replace: '点击替换',
                uploadFailed: '上传失败',
                fileExceedMsg: '{fileName} 文件不能超过 {size} MB',
                invalidFileName: '文件名不合法',
                invalidImageFormat: '只允许上传JPG|PNG|JPEG格式的图片',
                imageExceedMsg: '图片大小不能超过 {imgSize} MB',
                uploadLabel: '上传文件'
              },
              navigation: {
                headerTitle: '栏目名称'
              },
              searchSelect: {
                placeholder: '请输入',
                emptyText: '包含键值得过滤查询必须有一个值',
                condition: '或',
                remoteEmptyText: '查询无数据',
                remoteLoadingText: '正在加载中...',
                tips: '多个关键字用竖线 “|” 分隔',
                ok: '确认',
                cancel: '取消'
              },
              table: {
                emptyText: '暂无数据',
                sumText: '总计',
                setting: {
                  title: '表格设置',
                  fields: {
                    title: '字段显示设置',
                    subtitle: '（最多{max}项）',
                    selectAll: '全选'
                  },
                  lineHeight: {
                    title: '表格行高',
                    small: '小',
                    medium: '中',
                    large: '大'
                  },
                  options: {
                    ok: '确认',
                    cancel: '取消'
                  }
                },
                confirm: '确定',
                reset: '重置',
                all: '全部',
                filter: {
                  placeholder: '请输入关键字',
                  empty: '无匹配项'
                }
              },
              bigTree: {
                emptyText: '暂无搜索结果'
              },
              message: {
                copy: '复制',
                copied: '已复制'
              },
              image: {
                zoomIn: '放大',
                zoomOut: '缩小',
                rotateLeft: '向左旋转',
                rotateRight: '向右旋转',
                fullScreen: '适应屏幕',
                original: '快速回到 1：1'
              }
            }
          };

          exports.default = zhCN;

          Object.defineProperty(exports, '__esModule', { value: true });
        }));
        /***/ }),

      /***/ './node_modules/bk-magic-vue/lib/search-select.js':
      /*! ********************************************************!*\
  !*** ./node_modules/bk-magic-vue/lib/search-select.js ***!
  \********************************************************/
      /***/ (function (__unused_webpack_module, exports, __webpack_require__) {
        (function (global, factory) {
	 true ? factory(exports, __webpack_require__(/*! vue */ './node_modules/vue/dist/vue.runtime.esm.js'), __webpack_require__(/*! bk-magic-vue/lib/locale */ './node_modules/bk-magic-vue/lib/locale/index.js'))
            : 0;
        }(this, (exports, Vue, locale) => {
          'use strict';

          Vue = Vue && Vue.hasOwnProperty('default') ? Vue.default : Vue;
          locale = locale && locale.hasOwnProperty('default') ? locale.default : locale;

          function createCommonjsModule(fn, module) {
            return module = { exports: {} }, fn(module, module.exports), module.exports;
          }

          const _global = createCommonjsModule((module) => {
            const global = module.exports = typeof window !== 'undefined' && window.Math == Math
	  ? window : typeof self !== 'undefined' && self.Math == Math ? self
	  : Function('return this')();
            if (typeof __g === 'number') __g = global;
          });

          const _core = createCommonjsModule((module) => {
            const core = module.exports = { version: '2.6.12' };
            if (typeof __e === 'number') __e = core;
          });
          const _core_1 = _core.version;

          const _aFunction = function (it) {
	  if (typeof it !== 'function') throw TypeError(`${it} is not a function!`);
	  return it;
          };

          const _ctx = function (fn, that, length) {
	  _aFunction(fn);
	  if (that === undefined) return fn;
	  switch (length) {
	    case 1: return function (a) {
	      return fn.call(that, a);
	    };
	    case 2: return function (a, b) {
	      return fn.call(that, a, b);
	    };
	    case 3: return function (a, b, c) {
	      return fn.call(that, a, b, c);
	    };
	  }
	  return function () {
	    return fn.apply(that, arguments);
	  };
          };

          const _isObject = function (it) {
	  return typeof it === 'object' ? it !== null : typeof it === 'function';
          };

          const _anObject = function (it) {
	  if (!_isObject(it)) throw TypeError(`${it} is not an object!`);
	  return it;
          };

          const _fails = function (exec) {
	  try {
	    return !!exec();
	  } catch (e) {
	    return true;
	  }
          };

          const _descriptors = !_fails(() => Object.defineProperty({}, 'a', { get() {
            return 7;
          } }).a != 7);

          const document$1 = _global.document;
          const is = _isObject(document$1) && _isObject(document$1.createElement);
          const _domCreate = function (it) {
	  return is ? document$1.createElement(it) : {};
          };

          const _ie8DomDefine = !_descriptors && !_fails(() => Object.defineProperty(_domCreate('div'), 'a', { get() {
            return 7;
          } }).a != 7);

          const _toPrimitive = function (it, S) {
	  if (!_isObject(it)) return it;
	  let fn; let val;
	  if (S && typeof (fn = it.toString) === 'function' && !_isObject(val = fn.call(it))) return val;
	  if (typeof (fn = it.valueOf) === 'function' && !_isObject(val = fn.call(it))) return val;
	  if (!S && typeof (fn = it.toString) === 'function' && !_isObject(val = fn.call(it))) return val;
	  throw TypeError('Can\'t convert object to primitive value');
          };

          const dP = Object.defineProperty;
          const f = _descriptors ? Object.defineProperty : function defineProperty(O, P, Attributes) {
	  _anObject(O);
	  P = _toPrimitive(P, true);
	  _anObject(Attributes);
	  if (_ie8DomDefine) try {
	    return dP(O, P, Attributes);
	  } catch (e) {  }
	  if ('get' in Attributes || 'set' in Attributes) throw TypeError('Accessors not supported!');
	  if ('value' in Attributes) O[P] = Attributes.value;
	  return O;
          };
          const _objectDp = {
            f
          };

          const _propertyDesc = function (bitmap, value) {
	  return {
	    enumerable: !(bitmap & 1),
	    configurable: !(bitmap & 2),
	    writable: !(bitmap & 4),
	    value
	  };
          };

          const _hide = _descriptors ? function (object, key, value) {
	  return _objectDp.f(object, key, _propertyDesc(1, value));
          } : function (object, key, value) {
	  object[key] = value;
	  return object;
          };

          const { hasOwnProperty } = {};
          const _has = function (it, key) {
	  return hasOwnProperty.call(it, key);
          };

          const PROTOTYPE = 'prototype';
          var $export = function (type, name, source) {
	  const IS_FORCED = type & $export.F;
	  const IS_GLOBAL = type & $export.G;
	  const IS_STATIC = type & $export.S;
	  const IS_PROTO = type & $export.P;
	  const IS_BIND = type & $export.B;
	  const IS_WRAP = type & $export.W;
	  const exports = IS_GLOBAL ? _core : _core[name] || (_core[name] = {});
	  const expProto = exports[PROTOTYPE];
	  const target = IS_GLOBAL ? _global : IS_STATIC ? _global[name] : (_global[name] || {})[PROTOTYPE];
	  let key; let own; let out;
	  if (IS_GLOBAL) source = name;
	  for (key in source) {
	    own = !IS_FORCED && target && target[key] !== undefined;
	    if (own && _has(exports, key)) continue;
	    out = own ? target[key] : source[key];
	    exports[key] = IS_GLOBAL && typeof target[key] !== 'function' ? source[key]
	    : IS_BIND && own ? _ctx(out, _global)
	    : IS_WRAP && target[key] == out ? (function (C) {
	      const F = function (a, b, c) {
	        if (this instanceof C) {
	          switch (arguments.length) {
	            case 0: return new C();
	            case 1: return new C(a);
	            case 2: return new C(a, b);
	          } return new C(a, b, c);
	        } return C.apply(this, arguments);
	      };
	      F[PROTOTYPE] = C[PROTOTYPE];
	      return F;
	    }(out)) : IS_PROTO && typeof out === 'function' ? _ctx(Function.call, out) : out;
	    if (IS_PROTO) {
	      (exports.virtual || (exports.virtual = {}))[key] = out;
	      if (type & $export.R && expProto && !expProto[key]) _hide(expProto, key, out);
	    }
	  }
          };
          $export.F = 1;
          $export.G = 2;
          $export.S = 4;
          $export.P = 8;
          $export.B = 16;
          $export.W = 32;
          $export.U = 64;
          $export.R = 128;
          const _export = $export;

          const { toString } = {};
          const _cof = function (it) {
	  return toString.call(it).slice(8, -1);
          };

          const _iobject = Object('z').propertyIsEnumerable(0) ? Object : function (it) {
	  return _cof(it) == 'String' ? it.split('') : Object(it);
          };

          const _defined = function (it) {
	  if (it == undefined) throw TypeError(`Can't call method on  ${it}`);
	  return it;
          };

          const _toIobject = function (it) {
	  return _iobject(_defined(it));
          };

          const { ceil } = Math;
          const { floor } = Math;
          const _toInteger = function (it) {
	  return isNaN(it = +it) ? 0 : (it > 0 ? floor : ceil)(it);
          };

          const { min } = Math;
          const _toLength = function (it) {
	  return it > 0 ? min(_toInteger(it), 0x1fffffffffffff) : 0;
          };

          const { max } = Math;
          const min$1 = Math.min;
          const _toAbsoluteIndex = function (index, length) {
	  index = _toInteger(index);
	  return index < 0 ? max(index + length, 0) : min$1(index, length);
          };

          const _arrayIncludes = function (IS_INCLUDES) {
	  return function ($this, el, fromIndex) {
	    const O = _toIobject($this);
	    const length = _toLength(O.length);
	    let index = _toAbsoluteIndex(fromIndex, length);
	    let value;
	    if (IS_INCLUDES && el != el) while (length > index) {
	      value = O[index++];
	      if (value != value) return true;
	    } else for (;length > index; index++) if (IS_INCLUDES || index in O) {
	      if (O[index] === el) return IS_INCLUDES || index || 0;
	    } return !IS_INCLUDES && -1;
	  };
          };

          const _library = true;

          const _shared = createCommonjsModule((module) => {
            const SHARED = '__core-js_shared__';
            const store = _global[SHARED] || (_global[SHARED] = {});
            (module.exports = function (key, value) {
	  return store[key] || (store[key] = value !== undefined ? value : {});
            })('versions', []).push({
	  version: _core.version,
	  mode: 'pure',
	  copyright: '© 2020 Denis Pushkarev (zloirock.ru)'
            });
          });

          let id = 0;
          const px = Math.random();
          const _uid = function (key) {
	  return 'Symbol('.concat(key === undefined ? '' : key, ')_', (++id + px).toString(36));
          };

          const shared = _shared('keys');
          const _sharedKey = function (key) {
	  return shared[key] || (shared[key] = _uid(key));
          };

          const arrayIndexOf = _arrayIncludes(false);
          const IE_PROTO = _sharedKey('IE_PROTO');
          const _objectKeysInternal = function (object, names) {
	  const O = _toIobject(object);
	  let i = 0;
	  const result = [];
	  let key;
	  for (key in O) if (key != IE_PROTO) _has(O, key) && result.push(key);
	  while (names.length > i) if (_has(O, key = names[i++])) {
	    ~arrayIndexOf(result, key) || result.push(key);
	  }
	  return result;
          };

          const _enumBugKeys = (
	  'constructor,hasOwnProperty,isPrototypeOf,propertyIsEnumerable,toLocaleString,toString,valueOf'
          ).split(',');

          const _objectKeys = Object.keys || function keys(O) {
	  return _objectKeysInternal(O, _enumBugKeys);
          };

          const f$1 = {}.propertyIsEnumerable;
          const _objectPie = {
            f: f$1
          };

          const isEnum = _objectPie.f;
          const _objectToArray = function (isEntries) {
	  return function (it) {
	    const O = _toIobject(it);
	    const keys = _objectKeys(O);
	    const { length } = keys;
	    let i = 0;
	    const result = [];
	    let key;
	    while (length > i) {
	      key = keys[i++];
	      if (!_descriptors || isEnum.call(O, key)) {
	        result.push(isEntries ? [key, O[key]] : O[key]);
	      }
	    }
	    return result;
	  };
          };

          const $values = _objectToArray(false);
          _export(_export.S, 'Object', {
	  values: function values(it) {
	    return $values(it);
	  }
          });

          const { values } = _core.Object;

          const values$1 = values;

          function asyncGeneratorStep(gen, resolve, reject, _next, _throw, key, arg) {
	  try {
	    var info = gen[key](arg);
	    var { value } = info;
	  } catch (error) {
	    reject(error);
	    return;
	  }

	  if (info.done) {
	    resolve(value);
	  } else {
	    Promise.resolve(value).then(_next, _throw);
	  }
          }

          function _asyncToGenerator(fn) {
	  return function () {
	    const self = this;
	        const args = arguments;
	    return new Promise((resolve, reject) => {
	      const gen = fn.apply(self, args);

	      function _next(value) {
	        asyncGeneratorStep(gen, resolve, reject, _next, _throw, 'next', value);
	      }

	      function _throw(err) {
	        asyncGeneratorStep(gen, resolve, reject, _next, _throw, 'throw', err);
	      }

	      _next(undefined);
	    });
	  };
          }

          function _classCallCheck(instance, Constructor) {
	  if (!(instance instanceof Constructor)) {
	    throw new TypeError('Cannot call a class as a function');
	  }
          }

          function _defineProperties(target, props) {
	  for (let i = 0; i < props.length; i++) {
	    const descriptor = props[i];
	    descriptor.enumerable = descriptor.enumerable || false;
	    descriptor.configurable = true;
	    if ('value' in descriptor) descriptor.writable = true;
	    Object.defineProperty(target, descriptor.key, descriptor);
	  }
          }

          function _createClass(Constructor, protoProps, staticProps) {
	  if (protoProps) _defineProperties(Constructor.prototype, protoProps);
	  if (staticProps) _defineProperties(Constructor, staticProps);
	  Object.defineProperty(Constructor, 'prototype', {
	    writable: false
	  });
	  return Constructor;
          }

          function _defineProperty(obj, key, value) {
	  if (key in obj) {
	    Object.defineProperty(obj, key, {
	      value,
	      enumerable: true,
	      configurable: true,
	      writable: true
	    });
	  } else {
	    obj[key] = value;
	  }

	  return obj;
          }

          function _extends() {
	  _extends = Object.assign || function (target) {
	    for (let i = 1; i < arguments.length; i++) {
	      const source = arguments[i];

	      for (const key in source) {
	        if (Object.prototype.hasOwnProperty.call(source, key)) {
	          target[key] = source[key];
	        }
	      }
	    }

	    return target;
	  };

	  return _extends.apply(this, arguments);
          }

          function _objectSpread(target) {
	  for (let i = 1; i < arguments.length; i++) {
	    var source = arguments[i] != null ? Object(arguments[i]) : {};
	    const ownKeys = Object.keys(source);

	    if (typeof Object.getOwnPropertySymbols === 'function') {
	      ownKeys.push.apply(ownKeys, Object.getOwnPropertySymbols(source).filter(sym => Object.getOwnPropertyDescriptor(source, sym).enumerable));
	    }

	    ownKeys.forEach((key) => {
	      _defineProperty(target, key, source[key]);
	    });
	  }

	  return target;
          }

          function _toConsumableArray(arr) {
	  return _arrayWithoutHoles(arr) || _iterableToArray(arr) || _unsupportedIterableToArray(arr) || _nonIterableSpread();
          }

          function _arrayWithoutHoles(arr) {
	  if (Array.isArray(arr)) return _arrayLikeToArray(arr);
          }

          function _iterableToArray(iter) {
	  if (typeof Symbol !== 'undefined' && iter[Symbol.iterator] != null || iter['@@iterator'] != null) return Array.from(iter);
          }

          function _unsupportedIterableToArray(o, minLen) {
	  if (!o) return;
	  if (typeof o === 'string') return _arrayLikeToArray(o, minLen);
	  let n = Object.prototype.toString.call(o).slice(8, -1);
	  if (n === 'Object' && o.constructor) n = o.constructor.name;
	  if (n === 'Map' || n === 'Set') return Array.from(o);
	  if (n === 'Arguments' || /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(n)) return _arrayLikeToArray(o, minLen);
          }

          function _arrayLikeToArray(arr, len) {
	  if (len == null || len > arr.length) len = arr.length;

	  for (var i = 0, arr2 = new Array(len); i < len; i++) arr2[i] = arr[i];

	  return arr2;
          }

          function _nonIterableSpread() {
	  throw new TypeError('Invalid attempt to spread non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.');
          }

          const _stringAt = function (TO_STRING) {
	  return function (that, pos) {
	    const s = String(_defined(that));
	    const i = _toInteger(pos);
	    const l = s.length;
	    let a; let b;
	    if (i < 0 || i >= l) return TO_STRING ? '' : undefined;
	    a = s.charCodeAt(i);
	    return a < 0xd800 || a > 0xdbff || i + 1 === l || (b = s.charCodeAt(i + 1)) < 0xdc00 || b > 0xdfff
	      ? TO_STRING ? s.charAt(i) : a
	      : TO_STRING ? s.slice(i, i + 2) : (a - 0xd800 << 10) + (b - 0xdc00) + 0x10000;
	  };
          };

          const _redefine = _hide;

          const _iterators = {};

          const _objectDps = _descriptors ? Object.defineProperties : function defineProperties(O, Properties) {
	  _anObject(O);
	  const keys = _objectKeys(Properties);
	  const { length } = keys;
	  let i = 0;
	  let P;
	  while (length > i) _objectDp.f(O, P = keys[i++], Properties[P]);
	  return O;
          };

          const document$2 = _global.document;
          const _html = document$2 && document$2.documentElement;

          const IE_PROTO$1 = _sharedKey('IE_PROTO');
          const Empty = function () {  };
          const PROTOTYPE$1 = 'prototype';
          var createDict = function () {
	  const iframe = _domCreate('iframe');
	  let i = _enumBugKeys.length;
	  const lt = '<';
	  const gt = '>';
	  let iframeDocument;
	  iframe.style.display = 'none';
	  _html.appendChild(iframe);
	  iframe.src = 'javascript:';
	  iframeDocument = iframe.contentWindow.document;
	  iframeDocument.open();
	  iframeDocument.write(`${lt}script${gt}document.F=Object${lt}/script${gt}`);
	  iframeDocument.close();
	  createDict = iframeDocument.F;
	  while (i--) delete createDict[PROTOTYPE$1][_enumBugKeys[i]];
	  return createDict();
          };
          const _objectCreate = Object.create || function create(O, Properties) {
	  let result;
	  if (O !== null) {
	    Empty[PROTOTYPE$1] = _anObject(O);
	    result = new Empty();
	    Empty[PROTOTYPE$1] = null;
	    result[IE_PROTO$1] = O;
	  } else result = createDict();
	  return Properties === undefined ? result : _objectDps(result, Properties);
          };

          const _wks = createCommonjsModule((module) => {
            const store = _shared('wks');
            const { Symbol } = _global;
            const USE_SYMBOL = typeof Symbol === 'function';
            const $exports = module.exports = function (name) {
	  return store[name] || (store[name] =	    USE_SYMBOL && Symbol[name] || (USE_SYMBOL ? Symbol : _uid)(`Symbol.${name}`));
            };
            $exports.store = store;
          });

          const def = _objectDp.f;
          const TAG = _wks('toStringTag');
          const _setToStringTag = function (it, tag, stat) {
	  if (it && !_has(it = stat ? it : it.prototype, TAG)) def(it, TAG, { configurable: true, value: tag });
          };

          const IteratorPrototype = {};
          _hide(IteratorPrototype, _wks('iterator'), function () {
            return this;
          });
          const _iterCreate = function (Constructor, NAME, next) {
	  Constructor.prototype = _objectCreate(IteratorPrototype, { next: _propertyDesc(1, next) });
	  _setToStringTag(Constructor, `${NAME} Iterator`);
          };

          const _toObject = function (it) {
	  return Object(_defined(it));
          };

          const IE_PROTO$2 = _sharedKey('IE_PROTO');
          const ObjectProto = Object.prototype;
          const _objectGpo = Object.getPrototypeOf || function (O) {
	  O = _toObject(O);
	  if (_has(O, IE_PROTO$2)) return O[IE_PROTO$2];
	  if (typeof O.constructor === 'function' && O instanceof O.constructor) {
	    return O.constructor.prototype;
	  } return O instanceof Object ? ObjectProto : null;
          };

          const ITERATOR = _wks('iterator');
          const BUGGY = !([].keys && 'next' in [].keys());
          const FF_ITERATOR = '@@iterator';
          const KEYS = 'keys';
          const VALUES = 'values';
          const returnThis = function () {
            return this;
          };
          const _iterDefine = function (Base, NAME, Constructor, next, DEFAULT, IS_SET, FORCED) {
	  _iterCreate(Constructor, NAME, next);
	  const getMethod = function (kind) {
	    if (!BUGGY && kind in proto) return proto[kind];
	    switch (kind) {
	      case KEYS: return function keys() {
                  return new Constructor(this, kind);
                };
	      case VALUES: return function values() {
                  return new Constructor(this, kind);
                };
	    } return function entries() {
                return new Constructor(this, kind);
              };
	  };
	  const TAG = `${NAME} Iterator`;
	  const DEF_VALUES = DEFAULT == VALUES;
	  let VALUES_BUG = false;
	  var proto = Base.prototype;
	  const $native = proto[ITERATOR] || proto[FF_ITERATOR] || DEFAULT && proto[DEFAULT];
	  let $default = $native || getMethod(DEFAULT);
	  const $entries = DEFAULT ? !DEF_VALUES ? $default : getMethod('entries') : undefined;
	  const $anyNative = NAME == 'Array' ? proto.entries || $native : $native;
	  let methods; let key; let IteratorPrototype;
	  if ($anyNative) {
	    IteratorPrototype = _objectGpo($anyNative.call(new Base()));
	    if (IteratorPrototype !== Object.prototype && IteratorPrototype.next) {
	      _setToStringTag(IteratorPrototype, TAG, true);
	    }
	  }
	  if (DEF_VALUES && $native && $native.name !== VALUES) {
	    VALUES_BUG = true;
	    $default = function values() {
                return $native.call(this);
              };
	  }
	  if ((FORCED) && (BUGGY || VALUES_BUG || !proto[ITERATOR])) {
	    _hide(proto, ITERATOR, $default);
	  }
	  _iterators[NAME] = $default;
	  _iterators[TAG] = returnThis;
	  if (DEFAULT) {
	    methods = {
	      values: DEF_VALUES ? $default : getMethod(VALUES),
	      keys: IS_SET ? $default : getMethod(KEYS),
	      entries: $entries
	    };
	    if (FORCED) for (key in methods) {
	      if (!(key in proto)) _redefine(proto, key, methods[key]);
	    } else _export(_export.P + _export.F * (BUGGY || VALUES_BUG), NAME, methods);
	  }
	  return methods;
          };

          const $at = _stringAt(true);
          _iterDefine(String, 'String', function (iterated) {
	  this._t = String(iterated);
	  this._i = 0;
          }, function () {
	  const O = this._t;
	  const index = this._i;
	  let point;
	  if (index >= O.length) return { value: undefined, done: true };
	  point = $at(O, index);
	  this._i += point.length;
	  return { value: point, done: false };
          });

          const _iterStep = function (done, value) {
	  return { value, done: !!done };
          };

          const es6_array_iterator = _iterDefine(Array, 'Array', function (iterated, kind) {
	  this._t = _toIobject(iterated);
	  this._i = 0;
	  this._k = kind;
          }, function () {
	  const O = this._t;
	  const kind = this._k;
	  const index = this._i++;
	  if (!O || index >= O.length) {
	    this._t = undefined;
	    return _iterStep(1);
	  }
	  if (kind == 'keys') return _iterStep(0, index);
	  if (kind == 'values') return _iterStep(0, O[index]);
	  return _iterStep(0, [index, O[index]]);
          }, 'values');
          _iterators.Arguments = _iterators.Array;

          const TO_STRING_TAG = _wks('toStringTag');
          const DOMIterables = ('CSSRuleList,CSSStyleDeclaration,CSSValueList,ClientRectList,DOMRectList,DOMStringList,'
	  + 'DOMTokenList,DataTransferItemList,FileList,HTMLAllCollection,HTMLCollection,HTMLFormElement,HTMLSelectElement,'
	  + 'MediaList,MimeTypeArray,NamedNodeMap,NodeList,PaintRequestList,Plugin,PluginArray,SVGLengthList,SVGNumberList,'
	  + 'SVGPathSegList,SVGPointList,SVGStringList,SVGTransformList,SourceBufferList,StyleSheetList,TextTrackCueList,'
	  + 'TextTrackList,TouchList').split(',');
          for (let i = 0; i < DOMIterables.length; i++) {
	  const NAME = DOMIterables[i];
	  const Collection = _global[NAME];
	  const proto = Collection && Collection.prototype;
	  if (proto && !proto[TO_STRING_TAG]) _hide(proto, TO_STRING_TAG, NAME);
	  _iterators[NAME] = _iterators.Array;
          }

          const TAG$1 = _wks('toStringTag');
          const ARG = _cof(function () {
            return arguments;
          }()) == 'Arguments';
          const tryGet = function (it, key) {
	  try {
	    return it[key];
	  } catch (e) {  }
          };
          const _classof = function (it) {
	  let O; let T; let B;
	  return it === undefined ? 'Undefined' : it === null ? 'Null'
	    : typeof (T = tryGet(O = Object(it), TAG$1)) === 'string' ? T
	    : ARG ? _cof(O)
	    : (B = _cof(O)) == 'Object' && typeof O.callee === 'function' ? 'Arguments' : B;
          };

          const _anInstance = function (it, Constructor, name, forbiddenField) {
	  if (!(it instanceof Constructor) || (forbiddenField !== undefined && forbiddenField in it)) {
	    throw TypeError(`${name}: incorrect invocation!`);
	  } return it;
          };

          const _iterCall = function (iterator, fn, value, entries) {
	  try {
	    return entries ? fn(_anObject(value)[0], value[1]) : fn(value);
	  } catch (e) {
	    const ret = iterator.return;
	    if (ret !== undefined) _anObject(ret.call(iterator));
	    throw e;
	  }
          };

          const ITERATOR$1 = _wks('iterator');
          const ArrayProto = Array.prototype;
          const _isArrayIter = function (it) {
	  return it !== undefined && (_iterators.Array === it || ArrayProto[ITERATOR$1] === it);
          };

          const ITERATOR$2 = _wks('iterator');
          const core_getIteratorMethod = _core.getIteratorMethod = function (it) {
	  if (it != undefined) return it[ITERATOR$2]
	    || it['@@iterator']
	    || _iterators[_classof(it)];
          };

          const _forOf = createCommonjsModule((module) => {
            const BREAK = {};
            const RETURN = {};
            const exports = module.exports = function (iterable, entries, fn, that, ITERATOR) {
	  const iterFn = ITERATOR ? function () {
                return iterable;
              } : core_getIteratorMethod(iterable);
	  const f = _ctx(fn, that, entries ? 2 : 1);
	  let index = 0;
	  let length; let step; let iterator; let result;
	  if (typeof iterFn !== 'function') throw TypeError(`${iterable} is not iterable!`);
	  if (_isArrayIter(iterFn)) for (length = _toLength(iterable.length); length > index; index++) {
	    result = entries ? f(_anObject(step = iterable[index])[0], step[1]) : f(iterable[index]);
	    if (result === BREAK || result === RETURN) return result;
	  } else for (iterator = iterFn.call(iterable); !(step = iterator.next()).done;) {
	    result = _iterCall(iterator, f, step.value, entries);
	    if (result === BREAK || result === RETURN) return result;
	  }
            };
            exports.BREAK = BREAK;
            exports.RETURN = RETURN;
          });

          const SPECIES = _wks('species');
          const _speciesConstructor = function (O, D) {
	  const C = _anObject(O).constructor;
	  let S;
	  return C === undefined || (S = _anObject(C)[SPECIES]) == undefined ? D : _aFunction(S);
          };

          const _invoke = function (fn, args, that) {
	  const un = that === undefined;
	  switch (args.length) {
	    case 0: return un ? fn()
	                      : fn.call(that);
	    case 1: return un ? fn(args[0])
	                      : fn.call(that, args[0]);
	    case 2: return un ? fn(args[0], args[1])
	                      : fn.call(that, args[0], args[1]);
	    case 3: return un ? fn(args[0], args[1], args[2])
	                      : fn.call(that, args[0], args[1], args[2]);
	    case 4: return un ? fn(args[0], args[1], args[2], args[3])
	                      : fn.call(that, args[0], args[1], args[2], args[3]);
	  } return fn.apply(that, args);
          };

          const { process } = _global;
          let setTask = _global.setImmediate;
          let clearTask = _global.clearImmediate;
          const { MessageChannel } = _global;
          const { Dispatch } = _global;
          let counter = 0;
          const queue = {};
          const ONREADYSTATECHANGE = 'onreadystatechange';
          let defer; let channel; let port;
          const run = function () {
	  const id = +this;
	  if (queue.hasOwnProperty(id)) {
	    const fn = queue[id];
	    delete queue[id];
	    fn();
	  }
          };
          const listener = function (event) {
	  run.call(event.data);
          };
          if (!setTask || !clearTask) {
	  setTask = function setImmediate(fn) {
	    const args = [];
	    let i = 1;
	    while (arguments.length > i) args.push(arguments[i++]);
	    queue[++counter] = function () {
	      _invoke(typeof fn === 'function' ? fn : Function(fn), args);
	    };
	    defer(counter);
	    return counter;
	  };
	  clearTask = function clearImmediate(id) {
	    delete queue[id];
	  };
	  if (_cof(process) == 'process') {
	    defer = function (id) {
	      process.nextTick(_ctx(run, id, 1));
	    };
	  } else if (Dispatch && Dispatch.now) {
	    defer = function (id) {
	      Dispatch.now(_ctx(run, id, 1));
	    };
	  } else if (MessageChannel) {
	    channel = new MessageChannel();
	    port = channel.port2;
	    channel.port1.onmessage = listener;
	    defer = _ctx(port.postMessage, port, 1);
	  } else if (_global.addEventListener && typeof postMessage === 'function' && !_global.importScripts) {
	    defer = function (id) {
	      _global.postMessage(`${id}`, '*');
	    };
	    _global.addEventListener('message', listener, false);
	  } else if (ONREADYSTATECHANGE in _domCreate('script')) {
	    defer = function (id) {
	      _html.appendChild(_domCreate('script'))[ONREADYSTATECHANGE] = function () {
	        _html.removeChild(this);
	        run.call(id);
	      };
	    };
	  } else {
	    defer = function (id) {
	      setTimeout(_ctx(run, id, 1), 0);
	    };
	  }
          }
          const _task = {
	  set: setTask,
	  clear: clearTask
          };

          const macrotask = _task.set;
          const Observer = _global.MutationObserver || _global.WebKitMutationObserver;
          const process$1 = _global.process;
          const Promise$1 = _global.Promise;
          const isNode = _cof(process$1) == 'process';
          const _microtask = function () {
	  let head; let last; let notify;
	  const flush = function () {
	    let parent; let fn;
	    if (isNode && (parent = process$1.domain)) parent.exit();
	    while (head) {
	      fn = head.fn;
	      head = head.next;
	      try {
	        fn();
	      } catch (e) {
	        if (head) notify();
	        else last = undefined;
	        throw e;
	      }
	    } last = undefined;
	    if (parent) parent.enter();
	  };
	  if (isNode) {
	    notify = function () {
	      process$1.nextTick(flush);
	    };
	  } else if (Observer && !(_global.navigator && _global.navigator.standalone)) {
	    let toggle = true;
	    const node = document.createTextNode('');
	    new Observer(flush).observe(node, { characterData: true });
	    notify = function () {
	      node.data = toggle = !toggle;
	    };
	  } else if (Promise$1 && Promise$1.resolve) {
	    const promise = Promise$1.resolve(undefined);
	    notify = function () {
	      promise.then(flush);
	    };
	  } else {
	    notify = function () {
	      macrotask.call(_global, flush);
	    };
	  }
	  return function (fn) {
	    const task = { fn, next: undefined };
	    if (last) last.next = task;
	    if (!head) {
	      head = task;
	      notify();
	    } last = task;
	  };
          };

          function PromiseCapability(C) {
	  let resolve; let reject;
	  this.promise = new C(($$resolve, $$reject) => {
	    if (resolve !== undefined || reject !== undefined) throw TypeError('Bad Promise constructor');
	    resolve = $$resolve;
	    reject = $$reject;
	  });
	  this.resolve = _aFunction(resolve);
	  this.reject = _aFunction(reject);
          }
          const f$2 = function (C) {
	  return new PromiseCapability(C);
          };
          const _newPromiseCapability = {
            f: f$2
          };

          const _perform = function (exec) {
	  try {
	    return { e: false, v: exec() };
	  } catch (e) {
	    return { e: true, v: e };
	  }
          };

          const navigator$1 = _global.navigator;
          const _userAgent = navigator$1 && navigator$1.userAgent || '';

          const _promiseResolve = function (C, x) {
	  _anObject(C);
	  if (_isObject(x) && x.constructor === C) return x;
	  const promiseCapability = _newPromiseCapability.f(C);
	  const { resolve } = promiseCapability;
	  resolve(x);
	  return promiseCapability.promise;
          };

          const _redefineAll = function (target, src, safe) {
	  for (const key in src) {
	    if (safe && target[key]) target[key] = src[key];
	    else _hide(target, key, src[key]);
	  } return target;
          };

          const SPECIES$1 = _wks('species');
          const _setSpecies = function (KEY) {
	  const C = typeof _core[KEY] === 'function' ? _core[KEY] : _global[KEY];
	  if (_descriptors && C && !C[SPECIES$1]) _objectDp.f(C, SPECIES$1, {
	    configurable: true,
	    get() {
                return this;
              }
	  });
          };

          const ITERATOR$3 = _wks('iterator');
          let SAFE_CLOSING = false;
          try {
	  const riter = [7][ITERATOR$3]();
	  riter.return = function () {
              SAFE_CLOSING = true;
            };
	  Array.from(riter, () => {
              throw 2;
            });
          } catch (e) {  }
          const _iterDetect = function (exec, skipClosing) {
	  if (!skipClosing && !SAFE_CLOSING) return false;
	  let safe = false;
	  try {
	    const arr = [7];
	    const iter = arr[ITERATOR$3]();
	    iter.next = function () {
                return { done: safe = true };
              };
	    arr[ITERATOR$3] = function () {
                return iter;
              };
	    exec(arr);
	  } catch (e) {  }
	  return safe;
          };

          const task = _task.set;
          const microtask = _microtask();
          const PROMISE = 'Promise';
          const TypeError$1 = _global.TypeError;
          const process$2 = _global.process;
          const versions = process$2 && process$2.versions;
          const v8 = versions && versions.v8 || '';
          let $Promise = _global[PROMISE];
          const isNode$1 = _classof(process$2) == 'process';
          const empty = function () {  };
          let Internal; let newGenericPromiseCapability; let OwnPromiseCapability; let Wrapper;
          let newPromiseCapability = newGenericPromiseCapability = _newPromiseCapability.f;
          const USE_NATIVE = !!(function () {
	  try {
	    const promise = $Promise.resolve(1);
	    const FakePromise = (promise.constructor = {})[_wks('species')] = function (exec) {
	      exec(empty, empty);
	    };
	    return (isNode$1 || typeof PromiseRejectionEvent === 'function')
	      && promise.then(empty) instanceof FakePromise
	      && v8.indexOf('6.6') !== 0
	      && _userAgent.indexOf('Chrome/66') === -1;
	  } catch (e) {  }
          }());
          const isThenable = function (it) {
	  let then;
	  return _isObject(it) && typeof (then = it.then) === 'function' ? then : false;
          };
          const notify = function (promise, isReject) {
	  if (promise._n) return;
	  promise._n = true;
	  const chain = promise._c;
	  microtask(() => {
	    const value = promise._v;
	    const ok = promise._s == 1;
	    let i = 0;
	    const run = function (reaction) {
	      const handler = ok ? reaction.ok : reaction.fail;
	      const { resolve } = reaction;
	      const { reject } = reaction;
	      const { domain } = reaction;
	      let result; let then; let exited;
	      try {
	        if (handler) {
	          if (!ok) {
	            if (promise._h == 2) onHandleUnhandled(promise);
	            promise._h = 1;
	          }
	          if (handler === true) result = value;
	          else {
	            if (domain) domain.enter();
	            result = handler(value);
	            if (domain) {
	              domain.exit();
	              exited = true;
	            }
	          }
	          if (result === reaction.promise) {
	            reject(TypeError$1('Promise-chain cycle'));
	          } else if (then = isThenable(result)) {
	            then.call(result, resolve, reject);
	          } else resolve(result);
	        } else reject(value);
	      } catch (e) {
	        if (domain && !exited) domain.exit();
	        reject(e);
	      }
	    };
	    while (chain.length > i) run(chain[i++]);
	    promise._c = [];
	    promise._n = false;
	    if (isReject && !promise._h) onUnhandled(promise);
	  });
          };
          var onUnhandled = function (promise) {
	  task.call(_global, () => {
	    const value = promise._v;
	    const unhandled = isUnhandled(promise);
	    let result; let handler; let console;
	    if (unhandled) {
	      result = _perform(() => {
	        if (isNode$1) {
	          process$2.emit('unhandledRejection', value, promise);
	        } else if (handler = _global.onunhandledrejection) {
	          handler({ promise, reason: value });
	        } else if ((console = _global.console) && console.error) {
	          console.error('Unhandled promise rejection', value);
	        }
	      });
	      promise._h = isNode$1 || isUnhandled(promise) ? 2 : 1;
	    } promise._a = undefined;
	    if (unhandled && result.e) throw result.v;
	  });
          };
          var isUnhandled = function (promise) {
	  return promise._h !== 1 && (promise._a || promise._c).length === 0;
          };
          var onHandleUnhandled = function (promise) {
	  task.call(_global, () => {
	    let handler;
	    if (isNode$1) {
	      process$2.emit('rejectionHandled', promise);
	    } else if (handler = _global.onrejectionhandled) {
	      handler({ promise, reason: promise._v });
	    }
	  });
          };
          const $reject = function (value) {
	  let promise = this;
	  if (promise._d) return;
	  promise._d = true;
	  promise = promise._w || promise;
	  promise._v = value;
	  promise._s = 2;
	  if (!promise._a) promise._a = promise._c.slice();
	  notify(promise, true);
          };
          var $resolve = function (value) {
	  let promise = this;
	  let then;
	  if (promise._d) return;
	  promise._d = true;
	  promise = promise._w || promise;
	  try {
	    if (promise === value) throw TypeError$1('Promise can\'t be resolved itself');
	    if (then = isThenable(value)) {
	      microtask(() => {
	        const wrapper = { _w: promise, _d: false };
	        try {
	          then.call(value, _ctx($resolve, wrapper, 1), _ctx($reject, wrapper, 1));
	        } catch (e) {
	          $reject.call(wrapper, e);
	        }
	      });
	    } else {
	      promise._v = value;
	      promise._s = 1;
	      notify(promise, false);
	    }
	  } catch (e) {
	    $reject.call({ _w: promise, _d: false }, e);
	  }
          };
          if (!USE_NATIVE) {
	  $Promise = function Promise(executor) {
	    _anInstance(this, $Promise, PROMISE, '_h');
	    _aFunction(executor);
	    Internal.call(this);
	    try {
	      executor(_ctx($resolve, this, 1), _ctx($reject, this, 1));
	    } catch (err) {
	      $reject.call(this, err);
	    }
	  };
	  Internal = function Promise(executor) {
	    this._c = [];
	    this._a = undefined;
	    this._s = 0;
	    this._d = false;
	    this._v = undefined;
	    this._h = 0;
	    this._n = false;
	  };
	  Internal.prototype = _redefineAll($Promise.prototype, {
	    then: function then(onFulfilled, onRejected) {
	      const reaction = newPromiseCapability(_speciesConstructor(this, $Promise));
	      reaction.ok = typeof onFulfilled === 'function' ? onFulfilled : true;
	      reaction.fail = typeof onRejected === 'function' && onRejected;
	      reaction.domain = isNode$1 ? process$2.domain : undefined;
	      this._c.push(reaction);
	      if (this._a) this._a.push(reaction);
	      if (this._s) notify(this, false);
	      return reaction.promise;
	    },
	    catch(onRejected) {
	      return this.then(undefined, onRejected);
	    }
	  });
	  OwnPromiseCapability = function () {
	    const promise = new Internal();
	    this.promise = promise;
	    this.resolve = _ctx($resolve, promise, 1);
	    this.reject = _ctx($reject, promise, 1);
	  };
	  _newPromiseCapability.f = newPromiseCapability = function (C) {
	    return C === $Promise || C === Wrapper
	      ? new OwnPromiseCapability(C)
	      : newGenericPromiseCapability(C);
	  };
          }
          _export(_export.G + _export.W + _export.F * !USE_NATIVE, { Promise: $Promise });
          _setToStringTag($Promise, PROMISE);
          _setSpecies(PROMISE);
          Wrapper = _core[PROMISE];
          _export(_export.S + _export.F * !USE_NATIVE, PROMISE, {
	  reject: function reject(r) {
	    const capability = newPromiseCapability(this);
	    const $$reject = capability.reject;
	    $$reject(r);
	    return capability.promise;
	  }
          });
          _export(_export.S + _export.F * (_library), PROMISE, {
	  resolve: function resolve(x) {
	    return _promiseResolve(this === Wrapper ? $Promise : this, x);
	  }
          });
          _export(_export.S + _export.F * !(USE_NATIVE && _iterDetect((iter) => {
	  $Promise.all(iter).catch(empty);
          })), PROMISE, {
	  all: function all(iterable) {
	    const C = this;
	    const capability = newPromiseCapability(C);
	    const { resolve } = capability;
	    const { reject } = capability;
	    const result = _perform(() => {
	      const values = [];
	      let index = 0;
	      let remaining = 1;
	      _forOf(iterable, false, (promise) => {
	        const $index = index++;
	        let alreadyCalled = false;
	        values.push(undefined);
	        remaining++;
	        C.resolve(promise).then((value) => {
	          if (alreadyCalled) return;
	          alreadyCalled = true;
	          values[$index] = value;
	          --remaining || resolve(values);
	        }, reject);
	      });
	      --remaining || resolve(values);
	    });
	    if (result.e) reject(result.v);
	    return capability.promise;
	  },
	  race: function race(iterable) {
	    const C = this;
	    const capability = newPromiseCapability(C);
	    const { reject } = capability;
	    const result = _perform(() => {
	      _forOf(iterable, false, (promise) => {
	        C.resolve(promise).then(capability.resolve, reject);
	      });
	    });
	    if (result.e) reject(result.v);
	    return capability.promise;
	  }
          });

          _export(_export.P + _export.R, 'Promise', { finally(onFinally) {
	  const C = _speciesConstructor(this, _core.Promise || _global.Promise);
	  const isFunction = typeof onFinally === 'function';
	  return this.then(
	    isFunction ? x => _promiseResolve(C, onFinally()).then(() => x) : onFinally,
	    isFunction ? e => _promiseResolve(C, onFinally()).then(() => {
                throw e;
              }) : onFinally
	  );
          } });

          _export(_export.S, 'Promise', { try(callbackfn) {
	  const promiseCapability = _newPromiseCapability.f(this);
	  const result = _perform(callbackfn);
	  (result.e ? promiseCapability.reject : promiseCapability.resolve)(result.v);
	  return promiseCapability.promise;
          } });

          const promise = _core.Promise;

          const promise$1 = promise;

          const _createProperty = function (object, index, value) {
	  if (index in object) _objectDp.f(object, index, _propertyDesc(0, value));
	  else object[index] = value;
          };

          _export(_export.S + _export.F * !_iterDetect((iter) => {
            Array.from(iter);
          }), 'Array', {
	  from: function from(arrayLike) {
	    const O = _toObject(arrayLike);
	    const C = typeof this === 'function' ? this : Array;
	    const aLen = arguments.length;
	    let mapfn = aLen > 1 ? arguments[1] : undefined;
	    const mapping = mapfn !== undefined;
	    let index = 0;
	    const iterFn = core_getIteratorMethod(O);
	    let length; let result; let step; let iterator;
	    if (mapping) mapfn = _ctx(mapfn, aLen > 2 ? arguments[2] : undefined, 2);
	    if (iterFn != undefined && !(C == Array && _isArrayIter(iterFn))) {
	      for (iterator = iterFn.call(O), result = new C(); !(step = iterator.next()).done; index++) {
	        _createProperty(result, index, mapping ? _iterCall(iterator, mapfn, [step.value, index], true) : step.value);
	      }
	    } else {
	      length = _toLength(O.length);
	      for (result = new C(length); length > index; index++) {
	        _createProperty(result, index, mapping ? mapfn(O[index], index) : O[index]);
	      }
	    }
	    result.length = index;
	    return result;
	  }
          });

          const from_1 = _core.Array.from;

          const from_1$1 = from_1;

          const runtime_1 = createCommonjsModule((module) => {
            const runtime = (function (exports) {
	  const Op = Object.prototype;
	  const hasOwn = Op.hasOwnProperty;
	  let undefined$1;
	  const $Symbol = typeof Symbol === 'function' ? Symbol : {};
	  const iteratorSymbol = $Symbol.iterator || '@@iterator';
	  const asyncIteratorSymbol = $Symbol.asyncIterator || '@@asyncIterator';
	  const toStringTagSymbol = $Symbol.toStringTag || '@@toStringTag';
	  function define(obj, key, value) {
	    Object.defineProperty(obj, key, {
	      value,
	      enumerable: true,
	      configurable: true,
	      writable: true
	    });
	    return obj[key];
	  }
	  try {
	    define({}, '');
	  } catch (err) {
	    define = function (obj, key, value) {
	      return obj[key] = value;
	    };
	  }
	  function wrap(innerFn, outerFn, self, tryLocsList) {
	    const protoGenerator = outerFn && outerFn.prototype instanceof Generator ? outerFn : Generator;
	    const generator = Object.create(protoGenerator.prototype);
	    const context = new Context(tryLocsList || []);
	    generator._invoke = makeInvokeMethod(innerFn, self, context);
	    return generator;
	  }
	  exports.wrap = wrap;
	  function tryCatch(fn, obj, arg) {
	    try {
	      return { type: 'normal', arg: fn.call(obj, arg) };
	    } catch (err) {
	      return { type: 'throw', arg: err };
	    }
	  }
	  const GenStateSuspendedStart = 'suspendedStart';
	  const GenStateSuspendedYield = 'suspendedYield';
	  const GenStateExecuting = 'executing';
	  const GenStateCompleted = 'completed';
	  const ContinueSentinel = {};
	  function Generator() {}
	  function GeneratorFunction() {}
	  function GeneratorFunctionPrototype() {}
	  let IteratorPrototype = {};
	  define(IteratorPrototype, iteratorSymbol, function () {
	    return this;
	  });
	  const getProto = Object.getPrototypeOf;
	  const NativeIteratorPrototype = getProto && getProto(getProto(values([])));
	  if (NativeIteratorPrototype
	      && NativeIteratorPrototype !== Op
	      && hasOwn.call(NativeIteratorPrototype, iteratorSymbol)) {
	    IteratorPrototype = NativeIteratorPrototype;
	  }
	  const Gp = GeneratorFunctionPrototype.prototype =	    Generator.prototype = Object.create(IteratorPrototype);
	  GeneratorFunction.prototype = GeneratorFunctionPrototype;
	  define(Gp, 'constructor', GeneratorFunctionPrototype);
	  define(GeneratorFunctionPrototype, 'constructor', GeneratorFunction);
	  GeneratorFunction.displayName = define(
	    GeneratorFunctionPrototype,
	    toStringTagSymbol,
	    'GeneratorFunction'
	  );
	  function defineIteratorMethods(prototype) {
	    ['next', 'throw', 'return'].forEach((method) => {
	      define(prototype, method, function (arg) {
	        return this._invoke(method, arg);
	      });
	    });
	  }
	  exports.isGeneratorFunction = function (genFun) {
	    const ctor = typeof genFun === 'function' && genFun.constructor;
	    return ctor
	      ? ctor === GeneratorFunction
	        || (ctor.displayName || ctor.name) === 'GeneratorFunction'
	      : false;
	  };
	  exports.mark = function (genFun) {
	    if (Object.setPrototypeOf) {
	      Object.setPrototypeOf(genFun, GeneratorFunctionPrototype);
	    } else {
	      genFun.__proto__ = GeneratorFunctionPrototype;
	      define(genFun, toStringTagSymbol, 'GeneratorFunction');
	    }
	    genFun.prototype = Object.create(Gp);
	    return genFun;
	  };
	  exports.awrap = function (arg) {
	    return { __await: arg };
	  };
	  function AsyncIterator(generator, PromiseImpl) {
	    function invoke(method, arg, resolve, reject) {
	      const record = tryCatch(generator[method], generator, arg);
	      if (record.type === 'throw') {
	        reject(record.arg);
	      } else {
	        const result = record.arg;
	        const { value } = result;
	        if (value
	            && typeof value === 'object'
	            && hasOwn.call(value, '__await')) {
	          return PromiseImpl.resolve(value.__await).then((value) => {
	            invoke('next', value, resolve, reject);
	          }, (err) => {
	            invoke('throw', err, resolve, reject);
	          });
	        }
	        return PromiseImpl.resolve(value).then((unwrapped) => {
	          result.value = unwrapped;
	          resolve(result);
	        }, error => invoke('throw', error, resolve, reject));
	      }
	    }
	    let previousPromise;
	    function enqueue(method, arg) {
	      function callInvokeWithMethodAndArg() {
	        return new PromiseImpl((resolve, reject) => {
	          invoke(method, arg, resolve, reject);
	        });
	      }
	      return previousPromise =	        previousPromise ? previousPromise.then(
	          callInvokeWithMethodAndArg,
	          callInvokeWithMethodAndArg
	        ) : callInvokeWithMethodAndArg();
	    }
	    this._invoke = enqueue;
	  }
	  defineIteratorMethods(AsyncIterator.prototype);
	  define(AsyncIterator.prototype, asyncIteratorSymbol, function () {
	    return this;
	  });
	  exports.AsyncIterator = AsyncIterator;
	  exports.async = function (innerFn, outerFn, self, tryLocsList, PromiseImpl) {
	    if (PromiseImpl === void 0) PromiseImpl = Promise;
	    const iter = new AsyncIterator(
	      wrap(innerFn, outerFn, self, tryLocsList),
	      PromiseImpl
	    );
	    return exports.isGeneratorFunction(outerFn)
	      ? iter
	      : iter.next().then(result => (result.done ? result.value : iter.next()));
	  };
	  function makeInvokeMethod(innerFn, self, context) {
	    let state = GenStateSuspendedStart;
	    return function invoke(method, arg) {
	      if (state === GenStateExecuting) {
	        throw new Error('Generator is already running');
	      }
	      if (state === GenStateCompleted) {
	        if (method === 'throw') {
	          throw arg;
	        }
	        return doneResult();
	      }
	      context.method = method;
	      context.arg = arg;
	      while (true) {
	        const { delegate } = context;
	        if (delegate) {
	          const delegateResult = maybeInvokeDelegate(delegate, context);
	          if (delegateResult) {
	            if (delegateResult === ContinueSentinel) continue;
	            return delegateResult;
	          }
	        }
	        if (context.method === 'next') {
	          context.sent = context._sent = context.arg;
	        } else if (context.method === 'throw') {
	          if (state === GenStateSuspendedStart) {
	            state = GenStateCompleted;
	            throw context.arg;
	          }
	          context.dispatchException(context.arg);
	        } else if (context.method === 'return') {
	          context.abrupt('return', context.arg);
	        }
	        state = GenStateExecuting;
	        const record = tryCatch(innerFn, self, context);
	        if (record.type === 'normal') {
	          state = context.done
	            ? GenStateCompleted
	            : GenStateSuspendedYield;
	          if (record.arg === ContinueSentinel) {
	            continue;
	          }
	          return {
	            value: record.arg,
	            done: context.done
	          };
	        } if (record.type === 'throw') {
	          state = GenStateCompleted;
	          context.method = 'throw';
	          context.arg = record.arg;
	        }
	      }
	    };
	  }
	  function maybeInvokeDelegate(delegate, context) {
	    const method = delegate.iterator[context.method];
	    if (method === undefined$1) {
	      context.delegate = null;
	      if (context.method === 'throw') {
	        if (delegate.iterator.return) {
	          context.method = 'return';
	          context.arg = undefined$1;
	          maybeInvokeDelegate(delegate, context);
	          if (context.method === 'throw') {
	            return ContinueSentinel;
	          }
	        }
	        context.method = 'throw';
	        context.arg = new TypeError('The iterator does not provide a \'throw\' method');
	      }
	      return ContinueSentinel;
	    }
	    const record = tryCatch(method, delegate.iterator, context.arg);
	    if (record.type === 'throw') {
	      context.method = 'throw';
	      context.arg = record.arg;
	      context.delegate = null;
	      return ContinueSentinel;
	    }
	    const info = record.arg;
	    if (! info) {
	      context.method = 'throw';
	      context.arg = new TypeError('iterator result is not an object');
	      context.delegate = null;
	      return ContinueSentinel;
	    }
	    if (info.done) {
	      context[delegate.resultName] = info.value;
	      context.next = delegate.nextLoc;
	      if (context.method !== 'return') {
	        context.method = 'next';
	        context.arg = undefined$1;
	      }
	    } else {
	      return info;
	    }
	    context.delegate = null;
	    return ContinueSentinel;
	  }
	  defineIteratorMethods(Gp);
	  define(Gp, toStringTagSymbol, 'Generator');
	  define(Gp, iteratorSymbol, function () {
	    return this;
	  });
	  define(Gp, 'toString', () => '[object Generator]');
	  function pushTryEntry(locs) {
	    const entry = { tryLoc: locs[0] };
	    if (1 in locs) {
	      entry.catchLoc = locs[1];
	    }
	    if (2 in locs) {
	      entry.finallyLoc = locs[2];
	      entry.afterLoc = locs[3];
	    }
	    this.tryEntries.push(entry);
	  }
	  function resetTryEntry(entry) {
	    const record = entry.completion || {};
	    record.type = 'normal';
	    delete record.arg;
	    entry.completion = record;
	  }
	  function Context(tryLocsList) {
	    this.tryEntries = [{ tryLoc: 'root' }];
	    tryLocsList.forEach(pushTryEntry, this);
	    this.reset(true);
	  }
	  exports.keys = function (object) {
	    const keys = [];
	    for (const key in object) {
	      keys.push(key);
	    }
	    keys.reverse();
	    return function next() {
	      while (keys.length) {
	        const key = keys.pop();
	        if (key in object) {
	          next.value = key;
	          next.done = false;
	          return next;
	        }
	      }
	      next.done = true;
	      return next;
	    };
	  };
	  function values(iterable) {
	    if (iterable) {
	      const iteratorMethod = iterable[iteratorSymbol];
	      if (iteratorMethod) {
	        return iteratorMethod.call(iterable);
	      }
	      if (typeof iterable.next === 'function') {
	        return iterable;
	      }
	      if (!isNaN(iterable.length)) {
	        let i = -1; const next = function next() {
	          while (++i < iterable.length) {
	            if (hasOwn.call(iterable, i)) {
	              next.value = iterable[i];
	              next.done = false;
	              return next;
	            }
	          }
	          next.value = undefined$1;
	          next.done = true;
	          return next;
	        };
	        return next.next = next;
	      }
	    }
	    return { next: doneResult };
	  }
	  exports.values = values;
	  function doneResult() {
	    return { value: undefined$1, done: true };
	  }
	  Context.prototype = {
	    constructor: Context,
	    reset(skipTempReset) {
	      this.prev = 0;
	      this.next = 0;
	      this.sent = this._sent = undefined$1;
	      this.done = false;
	      this.delegate = null;
	      this.method = 'next';
	      this.arg = undefined$1;
	      this.tryEntries.forEach(resetTryEntry);
	      if (!skipTempReset) {
	        for (const name in this) {
	          if (name.charAt(0) === 't'
	              && hasOwn.call(this, name)
	              && !isNaN(+name.slice(1))) {
	            this[name] = undefined$1;
	          }
	        }
	      }
	    },
	    stop() {
	      this.done = true;
	      const rootEntry = this.tryEntries[0];
	      const rootRecord = rootEntry.completion;
	      if (rootRecord.type === 'throw') {
	        throw rootRecord.arg;
	      }
	      return this.rval;
	    },
	    dispatchException(exception) {
	      if (this.done) {
	        throw exception;
	      }
	      const context = this;
	      function handle(loc, caught) {
	        record.type = 'throw';
	        record.arg = exception;
	        context.next = loc;
	        if (caught) {
	          context.method = 'next';
	          context.arg = undefined$1;
	        }
	        return !! caught;
	      }
	      for (let i = this.tryEntries.length - 1; i >= 0; --i) {
	        const entry = this.tryEntries[i];
	        var record = entry.completion;
	        if (entry.tryLoc === 'root') {
	          return handle('end');
	        }
	        if (entry.tryLoc <= this.prev) {
	          const hasCatch = hasOwn.call(entry, 'catchLoc');
	          const hasFinally = hasOwn.call(entry, 'finallyLoc');
	          if (hasCatch && hasFinally) {
	            if (this.prev < entry.catchLoc) {
	              return handle(entry.catchLoc, true);
	            } if (this.prev < entry.finallyLoc) {
	              return handle(entry.finallyLoc);
	            }
	          } else if (hasCatch) {
	            if (this.prev < entry.catchLoc) {
	              return handle(entry.catchLoc, true);
	            }
	          } else if (hasFinally) {
	            if (this.prev < entry.finallyLoc) {
	              return handle(entry.finallyLoc);
	            }
	          } else {
	            throw new Error('try statement without catch or finally');
	          }
	        }
	      }
	    },
	    abrupt(type, arg) {
	      for (let i = this.tryEntries.length - 1; i >= 0; --i) {
	        const entry = this.tryEntries[i];
	        if (entry.tryLoc <= this.prev
	            && hasOwn.call(entry, 'finallyLoc')
	            && this.prev < entry.finallyLoc) {
	          var finallyEntry = entry;
	          break;
	        }
	      }
	      if (finallyEntry
	          && (type === 'break'
	           || type === 'continue')
	          && finallyEntry.tryLoc <= arg
	          && arg <= finallyEntry.finallyLoc) {
	        finallyEntry = null;
	      }
	      const record = finallyEntry ? finallyEntry.completion : {};
	      record.type = type;
	      record.arg = arg;
	      if (finallyEntry) {
	        this.method = 'next';
	        this.next = finallyEntry.finallyLoc;
	        return ContinueSentinel;
	      }
	      return this.complete(record);
	    },
	    complete(record, afterLoc) {
	      if (record.type === 'throw') {
	        throw record.arg;
	      }
	      if (record.type === 'break'
	          || record.type === 'continue') {
	        this.next = record.arg;
	      } else if (record.type === 'return') {
	        this.rval = this.arg = record.arg;
	        this.method = 'return';
	        this.next = 'end';
	      } else if (record.type === 'normal' && afterLoc) {
	        this.next = afterLoc;
	      }
	      return ContinueSentinel;
	    },
	    finish(finallyLoc) {
	      for (let i = this.tryEntries.length - 1; i >= 0; --i) {
	        const entry = this.tryEntries[i];
	        if (entry.finallyLoc === finallyLoc) {
	          this.complete(entry.completion, entry.afterLoc);
	          resetTryEntry(entry);
	          return ContinueSentinel;
	        }
	      }
	    },
	    catch(tryLoc) {
	      for (let i = this.tryEntries.length - 1; i >= 0; --i) {
	        const entry = this.tryEntries[i];
	        if (entry.tryLoc === tryLoc) {
	          const record = entry.completion;
	          if (record.type === 'throw') {
	            var thrown = record.arg;
	            resetTryEntry(entry);
	          }
	          return thrown;
	        }
	      }
	      throw new Error('illegal catch attempt');
	    },
	    delegateYield(iterable, resultName, nextLoc) {
	      this.delegate = {
	        iterator: values(iterable),
	        resultName,
	        nextLoc
	      };
	      if (this.method === 'next') {
	        this.arg = undefined$1;
	      }
	      return ContinueSentinel;
	    }
	  };
	  return exports;
            }(module.exports));
            try {
	  regeneratorRuntime = runtime;
            } catch (accidentalStrictMode) {
	  if (typeof globalThis === 'object') {
	    globalThis.regeneratorRuntime = runtime;
	  } else {
	    Function('r', 'regeneratorRuntime = r')(runtime);
	  }
            }
          });

          const regenerator = runtime_1;

          const _stringWs = '\x09\x0A\x0B\x0C\x0D\x20\xA0\u1680\u180E\u2000\u2001\u2002\u2003'
	  + '\u2004\u2005\u2006\u2007\u2008\u2009\u200A\u202F\u205F\u3000\u2028\u2029\uFEFF';

          const space = `[${_stringWs}]`;
          const non = '\u200b\u0085';
          const ltrim = RegExp(`^${space}${space}*`);
          const rtrim = RegExp(`${space + space}*$`);
          const exporter = function (KEY, exec, ALIAS) {
	  const exp = {};
	  const FORCE = _fails(() => !!_stringWs[KEY]() || non[KEY]() != non);
	  const fn = exp[KEY] = FORCE ? exec(trim) : _stringWs[KEY];
	  if (ALIAS) exp[ALIAS] = fn;
	  _export(_export.P + _export.F * FORCE, 'String', exp);
          };
          var trim = exporter.trim = function (string, TYPE) {
	  string = String(_defined(string));
	  if (TYPE & 1) string = string.replace(ltrim, '');
	  if (TYPE & 2) string = string.replace(rtrim, '');
	  return string;
          };
          const _stringTrim = exporter;

          const $parseInt = _global.parseInt;
          const $trim = _stringTrim.trim;
          const hex = /^[-+]?0[xX]/;
          const _parseInt = $parseInt(`${_stringWs}08`) !== 8 || $parseInt(`${_stringWs}0x16`) !== 22 ? function parseInt(str, radix) {
	  const string = $trim(String(str), 3);
	  return $parseInt(string, (radix >>> 0) || (hex.test(string) ? 16 : 10));
          } : $parseInt;

          _export(_export.G + _export.F * (parseInt != _parseInt), { parseInt: _parseInt });

          const _parseInt$1 = _core.parseInt;

          const _parseInt$2 = _parseInt$1;

          const _objectSap = function (KEY, exec) {
	  const fn = (_core.Object || {})[KEY] || Object[KEY];
	  const exp = {};
	  exp[KEY] = exec(fn);
	  _export(_export.S + _export.F * _fails(() => {
              fn(1);
            }), 'Object', exp);
          };

          _objectSap('keys', () => function keys(it) {
	    return _objectKeys(_toObject(it));
	  });

          const { keys } = _core.Object;

          const keys$1 = keys;

          function throttle(delay, noTrailing, callback, debounceMode) {
	  let timeoutID;
	  let cancelled = false;
	  let lastExec = 0;
	  function clearExistingTimeout() {
	    if (timeoutID) {
	      clearTimeout(timeoutID);
	    }
	  }
	  function cancel() {
	    clearExistingTimeout();
	    cancelled = true;
	  }
	  if (typeof noTrailing !== 'boolean') {
	    debounceMode = callback;
	    callback = noTrailing;
	    noTrailing = undefined;
	  }
	  function wrapper() {
	    const self = this;
	    const elapsed = Date.now() - lastExec;
	    const args = arguments;
	    if (cancelled) {
	      return;
	    }
	    function exec() {
	      lastExec = Date.now();
	      callback.apply(self, args);
	    }
	    function clear() {
	      timeoutID = undefined;
	    }
	    if (debounceMode && !timeoutID) {
	      exec();
	    }
	    clearExistingTimeout();
	    if (debounceMode === undefined && elapsed > delay) {
	      exec();
	    } else if (noTrailing !== true) {
	      timeoutID = setTimeout(debounceMode ? clear : exec, debounceMode === undefined ? delay - elapsed : delay);
	    }
	  }
	  wrapper.cancel = cancel;
	  return wrapper;
          }
          function debounce(delay, atBegin, callback) {
	  return callback === undefined ? throttle(delay, atBegin, false) : throttle(delay, callback, atBegin !== false);
          }

          const _isArray = Array.isArray || function isArray(arg) {
	  return _cof(arg) == 'Array';
          };

          _export(_export.S, 'Array', { isArray: _isArray });

          const { isArray } = _core.Array;

          const isArray$1 = isArray;

          const f$3 = Object.getOwnPropertySymbols;
          const _objectGops = {
            f: f$3
          };

          const $assign = Object.assign;
          const _objectAssign = !$assign || _fails(() => {
	  const A = {};
	  const B = {};
	  const S = Symbol();
	  const K = 'abcdefghijklmnopqrst';
	  A[S] = 7;
	  K.split('').forEach((k) => {
              B[k] = k;
            });
	  return $assign({}, A)[S] != 7 || Object.keys($assign({}, B)).join('') != K;
          }) ? function assign(target, source) {
	  const T = _toObject(target);
	  const aLen = arguments.length;
	  let index = 1;
	  const getSymbols = _objectGops.f;
	  const isEnum = _objectPie.f;
	  while (aLen > index) {
	    const S = _iobject(arguments[index++]);
	    const keys = getSymbols ? _objectKeys(S).concat(getSymbols(S)) : _objectKeys(S);
	    const { length } = keys;
	    let j = 0;
	    var key;
	    while (length > j) {
	      key = keys[j++];
	      if (!_descriptors || isEnum.call(S, key)) T[key] = S[key];
	    }
	  } return T;
            } : $assign;

          _export(_export.S + _export.F, 'Object', { assign: _objectAssign });

          const { assign } = _core.Object;

          const assign$1 = assign;

          const $parseFloat = _global.parseFloat;
          const $trim$1 = _stringTrim.trim;
          const _parseFloat = 1 / $parseFloat(`${_stringWs}-0`) !== -Infinity ? function parseFloat(str) {
	  const string = $trim$1(String(str), 3);
	  const result = $parseFloat(string);
	  return result === 0 && string.charAt(0) == '-' ? -0 : result;
          } : $parseFloat;

          _export(_export.G + _export.F * (parseFloat != _parseFloat), { parseFloat: _parseFloat });

          const _parseFloat$1 = _core.parseFloat;

          const _parseFloat$2 = _parseFloat$1;

          const isBrowser = typeof window !== 'undefined' && typeof document !== 'undefined';
          const longerTimeoutBrowsers = ['Edge', 'Trident', 'Firefox'];
          let timeoutDuration = 0;
          for (let i$1 = 0; i$1 < longerTimeoutBrowsers.length; i$1 += 1) {
	  if (isBrowser && navigator.userAgent.indexOf(longerTimeoutBrowsers[i$1]) >= 0) {
	    timeoutDuration = 1;
	    break;
	  }
          }
          function microtaskDebounce(fn) {
	  let called = false;
	  return function () {
	    if (called) {
	      return;
	    }
	    called = true;
	    window.Promise.resolve().then(() => {
	      called = false;
	      fn();
	    });
	  };
          }
          function taskDebounce(fn) {
	  let scheduled = false;
	  return function () {
	    if (!scheduled) {
	      scheduled = true;
	      setTimeout(() => {
	        scheduled = false;
	        fn();
	      }, timeoutDuration);
	    }
	  };
          }
          const supportsMicroTasks = isBrowser && window.Promise;
          const debounce$1 = supportsMicroTasks ? microtaskDebounce : taskDebounce;
          function isFunction(functionToCheck) {
	  const getType = {};
	  return functionToCheck && getType.toString.call(functionToCheck) === '[object Function]';
          }
          function getStyleComputedProperty(element, property) {
	  if (element.nodeType !== 1) {
	    return [];
	  }
	  const window = element.ownerDocument.defaultView;
	  const css = window.getComputedStyle(element, null);
	  return property ? css[property] : css;
          }
          function getParentNode(element) {
	  if (element.nodeName === 'HTML') {
	    return element;
	  }
	  return element.parentNode || element.host;
          }
          function getScrollParent(element) {
	  if (!element) {
	    return document.body;
	  }
	  switch (element.nodeName) {
	    case 'HTML':
	    case 'BODY':
	      return element.ownerDocument.body;
	    case '#document':
	      return element.body;
	  }
	  const _getStyleComputedProp = getStyleComputedProperty(element);
	      const { overflow } = _getStyleComputedProp;
	      const { overflowX } = _getStyleComputedProp;
	      const { overflowY } = _getStyleComputedProp;
	  if (/(auto|scroll|overlay)/.test(overflow + overflowY + overflowX)) {
	    return element;
	  }
	  return getScrollParent(getParentNode(element));
          }
          const isIE11 = isBrowser && !!(window.MSInputMethodContext && document.documentMode);
          const isIE10 = isBrowser && /MSIE 10/.test(navigator.userAgent);
          function isIE(version) {
	  if (version === 11) {
	    return isIE11;
	  }
	  if (version === 10) {
	    return isIE10;
	  }
	  return isIE11 || isIE10;
          }
          function getOffsetParent(element) {
	  if (!element) {
	    return document.documentElement;
	  }
	  const noOffsetParent = isIE(10) ? document.body : null;
	  let offsetParent = element.offsetParent || null;
	  while (offsetParent === noOffsetParent && element.nextElementSibling) {
	    offsetParent = (element = element.nextElementSibling).offsetParent;
	  }
	  const nodeName = offsetParent && offsetParent.nodeName;
	  if (!nodeName || nodeName === 'BODY' || nodeName === 'HTML') {
	    return element ? element.ownerDocument.documentElement : document.documentElement;
	  }
	  if (['TH', 'TD', 'TABLE'].indexOf(offsetParent.nodeName) !== -1 && getStyleComputedProperty(offsetParent, 'position') === 'static') {
	    return getOffsetParent(offsetParent);
	  }
	  return offsetParent;
          }
          function isOffsetContainer(element) {
	  const { nodeName } = element;
	  if (nodeName === 'BODY') {
	    return false;
	  }
	  return nodeName === 'HTML' || getOffsetParent(element.firstElementChild) === element;
          }
          function getRoot(node) {
	  if (node.parentNode !== null) {
	    return getRoot(node.parentNode);
	  }
	  return node;
          }
          function findCommonOffsetParent(element1, element2) {
	  if (!element1 || !element1.nodeType || !element2 || !element2.nodeType) {
	    return document.documentElement;
	  }
	  const order = element1.compareDocumentPosition(element2) & Node.DOCUMENT_POSITION_FOLLOWING;
	  const start = order ? element1 : element2;
	  const end = order ? element2 : element1;
	  const range = document.createRange();
	  range.setStart(start, 0);
	  range.setEnd(end, 0);
	  const { commonAncestorContainer } = range;
	  if (element1 !== commonAncestorContainer && element2 !== commonAncestorContainer || start.contains(end)) {
	    if (isOffsetContainer(commonAncestorContainer)) {
	      return commonAncestorContainer;
	    }
	    return getOffsetParent(commonAncestorContainer);
	  }
	  const element1root = getRoot(element1);
	  if (element1root.host) {
	    return findCommonOffsetParent(element1root.host, element2);
	  }
	    return findCommonOffsetParent(element1, getRoot(element2).host);
          }
          function getScroll(element) {
	  const side = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : 'top';
	  const upperSide = side === 'top' ? 'scrollTop' : 'scrollLeft';
	  const { nodeName } = element;
	  if (nodeName === 'BODY' || nodeName === 'HTML') {
	    const html = element.ownerDocument.documentElement;
	    const scrollingElement = element.ownerDocument.scrollingElement || html;
	    return scrollingElement[upperSide];
	  }
	  return element[upperSide];
          }
          function includeScroll(rect, element) {
	  const subtract = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : false;
	  const scrollTop = getScroll(element, 'top');
	  const scrollLeft = getScroll(element, 'left');
	  const modifier = subtract ? -1 : 1;
	  rect.top += scrollTop * modifier;
	  rect.bottom += scrollTop * modifier;
	  rect.left += scrollLeft * modifier;
	  rect.right += scrollLeft * modifier;
	  return rect;
          }
          function getBordersSize(styles, axis) {
	  const sideA = axis === 'x' ? 'Left' : 'Top';
	  const sideB = sideA === 'Left' ? 'Right' : 'Bottom';
	  return _parseFloat$2(styles['border'.concat(sideA, 'Width')], 10) + _parseFloat$2(styles['border'.concat(sideB, 'Width')], 10);
          }
          function getSize(axis, body, html, computedStyle) {
	  return Math.max(body['offset'.concat(axis)], body['scroll'.concat(axis)], html['client'.concat(axis)], html['offset'.concat(axis)], html['scroll'.concat(axis)], isIE(10) ? _parseInt$2(html['offset'.concat(axis)]) + _parseInt$2(computedStyle['margin'.concat(axis === 'Height' ? 'Top' : 'Left')]) + _parseInt$2(computedStyle['margin'.concat(axis === 'Height' ? 'Bottom' : 'Right')]) : 0);
          }
          function getWindowSizes(document) {
	  const { body } = document;
	  const html = document.documentElement;
	  const computedStyle = isIE(10) && getComputedStyle(html);
	  return {
	    height: getSize('Height', body, html, computedStyle),
	    width: getSize('Width', body, html, computedStyle)
	  };
          }
          const _extends$1 = assign$1 || function (target) {
	  for (let i = 1; i < arguments.length; i++) {
	    const source = arguments[i];
	    for (const key in source) {
	      if (Object.prototype.hasOwnProperty.call(source, key)) {
	        target[key] = source[key];
	      }
	    }
	  }
	  return target;
          };
          function getClientRect(offsets) {
	  return _extends$1({}, offsets, {
	    right: offsets.left + offsets.width,
	    bottom: offsets.top + offsets.height
	  });
          }
          function getBoundingClientRect(element) {
	  let rect = {};
	  try {
	    if (isIE(10)) {
	      rect = element.getBoundingClientRect();
	      const scrollTop = getScroll(element, 'top');
	      const scrollLeft = getScroll(element, 'left');
	      rect.top += scrollTop;
	      rect.left += scrollLeft;
	      rect.bottom += scrollTop;
	      rect.right += scrollLeft;
	    } else {
	      rect = element.getBoundingClientRect();
	    }
	  } catch (e) {}
	  const result = {
	    left: rect.left,
	    top: rect.top,
	    width: rect.right - rect.left,
	    height: rect.bottom - rect.top
	  };
	  const sizes = element.nodeName === 'HTML' ? getWindowSizes(element.ownerDocument) : {};
	  const width = sizes.width || element.clientWidth || result.right - result.left;
	  const height = sizes.height || element.clientHeight || result.bottom - result.top;
	  let horizScrollbar = element.offsetWidth - width;
	  let vertScrollbar = element.offsetHeight - height;
	  if (horizScrollbar || vertScrollbar) {
	    const styles = getStyleComputedProperty(element);
	    horizScrollbar -= getBordersSize(styles, 'x');
	    vertScrollbar -= getBordersSize(styles, 'y');
	    result.width -= horizScrollbar;
	    result.height -= vertScrollbar;
	  }
	  return getClientRect(result);
          }
          function getOffsetRectRelativeToArbitraryNode(children, parent) {
	  const fixedPosition = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : false;
	  const isIE10 = isIE(10);
	  const isHTML = parent.nodeName === 'HTML';
	  const childrenRect = getBoundingClientRect(children);
	  const parentRect = getBoundingClientRect(parent);
	  const scrollParent = getScrollParent(children);
	  const styles = getStyleComputedProperty(parent);
	  const borderTopWidth = _parseFloat$2(styles.borderTopWidth, 10);
	  const borderLeftWidth = _parseFloat$2(styles.borderLeftWidth, 10);
	  if (fixedPosition && isHTML) {
	    parentRect.top = Math.max(parentRect.top, 0);
	    parentRect.left = Math.max(parentRect.left, 0);
	  }
	  let offsets = getClientRect({
	    top: childrenRect.top - parentRect.top - borderTopWidth,
	    left: childrenRect.left - parentRect.left - borderLeftWidth,
	    width: childrenRect.width,
	    height: childrenRect.height
	  });
	  offsets.marginTop = 0;
	  offsets.marginLeft = 0;
	  if (!isIE10 && isHTML) {
	    const marginTop = _parseFloat$2(styles.marginTop, 10);
	    const marginLeft = _parseFloat$2(styles.marginLeft, 10);
	    offsets.top -= borderTopWidth - marginTop;
	    offsets.bottom -= borderTopWidth - marginTop;
	    offsets.left -= borderLeftWidth - marginLeft;
	    offsets.right -= borderLeftWidth - marginLeft;
	    offsets.marginTop = marginTop;
	    offsets.marginLeft = marginLeft;
	  }
	  if (isIE10 && !fixedPosition ? parent.contains(scrollParent) : parent === scrollParent && scrollParent.nodeName !== 'BODY') {
	    offsets = includeScroll(offsets, parent);
	  }
	  return offsets;
          }
          function getViewportOffsetRectRelativeToArtbitraryNode(element) {
	  const excludeScroll = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : false;
	  const html = element.ownerDocument.documentElement;
	  const relativeOffset = getOffsetRectRelativeToArbitraryNode(element, html);
	  const width = Math.max(html.clientWidth, window.innerWidth || 0);
	  const height = Math.max(html.clientHeight, window.innerHeight || 0);
	  const scrollTop = !excludeScroll ? getScroll(html) : 0;
	  const scrollLeft = !excludeScroll ? getScroll(html, 'left') : 0;
	  const offset = {
	    top: scrollTop - relativeOffset.top + relativeOffset.marginTop,
	    left: scrollLeft - relativeOffset.left + relativeOffset.marginLeft,
	    width,
	    height
	  };
	  return getClientRect(offset);
          }
          function isFixed(element) {
	  const { nodeName } = element;
	  if (nodeName === 'BODY' || nodeName === 'HTML') {
	    return false;
	  }
	  if (getStyleComputedProperty(element, 'position') === 'fixed') {
	    return true;
	  }
	  const parentNode = getParentNode(element);
	  if (!parentNode) {
	    return false;
	  }
	  return isFixed(parentNode);
          }
          function getFixedPositionOffsetParent(element) {
	  if (!element || !element.parentElement || isIE()) {
	    return document.documentElement;
	  }
	  let el = element.parentElement;
	  while (el && getStyleComputedProperty(el, 'transform') === 'none') {
	    el = el.parentElement;
	  }
	  return el || document.documentElement;
          }
          function getBoundaries(popper, reference, padding, boundariesElement) {
	  const fixedPosition = arguments.length > 4 && arguments[4] !== undefined ? arguments[4] : false;
	  let boundaries = {
	    top: 0,
	    left: 0
	  };
	  const offsetParent = fixedPosition ? getFixedPositionOffsetParent(popper) : findCommonOffsetParent(popper, reference);
	  if (boundariesElement === 'viewport') {
	    boundaries = getViewportOffsetRectRelativeToArtbitraryNode(offsetParent, fixedPosition);
	  } else {
	    let boundariesNode;
	    if (boundariesElement === 'scrollParent') {
	      boundariesNode = getScrollParent(getParentNode(reference));
	      if (boundariesNode.nodeName === 'BODY') {
	        boundariesNode = popper.ownerDocument.documentElement;
	      }
	    } else if (boundariesElement === 'window') {
	      boundariesNode = popper.ownerDocument.documentElement;
	    } else {
	      boundariesNode = boundariesElement;
	    }
	    const offsets = getOffsetRectRelativeToArbitraryNode(boundariesNode, offsetParent, fixedPosition);
	    if (boundariesNode.nodeName === 'HTML' && !isFixed(offsetParent)) {
	      const _getWindowSizes = getWindowSizes(popper.ownerDocument);
	          const { height } = _getWindowSizes;
	          const { width } = _getWindowSizes;
	      boundaries.top += offsets.top - offsets.marginTop;
	      boundaries.bottom = height + offsets.top;
	      boundaries.left += offsets.left - offsets.marginLeft;
	      boundaries.right = width + offsets.left;
	    } else {
	      boundaries = offsets;
	    }
	  }
	  padding = padding || 0;
	  const isPaddingNumber = typeof padding === 'number';
	  boundaries.left += isPaddingNumber ? padding : padding.left || 0;
	  boundaries.top += isPaddingNumber ? padding : padding.top || 0;
	  boundaries.right -= isPaddingNumber ? padding : padding.right || 0;
	  boundaries.bottom -= isPaddingNumber ? padding : padding.bottom || 0;
	  return boundaries;
          }
          function getArea(_ref) {
	  const { width } = _ref;
	      const { height } = _ref;
	  return width * height;
          }
          function computeAutoPlacement(placement, refRect, popper, reference, boundariesElement) {
	  const padding = arguments.length > 5 && arguments[5] !== undefined ? arguments[5] : 0;
	  if (placement.indexOf('auto') === -1) {
	    return placement;
	  }
	  const boundaries = getBoundaries(popper, reference, padding, boundariesElement);
	  const rects = {
	    top: {
	      width: boundaries.width,
	      height: refRect.top - boundaries.top
	    },
	    right: {
	      width: boundaries.right - refRect.right,
	      height: boundaries.height
	    },
	    bottom: {
	      width: boundaries.width,
	      height: boundaries.bottom - refRect.bottom
	    },
	    left: {
	      width: refRect.left - boundaries.left,
	      height: boundaries.height
	    }
	  };
	  const sortedAreas = keys$1(rects).map(key => _extends$1({
	      key
	    }, rects[key], {
	      area: getArea(rects[key])
	    }))
              .sort((a, b) => b.area - a.area);
	  const filteredAreas = sortedAreas.filter((_ref2) => {
	    const { width } = _ref2;
	        const { height } = _ref2;
	    return width >= popper.clientWidth && height >= popper.clientHeight;
	  });
	  const computedPlacement = filteredAreas.length > 0 ? filteredAreas[0].key : sortedAreas[0].key;
	  const variation = placement.split('-')[1];
	  return computedPlacement + (variation ? '-'.concat(variation) : '');
          }
          function getReferenceOffsets(state, popper, reference) {
	  const fixedPosition = arguments.length > 3 && arguments[3] !== undefined ? arguments[3] : null;
	  const commonOffsetParent = fixedPosition ? getFixedPositionOffsetParent(popper) : findCommonOffsetParent(popper, reference);
	  return getOffsetRectRelativeToArbitraryNode(reference, commonOffsetParent, fixedPosition);
          }
          function getOuterSizes(element) {
	  const window = element.ownerDocument.defaultView;
	  const styles = window.getComputedStyle(element);
	  const x = _parseFloat$2(styles.marginTop || 0) + _parseFloat$2(styles.marginBottom || 0);
	  const y = _parseFloat$2(styles.marginLeft || 0) + _parseFloat$2(styles.marginRight || 0);
	  const result = {
	    width: element.offsetWidth + y,
	    height: element.offsetHeight + x
	  };
	  return result;
          }
          function getOppositePlacement(placement) {
	  const hash = {
	    left: 'right',
	    right: 'left',
	    bottom: 'top',
	    top: 'bottom'
	  };
	  return placement.replace(/left|right|bottom|top/g, matched => hash[matched]);
          }
          function getPopperOffsets(popper, referenceOffsets, placement) {
	  placement = placement.split('-')[0];
	  const popperRect = getOuterSizes(popper);
	  const popperOffsets = {
	    width: popperRect.width,
	    height: popperRect.height
	  };
	  const isHoriz = ['right', 'left'].indexOf(placement) !== -1;
	  const mainSide = isHoriz ? 'top' : 'left';
	  const secondarySide = isHoriz ? 'left' : 'top';
	  const measurement = isHoriz ? 'height' : 'width';
	  const secondaryMeasurement = !isHoriz ? 'height' : 'width';
	  popperOffsets[mainSide] = referenceOffsets[mainSide] + referenceOffsets[measurement] / 2 - popperRect[measurement] / 2;
	  if (placement === secondarySide) {
	    popperOffsets[secondarySide] = referenceOffsets[secondarySide] - popperRect[secondaryMeasurement];
	  } else {
	    popperOffsets[secondarySide] = referenceOffsets[getOppositePlacement(secondarySide)];
	  }
	  return popperOffsets;
          }
          function find(arr, check) {
	  if (Array.prototype.find) {
	    return arr.find(check);
	  }
	  return arr.filter(check)[0];
          }
          function findIndex(arr, prop, value) {
	  if (Array.prototype.findIndex) {
	    return arr.findIndex(cur => cur[prop] === value);
	  }
	  const match = find(arr, obj => obj[prop] === value);
	  return arr.indexOf(match);
          }
          function runModifiers(modifiers, data, ends) {
	  const modifiersToRun = ends === undefined ? modifiers : modifiers.slice(0, findIndex(modifiers, 'name', ends));
	  modifiersToRun.forEach((modifier) => {
	    if (modifier.function) {
	      console.warn('`modifier.function` is deprecated, use `modifier.fn`!');
	    }
	    const fn = modifier.function || modifier.fn;
	    if (modifier.enabled && isFunction(fn)) {
	      data.offsets.popper = getClientRect(data.offsets.popper);
	      data.offsets.reference = getClientRect(data.offsets.reference);
	      data = fn(data, modifier);
	    }
	  });
	  return data;
          }
          function _update() {
	  if (this.state.isDestroyed) {
	    return;
	  }
	  let data = {
	    instance: this,
	    styles: {},
	    arrowStyles: {},
	    attributes: {},
	    flipped: false,
	    offsets: {}
	  };
	  data.offsets.reference = getReferenceOffsets(this.state, this.popper, this.reference, this.options.positionFixed);
	  data.placement = computeAutoPlacement(this.options.placement, data.offsets.reference, this.popper, this.reference, this.options.modifiers.flip.boundariesElement, this.options.modifiers.flip.padding);
	  data.originalPlacement = data.placement;
	  data.positionFixed = this.options.positionFixed;
	  data.offsets.popper = getPopperOffsets(this.popper, data.offsets.reference, data.placement);
	  data.offsets.popper.position = this.options.positionFixed ? 'fixed' : 'absolute';
	  data = runModifiers(this.modifiers, data);
	  if (!this.state.isCreated) {
	    this.state.isCreated = true;
	    this.options.onCreate(data);
	  } else {
	    this.options.onUpdate(data);
	  }
          }
          function isModifierEnabled(modifiers, modifierName) {
	  return modifiers.some((_ref3) => {
	    const { name } = _ref3;
	        const { enabled } = _ref3;
	    return enabled && name === modifierName;
	  });
          }
          function getSupportedPropertyName(property) {
	  const prefixes = [false, 'ms', 'Webkit', 'Moz', 'O'];
	  const upperProp = property.charAt(0).toUpperCase() + property.slice(1);
	  for (let _i = 0; _i < prefixes.length; _i++) {
	    const prefix = prefixes[_i];
	    const toCheck = prefix ? ''.concat(prefix).concat(upperProp) : property;
	    if (typeof document.body.style[toCheck] !== 'undefined') {
	      return toCheck;
	    }
	  }
	  return null;
          }
          function _destroy() {
	  this.state.isDestroyed = true;
	  if (isModifierEnabled(this.modifiers, 'applyStyle')) {
	    this.popper.removeAttribute('x-placement');
	    this.popper.style.position = '';
	    this.popper.style.top = '';
	    this.popper.style.left = '';
	    this.popper.style.right = '';
	    this.popper.style.bottom = '';
	    this.popper.style.willChange = '';
	    this.popper.style[getSupportedPropertyName('transform')] = '';
	  }
	  this.disableEventListeners();
	  if (this.options.removeOnDestroy) {
	    this.popper.parentNode.removeChild(this.popper);
	  }
	  return this;
          }
          function getWindow(element) {
	  const { ownerDocument } = element;
	  return ownerDocument ? ownerDocument.defaultView : window;
          }
          function attachToScrollParents(scrollParent, event, callback, scrollParents) {
	  const isBody = scrollParent.nodeName === 'BODY';
	  const target = isBody ? scrollParent.ownerDocument.defaultView : scrollParent;
	  target.addEventListener(event, callback, {
	    passive: true
	  });
	  if (!isBody) {
	    attachToScrollParents(getScrollParent(target.parentNode), event, callback, scrollParents);
	  }
	  scrollParents.push(target);
          }
          function setupEventListeners(reference, options, state, updateBound) {
	  state.updateBound = updateBound;
	  getWindow(reference).addEventListener('resize', state.updateBound, {
	    passive: true
	  });
	  const scrollElement = getScrollParent(reference);
	  attachToScrollParents(scrollElement, 'scroll', state.updateBound, state.scrollParents);
	  state.scrollElement = scrollElement;
	  state.eventsEnabled = true;
	  return state;
          }
          function _enableEventListeners() {
	  if (!this.state.eventsEnabled) {
	    this.state = setupEventListeners(this.reference, this.options, this.state, this.scheduleUpdate);
	  }
          }
          function removeEventListeners(reference, state) {
	  getWindow(reference).removeEventListener('resize', state.updateBound);
	  state.scrollParents.forEach((target) => {
	    target.removeEventListener('scroll', state.updateBound);
	  });
	  state.updateBound = null;
	  state.scrollParents = [];
	  state.scrollElement = null;
	  state.eventsEnabled = false;
	  return state;
          }
          function _disableEventListeners() {
	  if (this.state.eventsEnabled) {
	    cancelAnimationFrame(this.scheduleUpdate);
	    this.state = removeEventListeners(this.reference, this.state);
	  }
          }
          function isNumeric(n) {
	  return n !== '' && !isNaN(_parseFloat$2(n)) && isFinite(n);
          }
          function setStyles(element, styles) {
	  keys$1(styles).forEach((prop) => {
	    let unit = '';
	    if (['width', 'height', 'top', 'right', 'bottom', 'left'].indexOf(prop) !== -1 && isNumeric(styles[prop])) {
	      unit = 'px';
	    }
	    element.style[prop] = styles[prop] + unit;
	  });
          }
          function setAttributes(element, attributes) {
	  keys$1(attributes).forEach((prop) => {
	    const value = attributes[prop];
	    if (value !== false) {
	      element.setAttribute(prop, attributes[prop]);
	    } else {
	      element.removeAttribute(prop);
	    }
	  });
          }
          function applyStyle(data) {
	  setStyles(data.instance.popper, data.styles);
	  setAttributes(data.instance.popper, data.attributes);
	  if (data.arrowElement && keys$1(data.arrowStyles).length) {
	    setStyles(data.arrowElement, data.arrowStyles);
	  }
	  return data;
          }
          function applyStyleOnLoad(reference, popper, options, modifierOptions, state) {
	  const referenceOffsets = getReferenceOffsets(state, popper, reference, options.positionFixed);
	  const placement = computeAutoPlacement(options.placement, referenceOffsets, popper, reference, options.modifiers.flip.boundariesElement, options.modifiers.flip.padding);
	  popper.setAttribute('x-placement', placement);
	  setStyles(popper, {
	    position: options.positionFixed ? 'fixed' : 'absolute'
	  });
	  return options;
          }
          function getRoundedOffsets(data, shouldRound) {
	  const _data$offsets = data.offsets;
	      const { popper } = _data$offsets;
	      const { reference } = _data$offsets;
	  const { round } = Math;
	      const { floor } = Math;
	  const noRound = function noRound(v) {
	    return v;
	  };
	  const referenceWidth = round(reference.width);
	  const popperWidth = round(popper.width);
	  const isVertical = ['left', 'right'].indexOf(data.placement) !== -1;
	  const isVariation = data.placement.indexOf('-') !== -1;
	  const sameWidthParity = referenceWidth % 2 === popperWidth % 2;
	  const bothOddWidth = referenceWidth % 2 === 1 && popperWidth % 2 === 1;
	  const horizontalToInteger = !shouldRound ? noRound : isVertical || isVariation || sameWidthParity ? round : floor;
	  const verticalToInteger = !shouldRound ? noRound : round;
	  return {
	    left: horizontalToInteger(bothOddWidth && !isVariation && shouldRound ? popper.left - 1 : popper.left),
	    top: verticalToInteger(popper.top),
	    bottom: verticalToInteger(popper.bottom),
	    right: horizontalToInteger(popper.right)
	  };
          }
          const isFirefox = isBrowser && /Firefox/i.test(navigator.userAgent);
          function computeStyle(data, options) {
	  const { x } = options;
	      const { y } = options;
	  const { popper } = data.offsets;
	  const legacyGpuAccelerationOption = find(data.instance.modifiers, modifier => modifier.name === 'applyStyle').gpuAcceleration;
	  if (legacyGpuAccelerationOption !== undefined) {
	    console.warn('WARNING: `gpuAcceleration` option moved to `computeStyle` modifier and will not be supported in future versions of Popper.js!');
	  }
	  const gpuAcceleration = legacyGpuAccelerationOption !== undefined ? legacyGpuAccelerationOption : options.gpuAcceleration;
	  const offsetParent = getOffsetParent(data.instance.popper);
	  const offsetParentRect = getBoundingClientRect(offsetParent);
	  const styles = {
	    position: popper.position
	  };
	  const offsets = getRoundedOffsets(data, window.devicePixelRatio < 2 || !isFirefox);
	  const sideA = x === 'bottom' ? 'top' : 'bottom';
	  const sideB = y === 'right' ? 'left' : 'right';
	  const prefixedProperty = getSupportedPropertyName('transform');
	  let left; let top;
	  if (sideA === 'bottom') {
	    if (offsetParent.nodeName === 'HTML') {
	      top = -offsetParent.clientHeight + offsets.bottom;
	    } else {
	      top = -offsetParentRect.height + offsets.bottom;
	    }
	  } else {
	    top = offsets.top;
	  }
	  if (sideB === 'right') {
	    if (offsetParent.nodeName === 'HTML') {
	      left = -offsetParent.clientWidth + offsets.right;
	    } else {
	      left = -offsetParentRect.width + offsets.right;
	    }
	  } else {
	    left = offsets.left;
	  }
	  if (gpuAcceleration && prefixedProperty) {
	    styles[prefixedProperty] = 'translate3d('.concat(left, 'px, ').concat(top, 'px, 0)');
	    styles[sideA] = 0;
	    styles[sideB] = 0;
	    styles.willChange = 'transform';
	  } else {
	    const invertTop = sideA === 'bottom' ? -1 : 1;
	    const invertLeft = sideB === 'right' ? -1 : 1;
	    styles[sideA] = top * invertTop;
	    styles[sideB] = left * invertLeft;
	    styles.willChange = ''.concat(sideA, ', ').concat(sideB);
	  }
	  const attributes = {
	    'x-placement': data.placement
	  };
	  data.attributes = _extends$1({}, attributes, data.attributes);
	  data.styles = _extends$1({}, styles, data.styles);
	  data.arrowStyles = _extends$1({}, data.offsets.arrow, data.arrowStyles);
	  return data;
          }
          function isModifierRequired(modifiers, requestingName, requestedName) {
	  const requesting = find(modifiers, (_ref4) => {
	    const { name } = _ref4;
	    return name === requestingName;
	  });
	  const isRequired = !!requesting && modifiers.some(modifier => modifier.name === requestedName && modifier.enabled && modifier.order < requesting.order);
	  if (!isRequired) {
	    const _requesting = '`'.concat(requestingName, '`');
	    const requested = '`'.concat(requestedName, '`');
	    console.warn(''.concat(requested, ' modifier is required by ').concat(_requesting, ' modifier in order to work, be sure to include it before ')
                .concat(_requesting, '!'));
	  }
	  return isRequired;
          }
          function arrow(data, options) {
	  let _data$offsets$arrow;
	  if (!isModifierRequired(data.instance.modifiers, 'arrow', 'keepTogether')) {
	    return data;
	  }
	  let arrowElement = options.element;
	  if (typeof arrowElement === 'string') {
	    arrowElement = data.instance.popper.querySelector(arrowElement);
	    if (!arrowElement) {
	      return data;
	    }
	  } else {
	    if (!data.instance.popper.contains(arrowElement)) {
	      console.warn('WARNING: `arrow.element` must be child of its popper element!');
	      return data;
	    }
	  }
	  const placement = data.placement.split('-')[0];
	  const _data$offsets2 = data.offsets;
	      const { popper } = _data$offsets2;
	      const { reference } = _data$offsets2;
	  const isVertical = ['left', 'right'].indexOf(placement) !== -1;
	  const len = isVertical ? 'height' : 'width';
	  const sideCapitalized = isVertical ? 'Top' : 'Left';
	  const side = sideCapitalized.toLowerCase();
	  const altSide = isVertical ? 'left' : 'top';
	  const opSide = isVertical ? 'bottom' : 'right';
	  const arrowElementSize = getOuterSizes(arrowElement)[len];
	  if (reference[opSide] - arrowElementSize < popper[side]) {
	    data.offsets.popper[side] -= popper[side] - (reference[opSide] - arrowElementSize);
	  }
	  if (reference[side] + arrowElementSize > popper[opSide]) {
	    data.offsets.popper[side] += reference[side] + arrowElementSize - popper[opSide];
	  }
	  data.offsets.popper = getClientRect(data.offsets.popper);
	  const center = reference[side] + reference[len] / 2 - arrowElementSize / 2;
	  const css = getStyleComputedProperty(data.instance.popper);
	  const popperMarginSide = _parseFloat$2(css['margin'.concat(sideCapitalized)], 10);
	  const popperBorderSide = _parseFloat$2(css['border'.concat(sideCapitalized, 'Width')], 10);
	  let sideValue = center - data.offsets.popper[side] - popperMarginSide - popperBorderSide;
	  sideValue = Math.max(Math.min(popper[len] - arrowElementSize, sideValue), 0);
	  data.arrowElement = arrowElement;
	  data.offsets.arrow = (_data$offsets$arrow = {}, _defineProperty(_data$offsets$arrow, side, Math.round(sideValue)), _defineProperty(_data$offsets$arrow, altSide, ''), _data$offsets$arrow);
	  return data;
          }
          function getOppositeVariation(variation) {
	  if (variation === 'end') {
	    return 'start';
	  } if (variation === 'start') {
	    return 'end';
	  }
	  return variation;
          }
          const placements = ['auto-start', 'auto', 'auto-end', 'top-start', 'top', 'top-end', 'right-start', 'right', 'right-end', 'bottom-end', 'bottom', 'bottom-start', 'left-end', 'left', 'left-start'];
          const validPlacements = placements.slice(3);
          function clockwise(placement) {
	  const counter = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : false;
	  const index = validPlacements.indexOf(placement);
	  const arr = validPlacements.slice(index + 1).concat(validPlacements.slice(0, index));
	  return counter ? arr.reverse() : arr;
          }
          const BEHAVIORS = {
	  FLIP: 'flip',
	  CLOCKWISE: 'clockwise',
	  COUNTERCLOCKWISE: 'counterclockwise'
          };
          function flip(data, options) {
	  if (isModifierEnabled(data.instance.modifiers, 'inner')) {
	    return data;
	  }
	  if (data.flipped && data.placement === data.originalPlacement) {
	    return data;
	  }
	  const boundaries = getBoundaries(data.instance.popper, data.instance.reference, options.padding, options.boundariesElement, data.positionFixed);
	  let placement = data.placement.split('-')[0];
	  let placementOpposite = getOppositePlacement(placement);
	  let variation = data.placement.split('-')[1] || '';
	  let flipOrder = [];
	  switch (options.behavior) {
	    case BEHAVIORS.FLIP:
	      flipOrder = [placement, placementOpposite];
	      break;
	    case BEHAVIORS.CLOCKWISE:
	      flipOrder = clockwise(placement);
	      break;
	    case BEHAVIORS.COUNTERCLOCKWISE:
	      flipOrder = clockwise(placement, true);
	      break;
	    default:
	      flipOrder = options.behavior;
	  }
	  flipOrder.forEach((step, index) => {
	    if (placement !== step || flipOrder.length === index + 1) {
	      return data;
	    }
	    placement = data.placement.split('-')[0];
	    placementOpposite = getOppositePlacement(placement);
	    const popperOffsets = data.offsets.popper;
	    const refOffsets = data.offsets.reference;
	    const { floor } = Math;
	    const overlapsRef = placement === 'left' && floor(popperOffsets.right) > floor(refOffsets.left) || placement === 'right' && floor(popperOffsets.left) < floor(refOffsets.right) || placement === 'top' && floor(popperOffsets.bottom) > floor(refOffsets.top) || placement === 'bottom' && floor(popperOffsets.top) < floor(refOffsets.bottom);
	    const overflowsLeft = floor(popperOffsets.left) < floor(boundaries.left);
	    const overflowsRight = floor(popperOffsets.right) > floor(boundaries.right);
	    const overflowsTop = floor(popperOffsets.top) < floor(boundaries.top);
	    const overflowsBottom = floor(popperOffsets.bottom) > floor(boundaries.bottom);
	    const overflowsBoundaries = placement === 'left' && overflowsLeft || placement === 'right' && overflowsRight || placement === 'top' && overflowsTop || placement === 'bottom' && overflowsBottom;
	    const isVertical = ['top', 'bottom'].indexOf(placement) !== -1;
	    const flippedVariationByRef = !!options.flipVariations && (isVertical && variation === 'start' && overflowsLeft || isVertical && variation === 'end' && overflowsRight || !isVertical && variation === 'start' && overflowsTop || !isVertical && variation === 'end' && overflowsBottom);
	    const flippedVariationByContent = !!options.flipVariationsByContent && (isVertical && variation === 'start' && overflowsRight || isVertical && variation === 'end' && overflowsLeft || !isVertical && variation === 'start' && overflowsBottom || !isVertical && variation === 'end' && overflowsTop);
	    const flippedVariation = flippedVariationByRef || flippedVariationByContent;
	    if (overlapsRef || overflowsBoundaries || flippedVariation) {
	      data.flipped = true;
	      if (overlapsRef || overflowsBoundaries) {
	        placement = flipOrder[index + 1];
	      }
	      if (flippedVariation) {
	        variation = getOppositeVariation(variation);
	      }
	      data.placement = placement + (variation ? `-${variation}` : '');
	      data.offsets.popper = _extends$1({}, data.offsets.popper, getPopperOffsets(data.instance.popper, data.offsets.reference, data.placement));
	      data = runModifiers(data.instance.modifiers, data, 'flip');
	    }
	  });
	  return data;
          }
          function keepTogether(data) {
	  const _data$offsets3 = data.offsets;
	      const { popper } = _data$offsets3;
	      const { reference } = _data$offsets3;
	  const placement = data.placement.split('-')[0];
	  const { floor } = Math;
	  const isVertical = ['top', 'bottom'].indexOf(placement) !== -1;
	  const side = isVertical ? 'right' : 'bottom';
	  const opSide = isVertical ? 'left' : 'top';
	  const measurement = isVertical ? 'width' : 'height';
	  if (popper[side] < floor(reference[opSide])) {
	    data.offsets.popper[opSide] = floor(reference[opSide]) - popper[measurement];
	  }
	  if (popper[opSide] > floor(reference[side])) {
	    data.offsets.popper[opSide] = floor(reference[side]);
	  }
	  return data;
          }
          function toValue(str, measurement, popperOffsets, referenceOffsets) {
	  const split = str.match(/((?:\-|\+)?\d*\.?\d*)(.*)/);
	  const value = +split[1];
	  const unit = split[2];
	  if (!value) {
	    return str;
	  }
	  if (unit.indexOf('%') === 0) {
	    let element;
	    switch (unit) {
	      case '%p':
	        element = popperOffsets;
	        break;
	      case '%':
	      case '%r':
	      default:
	        element = referenceOffsets;
	    }
	    const rect = getClientRect(element);
	    return rect[measurement] / 100 * value;
	  } if (unit === 'vh' || unit === 'vw') {
	    let size;
	    if (unit === 'vh') {
	      size = Math.max(document.documentElement.clientHeight, window.innerHeight || 0);
	    } else {
	      size = Math.max(document.documentElement.clientWidth, window.innerWidth || 0);
	    }
	    return size / 100 * value;
	  }
	    return value;
          }
          function parseOffset(offset, popperOffsets, referenceOffsets, basePlacement) {
	  const offsets = [0, 0];
	  const useHeight = ['right', 'left'].indexOf(basePlacement) !== -1;
	  const fragments = offset.split(/(\+|\-)/).map(frag => frag.trim());
	  const divider = fragments.indexOf(find(fragments, frag => frag.search(/,|\s/) !== -1));
	  if (fragments[divider] && fragments[divider].indexOf(',') === -1) {
	    console.warn('Offsets separated by white space(s) are deprecated, use a comma (,) instead.');
	  }
	  const splitRegex = /\s*,\s*|\s+/;
	  let ops = divider !== -1 ? [fragments.slice(0, divider).concat([fragments[divider].split(splitRegex)[0]]), [fragments[divider].split(splitRegex)[1]].concat(fragments.slice(divider + 1))] : [fragments];
	  ops = ops.map((op, index) => {
	    const measurement = (index === 1 ? !useHeight : useHeight) ? 'height' : 'width';
	    let mergeWithPrevious = false;
	    return op
	    .reduce((a, b) => {
	      if (a[a.length - 1] === '' && ['+', '-'].indexOf(b) !== -1) {
	        a[a.length - 1] = b;
	        mergeWithPrevious = true;
	        return a;
	      } if (mergeWithPrevious) {
	        a[a.length - 1] += b;
	        mergeWithPrevious = false;
	        return a;
	      }
	        return a.concat(b);
	    }, [])
	    .map(str => toValue(str, measurement, popperOffsets, referenceOffsets));
	  });
	  ops.forEach((op, index) => {
	    op.forEach((frag, index2) => {
	      if (isNumeric(frag)) {
	        offsets[index] += frag * (op[index2 - 1] === '-' ? -1 : 1);
	      }
	    });
	  });
	  return offsets;
          }
          function offset(data, _ref5) {
	  const { offset } = _ref5;
	  const { placement } = data;
	      const _data$offsets4 = data.offsets;
	      const { popper } = _data$offsets4;
	      const { reference } = _data$offsets4;
	  const basePlacement = placement.split('-')[0];
	  let offsets;
	  if (isNumeric(+offset)) {
	    offsets = [+offset, 0];
	  } else {
	    offsets = parseOffset(offset, popper, reference, basePlacement);
	  }
	  if (basePlacement === 'left') {
	    popper.top += offsets[0];
	    popper.left -= offsets[1];
	  } else if (basePlacement === 'right') {
	    popper.top += offsets[0];
	    popper.left += offsets[1];
	  } else if (basePlacement === 'top') {
	    popper.left += offsets[0];
	    popper.top -= offsets[1];
	  } else if (basePlacement === 'bottom') {
	    popper.left += offsets[0];
	    popper.top += offsets[1];
	  }
	  data.popper = popper;
	  return data;
          }
          function preventOverflow(data, options) {
	  let boundariesElement = options.boundariesElement || getOffsetParent(data.instance.popper);
	  if (data.instance.reference === boundariesElement) {
	    boundariesElement = getOffsetParent(boundariesElement);
	  }
	  const transformProp = getSupportedPropertyName('transform');
	  const popperStyles = data.instance.popper.style;
	  const { top } = popperStyles;
	      const { left } = popperStyles;
	      const transform = popperStyles[transformProp];
	  popperStyles.top = '';
	  popperStyles.left = '';
	  popperStyles[transformProp] = '';
	  const boundaries = getBoundaries(data.instance.popper, data.instance.reference, options.padding, boundariesElement, data.positionFixed);
	  popperStyles.top = top;
	  popperStyles.left = left;
	  popperStyles[transformProp] = transform;
	  options.boundaries = boundaries;
	  const order = options.priority;
	  let { popper } = data.offsets;
	  const check = {
	    primary: function primary(placement) {
	      let value = popper[placement];
	      if (popper[placement] < boundaries[placement] && !options.escapeWithReference) {
	        value = Math.max(popper[placement], boundaries[placement]);
	      }
	      return _defineProperty({}, placement, value);
	    },
	    secondary: function secondary(placement) {
	      const mainSide = placement === 'right' ? 'left' : 'top';
	      let value = popper[mainSide];
	      if (popper[placement] > boundaries[placement] && !options.escapeWithReference) {
	        value = Math.min(popper[mainSide], boundaries[placement] - (placement === 'right' ? popper.width : popper.height));
	      }
	      return _defineProperty({}, mainSide, value);
	    }
	  };
	  order.forEach((placement) => {
	    const side = ['left', 'top'].indexOf(placement) !== -1 ? 'primary' : 'secondary';
	    popper = _extends$1({}, popper, check[side](placement));
	  });
	  data.offsets.popper = popper;
	  return data;
          }
          function shift(data) {
	  const { placement } = data;
	  const basePlacement = placement.split('-')[0];
	  const shiftvariation = placement.split('-')[1];
	  if (shiftvariation) {
	    const _data$offsets5 = data.offsets;
	        const { reference } = _data$offsets5;
	        const { popper } = _data$offsets5;
	    const isVertical = ['bottom', 'top'].indexOf(basePlacement) !== -1;
	    const side = isVertical ? 'left' : 'top';
	    const measurement = isVertical ? 'width' : 'height';
	    const shiftOffsets = {
	      start: _defineProperty({}, side, reference[side]),
	      end: _defineProperty({}, side, reference[side] + reference[measurement] - popper[measurement])
	    };
	    data.offsets.popper = _extends$1({}, popper, shiftOffsets[shiftvariation]);
	  }
	  return data;
          }
          function hide(data) {
	  if (!isModifierRequired(data.instance.modifiers, 'hide', 'preventOverflow')) {
	    return data;
	  }
	  const refRect = data.offsets.reference;
	  const bound = find(data.instance.modifiers, modifier => modifier.name === 'preventOverflow').boundaries;
	  if (refRect.bottom < bound.top || refRect.left > bound.right || refRect.top > bound.bottom || refRect.right < bound.left) {
	    if (data.hide === true) {
	      return data;
	    }
	    data.hide = true;
	    data.attributes['x-out-of-boundaries'] = '';
	  } else {
	    if (data.hide === false) {
	      return data;
	    }
	    data.hide = false;
	    data.attributes['x-out-of-boundaries'] = false;
	  }
	  return data;
          }
          function inner(data) {
	  const { placement } = data;
	  const basePlacement = placement.split('-')[0];
	  const _data$offsets6 = data.offsets;
	      const { popper } = _data$offsets6;
	      const { reference } = _data$offsets6;
	  const isHoriz = ['left', 'right'].indexOf(basePlacement) !== -1;
	  const subtractLength = ['top', 'left'].indexOf(basePlacement) === -1;
	  popper[isHoriz ? 'left' : 'top'] = reference[basePlacement] - (subtractLength ? popper[isHoriz ? 'width' : 'height'] : 0);
	  data.placement = getOppositePlacement(placement);
	  data.offsets.popper = getClientRect(popper);
	  return data;
          }
          const modifiers = {
	  shift: {
	    order: 100,
	    enabled: true,
	    fn: shift
	  },
	  offset: {
	    order: 200,
	    enabled: true,
	    fn: offset,
	    offset: 0
	  },
	  preventOverflow: {
	    order: 300,
	    enabled: true,
	    fn: preventOverflow,
	    priority: ['left', 'right', 'top', 'bottom'],
	    padding: 5,
	    boundariesElement: 'scrollParent'
	  },
	  keepTogether: {
	    order: 400,
	    enabled: true,
	    fn: keepTogether
	  },
	  arrow: {
	    order: 500,
	    enabled: true,
	    fn: arrow,
	    element: '[x-arrow]'
	  },
	  flip: {
	    order: 600,
	    enabled: true,
	    fn: flip,
	    behavior: 'flip',
	    padding: 5,
	    boundariesElement: 'viewport',
	    flipVariations: false,
	    flipVariationsByContent: false
	  },
	  inner: {
	    order: 700,
	    enabled: false,
	    fn: inner
	  },
	  hide: {
	    order: 800,
	    enabled: true,
	    fn: hide
	  },
	  computeStyle: {
	    order: 850,
	    enabled: true,
	    fn: computeStyle,
	    gpuAcceleration: true,
	    x: 'bottom',
	    y: 'right'
	  },
	  applyStyle: {
	    order: 900,
	    enabled: true,
	    fn: applyStyle,
	    onLoad: applyStyleOnLoad,
	    gpuAcceleration: undefined
	  }
          };
          const Defaults = {
	  placement: 'bottom',
	  positionFixed: false,
	  eventsEnabled: true,
	  removeOnDestroy: false,
	  onCreate: function onCreate() {},
	  onUpdate: function onUpdate() {},
	  modifiers
          };
          const Popper = (function () {
	  function Popper(reference, popper) {
	    const _this = this;
	    const options = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : {};
	    _classCallCheck(this, Popper);
	    this.scheduleUpdate = function () {
	      return requestAnimationFrame(_this.update);
	    };
	    this.update = debounce$1(this.update.bind(this));
	    this.options = _extends$1({}, Popper.Defaults, options);
	    this.state = {
	      isDestroyed: false,
	      isCreated: false,
	      scrollParents: []
	    };
	    this.reference = reference && reference.jquery ? reference[0] : reference;
	    this.popper = popper && popper.jquery ? popper[0] : popper;
	    this.options.modifiers = {};
	    keys$1(_extends$1({}, Popper.Defaults.modifiers, options.modifiers)).forEach((name) => {
	      _this.options.modifiers[name] = _extends$1({}, Popper.Defaults.modifiers[name] || {}, options.modifiers ? options.modifiers[name] : {});
	    });
	    this.modifiers = keys$1(this.options.modifiers).map(name => _extends$1({
	        name
	      }, _this.options.modifiers[name]))
	    .sort((a, b) => a.order - b.order);
	    this.modifiers.forEach((modifierOptions) => {
	      if (modifierOptions.enabled && isFunction(modifierOptions.onLoad)) {
	        modifierOptions.onLoad(_this.reference, _this.popper, _this.options, modifierOptions, _this.state);
	      }
	    });
	    this.update();
	    const { eventsEnabled } = this.options;
	    if (eventsEnabled) {
	      this.enableEventListeners();
	    }
	    this.state.eventsEnabled = eventsEnabled;
	  }
	  _createClass(Popper, [{
	    key: 'update',
	    value: function update() {
	      return _update.call(this);
	    }
	  }, {
	    key: 'destroy',
	    value: function destroy() {
	      return _destroy.call(this);
	    }
	  }, {
	    key: 'enableEventListeners',
	    value: function enableEventListeners() {
	      return _enableEventListeners.call(this);
	    }
	  }, {
	    key: 'disableEventListeners',
	    value: function disableEventListeners() {
	      return _disableEventListeners.call(this);
	    }
	  }]);
	  return Popper;
          }());
          Popper.Utils = (typeof window !== 'undefined' ? window : global).PopperUtils;
          Popper.placements = placements;
          Popper.Defaults = Defaults;

          function _extends$2() {
	  _extends$2 = assign$1 || function (target) {
	    for (let i = 1; i < arguments.length; i++) {
	      const source = arguments[i];
	      for (const key in source) {
	        if (Object.prototype.hasOwnProperty.call(source, key)) {
	          target[key] = source[key];
	        }
	      }
	    }
	    return target;
	  };
	  return _extends$2.apply(this, arguments);
          }
          const version = '4.3.4';
          const isBrowser$1 = typeof window !== 'undefined' && typeof document !== 'undefined';
          const ua = isBrowser$1 ? navigator.userAgent : '';
          const isIE$1 = /MSIE |Trident\//.test(ua);
          const isUCBrowser = /UCBrowser\//.test(ua);
          const isIOS = isBrowser$1 && /iPhone|iPad|iPod/.test(navigator.platform) && !window.MSStream;
          const defaultProps = {
	  a11y: true,
	  allowHTML: true,
	  animateFill: true,
	  animation: 'shift-away',
	  appendTo: function appendTo() {
	    return document.body;
	  },
	  aria: 'describedby',
	  arrow: false,
	  arrowType: 'sharp',
	  boundary: 'scrollParent',
	  content: '',
	  delay: 0,
	  distance: 10,
	  duration: [325, 275],
	  flip: true,
	  flipBehavior: 'flip',
	  flipOnUpdate: false,
	  followCursor: false,
	  hideOnClick: true,
	  ignoreAttributes: false,
	  inertia: false,
	  interactive: false,
	  interactiveBorder: 2,
	  interactiveDebounce: 0,
	  lazy: true,
	  width: 'auto',
	  maxWidth: 'auto',
	  multiple: false,
	  offset: 0,
	  onHidden: function onHidden() {},
	  onHide: function onHide() {},
	  onMount: function onMount() {},
	  onShow: function onShow() {},
	  onShown: function onShown() {},
	  onTrigger: function onTrigger() {},
	  placement: 'top',
	  popperOptions: {},
	  role: 'tooltip',
	  showOnInit: false,
	  size: 'regular',
	  sticky: false,
	  target: '',
	  theme: 'dark',
	  touch: true,
	  touchHold: false,
	  trigger: 'mouseenter focus',
	  triggerTarget: null,
	  updateDuration: 0,
	  wait: null,
	  zIndex: 9999,
	  extCls: ''
          };
          const POPPER_INSTANCE_DEPENDENCIES = ['arrow', 'arrowType', 'boundary', 'distance', 'flip', 'flipBehavior', 'flipOnUpdate', 'offset', 'placement', 'popperOptions'];
          const elementProto = isBrowser$1 ? Element.prototype : {};
          const matches = elementProto.matches || elementProto.matchesSelector || elementProto.webkitMatchesSelector || elementProto.mozMatchesSelector || elementProto.msMatchesSelector;
          function arrayFrom(value) {
	  return [].slice.call(value);
          }
          function closest(element, selector) {
	  return closestCallback(element, el => matches.call(el, selector));
          }
          function closestCallback(element, callback) {
	  while (element) {
	    if (callback(element)) {
	      return element;
	    }
	    element = element.parentElement;
	  }
	  return null;
          }
          const PASSIVE = {
	  passive: true
          };
          const PADDING = 4;
          const PLACEMENT_ATTRIBUTE = 'x-placement';
          const OUT_OF_BOUNDARIES_ATTRIBUTE = 'x-out-of-boundaries';
          const IOS_CLASS = 'tippy-iOS';
          const ACTIVE_CLASS = 'tippy-active';
          const POPPER_CLASS = 'tippy-popper';
          const TOOLTIP_CLASS = 'tippy-tooltip';
          const CONTENT_CLASS = 'tippy-content';
          const BACKDROP_CLASS = 'tippy-backdrop';
          const ARROW_CLASS = 'tippy-arrow';
          const ROUND_ARROW_CLASS = 'tippy-roundarrow';
          const POPPER_SELECTOR = '.'.concat(POPPER_CLASS);
          const TOOLTIP_SELECTOR = '.'.concat(TOOLTIP_CLASS);
          const CONTENT_SELECTOR = '.'.concat(CONTENT_CLASS);
          const BACKDROP_SELECTOR = '.'.concat(BACKDROP_CLASS);
          const ARROW_SELECTOR = '.'.concat(ARROW_CLASS);
          const ROUND_ARROW_SELECTOR = '.'.concat(ROUND_ARROW_CLASS);
          let isUsingTouch = false;
          function onDocumentTouch() {
	  if (isUsingTouch) {
	    return;
	  }
	  isUsingTouch = true;
	  if (isIOS) {
	    document.body.classList.add(IOS_CLASS);
	  }
	  if (window.performance) {
	    document.addEventListener('mousemove', onDocumentMouseMove);
	  }
          }
          let lastMouseMoveTime = 0;
          function onDocumentMouseMove() {
	  const now = performance.now();
	  if (now - lastMouseMoveTime < 20) {
	    isUsingTouch = false;
	    document.removeEventListener('mousemove', onDocumentMouseMove);
	    if (!isIOS) {
	      document.body.classList.remove(IOS_CLASS);
	    }
	  }
	  lastMouseMoveTime = now;
          }
          function onWindowBlur() {
	  const _document = document;
	      const { activeElement } = _document;
	  if (activeElement && activeElement.blur && activeElement._tippy) {
	    activeElement.blur();
	  }
          }
          function bindGlobalEventListeners() {
	  document.addEventListener('touchstart', onDocumentTouch, PASSIVE);
	  window.addEventListener('blur', onWindowBlur);
          }
          const keys$2 = keys$1(defaultProps);
          function getDataAttributeOptions(reference) {
	  return keys$2.reduce((acc, key) => {
	    const valueAsString = (reference.getAttribute('data-tippy-'.concat(key)) || '').trim();
	    if (!valueAsString) {
	      return acc;
	    }
	    if (key === 'content') {
	      acc[key] = valueAsString;
	    } else {
	      try {
	        acc[key] = JSON.parse(valueAsString);
	      } catch (e) {
	        acc[key] = valueAsString;
	      }
	    }
	    return acc;
	  }, {});
          }
          function polyfillElementPrototypeProperties(virtualReference) {
	  const polyfills = {
	    isVirtual: true,
	    attributes: virtualReference.attributes || {},
	    contains: function contains() {},
	    setAttribute: function setAttribute(key, value) {
	      virtualReference.attributes[key] = value;
	    },
	    getAttribute: function getAttribute(key) {
	      return virtualReference.attributes[key];
	    },
	    removeAttribute: function removeAttribute(key) {
	      delete virtualReference.attributes[key];
	    },
	    hasAttribute: function hasAttribute(key) {
	      return key in virtualReference.attributes;
	    },
	    addEventListener: function addEventListener() {},
	    removeEventListener: function removeEventListener() {},
	    classList: {
	      classNames: {},
	      add: function add(key) {
	        virtualReference.classList.classNames[key] = true;
	      },
	      remove: function remove(key) {
	        delete virtualReference.classList.classNames[key];
	      },
	      contains: function contains(key) {
	        return key in virtualReference.classList.classNames;
	      }
	    }
	  };
	  for (const key in polyfills) {
	    virtualReference[key] = polyfills[key];
	  }
          }
          function isBareVirtualElement(value) {
	  return {}.toString.call(value) === '[object Object]' && !value.addEventListener;
          }
          function isReferenceElement(value) {
	  return !!value._tippy && !matches.call(value, POPPER_SELECTOR);
          }
          function hasOwnProperty$1(obj, key) {
	  return {}.hasOwnProperty.call(obj, key);
          }
          function getArrayOfElements(value) {
	  if (isSingular(value)) {
	    return [value];
	  }
	  if (value instanceof NodeList) {
	    return arrayFrom(value);
	  }
	  if (isArray$1(value)) {
	    return value;
	  }
	  try {
	    return arrayFrom(document.querySelectorAll(value));
	  } catch (e) {
	    return [];
	  }
          }
          function getValue(value, index, defaultValue) {
	  if (isArray$1(value)) {
	    const v = value[index];
	    return v == null ? defaultValue : v;
	  }
	  return value;
          }
          function debounce$2(fn, ms) {
	  if (ms === 0) {
	    return fn;
	  }
	  let timeout;
	  return function (arg) {
	    clearTimeout(timeout);
	    timeout = setTimeout(() => {
	      fn(arg);
	    }, ms);
	  };
          }
          function getModifier(obj, key) {
	  return obj && obj.modifiers && obj.modifiers[key];
          }
          function includes(a, b) {
	  return a.indexOf(b) > -1;
          }
          function isRealElement(value) {
	  return value instanceof Element;
          }
          function isSingular(value) {
	  return !!(value && hasOwnProperty$1(value, 'isVirtual')) || isRealElement(value);
          }
          function innerHTML() {
	  return 'innerHTML';
          }
          function invokeWithArgsOrReturn(value, args) {
	  return typeof value === 'function' ? value.apply(null, args) : value;
          }
          function setFlipModifierEnabled(modifiers, value) {
	  modifiers.filter(m => m.name === 'flip')[0].enabled = value;
          }
          function canReceiveFocus(element) {
	  return isRealElement(element) ? matches.call(element, 'a[href],area[href],button,details,input,textarea,select,iframe,[tabindex]') && !element.hasAttribute('disabled') : true;
          }
          function div() {
	  return document.createElement('div');
          }
          function setTransitionDuration(els, value) {
	  els.forEach((el) => {
	    if (el) {
	      el.style.transitionDuration = ''.concat(value, 'ms');
	    }
	  });
          }
          function setVisibilityState(els, state) {
	  els.forEach((el) => {
	    if (el) {
	      el.setAttribute('data-state', state);
	    }
	  });
          }
          function evaluateProps(reference, props) {
	  const out = _extends$2({}, props, {
	    content: invokeWithArgsOrReturn(props.content, [reference])
	  }, props.ignoreAttributes ? {} : getDataAttributeOptions(reference));
	  if (out.arrow || isUCBrowser) {
	    out.animateFill = false;
	  }
	  return out;
          }
          function validateOptions(options, defaultProps) {
	  keys$1(options).forEach((option) => {
	    if (!hasOwnProperty$1(defaultProps, option)) {
	      throw new Error('[tippy]: `'.concat(option, '` is not a valid option'));
	    }
	  });
          }
          function setInnerHTML(element, html) {
	  element[innerHTML()] = isRealElement(html) ? html[innerHTML()] : html;
          }
          function setContent(contentEl, props) {
	  if (isRealElement(props.content)) {
	    setInnerHTML(contentEl, '');
	    contentEl.appendChild(props.content);
	  } else if (typeof props.content !== 'function') {
	    const key = props.allowHTML ? 'innerHTML' : 'textContent';
	    contentEl[key] = props.content;
	  }
          }
          function getChildren(popper) {
	  return {
	    tooltip: popper.querySelector(TOOLTIP_SELECTOR),
	    backdrop: popper.querySelector(BACKDROP_SELECTOR),
	    content: popper.querySelector(CONTENT_SELECTOR),
	    arrow: popper.querySelector(ARROW_SELECTOR) || popper.querySelector(ROUND_ARROW_SELECTOR)
	  };
          }
          function addInertia(tooltip) {
	  tooltip.setAttribute('data-inertia', '');
          }
          function removeInertia(tooltip) {
	  tooltip.removeAttribute('data-inertia');
          }
          function createArrowElement(arrowType) {
	  const arrow = div();
	  if (arrowType === 'round') {
	    arrow.className = ROUND_ARROW_CLASS;
	    setInnerHTML(arrow, '<svg viewBox="0 0 18 7" xmlns="http://www.w3.org/2000/svg"><path d="M0 7s2.021-.015 5.253-4.218C6.584 1.051 7.797.007 9 0c1.203-.007 2.416 1.035 3.761 2.782C16.012 7.005 18 7 18 7H0z"/></svg>');
	  } else {
	    arrow.className = ARROW_CLASS;
	  }
	  return arrow;
          }
          function createBackdropElement() {
	  const backdrop = div();
	  backdrop.className = BACKDROP_CLASS;
	  backdrop.setAttribute('data-state', 'hidden');
	  return backdrop;
          }
          function addInteractive(popper, tooltip) {
	  popper.setAttribute('tabindex', '-1');
	  tooltip.setAttribute('data-interactive', '');
          }
          function removeInteractive(popper, tooltip) {
	  popper.removeAttribute('tabindex');
	  tooltip.removeAttribute('data-interactive');
          }
          function updateTransitionEndListener(tooltip, action, listener) {
	  const eventName = isUCBrowser && document.body.style.webkitTransition !== undefined ? 'webkitTransitionEnd' : 'transitionend';
	  tooltip[`${action}EventListener`](eventName, listener);
          }
          function getBasicPlacement(popper) {
	  const fullPlacement = popper.getAttribute(PLACEMENT_ATTRIBUTE);
	  return fullPlacement ? fullPlacement.split('-')[0] : '';
          }
          function reflow(popper) {
	  void popper.offsetHeight;
          }
          function updateTheme(tooltip, action, theme) {
	  theme.split(' ').forEach((themeName) => {
	    tooltip.classList[action](`${themeName}-theme`);
	  });
          }
          function setWidth(tooltip, props, key) {
	  const width = props[key];
	  const parsedWidth = _parseInt$2(width);
	  if (typeof width === 'number') {
	    tooltip.style[key] = `${width}px`;
	  } else if (isNaN(parsedWidth)) {
	    tooltip.style[key] = width;
	  } else {
	    tooltip.style[key] = `${parsedWidth}px`;
	  }
          }
          function createPopperElement(id, props) {
	  const popper = div();
	  popper.className = POPPER_CLASS + (props.extCls ? ' '.concat(props.extCls) : '');
	  popper.id = 'tippy-'.concat(id);
	  popper.style.zIndex = `${props.zIndex}`;
	  popper.style.position = 'absolute';
	  popper.style.top = '0';
	  popper.style.left = '0';
	  if (props.role) {
	    popper.setAttribute('role', props.role);
	  }
	  const tooltip = div();
	  tooltip.className = TOOLTIP_CLASS;
	  setWidth(tooltip, props, 'maxWidth');
	  setWidth(tooltip, props, 'width');
	  tooltip.setAttribute('data-size', props.size);
	  tooltip.setAttribute('data-animation', props.animation);
	  tooltip.setAttribute('data-state', 'hidden');
	  updateTheme(tooltip, 'add', props.theme);
	  const content = div();
	  content.className = CONTENT_CLASS;
	  content.setAttribute('data-state', 'hidden');
	  if (props.interactive) {
	    addInteractive(popper, tooltip);
	  }
	  if (props.arrow) {
	    tooltip.appendChild(createArrowElement(props.arrowType));
	  }
	  if (props.animateFill) {
	    tooltip.appendChild(createBackdropElement());
	    tooltip.setAttribute('data-animatefill', '');
	  }
	  if (props.inertia) {
	    addInertia(tooltip);
	  }
	  setContent(content, props);
	  tooltip.appendChild(content);
	  popper.appendChild(tooltip);
	  return popper;
          }
          function updatePopperElement(popper, prevProps, nextProps) {
	  const _getChildren = getChildren(popper);
	      const { tooltip } = _getChildren;
	      const { content } = _getChildren;
	      const { backdrop } = _getChildren;
	      const { arrow } = _getChildren;
	  popper.style.zIndex = `${nextProps.zIndex}`;
	  tooltip.setAttribute('data-size', nextProps.size);
	  tooltip.setAttribute('data-animation', nextProps.animation);
	  tooltip.style.maxWidth = nextProps.maxWidth + (typeof nextProps.maxWidth === 'number' ? 'px' : '');
	  if (nextProps.role) {
	    popper.setAttribute('role', nextProps.role);
	  } else {
	    popper.removeAttribute('role');
	  }
	  if (prevProps.content !== nextProps.content) {
	    setContent(content, nextProps);
	  }
	  if (!prevProps.animateFill && nextProps.animateFill) {
	    tooltip.appendChild(createBackdropElement());
	    tooltip.setAttribute('data-animatefill', '');
	  } else if (prevProps.animateFill && !nextProps.animateFill) {
	    tooltip.removeChild(backdrop);
	    tooltip.removeAttribute('data-animatefill');
	  }
	  if (!prevProps.arrow && nextProps.arrow) {
	    tooltip.appendChild(createArrowElement(nextProps.arrowType));
	  } else if (prevProps.arrow && !nextProps.arrow) {
	    tooltip.removeChild(arrow);
	  }
	  if (prevProps.arrow && nextProps.arrow && prevProps.arrowType !== nextProps.arrowType) {
	    tooltip.replaceChild(createArrowElement(nextProps.arrowType), arrow);
	  }
	  if (!prevProps.interactive && nextProps.interactive) {
	    addInteractive(popper, tooltip);
	  } else if (prevProps.interactive && !nextProps.interactive) {
	    removeInteractive(popper, tooltip);
	  }
	  if (!prevProps.inertia && nextProps.inertia) {
	    addInertia(tooltip);
	  } else if (prevProps.inertia && !nextProps.inertia) {
	    removeInertia(tooltip);
	  }
	  if (prevProps.theme !== nextProps.theme) {
	    updateTheme(tooltip, 'remove', prevProps.theme);
	    updateTheme(tooltip, 'add', nextProps.theme);
	  }
          }
          function hideAll() {
	  const _ref = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : {};
	      const excludedReferenceOrInstance = _ref.exclude;
	      const { duration } = _ref;
	  arrayFrom(document.querySelectorAll(POPPER_SELECTOR)).forEach((popper) => {
	    const instance = popper._tippy;
	    if (instance) {
	      let isExcluded = false;
	      if (excludedReferenceOrInstance) {
	        isExcluded = isReferenceElement(excludedReferenceOrInstance) ? instance.reference === excludedReferenceOrInstance : popper === excludedReferenceOrInstance.popper;
	      }
	      if (!isExcluded) {
	        instance.hide(duration);
	      }
	    }
	  });
          }
          function isCursorOutsideInteractiveBorder(popperPlacement, popperRect, event, props) {
	  if (!popperPlacement) {
	    return true;
	  }
	  const x = event.clientX;
	      const y = event.clientY;
	  const { interactiveBorder } = props;
	      const { distance } = props;
	  const exceedsTop = popperRect.top - y > (popperPlacement === 'top' ? interactiveBorder + distance : interactiveBorder);
	  const exceedsBottom = y - popperRect.bottom > (popperPlacement === 'bottom' ? interactiveBorder + distance : interactiveBorder);
	  const exceedsLeft = popperRect.left - x > (popperPlacement === 'left' ? interactiveBorder + distance : interactiveBorder);
	  const exceedsRight = x - popperRect.right > (popperPlacement === 'right' ? interactiveBorder + distance : interactiveBorder);
	  return exceedsTop || exceedsBottom || exceedsLeft || exceedsRight;
          }
          function getOffsetDistanceInPx(distance) {
	  return `${-(distance - 10)}px`;
          }
          let idCounter = 1;
          let mouseMoveListeners = [];
          function createTippy(reference, collectionProps) {
	  const props = evaluateProps(reference, collectionProps);
	  if (!props.multiple && reference._tippy) {
	    return null;
	  }
	  let lastTriggerEventType;
	  let lastMouseMoveEvent;
	  let showTimeoutId;
	  let hideTimeoutId;
	  let scheduleHideAnimationFrameId;
	  let isScheduledToShow = false;
	  let isBeingDestroyed = false;
	  let previousPlacement;
	  let wasVisibleDuringPreviousUpdate = false;
	  let hasMountCallbackRun = false;
	  let currentMountCallback;
	  let currentTransitionEndListener;
	  let listeners = [];
	  let currentComputedPadding;
	  let debouncedOnMouseMove = debounce$2(onMouseMove, props.interactiveDebounce);
	  const id = idCounter++;
	  const popper = createPopperElement(id, props);
	  const popperChildren = getChildren(popper);
	  const popperInstance = null;
	  const state = {
	    isEnabled: true,
	    isVisible: false,
	    isDestroyed: false,
	    isMounted: false,
	    isShown: false
	  };
	  const instance = {
	    id,
	    reference,
	    popper,
	    popperChildren,
	    popperInstance,
	    props,
	    state,
	    clearDelayTimeouts,
	    set,
	    setContent,
	    show,
	    hide,
	    enable,
	    disable,
	    destroy
	  };
	  reference._tippy = instance;
	  popper._tippy = instance;
	  addTriggersToReference();
	  if (!props.lazy) {
	    createPopperInstance();
	  }
	  if (props.showOnInit) {
	    scheduleShow();
	  }
	  if (props.a11y && !props.target && !canReceiveFocus(getEventListenersTarget())) {
	    getEventListenersTarget().setAttribute('tabindex', '0');
	  }
	  popper.addEventListener('mouseenter', (event) => {
	    if (instance.props.interactive && instance.state.isVisible && lastTriggerEventType === 'mouseenter') {
	      scheduleShow(event, true);
	    }
	  });
	  popper.addEventListener('mouseleave', () => {
	    if (instance.props.interactive && lastTriggerEventType === 'mouseenter') {
	      document.addEventListener('mousemove', debouncedOnMouseMove);
	    }
	  });
	  return instance;
	  function removeFollowCursorListener() {
	    document.removeEventListener('mousemove', positionVirtualReferenceNearCursor);
	  }
	  function cleanupInteractiveMouseListeners() {
	    document.body.removeEventListener('mouseleave', scheduleHide);
	    document.removeEventListener('mousemove', debouncedOnMouseMove);
	    mouseMoveListeners = mouseMoveListeners.filter(listener => listener !== debouncedOnMouseMove);
	  }
	  function getEventListenersTarget() {
	    return instance.props.triggerTarget || reference;
	  }
	  function addDocumentClickListener() {
	    document.addEventListener('click', onDocumentClick, true);
	  }
	  function removeDocumentClickListener() {
	    document.removeEventListener('click', onDocumentClick, true);
	  }
	  function getTransitionableElements() {
	    return [instance.popperChildren.tooltip, instance.popperChildren.backdrop, instance.popperChildren.content];
	  }
	  function getIsInLooseFollowCursorMode() {
	    const { followCursor } = instance.props;
	    return followCursor && lastTriggerEventType !== 'focus' || isUsingTouch && followCursor === 'initial';
	  }
	  function makeSticky() {
	    setTransitionDuration([popper], isIE$1 ? 0 : instance.props.updateDuration);
	    function updatePosition() {
	      instance.popperInstance.scheduleUpdate();
	      if (instance.state.isMounted) {
	        requestAnimationFrame(updatePosition);
	      } else {
	        setTransitionDuration([popper], 0);
	      }
	    }
	    updatePosition();
	  }
	  function onTransitionedOut(duration, callback) {
	    onTransitionEnd(duration, () => {
	      if (!instance.state.isVisible && popper.parentNode && popper.parentNode.contains(popper)) {
	        callback();
	      }
	    });
	  }
	  function onTransitionedIn(duration, callback) {
	    onTransitionEnd(duration, callback);
	  }
	  function onTransitionEnd(duration, callback) {
	    const { tooltip } = instance.popperChildren;
	    function listener(event) {
	      if (event.target === tooltip) {
	        updateTransitionEndListener(tooltip, 'remove', listener);
	        callback();
	      }
	    }
	    if (duration === 0) {
	      return callback();
	    }
	    updateTransitionEndListener(tooltip, 'remove', currentTransitionEndListener);
	    updateTransitionEndListener(tooltip, 'add', listener);
	    currentTransitionEndListener = listener;
	  }
	  function on(eventType, handler) {
	    const options = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : false;
	    getEventListenersTarget().addEventListener(eventType, handler, options);
	    listeners.push({
	      eventType,
	      handler,
	      options
	    });
	  }
	  function addTriggersToReference() {
	    if (instance.props.touchHold && !instance.props.target) {
	      on('touchstart', onTrigger, PASSIVE);
	      on('touchend', onMouseLeave, PASSIVE);
	    }
	    instance.props.trigger.trim().split(' ')
                .forEach((eventType) => {
	      if (eventType === 'manual') {
	        return;
	      }
	      if (!instance.props.target) {
	        on(eventType, onTrigger);
	        switch (eventType) {
	          case 'mouseenter':
	            on('mouseleave', onMouseLeave);
	            break;
	          case 'focus':
	            on(isIE$1 ? 'focusout' : 'blur', onBlur);
	            break;
	        }
	      } else {
	        switch (eventType) {
	          case 'mouseenter':
	            on('mouseover', onDelegateShow);
	            on('mouseout', onDelegateHide);
	            break;
	          case 'focus':
	            on('focusin', onDelegateShow);
	            on('focusout', onDelegateHide);
	            break;
	          case 'click':
	            on(eventType, onDelegateShow);
	            break;
	        }
	      }
	    });
	  }
	  function removeTriggersFromReference() {
	    listeners.forEach((_ref) => {
	      const { eventType } = _ref;
	          const { handler } = _ref;
	          const { options } = _ref;
	      getEventListenersTarget().removeEventListener(eventType, handler, options);
	    });
	    listeners = [];
	  }
	  function positionVirtualReferenceNearCursor(event) {
	    const _lastMouseMoveEvent = lastMouseMoveEvent = event;
	        const x = _lastMouseMoveEvent.clientX;
	        const y = _lastMouseMoveEvent.clientY;
	    if (!currentComputedPadding) {
	      return;
	    }
	    const isCursorOverReference = closestCallback(event.target, el => el === reference);
	    const rect = reference.getBoundingClientRect();
	    const { followCursor } = instance.props;
	    const isHorizontal = followCursor === 'horizontal';
	    const isVertical = followCursor === 'vertical';
	    const isVerticalPlacement = includes(['top', 'bottom'], getBasicPlacement(popper));
	    const fullPlacement = popper.getAttribute(PLACEMENT_ATTRIBUTE);
	    const isVariation = fullPlacement ? !!fullPlacement.split('-')[1] : false;
	    const size = isVerticalPlacement ? popper.offsetWidth : popper.offsetHeight;
	    const halfSize = size / 2;
	    const verticalIncrease = isVerticalPlacement ? 0 : isVariation ? size : halfSize;
	    const horizontalIncrease = isVerticalPlacement ? isVariation ? size : halfSize : 0;
	    if (isCursorOverReference || !instance.props.interactive) {
	      instance.popperInstance.reference = _extends$2({}, instance.popperInstance.reference, {
	        clientWidth: 0,
	        clientHeight: 0,
	        getBoundingClientRect: function getBoundingClientRect() {
	          return {
	            width: isVerticalPlacement ? size : 0,
	            height: isVerticalPlacement ? 0 : size,
	            top: (isHorizontal ? rect.top : y) - verticalIncrease,
	            bottom: (isHorizontal ? rect.bottom : y) + verticalIncrease,
	            left: (isVertical ? rect.left : x) - horizontalIncrease,
	            right: (isVertical ? rect.right : x) + horizontalIncrease
	          };
	        }
	      });
	      instance.popperInstance.update();
	    }
	    if (followCursor === 'initial' && instance.state.isVisible) {
	      removeFollowCursorListener();
	    }
	  }
	  function createDelegateChildTippy(event) {
	    if (event) {
	      const targetEl = closest(event.target, instance.props.target);
	      if (targetEl && !targetEl._tippy) {
	        createTippy(targetEl, _extends$2({}, instance.props, {
	          content: invokeWithArgsOrReturn(collectionProps.content, [targetEl]),
	          appendTo: collectionProps.appendTo,
	          target: '',
	          showOnInit: true
	        }));
	      }
	    }
	  }
	  function onTrigger(event) {
	    if (!instance.state.isEnabled || isEventListenerStopped(event)) {
	      return;
	    }
	    if (!instance.state.isVisible) {
	      lastTriggerEventType = event.type;
	      if (event instanceof MouseEvent) {
	        lastMouseMoveEvent = event;
	        mouseMoveListeners.forEach(listener => listener(event));
	      }
	    }
	    if (event.type === 'click' && instance.props.hideOnClick !== false && instance.state.isVisible) {
	      scheduleHide();
	    } else {
	      scheduleShow(event);
	    }
	  }
	  function onMouseMove(event) {
	    const isCursorOverPopper = closest(event.target, POPPER_SELECTOR) === popper;
	    const isCursorOverReference = closestCallback(event.target, el => el === reference);
	    if (isCursorOverPopper || isCursorOverReference) {
	      return;
	    }
	    if (isCursorOutsideInteractiveBorder(getBasicPlacement(popper), popper.getBoundingClientRect(), event, instance.props)) {
	      cleanupInteractiveMouseListeners();
	      scheduleHide();
	    }
	  }
	  function onMouseLeave(event) {
	    if (isEventListenerStopped(event)) {
	      return;
	    }
	    if (instance.props.interactive) {
	      document.body.addEventListener('mouseleave', scheduleHide);
	      document.addEventListener('mousemove', debouncedOnMouseMove);
	      mouseMoveListeners.push(debouncedOnMouseMove);
	      return;
	    }
	    scheduleHide();
	  }
	  function onBlur(event) {
	    if (event.target !== getEventListenersTarget()) {
	      return;
	    }
	    if (instance.props.interactive && event.relatedTarget && popper.contains(event.relatedTarget)) {
	      return;
	    }
	    scheduleHide();
	  }
	  function onDelegateShow(event) {
	    if (closest(event.target, instance.props.target)) {
	      scheduleShow(event);
	    }
	  }
	  function onDelegateHide(event) {
	    if (closest(event.target, instance.props.target)) {
	      scheduleHide();
	    }
	  }
	  function isEventListenerStopped(event) {
	    const supportsTouch = ('ontouchstart' in window);
	    const isTouchEvent = includes(event.type, 'touch');
	    const { touchHold } = instance.props;
	    return supportsTouch && isUsingTouch && touchHold && !isTouchEvent || isUsingTouch && !touchHold && isTouchEvent;
	  }
	  function runMountCallback() {
	    if (!hasMountCallbackRun && currentMountCallback) {
	      hasMountCallbackRun = true;
	      reflow(popper);
	      currentMountCallback();
	    }
	  }
	  function createPopperInstance() {
	    const { popperOptions } = instance.props;
	    const _instance$popperChild = instance.popperChildren;
	        const { tooltip } = _instance$popperChild;
	        const { arrow } = _instance$popperChild;
	    const preventOverflowModifier = getModifier(popperOptions, 'preventOverflow');
	    function applyMutations(data) {
	      if (instance.props.flip && !instance.props.flipOnUpdate) {
	        if (data.flipped) {
	          instance.popperInstance.options.placement = data.placement;
	        }
	        setFlipModifierEnabled(instance.popperInstance.modifiers, false);
	      }
	      tooltip.setAttribute(PLACEMENT_ATTRIBUTE, data.placement);
	      if (data.attributes[OUT_OF_BOUNDARIES_ATTRIBUTE] !== false) {
	        tooltip.setAttribute(OUT_OF_BOUNDARIES_ATTRIBUTE, '');
	      } else {
	        tooltip.removeAttribute(OUT_OF_BOUNDARIES_ATTRIBUTE);
	      }
	      if (previousPlacement && previousPlacement !== data.placement && wasVisibleDuringPreviousUpdate) {
	        tooltip.style.transition = 'none';
	        requestAnimationFrame(() => {
	          tooltip.style.transition = '';
	        });
	      }
	      previousPlacement = data.placement;
	      wasVisibleDuringPreviousUpdate = instance.state.isVisible;
	      const basicPlacement = getBasicPlacement(popper);
	      const styles = tooltip.style;
	      styles.top = styles.bottom = styles.left = styles.right = '';
	      styles[basicPlacement] = getOffsetDistanceInPx(instance.props.distance);
	      const padding = preventOverflowModifier && preventOverflowModifier.padding !== undefined ? preventOverflowModifier.padding : PADDING;
	      const isPaddingNumber = typeof padding === 'number';
	      const computedPadding = _extends$2({
	        top: isPaddingNumber ? padding : padding.top,
	        bottom: isPaddingNumber ? padding : padding.bottom,
	        left: isPaddingNumber ? padding : padding.left,
	        right: isPaddingNumber ? padding : padding.right
	      }, !isPaddingNumber && padding);
	      computedPadding[basicPlacement] = isPaddingNumber ? padding + instance.props.distance : (padding[basicPlacement] || 0) + instance.props.distance;
	      instance.popperInstance.modifiers.filter(m => m.name === 'preventOverflow')[0].padding = computedPadding;
	      currentComputedPadding = computedPadding;
	    }
	    const config = _extends$2({
	      eventsEnabled: false,
	      placement: instance.props.placement
	    }, popperOptions, {
	      modifiers: _extends$2({}, popperOptions ? popperOptions.modifiers : {}, {
	        preventOverflow: _extends$2({
	          boundariesElement: instance.props.boundary,
	          padding: PADDING
	        }, preventOverflowModifier),
	        arrow: _extends$2({
	          element: arrow,
	          enabled: !!arrow
	        }, getModifier(popperOptions, 'arrow')),
	        flip: _extends$2({
	          enabled: instance.props.flip,
	          padding: instance.props.distance + PADDING,
	          behavior: instance.props.flipBehavior
	        }, getModifier(popperOptions, 'flip')),
	        offset: _extends$2({
	          offset: instance.props.offset
	        }, getModifier(popperOptions, 'offset'))
	      }),
	      onCreate: function onCreate(data) {
	        applyMutations(data);
	        runMountCallback();
	        if (popperOptions && popperOptions.onCreate) {
	          popperOptions.onCreate(data);
	        }
	      },
	      onUpdate: function onUpdate(data) {
	        applyMutations(data);
	        runMountCallback();
	        if (popperOptions && popperOptions.onUpdate) {
	          popperOptions.onUpdate(data);
	        }
	      }
	    });
	    instance.popperInstance = new Popper(reference, popper, config);
	  }
	  function mount() {
	    hasMountCallbackRun = false;
	    const isInLooseFollowCursorMode = getIsInLooseFollowCursorMode();
	    if (instance.popperInstance) {
	      setFlipModifierEnabled(instance.popperInstance.modifiers, instance.props.flip);
	      if (!isInLooseFollowCursorMode) {
	        instance.popperInstance.reference = reference;
	        instance.popperInstance.enableEventListeners();
	      }
	      instance.popperInstance.scheduleUpdate();
	    } else {
	      createPopperInstance();
	      if (!isInLooseFollowCursorMode) {
	        instance.popperInstance.enableEventListeners();
	      }
	    }
	    const { appendTo } = instance.props;
	    const parentNode = appendTo === 'parent' ? reference.parentNode : invokeWithArgsOrReturn(appendTo, [reference]);
	    if (!parentNode.contains(popper)) {
	      parentNode.appendChild(popper);
	      instance.props.onMount(instance);
	      instance.state.isMounted = true;
	    }
	  }
	  function scheduleShow(event, shouldAvoidCallingOnTrigger) {
	    clearDelayTimeouts();
	    if (instance.state.isVisible) {
	      return;
	    }
	    if (instance.props.target) {
	      return createDelegateChildTippy(event);
	    }
	    isScheduledToShow = true;
	    if (event && !shouldAvoidCallingOnTrigger) {
	      instance.props.onTrigger(instance, event);
	    }
	    if (instance.props.wait) {
	      return instance.props.wait(instance, event);
	    }
	    if (getIsInLooseFollowCursorMode() && !instance.state.isMounted) {
	      if (!instance.popperInstance) {
	        createPopperInstance();
	      }
	      document.addEventListener('mousemove', positionVirtualReferenceNearCursor);
	    }
	    addDocumentClickListener();
	    const delay = getValue(instance.props.delay, 0, defaultProps.delay);
	    if (delay) {
	      showTimeoutId = setTimeout(() => {
	        show();
	      }, delay);
	    } else {
	      show();
	    }
	  }
	  function scheduleHide() {
	    clearDelayTimeouts();
	    if (!instance.state.isVisible) {
	      return removeFollowCursorListener();
	    }
	    isScheduledToShow = false;
	    const delay = getValue(instance.props.delay, 1, defaultProps.delay);
	    if (delay) {
	      hideTimeoutId = setTimeout(() => {
	        if (instance.state.isVisible) {
	          hide();
	        }
	      }, delay);
	    } else {
	      scheduleHideAnimationFrameId = requestAnimationFrame(() => {
	        hide();
	      });
	    }
	  }
	  function onDocumentClick(event) {
	    if (instance.props.interactive && popper.contains(event.target)) {
	      return;
	    }
	    if (getEventListenersTarget().contains(event.target)) {
	      if (isUsingTouch) {
	        return;
	      }
	      if (instance.state.isVisible && includes(instance.props.trigger, 'click')) {
	        return;
	      }
	    }
	    if (instance.props.hideOnClick === true) {
	      clearDelayTimeouts();
	      hide();
	    }
	  }
	  function enable() {
	    instance.state.isEnabled = true;
	  }
	  function disable() {
	    instance.state.isEnabled = false;
	  }
	  function clearDelayTimeouts() {
	    clearTimeout(showTimeoutId);
	    clearTimeout(hideTimeoutId);
	    cancelAnimationFrame(scheduleHideAnimationFrameId);
	  }
	  function set(options) {
	    options = options || {};
	    validateOptions(options, defaultProps);
	    removeTriggersFromReference();
	    const prevProps = instance.props;
	    const nextProps = evaluateProps(reference, _extends$2({}, instance.props, options, {
	      ignoreAttributes: true
	    }));
	    nextProps.ignoreAttributes = hasOwnProperty$1(options, 'ignoreAttributes') ? options.ignoreAttributes || false : prevProps.ignoreAttributes;
	    instance.props = nextProps;
	    addTriggersToReference();
	    cleanupInteractiveMouseListeners();
	    debouncedOnMouseMove = debounce$2(onMouseMove, nextProps.interactiveDebounce);
	    updatePopperElement(popper, prevProps, nextProps);
	    instance.popperChildren = getChildren(popper);
	    if (instance.popperInstance) {
	      if (POPPER_INSTANCE_DEPENDENCIES.some(prop => hasOwnProperty$1(options, prop) && options[prop] !== prevProps[prop])) {
	        instance.popperInstance.destroy();
	        createPopperInstance();
	        if (instance.state.isVisible) {
	          instance.popperInstance.enableEventListeners();
	        }
	        if (instance.props.followCursor && lastMouseMoveEvent) {
	          positionVirtualReferenceNearCursor(lastMouseMoveEvent);
	        }
	      } else {
	        instance.popperInstance.update();
	      }
	    }
	  }
	  function setContent(content) {
	    set({
	      content
	    });
	  }
	  function show() {
	    const duration = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : getValue(instance.props.duration, 0, defaultProps.duration[1]);
	    if (instance.state.isDestroyed || !instance.state.isEnabled || isUsingTouch && !instance.props.touch) {
	      return;
	    }
	    if (getEventListenersTarget().hasAttribute('disabled')) {
	      return;
	    }
	    if (instance.props.onShow(instance) === false) {
	      return;
	    }
	    addDocumentClickListener();
	    popper.style.visibility = 'visible';
	    instance.state.isVisible = true;
	    if (instance.props.interactive) {
	      getEventListenersTarget().classList.add(ACTIVE_CLASS);
	    }
	    const transitionableElements = getTransitionableElements();
	    setTransitionDuration(transitionableElements.concat(popper), 0);
	    currentMountCallback = function currentMountCallback() {
	      if (!instance.state.isVisible) {
	        return;
	      }
	      const isInLooseFollowCursorMode = getIsInLooseFollowCursorMode();
	      if (isInLooseFollowCursorMode && lastMouseMoveEvent) {
	        positionVirtualReferenceNearCursor(lastMouseMoveEvent);
	      } else if (!isInLooseFollowCursorMode) {
	        instance.popperInstance.update();
	      }
	      if (instance.popperChildren.backdrop) {
	        instance.popperChildren.content.style.transitionDelay = `${Math.round(duration / 12)}ms`;
	      }
	      if (instance.props.sticky) {
	        makeSticky();
	      }
	      setTransitionDuration([popper], instance.props.updateDuration);
	      setTransitionDuration(transitionableElements, duration);
	      setVisibilityState(transitionableElements, 'visible');
	      onTransitionedIn(duration, () => {
	        if (instance.props.aria) {
	          getEventListenersTarget().setAttribute('aria-'.concat(instance.props.aria), popper.id);
	        }
	        instance.props.onShown(instance);
	        instance.state.isShown = true;
	      });
	    };
	    mount();
	  }
	  function hide() {
	    const duration = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : getValue(instance.props.duration, 1, defaultProps.duration[1]);
	    if (instance.state.isDestroyed || !instance.state.isEnabled && !isBeingDestroyed) {
	      return;
	    }
	    if (instance.props.onHide(instance) === false && !isBeingDestroyed) {
	      return;
	    }
	    removeDocumentClickListener();
	    popper.style.visibility = 'hidden';
	    instance.state.isVisible = false;
	    instance.state.isShown = false;
	    wasVisibleDuringPreviousUpdate = false;
	    if (instance.props.interactive) {
	      getEventListenersTarget().classList.remove(ACTIVE_CLASS);
	    }
	    const transitionableElements = getTransitionableElements();
	    setTransitionDuration(transitionableElements, duration);
	    setVisibilityState(transitionableElements, 'hidden');
	    onTransitionedOut(duration, () => {
	      if (!isScheduledToShow) {
	        removeFollowCursorListener();
	      }
	      if (instance.props.aria) {
	        getEventListenersTarget().removeAttribute('aria-'.concat(instance.props.aria));
	      }
	      instance.popperInstance.disableEventListeners();
	      instance.popperInstance.options.placement = instance.props.placement;
	      popper.parentNode.removeChild(popper);
	      instance.props.onHidden(instance);
	      instance.state.isMounted = false;
	    });
	  }
	  function destroy(destroyTargetInstances) {
	    if (instance.state.isDestroyed) {
	      return;
	    }
	    isBeingDestroyed = true;
	    if (instance.state.isMounted) {
	      hide(0);
	    }
	    removeTriggersFromReference();
	    delete reference._tippy;
	    const { target } = instance.props;
	    if (target && destroyTargetInstances && isRealElement(reference)) {
	      arrayFrom(reference.querySelectorAll(target)).forEach((child) => {
	        if (child._tippy) {
	          child._tippy.destroy();
	        }
	      });
	    }
	    if (instance.popperInstance) {
	      instance.popperInstance.destroy();
	    }
	    isBeingDestroyed = false;
	    instance.state.isDestroyed = true;
	  }
          }
          function group(instances) {
	  const _ref = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : {};
	      const _ref$delay = _ref.delay;
	      const delay = _ref$delay === void 0 ? instances[0].props.delay : _ref$delay;
	      const _ref$duration = _ref.duration;
	      const duration = _ref$duration === void 0 ? 0 : _ref$duration;
	  let isAnyTippyOpen = false;
	  instances.forEach((instance) => {
	    if (instance._originalProps) {
	      instance.set(instance._originalProps);
	    } else {
	      instance._originalProps = _extends$2({}, instance.props);
	    }
	  });
	  function setIsAnyTippyOpen(value) {
	    isAnyTippyOpen = value;
	    updateInstances();
	  }
	  function onShow(instance) {
	    instance._originalProps.onShow(instance);
	    instances.forEach((instance) => {
	      instance.set({
	        duration
	      });
	      if (instance.state.isVisible) {
	        instance.hide();
	      }
	    });
	    setIsAnyTippyOpen(true);
	  }
	  function onHide(instance) {
	    instance._originalProps.onHide(instance);
	    setIsAnyTippyOpen(false);
	  }
	  function onShown(instance) {
	    instance._originalProps.onShown(instance);
	    instance.set({
	      duration: instance._originalProps.duration
	    });
	  }
	  function updateInstances() {
	    instances.forEach((instance) => {
	      instance.set({
	        onShow,
	        onShown,
	        onHide,
	        delay: isAnyTippyOpen ? [0, isArray$1(delay) ? delay[1] : delay] : delay,
	        duration: isAnyTippyOpen ? duration : instance._originalProps.duration
	      });
	    });
	  }
	  updateInstances();
          }
          let globalEventListenersBound = false;
          function tippy(targets, options) {
	  validateOptions(options || {}, defaultProps);
	  if (!globalEventListenersBound) {
	    bindGlobalEventListeners();
	    globalEventListenersBound = true;
	  }
	  const props = _extends$2({}, defaultProps, options);
	  if (isBareVirtualElement(targets)) {
	    polyfillElementPrototypeProperties(targets);
	  }
	  const instances = getArrayOfElements(targets).reduce((acc, reference) => {
	    const instance = reference && createTippy(reference, props);
	    if (instance) {
	      acc.push(instance);
	    }
	    return acc;
	  }, []);
	  return isSingular(targets) ? instances[0] : instances;
          }
          tippy.version = version;
          tippy.defaults = defaultProps;
          tippy.setDefaults = function (partialDefaults) {
	  keys$1(partialDefaults).forEach((key) => {
	    defaultProps[key] = partialDefaults[key];
	  });
          };
          tippy.hideAll = hideAll;
          tippy.group = group;
          function autoInit() {
	  arrayFrom(document.querySelectorAll('[data-tippy]')).forEach((el) => {
	    const content = el.getAttribute('data-tippy');
	    if (content) {
	      tippy(el, {
	        content
	      });
	    }
	  });
          }
          if (isBrowser$1) {
	  setTimeout(autoInit);
          }

          const emitter = {
	  methods: {
	    dispatch: function dispatch(componentName, eventName, params) {
	      let parent = this.$parent || this.$root;
	      let { name } = parent.$options;
	      while (parent && (!name || name !== componentName)) {
	        parent = parent.$parent;
	        if (parent) {
	          name = parent.$options.name;
	        }
	      }
	      if (parent) {
	        parent.$emit.apply(parent, [eventName].concat(params));
	      }
	    }
	  }
          };

          const nodeList = [];
          const clickctx = '$clickoutsideCtx';
          let beginClick;
          let seed = 0;
          document.addEventListener('mousedown', event => beginClick = event);
          document.addEventListener('mouseup', (event) => {
	  nodeList.forEach((node) => {
	    node[clickctx].clickoutsideHandler(event, beginClick);
	  });
          });
          const bkClickoutside = {
	  bind: function bind(el, binding, vnode) {
	    nodeList.push(el);
	    const id = seed++;
	    const clickoutsideHandler = function clickoutsideHandler() {
	      const mouseup = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : {};
	      const mousedown = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : {};
	      if (!vnode.context
	      || !mouseup.target || !mousedown.target || el.contains(mouseup.target)
	      || el.contains(mousedown.target)
	      || el === mouseup.target
	      || vnode.context.popup
	      && (vnode.context.popup.contains(mouseup.target)
	      || vnode.context.popup.contains(mousedown.target)
	      )) {
	        return;
	      }
	      if (binding.expression
	      && el[clickctx].callbackName
	      && vnode.context[el[clickctx].callbackName]
	      ) {
	        vnode.context[el[clickctx].callbackName](mouseup, mousedown, el);
	      } else {
	        el[clickctx].bindingFn && el[clickctx].bindingFn(mouseup, mousedown, el);
	      }
	    };
	    el[clickctx] = {
	      id,
	      clickoutsideHandler,
	      callbackName: binding.expression,
	      callbackFn: binding.value
	    };
	  },
	  update: function update(el, binding) {
	    el[clickctx].callbackName = binding.expression;
	    el[clickctx].callbackFn = binding.value;
	  },
	  unbind: function unbind(el) {
	    for (let i = 0, len = nodeList.length; i < len; i++) {
	      if (nodeList[i][clickctx].id === el[clickctx].id) {
	        nodeList.splice(i, 1);
	        break;
	      }
	    }
	  }
          };
          bkClickoutside.install = function (Vue) {
	  Vue.directive('bkClickoutside', bkClickoutside);
          };

          function _extends$3() {
            return _extends$3 = Object.assign || function (a) {
              for (var b, c = 1;c < arguments.length;c++) for (const d in b = arguments[c], b)Object.prototype.hasOwnProperty.call(b, d) && (a[d] = b[d]);return a;
            }, _extends$3.apply(this, arguments);
          } const normalMerge = ['attrs', 'props', 'domProps']; const toArrayMerge = ['class', 'style', 'directives']; const functionalMerge = ['on', 'nativeOn']; const mergeJsxProps = function (a) {
            return a.reduce((c, a) => {
              for (const b in a) if (!c[b])c[b] = a[b];else if (-1 !== normalMerge.indexOf(b))c[b] = _extends$3({}, c[b], a[b]);else if (-1 !== toArrayMerge.indexOf(b)) {
                const d = c[b] instanceof Array ? c[b] : [c[b]]; const e = a[b] instanceof Array ? a[b] : [a[b]];c[b] = d.concat(e);
              } else if (-1 !== functionalMerge.indexOf(b)) {
                for (const f in a[b]) if (c[b][f]) {
                  const g = c[b][f] instanceof Array ? c[b][f] : [c[b][f]]; const h = a[b][f] instanceof Array ? a[b][f] : [a[b][f]];c[b][f] = g.concat(h);
                } else c[b][f] = a[b][f];
              } else if ('hook' == b) for (const i in a[b])c[b][i] = c[b][i] ? mergeFn(c[b][i], a[b][i]) : a[b][i];else c[b] = a[b];return c;
            }, {});
          }; var mergeFn = function (a, b) {
            return function () {
              a && a.apply(this, arguments), b && b.apply(this, arguments);
            };
          };const helper = mergeJsxProps;

          const script = {
	  name: 'bk-search-select-menu',
	  mixins: [locale.mixin],
	  props: {
	    list: {
	      type: Array,
	      default: function _default() {
	        return [];
	      }
	    },
	    isCondition: Boolean,
	    condition: Object,
	    displayKey: {
	      type: String,
	      require: true
	    },
	    filter: {
	      type: String,
	      default: ''
	    },
	    error: {
	      type: String,
	      default: ''
	    },
	    multiable: Boolean,
	    child: Boolean,
	    loading: Boolean,
	    remoteEmptyText: String,
	    remoteLoadingText: String,
	    checked: {
	      type: Object,
	      default: function _default() {
	        return {};
	      }
	    },
	    primaryKey: {
	      type: String,
	      require: true
	    },
	    isChildCondition: Boolean
	  },
	  data: function data() {
	    return {
	      hoverId: '',
	      hasFocus: false
	    };
	  },
	  mounted: function mounted() {
	    this.handleMounted();
	  },
	  beforeDestroy: function beforeDestroy() {
	    this.handleDestroy();
	  },
	  methods: {
	    handleDestroy: function handleDestroy() {
	      document.removeEventListener('keydown', this.handleDocumentKeydown);
	    },
	    handleMounted: function handleMounted() {
	      this.handleDestroy();
	      document.addEventListener('keydown', this.handleDocumentKeydown);
	    },
	    handleClick: function handleClick(item, index) {
	      if (item.disabled) {
	        return false;
	      }
	      if (this.isChildCondition && !this.multiable) {
	        this.$emit('child-condition-select', item, index);
	        this.hasFocus = false;
	      } else if (!this.multiable || !this.child) {
	        this.$emit('select', item, index);
	        this.hasFocus = false;
	        this.handleDestroy();
	      } else {
	        this.$refs[item[this.primaryKey]].style.display = this.checked[item[this.primaryKey]] ? 'none' : 'block';
	        this.$emit('select-check', item, index);
	      }
	    },
	    handleCheckClick: function handleCheckClick(item, index, next, old, id) {
	      this.$emit('select-check', item, index, next, old);
	    },
	    setCheckValue: function setCheckValue(item, val) {
	      const ref = this.$refs[item[this.primaryKey]];
	      if (ref) {
	        ref.style.display = this.checked[item[this.primaryKey]] ? 'none' : 'block';
	      }
	    },
	    handleSelectEnter: function handleSelectEnter(e) {
	      this.$emit('select-enter', e);
	    },
	    handleDocumentKeydown: function handleDocumentKeydown(e) {
	      const _this = this;
	      const len = this.list && this.list.length;
	      if (['ArrowDown', 'ArrowUp'].includes(e.code) && len && this.list.some(item => !item.disabled)) {
	        e.preventDefault();
	        e.stopPropagation();
	        this.$el.focus();
	        this.hasFocus = true;
	        let i = len;
	        let curIndex = this.list.findIndex(set => set[_this.primaryKey] === _this.hoverId);
	        while (i >= 0) {
	          curIndex = e.code === 'ArrowDown' ? curIndex + 1 : curIndex - 1;
	          curIndex = curIndex > len - 1 ? 0 : curIndex < 0 ? len - 1 : curIndex;
	          const item = this.list[curIndex];
	          if (!item.disabled) {
	            i = -1;
	            this.hoverId = item.id;
	            return;
	          }
	          i--;
	        }
	      } else if (this.hasFocus && ['Enter', 'NumpadEnter'].includes(e.code) && len && this.hoverId) {
	        const _curIndex = this.list.findIndex(set => set[_this.primaryKey] === _this.hoverId);
	        if (_curIndex > -1) {
	          const curItem = this.list[_curIndex];
	          this.handleClick(curItem, _curIndex);
	        }
	      }
	    },
	    handleKeyDown: function handleKeyDown(e) {
	      if (e.code === 'Enter' || e.code === 'NumpadEnter') ;
	    },
	    handleSelectCancel: function handleSelectCancel(e) {
	      const _this2 = this;
	      keys$1(this.checked).forEach((key) => {
	        _this2.$refs[key] && (_this2.$refs[key].style.display = 'none');
	      });
	      this.$emit('select-cancel', e);
	    }
	  },
	  render: function render(h) {
	    const _this3 = this;
	    const { list } = this;
	        const { condition } = this;
	        const { displayKey } = this;
	        const { primaryKey } = this;
	        const { filter } = this;
	        const { multiable } = this;
	        const { child } = this;
	        const { checked } = this;
	        const { remoteLoadingText } = this;
	        const { remoteEmptyText } = this;
	        const _this$loading = this.loading;
	        const loading = _this$loading === void 0 ? false : _this$loading;
	        const _this$isCondition = this.isCondition;
	        const isCondition = _this$isCondition === void 0 ? false : _this$isCondition;
	        const _this$isChildConditio = this.isChildCondition;
	        const isChildCondition = _this$isChildConditio === void 0 ? false : _this$isChildConditio;
	        const _this$error = this.error;
	        const error = _this$error === void 0 ? '' : _this$error;
	        const { hoverId } = this;
	    if (error) {
	      return h('div', {
	        class: {
	          'bk-search-list': true
	        }
	      }, [h('div', {
	        class: {
	          'bk-search-list-error': true
	        }
	      }, [error])]);
	    } if (!loading && (!list || !list.length)) {
	      return h('div', {
	        class: {
	          'bk-search-list': true
	        }
	      }, [h('div', {
	        class: {
	          'bk-search-list-loading': true
	        }
	      }, [remoteEmptyText])]);
	    }
	    const conditionEvent = {
	      on: {}
	    };
	    const wrapEvent = {
	      on: {}
	    };
	    const footerEnterEvent = {
	      on: {}
	    };
	    const footerCancelEvent = {
	      on: {}
	    };
	    this.hoverIndex = 0;
	    const items = this._l(list, (item, index) => {
	      const id = item[primaryKey];
	      const isFilter = filter && item[displayKey].includes(filter);
	      const text = item[displayKey];
	      const events = {
	        on: {}
	      };
	      let i; let pre; let next;
	      events.on.click = function (e) {
	        return _this3.handleClick(item, index);
	      };
	      if (isFilter) {
	        i = text.indexOf(filter);
	        pre = text.slice(0, i);
	        next = text.slice(i + filter.length, text.length);
	      }
	      return h('li', {
	        class: {
	          'bk-search-list-menu-item': true,
	          'is-group': !!item.isGroup,
	          'is-disabled': item.disabled,
	          'is-hover': !item.disabled && hoverId === id
	        }
	      }, [h('div', helper([{}, events, {
	        class: {
	          'item-name': true
	        }
	      }]), [isFilter ? h('div', [pre, h('span', {
	        class: {
	          'item-name-filter': true
	        }
	      }, [filter]), next]) : text]), h('span', {
	        directives: [{
	          name: 'show',
	          value: multiable && child && checked[text] && !isChildCondition
	        }],
	        ref: id,
	        class: {
	          'bk-icon icon-check-1 item-icon': true
	        }
	      })]);
	    });
	    if (multiable && child) {
	      footerEnterEvent.on.click = function (e) {
	        return _this3.handleSelectEnter(e);
	      };
	      footerCancelEvent.on.click = function (e) {
	        return _this3.handleSelectCancel(e);
	      };
	    }
	    if (isCondition && !isChildCondition) {
	      conditionEvent.on.click = function (_) {
	        return _this3.$emit('select-conditon', condition);
	      };
	    }
	    return h('div', helper([{
	      class: {
	        'bk-search-list': true
	      }
	    }, wrapEvent, {
	      attrs: {
	        tabIndex: '-1'
	      }
	    }]), [h('div', {
	      directives: [{
	        name: 'show',
	        value: loading
	      }],
	      class: {
	        'bk-search-list-loading': true
	      }
	    }, [remoteLoadingText]), !isCondition ? '' : h('div', helper([{
	      directives: [{
	        name: 'show',
	        value: !loading
	      }],
	      class: {
	        'bk-search-list-condition': true
	      }
	    }, conditionEvent]), [condition[displayKey]]), h('div', {
	      directives: [{
	        name: 'show',
	        value: !loading
	      }],
	      class: 'search-menu-wrap'
	    }, [h('ul', {
	      class: {
	        'bk-search-list-menu': true
	      }
	    }, [items])]), multiable && child && !loading ? h('div', {
	      class: {
	        'bk-search-list-footer': true
	      }
	    }, [h('span', helper([{
	      class: {
	        'footer-btn': true
	      }
	    }, footerEnterEvent]), [this.t('bk.searchSelect.ok')]), h('span', helper([{
	      class: {
	        'footer-btn': true
	      }
	    }, footerCancelEvent]), [this.t('bk.searchSelect.cancel')])]) : '']);
	  }
          };

          function normalizeComponent(
            template, style, script, scopeId, isFunctionalTemplate, moduleIdentifier
            , shadowMode, createInjector, createInjectorSSR, createInjectorShadow
          ) {
	  if (typeof shadowMode !== 'boolean') {
	    createInjectorSSR = createInjector;
	    createInjector = shadowMode;
	    shadowMode = false;
	  }
	  const options = typeof script === 'function' ? script.options : script;
	  if (template && template.render) {
	    options.render = template.render;
	    options.staticRenderFns = template.staticRenderFns;
	    options._compiled = true;
	    if (isFunctionalTemplate) {
	      options.functional = true;
	    }
	  }
	  if (scopeId) {
	    options._scopeId = scopeId;
	  }
	  let hook;
	  if (moduleIdentifier) {
	    hook = function hook(context) {
	      context = context
	      || this.$vnode && this.$vnode.ssrContext
	      || this.parent && this.parent.$vnode && this.parent.$vnode.ssrContext;
	      if (!context && typeof __VUE_SSR_CONTEXT__ !== 'undefined') {
	        context = __VUE_SSR_CONTEXT__;
	      }
	      if (style) {
	        style.call(this, createInjectorSSR(context));
	      }
	      if (context && context._registeredComponents) {
	        context._registeredComponents.add(moduleIdentifier);
	      }
	    };
	    options._ssrRegister = hook;
	  } else if (style) {
	    hook = shadowMode ? function () {
	      style.call(this, createInjectorShadow(this.$root.$options.shadowRoot));
	    } : function (context) {
	      style.call(this, createInjector(context));
	    };
	  }
	  if (hook) {
	    if (options.functional) {
	      const originalRender = options.render;
	      options.render = function renderWithStyleInjection(h, context) {
	        hook.call(context);
	        return originalRender(h, context);
	      };
	    } else {
	      const existing = options.beforeCreate;
	      options.beforeCreate = existing ? [].concat(existing, hook) : [hook];
	    }
	  }
	  return script;
          }
          const normalizeComponent_1 = normalizeComponent;

          /* script */
          const __vue_script__ = script;
          /* template */

          /* style */

          const __vue_inject_styles__ = undefined;
          /* scoped */

          const __vue_scope_id__ = undefined;
          /* module identifier */

          const __vue_module_identifier__ = undefined;
          /* functional template */

          const __vue_is_functional_template__ = undefined;
          /* style inject */

          /* style inject SSR */

          /* style inject shadow dom */

          const __vue_component__ = /* #__PURE__*/normalizeComponent_1({}, __vue_inject_styles__, __vue_script__, __vue_scope_id__, __vue_is_functional_template__, __vue_module_identifier__, false, undefined, undefined, undefined);

          const variable = {
	  dropdownMarginBottom: '4px'
          };
          const variable_1 = variable.dropdownMarginBottom;

          const requestFrame = (function () {
	  const raf = window.requestAnimationFrame || window.mozRequestAnimationFrame || window.webkitRequestAnimationFrame || function (fn) {
	    return window.setTimeout(fn, 20);
	  };
	  return function (fn) {
	    return raf(fn);
	  };
          }());
          const cancelFrame = (function () {
	  const cancel = window.cancelAnimationFrame || window.mozCancelAnimationFrame || window.webkitCancelAnimationFrame || window.clearTimeout;
	  return function (id) {
	    return cancel(id);
	  };
          }());
          const resetTrigger = function resetTrigger(element) {
	  const trigger = element.__resizeTrigger__;
	  const expand = trigger.firstElementChild;
	  const contract = trigger.lastElementChild;
	  const expandChild = expand.firstElementChild;
	  contract.scrollLeft = contract.scrollWidth;
	  contract.scrollTop = contract.scrollHeight;
	  expandChild.style.width = `${expand.offsetWidth + 1}px`;
	  expandChild.style.height = `${expand.offsetHeight + 1}px`;
	  expand.scrollLeft = expand.scrollWidth;
	  expand.scrollTop = expand.scrollHeight;
          };
          const checkTriggers = function checkTriggers(element) {
	  return element.offsetWidth !== element.__resizeLast__.width || element.offsetHeight !== element.__resizeLast__.height;
          };
          const scrollListener = function scrollListener(event) {
	  const _this = this;
	  resetTrigger(this);
	  if (this.__resizeRAF__) cancelFrame(this.__resizeRAF__);
	  this.__resizeRAF__ = requestFrame(() => {
	    if (checkTriggers(_this)) {
	      _this.__resizeLast__.width = _this.offsetWidth;
	      _this.__resizeLast__.height = _this.offsetHeight;
	      _this.__resizeListeners__.forEach((fn) => {
	        fn.call(_this, event);
	      });
	    }
	  });
          };
          const { attachEvent } = document;
          const DOM_PREFIXES = 'Webkit Moz O ms'.split(' ');
          const START_EVENTS = 'webkitAnimationStart animationstart oAnimationStart MSAnimationStart'.split(' ');
          const RESIZE_ANIMATION_NAME = 'resizeanim';
          let animation = false;
          let keyFramePrefix = '';
          let animationStartEvent = 'animationstart';
          if (!attachEvent) {
	  const testElement = document.createElement('fakeelement');
	  if (testElement.style.animationName !== undefined) {
	    animation = true;
	  }
	  if (animation === false) {
	    let prefix = '';
	    for (let i$2 = 0; i$2 < DOM_PREFIXES.length; i$2++) {
	      if (testElement.style[`${DOM_PREFIXES[i$2]}AnimationName`] !== undefined) {
	        prefix = DOM_PREFIXES[i$2];
	        keyFramePrefix = `-${prefix.toLowerCase()}-`;
	        animationStartEvent = START_EVENTS[i$2];
	        animation = true;
	        break;
	      }
	    }
	  }
          }
          let stylesCreated = false;
          const createStyles = function createStyles() {
	  if (!stylesCreated) {
	    const animationKeyframes = '@'.concat(keyFramePrefix, 'keyframes ').concat(RESIZE_ANIMATION_NAME, ' { from { opacity: 0; } to { opacity: 0; } } ');
	    const animationStyle = ''.concat(keyFramePrefix, 'animation: 1ms ').concat(RESIZE_ANIMATION_NAME, ';');
	    const css = ''.concat(animationKeyframes, '\n      .resize-triggers { ').concat(animationStyle, ' visibility: hidden; opacity: 0; }\n      .resize-triggers, .resize-triggers > div, .contract-trigger:before { content: " "; display: block; position: absolute; top: 0; left: 0; height: 100%; width: 100%; overflow: hidden; z-index: -1 }\n      .resize-triggers > div { background: #eee; overflow: auto; }\n      .contract-trigger:before { width: 200%; height: 200%; }');
	    const head = document.head || document.getElementsByTagName('head')[0];
	    const style = document.createElement('style');
	    style.type = 'text/css';
	    if (style.styleSheet) {
	      style.styleSheet.cssText = css;
	    } else {
	      style.appendChild(document.createTextNode(css));
	    }
	    head.appendChild(style);
	    stylesCreated = true;
	  }
          };
          const addResizeListener = function addResizeListener(element, fn) {
	  if (attachEvent) {
	    element.attachEvent('onresize', fn);
	  } else {
	    if (!element.__resizeTrigger__) {
	      if (getComputedStyle(element).position === 'static') {
	        element.style.position = 'relative';
	      }
	      createStyles();
	      element.__resizeLast__ = {};
	      element.__resizeListeners__ = [];
	      const resizeTrigger = element.__resizeTrigger__ = document.createElement('div');
	      resizeTrigger.className = 'resize-triggers';
	      resizeTrigger.innerHTML = '<div class="expand-trigger"><div></div></div><div class="contract-trigger"></div>';
	      element.appendChild(resizeTrigger);
	      resetTrigger(element);
	      element.addEventListener('scroll', scrollListener, true);
	      if (animationStartEvent) {
	        resizeTrigger.addEventListener(animationStartEvent, (event) => {
	          if (event.animationName === RESIZE_ANIMATION_NAME) {
	            resetTrigger(element);
	          }
	        });
	      }
	    }
	    element.__resizeListeners__.push(fn);
	  }
          };
          const removeResizeListener = function removeResizeListener(element, fn) {
	  if (!element || !element.__resizeListeners__) return;
	  if (attachEvent) {
	    element.detachEvent('onresize', fn);
	  } else {
	    element.__resizeListeners__.splice(element.__resizeListeners__.indexOf(fn), 1);
	    if (!element.__resizeListeners__.length) {
	      element.removeEventListener('scroll', scrollListener);
	      element.__resizeTrigger__ = !element.removeChild(element.__resizeTrigger__);
	    }
	  }
          };

          const script$1 = {
	  name: 'bk-search-select',
	  directives: {
	    clickoutside: bkClickoutside
	  },
	  mixins: [emitter, locale.mixin],
	  model: {
	    prop: 'values',
	    event: 'change'
	  },
	  props: {
	    data: {
	      type: Array,
	      default: function _default() {
	        return [];
	      }
	    },
	    splitCode: {
	      type: String,
	      default: ' | '
	    },
	    explainCode: {
	      type: String,
	      default: '：'
	    },
	    placeholder: {
	      type: String,
	      default: ''
	    },
	    emptyText: {
	      type: String,
	      default: ''
	    },
	    maxHeight: {
	      type: [String, Number],
	      default: 120
	    },
	    minHeight: {
	      type: [String, Number],
	      default: 26
	    },
	    shrink: {
	      type: Boolean,
	      default: true
	    },
	    showDelay: {
	      type: Number,
	      default: 100
	    },
	    displayKey: {
	      type: String,
	      default: 'name'
	    },
	    primaryKey: {
	      type: String,
	      default: 'id'
	    },
	    condition: {
	      type: Object,
	      default: function _default() {
	        return {};
	      }
	    },
	    values: {
	      type: Array,
	      default: function _default() {
	        return [];
	      }
	    },
	    filter: Boolean,
	    filterChildrenMethod: Function,
	    filterMenuMethod: Function,
	    remoteMethod: Function,
	    remoteEmptyText: {
	      type: String,
	      default: ''
	    },
	    remoteLoadingText: {
	      type: String,
	      default: ''
	    },
	    multiable: {
	      type: Boolean,
	      default: false
	    },
	    keyDelay: {
	      type: Number,
	      default: 300
	    },
	    showCondition: {
	      type: Boolean,
	      default: true
	    },
	    readonly: {
	      type: Boolean,
	      default: false
	    },
	    wrapZindex: {
	      type: [String, Number],
	      default: 9
	    },
	    defaultFocus: {
	      type: Boolean,
	      default: false
	    },
	    inputType: {
	      type: String,
	      default: 'text',
	      validator: function validator(v) {
	        return ['text', 'number'].indexOf(v) !== -1;
	      }
	    },
	    popoverZindex: {
	      type: Number,
	      default: 999
	    },
	    showPopoverTagChange: {
	      type: Boolean,
	      default: true
	    },
	    clearable: {
	      type: Boolean,
	      default: false
	    },
	    validateMessage: {
	      type: String,
	      default: ''
	    },
	    extCls: {
	      type: String,
	      default: ''
	    }
	  },
	  data: function data() {
	    return {
	      menuInstance: null,
	      popperMenuInstance: null,
	      menuChildInstance: null,
	      menu: {
	        active: -1,
	        id: null,
	        child: false,
	        checked: {},
	        loading: false,
	        childCondition: {}
	      },
	      chip: {
	        list: []
	      },
	      input: {
	        focus: false,
	        value: ''
	      },
	      overflow: {
	        chipIndex: -1
	      },
	      handleInputSearchPlus: function handleInputSearchPlus() {},
	      handleSearchSelectResize: function handleSearchSelectResize() {},
	      defaultPlaceholder: '',
	      defaultEmptyText: '',
	      defaultRemoteEmptyText: '',
	      defaultRemoteLoadingText: '',
	      defaultCondition: {},
	      validateStr: ''
	    };
	  },
	  computed: {
	    curItem: function curItem() {
	      const _this = this;
	      return this.data.find(item => item[_this.primaryKey] === _this.menu.id) || {};
	    },
	    childList: function childList() {
	      const ret = [];
	      let i = 0;
	      while (i < this.data.length) {
	        const item = this.data[i];
	        if (item.children && item.children.length) {
	          ret.push.apply(ret, _toConsumableArray(item.children));
	        }
	        i++;
	      }
	      return ret;
	    },
	    showItemPlaceholder: function showItemPlaceholder() {
	      return this.menu.active >= 0 && String(this.curItem.placeholder).length && this.input.value === this.curItem[this.displayKey] + this.explainCode;
	    }
	  },
	  watch: {
	    values: {
	      handler: function handler(v) {
	        if (v !== this.chip.list) {
	          this.chip.list = _toConsumableArray(v);
	        }
	      },
	      deep: true,
	      immediate: true
	    },
	    validateMessage: {
	      handler: function handler(v) {
	        this.validateStr = v;
	      },
	      immediate: true
	    },
	    'input.focus': {
	      handler: function handler(v) {
	        const _this2 = this;
	        if (v) {
	          this.overflow.chipIndex = -1;
	        } else {
	          this.$refs.wrap && this.$refs.wrap.scrollTo(0, 0);
	          setTimeout(() => {
	            _this2._isMounted && _this2.handleSearchInputResize();
	          }, 300);
	        }
	      },
	      immediate: true
	    }
	  },
	  created: function created() {
	    const _this3 = this;
	    this.input.focus = this.defaultFocus;
	    this.defaultPlaceholder = this.placeholder || this.t('bk.searchSelect.placeholder');
	    this.defaultEmptyText = this.emptyText || this.t('bk.searchSelect.emptyText');
	    this.defaultRemoteEmptyText = this.remoteEmptyText || this.t('bk.searchSelect.remoteEmptyText');
	    this.defaultRemoteLoadingText = this.remoteLoadingText || this.t('bk.searchSelect.remoteLoadingText');
	    this.defaultCondition = _extends({}, {
	      name: this.t('bk.searchSelect.condition')
	    });
	    if (!keys$1(this.defaultCondition).includes(this.displayKey)) {
	      this.defaultCondition[this.displayKey] = this.t('bk.searchSelect.condition');
	    }
	    this.handleInputSearchPlus = debounce(this.keyDelay, v => _this3.handleSearch(v));
	  },
	  mounted: function mounted() {
	    if (this.input.focus) {
	      this.$refs.input.focus();
	    }
	    this.handleSearchSelectResize = debounce(32, this.handleSearchInputResize);
	    addResizeListener(this.$el, this.handleSearchSelectResize);
	  },
	  beforeDestroy: function beforeDestroy() {
	    this.menuInstance = null;
	    this.menuChildInstance = null;
	    this.popperMenuInstance && this.popperMenuInstance.destroy(true);
	    removeResizeListener(this.$el, this.handleSearchSelectResize);
	  },
	  methods: {
	    handleSearchInputResize: function handleSearchInputResize() {
	      if (this.input.focus || this.chip.list.length < 1) {
	        this.overflow.chipIndex = -1;
	        return;
	      }
	      const inputEl = this.$el.querySelector('.bk-search-select');
	      const maxWidth = this.$el.querySelector('.search-input').clientWidth - 8;
	      const tagList = inputEl.querySelectorAll('.search-input-chip:not(.overflow-chip)');
	      let width = 0;
	      let index = 0;
	      let i = 0;
	      while (width <= maxWidth - 40 && i <= tagList.length - 1) {
	        const el = tagList[i];
	        width += el ? el.clientWidth + 6 : 0;
	        i += 1;
	        if (width <= maxWidth - 40) index = i;
	      }
	      if (index === tagList.length - 1 && width <= maxWidth) {
	        this.overflow.chipIndex = -1;
	        return;
	      }
	      this.overflow.chipIndex = width >= maxWidth - 40 ? index : -1;
	    },
	    initMenu: function initMenu() {
	      if (!this.menuInstance) {
	        this.menuInstance = new Vue(__vue_component__).$mount();
	        this.menuInstance.condition = this.defaultCondition;
	        this.menuInstance.displayKey = this.displayKey;
	        this.menuInstance.primaryKey = this.primaryKey;
	        this.menuInstance.multiable = false;
	        this.menuInstance.$on('select', this.handleMenuSelect);
	        this.menuInstance.$on('select-conditon', this.handleSelectConditon);
	      }
	    },
	    initChildMenu: function initChildMenu() {
	      this.menuChildInstance = new Vue(__vue_component__).$mount();
	      this.menuChildInstance.displayKey = this.displayKey;
	      this.menuChildInstance.primaryKey = this.primaryKey;
	      this.menuChildInstance.multiable = this.curItem.conditions && this.curItem.conditions.length ? false : this.curItem.multiable || false;
	      this.menuChildInstance.child = true;
	      this.menuChildInstance.remoteEmptyText = this.defaultRemoteEmptyText;
	      this.menuChildInstance.remoteLoadingText = this.defaultRemoteLoadingText;
	      this.menuChildInstance.$on('select', this.handleMenuChildSelect);
	      this.menuChildInstance.$on('select-check', this.handleSelectCheck);
	      this.menuChildInstance.$on('select-enter', this.handleKeyEnter);
	      this.menuChildInstance.$on('select-cancel', this.handleCancel);
	      this.menuChildInstance.$on('child-condition-select', this.handleChildConditionSelect);
	    },
	    initPopover: function initPopover(el) {
	      const _this4 = this;
	      if (!this.popperMenuInstance) {
	        this.popperMenuInstance = tippy(this.$refs.input, {
	          content: el || this.menuInstance.$el,
	          arrow: false,
	          placement: 'bottom-start',
	          trigger: 'manual',
	          theme: 'light bk-search-select-theme',
	          hideOnClick: false,
	          animateFill: false,
	          animation: 'slide-toggle',
	          lazy: false,
	          ignoreAttributes: true,
	          boundary: 'window',
	          distance: 10 + _parseInt$2(variable_1),
	          zIndex: this.popoverZindex,
	          onHide: function onHide() {
	            _this4.menuInstance && _this4.menuInstance.handleDestroy();
	            _this4.menuChildInstance && _this4.menuChildInstance.handleDestroy();
	            return true;
	          }
	        });
	      }
	    },
	    showMenu: function showMenu() {
	      const show = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : true;
	      if (!this.menuInstance) {
	        this.initMenu();
	      }
	      this.handelePopperEventListener(false);
	      this.menuInstance.isCondition = this.showCondition && !!this.chip.list.length && this.chip.list[this.chip.list.length - 1][this.primaryKey] !== this.defaultCondition[this.primaryKey];
	      this.menuInstance.list = this.data;
	      if (show) {
	        this.showPopper(this.menuInstance.$el);
	        this.$emit('show-menu', this.menuInstance);
	      } else {
	        this.hidePopper();
	      }
	    },
	    showChildMenu: function showChildMenu(list, filter) {
	      const isShow = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : true;
	      this.menuChildInstance.filter = filter;
	      this.menuChildInstance.list = list;
	      this.handelePopperEventListener(true);
	      isShow && this.showPopper(this.menuChildInstance.$el);
	    },
	    handelePopperEventListener: function handelePopperEventListener() {
	      const isChild = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : false;
	      if (isChild) {
	        this.menuInstance && this.menuInstance.handleDestroy();
	        this.menuChildInstance && this.menuChildInstance.handleMounted();
	        return;
	      }
	      this.menuChildInstance && this.menuChildInstance.handleDestroy();
	      this.menuInstance.handleMounted();
	    },
	    showPopper: function showPopper(el) {
	      if (this.data.length) {
	        if (!this.popperMenuInstance) {
	          this.initPopover();
	        } else {
	          this.popperMenuInstance.setContent(el);
	        }
	        this.popperMenuInstance.popperInstance.update();
	        this.popperMenuInstance.show(this.showDelay);
	      }
	    },
	    hidePopper: function hidePopper() {
	      this.popperMenuInstance && this.popperMenuInstance.hide(0);
	    },
	    handleInputChange: function handleInputChange(e) {
	      this.clearInput();
	      let text = e.target.innerText;
	      if (/(\r|\n)/gm.test(text) || /\s{2}/gm.test(text)) {
	        e.preventDefault();
	        text = text.replace(/(\r|\n)/gm, this.splitCode).replace(/\s{2}/gm, '');
	        this.$refs.input.innerText = text;
	        this.handleInputFocus();
	      }
	      this.input.value = text;
	      this.handleInputSearchPlus(text);
	      this.$emit('input-change', e);
	    },
	    handleSearch: function handleSearch(text) {
	      const _this5 = this;
	      return _asyncToGenerator(regenerator.mark(function _callee() {
	        let include; let list; let filter;
	        return regenerator.wrap((_context) => {
	          while (1) {
	            switch (_context.prev = _context.next) {
	              case 0:
	                include = _this5.input.value.includes(_this5.explainCode);
	                list = [];
	                if (!(include && _this5.menuChildInstance)) {
	                  _context.next = 16;
	                  break;
	                }
	                filter = text.replace(_this5.curItem[_this5.displayKey] + _this5.explainCode, '');
	                if (!(_this5.curItem.remote && typeof _this5.remoteMethod === 'function')) {
	                  _context.next = 12;
	                  break;
	                }
	                _this5.menuChildInstance.loading = true;
	                _context.next = 8;
	                return _this5.remoteMethod(filter, _this5.curItem, _this5.menu.active).finally(() => {
	                  _this5.menuChildInstance.loading = false;
	                });
	              case 8:
	                list = _context.sent;
	                if (list && list.length) {
	                  _this5.showChildMenu(list, filter, !!list.length);
	                } else {
	                  _this5.hidePopper();
	                }
	                _context.next = 14;
	                break;
	              case 12:
	                list = _this5.handleFilter(filter);
	                if (list && list.length) {
	                  _this5.showChildMenu(list, filter, !!list.length);
	                } else {
	                  _this5.hidePopper();
	                }
	              case 14:
	                _context.next = 17;
	                break;
	              case 16:
	                if (!include && _this5.menuInstance) {
	                  list = _this5.handleFilter(text);
	                  if (list && list.length) {
	                    _this5.menuInstance.filter = text;
	                    _this5.menuInstance.list = list;
	                    _this5.showPopper(_this5.menuInstance.$el);
	                  } else {
	                    if (_this5.$refs.input.innerText) {
	                      _this5.hidePopper();
	                    }
	                  }
	                }
	              case 17:
	              case 'end':
	                return _context.stop();
	            }
	          }
	        }, _callee);
	      }))();
	    },
	    handleFilter: function handleFilter(v) {
	      const _this6 = this;
	      let filterList = [];
	      if (!this.input.value.length || !~this.input.value.indexOf(this.explainCode)) {
	        if (this.filter && typeof this.filterMenuMethod === 'function') {
	          filterList = this.filterMenuMethod(this.data, v);
	        } else {
	          if (v.length) {
	            let _filterList;
	            filterList = this.childList.filter(item => item[_this6.displayKey] && ~item[_this6.displayKey].indexOf(v));
	            if (filterList.length) {
	              let item = filterList[filterList.length - 1];
	              item = _objectSpread({}, item, {
	                isGroup: true
	              });
	              filterList[filterList.length - 1] = item;
	            }
	            (_filterList = filterList).push.apply(_filterList, _toConsumableArray(this.data.filter(item => item[_this6.displayKey] && ~item[_this6.displayKey].indexOf(v))));
	          } else {
	            filterList = this.data;
	          }
	        }
	      } else if (this.curItem.children && this.curItem.children.length) {
	        if (this.filter && typeof this.filterChildrenMethod === 'function') {
	          filterList = this.filterChildrenMethod(this.curItem.children, v);
	        } else {
	          filterList = this.curItem.children.filter(item => item[_this6.displayKey] && ~item[_this6.displayKey].indexOf(v));
	        }
	      }
	      return filterList;
	    },
	    handleInputCut: function handleInputCut(e) {
	      const selection = document.getSelection();
	      if (selection.anchorOffset >= this.input.value.length) {
	        this.input.value = '';
	      }
	      this.$emit('input-cut', e);
	    },
	    handleInputOutSide: function handleInputOutSide(e) {
	      const parent = e.target.offsetParent;
	      const classList = parent ? parent.classList : null;
	      const unFocus = !parent || classList && !from_1$1(classList.values()).some(key => ['bk-search-select', 'bk-search-list', 'tippy-tooltip', 'bk-form-checkbox', 'search-input-list', 'search-input-chip'].includes(key));
	      if (unFocus) {
	        this.hidePopper();
	        this.input.focus = false;
	      }
	      this.$emit('input-click-outside', e);
	    },
	    handleCancel: function handleCancel(e) {
	      this.handleClearChildSelectChecked();
	      this.hidePopper();
	      this.input.focus = false;
	      this.$refs.input.focus();
	    },
	    handleInputClick: function handleInputClick(e) {
	      const _this7 = this;
	      this.input.focus = true;
	      if (!this.input.value) {
	        if (!this.menuInstance) {
	          this.initMenu();
	        }
	        this.menuInstance.isCondition = this.showCondition && !!this.chip.list.length && this.chip.list[this.chip.list.length - 1][this.primaryKey] !== this.defaultCondition[this.primaryKey];
	        this.menuInstance.list = this.data;
	        this.menu.child = false;
	        this.$nextTick((_) => {
	          _this7.handelePopperEventListener();
	          _this7.showPopper(_this7.menuInstance.$el);
	        });
	      } else {
	        const cur = this.curItem;
	        if (cur && (cur.children && cur.children.length || cur.conditions && cur.conditions.length) && this.popperMenuInstance) {
	          if (this.menuChildInstance) {
	            this.menuChildInstance.error = '';
	          }
	          this.menu.child = true;
	          this.popperMenuInstance.show(this.showDelay);
	        } else if (typeof cur.id === 'undefined' && this.menuInstance && this.menuInstance.list.length && this.menuInstance.filter) {
	          this.popperMenuInstance.show(this.showDelay);
	        }
	        this.handelePopperEventListener(true);
	      }
	      this.$emit('input-click', e);
	    },
	    handleInputFocus: function handleInputFocus(e) {
	      this.input.focus = true;
	      const { input } = this.$refs;
	      let selection = null;
	      if (window.getSelection) {
	        selection = window.getSelection();
	        selection.selectAllChildren(input);
	        selection.collapseToEnd();
	      } else if (document.onselectionchange) {
	        selection = document.onselectionchange.createRange();
	        selection.moveToElementText(input);
	        selection.collapse(false);
	        selection.select();
	      }
	      this.$emit('input-focus', e);
	    },
	    updateChildMenu: function updateChildMenu(item, index, isCondition) {
	      const _this8 = this;
	      return _asyncToGenerator(regenerator.mark(function _callee2() {
	        let isChild; let isRemote; let list;
	        return regenerator.wrap((_context2) => {
	          while (1) {
	            switch (_context2.prev = _context2.next) {
	              case 0:
	                isChild = item.children && item.children.length;
	                if (!isCondition) {
	                  _context2.next = 14;
	                  break;
	                }
	                _this8.$refs.input.blur();
	                if (!_this8.menuChildInstance || _this8.menuChildInstance.multiable || _this8.menuChildInstance.multiable !== _this8.curItem.multiable) {
	                  _this8.initChildMenu();
	                }
	                _this8.menuChildInstance.isChildCondition = isCondition;
	                _this8.menuChildInstance.error = '';
	                _this8.menuChildInstance.loading = false;
	                _this8.menuChildInstance.checked = _this8.menu.checked;
	                _this8.showPopper(_this8.menuChildInstance.$el);
	                _this8.menu.child = false;
	                _this8.menuChildInstance.list = item.conditions;
	                setTimeout(() => {
	                  _this8.$refs.input.focus();
	                }, 20);
	                _context2.next = 37;
	                break;
	              case 14:
	                isRemote = _this8.curItem.remote && typeof _this8.remoteMethod === 'function';
	                if (!(isChild || isRemote)) {
	                  _context2.next = 35;
	                  break;
	                }
	                _this8.$refs.input.blur();
	                if (!_this8.menuChildInstance || _this8.menuChildInstance.multiable || _this8.menuChildInstance.multiable !== _this8.curItem.multiable) {
	                  _this8.initChildMenu();
	                }
	                _this8.menuChildInstance.isChildCondition = isCondition;
	                _this8.menuChildInstance.error = '';
	                _this8.menuChildInstance.loading = isRemote;
	                _this8.menuChildInstance.checked = _this8.menu.checked;
	                _this8.showPopper(_this8.menuChildInstance.$el);
	                _this8.menu.child = true;
	                if (!isRemote) {
	                  _context2.next = 31;
	                  break;
	                }
	                _context2.next = 27;
	                return _this8.remoteMethod(_this8.input.value, item, index).finally(() => {
	                  _this8.menuChildInstance.loading = false;
	                });
	              case 27:
	                list = _context2.sent;
	                _this8.menuChildInstance.list = list;
	                _context2.next = 32;
	                break;
	              case 31:
	                _this8.menuChildInstance.list = item.children;
	              case 32:
	                setTimeout(() => {
	                  _this8.$refs.input.focus();
	                }, 20);
	                _context2.next = 37;
	                break;
	              case 35:
	                _this8.hidePopper();
	                setTimeout(() => {
	                  _this8.handleInputFocus();
	                }, 20);
	              case 37:
	              case 'end':
	                return _context2.stop();
	            }
	          }
	        }, _callee2);
	      }))();
	    },
	    handleMenuSelect: function handleMenuSelect(item, index) {
	      const _this9 = this;
	      const isChildClick = ~this.data.findIndex(set => set[_this9.primaryKey] === item[_this9.primaryKey]);
	      if (!isChildClick) {
	        this.input.value = item[this.displayKey];
	        this.$nextTick().then(() => {
	          _this9.updateInput(_this9.input.value);
	          _this9.handleKeyEnter();
	        });
	      } else {
	        this.menu.active = ~isChildClick;
	        this.menu.id = this.data[this.menu.active][this.primaryKey];
	        const isChildCondition = !!(this.curItem.conditions && this.curItem.conditions.length);
	        this.input.value = item[this.displayKey] + this.explainCode;
	        this.$nextTick().then(() => {
	          _this9.updateInput(_this9.input.value);
	          _this9.updateChildMenu(item, index, isChildCondition);
	          _this9.$emit('menu-select', item, index);
	        });
	      }
	    },
	    handleMenuChildSelect: function handleMenuChildSelect(item, index) {
	      this.input.value += item[this.displayKey];
	      this.updateInput(this.input.value);
	      this.handleEnter(this.input.value, item, true);
	      this.$emit('menu-child-select', item, index);
	    },
	    handleChildConditionSelect: function handleChildConditionSelect(item, index) {
	      this.input.value += item[this.displayKey];
	      this.updateInput(this.input.value);
	      this.menu.childCondition = item;
	      this.updateChildMenu(this.curItem, index, false);
	      this.$emit('menu-child-condition-select', item, index);
	    },
	    handleInputKeyup: function handleInputKeyup(e) {
	      if (this.readonly && !(e.code === 'Backspace')) {
	        e.preventDefault();
	        return false;
	      }
	      switch (e.code) {
	        case 'Enter':
	        case 'NumpadEnter':
	          this.handleKeyEnter(e, true, true);
	          break;
	        case 'Backspace':
	          this.handleKeyBackspace(e);
	          break;
	        case 'ArrowDown':
	        case 'ArrowUp':
	          e.preventDefault();
	          break;
	        default:
	          if (this.inputType === 'number') {
	            const value = `${this.input.value}`;
	            if (!(value === '' && e.key === '-' || value !== '0' && value !== '-0' && e.key === '0' || (value === '0' || value === '-0' || /^-?[1-9]?[0-9]*[1-9]+$/.test(value)) && e.key === '.' || '123456789'.indexOf(e.key) > -1)) {
	              e.preventDefault();
	              return false;
	            }
	          }
	          this.handleKeyDefault(e);
	          return false;
	      }
	    },
	    handleKeyDefault: function handleKeyDefault(e) {
	      if (keys$1(this.menu.checked).length) {
	        e.preventDefault();
	        return false;
	      }
	    },
	    handleKeyBackspace: function handleKeyBackspace(e) {
	      const _this10 = this;
	      const keys = keys$1(this.menu.checked);
	      if (this.curItem.multiable && keys.length) {
	        const key = keys[keys.length - 1];
	        this.menuChildInstance && this.menuChildInstance.setCheckValue(this.menu.checked[key], false);
	        delete this.menu.checked[key];
	        this.updateCheckedInputVal();
	        e.preventDefault();
	        this.handleInputFocus();
	        return false;
	      }
	      const condition = this.menu.childCondition[this.displayKey];
	      const curVal = this.curItem[this.displayKey] + this.explainCode;
	      if (condition && curVal + condition === this.input.value) {
	        this.menu.childCondition = {};
	        this.input.value = curVal;
	        this.updateInput(this.input.value);
	        this.updateChildMenu(this.curItem, this.menu.active, true);
	        e.preventDefault();
	        return false;
	      }
	      if (!this.input.value && !(!this.chip.list.length && !this.$refs.input.textContent.length)) {
	        const item = this.chip.list.pop();
	        this.$nextTick().then(() => {
	          _this10.showMenu(_this10.showPopoverTagChange);
	        });
	        this.$emit('change', this.chip.list);
	        this.$emit('key-delete', item);
	        this.dispatch('bk-form-item', 'form-change');
	      } else {
	        if (!this.input.value.includes(this.curItem[this.displayKey] + this.explainCode)) {
	          this.menu.active = -1;
	          this.menu.id = null;
	        } else {
	          if (this.readonly) {
	            this.updateInput();
	            this.handleCancel();
	            this.menu.active = -1;
	            this.menu.id = null;
	            this.input.value = '';
	            e.preventDefault();
	            return false;
	          }
	        }
	      }
	    },
	    handleKeyEnter: function handleKeyEnter(e) {
	      const _this11 = this;
	      const needShowPopover = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : true;
	      const needEmitKeyEnter = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : false;
	      return _asyncToGenerator(regenerator.mark(function _callee3() {
	        return regenerator.wrap((_context3) => {
	          while (1) {
	            switch (_context3.prev = _context3.next) {
	              case 0:
	                _context3.next = 2;
	                return new promise$1((resolve) => {
	                  if (!_this11.input.value) {
	                    resolve();
	                  } else if (_this11.input.value === _this11.curItem[_this11.displayKey] + _this11.explainCode) {
	                    e.preventDefault();
	                    if (!_this11.menuChildInstance) {
	                      _this11.initChildMenu();
	                    }
	                    _this11.menuChildInstance.error = _this11.defaultEmptyText;
	                    _this11.$nextTick((_) => {
	                      _this11.showPopper(_this11.menuChildInstance.$el);
	                    });
	                    _this11.handleInputFocus();
	                    resolve();
	                  } else {
	                    setTimeout(() => {
	                      if (_this11.menu.id !== null) {
	                        let _this11$handleEnter;
	                        let val = _this11.input.value.replace(_this11.curItem[_this11.displayKey] + _this11.explainCode, '');
	                        if (keys$1(_this11.menu.childCondition).length) {
	                          val = val.replace(_this11.menu.childCondition[_this11.displayKey], '');
	                        }
	                        _this11.handleEnter(_this11.input.value, (_this11$handleEnter = {}, _defineProperty(_this11$handleEnter, _this11.primaryKey, val), _defineProperty(_this11$handleEnter, _this11.displayKey, val), _this11$handleEnter), true, needShowPopover);
	                      } else {
	                        let _this11$handleEnter2;
	                        _this11.handleEnter(_this11.input.value, (_this11$handleEnter2 = {}, _defineProperty(_this11$handleEnter2, _this11.primaryKey, _this11.input.value), _defineProperty(_this11$handleEnter2, _this11.displayKey, _this11.input.value), _this11$handleEnter2), false, needShowPopover);
	                      }
	                      resolve();
	                    }, 0);
	                  }
	                });
	              case 2:
	                needEmitKeyEnter && _this11.$emit('key-enter', e);
	              case 3:
	              case 'end':
	                return _context3.stop();
	            }
	          }
	        }, _callee3);
	      }))();
	    },
	    handleValidate: function handleValidate(valList) {
	      const _this12 = this;
	      return _asyncToGenerator(regenerator.mark(function _callee4() {
	        let validate; let selection;
	        return regenerator.wrap((_context4) => {
	          while (1) {
	            switch (_context4.prev = _context4.next) {
	              case 0:
	                validate = true;
	                if (!(_this12.curItem && _this12.curItem.validate && typeof _this12.curItem.validate === 'function')) {
	                  _context4.next = 8;
	                  break;
	                }
	                _context4.next = 4;
	                return _this12.curItem.validate(_toConsumableArray(valList), _this12.curItem);
	              case 4:
	                validate = _context4.sent;
	                if (typeof validate === 'string') {
	                  _this12.validateStr = validate;
	                  validate = false;
	                } else {
	                  validate && (_this12.validateStr = '');
	                }
	                _context4.next = 9;
	                break;
	              case 8:
	                _this12.validateStr = '';
	              case 9:
	                if (!validate) {
	                  selection = window.getSelection();
	                  if (selection.focusOffset === 0) {
	                    selection.selectAllChildren(_this12.$refs.input);
	                    selection.collapseToEnd();
	                  }
	                }
	                return _context4.abrupt('return', validate);
	              case 11:
	              case 'end':
	                return _context4.stop();
	            }
	          }
	        }, _callee4);
	      }))();
	    },
	    handleEnter: function handleEnter(val, item) {
	      const _this13 = this;
	      const child = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : false;
	      const needShowPopover = arguments.length > 3 && arguments[3] !== undefined ? arguments[3] : true;
	      return _asyncToGenerator(regenerator.mark(function _callee5() {
	        let values; let data; let validate; let _validate;
	        return regenerator.wrap((_context5) => {
	          while (1) {
	            switch (_context5.prev = _context5.next) {
	              case 0:
	                if (!child) {
	                  _context5.next = 19;
	                  break;
	                }
	                if (!(_this13.input.value === _this13.defaultCondition[_this13.displayKey])) {
	                  _context5.next = 5;
	                  break;
	                }
	                _this13.chip.list.push(_this13.defaultCondition);
	                _context5.next = 17;
	                break;
	              case 5:
	                values = [];
	                if (keys$1(_this13.menu.checked).length) {
	                  values = values$1(_this13.menu.checked);
	                } else {
	                  values.push(item);
	                }
	                data = _extends({}, _this13.curItem, {
	                  values
	                });
	                if (keys$1(_this13.menu.childCondition).length) {
	                  data.condition = _this13.menu.childCondition;
	                }
	                if (data.children) {
	                  delete data.children;
	                }
	                if (data.conditions) {
	                  delete data.conditions;
	                }
	                _context5.next = 13;
	                return _this13.handleValidate(values);
	              case 13:
	                validate = _context5.sent;
	                if (validate) {
	                  _context5.next = 16;
	                  break;
	                }
	                return _context5.abrupt('return');
	              case 16:
	                _this13.chip.list.push(data);
	              case 17:
	                _context5.next = 25;
	                break;
	              case 19:
	                _context5.next = 21;
	                return _this13.handleValidate([item]);
	              case 21:
	                _validate = _context5.sent;
	                if (_validate) {
	                  _context5.next = 24;
	                  break;
	                }
	                return _context5.abrupt('return');
	              case 24:
	                _this13.chip.list.push(item);
	              case 25:
	                _this13.menu.checked = {};
	                _this13.menu.active = -1;
	                _this13.menu.id = null;
	                _this13.input.value = '';
	                _this13.menu.childCondition = {};
	                _this13.updateInput();
	                if (_this13.menuInstance) {
	                  _this13.menuInstance.filter = '';
	                }
	                if (needShowPopover) {
	                  _this13.$nextTick(_ => _this13.showMenu(_this13.showPopoverTagChange));
	                  _this13.$refs.input.focus();
	                }
	                _this13.$emit('change', _this13.chip.list);
	                _this13.dispatch('bk-form-item', 'form-change');
	              case 35:
	              case 'end':
	                return _context5.stop();
	            }
	          }
	        }, _callee5);
	      }))();
	    },
	    handleClear: function handleClear(index, item) {
	      const _this14 = this;
	      const name = this.chip.list.splice(index, 1);
	      setTimeout(() => {
	        _this14.popperMenuInstance && _this14.popperMenuInstance.popperInstance && _this14.popperMenuInstance.popperInstance.update();
	        !_this14.input.value.length && _this14.showMenu();
	        _this14.$emit('change', _this14.chip.list);
	        _this14.$emit('chip-del', name);
	        _this14.dispatch('bk-form-item', 'form-change');
	      }, 0);
	    },
	    handleSelectConditon: function handleSelectConditon(item) {
	      this.input.value = item[this.displayKey];
	      this.updateInput(this.input.value);
	      this.handleEnter(this.input.value, item, true);
	      this.$emit('condition-select', item);
	    },
	    handleSelectCheck: function handleSelectCheck(item, index) {
	      const next = !this.menu.checked[item[this.primaryKey]];
	      if (next) {
	        this.menu.checked[item[this.primaryKey]] = item;
	      } else {
	        delete this.menu.checked[item[this.primaryKey]];
	      }
	      this.menuChildInstance.checked = this.menu.checked;
	      this.updateCheckedInputVal();
	      this.handlePopoverCheckUpdate();
	      this.popperMenuInstance.popperInstance.update();
	      this.$emit('child-checked', item, index, next);
	    },
	    handleClearChildSelectChecked: function handleClearChildSelectChecked() {
	      this.menu.checked = {};
	      this.menuChildInstance.checked = this.menu.checked;
	      this.updateCheckedInputVal();
	      this.handlePopoverCheckUpdate();
	      this.popperMenuInstance.popperInstance.update();
	    },
	    handleWrapClick: function handleWrapClick() {
	      if (this.shrink) {
	        this.$refs.input.focus();
	      }
	    },
	    updateCheckedInputVal: function updateCheckedInputVal() {
	      const _this15 = this;
	      if (this.menu.id !== null) {
	        const val = values$1(this.menu.checked).map(set => set[_this15.displayKey])
                    .join(this.splitCode);
	        this.input.value = this.curItem[this.displayKey] + this.explainCode + val;
	        this.updateInput(this.input.value);
	      }
	    },
	    updateInput: function updateInput() {
	      const val = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : '';
	      this.$refs.input.innerText = val;
	    },
	    clearInput: function clearInput() {
	      const text = this.$refs.input.innerText;
	      if (text[text.length - 1] === '\n' || text[0] === '\r') {
	        this.updateInput(text.slice(0, -1));
	        this.clearInput();
	      } else if (text[0] === '\n' || text[0] === '\r') {
	        this.updateInput(text.slice(1));
	        this.clearInput();
	      }
	    },
	    handlePopoverCheckUpdate: function handlePopoverCheckUpdate() {
	      const { distance } = this.popperMenuInstance.props;
	      const height = this.$refs.wrap.clientHeight;
	      if (-height !== distance) {
	        this.popperMenuInstance.popperInstance.update();
	      }
	    },
	    handleClearAll: function handleClearAll(e) {
	      this.menu.active = -1;
	      this.menu.id = null;
	      this.input.value = '';
	      this.menuInstance = null;
	      this.updateInput(this.input.value);
	      this.clearInput();
	      this.values.splice(0, this.values.length);
	      this.$emit('clear', e);
	    },
	    handleClickSearch: function handleClickSearch(e) {
	      this.handleKeyEnter(e, false, false);
	      this.$emit('search', e);
	    },
	    getMenuInstance: function getMenuInstance() {
	      return this.menuInstance;
	    },
	    getChildMenuInstance: function getChildMenuInstance() {
	      return this.menuChildInstance;
	    },
	    getInputInstance: function getInputInstance() {
	      return this.$refs.input;
	    }
	  }
          };

          /* script */
          const __vue_script__$1 = script$1;
          /* template */

          const __vue_render__ = function __vue_render__() {
	  const _vm = this;

	  const _h = _vm.$createElement;

	  const _c = _vm._self._c || _h;

	  return _c('div', _vm._b({
	    staticClass: 'search-select-wrap',
	    class: _vm.extCls,
	    style: {
	      'z-index': _vm.wrapZindex
	    }
	  }, 'div', _vm.$attrs, false), [_c('div', {
	    ref: 'wrap',
	    staticClass: 'bk-search-select',
	    class: {
	      'is-focus': _vm.input.focus
	    },
	    on: {
	      click: _vm.handleWrapClick
	    }
	  }, [_c('div', {
	    staticClass: 'search-prefix'
	  }, [_vm._t('prefix')], 2), _c('div', {
	    staticClass: 'search-input',
	    style: {
	      maxHeight: `${_vm.shrink ? _vm.input.focus ? _vm.maxHeight : _vm.minHeight : _vm.maxHeight}px`
	    }
	  }, [_vm._l(_vm.chip.list, (item, index) => [(_vm.overflow.chipIndex >= 0 ? index < _vm.overflow.chipIndex : index >= 0) ? _c('div', {
	      key: `${index}_pre_key`,
	      staticClass: 'search-input-chip'
	    }, [_c('span', {
	      staticClass: 'chip-name'
	    }, [_vm._v(`\n            ${_vm._s(item[_vm.displayKey] + (item.values && item.values.length ? _vm.explainCode + (item.condition ? item.condition[_vm.displayKey] : '') + item.values.map(v => v[_vm.displayKey]).join(_vm.splitCode) : ''))}\n          `)]), _c('span', {
	      staticClass: 'chip-clear bk-icon icon-close',
	      on: {
	        click: function click($event) {
	          _vm.handleClear(index, item);
	        }
	      }
	    })]) : _vm._e()]), _vm.chip.list.length && _vm.overflow.chipIndex >= 0 ? _c('div', {
	    staticClass: 'search-input-chip overflow-chip',
	    staticStyle: {
	      'padding-right': '8px'
	    }
	  }, [_vm._v(`+${_vm._s(_vm.chip.list.length - _vm.overflow.chipIndex)}`)]) : _vm._e(), _vm.chip.list.length && _vm.overflow.chipIndex >= 0 ? [_vm._l(_vm.chip.list, (item, index) => [index >= _vm.overflow.chipIndex ? _c('div', {
	      key: `${index}_next_key`,
	      staticClass: 'search-input-chip hidden-chip'
	    }, [_c('span', {
	      staticClass: 'chip-name'
	    }, [_vm._v(`\n              ${_vm._s(item[_vm.displayKey] + (item.values && item.values.length ? _vm.explainCode + (item.condition ? item.condition[_vm.displayKey] : '') + item.values.map(v => v[_vm.displayKey]).join(_vm.splitCode) : ''))}\n            `)]), _c('span', {
	      staticClass: 'chip-clear bk-icon icon-close',
	      on: {
	        click: function click($event) {
	          _vm.handleClear(index, item);
	        }
	      }
	    })]) : _vm._e()])] : _vm._e(), _c('div', {
	    staticClass: 'search-input-input'
	  }, [_c('div', {
	    directives: [{
	      name: 'clickoutside',
	      rawName: 'v-clickoutside',
	      value: _vm.handleInputOutSide,
	      expression: 'handleInputOutSide'
	    }],
	    ref: 'input',
	    staticClass: 'div-input',
	    class: {
	      'input-before': !_vm.chip.list.length && !_vm.input.value.length,
	      'input-after': _vm.showItemPlaceholder
	    },
	    attrs: {
	      contenteditable: 'plaintext-only',
	      'data-placeholder': _vm.defaultPlaceholder,
	      'data-tips': _vm.curItem.placeholder || '',
	      spellcheck: 'false'
	    },
	    on: {
	      click: _vm.handleInputClick,
	      focus: _vm.handleInputFocus,
	      cut: _vm.handleInputCut,
	      input: _vm.handleInputChange,
	      keydown: _vm.handleInputKeyup
	    }
	  })])], 2), _c('div', {
	    staticClass: 'search-nextfix'
	  }, [_vm.clearable && (_vm.chip.list.length || _vm.input.value.length) ? _c('i', {
	    staticClass: 'search-clear bk-icon icon-close-circle-shape',
	    on: {
	      click: function click($event) {
	        if ($event.target !== $event.currentTarget) {
	          return null;
	        }

	        return _vm.handleClearAll($event);
	      }
	    }
	  }) : _vm._e(), _vm._t('nextfix', [_c('i', {
	    staticClass: 'bk-icon icon-search search-nextfix-icon',
	    class: {
	      'is-focus': _vm.input.focus
	    },
	    on: {
	      click: function click($event) {
	        if ($event.target !== $event.currentTarget) {
	          return null;
	        }

	        return _vm.handleClickSearch($event);
	      }
	    }
	  })])], 2)]), _vm.validateStr.length ? _c('div', {
	    staticClass: 'bk-select-tips'
	  }, [_vm._t('validate', [_c('i', {
	    staticClass: 'bk-icon icon-exclamation-circle-shape select-tips'
	  }), _vm._v(`${_vm._s(_vm.validateStr || '')}\n    `)])], 2) : _vm._e()]);
          };

          const __vue_staticRenderFns__ = [];
          /* style */

          const __vue_inject_styles__$1 = undefined;
          /* scoped */

          const __vue_scope_id__$1 = undefined;
          /* module identifier */

          const __vue_module_identifier__$1 = undefined;
          /* functional template */

          const __vue_is_functional_template__$1 = false;
          /* style inject */

          /* style inject SSR */

          /* style inject shadow dom */

          const __vue_component__$1 = /* #__PURE__*/normalizeComponent_1({
	  render: __vue_render__,
	  staticRenderFns: __vue_staticRenderFns__
          }, __vue_inject_styles__$1, __vue_script__$1, __vue_scope_id__$1, __vue_is_functional_template__$1, __vue_module_identifier__$1, false, undefined, undefined, undefined);

          function setInstaller(component, afterInstall) {
	  component.install = function (Vue) {
	    const options = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : {};
	    const props = component.props || {};
	    keys$1(options).forEach((key) => {
	      if (props.hasOwnProperty(key)) {
	        if (typeof props[key] === 'function' || props[key] instanceof Array) {
	          props[key] = {
	            type: props[key],
	            default: options[key]
	          };
	        } else {
	          props[key].default = options[key];
	        }
	      }
	    });
	    component.name = options.namespace ? component.name.replace('bk', options.namespace) : component.name;
	    Vue.component(component.name, component);
	    typeof afterInstall === 'function' && afterInstall(Vue, options);
	  };
          }

          setInstaller(__vue_component__$1);

          exports.default = __vue_component__$1;

          Object.defineProperty(exports, '__esModule', { value: true });
        }));
        /***/ }),

      /***/ './node_modules/css-loader/dist/cjs.js??clonedRuleSet-4[0].rules[0].use[1]!./node_modules/bk-magic-vue/lib/ui/iconfont.css':
      /*! *********************************************************************************************************************************!*\
  !*** ./node_modules/css-loader/dist/cjs.js??clonedRuleSet-4[0].rules[0].use[1]!./node_modules/bk-magic-vue/lib/ui/iconfont.css ***!
  \*********************************************************************************************************************************/
      /***/ ((module, __webpack_exports__, __webpack_require__) => {
        'use strict';
        __webpack_require__.r(__webpack_exports__);
        /* harmony export */ __webpack_require__.d(__webpack_exports__, {
          /* harmony export */   default: () => (__WEBPACK_DEFAULT_EXPORT__)
          /* harmony export */ });
        /* harmony import */ const _css_loader_dist_runtime_cssWithMappingToString_js__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! ../../../css-loader/dist/runtime/cssWithMappingToString.js */ './node_modules/css-loader/dist/runtime/cssWithMappingToString.js');
        /* harmony import */ const _css_loader_dist_runtime_cssWithMappingToString_js__WEBPACK_IMPORTED_MODULE_0___default = /* #__PURE__*/__webpack_require__.n(_css_loader_dist_runtime_cssWithMappingToString_js__WEBPACK_IMPORTED_MODULE_0__);
        /* harmony import */ const _css_loader_dist_runtime_api_js__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! ../../../css-loader/dist/runtime/api.js */ './node_modules/css-loader/dist/runtime/api.js');
        /* harmony import */ const _css_loader_dist_runtime_api_js__WEBPACK_IMPORTED_MODULE_1___default = /* #__PURE__*/__webpack_require__.n(_css_loader_dist_runtime_api_js__WEBPACK_IMPORTED_MODULE_1__);
        /* harmony import */ const _css_loader_dist_runtime_getUrl_js__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! ../../../css-loader/dist/runtime/getUrl.js */ './node_modules/css-loader/dist/runtime/getUrl.js');
        /* harmony import */ const _css_loader_dist_runtime_getUrl_js__WEBPACK_IMPORTED_MODULE_2___default = /* #__PURE__*/__webpack_require__.n(_css_loader_dist_runtime_getUrl_js__WEBPACK_IMPORTED_MODULE_2__);
        /* harmony import */ const _fonts_iconcool_svg__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(/*! ./fonts/iconcool.svg */ './node_modules/bk-magic-vue/lib/ui/fonts/iconcool.svg');
        /* harmony import */ const _fonts_iconcool_ttf__WEBPACK_IMPORTED_MODULE_4__ = __webpack_require__(/*! ./fonts/iconcool.ttf */ './node_modules/bk-magic-vue/lib/ui/fonts/iconcool.ttf');
        /* harmony import */ const _fonts_iconcool_woff__WEBPACK_IMPORTED_MODULE_5__ = __webpack_require__(/*! ./fonts/iconcool.woff */ './node_modules/bk-magic-vue/lib/ui/fonts/iconcool.woff');
        /* harmony import */ const _fonts_iconcool_eot__WEBPACK_IMPORTED_MODULE_6__ = __webpack_require__(/*! ./fonts/iconcool.eot */ './node_modules/bk-magic-vue/lib/ui/fonts/iconcool.eot');
        // Imports


        const ___CSS_LOADER_EXPORT___ = _css_loader_dist_runtime_api_js__WEBPACK_IMPORTED_MODULE_1___default()((_css_loader_dist_runtime_cssWithMappingToString_js__WEBPACK_IMPORTED_MODULE_0___default()));
        const ___CSS_LOADER_URL_REPLACEMENT_0___ = _css_loader_dist_runtime_getUrl_js__WEBPACK_IMPORTED_MODULE_2___default()(_fonts_iconcool_svg__WEBPACK_IMPORTED_MODULE_3__.default, { hash: '#iconcool' });
        const ___CSS_LOADER_URL_REPLACEMENT_1___ = _css_loader_dist_runtime_getUrl_js__WEBPACK_IMPORTED_MODULE_2___default()(_fonts_iconcool_ttf__WEBPACK_IMPORTED_MODULE_4__.default);
        const ___CSS_LOADER_URL_REPLACEMENT_2___ = _css_loader_dist_runtime_getUrl_js__WEBPACK_IMPORTED_MODULE_2___default()(_fonts_iconcool_woff__WEBPACK_IMPORTED_MODULE_5__.default);
        const ___CSS_LOADER_URL_REPLACEMENT_3___ = _css_loader_dist_runtime_getUrl_js__WEBPACK_IMPORTED_MODULE_2___default()(_fonts_iconcool_eot__WEBPACK_IMPORTED_MODULE_6__.default, { hash: '?#iefix' });
        // Module
        ___CSS_LOADER_EXPORT___.push([module.id, `@font-face{\n\tfont-family:"bk";\n\tsrc:url(${___CSS_LOADER_URL_REPLACEMENT_0___}) format("svg"),\nurl(${___CSS_LOADER_URL_REPLACEMENT_1___}) format("truetype"),\nurl(${___CSS_LOADER_URL_REPLACEMENT_2___}) format("woff"),\nurl(${___CSS_LOADER_URL_REPLACEMENT_3___}) format("embedded-opentype");\n    font-weight:normal;\n    font-style:normal;\n}\n\n.bk-icon{\n  font-family:'bk' !important;\n  speak:none;\n  font-style:normal;\n  font-weight:normal;\n  -webkit-font-feature-settings:normal;\n          font-feature-settings:normal;\n  font-variant:normal;\n  text-transform:none;\n  line-height:1;\n  text-align:center;\n  -webkit-font-smoothing:antialiased;\n  -moz-osx-font-smoothing:grayscale;\n}\n\n.icon-angle-double-down:before{\n\tcontent:"\\e101";\n}\n\n.icon-angle-double-left:before{\n\tcontent:"\\e102";\n}\n\n.icon-angle-double-right:before{\n\tcontent:"\\e103";\n}\n\n.icon-angle-double-up:before{\n\tcontent:"\\e104";\n}\n\n.icon-angle-left:before{\n\tcontent:"\\e105";\n}\n\n.icon-angle-down:before{\n\tcontent:"\\e106";\n}\n\n.icon-angle-right:before{\n\tcontent:"\\e107";\n}\n\n.icon-angle-up:before{\n\tcontent:"\\e108";\n}\n\n.icon-apps-shape:before{\n\tcontent:"\\e109";\n}\n\n.icon-apps:before{\n\tcontent:"\\e10a";\n}\n\n.icon-area-chart:before{\n\tcontent:"\\e10b";\n}\n\n.icon-arrows-down-circle-shape:before{\n\tcontent:"\\e10c";\n}\n\n.icon-arrows-down-circle:before{\n\tcontent:"\\e10d";\n}\n\n.icon-arrows-down-shape:before{\n\tcontent:"\\e10e";\n}\n\n.icon-arrows-down:before{\n\tcontent:"\\e10f";\n}\n\n.icon-arrows-left-circle-shape:before{\n\tcontent:"\\e110";\n}\n\n.icon-arrows-left-circle:before{\n\tcontent:"\\e111";\n}\n\n.icon-arrows-left-shape:before{\n\tcontent:"\\e112";\n}\n\n.icon-arrows-left:before{\n\tcontent:"\\e113";\n}\n\n.icon-arrows-m-down-shape:before{\n\tcontent:"\\e114";\n}\n\n.icon-arrows-m-left-shape:before{\n\tcontent:"\\e115";\n}\n\n.icon-arrows-m-right-shape:before{\n\tcontent:"\\e116";\n}\n\n.icon-arrows-m-up-shape:before{\n\tcontent:"\\e117";\n}\n\n.icon-arrows-right-circle-shape:before{\n\tcontent:"\\e118";\n}\n\n.icon-arrows-right-circle:before{\n\tcontent:"\\e119";\n}\n\n.icon-arrows-right-shape:before{\n\tcontent:"\\e11a";\n}\n\n.icon-arrows-right:before{\n\tcontent:"\\e11b";\n}\n\n.icon-arrows-up-circle-shape:before{\n\tcontent:"\\e11c";\n}\n\n.icon-arrows-up-circle:before{\n\tcontent:"\\e11d";\n}\n\n.icon-arrows-up-shape:before{\n\tcontent:"\\e11e";\n}\n\n.icon-arrows-up:before{\n\tcontent:"\\e11f";\n}\n\n.icon-back-shape:before{\n\tcontent:"\\e120";\n}\n\n.icon-back:before{\n\tcontent:"\\e121";\n}\n\n.icon-back2:before{\n\tcontent:"\\e122";\n}\n\n.icon-bar-chart:before{\n\tcontent:"\\e123";\n}\n\n.icon-bk:before{\n\tcontent:"\\e124";\n}\n\n.icon-block-shape:before{\n\tcontent:"\\e125";\n}\n\n.icon-calendar-shape:before{\n\tcontent:"\\e126";\n}\n\n.icon-calendar:before{\n\tcontent:"\\e127";\n}\n\n.icon-chain:before{\n\tcontent:"\\e128";\n}\n\n.icon-check-1:before{\n\tcontent:"\\e129";\n}\n\n.icon-check-circle-shape:before{\n\tcontent:"\\e12a";\n}\n\n.icon-check-circle:before{\n\tcontent:"\\e12b";\n}\n\n.icon-circle-2-1:before{\n\tcontent:"\\e12c";\n}\n\n.icon-circle-4-1:before{\n\tcontent:"\\e12d";\n}\n\n.icon-circle-shape:before{\n\tcontent:"\\e12e";\n}\n\n.icon-circle:before{\n\tcontent:"\\e12f";\n}\n\n.icon-clipboard-shape:before{\n\tcontent:"\\e130";\n}\n\n.icon-clipboard:before{\n\tcontent:"\\e131";\n}\n\n.icon-clock-shape:before{\n\tcontent:"\\e132";\n}\n\n.icon-clock:before{\n\tcontent:"\\e133";\n}\n\n.icon-close-circle-shape:before{\n\tcontent:"\\e134";\n}\n\n.icon-close-circle:before{\n\tcontent:"\\e135";\n}\n\n.icon-close:before{\n\tcontent:"\\e136";\n}\n\n.icon-close3-shape:before{\n\tcontent:"\\e137";\n}\n\n.icon-code:before{\n\tcontent:"\\e138";\n}\n\n.icon-cog-shape:before{\n\tcontent:"\\e139";\n}\n\n.icon-cog:before{\n\tcontent:"\\e13a";\n}\n\n.icon-cry-shape:before{\n\tcontent:"\\e13b";\n}\n\n.icon-cry:before{\n\tcontent:"\\e13c";\n}\n\n.icon-dashboard-2-shape:before{\n\tcontent:"\\e13d";\n}\n\n.icon-dashboard-2:before{\n\tcontent:"\\e13e";\n}\n\n.icon-dashboard-shape:before{\n\tcontent:"\\e13f";\n}\n\n.icon-dashboard:before{\n\tcontent:"\\e140";\n}\n\n.icon-data-shape:before{\n\tcontent:"\\e141";\n}\n\n.icon-data:before{\n\tcontent:"\\e142";\n}\n\n.icon-data2-shape:before{\n\tcontent:"\\e143";\n}\n\n.icon-data2:before{\n\tcontent:"\\e144";\n}\n\n.icon-dedent:before{\n\tcontent:"\\e145";\n}\n\n.icon-delete:before{\n\tcontent:"\\e146";\n}\n\n.icon-dialogue-empty-shape:before{\n\tcontent:"\\e147";\n}\n\n.icon-dialogue-empty:before{\n\tcontent:"\\e148";\n}\n\n.icon-dialogue-shape:before{\n\tcontent:"\\e149";\n}\n\n.icon-dialogue:before{\n\tcontent:"\\e14a";\n}\n\n.icon-dispirited-shape:before{\n\tcontent:"\\e14b";\n}\n\n.icon-dispirited:before{\n\tcontent:"\\e14c";\n}\n\n.icon-docker:before{\n\tcontent:"\\e14d";\n}\n\n.icon-down-shape:before{\n\tcontent:"\\e14e";\n}\n\n.icon-download:before{\n\tcontent:"\\e14f";\n}\n\n.icon-edit:before{\n\tcontent:"\\e150";\n}\n\n.icon-edit2:before{\n\tcontent:"\\e151";\n}\n\n.icon-ellipsis:before{\n\tcontent:"\\e152";\n}\n\n.icon-email-shape:before{\n\tcontent:"\\e153";\n}\n\n.icon-email:before{\n\tcontent:"\\e154";\n}\n\n.icon-empty-shape:before{\n\tcontent:"\\e155";\n}\n\n.icon-empty:before{\n\tcontent:"\\e156";\n}\n\n.icon-end:before{\n\tcontent:"\\e157";\n}\n\n.icon-exclamation-circle-shape:before{\n\tcontent:"\\e158";\n}\n\n.icon-exclamation-circle:before{\n\tcontent:"\\e159";\n}\n\n.icon-exclamation-triangle-shape:before{\n\tcontent:"\\e15a";\n}\n\n.icon-exclamation-triangle:before{\n\tcontent:"\\e15b";\n}\n\n.icon-exclamation:before{\n\tcontent:"\\e15c";\n}\n\n.icon-execute:before{\n\tcontent:"\\e15d";\n}\n\n.icon-eye-shape:before{\n\tcontent:"\\e15e";\n}\n\n.icon-eye-slash-shape:before{\n\tcontent:"\\e15f";\n}\n\n.icon-eye-slash:before{\n\tcontent:"\\e160";\n}\n\n.icon-eye:before{\n\tcontent:"\\e161";\n}\n\n.icon-file-plus-shape:before{\n\tcontent:"\\e162";\n}\n\n.icon-file-plus:before{\n\tcontent:"\\e163";\n}\n\n.icon-file-shape:before{\n\tcontent:"\\e164";\n}\n\n.icon-file:before{\n\tcontent:"\\e165";\n}\n\n.icon-folder-open-shape:before{\n\tcontent:"\\e166";\n}\n\n.icon-folder-open:before{\n\tcontent:"\\e167";\n}\n\n.icon-folder-plus-shape:before{\n\tcontent:"\\e168";\n}\n\n.icon-folder-plus:before{\n\tcontent:"\\e169";\n}\n\n.icon-folder-shape:before{\n\tcontent:"\\e16a";\n}\n\n.icon-folder:before{\n\tcontent:"\\e16b";\n}\n\n.icon-full-screen:before{\n\tcontent:"\\e16c";\n}\n\n.icon-heart-shape:before{\n\tcontent:"\\e16d";\n}\n\n.icon-heart:before{\n\tcontent:"\\e16e";\n}\n\n.icon-hide:before{\n\tcontent:"\\e16f";\n}\n\n.icon-home-shape:before{\n\tcontent:"\\e170";\n}\n\n.icon-home:before{\n\tcontent:"\\e171";\n}\n\n.icon-id-shape:before{\n\tcontent:"\\e172";\n}\n\n.icon-id:before{\n\tcontent:"\\e173";\n}\n\n.icon-image-shape:before{\n\tcontent:"\\e174";\n}\n\n.icon-image:before{\n\tcontent:"\\e175";\n}\n\n.icon-indent:before{\n\tcontent:"\\e176";\n}\n\n.icon-info-circle-shape:before{\n\tcontent:"\\e177";\n}\n\n.icon-info-circle:before{\n\tcontent:"\\e178";\n}\n\n.icon-info:before{\n\tcontent:"\\e179";\n}\n\n.icon-key:before{\n\tcontent:"\\e17a";\n}\n\n.icon-left-shape:before{\n\tcontent:"\\e17b";\n}\n\n.icon-line-chart:before{\n\tcontent:"\\e17c";\n}\n\n.icon-list:before{\n\tcontent:"\\e17d";\n}\n\n.icon-lock-shape:before{\n\tcontent:"\\e17e";\n}\n\n.icon-lock:before{\n\tcontent:"\\e17f";\n}\n\n.icon-minus-circle-shape:before{\n\tcontent:"\\e180";\n}\n\n.icon-minus-circle:before{\n\tcontent:"\\e181";\n}\n\n.icon-minus-square-shape:before{\n\tcontent:"\\e182";\n}\n\n.icon-minus-square:before{\n\tcontent:"\\e183";\n}\n\n.icon-minus:before{\n\tcontent:"\\e184";\n}\n\n.icon-mobile-shape:before{\n\tcontent:"\\e185";\n}\n\n.icon-mobile:before{\n\tcontent:"\\e186";\n}\n\n.icon-monitors-cog:before{\n\tcontent:"\\e187";\n}\n\n.icon-monitors:before{\n\tcontent:"\\e188";\n}\n\n.icon-more:before{\n\tcontent:"\\e189";\n}\n\n.icon-move:before{\n\tcontent:"\\e18a";\n}\n\n.icon-next-shape:before{\n\tcontent:"\\e18b";\n}\n\n.icon-next:before{\n\tcontent:"\\e18c";\n}\n\n.icon-order-shape:before{\n\tcontent:"\\e18d";\n}\n\n.icon-order:before{\n\tcontent:"\\e18e";\n}\n\n.icon-panel-permission:before{\n\tcontent:"\\e18f";\n}\n\n.icon-panel-shape:before{\n\tcontent:"\\e190";\n}\n\n.icon-panel:before{\n\tcontent:"\\e191";\n}\n\n.icon-panels:before{\n\tcontent:"\\e192";\n}\n\n.icon-password-shape:before{\n\tcontent:"\\e193";\n}\n\n.icon-password:before{\n\tcontent:"\\e194";\n}\n\n.icon-pause:before{\n\tcontent:"\\e195";\n}\n\n.icon-pc-shape:before{\n\tcontent:"\\e196";\n}\n\n.icon-pc:before{\n\tcontent:"\\e197";\n}\n\n.icon-pie-chart-shape:before{\n\tcontent:"\\e198";\n}\n\n.icon-pie-chart:before{\n\tcontent:"\\e199";\n}\n\n.icon-pipeline-shape:before{\n\tcontent:"\\e19a";\n}\n\n.icon-pipeline:before{\n\tcontent:"\\e19b";\n}\n\n.icon-play-circle-shape:before{\n\tcontent:"\\e19c";\n}\n\n.icon-play-shape:before{\n\tcontent:"\\e19d";\n}\n\n.icon-play:before{\n\tcontent:"\\e19e";\n}\n\n.icon-play2:before{\n\tcontent:"\\e19f";\n}\n\n.icon-play3:before{\n\tcontent:"\\e1a0";\n}\n\n.icon-plus-circle-shape:before{\n\tcontent:"\\e1a1";\n}\n\n.icon-plus-circle:before{\n\tcontent:"\\e1a2";\n}\n\n.icon-plus-square-shape:before{\n\tcontent:"\\e1a3";\n}\n\n.icon-plus-square:before{\n\tcontent:"\\e1a4";\n}\n\n.icon-plus:before{\n\tcontent:"\\e1a5";\n}\n\n.icon-project:before{\n\tcontent:"\\e1a6";\n}\n\n.icon-qq-shape:before{\n\tcontent:"\\e1a7";\n}\n\n.icon-qq:before{\n\tcontent:"\\e1a8";\n}\n\n.icon-question-circle-shape:before{\n\tcontent:"\\e1a9";\n}\n\n.icon-question-circle:before{\n\tcontent:"\\e1aa";\n}\n\n.icon-question:before{\n\tcontent:"\\e1ab";\n}\n\n.icon-refresh:before{\n\tcontent:"\\e1ac";\n}\n\n.icon-right-shape:before{\n\tcontent:"\\e1ad";\n}\n\n.icon-rtx:before{\n\tcontent:"\\e1ae";\n}\n\n.icon-save-shape:before{\n\tcontent:"\\e1af";\n}\n\n.icon-save:before{\n\tcontent:"\\e1b0";\n}\n\n.icon-script-file:before{\n\tcontent:"\\e1b1";\n}\n\n.icon-script-files:before{\n\tcontent:"\\e1b2";\n}\n\n.icon-search:before{\n\tcontent:"\\e1b3";\n}\n\n.icon-sina-shape:before{\n\tcontent:"\\e1b4";\n}\n\n.icon-sina:before{\n\tcontent:"\\e1b5";\n}\n\n.icon-sitemap-shape:before{\n\tcontent:"\\e1b6";\n}\n\n.icon-sitemap:before{\n\tcontent:"\\e1b7";\n}\n\n.icon-smile-shape:before{\n\tcontent:"\\e1b8";\n}\n\n.icon-smile:before{\n\tcontent:"\\e1b9";\n}\n\n.icon-sort:before{\n\tcontent:"\\e1ba";\n}\n\n.icon-star-shape:before{\n\tcontent:"\\e1bb";\n}\n\n.icon-star:before{\n\tcontent:"\\e1bc";\n}\n\n.icon-stop-shape:before{\n\tcontent:"\\e1bd";\n}\n\n.icon-stop:before{\n\tcontent:"\\e1be";\n}\n\n.icon-tree-application-shape:before{\n\tcontent:"\\e1bf";\n}\n\n.icon-tree-application:before{\n\tcontent:"\\e1c0";\n}\n\n.icon-tree-group-shape:before{\n\tcontent:"\\e1c1";\n}\n\n.icon-tree-group:before{\n\tcontent:"\\e1c2";\n}\n\n.icon-tree-module-shape:before{\n\tcontent:"\\e1c3";\n}\n\n.icon-tree-module:before{\n\tcontent:"\\e1c4";\n}\n\n.icon-tree-process-shape:before{\n\tcontent:"\\e1c5";\n}\n\n.icon-tree-process:before{\n\tcontent:"\\e1c6";\n}\n\n.icon-un-full-screen:before{\n\tcontent:"\\e1c8";\n}\n\n.icon-unlock-shape:before{\n\tcontent:"\\e1c7";\n}\n\n.icon-unlock:before{\n\tcontent:"\\e1c9";\n}\n\n.icon-up-shape:before{\n\tcontent:"\\e1ca";\n}\n\n.icon-upload:before{\n\tcontent:"\\e1cb";\n}\n\n.icon-user-shape:before{\n\tcontent:"\\e1cc";\n}\n\n.icon-user:before{\n\tcontent:"\\e1cd";\n}\n\n.icon-weixin-shape:before{\n\tcontent:"\\e1ce";\n}\n\n.icon-weixin:before{\n\tcontent:"\\e1cf";\n}\n\n.icon-work-manage:before{\n\tcontent:"\\e1d0";\n}\n\n.icon-funnel:before{\n\tcontent:"\\e1d1";\n}\n\n.icon-user-group:before{\n\tcontent:"\\e1d2";\n}\n\n.icon-user-3:before{\n\tcontent:"\\e1d3";\n}\n\n.icon-copy:before{\n\tcontent:"\\e1d4";\n}\n\n.icon-batch-edit-line:before{\n\tcontent:"\\e1d6";\n}\n\n.icon-refresh-line:before{\n\tcontent:"\\e1d5";\n}\n\n.icon-close-line:before{\n\tcontent:"\\e1d7";\n}\n\n.icon-1_up:before{\n\tcontent:"\\e1d8";\n}\n\n.icon-arrows-right--line:before{\n\tcontent:"\\e1db";\n}\n\n.icon-arrows-left-line:before{\n\tcontent:"\\e1d9";\n}\n\n.icon-arrows-down-line:before{\n\tcontent:"\\e1dc";\n}\n\n.icon-arrows-up-line:before{\n\tcontent:"\\e1da";\n}\n\n.icon-angle-double-right-line:before{\n\tcontent:"\\e1e1";\n}\n\n.icon-angle-double-down-line:before{\n\tcontent:"\\e1de";\n}\n\n.icon-angle-double-up-line:before{\n\tcontent:"\\e1df";\n}\n\n.icon-angle-double-left-line:before{\n\tcontent:"\\e1dd";\n}\n\n.icon-angle-left-line:before{\n\tcontent:"\\e1e0";\n}\n\n.icon-angle-right-line:before{\n\tcontent:"\\e1e2";\n}\n\n.icon-angle-up-line:before{\n\tcontent:"\\e1e4";\n}\n\n.icon-angle-down-line:before{\n\tcontent:"\\e1e3";\n}\n\n.icon-check-line:before{\n\tcontent:"\\e1ed";\n}\n\n.icon-close-line-2:before{\n\tcontent:"\\e1ec";\n}\n\n.icon-edit-line:before{\n\tcontent:"\\e1ee";\n}\n\n.icon-list-line:before{\n\tcontent:"\\e1eb";\n}\n\n.icon-plus-line:before{\n\tcontent:"\\e1ef";\n}\n\n.icon-angle-up-fill:before{\n\tcontent:"\\e1f0";\n}\n\n.icon-angle-down-fill:before{\n\tcontent:"\\e1f1";\n}\n\n.icon-grag-fill:before{\n\tcontent:"\\e1f2";\n}\n\n.icon-template-fill-49:before{\n\tcontent:"\\e1f3";\n}\n\n.icon-folder-fill:before{\n\tcontent:"\\e1f4";\n}\n\n.icon-expand-line:before{\n\tcontent:"\\e1f5";\n}\n\n.icon-shrink-line:before{\n\tcontent:"\\e1f6";\n}\n\n.icon-minus-line:before{\n\tcontent:"\\e1f7";\n}\n\n.icon-compressed-file:before{\n\tcontent:"\\e1f8";\n}\n\n.icon-upload-cloud:before{\n\tcontent:"\\e1fa";\n}\n\n.icon-text-file:before{\n\tcontent:"\\e1f9";\n}\n\n.icon-filliscreen-line:before{\n\tcontent:"\\e1fe";\n}\n\n.icon-left-turn-line:before{\n\tcontent:"\\e1fb";\n}\n\n.icon-right-turn-line:before{\n\tcontent:"\\e1fc";\n}\n\n.icon-enlarge-line:before{\n\tcontent:"\\e1fd";\n}\n\n.icon-narrow-line:before{\n\tcontent:"\\e1ff";\n}\n\n.icon-unfull-screen:before{\n\tcontent:"\\e200";\n}\n\n.icon-image:before{\n\tcontent:"\\e203";\n}\n\n.icon-image-fail:before{\n\tcontent:"\\e204";\n}\n\n.icon-normalized:before{\n\tcontent:"\\e205";\n}\n\n.icon-chinese:before{\n\tcontent:"\\e206";\n}\n\n.icon-english:before{\n\tcontent:"\\e207";\n}\n\n.icon-japanese:before{\n\tcontent:"\\e208";\n}\n`, '', { version: 3, sources: ['webpack://./node_modules/bk-magic-vue/lib/ui/iconfont.css'], names: [], mappings: 'AAAA;CACC,gBAAgB;CAChB;;;mEAG2D;IACxD,kBAAkB;IAClB,iBAAiB;AACrB;;AAEA;EACE,2BAA2B;EAC3B,UAAU;EACV,iBAAiB;EACjB,kBAAkB;EAClB,oCAAoC;UAC5B,4BAA4B;EACpC,mBAAmB;EACnB,mBAAmB;EACnB,aAAa;EACb,iBAAiB;EACjB,kCAAkC;EAClC,iCAAiC;AACnC;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB;;AAEA;CACC,eAAe;AAChB', sourcesContent: ['@font-face{\n\tfont-family:"bk";\n\tsrc:url("fonts/iconcool.svg#iconcool") format("svg"),\nurl("fonts/iconcool.ttf") format("truetype"),\nurl("fonts/iconcool.woff") format("woff"),\nurl("fonts/iconcool.eot?#iefix") format("embedded-opentype");\n    font-weight:normal;\n    font-style:normal;\n}\n\n.bk-icon{\n  font-family:\'bk\' !important;\n  speak:none;\n  font-style:normal;\n  font-weight:normal;\n  -webkit-font-feature-settings:normal;\n          font-feature-settings:normal;\n  font-variant:normal;\n  text-transform:none;\n  line-height:1;\n  text-align:center;\n  -webkit-font-smoothing:antialiased;\n  -moz-osx-font-smoothing:grayscale;\n}\n\n.icon-angle-double-down:before{\n\tcontent:"\\e101";\n}\n\n.icon-angle-double-left:before{\n\tcontent:"\\e102";\n}\n\n.icon-angle-double-right:before{\n\tcontent:"\\e103";\n}\n\n.icon-angle-double-up:before{\n\tcontent:"\\e104";\n}\n\n.icon-angle-left:before{\n\tcontent:"\\e105";\n}\n\n.icon-angle-down:before{\n\tcontent:"\\e106";\n}\n\n.icon-angle-right:before{\n\tcontent:"\\e107";\n}\n\n.icon-angle-up:before{\n\tcontent:"\\e108";\n}\n\n.icon-apps-shape:before{\n\tcontent:"\\e109";\n}\n\n.icon-apps:before{\n\tcontent:"\\e10a";\n}\n\n.icon-area-chart:before{\n\tcontent:"\\e10b";\n}\n\n.icon-arrows-down-circle-shape:before{\n\tcontent:"\\e10c";\n}\n\n.icon-arrows-down-circle:before{\n\tcontent:"\\e10d";\n}\n\n.icon-arrows-down-shape:before{\n\tcontent:"\\e10e";\n}\n\n.icon-arrows-down:before{\n\tcontent:"\\e10f";\n}\n\n.icon-arrows-left-circle-shape:before{\n\tcontent:"\\e110";\n}\n\n.icon-arrows-left-circle:before{\n\tcontent:"\\e111";\n}\n\n.icon-arrows-left-shape:before{\n\tcontent:"\\e112";\n}\n\n.icon-arrows-left:before{\n\tcontent:"\\e113";\n}\n\n.icon-arrows-m-down-shape:before{\n\tcontent:"\\e114";\n}\n\n.icon-arrows-m-left-shape:before{\n\tcontent:"\\e115";\n}\n\n.icon-arrows-m-right-shape:before{\n\tcontent:"\\e116";\n}\n\n.icon-arrows-m-up-shape:before{\n\tcontent:"\\e117";\n}\n\n.icon-arrows-right-circle-shape:before{\n\tcontent:"\\e118";\n}\n\n.icon-arrows-right-circle:before{\n\tcontent:"\\e119";\n}\n\n.icon-arrows-right-shape:before{\n\tcontent:"\\e11a";\n}\n\n.icon-arrows-right:before{\n\tcontent:"\\e11b";\n}\n\n.icon-arrows-up-circle-shape:before{\n\tcontent:"\\e11c";\n}\n\n.icon-arrows-up-circle:before{\n\tcontent:"\\e11d";\n}\n\n.icon-arrows-up-shape:before{\n\tcontent:"\\e11e";\n}\n\n.icon-arrows-up:before{\n\tcontent:"\\e11f";\n}\n\n.icon-back-shape:before{\n\tcontent:"\\e120";\n}\n\n.icon-back:before{\n\tcontent:"\\e121";\n}\n\n.icon-back2:before{\n\tcontent:"\\e122";\n}\n\n.icon-bar-chart:before{\n\tcontent:"\\e123";\n}\n\n.icon-bk:before{\n\tcontent:"\\e124";\n}\n\n.icon-block-shape:before{\n\tcontent:"\\e125";\n}\n\n.icon-calendar-shape:before{\n\tcontent:"\\e126";\n}\n\n.icon-calendar:before{\n\tcontent:"\\e127";\n}\n\n.icon-chain:before{\n\tcontent:"\\e128";\n}\n\n.icon-check-1:before{\n\tcontent:"\\e129";\n}\n\n.icon-check-circle-shape:before{\n\tcontent:"\\e12a";\n}\n\n.icon-check-circle:before{\n\tcontent:"\\e12b";\n}\n\n.icon-circle-2-1:before{\n\tcontent:"\\e12c";\n}\n\n.icon-circle-4-1:before{\n\tcontent:"\\e12d";\n}\n\n.icon-circle-shape:before{\n\tcontent:"\\e12e";\n}\n\n.icon-circle:before{\n\tcontent:"\\e12f";\n}\n\n.icon-clipboard-shape:before{\n\tcontent:"\\e130";\n}\n\n.icon-clipboard:before{\n\tcontent:"\\e131";\n}\n\n.icon-clock-shape:before{\n\tcontent:"\\e132";\n}\n\n.icon-clock:before{\n\tcontent:"\\e133";\n}\n\n.icon-close-circle-shape:before{\n\tcontent:"\\e134";\n}\n\n.icon-close-circle:before{\n\tcontent:"\\e135";\n}\n\n.icon-close:before{\n\tcontent:"\\e136";\n}\n\n.icon-close3-shape:before{\n\tcontent:"\\e137";\n}\n\n.icon-code:before{\n\tcontent:"\\e138";\n}\n\n.icon-cog-shape:before{\n\tcontent:"\\e139";\n}\n\n.icon-cog:before{\n\tcontent:"\\e13a";\n}\n\n.icon-cry-shape:before{\n\tcontent:"\\e13b";\n}\n\n.icon-cry:before{\n\tcontent:"\\e13c";\n}\n\n.icon-dashboard-2-shape:before{\n\tcontent:"\\e13d";\n}\n\n.icon-dashboard-2:before{\n\tcontent:"\\e13e";\n}\n\n.icon-dashboard-shape:before{\n\tcontent:"\\e13f";\n}\n\n.icon-dashboard:before{\n\tcontent:"\\e140";\n}\n\n.icon-data-shape:before{\n\tcontent:"\\e141";\n}\n\n.icon-data:before{\n\tcontent:"\\e142";\n}\n\n.icon-data2-shape:before{\n\tcontent:"\\e143";\n}\n\n.icon-data2:before{\n\tcontent:"\\e144";\n}\n\n.icon-dedent:before{\n\tcontent:"\\e145";\n}\n\n.icon-delete:before{\n\tcontent:"\\e146";\n}\n\n.icon-dialogue-empty-shape:before{\n\tcontent:"\\e147";\n}\n\n.icon-dialogue-empty:before{\n\tcontent:"\\e148";\n}\n\n.icon-dialogue-shape:before{\n\tcontent:"\\e149";\n}\n\n.icon-dialogue:before{\n\tcontent:"\\e14a";\n}\n\n.icon-dispirited-shape:before{\n\tcontent:"\\e14b";\n}\n\n.icon-dispirited:before{\n\tcontent:"\\e14c";\n}\n\n.icon-docker:before{\n\tcontent:"\\e14d";\n}\n\n.icon-down-shape:before{\n\tcontent:"\\e14e";\n}\n\n.icon-download:before{\n\tcontent:"\\e14f";\n}\n\n.icon-edit:before{\n\tcontent:"\\e150";\n}\n\n.icon-edit2:before{\n\tcontent:"\\e151";\n}\n\n.icon-ellipsis:before{\n\tcontent:"\\e152";\n}\n\n.icon-email-shape:before{\n\tcontent:"\\e153";\n}\n\n.icon-email:before{\n\tcontent:"\\e154";\n}\n\n.icon-empty-shape:before{\n\tcontent:"\\e155";\n}\n\n.icon-empty:before{\n\tcontent:"\\e156";\n}\n\n.icon-end:before{\n\tcontent:"\\e157";\n}\n\n.icon-exclamation-circle-shape:before{\n\tcontent:"\\e158";\n}\n\n.icon-exclamation-circle:before{\n\tcontent:"\\e159";\n}\n\n.icon-exclamation-triangle-shape:before{\n\tcontent:"\\e15a";\n}\n\n.icon-exclamation-triangle:before{\n\tcontent:"\\e15b";\n}\n\n.icon-exclamation:before{\n\tcontent:"\\e15c";\n}\n\n.icon-execute:before{\n\tcontent:"\\e15d";\n}\n\n.icon-eye-shape:before{\n\tcontent:"\\e15e";\n}\n\n.icon-eye-slash-shape:before{\n\tcontent:"\\e15f";\n}\n\n.icon-eye-slash:before{\n\tcontent:"\\e160";\n}\n\n.icon-eye:before{\n\tcontent:"\\e161";\n}\n\n.icon-file-plus-shape:before{\n\tcontent:"\\e162";\n}\n\n.icon-file-plus:before{\n\tcontent:"\\e163";\n}\n\n.icon-file-shape:before{\n\tcontent:"\\e164";\n}\n\n.icon-file:before{\n\tcontent:"\\e165";\n}\n\n.icon-folder-open-shape:before{\n\tcontent:"\\e166";\n}\n\n.icon-folder-open:before{\n\tcontent:"\\e167";\n}\n\n.icon-folder-plus-shape:before{\n\tcontent:"\\e168";\n}\n\n.icon-folder-plus:before{\n\tcontent:"\\e169";\n}\n\n.icon-folder-shape:before{\n\tcontent:"\\e16a";\n}\n\n.icon-folder:before{\n\tcontent:"\\e16b";\n}\n\n.icon-full-screen:before{\n\tcontent:"\\e16c";\n}\n\n.icon-heart-shape:before{\n\tcontent:"\\e16d";\n}\n\n.icon-heart:before{\n\tcontent:"\\e16e";\n}\n\n.icon-hide:before{\n\tcontent:"\\e16f";\n}\n\n.icon-home-shape:before{\n\tcontent:"\\e170";\n}\n\n.icon-home:before{\n\tcontent:"\\e171";\n}\n\n.icon-id-shape:before{\n\tcontent:"\\e172";\n}\n\n.icon-id:before{\n\tcontent:"\\e173";\n}\n\n.icon-image-shape:before{\n\tcontent:"\\e174";\n}\n\n.icon-image:before{\n\tcontent:"\\e175";\n}\n\n.icon-indent:before{\n\tcontent:"\\e176";\n}\n\n.icon-info-circle-shape:before{\n\tcontent:"\\e177";\n}\n\n.icon-info-circle:before{\n\tcontent:"\\e178";\n}\n\n.icon-info:before{\n\tcontent:"\\e179";\n}\n\n.icon-key:before{\n\tcontent:"\\e17a";\n}\n\n.icon-left-shape:before{\n\tcontent:"\\e17b";\n}\n\n.icon-line-chart:before{\n\tcontent:"\\e17c";\n}\n\n.icon-list:before{\n\tcontent:"\\e17d";\n}\n\n.icon-lock-shape:before{\n\tcontent:"\\e17e";\n}\n\n.icon-lock:before{\n\tcontent:"\\e17f";\n}\n\n.icon-minus-circle-shape:before{\n\tcontent:"\\e180";\n}\n\n.icon-minus-circle:before{\n\tcontent:"\\e181";\n}\n\n.icon-minus-square-shape:before{\n\tcontent:"\\e182";\n}\n\n.icon-minus-square:before{\n\tcontent:"\\e183";\n}\n\n.icon-minus:before{\n\tcontent:"\\e184";\n}\n\n.icon-mobile-shape:before{\n\tcontent:"\\e185";\n}\n\n.icon-mobile:before{\n\tcontent:"\\e186";\n}\n\n.icon-monitors-cog:before{\n\tcontent:"\\e187";\n}\n\n.icon-monitors:before{\n\tcontent:"\\e188";\n}\n\n.icon-more:before{\n\tcontent:"\\e189";\n}\n\n.icon-move:before{\n\tcontent:"\\e18a";\n}\n\n.icon-next-shape:before{\n\tcontent:"\\e18b";\n}\n\n.icon-next:before{\n\tcontent:"\\e18c";\n}\n\n.icon-order-shape:before{\n\tcontent:"\\e18d";\n}\n\n.icon-order:before{\n\tcontent:"\\e18e";\n}\n\n.icon-panel-permission:before{\n\tcontent:"\\e18f";\n}\n\n.icon-panel-shape:before{\n\tcontent:"\\e190";\n}\n\n.icon-panel:before{\n\tcontent:"\\e191";\n}\n\n.icon-panels:before{\n\tcontent:"\\e192";\n}\n\n.icon-password-shape:before{\n\tcontent:"\\e193";\n}\n\n.icon-password:before{\n\tcontent:"\\e194";\n}\n\n.icon-pause:before{\n\tcontent:"\\e195";\n}\n\n.icon-pc-shape:before{\n\tcontent:"\\e196";\n}\n\n.icon-pc:before{\n\tcontent:"\\e197";\n}\n\n.icon-pie-chart-shape:before{\n\tcontent:"\\e198";\n}\n\n.icon-pie-chart:before{\n\tcontent:"\\e199";\n}\n\n.icon-pipeline-shape:before{\n\tcontent:"\\e19a";\n}\n\n.icon-pipeline:before{\n\tcontent:"\\e19b";\n}\n\n.icon-play-circle-shape:before{\n\tcontent:"\\e19c";\n}\n\n.icon-play-shape:before{\n\tcontent:"\\e19d";\n}\n\n.icon-play:before{\n\tcontent:"\\e19e";\n}\n\n.icon-play2:before{\n\tcontent:"\\e19f";\n}\n\n.icon-play3:before{\n\tcontent:"\\e1a0";\n}\n\n.icon-plus-circle-shape:before{\n\tcontent:"\\e1a1";\n}\n\n.icon-plus-circle:before{\n\tcontent:"\\e1a2";\n}\n\n.icon-plus-square-shape:before{\n\tcontent:"\\e1a3";\n}\n\n.icon-plus-square:before{\n\tcontent:"\\e1a4";\n}\n\n.icon-plus:before{\n\tcontent:"\\e1a5";\n}\n\n.icon-project:before{\n\tcontent:"\\e1a6";\n}\n\n.icon-qq-shape:before{\n\tcontent:"\\e1a7";\n}\n\n.icon-qq:before{\n\tcontent:"\\e1a8";\n}\n\n.icon-question-circle-shape:before{\n\tcontent:"\\e1a9";\n}\n\n.icon-question-circle:before{\n\tcontent:"\\e1aa";\n}\n\n.icon-question:before{\n\tcontent:"\\e1ab";\n}\n\n.icon-refresh:before{\n\tcontent:"\\e1ac";\n}\n\n.icon-right-shape:before{\n\tcontent:"\\e1ad";\n}\n\n.icon-rtx:before{\n\tcontent:"\\e1ae";\n}\n\n.icon-save-shape:before{\n\tcontent:"\\e1af";\n}\n\n.icon-save:before{\n\tcontent:"\\e1b0";\n}\n\n.icon-script-file:before{\n\tcontent:"\\e1b1";\n}\n\n.icon-script-files:before{\n\tcontent:"\\e1b2";\n}\n\n.icon-search:before{\n\tcontent:"\\e1b3";\n}\n\n.icon-sina-shape:before{\n\tcontent:"\\e1b4";\n}\n\n.icon-sina:before{\n\tcontent:"\\e1b5";\n}\n\n.icon-sitemap-shape:before{\n\tcontent:"\\e1b6";\n}\n\n.icon-sitemap:before{\n\tcontent:"\\e1b7";\n}\n\n.icon-smile-shape:before{\n\tcontent:"\\e1b8";\n}\n\n.icon-smile:before{\n\tcontent:"\\e1b9";\n}\n\n.icon-sort:before{\n\tcontent:"\\e1ba";\n}\n\n.icon-star-shape:before{\n\tcontent:"\\e1bb";\n}\n\n.icon-star:before{\n\tcontent:"\\e1bc";\n}\n\n.icon-stop-shape:before{\n\tcontent:"\\e1bd";\n}\n\n.icon-stop:before{\n\tcontent:"\\e1be";\n}\n\n.icon-tree-application-shape:before{\n\tcontent:"\\e1bf";\n}\n\n.icon-tree-application:before{\n\tcontent:"\\e1c0";\n}\n\n.icon-tree-group-shape:before{\n\tcontent:"\\e1c1";\n}\n\n.icon-tree-group:before{\n\tcontent:"\\e1c2";\n}\n\n.icon-tree-module-shape:before{\n\tcontent:"\\e1c3";\n}\n\n.icon-tree-module:before{\n\tcontent:"\\e1c4";\n}\n\n.icon-tree-process-shape:before{\n\tcontent:"\\e1c5";\n}\n\n.icon-tree-process:before{\n\tcontent:"\\e1c6";\n}\n\n.icon-un-full-screen:before{\n\tcontent:"\\e1c8";\n}\n\n.icon-unlock-shape:before{\n\tcontent:"\\e1c7";\n}\n\n.icon-unlock:before{\n\tcontent:"\\e1c9";\n}\n\n.icon-up-shape:before{\n\tcontent:"\\e1ca";\n}\n\n.icon-upload:before{\n\tcontent:"\\e1cb";\n}\n\n.icon-user-shape:before{\n\tcontent:"\\e1cc";\n}\n\n.icon-user:before{\n\tcontent:"\\e1cd";\n}\n\n.icon-weixin-shape:before{\n\tcontent:"\\e1ce";\n}\n\n.icon-weixin:before{\n\tcontent:"\\e1cf";\n}\n\n.icon-work-manage:before{\n\tcontent:"\\e1d0";\n}\n\n.icon-funnel:before{\n\tcontent:"\\e1d1";\n}\n\n.icon-user-group:before{\n\tcontent:"\\e1d2";\n}\n\n.icon-user-3:before{\n\tcontent:"\\e1d3";\n}\n\n.icon-copy:before{\n\tcontent:"\\e1d4";\n}\n\n.icon-batch-edit-line:before{\n\tcontent:"\\e1d6";\n}\n\n.icon-refresh-line:before{\n\tcontent:"\\e1d5";\n}\n\n.icon-close-line:before{\n\tcontent:"\\e1d7";\n}\n\n.icon-1_up:before{\n\tcontent:"\\e1d8";\n}\n\n.icon-arrows-right--line:before{\n\tcontent:"\\e1db";\n}\n\n.icon-arrows-left-line:before{\n\tcontent:"\\e1d9";\n}\n\n.icon-arrows-down-line:before{\n\tcontent:"\\e1dc";\n}\n\n.icon-arrows-up-line:before{\n\tcontent:"\\e1da";\n}\n\n.icon-angle-double-right-line:before{\n\tcontent:"\\e1e1";\n}\n\n.icon-angle-double-down-line:before{\n\tcontent:"\\e1de";\n}\n\n.icon-angle-double-up-line:before{\n\tcontent:"\\e1df";\n}\n\n.icon-angle-double-left-line:before{\n\tcontent:"\\e1dd";\n}\n\n.icon-angle-left-line:before{\n\tcontent:"\\e1e0";\n}\n\n.icon-angle-right-line:before{\n\tcontent:"\\e1e2";\n}\n\n.icon-angle-up-line:before{\n\tcontent:"\\e1e4";\n}\n\n.icon-angle-down-line:before{\n\tcontent:"\\e1e3";\n}\n\n.icon-check-line:before{\n\tcontent:"\\e1ed";\n}\n\n.icon-close-line-2:before{\n\tcontent:"\\e1ec";\n}\n\n.icon-edit-line:before{\n\tcontent:"\\e1ee";\n}\n\n.icon-list-line:before{\n\tcontent:"\\e1eb";\n}\n\n.icon-plus-line:before{\n\tcontent:"\\e1ef";\n}\n\n.icon-angle-up-fill:before{\n\tcontent:"\\e1f0";\n}\n\n.icon-angle-down-fill:before{\n\tcontent:"\\e1f1";\n}\n\n.icon-grag-fill:before{\n\tcontent:"\\e1f2";\n}\n\n.icon-template-fill-49:before{\n\tcontent:"\\e1f3";\n}\n\n.icon-folder-fill:before{\n\tcontent:"\\e1f4";\n}\n\n.icon-expand-line:before{\n\tcontent:"\\e1f5";\n}\n\n.icon-shrink-line:before{\n\tcontent:"\\e1f6";\n}\n\n.icon-minus-line:before{\n\tcontent:"\\e1f7";\n}\n\n.icon-compressed-file:before{\n\tcontent:"\\e1f8";\n}\n\n.icon-upload-cloud:before{\n\tcontent:"\\e1fa";\n}\n\n.icon-text-file:before{\n\tcontent:"\\e1f9";\n}\n\n.icon-filliscreen-line:before{\n\tcontent:"\\e1fe";\n}\n\n.icon-left-turn-line:before{\n\tcontent:"\\e1fb";\n}\n\n.icon-right-turn-line:before{\n\tcontent:"\\e1fc";\n}\n\n.icon-enlarge-line:before{\n\tcontent:"\\e1fd";\n}\n\n.icon-narrow-line:before{\n\tcontent:"\\e1ff";\n}\n\n.icon-unfull-screen:before{\n\tcontent:"\\e200";\n}\n\n.icon-image:before{\n\tcontent:"\\e203";\n}\n\n.icon-image-fail:before{\n\tcontent:"\\e204";\n}\n\n.icon-normalized:before{\n\tcontent:"\\e205";\n}\n\n.icon-chinese:before{\n\tcontent:"\\e206";\n}\n\n.icon-english:before{\n\tcontent:"\\e207";\n}\n\n.icon-japanese:before{\n\tcontent:"\\e208";\n}\n'], sourceRoot: '' }]);
        // Exports
        /* harmony default export */ const __WEBPACK_DEFAULT_EXPORT__ = (___CSS_LOADER_EXPORT___);
        /***/ }),

      /***/ './node_modules/css-loader/dist/cjs.js??clonedRuleSet-4[0].rules[0].use[1]!./node_modules/bk-magic-vue/lib/ui/popover.css':
      /*! ********************************************************************************************************************************!*\
  !*** ./node_modules/css-loader/dist/cjs.js??clonedRuleSet-4[0].rules[0].use[1]!./node_modules/bk-magic-vue/lib/ui/popover.css ***!
  \********************************************************************************************************************************/
      /***/ ((module, __webpack_exports__, __webpack_require__) => {
        'use strict';
        __webpack_require__.r(__webpack_exports__);
        /* harmony export */ __webpack_require__.d(__webpack_exports__, {
          /* harmony export */   default: () => (__WEBPACK_DEFAULT_EXPORT__)
          /* harmony export */ });
        /* harmony import */ const _css_loader_dist_runtime_cssWithMappingToString_js__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! ../../../css-loader/dist/runtime/cssWithMappingToString.js */ './node_modules/css-loader/dist/runtime/cssWithMappingToString.js');
        /* harmony import */ const _css_loader_dist_runtime_cssWithMappingToString_js__WEBPACK_IMPORTED_MODULE_0___default = /* #__PURE__*/__webpack_require__.n(_css_loader_dist_runtime_cssWithMappingToString_js__WEBPACK_IMPORTED_MODULE_0__);
        /* harmony import */ const _css_loader_dist_runtime_api_js__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! ../../../css-loader/dist/runtime/api.js */ './node_modules/css-loader/dist/runtime/api.js');
        /* harmony import */ const _css_loader_dist_runtime_api_js__WEBPACK_IMPORTED_MODULE_1___default = /* #__PURE__*/__webpack_require__.n(_css_loader_dist_runtime_api_js__WEBPACK_IMPORTED_MODULE_1__);
        // Imports


        const ___CSS_LOADER_EXPORT___ = _css_loader_dist_runtime_api_js__WEBPACK_IMPORTED_MODULE_1___default()((_css_loader_dist_runtime_cssWithMappingToString_js__WEBPACK_IMPORTED_MODULE_0___default()));
        // Module
        ___CSS_LOADER_EXPORT___.push([module.id, '.bk-tooltip{\n    display:inline-block;\n}\n\n.bk-tooltip-ref{\n    display:inline-block;\n    position:relative;\n    outline:0;\n}\n\n.tippy-iOS{\n    cursor:pointer !important;\n    -webkit-tap-highlight-color:transparent\n}\n\n.tippy-popper{\n    -webkit-transition-timing-function:cubic-bezier(.165, .84, .44, 1);\n            transition-timing-function:cubic-bezier(.165, .84, .44, 1);\n    max-width:calc(100% - 8px);\n    pointer-events:none;\n    outline:0\n}\n\n.tippy-popper[x-placement^=top] .tippy-backdrop{\n    border-radius:40% 40% 0 0\n}\n\n.tippy-popper[x-placement^=top] .tippy-roundarrow{\n    bottom:-7px;\n    bottom:-6.5px;\n    -webkit-transform-origin:50% 0;\n    transform-origin:50% 0;\n    margin:0 3px\n}\n\n.tippy-popper[x-placement^=top] .tippy-roundarrow svg{\n    position:absolute;\n    left:0;\n    -webkit-transform:rotate(180deg);\n    transform:rotate(180deg)\n}\n\n.tippy-popper[x-placement^=top] .tippy-arrow{\n    border-top:8px solid #333;\n    border-right:8px solid transparent;\n    border-left:8px solid transparent;\n    bottom:-7px;\n    margin:0 3px;\n    -webkit-transform-origin:50% 0;\n    transform-origin:50% 0\n}\n\n.tippy-popper[x-placement^=top] .tippy-backdrop{\n    -webkit-transform-origin:0 25%;\n    transform-origin:0 25%\n}\n\n.tippy-popper[x-placement^=top] .tippy-backdrop[data-state=visible]{\n    -webkit-transform:scale(1) translate(-50%, -55%);\n    transform:scale(1) translate(-50%, -55%)\n}\n\n.tippy-popper[x-placement^=top] .tippy-backdrop[data-state=hidden]{\n    -webkit-transform:scale(.2) translate(-50%, -45%);\n    transform:scale(.2) translate(-50%, -45%);\n    opacity:0\n}\n\n.tippy-popper[x-placement^=top] [data-animation=shift-toward][data-state=visible]{\n    -webkit-transform:translateY(-10px);\n    transform:translateY(-10px)\n}\n\n.tippy-popper[x-placement^=top] [data-animation=shift-toward][data-state=hidden]{\n    opacity:0;\n    -webkit-transform:translateY(-20px);\n    transform:translateY(-20px)\n}\n\n.tippy-popper[x-placement^=top] [data-animation=perspective]{\n    -webkit-transform-origin:bottom;\n    transform-origin:bottom\n}\n\n.tippy-popper[x-placement^=top] [data-animation=perspective][data-state=visible]{\n    -webkit-transform:perspective(700px) translateY(-10px) rotateX(0);\n    transform:perspective(700px) translateY(-10px) rotateX(0)\n}\n\n.tippy-popper[x-placement^=top] [data-animation=perspective][data-state=hidden]{\n    opacity:0;\n    -webkit-transform:perspective(700px) translateY(0) rotateX(60deg);\n    transform:perspective(700px) translateY(0) rotateX(60deg)\n}\n\n.tippy-popper[x-placement^=top] [data-animation=fade][data-state=visible]{\n    -webkit-transform:translateY(-10px);\n    transform:translateY(-10px)\n}\n\n.tippy-popper[x-placement^=top] [data-animation=fade][data-state=hidden]{\n    opacity:0;\n    -webkit-transform:translateY(-10px);\n    transform:translateY(-10px)\n}\n\n.tippy-popper[x-placement^=top] [data-animation=shift-away][data-state=visible]{\n    -webkit-transform:translateY(-10px);\n    transform:translateY(-10px)\n}\n\n.tippy-popper[x-placement^=top] [data-animation=shift-away][data-state=hidden]{\n    opacity:0;\n    -webkit-transform:translateY(0);\n    transform:translateY(0)\n}\n\n.tippy-popper[x-placement^=top] [data-animation=scale]{\n    -webkit-transform-origin:bottom;\n    transform-origin:bottom\n}\n\n.tippy-popper[x-placement^=top] [data-animation=scale][data-state=visible]{\n    -webkit-transform:translateY(-10px) scale(1);\n    transform:translateY(-10px) scale(1)\n}\n\n.tippy-popper[x-placement^=top] [data-animation=scale][data-state=hidden]{\n    opacity:0;\n    -webkit-transform:translateY(-10px) scale(.5);\n    transform:translateY(-10px) scale(.5)\n}\n\n.tippy-popper[x-placement^=top] [data-animation=slide-toggle]{\n    -webkit-transform-origin:center bottom;\n            transform-origin:center bottom;\n}\n\n.tippy-popper[x-placement^=top] [data-animation=slide-toggle][data-state=visible]{\n    -webkit-transform:scaleY(1);\n            transform:scaleY(1);\n    opacity:1;\n}\n\n.tippy-popper[x-placement^=top] [data-animation=slide-toggle][data-state=hidden]{\n    opacity:0;\n    -webkit-transform:scaleY(0);\n            transform:scaleY(0);\n}\n\n.tippy-popper[x-placement^=bottom] .tippy-backdrop{\n    border-radius:0 0 30% 30%\n}\n\n.tippy-popper[x-placement^=bottom] .tippy-roundarrow{\n    top:-7px;\n    -webkit-transform-origin:50% 100%;\n    transform-origin:50% 100%;\n    margin:0 3px\n}\n\n.tippy-popper[x-placement^=bottom] .tippy-roundarrow svg{\n    position:absolute;\n    left:0;\n    -webkit-transform:rotate(0);\n    transform:rotate(0)\n}\n\n.tippy-popper[x-placement^=bottom] .tippy-arrow{\n    border-bottom:8px solid #333;\n    border-right:8px solid transparent;\n    border-left:8px solid transparent;\n    top:-7px;\n    margin:0 3px;\n    -webkit-transform-origin:50% 100%;\n    transform-origin:50% 100%\n}\n\n.tippy-popper[x-placement^=bottom] .tippy-backdrop{\n    -webkit-transform-origin:0 -50%;\n    transform-origin:0 -50%\n}\n\n.tippy-popper[x-placement^=bottom] .tippy-backdrop[data-state=visible]{\n    -webkit-transform:scale(1) translate(-50%, -45%);\n    transform:scale(1) translate(-50%, -45%)\n}\n\n.tippy-popper[x-placement^=bottom] .tippy-backdrop[data-state=hidden]{\n    -webkit-transform:scale(.2) translate(-50%);\n    transform:scale(.2) translate(-50%);\n    opacity:0\n}\n\n.tippy-popper[x-placement^=bottom] [data-animation=shift-toward][data-state=visible]{\n    -webkit-transform:translateY(10px);\n    transform:translateY(10px)\n}\n\n.tippy-popper[x-placement^=bottom] [data-animation=shift-toward][data-state=hidden]{\n    opacity:0;\n    -webkit-transform:translateY(20px);\n    transform:translateY(20px)\n}\n\n.tippy-popper[x-placement^=bottom] [data-animation=perspective]{\n    -webkit-transform-origin:top;\n    transform-origin:top\n}\n\n.tippy-popper[x-placement^=bottom] [data-animation=perspective][data-state=visible]{\n    -webkit-transform:perspective(700px) translateY(10px) rotateX(0);\n    transform:perspective(700px) translateY(10px) rotateX(0)\n}\n\n.tippy-popper[x-placement^=bottom] [data-animation=perspective][data-state=hidden]{\n    opacity:0;\n    -webkit-transform:perspective(700px) translateY(0) rotateX(-60deg);\n    transform:perspective(700px) translateY(0) rotateX(-60deg)\n}\n\n.tippy-popper[x-placement^=bottom] [data-animation=fade][data-state=visible]{\n    -webkit-transform:translateY(10px);\n    transform:translateY(10px)\n}\n\n.tippy-popper[x-placement^=bottom] [data-animation=fade][data-state=hidden]{\n    opacity:0;\n    -webkit-transform:translateY(10px);\n    transform:translateY(10px)\n}\n\n.tippy-popper[x-placement^=bottom] [data-animation=shift-away][data-state=visible]{\n    -webkit-transform:translateY(10px);\n    transform:translateY(10px)\n}\n\n.tippy-popper[x-placement^=bottom] [data-animation=shift-away][data-state=hidden]{\n    opacity:0;\n    -webkit-transform:translateY(0);\n    transform:translateY(0)\n}\n\n.tippy-popper[x-placement^=bottom] [data-animation=scale]{\n    -webkit-transform-origin:top;\n    transform-origin:top\n}\n\n.tippy-popper[x-placement^=bottom] [data-animation=scale][data-state=visible]{\n    -webkit-transform:translateY(10px) scale(1);\n    transform:translateY(10px) scale(1)\n}\n\n.tippy-popper[x-placement^=bottom] [data-animation=scale][data-state=hidden]{\n    opacity:0;\n    -webkit-transform:translateY(10px) scale(.5);\n    transform:translateY(10px) scale(.5)\n}\n\n.tippy-popper[x-placement^=bottom] [data-animation=slide-toggle]{\n    -webkit-transform-origin:center top;\n            transform-origin:center top;\n}\n\n.tippy-popper[x-placement^=bottom] [data-animation=slide-toggle][data-state=visible]{\n    opacity:1;\n    -webkit-transform:scaleY(1);\n            transform:scaleY(1);\n}\n\n.tippy-popper[x-placement^=bottom] [data-animation=slide-toggle][data-state=hidden]{\n    opacity:0;\n    -webkit-transform:scaleY(0);\n            transform:scaleY(0);\n}\n\n.tippy-popper[x-placement^=left] .tippy-backdrop{\n    border-radius:50% 0 0 50%\n}\n\n.tippy-popper[x-placement^=left] .tippy-roundarrow{\n    right:-12px;\n    -webkit-transform-origin:33.33333333% 50%;\n    transform-origin:33.33333333% 50%;\n    margin:3px 0\n}\n\n.tippy-popper[x-placement^=left] .tippy-roundarrow svg{\n    position:absolute;\n    left:0;\n    -webkit-transform:rotate(90deg);\n    transform:rotate(90deg)\n}\n\n.tippy-popper[x-placement^=left] .tippy-arrow{\n    border-left:8px solid #333;\n    border-top:8px solid transparent;\n    border-bottom:8px solid transparent;\n    right:-7px;\n    margin:3px 0;\n    -webkit-transform-origin:0 50%;\n    transform-origin:0 50%\n}\n\n.tippy-popper[x-placement^=left] .tippy-backdrop{\n    -webkit-transform-origin:50% 0;\n    transform-origin:50% 0\n}\n\n.tippy-popper[x-placement^=left] .tippy-backdrop[data-state=visible]{\n    -webkit-transform:scale(1) translate(-50%, -50%);\n    transform:scale(1) translate(-50%, -50%)\n}\n\n.tippy-popper[x-placement^=left] .tippy-backdrop[data-state=hidden]{\n    -webkit-transform:scale(.2) translate(-75%, -50%);\n    transform:scale(.2) translate(-75%, -50%);\n    opacity:0\n}\n\n.tippy-popper[x-placement^=left] [data-animation=shift-toward][data-state=visible]{\n    -webkit-transform:translateX(-10px);\n    transform:translateX(-10px)\n}\n\n.tippy-popper[x-placement^=left] [data-animation=shift-toward][data-state=hidden]{\n    opacity:0;\n    -webkit-transform:translateX(-20px);\n    transform:translateX(-20px)\n}\n\n.tippy-popper[x-placement^=left] [data-animation=perspective]{\n    -webkit-transform-origin:right;\n    transform-origin:right\n}\n\n.tippy-popper[x-placement^=left] [data-animation=perspective][data-state=visible]{\n    -webkit-transform:perspective(700px) translateX(-10px) rotateY(0);\n    transform:perspective(700px) translateX(-10px) rotateY(0)\n}\n\n.tippy-popper[x-placement^=left] [data-animation=perspective][data-state=hidden]{\n    opacity:0;\n    -webkit-transform:perspective(700px) translateX(0) rotateY(-60deg);\n    transform:perspective(700px) translateX(0) rotateY(-60deg)\n}\n\n.tippy-popper[x-placement^=left] [data-animation=fade][data-state=visible]{\n    -webkit-transform:translateX(-10px);\n    transform:translateX(-10px)\n}\n\n.tippy-popper[x-placement^=left] [data-animation=fade][data-state=hidden]{\n    opacity:0;\n    -webkit-transform:translateX(-10px);\n    transform:translateX(-10px)\n}\n\n.tippy-popper[x-placement^=left] [data-animation=shift-away][data-state=visible]{\n    -webkit-transform:translateX(-10px);\n    transform:translateX(-10px)\n}\n\n.tippy-popper[x-placement^=left] [data-animation=shift-away][data-state=hidden]{\n    opacity:0;\n    -webkit-transform:translateX(0);\n    transform:translateX(0)\n}\n\n.tippy-popper[x-placement^=left] [data-animation=scale]{\n    -webkit-transform-origin:right;\n    transform-origin:right\n}\n\n.tippy-popper[x-placement^=left] [data-animation=scale][data-state=visible]{\n    -webkit-transform:translateX(-10px) scale(1);\n    transform:translateX(-10px) scale(1)\n}\n\n.tippy-popper[x-placement^=left] [data-animation=scale][data-state=hidden]{\n    opacity:0;\n    -webkit-transform:translateX(-10px) scale(.5);\n    transform:translateX(-10px) scale(.5)\n}\n\n.tippy-popper[x-placement^=right] .tippy-backdrop{\n    border-radius:0 50% 50% 0\n}\n\n.tippy-popper[x-placement^=right] .tippy-roundarrow{\n    left:-12px;\n    -webkit-transform-origin:66.66666666% 50%;\n    transform-origin:66.66666666% 50%;\n    margin:3px 0\n}\n\n.tippy-popper[x-placement^=right] .tippy-roundarrow svg{\n    position:absolute;\n    left:0;\n    -webkit-transform:rotate(-90deg);\n    transform:rotate(-90deg)\n}\n\n.tippy-popper[x-placement^=right] .tippy-arrow{\n    border-right:8px solid #333;\n    border-top:8px solid transparent;\n    border-bottom:8px solid transparent;\n    left:-7px;\n    margin:3px 0;\n    -webkit-transform-origin:100% 50%;\n    transform-origin:100% 50%\n}\n\n.tippy-popper[x-placement^=right] .tippy-backdrop{\n    -webkit-transform-origin:-50% 0;\n    transform-origin:-50% 0\n}\n\n.tippy-popper[x-placement^=right] .tippy-backdrop[data-state=visible]{\n    -webkit-transform:scale(1) translate(-50%, -50%);\n    transform:scale(1) translate(-50%, -50%)\n}\n\n.tippy-popper[x-placement^=right] .tippy-backdrop[data-state=hidden]{\n    -webkit-transform:scale(.2) translate(-25%, -50%);\n    transform:scale(.2) translate(-25%, -50%);\n    opacity:0\n}\n\n.tippy-popper[x-placement^=right] [data-animation=shift-toward][data-state=visible]{\n    -webkit-transform:translateX(10px);\n    transform:translateX(10px)\n}\n\n.tippy-popper[x-placement^=right] [data-animation=shift-toward][data-state=hidden]{\n    opacity:0;\n    -webkit-transform:translateX(20px);\n    transform:translateX(20px)\n}\n\n.tippy-popper[x-placement^=right] [data-animation=perspective]{\n    -webkit-transform-origin:left;\n    transform-origin:left\n}\n\n.tippy-popper[x-placement^=right] [data-animation=perspective][data-state=visible]{\n    -webkit-transform:perspective(700px) translateX(10px) rotateY(0);\n    transform:perspective(700px) translateX(10px) rotateY(0)\n}\n\n.tippy-popper[x-placement^=right] [data-animation=perspective][data-state=hidden]{\n    opacity:0;\n    -webkit-transform:perspective(700px) translateX(0) rotateY(60deg);\n    transform:perspective(700px) translateX(0) rotateY(60deg)\n}\n\n.tippy-popper[x-placement^=right] [data-animation=fade][data-state=visible]{\n    -webkit-transform:translateX(10px);\n    transform:translateX(10px)\n}\n\n.tippy-popper[x-placement^=right] [data-animation=fade][data-state=hidden]{\n    opacity:0;\n    -webkit-transform:translateX(10px);\n    transform:translateX(10px)\n}\n\n.tippy-popper[x-placement^=right] [data-animation=shift-away][data-state=visible]{\n    -webkit-transform:translateX(10px);\n    transform:translateX(10px)\n}\n\n.tippy-popper[x-placement^=right] [data-animation=shift-away][data-state=hidden]{\n    opacity:0;\n    -webkit-transform:translateX(0);\n    transform:translateX(0)\n}\n\n.tippy-popper[x-placement^=right] [data-animation=scale]{\n    -webkit-transform-origin:left;\n    transform-origin:left\n}\n\n.tippy-popper[x-placement^=right] [data-animation=scale][data-state=visible]{\n    -webkit-transform:translateX(10px) scale(1);\n    transform:translateX(10px) scale(1)\n}\n\n.tippy-popper[x-placement^=right] [data-animation=scale][data-state=hidden]{\n    opacity:0;\n    -webkit-transform:translateX(10px) scale(.5);\n    transform:translateX(10px) scale(.5)\n}\n\n.tippy-tooltip{\n    position:relative;\n    color:#fff;\n    border-radius:4px;\n    font-size:.9rem;\n    padding:.3rem .6rem;\n    text-align:left;\n    -webkit-font-smoothing:antialiased;\n    -moz-osx-font-smoothing:grayscale;\n    background-color:rgba(0, 0, 0, .8);\n}\n\n.tippy-tooltip[data-size=small]{\n    padding:7px 14px;\n    font-size:12px;\n}\n\n.tippy-tooltip[data-size=large]{\n    padding:.4rem .8rem;\n    font-size:1rem;\n}\n\n.tippy-tooltip[data-animatefill]{\n    overflow:hidden;\n    background-color:transparent\n}\n\n.tippy-tooltip[data-interactive],\n.tippy-tooltip[data-interactive] .tippy-roundarrow path{\n    pointer-events:auto\n}\n\n.tippy-tooltip[data-inertia][data-state=visible]{\n    -webkit-transition-timing-function:cubic-bezier(.54, 1.5, .38, 1.11);\n            transition-timing-function:cubic-bezier(.54, 1.5, .38, 1.11)\n}\n\n.tippy-tooltip[data-inertia][data-state=hidden]{\n    -webkit-transition-timing-function:ease;\n            transition-timing-function:ease\n}\n\n.tippy-arrow,\n.tippy-roundarrow{\n    position:absolute;\n    width:0;\n    height:0\n}\n\n.tippy-roundarrow{\n    width:18px;\n    height:7px;\n    fill:#333;\n    pointer-events:none\n}\n\n.tippy-backdrop{\n    position:absolute;\n    background-color:#333;\n    border-radius:50%;\n    width:calc(110% + 2rem);\n    left:50%;\n    top:50%;\n    z-index:-1;\n    -webkit-transition:all cubic-bezier(.46, .1, .52, .98);\n    transition:all cubic-bezier(.46, .1, .52, .98);\n    -webkit-backface-visibility:hidden;\n    backface-visibility:hidden\n}\n\n.tippy-backdrop:after{\n    content:"";\n    float:left;\n    padding-top:100%\n}\n\n.tippy-backdrop+.tippy-content{\n    -webkit-transition-property:opacity;\n    transition-property:opacity;\n    will-change:opacity\n}\n\n.tippy-backdrop+.tippy-content[data-state=visible]{\n    opacity:1\n}\n\n.tippy-backdrop+.tippy-content[data-state=hidden]{\n    opacity:0\n}\n\n.tippy-tooltip.light-theme{\n    color:#26323d;\n    -webkit-box-shadow:0px 0px 6px 0px rgba(220, 222, 229, 1);\n            box-shadow:0px 0px 6px 0px rgba(220, 222, 229, 1);\n    background-color:#fff;\n}\n\n.tippy-tooltip.light-theme:before{\n    content:\'\';\n    position:absolute;\n    top:0;\n    right:0;\n    bottom:0;\n    left:0;\n    z-index:-1;\n    border-radius:inherit;\n    background:inherit;\n}\n\n.tippy-tooltip.light-theme .tippy-arrow{\n    z-index:-2;\n    width:11px;\n    height:11px;\n    border:none !important;\n    -webkit-box-shadow:inherit;\n            box-shadow:inherit;\n    background:inherit;\n    -webkit-transform-origin:center center;\n            transform-origin:center center;\n    -webkit-transform:rotateZ(45deg);\n            transform:rotateZ(45deg);\n}\n\n.tippy-tooltip.light-theme[x-placement^=top] .tippy-arrow{\n    bottom:-5px;\n}\n\n.tippy-tooltip.light-theme[x-placement^=bottom] .tippy-arrow{\n    top:-5px;\n}\n\n.tippy-tooltip.light-theme[x-placement^=left] .tippy-arrow{\n    right:-5px;\n}\n\n.tippy-tooltip.light-theme[x-placement^=right] .tippy-arrow{\n    left:-5px;\n}\n\n.tippy-tooltip.light-theme .tippy-backdrop{\n    background-color:#fff\n}\n\n.tippy-tooltip.light-theme .tippy-roundarrow{\n    fill:#fff\n}\n\n.tippy-tooltip.light-theme[data-animatefill]{\n    background-color:transparent\n}\n\n.tippy-tooltip.light-border-theme{\n    color:#26323d;\n    -webkit-box-shadow:0px 0px 6px 0px rgba(220, 222, 229, 1);\n            box-shadow:0px 0px 6px 0px rgba(220, 222, 229, 1);\n    background-color:#fff;\n    border:1px solid #dcdee5;\n}\n\n.tippy-tooltip.light-border-theme:before{\n    content:\'\';\n    position:absolute;\n    top:0;\n    right:0;\n    bottom:0;\n    left:0;\n    z-index:-1;\n    border-radius:inherit;\n    background:inherit;\n}\n\n.tippy-tooltip.light-border-theme .tippy-arrow{\n    z-index:-2;\n    width:11px;\n    height:11px;\n    border:1px solid #dcdee5;\n    -webkit-box-shadow:inherit;\n            box-shadow:inherit;\n    background:inherit;\n    -webkit-transform-origin:center center;\n            transform-origin:center center;\n    -webkit-transform:rotateZ(45deg);\n            transform:rotateZ(45deg);\n}\n\n.tippy-tooltip.light-border-theme[x-placement^=top] .tippy-arrow{\n    bottom:-5px;\n}\n\n.tippy-tooltip.light-border-theme[x-placement^=bottom] .tippy-arrow{\n    top:-5px;\n}\n\n.tippy-tooltip.light-border-theme[x-placement^=left] .tippy-arrow{\n    right:-5px;\n}\n\n.tippy-tooltip.light-border-theme[x-placement^=right] .tippy-arrow{\n    left:-5px;\n}\n\n.tippy-tooltip.light-border-theme .tippy-backdrop{\n    background-color:#fff\n}\n\n.tippy-tooltip.light-border-theme .tippy-roundarrow{\n    fill:#fff\n}\n\n.tippy-tooltip.light-border-theme[data-animatefill]{\n    background-color:transparent\n}\n', '', { version: 3, sources: ['webpack://./node_modules/bk-magic-vue/lib/ui/popover.css'], names: [], mappings: 'AAAA;IACI,oBAAoB;AACxB;;AAEA;IACI,oBAAoB;IACpB,iBAAiB;IACjB,SAAS;AACb;;AAEA;IACI,yBAAyB;IACzB;AACJ;;AAEA;IACI,kEAAkE;YAC1D,0DAA0D;IAClE,0BAA0B;IAC1B,mBAAmB;IACnB;AACJ;;AAEA;IACI;AACJ;;AAEA;IACI,WAAW;IACX,aAAa;IACb,8BAA8B;IAC9B,sBAAsB;IACtB;AACJ;;AAEA;IACI,iBAAiB;IACjB,MAAM;IACN,gCAAgC;IAChC;AACJ;;AAEA;IACI,yBAAyB;IACzB,kCAAkC;IAClC,iCAAiC;IACjC,WAAW;IACX,YAAY;IACZ,8BAA8B;IAC9B;AACJ;;AAEA;IACI,8BAA8B;IAC9B;AACJ;;AAEA;IACI,gDAAgD;IAChD;AACJ;;AAEA;IACI,iDAAiD;IACjD,yCAAyC;IACzC;AACJ;;AAEA;IACI,mCAAmC;IACnC;AACJ;;AAEA;IACI,SAAS;IACT,mCAAmC;IACnC;AACJ;;AAEA;IACI,+BAA+B;IAC/B;AACJ;;AAEA;IACI,iEAAiE;IACjE;AACJ;;AAEA;IACI,SAAS;IACT,iEAAiE;IACjE;AACJ;;AAEA;IACI,mCAAmC;IACnC;AACJ;;AAEA;IACI,SAAS;IACT,mCAAmC;IACnC;AACJ;;AAEA;IACI,mCAAmC;IACnC;AACJ;;AAEA;IACI,SAAS;IACT,+BAA+B;IAC/B;AACJ;;AAEA;IACI,+BAA+B;IAC/B;AACJ;;AAEA;IACI,4CAA4C;IAC5C;AACJ;;AAEA;IACI,SAAS;IACT,6CAA6C;IAC7C;AACJ;;AAEA;IACI,sCAAsC;YAC9B,8BAA8B;AAC1C;;AAEA;IACI,2BAA2B;YACnB,mBAAmB;IAC3B,SAAS;AACb;;AAEA;IACI,SAAS;IACT,2BAA2B;YACnB,mBAAmB;AAC/B;;AAEA;IACI;AACJ;;AAEA;IACI,QAAQ;IACR,iCAAiC;IACjC,yBAAyB;IACzB;AACJ;;AAEA;IACI,iBAAiB;IACjB,MAAM;IACN,2BAA2B;IAC3B;AACJ;;AAEA;IACI,4BAA4B;IAC5B,kCAAkC;IAClC,iCAAiC;IACjC,QAAQ;IACR,YAAY;IACZ,iCAAiC;IACjC;AACJ;;AAEA;IACI,+BAA+B;IAC/B;AACJ;;AAEA;IACI,gDAAgD;IAChD;AACJ;;AAEA;IACI,2CAA2C;IAC3C,mCAAmC;IACnC;AACJ;;AAEA;IACI,kCAAkC;IAClC;AACJ;;AAEA;IACI,SAAS;IACT,kCAAkC;IAClC;AACJ;;AAEA;IACI,4BAA4B;IAC5B;AACJ;;AAEA;IACI,gEAAgE;IAChE;AACJ;;AAEA;IACI,SAAS;IACT,kEAAkE;IAClE;AACJ;;AAEA;IACI,kCAAkC;IAClC;AACJ;;AAEA;IACI,SAAS;IACT,kCAAkC;IAClC;AACJ;;AAEA;IACI,kCAAkC;IAClC;AACJ;;AAEA;IACI,SAAS;IACT,+BAA+B;IAC/B;AACJ;;AAEA;IACI,4BAA4B;IAC5B;AACJ;;AAEA;IACI,2CAA2C;IAC3C;AACJ;;AAEA;IACI,SAAS;IACT,4CAA4C;IAC5C;AACJ;;AAEA;IACI,mCAAmC;YAC3B,2BAA2B;AACvC;;AAEA;IACI,SAAS;IACT,2BAA2B;YACnB,mBAAmB;AAC/B;;AAEA;IACI,SAAS;IACT,2BAA2B;YACnB,mBAAmB;AAC/B;;AAEA;IACI;AACJ;;AAEA;IACI,WAAW;IACX,yCAAyC;IACzC,iCAAiC;IACjC;AACJ;;AAEA;IACI,iBAAiB;IACjB,MAAM;IACN,+BAA+B;IAC/B;AACJ;;AAEA;IACI,0BAA0B;IAC1B,gCAAgC;IAChC,mCAAmC;IACnC,UAAU;IACV,YAAY;IACZ,8BAA8B;IAC9B;AACJ;;AAEA;IACI,8BAA8B;IAC9B;AACJ;;AAEA;IACI,gDAAgD;IAChD;AACJ;;AAEA;IACI,iDAAiD;IACjD,yCAAyC;IACzC;AACJ;;AAEA;IACI,mCAAmC;IACnC;AACJ;;AAEA;IACI,SAAS;IACT,mCAAmC;IACnC;AACJ;;AAEA;IACI,8BAA8B;IAC9B;AACJ;;AAEA;IACI,iEAAiE;IACjE;AACJ;;AAEA;IACI,SAAS;IACT,kEAAkE;IAClE;AACJ;;AAEA;IACI,mCAAmC;IACnC;AACJ;;AAEA;IACI,SAAS;IACT,mCAAmC;IACnC;AACJ;;AAEA;IACI,mCAAmC;IACnC;AACJ;;AAEA;IACI,SAAS;IACT,+BAA+B;IAC/B;AACJ;;AAEA;IACI,8BAA8B;IAC9B;AACJ;;AAEA;IACI,4CAA4C;IAC5C;AACJ;;AAEA;IACI,SAAS;IACT,6CAA6C;IAC7C;AACJ;;AAEA;IACI;AACJ;;AAEA;IACI,UAAU;IACV,yCAAyC;IACzC,iCAAiC;IACjC;AACJ;;AAEA;IACI,iBAAiB;IACjB,MAAM;IACN,gCAAgC;IAChC;AACJ;;AAEA;IACI,2BAA2B;IAC3B,gCAAgC;IAChC,mCAAmC;IACnC,SAAS;IACT,YAAY;IACZ,iCAAiC;IACjC;AACJ;;AAEA;IACI,+BAA+B;IAC/B;AACJ;;AAEA;IACI,gDAAgD;IAChD;AACJ;;AAEA;IACI,iDAAiD;IACjD,yCAAyC;IACzC;AACJ;;AAEA;IACI,kCAAkC;IAClC;AACJ;;AAEA;IACI,SAAS;IACT,kCAAkC;IAClC;AACJ;;AAEA;IACI,6BAA6B;IAC7B;AACJ;;AAEA;IACI,gEAAgE;IAChE;AACJ;;AAEA;IACI,SAAS;IACT,iEAAiE;IACjE;AACJ;;AAEA;IACI,kCAAkC;IAClC;AACJ;;AAEA;IACI,SAAS;IACT,kCAAkC;IAClC;AACJ;;AAEA;IACI,kCAAkC;IAClC;AACJ;;AAEA;IACI,SAAS;IACT,+BAA+B;IAC/B;AACJ;;AAEA;IACI,6BAA6B;IAC7B;AACJ;;AAEA;IACI,2CAA2C;IAC3C;AACJ;;AAEA;IACI,SAAS;IACT,4CAA4C;IAC5C;AACJ;;AAEA;IACI,iBAAiB;IACjB,UAAU;IACV,iBAAiB;IACjB,eAAe;IACf,mBAAmB;IACnB,eAAe;IACf,kCAAkC;IAClC,iCAAiC;IACjC,kCAAkC;AACtC;;AAEA;IACI,gBAAgB;IAChB,cAAc;AAClB;;AAEA;IACI,mBAAmB;IACnB,cAAc;AAClB;;AAEA;IACI,eAAe;IACf;AACJ;;AAEA;;IAEI;AACJ;;AAEA;IACI,oEAAoE;YAC5D;AACZ;;AAEA;IACI,uCAAuC;YAC/B;AACZ;;AAEA;;IAEI,iBAAiB;IACjB,OAAO;IACP;AACJ;;AAEA;IACI,UAAU;IACV,UAAU;IACV,SAAS;IACT;AACJ;;AAEA;IACI,iBAAiB;IACjB,qBAAqB;IACrB,iBAAiB;IACjB,uBAAuB;IACvB,QAAQ;IACR,OAAO;IACP,UAAU;IACV,sDAAsD;IACtD,8CAA8C;IAC9C,kCAAkC;IAClC;AACJ;;AAEA;IACI,UAAU;IACV,UAAU;IACV;AACJ;;AAEA;IACI,mCAAmC;IACnC,2BAA2B;IAC3B;AACJ;;AAEA;IACI;AACJ;;AAEA;IACI;AACJ;;AAEA;IACI,aAAa;IACb,yDAAyD;YACjD,iDAAiD;IACzD,qBAAqB;AACzB;;AAEA;IACI,UAAU;IACV,iBAAiB;IACjB,KAAK;IACL,OAAO;IACP,QAAQ;IACR,MAAM;IACN,UAAU;IACV,qBAAqB;IACrB,kBAAkB;AACtB;;AAEA;IACI,UAAU;IACV,UAAU;IACV,WAAW;IACX,sBAAsB;IACtB,0BAA0B;YAClB,kBAAkB;IAC1B,kBAAkB;IAClB,sCAAsC;YAC9B,8BAA8B;IACtC,gCAAgC;YACxB,wBAAwB;AACpC;;AAEA;IACI,WAAW;AACf;;AAEA;IACI,QAAQ;AACZ;;AAEA;IACI,UAAU;AACd;;AAEA;IACI,SAAS;AACb;;AAEA;IACI;AACJ;;AAEA;IACI;AACJ;;AAEA;IACI;AACJ;;AAEA;IACI,aAAa;IACb,yDAAyD;YACjD,iDAAiD;IACzD,qBAAqB;IACrB,wBAAwB;AAC5B;;AAEA;IACI,UAAU;IACV,iBAAiB;IACjB,KAAK;IACL,OAAO;IACP,QAAQ;IACR,MAAM;IACN,UAAU;IACV,qBAAqB;IACrB,kBAAkB;AACtB;;AAEA;IACI,UAAU;IACV,UAAU;IACV,WAAW;IACX,wBAAwB;IACxB,0BAA0B;YAClB,kBAAkB;IAC1B,kBAAkB;IAClB,sCAAsC;YAC9B,8BAA8B;IACtC,gCAAgC;YACxB,wBAAwB;AACpC;;AAEA;IACI,WAAW;AACf;;AAEA;IACI,QAAQ;AACZ;;AAEA;IACI,UAAU;AACd;;AAEA;IACI,SAAS;AACb;;AAEA;IACI;AACJ;;AAEA;IACI;AACJ;;AAEA;IACI;AACJ', sourcesContent: ['.bk-tooltip{\n    display:inline-block;\n}\n\n.bk-tooltip-ref{\n    display:inline-block;\n    position:relative;\n    outline:0;\n}\n\n.tippy-iOS{\n    cursor:pointer !important;\n    -webkit-tap-highlight-color:transparent\n}\n\n.tippy-popper{\n    -webkit-transition-timing-function:cubic-bezier(.165, .84, .44, 1);\n            transition-timing-function:cubic-bezier(.165, .84, .44, 1);\n    max-width:calc(100% - 8px);\n    pointer-events:none;\n    outline:0\n}\n\n.tippy-popper[x-placement^=top] .tippy-backdrop{\n    border-radius:40% 40% 0 0\n}\n\n.tippy-popper[x-placement^=top] .tippy-roundarrow{\n    bottom:-7px;\n    bottom:-6.5px;\n    -webkit-transform-origin:50% 0;\n    transform-origin:50% 0;\n    margin:0 3px\n}\n\n.tippy-popper[x-placement^=top] .tippy-roundarrow svg{\n    position:absolute;\n    left:0;\n    -webkit-transform:rotate(180deg);\n    transform:rotate(180deg)\n}\n\n.tippy-popper[x-placement^=top] .tippy-arrow{\n    border-top:8px solid #333;\n    border-right:8px solid transparent;\n    border-left:8px solid transparent;\n    bottom:-7px;\n    margin:0 3px;\n    -webkit-transform-origin:50% 0;\n    transform-origin:50% 0\n}\n\n.tippy-popper[x-placement^=top] .tippy-backdrop{\n    -webkit-transform-origin:0 25%;\n    transform-origin:0 25%\n}\n\n.tippy-popper[x-placement^=top] .tippy-backdrop[data-state=visible]{\n    -webkit-transform:scale(1) translate(-50%, -55%);\n    transform:scale(1) translate(-50%, -55%)\n}\n\n.tippy-popper[x-placement^=top] .tippy-backdrop[data-state=hidden]{\n    -webkit-transform:scale(.2) translate(-50%, -45%);\n    transform:scale(.2) translate(-50%, -45%);\n    opacity:0\n}\n\n.tippy-popper[x-placement^=top] [data-animation=shift-toward][data-state=visible]{\n    -webkit-transform:translateY(-10px);\n    transform:translateY(-10px)\n}\n\n.tippy-popper[x-placement^=top] [data-animation=shift-toward][data-state=hidden]{\n    opacity:0;\n    -webkit-transform:translateY(-20px);\n    transform:translateY(-20px)\n}\n\n.tippy-popper[x-placement^=top] [data-animation=perspective]{\n    -webkit-transform-origin:bottom;\n    transform-origin:bottom\n}\n\n.tippy-popper[x-placement^=top] [data-animation=perspective][data-state=visible]{\n    -webkit-transform:perspective(700px) translateY(-10px) rotateX(0);\n    transform:perspective(700px) translateY(-10px) rotateX(0)\n}\n\n.tippy-popper[x-placement^=top] [data-animation=perspective][data-state=hidden]{\n    opacity:0;\n    -webkit-transform:perspective(700px) translateY(0) rotateX(60deg);\n    transform:perspective(700px) translateY(0) rotateX(60deg)\n}\n\n.tippy-popper[x-placement^=top] [data-animation=fade][data-state=visible]{\n    -webkit-transform:translateY(-10px);\n    transform:translateY(-10px)\n}\n\n.tippy-popper[x-placement^=top] [data-animation=fade][data-state=hidden]{\n    opacity:0;\n    -webkit-transform:translateY(-10px);\n    transform:translateY(-10px)\n}\n\n.tippy-popper[x-placement^=top] [data-animation=shift-away][data-state=visible]{\n    -webkit-transform:translateY(-10px);\n    transform:translateY(-10px)\n}\n\n.tippy-popper[x-placement^=top] [data-animation=shift-away][data-state=hidden]{\n    opacity:0;\n    -webkit-transform:translateY(0);\n    transform:translateY(0)\n}\n\n.tippy-popper[x-placement^=top] [data-animation=scale]{\n    -webkit-transform-origin:bottom;\n    transform-origin:bottom\n}\n\n.tippy-popper[x-placement^=top] [data-animation=scale][data-state=visible]{\n    -webkit-transform:translateY(-10px) scale(1);\n    transform:translateY(-10px) scale(1)\n}\n\n.tippy-popper[x-placement^=top] [data-animation=scale][data-state=hidden]{\n    opacity:0;\n    -webkit-transform:translateY(-10px) scale(.5);\n    transform:translateY(-10px) scale(.5)\n}\n\n.tippy-popper[x-placement^=top] [data-animation=slide-toggle]{\n    -webkit-transform-origin:center bottom;\n            transform-origin:center bottom;\n}\n\n.tippy-popper[x-placement^=top] [data-animation=slide-toggle][data-state=visible]{\n    -webkit-transform:scaleY(1);\n            transform:scaleY(1);\n    opacity:1;\n}\n\n.tippy-popper[x-placement^=top] [data-animation=slide-toggle][data-state=hidden]{\n    opacity:0;\n    -webkit-transform:scaleY(0);\n            transform:scaleY(0);\n}\n\n.tippy-popper[x-placement^=bottom] .tippy-backdrop{\n    border-radius:0 0 30% 30%\n}\n\n.tippy-popper[x-placement^=bottom] .tippy-roundarrow{\n    top:-7px;\n    -webkit-transform-origin:50% 100%;\n    transform-origin:50% 100%;\n    margin:0 3px\n}\n\n.tippy-popper[x-placement^=bottom] .tippy-roundarrow svg{\n    position:absolute;\n    left:0;\n    -webkit-transform:rotate(0);\n    transform:rotate(0)\n}\n\n.tippy-popper[x-placement^=bottom] .tippy-arrow{\n    border-bottom:8px solid #333;\n    border-right:8px solid transparent;\n    border-left:8px solid transparent;\n    top:-7px;\n    margin:0 3px;\n    -webkit-transform-origin:50% 100%;\n    transform-origin:50% 100%\n}\n\n.tippy-popper[x-placement^=bottom] .tippy-backdrop{\n    -webkit-transform-origin:0 -50%;\n    transform-origin:0 -50%\n}\n\n.tippy-popper[x-placement^=bottom] .tippy-backdrop[data-state=visible]{\n    -webkit-transform:scale(1) translate(-50%, -45%);\n    transform:scale(1) translate(-50%, -45%)\n}\n\n.tippy-popper[x-placement^=bottom] .tippy-backdrop[data-state=hidden]{\n    -webkit-transform:scale(.2) translate(-50%);\n    transform:scale(.2) translate(-50%);\n    opacity:0\n}\n\n.tippy-popper[x-placement^=bottom] [data-animation=shift-toward][data-state=visible]{\n    -webkit-transform:translateY(10px);\n    transform:translateY(10px)\n}\n\n.tippy-popper[x-placement^=bottom] [data-animation=shift-toward][data-state=hidden]{\n    opacity:0;\n    -webkit-transform:translateY(20px);\n    transform:translateY(20px)\n}\n\n.tippy-popper[x-placement^=bottom] [data-animation=perspective]{\n    -webkit-transform-origin:top;\n    transform-origin:top\n}\n\n.tippy-popper[x-placement^=bottom] [data-animation=perspective][data-state=visible]{\n    -webkit-transform:perspective(700px) translateY(10px) rotateX(0);\n    transform:perspective(700px) translateY(10px) rotateX(0)\n}\n\n.tippy-popper[x-placement^=bottom] [data-animation=perspective][data-state=hidden]{\n    opacity:0;\n    -webkit-transform:perspective(700px) translateY(0) rotateX(-60deg);\n    transform:perspective(700px) translateY(0) rotateX(-60deg)\n}\n\n.tippy-popper[x-placement^=bottom] [data-animation=fade][data-state=visible]{\n    -webkit-transform:translateY(10px);\n    transform:translateY(10px)\n}\n\n.tippy-popper[x-placement^=bottom] [data-animation=fade][data-state=hidden]{\n    opacity:0;\n    -webkit-transform:translateY(10px);\n    transform:translateY(10px)\n}\n\n.tippy-popper[x-placement^=bottom] [data-animation=shift-away][data-state=visible]{\n    -webkit-transform:translateY(10px);\n    transform:translateY(10px)\n}\n\n.tippy-popper[x-placement^=bottom] [data-animation=shift-away][data-state=hidden]{\n    opacity:0;\n    -webkit-transform:translateY(0);\n    transform:translateY(0)\n}\n\n.tippy-popper[x-placement^=bottom] [data-animation=scale]{\n    -webkit-transform-origin:top;\n    transform-origin:top\n}\n\n.tippy-popper[x-placement^=bottom] [data-animation=scale][data-state=visible]{\n    -webkit-transform:translateY(10px) scale(1);\n    transform:translateY(10px) scale(1)\n}\n\n.tippy-popper[x-placement^=bottom] [data-animation=scale][data-state=hidden]{\n    opacity:0;\n    -webkit-transform:translateY(10px) scale(.5);\n    transform:translateY(10px) scale(.5)\n}\n\n.tippy-popper[x-placement^=bottom] [data-animation=slide-toggle]{\n    -webkit-transform-origin:center top;\n            transform-origin:center top;\n}\n\n.tippy-popper[x-placement^=bottom] [data-animation=slide-toggle][data-state=visible]{\n    opacity:1;\n    -webkit-transform:scaleY(1);\n            transform:scaleY(1);\n}\n\n.tippy-popper[x-placement^=bottom] [data-animation=slide-toggle][data-state=hidden]{\n    opacity:0;\n    -webkit-transform:scaleY(0);\n            transform:scaleY(0);\n}\n\n.tippy-popper[x-placement^=left] .tippy-backdrop{\n    border-radius:50% 0 0 50%\n}\n\n.tippy-popper[x-placement^=left] .tippy-roundarrow{\n    right:-12px;\n    -webkit-transform-origin:33.33333333% 50%;\n    transform-origin:33.33333333% 50%;\n    margin:3px 0\n}\n\n.tippy-popper[x-placement^=left] .tippy-roundarrow svg{\n    position:absolute;\n    left:0;\n    -webkit-transform:rotate(90deg);\n    transform:rotate(90deg)\n}\n\n.tippy-popper[x-placement^=left] .tippy-arrow{\n    border-left:8px solid #333;\n    border-top:8px solid transparent;\n    border-bottom:8px solid transparent;\n    right:-7px;\n    margin:3px 0;\n    -webkit-transform-origin:0 50%;\n    transform-origin:0 50%\n}\n\n.tippy-popper[x-placement^=left] .tippy-backdrop{\n    -webkit-transform-origin:50% 0;\n    transform-origin:50% 0\n}\n\n.tippy-popper[x-placement^=left] .tippy-backdrop[data-state=visible]{\n    -webkit-transform:scale(1) translate(-50%, -50%);\n    transform:scale(1) translate(-50%, -50%)\n}\n\n.tippy-popper[x-placement^=left] .tippy-backdrop[data-state=hidden]{\n    -webkit-transform:scale(.2) translate(-75%, -50%);\n    transform:scale(.2) translate(-75%, -50%);\n    opacity:0\n}\n\n.tippy-popper[x-placement^=left] [data-animation=shift-toward][data-state=visible]{\n    -webkit-transform:translateX(-10px);\n    transform:translateX(-10px)\n}\n\n.tippy-popper[x-placement^=left] [data-animation=shift-toward][data-state=hidden]{\n    opacity:0;\n    -webkit-transform:translateX(-20px);\n    transform:translateX(-20px)\n}\n\n.tippy-popper[x-placement^=left] [data-animation=perspective]{\n    -webkit-transform-origin:right;\n    transform-origin:right\n}\n\n.tippy-popper[x-placement^=left] [data-animation=perspective][data-state=visible]{\n    -webkit-transform:perspective(700px) translateX(-10px) rotateY(0);\n    transform:perspective(700px) translateX(-10px) rotateY(0)\n}\n\n.tippy-popper[x-placement^=left] [data-animation=perspective][data-state=hidden]{\n    opacity:0;\n    -webkit-transform:perspective(700px) translateX(0) rotateY(-60deg);\n    transform:perspective(700px) translateX(0) rotateY(-60deg)\n}\n\n.tippy-popper[x-placement^=left] [data-animation=fade][data-state=visible]{\n    -webkit-transform:translateX(-10px);\n    transform:translateX(-10px)\n}\n\n.tippy-popper[x-placement^=left] [data-animation=fade][data-state=hidden]{\n    opacity:0;\n    -webkit-transform:translateX(-10px);\n    transform:translateX(-10px)\n}\n\n.tippy-popper[x-placement^=left] [data-animation=shift-away][data-state=visible]{\n    -webkit-transform:translateX(-10px);\n    transform:translateX(-10px)\n}\n\n.tippy-popper[x-placement^=left] [data-animation=shift-away][data-state=hidden]{\n    opacity:0;\n    -webkit-transform:translateX(0);\n    transform:translateX(0)\n}\n\n.tippy-popper[x-placement^=left] [data-animation=scale]{\n    -webkit-transform-origin:right;\n    transform-origin:right\n}\n\n.tippy-popper[x-placement^=left] [data-animation=scale][data-state=visible]{\n    -webkit-transform:translateX(-10px) scale(1);\n    transform:translateX(-10px) scale(1)\n}\n\n.tippy-popper[x-placement^=left] [data-animation=scale][data-state=hidden]{\n    opacity:0;\n    -webkit-transform:translateX(-10px) scale(.5);\n    transform:translateX(-10px) scale(.5)\n}\n\n.tippy-popper[x-placement^=right] .tippy-backdrop{\n    border-radius:0 50% 50% 0\n}\n\n.tippy-popper[x-placement^=right] .tippy-roundarrow{\n    left:-12px;\n    -webkit-transform-origin:66.66666666% 50%;\n    transform-origin:66.66666666% 50%;\n    margin:3px 0\n}\n\n.tippy-popper[x-placement^=right] .tippy-roundarrow svg{\n    position:absolute;\n    left:0;\n    -webkit-transform:rotate(-90deg);\n    transform:rotate(-90deg)\n}\n\n.tippy-popper[x-placement^=right] .tippy-arrow{\n    border-right:8px solid #333;\n    border-top:8px solid transparent;\n    border-bottom:8px solid transparent;\n    left:-7px;\n    margin:3px 0;\n    -webkit-transform-origin:100% 50%;\n    transform-origin:100% 50%\n}\n\n.tippy-popper[x-placement^=right] .tippy-backdrop{\n    -webkit-transform-origin:-50% 0;\n    transform-origin:-50% 0\n}\n\n.tippy-popper[x-placement^=right] .tippy-backdrop[data-state=visible]{\n    -webkit-transform:scale(1) translate(-50%, -50%);\n    transform:scale(1) translate(-50%, -50%)\n}\n\n.tippy-popper[x-placement^=right] .tippy-backdrop[data-state=hidden]{\n    -webkit-transform:scale(.2) translate(-25%, -50%);\n    transform:scale(.2) translate(-25%, -50%);\n    opacity:0\n}\n\n.tippy-popper[x-placement^=right] [data-animation=shift-toward][data-state=visible]{\n    -webkit-transform:translateX(10px);\n    transform:translateX(10px)\n}\n\n.tippy-popper[x-placement^=right] [data-animation=shift-toward][data-state=hidden]{\n    opacity:0;\n    -webkit-transform:translateX(20px);\n    transform:translateX(20px)\n}\n\n.tippy-popper[x-placement^=right] [data-animation=perspective]{\n    -webkit-transform-origin:left;\n    transform-origin:left\n}\n\n.tippy-popper[x-placement^=right] [data-animation=perspective][data-state=visible]{\n    -webkit-transform:perspective(700px) translateX(10px) rotateY(0);\n    transform:perspective(700px) translateX(10px) rotateY(0)\n}\n\n.tippy-popper[x-placement^=right] [data-animation=perspective][data-state=hidden]{\n    opacity:0;\n    -webkit-transform:perspective(700px) translateX(0) rotateY(60deg);\n    transform:perspective(700px) translateX(0) rotateY(60deg)\n}\n\n.tippy-popper[x-placement^=right] [data-animation=fade][data-state=visible]{\n    -webkit-transform:translateX(10px);\n    transform:translateX(10px)\n}\n\n.tippy-popper[x-placement^=right] [data-animation=fade][data-state=hidden]{\n    opacity:0;\n    -webkit-transform:translateX(10px);\n    transform:translateX(10px)\n}\n\n.tippy-popper[x-placement^=right] [data-animation=shift-away][data-state=visible]{\n    -webkit-transform:translateX(10px);\n    transform:translateX(10px)\n}\n\n.tippy-popper[x-placement^=right] [data-animation=shift-away][data-state=hidden]{\n    opacity:0;\n    -webkit-transform:translateX(0);\n    transform:translateX(0)\n}\n\n.tippy-popper[x-placement^=right] [data-animation=scale]{\n    -webkit-transform-origin:left;\n    transform-origin:left\n}\n\n.tippy-popper[x-placement^=right] [data-animation=scale][data-state=visible]{\n    -webkit-transform:translateX(10px) scale(1);\n    transform:translateX(10px) scale(1)\n}\n\n.tippy-popper[x-placement^=right] [data-animation=scale][data-state=hidden]{\n    opacity:0;\n    -webkit-transform:translateX(10px) scale(.5);\n    transform:translateX(10px) scale(.5)\n}\n\n.tippy-tooltip{\n    position:relative;\n    color:#fff;\n    border-radius:4px;\n    font-size:.9rem;\n    padding:.3rem .6rem;\n    text-align:left;\n    -webkit-font-smoothing:antialiased;\n    -moz-osx-font-smoothing:grayscale;\n    background-color:rgba(0, 0, 0, .8);\n}\n\n.tippy-tooltip[data-size=small]{\n    padding:7px 14px;\n    font-size:12px;\n}\n\n.tippy-tooltip[data-size=large]{\n    padding:.4rem .8rem;\n    font-size:1rem;\n}\n\n.tippy-tooltip[data-animatefill]{\n    overflow:hidden;\n    background-color:transparent\n}\n\n.tippy-tooltip[data-interactive],\n.tippy-tooltip[data-interactive] .tippy-roundarrow path{\n    pointer-events:auto\n}\n\n.tippy-tooltip[data-inertia][data-state=visible]{\n    -webkit-transition-timing-function:cubic-bezier(.54, 1.5, .38, 1.11);\n            transition-timing-function:cubic-bezier(.54, 1.5, .38, 1.11)\n}\n\n.tippy-tooltip[data-inertia][data-state=hidden]{\n    -webkit-transition-timing-function:ease;\n            transition-timing-function:ease\n}\n\n.tippy-arrow,\n.tippy-roundarrow{\n    position:absolute;\n    width:0;\n    height:0\n}\n\n.tippy-roundarrow{\n    width:18px;\n    height:7px;\n    fill:#333;\n    pointer-events:none\n}\n\n.tippy-backdrop{\n    position:absolute;\n    background-color:#333;\n    border-radius:50%;\n    width:calc(110% + 2rem);\n    left:50%;\n    top:50%;\n    z-index:-1;\n    -webkit-transition:all cubic-bezier(.46, .1, .52, .98);\n    transition:all cubic-bezier(.46, .1, .52, .98);\n    -webkit-backface-visibility:hidden;\n    backface-visibility:hidden\n}\n\n.tippy-backdrop:after{\n    content:"";\n    float:left;\n    padding-top:100%\n}\n\n.tippy-backdrop+.tippy-content{\n    -webkit-transition-property:opacity;\n    transition-property:opacity;\n    will-change:opacity\n}\n\n.tippy-backdrop+.tippy-content[data-state=visible]{\n    opacity:1\n}\n\n.tippy-backdrop+.tippy-content[data-state=hidden]{\n    opacity:0\n}\n\n.tippy-tooltip.light-theme{\n    color:#26323d;\n    -webkit-box-shadow:0px 0px 6px 0px rgba(220, 222, 229, 1);\n            box-shadow:0px 0px 6px 0px rgba(220, 222, 229, 1);\n    background-color:#fff;\n}\n\n.tippy-tooltip.light-theme:before{\n    content:\'\';\n    position:absolute;\n    top:0;\n    right:0;\n    bottom:0;\n    left:0;\n    z-index:-1;\n    border-radius:inherit;\n    background:inherit;\n}\n\n.tippy-tooltip.light-theme .tippy-arrow{\n    z-index:-2;\n    width:11px;\n    height:11px;\n    border:none !important;\n    -webkit-box-shadow:inherit;\n            box-shadow:inherit;\n    background:inherit;\n    -webkit-transform-origin:center center;\n            transform-origin:center center;\n    -webkit-transform:rotateZ(45deg);\n            transform:rotateZ(45deg);\n}\n\n.tippy-tooltip.light-theme[x-placement^=top] .tippy-arrow{\n    bottom:-5px;\n}\n\n.tippy-tooltip.light-theme[x-placement^=bottom] .tippy-arrow{\n    top:-5px;\n}\n\n.tippy-tooltip.light-theme[x-placement^=left] .tippy-arrow{\n    right:-5px;\n}\n\n.tippy-tooltip.light-theme[x-placement^=right] .tippy-arrow{\n    left:-5px;\n}\n\n.tippy-tooltip.light-theme .tippy-backdrop{\n    background-color:#fff\n}\n\n.tippy-tooltip.light-theme .tippy-roundarrow{\n    fill:#fff\n}\n\n.tippy-tooltip.light-theme[data-animatefill]{\n    background-color:transparent\n}\n\n.tippy-tooltip.light-border-theme{\n    color:#26323d;\n    -webkit-box-shadow:0px 0px 6px 0px rgba(220, 222, 229, 1);\n            box-shadow:0px 0px 6px 0px rgba(220, 222, 229, 1);\n    background-color:#fff;\n    border:1px solid #dcdee5;\n}\n\n.tippy-tooltip.light-border-theme:before{\n    content:\'\';\n    position:absolute;\n    top:0;\n    right:0;\n    bottom:0;\n    left:0;\n    z-index:-1;\n    border-radius:inherit;\n    background:inherit;\n}\n\n.tippy-tooltip.light-border-theme .tippy-arrow{\n    z-index:-2;\n    width:11px;\n    height:11px;\n    border:1px solid #dcdee5;\n    -webkit-box-shadow:inherit;\n            box-shadow:inherit;\n    background:inherit;\n    -webkit-transform-origin:center center;\n            transform-origin:center center;\n    -webkit-transform:rotateZ(45deg);\n            transform:rotateZ(45deg);\n}\n\n.tippy-tooltip.light-border-theme[x-placement^=top] .tippy-arrow{\n    bottom:-5px;\n}\n\n.tippy-tooltip.light-border-theme[x-placement^=bottom] .tippy-arrow{\n    top:-5px;\n}\n\n.tippy-tooltip.light-border-theme[x-placement^=left] .tippy-arrow{\n    right:-5px;\n}\n\n.tippy-tooltip.light-border-theme[x-placement^=right] .tippy-arrow{\n    left:-5px;\n}\n\n.tippy-tooltip.light-border-theme .tippy-backdrop{\n    background-color:#fff\n}\n\n.tippy-tooltip.light-border-theme .tippy-roundarrow{\n    fill:#fff\n}\n\n.tippy-tooltip.light-border-theme[data-animatefill]{\n    background-color:transparent\n}\n'], sourceRoot: '' }]);
        // Exports
        /* harmony default export */ const __WEBPACK_DEFAULT_EXPORT__ = (___CSS_LOADER_EXPORT___);
        /***/ }),

      /***/ './node_modules/css-loader/dist/cjs.js??clonedRuleSet-4[0].rules[0].use[1]!./node_modules/bk-magic-vue/lib/ui/search-select-menu.css':
      /*! *******************************************************************************************************************************************!*\
  !*** ./node_modules/css-loader/dist/cjs.js??clonedRuleSet-4[0].rules[0].use[1]!./node_modules/bk-magic-vue/lib/ui/search-select-menu.css ***!
  \*******************************************************************************************************************************************/
      /***/ ((module, __webpack_exports__, __webpack_require__) => {
        'use strict';
        __webpack_require__.r(__webpack_exports__);
        /* harmony export */ __webpack_require__.d(__webpack_exports__, {
          /* harmony export */   default: () => (__WEBPACK_DEFAULT_EXPORT__)
          /* harmony export */ });
        /* harmony import */ const _css_loader_dist_runtime_cssWithMappingToString_js__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! ../../../css-loader/dist/runtime/cssWithMappingToString.js */ './node_modules/css-loader/dist/runtime/cssWithMappingToString.js');
        /* harmony import */ const _css_loader_dist_runtime_cssWithMappingToString_js__WEBPACK_IMPORTED_MODULE_0___default = /* #__PURE__*/__webpack_require__.n(_css_loader_dist_runtime_cssWithMappingToString_js__WEBPACK_IMPORTED_MODULE_0__);
        /* harmony import */ const _css_loader_dist_runtime_api_js__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! ../../../css-loader/dist/runtime/api.js */ './node_modules/css-loader/dist/runtime/api.js');
        /* harmony import */ const _css_loader_dist_runtime_api_js__WEBPACK_IMPORTED_MODULE_1___default = /* #__PURE__*/__webpack_require__.n(_css_loader_dist_runtime_api_js__WEBPACK_IMPORTED_MODULE_1__);
        // Imports


        const ___CSS_LOADER_EXPORT___ = _css_loader_dist_runtime_api_js__WEBPACK_IMPORTED_MODULE_1___default()((_css_loader_dist_runtime_cssWithMappingToString_js__WEBPACK_IMPORTED_MODULE_0___default()));
        // Module
        ___CSS_LOADER_EXPORT___.push([module.id, '.bk-search-list{\n    font-size:12px;\n    position:relative;\n    max-height:280px;\n    min-height:32px;\n    min-width:230px;\n    line-height:32px;\n    color:#63656e;\n    margin:-0.3rem -0.6rem;\n    outline:none;\n    resize:none;\n    pointer-events:all;\n    border:1px solid #dcdee5;\n    border-radius:2px;\n}\n\n.bk-search-list-condition{\n        border-bottom:1px solid #dcdee5;\n        padding:0 10px 0 16px;\n        pointer-events:auto\n    }\n\n.bk-search-list-condition:hover{\n            cursor:pointer;\n            color:#3a84ff;\n            background-color:rgba(234, 243, 255, 0.7);\n        }\n\n.bk-search-list-menu{\n        margin:0;\n        display:-webkit-box;\n        display:-ms-flexbox;\n        display:flex;\n        -webkit-box-orient:vertical;\n        -webkit-box-direction:normal;\n            -ms-flex-direction:column;\n                flex-direction:column;\n        pointer-events:all;\n        max-height:200px;\n        overflow-x:hidden;\n        overflow-y:auto;\n        padding:0\n    }\n\n.bk-search-list-menu::-webkit-scrollbar{\n        width:6px;\n        height:6px;\n    }\n\n.bk-search-list-menu::-webkit-scrollbar-thumb{\n        min-height:24px;\n        border-radius:3px;\n        background-color:#dcdee5;\n    }\n\n.bk-search-list-menu .is-group{\n            border-bottom:1px solid #dcdee5;\n        }\n\n.bk-search-list-menu-item{\n            -webkit-box-flex:1;\n                -ms-flex:1 0 32px;\n                    flex:1 0 32px;\n            display:-webkit-box;\n            display:-ms-flexbox;\n            display:flex;\n            -webkit-box-align:center;\n                -ms-flex-align:center;\n                    align-items:center;\n            -webkit-box-pack:start;\n                -ms-flex-pack:start;\n                    justify-content:flex-start;\n            pointer-events:auto;\n            text-overflow:ellipsis;\n            overflow:hidden;\n            white-space:nowrap;\n            padding:0 10px 0 16px\n        }\n\n.bk-search-list-menu-item.is-disabled{\n                color:#c4c6cc;\n                cursor:not-allowed;\n            }\n\n.bk-search-list-menu-item .item-name{\n                -webkit-box-flex:1;\n                    -ms-flex:1;\n                        flex:1;\n                line-height:32px;\n            }\n\n.bk-search-list-menu-item .item-name-filter{\n                    color:#313238;\n                    display:inline-block;\n                }\n\n.bk-search-list-menu-item .item-icon{\n                color:#3a84ff;\n                font-size:16px;\n                font-weight:bold;\n            }\n\n.bk-search-list-menu-item.is-hover, .bk-search-list-menu-item:not(.is-disabled):hover{\n                cursor:pointer;\n                color:#3a84ff;\n                background-color:rgba(234, 243, 255, 0.7);\n            }\n\n.bk-search-list-loading{\n        padding:0 16px;\n        text-align:center;\n        line-height:32px;\n    }\n\n.bk-search-list-error{\n        padding:0 10px 0 16px;\n        line-height:32px;\n        font-weight:bold;\n    }\n\n.bk-search-list-footer{\n        display:-webkit-box;\n        display:-ms-flexbox;\n        display:flex;\n        line-height:32px;\n        -webkit-box-orient:horizontal;\n        -webkit-box-direction:normal;\n            -ms-flex-direction:row;\n                flex-direction:row;\n        -ms-flex-pack:distribute;\n            justify-content:space-around;\n        -webkit-box-align:center;\n            -ms-flex-align:center;\n                align-items:center;\n        pointer-events:auto;\n    }\n\n.bk-search-list-footer .footer-btn{\n            -webkit-box-flex:1;\n                -ms-flex:1;\n                    flex:1;\n            text-align:center;\n            border-top:1px solid #dcdee5;\n            pointer-events:auto\n        }\n\n.bk-search-list-footer .footer-btn:hover{\n                cursor:pointer;\n                color:#3a84ff;\n                background-color:rgba(234, 243, 255, 0.7);\n            }\n\n.bk-search-list-footer .footer-btn:first-child{\n                border-right:1px solid #dcdee5;\n            }\n\n.bk-search-list .search-menu-wrap{\n        padding:6px 0;\n    }\n\n.tippy-tooltip.bk-search-select-theme-theme{\n        -webkit-box-shadow:0 3px 9px 0 rgba(0, 0, 0, .1);\n                box-shadow:0 3px 9px 0 rgba(0, 0, 0, .1);\n        border-radius:2px;\n    }\n', '', { version: 3, sources: ['webpack://./node_modules/bk-magic-vue/lib/ui/search-select-menu.css'], names: [], mappings: 'AAAA;IACI,cAAc;IACd,iBAAiB;IACjB,gBAAgB;IAChB,eAAe;IACf,eAAe;IACf,gBAAgB;IAChB,aAAa;IACb,sBAAsB;IACtB,YAAY;IACZ,WAAW;IACX,kBAAkB;IAClB,wBAAwB;IACxB,iBAAiB;AACrB;;AAEA;QACQ,+BAA+B;QAC/B,qBAAqB;QACrB;IACJ;;AAEJ;YACY,cAAc;YACd,aAAa;YACb,yCAAyC;QAC7C;;AAER;QACQ,QAAQ;QACR,mBAAmB;QACnB,mBAAmB;QACnB,YAAY;QACZ,2BAA2B;QAC3B,4BAA4B;YACxB,yBAAyB;gBACrB,qBAAqB;QAC7B,kBAAkB;QAClB,gBAAgB;QAChB,iBAAiB;QACjB,eAAe;QACf;IACJ;;AAEJ;QACQ,SAAS;QACT,UAAU;IACd;;AAEJ;QACQ,eAAe;QACf,iBAAiB;QACjB,wBAAwB;IAC5B;;AAEJ;YACY,+BAA+B;QACnC;;AAER;YACY,kBAAkB;gBACd,iBAAiB;oBACb,aAAa;YACrB,mBAAmB;YACnB,mBAAmB;YACnB,YAAY;YACZ,wBAAwB;gBACpB,qBAAqB;oBACjB,kBAAkB;YAC1B,sBAAsB;gBAClB,mBAAmB;oBACf,0BAA0B;YAClC,mBAAmB;YACnB,sBAAsB;YACtB,eAAe;YACf,kBAAkB;YAClB;QACJ;;AAER;gBACgB,aAAa;gBACb,kBAAkB;YACtB;;AAEZ;gBACgB,kBAAkB;oBACd,UAAU;wBACN,MAAM;gBACd,gBAAgB;YACpB;;AAEZ;oBACoB,aAAa;oBACb,oBAAoB;gBACxB;;AAEhB;gBACgB,aAAa;gBACb,cAAc;gBACd,gBAAgB;YACpB;;AAEZ;gBACgB,cAAc;gBACd,aAAa;gBACb,yCAAyC;YAC7C;;AAEZ;QACQ,cAAc;QACd,iBAAiB;QACjB,gBAAgB;IACpB;;AAEJ;QACQ,qBAAqB;QACrB,gBAAgB;QAChB,gBAAgB;IACpB;;AAEJ;QACQ,mBAAmB;QACnB,mBAAmB;QACnB,YAAY;QACZ,gBAAgB;QAChB,6BAA6B;QAC7B,4BAA4B;YACxB,sBAAsB;gBAClB,kBAAkB;QAC1B,wBAAwB;YACpB,4BAA4B;QAChC,wBAAwB;YACpB,qBAAqB;gBACjB,kBAAkB;QAC1B,mBAAmB;IACvB;;AAEJ;YACY,kBAAkB;gBACd,UAAU;oBACN,MAAM;YACd,iBAAiB;YACjB,4BAA4B;YAC5B;QACJ;;AAER;gBACgB,cAAc;gBACd,aAAa;gBACb,yCAAyC;YAC7C;;AAEZ;gBACgB,8BAA8B;YAClC;;AAEZ;QACQ,aAAa;IACjB;;AAEJ;QACQ,gDAAgD;gBACxC,wCAAwC;QAChD,iBAAiB;IACrB', sourcesContent: ['.bk-search-list{\n    font-size:12px;\n    position:relative;\n    max-height:280px;\n    min-height:32px;\n    min-width:230px;\n    line-height:32px;\n    color:#63656e;\n    margin:-0.3rem -0.6rem;\n    outline:none;\n    resize:none;\n    pointer-events:all;\n    border:1px solid #dcdee5;\n    border-radius:2px;\n}\n\n.bk-search-list-condition{\n        border-bottom:1px solid #dcdee5;\n        padding:0 10px 0 16px;\n        pointer-events:auto\n    }\n\n.bk-search-list-condition:hover{\n            cursor:pointer;\n            color:#3a84ff;\n            background-color:rgba(234, 243, 255, 0.7);\n        }\n\n.bk-search-list-menu{\n        margin:0;\n        display:-webkit-box;\n        display:-ms-flexbox;\n        display:flex;\n        -webkit-box-orient:vertical;\n        -webkit-box-direction:normal;\n            -ms-flex-direction:column;\n                flex-direction:column;\n        pointer-events:all;\n        max-height:200px;\n        overflow-x:hidden;\n        overflow-y:auto;\n        padding:0\n    }\n\n.bk-search-list-menu::-webkit-scrollbar{\n        width:6px;\n        height:6px;\n    }\n\n.bk-search-list-menu::-webkit-scrollbar-thumb{\n        min-height:24px;\n        border-radius:3px;\n        background-color:#dcdee5;\n    }\n\n.bk-search-list-menu .is-group{\n            border-bottom:1px solid #dcdee5;\n        }\n\n.bk-search-list-menu-item{\n            -webkit-box-flex:1;\n                -ms-flex:1 0 32px;\n                    flex:1 0 32px;\n            display:-webkit-box;\n            display:-ms-flexbox;\n            display:flex;\n            -webkit-box-align:center;\n                -ms-flex-align:center;\n                    align-items:center;\n            -webkit-box-pack:start;\n                -ms-flex-pack:start;\n                    justify-content:flex-start;\n            pointer-events:auto;\n            text-overflow:ellipsis;\n            overflow:hidden;\n            white-space:nowrap;\n            padding:0 10px 0 16px\n        }\n\n.bk-search-list-menu-item.is-disabled{\n                color:#c4c6cc;\n                cursor:not-allowed;\n            }\n\n.bk-search-list-menu-item .item-name{\n                -webkit-box-flex:1;\n                    -ms-flex:1;\n                        flex:1;\n                line-height:32px;\n            }\n\n.bk-search-list-menu-item .item-name-filter{\n                    color:#313238;\n                    display:inline-block;\n                }\n\n.bk-search-list-menu-item .item-icon{\n                color:#3a84ff;\n                font-size:16px;\n                font-weight:bold;\n            }\n\n.bk-search-list-menu-item.is-hover, .bk-search-list-menu-item:not(.is-disabled):hover{\n                cursor:pointer;\n                color:#3a84ff;\n                background-color:rgba(234, 243, 255, 0.7);\n            }\n\n.bk-search-list-loading{\n        padding:0 16px;\n        text-align:center;\n        line-height:32px;\n    }\n\n.bk-search-list-error{\n        padding:0 10px 0 16px;\n        line-height:32px;\n        font-weight:bold;\n    }\n\n.bk-search-list-footer{\n        display:-webkit-box;\n        display:-ms-flexbox;\n        display:flex;\n        line-height:32px;\n        -webkit-box-orient:horizontal;\n        -webkit-box-direction:normal;\n            -ms-flex-direction:row;\n                flex-direction:row;\n        -ms-flex-pack:distribute;\n            justify-content:space-around;\n        -webkit-box-align:center;\n            -ms-flex-align:center;\n                align-items:center;\n        pointer-events:auto;\n    }\n\n.bk-search-list-footer .footer-btn{\n            -webkit-box-flex:1;\n                -ms-flex:1;\n                    flex:1;\n            text-align:center;\n            border-top:1px solid #dcdee5;\n            pointer-events:auto\n        }\n\n.bk-search-list-footer .footer-btn:hover{\n                cursor:pointer;\n                color:#3a84ff;\n                background-color:rgba(234, 243, 255, 0.7);\n            }\n\n.bk-search-list-footer .footer-btn:first-child{\n                border-right:1px solid #dcdee5;\n            }\n\n.bk-search-list .search-menu-wrap{\n        padding:6px 0;\n    }\n\n.tippy-tooltip.bk-search-select-theme-theme{\n        -webkit-box-shadow:0 3px 9px 0 rgba(0, 0, 0, .1);\n                box-shadow:0 3px 9px 0 rgba(0, 0, 0, .1);\n        border-radius:2px;\n    }\n'], sourceRoot: '' }]);
        // Exports
        /* harmony default export */ const __WEBPACK_DEFAULT_EXPORT__ = (___CSS_LOADER_EXPORT___);
        /***/ }),

      /***/ './node_modules/css-loader/dist/cjs.js??clonedRuleSet-4[0].rules[0].use[1]!./node_modules/bk-magic-vue/lib/ui/search-select.css':
      /*! **************************************************************************************************************************************!*\
  !*** ./node_modules/css-loader/dist/cjs.js??clonedRuleSet-4[0].rules[0].use[1]!./node_modules/bk-magic-vue/lib/ui/search-select.css ***!
  \**************************************************************************************************************************************/
      /***/ ((module, __webpack_exports__, __webpack_require__) => {
        'use strict';
        __webpack_require__.r(__webpack_exports__);
        /* harmony export */ __webpack_require__.d(__webpack_exports__, {
          /* harmony export */   default: () => (__WEBPACK_DEFAULT_EXPORT__)
          /* harmony export */ });
        /* harmony import */ const _css_loader_dist_runtime_cssWithMappingToString_js__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! ../../../css-loader/dist/runtime/cssWithMappingToString.js */ './node_modules/css-loader/dist/runtime/cssWithMappingToString.js');
        /* harmony import */ const _css_loader_dist_runtime_cssWithMappingToString_js__WEBPACK_IMPORTED_MODULE_0___default = /* #__PURE__*/__webpack_require__.n(_css_loader_dist_runtime_cssWithMappingToString_js__WEBPACK_IMPORTED_MODULE_0__);
        /* harmony import */ const _css_loader_dist_runtime_api_js__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! ../../../css-loader/dist/runtime/api.js */ './node_modules/css-loader/dist/runtime/api.js');
        /* harmony import */ const _css_loader_dist_runtime_api_js__WEBPACK_IMPORTED_MODULE_1___default = /* #__PURE__*/__webpack_require__.n(_css_loader_dist_runtime_api_js__WEBPACK_IMPORTED_MODULE_1__);
        // Imports


        const ___CSS_LOADER_EXPORT___ = _css_loader_dist_runtime_api_js__WEBPACK_IMPORTED_MODULE_1___default()((_css_loader_dist_runtime_cssWithMappingToString_js__WEBPACK_IMPORTED_MODULE_0___default()));
        // Module
        ___CSS_LOADER_EXPORT___.push([module.id, '.search-select-wrap{\n    position:relative;\n    overflow:inherit;\n    z-index:9;\n    height:32px;\n}\n\n.search-select-wrap .bk-search-select{\n        display:-webkit-box;\n        display:-ms-flexbox;\n        display:flex;\n        -webkit-box-orient:horizontal;\n        -webkit-box-direction:normal;\n            -ms-flex-direction:row;\n                flex-direction:row;\n        -webkit-box-align:center;\n            -ms-flex-align:center;\n                align-items:center;\n        font-size:12px;\n        min-height:30px;\n        -webkit-box-sizing:border-box;\n                box-sizing:border-box;\n        position:relative;\n        border:1px solid #c4c6cc;\n        border-radius:2px;\n        outline:none;\n        resize:none;\n        -webkit-transition:border 0.2s linear;\n        transition:border 0.2s linear;\n        overflow:hidden;\n        color:#63656e;\n        -ms-flex-wrap:wrap;\n            flex-wrap:wrap\n    }\n\n.search-select-wrap .bk-search-select.is-focus{\n            border-color:#3c96ff !important;\n            background:#fff !important;\n            color:#3c96ff;\n            overflow:auto;\n        }\n\n.search-select-wrap .bk-search-select .search-prefix{\n            -webkit-box-flex:0;\n                -ms-flex:0 0 auto;\n                    flex:0 0 auto;\n            display:-webkit-box;\n            display:-ms-flexbox;\n            display:flex;\n            -webkit-box-align:center;\n                -ms-flex-align:center;\n                    align-items:center;\n            height:100%;\n        }\n\n.search-select-wrap .bk-search-select .search-input{\n            -webkit-box-flex:1;\n                -ms-flex:1;\n                    flex:1;\n            position:relative;\n            padding:0 2px;\n            text-align:left;\n            overflow:visible;\n            display:-webkit-box;\n            display:-ms-flexbox;\n            display:flex;\n            -ms-flex-wrap:wrap;\n                flex-wrap:wrap;\n            -webkit-box-align:center;\n                -ms-flex-align:center;\n                    align-items:center;\n            min-height:26px;\n            margin-top:4px;\n            -webkit-transition:max-height .3s cubic-bezier(0.4, 0, 0.2, 1);\n            transition:max-height .3s cubic-bezier(0.4, 0, 0.2, 1);\n        }\n\n.search-select-wrap .bk-search-select .search-input-chip{\n                -webkit-box-flex:0;\n                    -ms-flex:0 0 auto;\n                        flex:0 0 auto;\n                max-width:99%;\n                display:inline-block;\n                -ms-flex-item-align:center;\n                    -ms-grid-row-align:center;\n                    align-self:center;\n                color:#63656e;\n                margin:0 0 4px 6px;\n                padding-left:8px;\n                position:relative;\n                background:#f0f1f5;\n                border-radius:2px;\n                line-height:22px\n            }\n\n.search-select-wrap .bk-search-select .search-input-chip.hidden-chip{\n                    visibility:hidden\n                }\n\n.search-select-wrap .bk-search-select .search-input-chip:hover{\n                    background:#dcdee5;\n                }\n\n.search-select-wrap .bk-search-select .search-input-chip:hover .chip-clear{\n                        color:#63656e;\n                    }\n\n.search-select-wrap .bk-search-select .search-input-chip .chip-name{\n                    display:inline-block;\n                    margin-right:20px;\n                    word-break:break-all;\n                }\n\n.search-select-wrap .bk-search-select .search-input-chip .chip-clear{\n                    color:#979ba5;\n                    position:absolute;\n                    right:3px;\n                    line-height:normal;\n                    display:inline-block;\n                    top:4px;\n                    text-align:center;\n                    cursor:pointer;\n                    font-size:14px;\n                }\n\n.search-select-wrap .bk-search-select .search-input-input{\n                position:relative;\n                padding:0 10px;\n                color:#63656e;\n                -webkit-box-flex:1;\n                    -ms-flex:1 1 auto;\n                        flex:1 1 auto;\n                border:none;\n                height:100%;\n                min-width:40px;\n                display:-webkit-box;\n                display:-ms-flexbox;\n                display:flex;\n                -webkit-box-align:center;\n                    -ms-flex-align:center;\n                        align-items:center;\n                margin-top:-4px;\n            }\n\n.search-select-wrap .bk-search-select .search-input-input .div-input{\n                    -webkit-box-flex:1;\n                        -ms-flex:1 1 auto;\n                            flex:1 1 auto;\n                    line-height:20px;\n                    padding:5px 0;\n                    height:30px;\n                    word-break:break-all\n                }\n\n.search-select-wrap .bk-search-select .search-input-input .div-input:focus{\n                        outline:none;\n                    }\n\n.search-select-wrap .bk-search-select .search-input-input .input-before:before{\n                        content:attr(data-placeholder);\n                        color:#c4c6cc;\n                        padding-left:2px;\n                    }\n\n.search-select-wrap .bk-search-select .search-input-input .input-after:after{\n                        content:attr(data-tips);\n                        color:#c4c6cc;\n                        padding-left:2px;\n                    }\n\n.search-select-wrap .bk-search-select .search-select-wrap .bk-search-select .search-nextfix{\n    -webkit-box-flex:0;\n    -ms-flex:0 0 auto;\n    flex:0 0 auto;\n    display:-webkit-box;\n    display:-ms-flexbox;\n    display:flex;\n    -webkit-box-align:center;\n    -ms-flex-align:center;\n    align-items:center;\n    height:100%;\n}\n\n.search-select-wrap .bk-search-select .search-nextfix{\n    color:#c4c6cc;\n    display:-webkit-box;\n    display:-ms-flexbox;\n    display:flex;\n    -webkit-box-align:center;\n    -ms-flex-align:center;\n    align-items:center;\n}\n\n.search-select-wrap .bk-search-select .search-nextfix .search-clear{\n                color:#c4c6cc;\n                font-size:14px;\n                width:12px;\n                height:12px;\n                margin-right:6px\n            }\n\n.search-select-wrap .bk-search-select .search-nextfix .search-clear:hover{\n                    cursor:pointer;\n                    color:#979ba5;\n                }\n\n.search-select-wrap .bk-search-select .search-nextfix .search-nextfix-icon{\n                margin-right:8px;\n                font-size:16px;\n                -webkit-transition:color 0.2s linear;\n                transition:color 0.2s linear\n            }\n\n.search-select-wrap .bk-search-select .search-nextfix .search-nextfix-icon.is-focus{\n                    border-color:#3c96ff !important;\n                    background:#fff !important;\n                    color:#3c96ff;\n                }\n\n.search-select-wrap .bk-search-select::-webkit-scrollbar{\n            width:3px;\n            height:5px;\n        }\n\n.search-select-wrap .bk-search-select::-webkit-scrollbar-thumb{\n            border-radius:20px;\n            background:#e6e9ea;\n            -webkit-box-shadow:inset 0 0 6px rgba(204, 204, 204, 0.3);\n                    box-shadow:inset 0 0 6px rgba(204, 204, 204, 0.3);\n        }\n\n.search-select-wrap .bk-select-tips{\n        color:#ea3636;\n        font-size:12px;\n        margin-top:5px;\n        display:-webkit-box;\n        display:-ms-flexbox;\n        display:flex;\n        -webkit-box-align:center;\n            -ms-flex-align:center;\n                align-items:center;\n        line-height:16px;\n    }\n\n.search-select-wrap .bk-select-tips .select-tips{\n            font-size:16px;\n            margin-right:5px;\n            width:16px;\n            height:16px;\n        }\n', '', { version: 3, sources: ['webpack://./node_modules/bk-magic-vue/lib/ui/search-select.css'], names: [], mappings: 'AAAA;IACI,iBAAiB;IACjB,gBAAgB;IAChB,SAAS;IACT,WAAW;AACf;;AAEA;QACQ,mBAAmB;QACnB,mBAAmB;QACnB,YAAY;QACZ,6BAA6B;QAC7B,4BAA4B;YACxB,sBAAsB;gBAClB,kBAAkB;QAC1B,wBAAwB;YACpB,qBAAqB;gBACjB,kBAAkB;QAC1B,cAAc;QACd,eAAe;QACf,6BAA6B;gBACrB,qBAAqB;QAC7B,iBAAiB;QACjB,wBAAwB;QACxB,iBAAiB;QACjB,YAAY;QACZ,WAAW;QACX,qCAAqC;QACrC,6BAA6B;QAC7B,eAAe;QACf,aAAa;QACb,kBAAkB;YACd;IACR;;AAEJ;YACY,+BAA+B;YAC/B,0BAA0B;YAC1B,aAAa;YACb,aAAa;QACjB;;AAER;YACY,kBAAkB;gBACd,iBAAiB;oBACb,aAAa;YACrB,mBAAmB;YACnB,mBAAmB;YACnB,YAAY;YACZ,wBAAwB;gBACpB,qBAAqB;oBACjB,kBAAkB;YAC1B,WAAW;QACf;;AAER;YACY,kBAAkB;gBACd,UAAU;oBACN,MAAM;YACd,iBAAiB;YACjB,aAAa;YACb,eAAe;YACf,gBAAgB;YAChB,mBAAmB;YACnB,mBAAmB;YACnB,YAAY;YACZ,kBAAkB;gBACd,cAAc;YAClB,wBAAwB;gBACpB,qBAAqB;oBACjB,kBAAkB;YAC1B,eAAe;YACf,cAAc;YACd,8DAA8D;YAC9D,sDAAsD;QAC1D;;AAER;gBACgB,kBAAkB;oBACd,iBAAiB;wBACb,aAAa;gBACrB,aAAa;gBACb,oBAAoB;gBACpB,0BAA0B;oBACtB,yBAAyB;oBACzB,iBAAiB;gBACrB,aAAa;gBACb,kBAAkB;gBAClB,gBAAgB;gBAChB,iBAAiB;gBACjB,kBAAkB;gBAClB,iBAAiB;gBACjB;YACJ;;AAEZ;oBACoB;gBACJ;;AAEhB;oBACoB,kBAAkB;gBACtB;;AAEhB;wBACwB,aAAa;oBACjB;;AAEpB;oBACoB,oBAAoB;oBACpB,iBAAiB;oBACjB,oBAAoB;gBACxB;;AAEhB;oBACoB,aAAa;oBACb,iBAAiB;oBACjB,SAAS;oBACT,kBAAkB;oBAClB,oBAAoB;oBACpB,OAAO;oBACP,iBAAiB;oBACjB,cAAc;oBACd,cAAc;gBAClB;;AAEhB;gBACgB,iBAAiB;gBACjB,cAAc;gBACd,aAAa;gBACb,kBAAkB;oBACd,iBAAiB;wBACb,aAAa;gBACrB,WAAW;gBACX,WAAW;gBACX,cAAc;gBACd,mBAAmB;gBACnB,mBAAmB;gBACnB,YAAY;gBACZ,wBAAwB;oBACpB,qBAAqB;wBACjB,kBAAkB;gBAC1B,eAAe;YACnB;;AAEZ;oBACoB,kBAAkB;wBACd,iBAAiB;4BACb,aAAa;oBACrB,gBAAgB;oBAChB,aAAa;oBACb,WAAW;oBACX;gBACJ;;AAEhB;wBACwB,YAAY;oBAChB;;AAEpB;wBACwB,8BAA8B;wBAC9B,aAAa;wBACb,gBAAgB;oBACpB;;AAEpB;wBACwB,uBAAuB;wBACvB,aAAa;wBACb,gBAAgB;oBACpB;;AAEpB;IACI,kBAAkB;IAClB,iBAAiB;IACjB,aAAa;IACb,mBAAmB;IACnB,mBAAmB;IACnB,YAAY;IACZ,wBAAwB;IACxB,qBAAqB;IACrB,kBAAkB;IAClB,WAAW;AACf;;AAEA;IACI,aAAa;IACb,mBAAmB;IACnB,mBAAmB;IACnB,YAAY;IACZ,wBAAwB;IACxB,qBAAqB;IACrB,kBAAkB;AACtB;;AAEA;gBACgB,aAAa;gBACb,cAAc;gBACd,UAAU;gBACV,WAAW;gBACX;YACJ;;AAEZ;oBACoB,cAAc;oBACd,aAAa;gBACjB;;AAEhB;gBACgB,gBAAgB;gBAChB,cAAc;gBACd,oCAAoC;gBACpC;YACJ;;AAEZ;oBACoB,+BAA+B;oBAC/B,0BAA0B;oBAC1B,aAAa;gBACjB;;AAEhB;YACY,SAAS;YACT,UAAU;QACd;;AAER;YACY,kBAAkB;YAClB,kBAAkB;YAClB,yDAAyD;oBACjD,iDAAiD;QAC7D;;AAER;QACQ,aAAa;QACb,cAAc;QACd,cAAc;QACd,mBAAmB;QACnB,mBAAmB;QACnB,YAAY;QACZ,wBAAwB;YACpB,qBAAqB;gBACjB,kBAAkB;QAC1B,gBAAgB;IACpB;;AAEJ;YACY,cAAc;YACd,gBAAgB;YAChB,UAAU;YACV,WAAW;QACf', sourcesContent: ['.search-select-wrap{\n    position:relative;\n    overflow:inherit;\n    z-index:9;\n    height:32px;\n}\n\n.search-select-wrap .bk-search-select{\n        display:-webkit-box;\n        display:-ms-flexbox;\n        display:flex;\n        -webkit-box-orient:horizontal;\n        -webkit-box-direction:normal;\n            -ms-flex-direction:row;\n                flex-direction:row;\n        -webkit-box-align:center;\n            -ms-flex-align:center;\n                align-items:center;\n        font-size:12px;\n        min-height:30px;\n        -webkit-box-sizing:border-box;\n                box-sizing:border-box;\n        position:relative;\n        border:1px solid #c4c6cc;\n        border-radius:2px;\n        outline:none;\n        resize:none;\n        -webkit-transition:border 0.2s linear;\n        transition:border 0.2s linear;\n        overflow:hidden;\n        color:#63656e;\n        -ms-flex-wrap:wrap;\n            flex-wrap:wrap\n    }\n\n.search-select-wrap .bk-search-select.is-focus{\n            border-color:#3c96ff !important;\n            background:#fff !important;\n            color:#3c96ff;\n            overflow:auto;\n        }\n\n.search-select-wrap .bk-search-select .search-prefix{\n            -webkit-box-flex:0;\n                -ms-flex:0 0 auto;\n                    flex:0 0 auto;\n            display:-webkit-box;\n            display:-ms-flexbox;\n            display:flex;\n            -webkit-box-align:center;\n                -ms-flex-align:center;\n                    align-items:center;\n            height:100%;\n        }\n\n.search-select-wrap .bk-search-select .search-input{\n            -webkit-box-flex:1;\n                -ms-flex:1;\n                    flex:1;\n            position:relative;\n            padding:0 2px;\n            text-align:left;\n            overflow:visible;\n            display:-webkit-box;\n            display:-ms-flexbox;\n            display:flex;\n            -ms-flex-wrap:wrap;\n                flex-wrap:wrap;\n            -webkit-box-align:center;\n                -ms-flex-align:center;\n                    align-items:center;\n            min-height:26px;\n            margin-top:4px;\n            -webkit-transition:max-height .3s cubic-bezier(0.4, 0, 0.2, 1);\n            transition:max-height .3s cubic-bezier(0.4, 0, 0.2, 1);\n        }\n\n.search-select-wrap .bk-search-select .search-input-chip{\n                -webkit-box-flex:0;\n                    -ms-flex:0 0 auto;\n                        flex:0 0 auto;\n                max-width:99%;\n                display:inline-block;\n                -ms-flex-item-align:center;\n                    -ms-grid-row-align:center;\n                    align-self:center;\n                color:#63656e;\n                margin:0 0 4px 6px;\n                padding-left:8px;\n                position:relative;\n                background:#f0f1f5;\n                border-radius:2px;\n                line-height:22px\n            }\n\n.search-select-wrap .bk-search-select .search-input-chip.hidden-chip{\n                    visibility:hidden\n                }\n\n.search-select-wrap .bk-search-select .search-input-chip:hover{\n                    background:#dcdee5;\n                }\n\n.search-select-wrap .bk-search-select .search-input-chip:hover .chip-clear{\n                        color:#63656e;\n                    }\n\n.search-select-wrap .bk-search-select .search-input-chip .chip-name{\n                    display:inline-block;\n                    margin-right:20px;\n                    word-break:break-all;\n                }\n\n.search-select-wrap .bk-search-select .search-input-chip .chip-clear{\n                    color:#979ba5;\n                    position:absolute;\n                    right:3px;\n                    line-height:normal;\n                    display:inline-block;\n                    top:4px;\n                    text-align:center;\n                    cursor:pointer;\n                    font-size:14px;\n                }\n\n.search-select-wrap .bk-search-select .search-input-input{\n                position:relative;\n                padding:0 10px;\n                color:#63656e;\n                -webkit-box-flex:1;\n                    -ms-flex:1 1 auto;\n                        flex:1 1 auto;\n                border:none;\n                height:100%;\n                min-width:40px;\n                display:-webkit-box;\n                display:-ms-flexbox;\n                display:flex;\n                -webkit-box-align:center;\n                    -ms-flex-align:center;\n                        align-items:center;\n                margin-top:-4px;\n            }\n\n.search-select-wrap .bk-search-select .search-input-input .div-input{\n                    -webkit-box-flex:1;\n                        -ms-flex:1 1 auto;\n                            flex:1 1 auto;\n                    line-height:20px;\n                    padding:5px 0;\n                    height:30px;\n                    word-break:break-all\n                }\n\n.search-select-wrap .bk-search-select .search-input-input .div-input:focus{\n                        outline:none;\n                    }\n\n.search-select-wrap .bk-search-select .search-input-input .input-before:before{\n                        content:attr(data-placeholder);\n                        color:#c4c6cc;\n                        padding-left:2px;\n                    }\n\n.search-select-wrap .bk-search-select .search-input-input .input-after:after{\n                        content:attr(data-tips);\n                        color:#c4c6cc;\n                        padding-left:2px;\n                    }\n\n.search-select-wrap .bk-search-select .search-select-wrap .bk-search-select .search-nextfix{\n    -webkit-box-flex:0;\n    -ms-flex:0 0 auto;\n    flex:0 0 auto;\n    display:-webkit-box;\n    display:-ms-flexbox;\n    display:flex;\n    -webkit-box-align:center;\n    -ms-flex-align:center;\n    align-items:center;\n    height:100%;\n}\n\n.search-select-wrap .bk-search-select .search-nextfix{\n    color:#c4c6cc;\n    display:-webkit-box;\n    display:-ms-flexbox;\n    display:flex;\n    -webkit-box-align:center;\n    -ms-flex-align:center;\n    align-items:center;\n}\n\n.search-select-wrap .bk-search-select .search-nextfix .search-clear{\n                color:#c4c6cc;\n                font-size:14px;\n                width:12px;\n                height:12px;\n                margin-right:6px\n            }\n\n.search-select-wrap .bk-search-select .search-nextfix .search-clear:hover{\n                    cursor:pointer;\n                    color:#979ba5;\n                }\n\n.search-select-wrap .bk-search-select .search-nextfix .search-nextfix-icon{\n                margin-right:8px;\n                font-size:16px;\n                -webkit-transition:color 0.2s linear;\n                transition:color 0.2s linear\n            }\n\n.search-select-wrap .bk-search-select .search-nextfix .search-nextfix-icon.is-focus{\n                    border-color:#3c96ff !important;\n                    background:#fff !important;\n                    color:#3c96ff;\n                }\n\n.search-select-wrap .bk-search-select::-webkit-scrollbar{\n            width:3px;\n            height:5px;\n        }\n\n.search-select-wrap .bk-search-select::-webkit-scrollbar-thumb{\n            border-radius:20px;\n            background:#e6e9ea;\n            -webkit-box-shadow:inset 0 0 6px rgba(204, 204, 204, 0.3);\n                    box-shadow:inset 0 0 6px rgba(204, 204, 204, 0.3);\n        }\n\n.search-select-wrap .bk-select-tips{\n        color:#ea3636;\n        font-size:12px;\n        margin-top:5px;\n        display:-webkit-box;\n        display:-ms-flexbox;\n        display:flex;\n        -webkit-box-align:center;\n            -ms-flex-align:center;\n                align-items:center;\n        line-height:16px;\n    }\n\n.search-select-wrap .bk-select-tips .select-tips{\n            font-size:16px;\n            margin-right:5px;\n            width:16px;\n            height:16px;\n        }\n'], sourceRoot: '' }]);
        // Exports
        /* harmony default export */ const __WEBPACK_DEFAULT_EXPORT__ = (___CSS_LOADER_EXPORT___);
        /***/ }),

      /***/ './node_modules/css-loader/dist/runtime/api.js':
      /*! *****************************************************!*\
  !*** ./node_modules/css-loader/dist/runtime/api.js ***!
  \*****************************************************/
      /***/ ((module) => {
        'use strict';


        /*
  MIT License http://www.opensource.org/licenses/mit-license.php
  Author Tobias Koppers @sokra
*/
        // css base code, injected by the css-loader
        // eslint-disable-next-line func-names
        module.exports = function (cssWithMappingToString) {
          const list = []; // return the list of modules as css string

          list.toString = function toString() {
            return this.map((item) => {
              const content = cssWithMappingToString(item);

              if (item[2]) {
                return '@media '.concat(item[2], ' {').concat(content, '}');
              }

              return content;
            }).join('');
          }; // import a list of modules into the list
          // eslint-disable-next-line func-names


          list.i = function (modules, mediaQuery, dedupe) {
            if (typeof modules === 'string') {
              // eslint-disable-next-line no-param-reassign
              modules = [[null, modules, '']];
            }

            const alreadyImportedModules = {};

            if (dedupe) {
              for (let i = 0; i < this.length; i++) {
                // eslint-disable-next-line prefer-destructuring
                const id = this[i][0];

                if (id != null) {
                  alreadyImportedModules[id] = true;
                }
              }
            }

            for (let _i = 0; _i < modules.length; _i++) {
              const item = [].concat(modules[_i]);

              if (dedupe && alreadyImportedModules[item[0]]) {
                // eslint-disable-next-line no-continue
                continue;
              }

              if (mediaQuery) {
                if (!item[2]) {
                  item[2] = mediaQuery;
                } else {
                  item[2] = ''.concat(mediaQuery, ' and ').concat(item[2]);
                }
              }

              list.push(item);
            }
          };

          return list;
        };
        /***/ }),

      /***/ './node_modules/css-loader/dist/runtime/cssWithMappingToString.js':
      /*! ************************************************************************!*\
  !*** ./node_modules/css-loader/dist/runtime/cssWithMappingToString.js ***!
  \************************************************************************/
      /***/ ((module) => {
        'use strict';


        function _slicedToArray(arr, i) {
          return _arrayWithHoles(arr) || _iterableToArrayLimit(arr, i) || _unsupportedIterableToArray(arr, i) || _nonIterableRest();
        }

        function _nonIterableRest() {
          throw new TypeError('Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.');
        }

        function _unsupportedIterableToArray(o, minLen) {
          if (!o) return; if (typeof o === 'string') return _arrayLikeToArray(o, minLen); let n = Object.prototype.toString.call(o).slice(8, -1); if (n === 'Object' && o.constructor) n = o.constructor.name; if (n === 'Map' || n === 'Set') return Array.from(o); if (n === 'Arguments' || /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(n)) return _arrayLikeToArray(o, minLen);
        }

        function _arrayLikeToArray(arr, len) {
          if (len == null || len > arr.length) len = arr.length; for (var i = 0, arr2 = new Array(len); i < len; i++) {
            arr2[i] = arr[i];
          } return arr2;
        }

        function _iterableToArrayLimit(arr, i) {
          let _i = arr && (typeof Symbol !== 'undefined' && arr[Symbol.iterator] || arr['@@iterator']); if (_i == null) return; const _arr = []; let _n = true; let _d = false; let _s; let _e; try {
            for (_i = _i.call(arr); !(_n = (_s = _i.next()).done); _n = true) {
              _arr.push(_s.value); if (i && _arr.length === i) break;
            }
          } catch (err) {
            _d = true; _e = err;
          } finally {
            try {
              if (!_n && _i.return != null) _i.return();
            } finally {
              if (_d) throw _e;
            }
          } return _arr;
        }

        function _arrayWithHoles(arr) {
          if (Array.isArray(arr)) return arr;
        }

        module.exports = function cssWithMappingToString(item) {
          const _item = _slicedToArray(item, 4);
          const content = _item[1];
          const cssMapping = _item[3];

          if (!cssMapping) {
            return content;
          }

          if (typeof btoa === 'function') {
            // eslint-disable-next-line no-undef
            const base64 = btoa(unescape(encodeURIComponent(JSON.stringify(cssMapping))));
            const data = 'sourceMappingURL=data:application/json;charset=utf-8;base64,'.concat(base64);
            const sourceMapping = '/*# '.concat(data, ' */');
            const sourceURLs = cssMapping.sources.map(source => '/*# sourceURL='.concat(cssMapping.sourceRoot || '').concat(source, ' */'));
            return [content].concat(sourceURLs).concat([sourceMapping])
              .join('\n');
          }

          return [content].join('\n');
        };
        /***/ }),

      /***/ './node_modules/css-loader/dist/runtime/getUrl.js':
      /*! ********************************************************!*\
  !*** ./node_modules/css-loader/dist/runtime/getUrl.js ***!
  \********************************************************/
      /***/ ((module) => {
        'use strict';


        module.exports = function (url, options) {
          if (!options) {
            // eslint-disable-next-line no-param-reassign
            options = {};
          } // eslint-disable-next-line no-underscore-dangle, no-param-reassign


          url = url && url.__esModule ? url.default : url;

          if (typeof url !== 'string') {
            return url;
          } // If url is already wrapped in quotes, remove them


          if (/^['"].*['"]$/.test(url)) {
            // eslint-disable-next-line no-param-reassign
            url = url.slice(1, -1);
          }

          if (options.hash) {
            // eslint-disable-next-line no-param-reassign
            url += options.hash;
          } // Should url be wrapped?
          // See https://drafts.csswg.org/css-values-3/#urls


          if (/["'() \t\n]/.test(url) || options.needQuotes) {
            return '"'.concat(url.replace(/"/g, '\\"').replace(/\n/g, '\\n'), '"');
          }

          return url;
        };
        /***/ }),

      /***/ './node_modules/bk-magic-vue/lib/ui/fonts/iconcool.eot':
      /*! *************************************************************!*\
  !*** ./node_modules/bk-magic-vue/lib/ui/fonts/iconcool.eot ***!
  \*************************************************************/
      /***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {
        'use strict';
        __webpack_require__.r(__webpack_exports__);
        /* harmony export */ __webpack_require__.d(__webpack_exports__, {
          /* harmony export */   default: () => (__WEBPACK_DEFAULT_EXPORT__)
          /* harmony export */ });
        /* harmony default export */ const __WEBPACK_DEFAULT_EXPORT__ = (`${__webpack_require__.p}fonts/iconcool.eot`);
        /***/ }),

      /***/ './node_modules/bk-magic-vue/lib/ui/fonts/iconcool.ttf':
      /*! *************************************************************!*\
  !*** ./node_modules/bk-magic-vue/lib/ui/fonts/iconcool.ttf ***!
  \*************************************************************/
      /***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {
        'use strict';
        __webpack_require__.r(__webpack_exports__);
        /* harmony export */ __webpack_require__.d(__webpack_exports__, {
          /* harmony export */   default: () => (__WEBPACK_DEFAULT_EXPORT__)
          /* harmony export */ });
        /* harmony default export */ const __WEBPACK_DEFAULT_EXPORT__ = (`${__webpack_require__.p}fonts/iconcool.ttf`);
        /***/ }),

      /***/ './node_modules/bk-magic-vue/lib/ui/fonts/iconcool.woff':
      /*! **************************************************************!*\
  !*** ./node_modules/bk-magic-vue/lib/ui/fonts/iconcool.woff ***!
  \**************************************************************/
      /***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {
        'use strict';
        __webpack_require__.r(__webpack_exports__);
        /* harmony export */ __webpack_require__.d(__webpack_exports__, {
          /* harmony export */   default: () => (__WEBPACK_DEFAULT_EXPORT__)
          /* harmony export */ });
        /* harmony default export */ const __WEBPACK_DEFAULT_EXPORT__ = (`${__webpack_require__.p}fonts/iconcool.woff`);
        /***/ }),

      /***/ './node_modules/bk-magic-vue/lib/ui/fonts/iconcool.svg':
      /*! *************************************************************!*\
  !*** ./node_modules/bk-magic-vue/lib/ui/fonts/iconcool.svg ***!
  \*************************************************************/
      /***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {
        'use strict';
        __webpack_require__.r(__webpack_exports__);
        /* harmony export */ __webpack_require__.d(__webpack_exports__, {
          /* harmony export */   default: () => (__WEBPACK_DEFAULT_EXPORT__)
          /* harmony export */ });
        /* harmony default export */ const __WEBPACK_DEFAULT_EXPORT__ = ('data:image/svg+xml;base64,PD94bWwgdmVyc2lvbj0iMS4wIiBzdGFuZGFsb25lPSJubyI/PgogIDwhRE9DVFlQRSBzdmcgUFVCTElDICItLy9XM0MvL0RURCBTVkcgMS4xLy9FTiIgImh0dHA6Ly93d3cudzMub3JnL0dyYXBoaWNzL1NWRy8xLjEvRFREL3N2ZzExLmR0ZCIgPgogIDxzdmc+CiAgPG1ldGFkYXRhPgogIENyZWF0ZWQgYnkgZm9udC1jYXJyaWVyCiAgPC9tZXRhZGF0YT4KICA8ZGVmcz4KICA8Zm9udCBpZD0iaWNvbmZvbnQiIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiA+CiAgICA8Zm9udC1mYWNlCiAgICAgIAogICAgICBmb250LWZhbWlseT0iaWNvbmZvbnQiCiAgICAgIAogICAgICBmb250LXdlaWdodD0iNDAwIgogICAgICAKICAgICAgZm9udC1zdHJldGNoPSJub3JtYWwiCiAgICAgIAogICAgICB1bml0cy1wZXItZW09IjEwMjQiCiAgICAgIAogICAgICBhc2NlbnQ9IjgxMiIKICAgICAgCiAgICAgIGRlc2NlbnQ9Ii0yMTIiCiAgICAgIAogICAgLz4KICAgICAgPG1pc3NpbmctZ2x5cGggLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0ieCIgdW5pY29kZT0iJiN4Nzg7IiBob3Jpei1hZHYteD0iMTAwIgogICAgICAgIGQ9Ik0yMCAyMCBMNTAgMjAgTDUwIC0yMCBaIiAvPgogICAgICAKCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTEwMSIgdW5pY29kZT0iJiN4RTEwMTsiIGQ9Ik0yODggNDYwTDMzNiA1MDggNTEyIDMzMiA2ODggNTA4IDczNiA0NjAgNTEyIDIzNlpNMjg4IDI2OEwzMzYgMzE2IDUxMiAxNDAgNjg4IDMxNiA3MzYgMjY4IDUxMiA0NFoiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxMDIiIHVuaWNvZGU9IiYjeEUxMDI7IiBkPSJNNjk3LjYgNTMwLjRMNzQ1LjYgNDgyLjQgNTY5LjYgMzA2LjQgNzQ1LjYgMTMwLjQgNjk3LjYgODIuNCA0NzMuNiAzMDYuNCA2OTcuNiA1MzAuNFpNNTA1LjYgNTMwLjRMNTUzLjYgNDgyLjQgMzc3LjYgMzA2LjQgNTUzLjYgMTMwLjQgNTA1LjYgODIuNCAyODEuNiAzMDYuNCA1MDUuNiA1MzAuNFoiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxMDMiIHVuaWNvZGU9IiYjeEUxMDM7IiBkPSJNMzU4LjQgODIuNEwzMTAuNCAxMzAuNCA0ODYuNCAzMDYuNCAzMTAuNCA0ODIuNCAzNTguNCA1MzAuNCA1ODIuNCAzMDYuNCAzNTguNCA4Mi40Wk01NTAuNCA4Mi40TDUwMi40IDEzMC40IDY3OC40IDMwNi40IDUwMi40IDQ4Mi40IDU1MC40IDUzMC40IDc3NC40IDMwNi40IDU1MC40IDgyLjRaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMTA0IiB1bmljb2RlPSImI3hFMTA0OyIgZD0iTTczNiAxNDBMNjg4IDkyIDUxMiAyNjggMzM2IDkyIDI4OCAxNDAgNTEyIDM2NFpNNzM2IDMzMkw2ODggMjg0IDUxMiA0NjAgMzM2IDI4NCAyODggMzMyIDUxMiA1NTZaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMTA1IiB1bmljb2RlPSImI3hFMTA1OyIgZD0iTTM3NiAzMDhMNjAwIDUzMiA2NDggNDg0IDQ3MiAzMDggNjQ4IDEzMiA2MDAgODQgMzc2IDMwOFoiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxMDYiIHVuaWNvZGU9IiYjeEUxMDY7IiBkPSJNMjg4IDM2NEwzMzYgNDEyIDUxMiAyMzYgNjg4IDQxMiA3MzYgMzY0IDUxMiAxNDBaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMTA3IiB1bmljb2RlPSImI3hFMTA3OyIgZD0iTTQyNCA4NEwzNzYgMTMyIDU1MiAzMDggMzc2IDQ4NCA0MjQgNTMyIDY0OCAzMDggNDI0IDg0WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTEwOCIgdW5pY29kZT0iJiN4RTEwODsiIGQ9Ik01MTIgNDQ0TDczNiAyMjAgNjg4IDE3MiA1MTIgMzQ4IDMzNiAxNzIgMjg4IDIyMCA1MTIgNDQ0WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTEwOSIgdW5pY29kZT0iJiN4RTEwOTsiIGQ9Ik0zNTIuMjEzMy0yMTJIOTYuMDQyN0M0My4wMDgtMjEyIDAtMTY4Ljk5MiAwLTExNS45NTczVjE0MC4yMTMzQzAgMTkzLjI0OCA0My4wMDggMjM2LjI1NiA5Ni4wNDI3IDIzNi4yNTZIMzUyLjIxMzNDNDA1LjI0OCAyMzYuMjU2IDQ0OC4yNTYgMTkzLjI0OCA0NDguMjU2IDE0MC4yMTMzVi0xMTUuOTU3M0M0NDguMjU2LTE2OC45OTIgNDA1LjI0OC0yMTIgMzUyLjIxMzMtMjEyWk0zNTIuMjEzMyAzMDAuMzQxM0g5Ni4wNDI3QzQzLjAwOCAzMDAuMzQxMyAwIDM0My4zNDkzIDAgMzk2LjM4NFY2NTIuNTU0N0MwIDcwNS41ODkzIDQzLjAwOCA3NDguNTk3MyA5Ni4wNDI3IDc0OC41OTczSDM1Mi4yMTMzQzQwNS4yNDggNzQ4LjU5NzMgNDQ4LjI1NiA3MDUuNTg5MyA0NDguMjU2IDY1Mi41NTQ3VjM5Ni4zODRDNDQ4LjI1NiAzNDMuMzQ5MyA0MDUuMjQ4IDMwMC4zNDEzIDM1Mi4yMTMzIDMwMC4zNDEzWk04NjQuNTU0Ny0yMTJINjA4LjM4NEM1NTUuMzQ5My0yMTIgNTEyLjM0MTMtMTY4Ljk5MiA1MTIuMzQxMy0xMTUuOTU3M1YxNDAuMjEzM0M1MTIuMzQxMyAxOTMuMjQ4IDU1NS4zNDkzIDIzNi4yNTYgNjA4LjM4NCAyMzYuMjU2SDg2NC41NTQ3QzkxNy41ODkzIDIzNi4yNTYgOTYwLjU5NzMgMTkzLjI0OCA5NjAuNTk3MyAxNDAuMjEzM1YtMTE1Ljk1NzNDOTYwLjU5NzMtMTY4Ljk5MiA5MTcuNTg5My0yMTIgODY0LjU1NDctMjEyWk03NTIuNDY5MyAyNjguMjk4N0M3NTIuNDI2NyAyNjguMjk4NyA3NTIuMzQxMyAyNjguMjk4NyA3NTIuMjk4NyAyNjguMjk4NyA3MjUuODQ1MyAyNjguMjk4NyA3MDEuODY2NyAyNzkuMDUwNyA2ODQuNTg2NyAyOTYuNDU4N0w1MDguNDU4NyA0NzIuNTg2N0M0OTEuMDkzMyA0ODkuOTUyIDQ4MC4zODQgNTEzLjk3MzMgNDgwLjM4NCA1NDAuNDY5M1M0OTEuMTM2IDU5MC45ODY3IDUwOC40NTg3IDYwOC4zNTJMNjg0LjU4NjcgNzg0LjQ4QzcwMi4yNTA3IDgwMS4yNDggNzI2LjE0NCA4MTEuNTczMyA3NTIuNDY5MyA4MTEuNTczM1M4MDIuNjg4IDgwMS4yNDggODIwLjM5NDcgNzg0LjQzNzNMOTk2LjQ4IDYwOC4zNTJDMTAxMy44NDUzIDU5MC45ODY3IDEwMjQuNTU0NyA1NjYuOTY1MyAxMDI0LjU1NDcgNTQwLjQ2OTNTMTAxMy44MDI3IDQ4OS45NTIgOTk2LjQ4IDQ3Mi41ODY3TDgyMC4zNTIgMjk2LjQ1ODdDODAzLjA3MiAyNzkuMDUwNyA3NzkuMDkzMyAyNjguMjk4NyA3NTIuNjQgMjY4LjI5ODcgNzUyLjU5NzMgMjY4LjI5ODcgNzUyLjUxMiAyNjguMjk4NyA3NTIuNDY5MyAyNjguMjk4N1oiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxMEEiIHVuaWNvZGU9IiYjeEUxMEE7IiBkPSJNMzUyLjIxMzMtMjEySDk2LjA0MjdDNDMuMDA4LTIxMiAwLTE2OC45OTIgMC0xMTUuOTU3M1YxNDAuMjEzM0MwIDE5My4yNDggNDMuMDA4IDIzNi4yNTYgOTYuMDQyNyAyMzYuMjU2SDM1Mi4yMTMzQzQwNS4yNDggMjM2LjI1NiA0NDguMjU2IDE5My4yNDggNDQ4LjI1NiAxNDAuMjEzM1YtMTE1Ljk1NzNDNDQ4LjI1Ni0xNjguOTkyIDQwNS4yNDgtMjEyIDM1Mi4yMTMzLTIxMlpNOTYuMDQyNyAxNzIuMjU2Qzc4LjM3ODcgMTcyLjI1NiA2NC4wNDI3IDE1Ny45MiA2NC4wNDI3IDE0MC4yNTZWLTExNS45MTQ3QzY0LjA0MjctMTMzLjU3ODcgNzguMzc4Ny0xNDcuOTE0NyA5Ni4wNDI3LTE0Ny45MTQ3SDM1Mi4yMTMzQzM2OS44NzczLTE0Ny45MTQ3IDM4NC4yMTMzLTEzMy41Nzg3IDM4NC4yMTMzLTExNS45MTQ3VjE0MC4yNTZDMzg0LjIxMzMgMTU3LjkyIDM2OS44NzczIDE3Mi4yNTYgMzUyLjIxMzMgMTcyLjI1NlpNMzUyLjIxMzMgMzAwLjM0MTNIOTYuMDQyN0M0My4wMDggMzAwLjM0MTMgMCAzNDMuMzQ5MyAwIDM5Ni4zODRWNjUyLjU1NDdDMCA3MDUuNTg5MyA0My4wMDggNzQ4LjU5NzMgOTYuMDQyNyA3NDguNTk3M0gzNTIuMjEzM0M0MDUuMjQ4IDc0OC41OTczIDQ0OC4yNTYgNzA1LjU4OTMgNDQ4LjI1NiA2NTIuNTU0N1YzOTYuMzg0QzQ0OC4yNTYgMzQzLjM0OTMgNDA1LjI0OCAzMDAuMzQxMyAzNTIuMjEzMyAzMDAuMzQxM1pNOTYuMDQyNyA2ODQuNTU0N0M3OC4zNzg3IDY4NC41NTQ3IDY0LjA0MjcgNjcwLjIxODcgNjQuMDQyNyA2NTIuNTU0N1YzOTYuMzg0QzY0LjA0MjcgMzc4LjcyIDc4LjM3ODcgMzY0LjM4NCA5Ni4wNDI3IDM2NC4zODRIMzUyLjIxMzNDMzY5Ljg3NzMgMzY0LjM4NCAzODQuMjEzMyAzNzguNzIgMzg0LjIxMzMgMzk2LjM4NFY2NTIuNTU0N0MzODQuMjEzMyA2NzAuMjE4NyAzNjkuODc3MyA2ODQuNTU0NyAzNTIuMjEzMyA2ODQuNTU0N1pNODY0LjU1NDctMjEySDYwOC4zODRDNTU1LjM0OTMtMjEyIDUxMi4zNDEzLTE2OC45OTIgNTEyLjM0MTMtMTE1Ljk1NzNWMTQwLjIxMzNDNTEyLjM0MTMgMTkzLjI0OCA1NTUuMzQ5MyAyMzYuMjU2IDYwOC4zODQgMjM2LjI1Nkg4NjQuNTU0N0M5MTcuNTg5MyAyMzYuMjU2IDk2MC41OTczIDE5My4yNDggOTYwLjU5NzMgMTQwLjIxMzNWLTExNS45NTczQzk2MC41OTczLTE2OC45OTIgOTE3LjU4OTMtMjEyIDg2NC41NTQ3LTIxMlpNNjA4LjM4NCAxNzIuMjU2QzU5MC43MiAxNzIuMjU2IDU3Ni4zODQgMTU3LjkyIDU3Ni4zODQgMTQwLjI1NlYtMTE1LjkxNDdDNTc2LjM4NC0xMzMuNTc4NyA1OTAuNzItMTQ3LjkxNDcgNjA4LjM4NC0xNDcuOTE0N0g4NjQuNTU0N0M4ODIuMjE4Ny0xNDcuOTE0NyA4OTYuNTU0Ny0xMzMuNTc4NyA4OTYuNTU0Ny0xMTUuOTE0N1YxNDAuMjU2Qzg5Ni41NTQ3IDE1Ny45MiA4ODIuMjE4NyAxNzIuMjU2IDg2NC41NTQ3IDE3Mi4yNTZaTTc1Mi40NjkzIDI2OC4yOTg3Qzc1Mi40MjY3IDI2OC4yOTg3IDc1Mi4zNDEzIDI2OC4yOTg3IDc1Mi4yOTg3IDI2OC4yOTg3IDcyNS44NDUzIDI2OC4yOTg3IDcwMS44NjY3IDI3OS4wNTA3IDY4NC41ODY3IDI5Ni40NTg3TDUwOC40NTg3IDQ3Mi41ODY3QzQ5MS4wOTMzIDQ4OS45NTIgNDgwLjM4NCA1MTMuOTczMyA0ODAuMzg0IDU0MC40NjkzUzQ5MS4xMzYgNTkwLjk4NjcgNTA4LjQ1ODcgNjA4LjM1Mkw2ODQuNTg2NyA3ODQuNDhDNzAyLjI1MDcgODAxLjI0OCA3MjYuMTQ0IDgxMS41NzMzIDc1Mi40NjkzIDgxMS41NzMzUzgwMi42ODggODAxLjI0OCA4MjAuMzk0NyA3ODQuNDM3M0w5OTYuNDggNjA4LjM1MkMxMDEzLjg0NTMgNTkwLjk4NjcgMTAyNC41NTQ3IDU2Ni45NjUzIDEwMjQuNTU0NyA1NDAuNDY5M1MxMDEzLjgwMjcgNDg5Ljk1MiA5OTYuNDggNDcyLjU4NjdMODIwLjM1MiAyOTYuNDU4N0M4MDMuMDcyIDI3OS4wNTA3IDc3OS4wOTMzIDI2OC4yOTg3IDc1Mi42NCAyNjguMjk4NyA3NTIuNTk3MyAyNjguMjk4NyA3NTIuNTEyIDI2OC4yOTg3IDc1Mi40NjkzIDI2OC4yOTg3Wk03NTIuNDY5MyA3NDguNTk3M0M3NDMuNjggNzQ4LjQ2OTMgNzM1Ljc4NjcgNzQ0LjggNzMwLjA2OTMgNzM4Ljk5NzNMNTUzLjMwMTMgNTYyLjg2OTNDNTQ3LjQ1NiA1NTcuMDY2NyA1NDMuODI5MyA1NDkuMDAyNyA1NDMuODI5MyA1NDAuMTI4UzU0Ny40NTYgNTIzLjE4OTMgNTUzLjMwMTMgNTE3LjM4NjdMNzMwLjA2OTMgMzQxLjI1ODdDNzM1Ljg3MiAzMzUuNDEzMyA3NDMuOTM2IDMzMS43ODY3IDc1Mi44MTA3IDMzMS43ODY3Uzc2OS43NDkzIDMzNS40MTMzIDc3NS41NTIgMzQxLjI1ODdMOTUxLjY4IDUxOC4wMjY3Qzk1Ny41MjUzIDUyMy44MjkzIDk2MS4xNTIgNTMxLjg5MzMgOTYxLjE1MiA1NDAuNzY4Uzk1Ny41MjUzIDU1Ny43MDY3IDk1MS42OCA1NjMuNTA5M0w3NzQuOTEyIDczOS42MzczQzc2OS4xNTIgNzQ1LjE4NCA3NjEuMzQ0IDc0OC41OTczIDc1Mi42ODI3IDc0OC41OTczIDc1Mi41OTczIDc0OC41OTczIDc1Mi41NTQ3IDc0OC41OTczIDc1Mi40NjkzIDc0OC41OTczWiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTEwQiIgdW5pY29kZT0iJiN4RTEwQjsiIGQ9Ik0xNjAgNDRMMTYwIDYyMCA5NiA2MjAgOTYtMjAgMTI4LTIwIDE2MC0yMCA5NjAtMjAgOTYwIDQ0IDE2MCA0NFpNODgzLjA0IDExMS4zNkw5MTIgMTExLjM2IDkxMiAxNTEuNjggOTEyIDQ0NCA5MTIgNTU1LjM2IDY3MC4wOCAzNTMuNiA0MjEuNzYgNDc4LjA4IDIxNi45NiAzMDkuNzYgMjE2Ljk2IDIyMCAyMTYuOTYgMTUxLjY4IDIxNi45NiAxMjQgMjE2Ljk2IDExMS4zNiA4MzIgMTExLjM2IDg4My4wNCAxMTEuMzZaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMTBDIiB1bmljb2RlPSImI3hFMTBDOyIgZD0iTTUxMiA4MTJDMjI5LjI0OCA4MTIgMCA1ODIuNzUyIDAgMzAwUzIyOS4yNDgtMjEyIDUxMi0yMTJDNzk0Ljc1Mi0yMTIgMTAyNCAxNy4yNDggMTAyNCAzMDBTNzk0Ljc1MiA4MTIgNTEyIDgxMlpNNzIzLjIgMjI0LjQ4TDUzMS4yIDUyLjMyIDUyNi4wOCA0OS4xMkg1MjEuNkM1MTguMTAxMyA0Ny42MjY3IDUxNC4wNDggNDYuNzMwNyA1MDkuNzgxMyA0Ni43MzA3UzUwMS40MTg3IDQ3LjU4NCA0OTcuNzQ5MyA0OS4xNjI3TDQ5My40ODI3IDQ5LjA3NzMgNDg4LjM2MjcgNTIuMjc3MyAyOTYuMzYyNyAyMjQuNDM3M0MyODkuMDI0IDIzMC4zNjggMjg0LjQxNiAyMzkuMzI4IDI4NC40MTYgMjQ5LjM5NzMgMjg0LjQxNiAyNjcuMDYxMyAyOTguNzUyIDI4MS4zOTczIDMxNi40MTYgMjgxLjM5NzMgMzI1LjM3NiAyODEuMzk3MyAzMzMuNDQgMjc3LjcyOCAzMzkuMjQyNyAyNzEuNzk3M0w0ODAuMDQyNyAxNDguMjc3M1Y1MjMuOTU3M0M0ODAuMDQyNyA1NDEuNjIxMyA0OTQuMzc4NyA1NTUuOTU3MyA1MTIuMDQyNyA1NTUuOTU3M1M1NDQuMDQyNyA1NDEuNjIxMyA1NDQuMDQyNyA1MjMuOTU3M1YxNDguMjc3M0w2ODAuMzYyNyAyNzEuNzk3M0M2ODYuMTY1MyAyNzcuNzI4IDY5NC4yNzIgMjgxLjM5NzMgNzAzLjE4OTMgMjgxLjM5NzMgNzIwLjg1MzMgMjgxLjM5NzMgNzM1LjE4OTMgMjY3LjA2MTMgNzM1LjE4OTMgMjQ5LjM5NzMgNzM1LjE4OTMgMjM5LjMyOCA3MzAuNTM4NyAyMzAuMzY4IDcyMy4yODUzIDIyNC40OFoiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxMEQiIHVuaWNvZGU9IiYjeEUxMEQ7IiBkPSJNNTEyIDgxMkMyMjkuNzYgODEyIDAgNTgyLjI0IDAgMzAwUzIyOS43Ni0yMTIgNTEyLTIxMiAxMDI0IDE3Ljc2IDEwMjQgMzAwIDc5NC4yNCA4MTIgNTEyIDgxMlpNNTEyLTE0OEMyNjQuOTYtMTQ4IDY0IDUyLjk2IDY0IDMwMFMyNjQuOTYgNzQ4IDUxMiA3NDhDNzU5LjA0IDc0OCA5NjAgNTQ3LjA0IDk2MCAzMDBTNzU5LjA0LTE0OCA1MTItMTQ4Wk02ODAuMzIgMjcxLjg0TDU0NCAxNDguMzJWNTI0QzU0NCA1NDEuOTIgNTI5LjkyIDU1NiA1MTIgNTU2UzQ4MCA1NDEuOTIgNDgwIDUyNFYxNDguMzJMMzQ0LjMyIDI3MS44NEMzMzEuNTIgMjgzLjM2IDMxMS4wNCAyODIuNzIgMjk4Ljg4IDI2OS45MiAyODYuNzIgMjU2LjQ4IDI4OCAyMzYuNjQgMzAwLjggMjI0LjQ4TDQ5MC4yNCA1Mi4zMkM0OTEuNTIgNTEuMDQgNDkzLjQ0IDUwLjQgNDk1LjM2IDQ5LjEyIDQ5Ni42NCA0OC40OCA0OTcuOTIgNDcuMiA0OTkuODQgNDYuNTYgNTAzLjY4IDQ0LjY0IDUwOC4xNiA0NCA1MTIgNDRTNTIwLjMyIDQ0LjY0IDUyNC4xNiA0Ni41NkM1MjYuMDggNDcuMiA1MjcuMzYgNDguNDggNTI4LjY0IDQ5LjEyIDUzMC41NiA1MC40IDUzMi40OCA1MS4wNCA1MzMuNzYgNTIuMzJMNzIzLjIgMjI0LjQ4QzczNi42NCAyMzYuNjQgNzM3LjI4IDI1Ni40OCA3MjUuMTIgMjY5LjkyIDcxMy42IDI4Mi43MiA2OTMuMTIgMjg0IDY4MC4zMiAyNzEuODRaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMTBFIiB1bmljb2RlPSImI3hFMTBFOyIgZD0iTTk2My40MTMzIDE5Ny42Qzk2My4wMjkzIDIwNC4xNzA3IDk2MC41MTIgMjEwLjA1ODcgOTU2LjU0NCAyMTQuNzA5M0w5NTYuNTg2NyAyMTguOTMzM0M5NTMuODU2IDIyMS41MzYgOTUwLjc4NCAyMjMuNzk3MyA5NDcuNDEzMyAyMjUuNjMyTDk0Ny4yIDIyNS43Nkg2NTIuOFY3MjYuNjY2N0M2NTIuOCA3NzMuODEzMyA2MTQuNjEzMyA4MTIgNTY3LjQ2NjcgODEySDQ4Mi4xMzMzQzQzNC45ODY3IDgxMiAzOTYuOCA3NzMuODEzMyAzOTYuOCA3MjYuNjY2N1YyMzQuMjkzM0gxMTAuMDhDMTA1LjE3MzMgMjMwLjYyNCAxMDEuMTYyNyAyMjYuMTAxMyA5OC4yNjEzIDIyMC44NTMzTDk4LjEzMzMgMjIwLjY0VjIxNi4zNzMzQzkzLjk5NDcgMjExLjU5NDcgOTEuNDM0NyAyMDUuMzIyNyA5MS4zMDY3IDE5OC40OTYgOTEuMjIxMyAxOTcuNDI5MyA5MS4xNzg3IDE5Ni4yNzczIDkxLjE3ODcgMTk1LjA0UzkxLjIyMTMgMTkyLjY1MDcgOTEuMzQ5MyAxOTEuNDU2TDkxLjM0OTMgMTkxLjYyNjdDOTEuMTM2IDE5MC4wOTA3IDkxLjA1MDcgMTg4LjI5ODcgOTEuMDUwNyAxODYuNTA2N1M5MS4xNzg3IDE4Mi45MjI3IDkxLjM5MiAxODEuMTczM0M5MS4zMDY3IDE4MC40OTA3IDkxLjI2NCAxNzkuNDY2NyA5MS4yNjQgMTc4LjRTOTEuMzA2NyAxNzYuMzA5MyA5MS4zOTIgMTc1LjI4NTNDOTIuNzE0NyAxNzIuODEwNyA5NC4xMjI3IDE3MC41OTIgOTUuNzQ0IDE2OC41MDEzTDk4LjIxODcgMTYwLjkwNjcgNDk1LjAxODctMjAwLjA1MzNDNTAyLjU3MDctMjA2Ljg4IDUxMi41OTczLTIxMS4wNjEzIDUyMy42MDUzLTIxMS4wNjEzUzU0NC42NC0yMDYuODggNTUyLjIzNDctMjAwLjA1MzNMOTUxLjU1MiAxNjAuMDEwNyA5NTYuNjcyIDE2Ni44MzczIDk2MC45Mzg3IDE3My42NjRDOTYxLjAyNCAxNzQuNTYgOTYxLjAyNCAxNzUuNTg0IDk2MS4wMjQgMTc2LjY1MDdTOTYwLjk4MTMgMTc4Ljc0MTMgOTYwLjg5NiAxNzkuNzY1M0M5NjEuMTA5MyAxODEuMTczMyA5NjEuMTk0NyAxODIuOTIyNyA5NjEuMTk0NyAxODQuNzU3M1M5NjEuMDY2NyAxODguMzQxMyA5NjAuODUzMyAxOTAuMDkwN0w5NjAuODUzMyAxODkuODc3M0M5NjEuODc3MyAxOTIuMDUzMyA5NjIuNzMwNyAxOTQuNjEzMyA5NjMuMzcwNyAxOTcuMzAxM1oiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxMEYiIHVuaWNvZGU9IiYjeEUxMEY7IiBkPSJNNDgwIDIwNFY1MjRINTQ0VjIwNEw2NDAgMzAwIDY4OCAyNTIgNTEyIDc2IDMzNiAyNTIgMzg0IDMwMFoiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxMTAiIHVuaWNvZGU9IiYjeEUxMTA7IiBkPSJNNTEyIDgxMkMyMjkuMjQ4IDgxMiAwIDU4Mi43NTIgMCAzMDBTMjI5LjI0OC0yMTIgNTEyLTIxMkM3OTQuNzUyLTIxMiAxMDI0IDE3LjI0OCAxMDI0IDMwMFM3OTQuNzUyIDgxMiA1MTIgODEyWk03MzYgMjY4SDM2MC4zMkw0ODMuODQgMTMxLjY4QzQ4OS43NzA3IDEyNS44NzczIDQ5My40NCAxMTcuNzcwNyA0OTMuNDQgMTA4Ljg1MzMgNDkzLjQ0IDkxLjE4OTMgNDc5LjEwNCA3Ni44NTMzIDQ2MS40NCA3Ni44NTMzIDQ1MS4zNzA3IDc2Ljg1MzMgNDQyLjQxMDcgODEuNTA0IDQzNi41MjI3IDg4Ljc1NzNMMjY0LjMyIDI4MC44QzI2NC4yMzQ3IDI4MS41NjggMjY0LjE5MiAyODIuNDY0IDI2NC4xOTIgMjgzLjM2UzI2NC4yMzQ3IDI4NS4xNTIgMjY0LjMyIDI4Ni4wNDhMMjY0LjMyIDI5MC40QzI2Mi44NjkzIDI5My44OTg3IDI2Mi4wNTg3IDI5Ny45OTQ3IDI2Mi4wNTg3IDMwMi4yMTg3UzI2Mi45MTIgMzEwLjUzODcgMjY0LjQwNTMgMzE0LjI5MzNMMjY0LjMyIDMxOC41NkMyNjQuMjM0NyAzMTkuMzI4IDI2NC4xOTIgMzIwLjIyNCAyNjQuMTkyIDMyMS4xMlMyNjQuMjM0NyAzMjIuOTEyIDI2NC4zMiAzMjMuODA4TDQzNi40OCA1MTUuNjhDNDQyLjQxMDcgNTIzLjAxODcgNDUxLjM3MDcgNTI3LjYyNjcgNDYxLjQ0IDUyNy42MjY3IDQ3OS4xMDQgNTI3LjYyNjcgNDkzLjQ0IDUxMy4yOTA3IDQ5My40NCA0OTUuNjI2NyA0OTMuNDQgNDg2LjY2NjcgNDg5Ljc3MDcgNDc4LjYwMjcgNDgzLjg0IDQ3Mi44TDM2MC4zMiAzMzJINzM2Qzc1My42NjQgMzMyIDc2OCAzMTcuNjY0IDc2OCAzMDBTNzUzLjY2NCAyNjggNzM2IDI2OFoiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxMTEiIHVuaWNvZGU9IiYjeEUxMTE7IiBkPSJNNTEyIDgxMkMyMjkuNzYgODEyIDAgNTgyLjI0IDAgMzAwUzIyOS43Ni0yMTIgNTEyLTIxMiAxMDI0IDE3Ljc2IDEwMjQgMzAwIDc5NC4yNCA4MTIgNTEyIDgxMlpNNTEyLTE0OEMyNjQuOTYtMTQ4IDY0IDUyLjk2IDY0IDMwMFMyNjQuOTYgNzQ4IDUxMiA3NDhDNzU5LjA0IDc0OCA5NjAgNTQ3LjA0IDk2MCAzMDBTNzU5LjA0LTE0OCA1MTItMTQ4Wk03MzYgMzMySDM2MC4zMkw0ODMuODQgNDY4LjMyQzQ5NiA0ODEuMTIgNDk0LjcyIDUwMS42IDQ4MS45MiA1MTMuNzYgNDY5LjEyIDUyNS4yOCA0NDguNjQgNTI0IDQzNi40OCA1MTEuMkwyNjQuMzIgMzIxLjc2QzI2My4wNCAzMTkuODQgMjYyLjQgMzE3LjkyIDI2MS4xMiAzMTYuNjQgMjYwLjQ4IDMxNC43MiAyNTkuMiAzMTMuNDQgMjU4LjU2IDMxMi4xNiAyNTUuMzYgMzA0LjQ4IDI1NS4zNiAyOTYuMTYgMjU4LjU2IDI4OC40OCAyNTkuMiAyODYuNTYgMjYwLjQ4IDI4NS4yOCAyNjEuMTIgMjg0IDI2Mi40IDI4Mi4wOCAyNjMuMDQgMjgwLjE2IDI2NC4zMiAyNzguMjRMNDM2LjQ4IDg4LjhDNDQyLjg4IDgxLjc2IDQ1MS4yIDc4LjU2IDQ2MC4xNiA3OC41NiA0NjcuODQgNzguNTYgNDc1LjUyIDgxLjEyIDQ4MS45MiA4Ni44OCA0OTQuNzIgOTkuMDQgNDk2IDExOC44OCA0ODMuODQgMTMyLjMyTDM2MC4zMiAyNjhINzM2Qzc1My45MiAyNjggNzY4IDI4Mi4wOCA3NjggMzAwUzc1My45MiAzMzIgNzM2IDMzMloiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxMTIiIHVuaWNvZGU9IiYjeEUxMTI7IiBkPSJNOTM4LjY2NjcgNDE1LjJINDQ2LjI5MzNWNjg1LjcwNjdDNDQ2LjM3ODcgNjg2LjYwMjcgNDQ2LjM3ODcgNjg3LjYyNjcgNDQ2LjM3ODcgNjg4LjY5MzNTNDQ2LjMzNiA2OTAuNzg0IDQ0Ni4yNTA3IDY5MS44MDhDNDQ2LjQ2NCA2OTMuMjE2IDQ0Ni41NDkzIDY5NC45NjUzIDQ0Ni41NDkzIDY5Ni44UzQ0Ni40MjEzIDcwMC4zODQgNDQ2LjIwOCA3MDIuMTMzM0w0NDYuMjA4IDcwMS45MkM0NDIuNTM4NyA3MDYuODI2NyA0MzguMDE2IDcxMC44MzczIDQzMi43NjggNzEzLjczODdMNDMyLjU1NDcgNzEzLjg2NjcgNDI2LjU4MTMgNzE4Ljk4NjcgNDE4LjA0OCA3MjQuMTA2N0gzODYuNDc0N0wzNzkuNjQ4IDcxOS44NCAzNzIuODIxMyA3MTMuODY2NyAxMS4wMDggMzE2LjIxMzNDNC4xODEzIDMwOC42NjEzIDAgMjk4LjYzNDcgMCAyODcuNjI2N1M0LjE4MTMgMjY2LjU5MiAxMS4wMDggMjU4Ljk5NzNMMzcxLjkyNTMtMTM5LjQ2NjcgMzc4Ljc1Mi0xNDQuNTg2NyAzODUuNTc4Ny0xNDguODUzM0g0MTguMDA1M0w0MjYuNTM4Ny0xNDMuNzMzM0g0MzAuODA1M0M0MzMuNDA4LTE0MS4wMDI3IDQzNS42NjkzLTEzNy45MzA3IDQzNy41MDQtMTM0LjU2TDQzNy42MzItMTM0LjM0NjdDNDM3LjgwMjctMTMyLjkzODcgNDM3Ljg4OC0xMzEuMzE3MyA0MzcuODg4LTEyOS42NTMzUzQzNy44MDI3LTEyNi4zNjggNDM3LjYzMi0xMjQuNzQ2N0M0MzcuNzE3My0xMjMuOTM2IDQzNy44MDI3LTEyMi43NDEzIDQzNy44MDI3LTEyMS41NDY3UzQzNy43Ni0xMTkuMTU3MyA0MzcuNjc0Ny0xMTcuOTYyN0w0MzcuNjc0NyAxNTkuMkg5MzguNTgxM0M5ODUuNzI4IDE1OS4yIDEwMjMuOTE0NyAxOTcuMzg2NyAxMDIzLjkxNDcgMjQ0LjUzMzNWMzI5Ljg2NjdDMTAyMy45MTQ3IDM3Ny4wMTMzIDk4NS43MjggNDE1LjIgOTM4LjU4MTMgNDE1LjJaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMTEzIiB1bmljb2RlPSImI3hFMTEzOyIgZD0iTTQxNiAzMzJINzM2VjI2OEg0MTZMNTEyIDE3MiA0NjQgMTI0IDI4OCAzMDAgNDY0IDQ3NiA1MTIgNDI4WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTExNCIgdW5pY29kZT0iJiN4RTExNDsiIGQ9Ik0xMDI0IDcwOC4xNDkzQzEwMjQuMTcwNyA3MDkuMzQ0IDEwMjQuMjU2IDcxMC43NTIgMTAyNC4yNTYgNzEyLjE2UzEwMjQuMTcwNyA3MTQuOTc2IDEwMjQgNzE2LjM0MTNDMTAyMi43NjI3IDcxOC45ODY3IDEwMjEuMzEyIDcyMS4zNzYgMTAxOS41NjI3IDcyMy41NTJMMTAxOS42MDUzIDcyNy44NjEzIDEwMTIuMzA5MyA3MzIuOTgxMyAxMDAyLjA2OTMgNzM4LjgyNjdIOTc1LjAxODdMOTY2Ljk1NDcgNzM0LjQzMkg5NjMuMjg1M0w1MTIgMzIwLjQzNzMgNjEuNDQgNzI5LjMxMkg1Ny4wNDUzTDQ5Ljc0OTMgNzM4LjgyNjdIMTYuODUzM0wxMC4yODI3IDczMy43MDY3VjcyOS4zMTJDOC42MTg3IDcyNy4xNzg3IDcuMTY4IDcyNC43ODkzIDUuOTczMyA3MjIuMjI5MyA1LjcxNzMgNzIwLjgyMTMgNS42MzIgNzE5LjQxMzMgNS42MzIgNzE4LjAwNTNTNS43MTczIDcxNS4xODkzIDUuODg4IDcxMy44MjRDNS44MDI3IDcxMy4yMjY3IDUuNzYgNzEyLjMzMDcgNS43NiA3MTEuNDM0N1M1LjgwMjcgNzA5LjY0MjcgNS44NDUzIDcwOC43NDY3TDUuODQ1MyAzMjguNTAxM0gwQy0wLjEyOCAzMjcuMzA2Ny0wLjIxMzMgMzI1Ljg5ODctMC4yMTMzIDMyNC40OTA3Uy0wLjEyOCAzMjEuNjc0NyAwLjA0MjcgMzIwLjMwOTNDLTAuMDQyNyAzMTkuNTg0LTAuMDg1MyAzMTguNTYtMC4wODUzIDMxNy41MzZTLTAuMDQyNyAzMTUuNDg4IDAuMDQyNyAzMTQuNDY0TDAuMDQyNyAzMTAuMTk3M0MxLjUzNiAzMDcuNDI0IDMuMjQyNyAzMDQuOTkyIDUuMjA1MyAzMDIuODU4N0w1LjE2MjcgMzAyLjkwMTMgNDgwLjU5NzMtMTI4LjYyOTNDNDg3LjE2OC0xMzQuNTE3MyA0OTUuOTE0Ny0xMzguMTQ0IDUwNS40NzItMTM4LjE0NFM1MjMuNzc2LTEzNC41NiA1MzAuMzg5My0xMjguNjI5M0wxMDEyLjM1MiAyOTkuOTU3M0MxMDE0LjI3MiAzMDIuMDkwNyAxMDE1Ljk3ODcgMzA0LjQ4IDEwMTcuMzg2NyAzMDcuMDgyN0wxMDE3LjQ3MiAzMTEuNjQ4QzEwMTcuNTU3MyAzMTIuNTQ0IDEwMTcuNiAzMTMuNTI1MyAxMDE3LjYgMzE0LjU5MlMxMDE3LjU1NzMgMzE2LjY0IDEwMTcuNDcyIDMxNy42NjRDMTAxNy42NDI3IDMxOC43MzA3IDEwMTcuNzI4IDMyMC4xMzg3IDEwMTcuNzI4IDMyMS41NDY3UzEwMTcuNjQyNyAzMjQuMzYyNyAxMDE3LjQ3MiAzMjUuNzI4TDEwMTcuNDcyIDMyNS41NTczVjcwMi45ODY3QzEwMTkuOTg5MyA3MDQuNDggMTAyMi4xMjI3IDcwNi4xODY3IDEwMjQuMDQyNyA3MDguMTA2N1oiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxMTUiIHVuaWNvZGU9IiYjeEUxMTU7IiBkPSJNOTUwLjg2OTMtMTYyLjI1MDdDOTQ5LjY3NDctMTU5LjE3ODcgOTQ4LjE4MTMtMTU2LjUzMzMgOTQ2LjM4OTMtMTU0LjEwMTNMOTQ2LjQ3NDctMTUwLjU2IDUzMi40OCAzMDAgOTQxLjM1NDcgNzUwLjU2Vjc1NC45NTQ3Qzk0My4wMTg3IDc1Ny4wODggOTQ0LjQ2OTMgNzU5LjQ3NzMgOTQ1LjY2NCA3NjIuMDM3MyA5NDUuODc3MyA3NjMuNDQ1MyA5NDUuOTYyNyA3NjQuODUzMyA5NDUuOTYyNyA3NjYuMjYxM1M5NDUuODc3MyA3NjkuMDc3MyA5NDUuNzA2NyA3NzAuNDQyN0M5NDUuNzkyIDc3MS4wNCA5NDUuODM0NyA3NzEuOTM2IDk0NS44MzQ3IDc3Mi44MzJTOTQ1Ljc5MiA3NzQuNjI0IDk0NS43NDkzIDc3NS41Mkw5NDUuNzQ5MyA3NzUuMzkyQzk0NS45NjI3IDc3Ni44IDk0Ni4wNDggNzc4LjQ2NCA5NDYuMDQ4IDc4MC4xMjhTOTQ1LjkyIDc4My40NTYgOTQ1LjcwNjcgNzg1LjA3NzNDOTQ1Ljc0OTMgNzg1LjU0NjcgOTQ1Ljc5MiA3ODYuMzE0NyA5NDUuNzkyIDc4Ny4wODI3Uzk0NS43NDkzIDc4OC42MTg3IDk0NS43MDY3IDc4OS4zODY3TDk0NS43MDY3IDc5NC40MjEzQzk0NC4xNzA3IDc5Ni44OTYgOTQyLjUwNjcgNzk5LjA3MiA5NDAuNTg2NyA4MDAuOTkyTDk0MC41ODY3IDgwMC45OTJIOTM2LjE5Mkw5MjguMTI4IDgxMS45NTczSDUyMi4xOTczTDUxMS45NTczIDgwMC45OTIgODAuNDI2NyAzMjUuNTU3M0M3NC41Mzg3IDMxOC45ODY3IDcwLjkxMiAzMTAuMjQgNzAuOTEyIDMwMC42ODI3Uzc0LjQ5NiAyODIuMzc4NyA4MC40MjY3IDI3NS43NjUzTDUxMS45NTczLTIwMC4zNTIgNTE5LjI1MzMtMjA1LjQ3Mkg5MjUuOTA5M0w5MzMuMjA1My0yMDEuMDc3M0g5MzcuNkM5MzkuNTItMTk4Ljk0NCA5NDEuMjI2Ny0xOTYuNTU0NyA5NDIuNjM0Ny0xOTMuOTUyTDk0Mi43Mi0xODkuMzg2N0M5NDIuODA1My0xODcuMjk2IDk0Mi44NDgtMTg0Ljg2NCA5NDIuODQ4LTE4Mi40MzJTOTQyLjgwNTMtMTc3LjU2OCA5NDIuNzItMTc1LjEzNkw5NDIuNzItMTc1LjQ3NzNDOTQyLjgwNTMtMTc0LjU4MTMgOTQyLjg0OC0xNzMuNiA5NDIuODQ4LTE3Mi41MzMzUzk0Mi44MDUzLTE3MC40ODUzIDk0Mi43Mi0xNjkuNDYxM0M5NDUuODM0Ny0xNjcuNTQxMyA5NDguNDgtMTY1LjEwOTMgOTUwLjc0MTMtMTYyLjMzNloiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxMTYiIHVuaWNvZGU9IiYjeEUxMTY7IiBkPSJNOTQxLjM1NDcgMzI0Ljg3NDdMNTEyIDgwMC4zMDkzIDUwNC43MDQgODA1LjQyOTMgNDk3LjQwOCA4MTJIOTUuODcyTDg4LjU3NiA4MDcuNjA1M0g4NC4xODEzQzgyLjI2MTMgODA1LjY4NTMgODAuNTk3MyA4MDMuNTA5MyA3OS4xNDY3IDgwMS4xNjI3TDczLjIxNiA3OTAuMDI2N0M3My4xNzMzIDc4OS4zODY3IDczLjE3MzMgNzg4LjYxODcgNzMuMTczMyA3ODcuODUwN1M3My4yMTYgNzg2LjMxNDcgNzMuMjU4NyA3ODUuNTQ2N0M3My4wNDUzIDc4NC4yMjQgNzIuOTYgNzgyLjU2IDcyLjk2IDc4MC44OTZTNzMuMDg4IDc3Ny41NjggNzMuMzAxMyA3NzUuOTQ2N0w3My4zMDEzIDc3Ni4xMTczQzczLjI1ODcgNzc1LjM0OTMgNzMuMjE2IDc3NC40NTMzIDczLjIxNiA3NzMuNTU3M1M3My4yNTg3IDc3MS43NjUzIDczLjMwMTMgNzcwLjg2OTNDNzMuMTczMyA3NjkuNzYgNzMuMDg4IDc2OC4zOTQ3IDczLjA4OCA3NjYuOTQ0UzczLjE3MzMgNzY0LjEyOCA3My4zNDQgNzYyLjc2MjdDNzQuNTgxMyA3NjAuMTYgNzYuMDMyIDc1Ny43MjggNzcuNzgxMyA3NTUuNTUyTDc3LjczODcgNzUxLjI0MjcgNDkxLjczMzMgMjk5Ljk1NzMgODMuNTg0LTE0OS44NzczVi0xNTMuNTQ2N0M4MS44NzczLTE1NS44NTA3IDgwLjQyNjctMTU4LjUzODcgNzkuMjc0Ny0xNjEuMzU0NyA3OS4wNjEzLTE2Mi42NzczIDc5LjAxODctMTYzLjk1NzMgNzkuMDE4Ny0xNjUuMjM3M1M3OS4xMDQtMTY3Ljc5NzMgNzkuMjMyLTE2OS4wMzQ3Qzc5LjE0NjctMTY5Ljc2IDc5LjEwNC0xNzAuNzg0IDc5LjEwNC0xNzEuODA4Uzc5LjE0NjctMTczLjg1NiA3OS4yMzItMTc0Ljg4TDczLjM4NjctMTc0Ljc1MkM3My4zMDEzLTE3Ni44NDI3IDczLjI1ODctMTc5LjI3NDcgNzMuMjU4Ny0xODEuNzA2N1M3My4zMDEzLTE4Ni41NzA3IDczLjM4NjctMTg5LjAwMjdMNzMuMzg2Ny0xOTMuMDU2Qzc0Ljg4LTE5NS44MjkzIDc2LjU4NjctMTk4LjIxODcgNzguNTQ5My0yMDAuMzk0N0w3OC41MDY3LTIwMC4zNTJIODIuOTAxM0w5MC4xOTczLTIwNC43NDY3SDQ5Ni44NTMzTDUwNC4xNDkzLTE5OS42MjY3SDUxMi4yMTMzTDk0My43NDQgMjc1LjgwOEM5NDkuNjMyIDI4Mi4zNzg3IDk1My4yNTg3IDI5MS4xMjUzIDk1My4yNTg3IDMwMC42ODI3Uzk0OS42NzQ3IDMxOC45ODY3IDk0My43NDQgMzI1LjZaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMTE3IiB1bmljb2RlPSImI3hFMTE3OyIgZD0iTTEwMjQgMjcyLjIyNEMxMDI0LjEyOCAyNzMuNDE4NyAxMDI0LjIxMzMgMjc0LjgyNjcgMTAyNC4yMTMzIDI3Ni4yMzQ3UzEwMjQuMTI4IDI3OS4wNTA3IDEwMjMuOTU3MyAyODAuNDE2QzEwMjQuMDQyNyAyODEuMTQxMyAxMDI0LjA4NTMgMjgyLjE2NTMgMTAyNC4wODUzIDI4My4xODkzUzEwMjQuMDQyNyAyODUuMjM3MyAxMDIzLjk1NzMgMjg2LjI2MTNMMTAyMy45NTczIDI5MC41MjhDMTAyMi40NjQgMjkzLjMwMTMgMTAyMC43NTczIDI5NS42OTA3IDEwMTguNzk0NyAyOTcuODY2N0wxMDE4LjgzNzMgMjk3LjgyNCA1NDMuNDAyNyA3MjkuMzU0N0M1MzYuODMyIDczNS4yNDI3IDUyOC4wODUzIDczOC44NjkzIDUxOC41MjggNzM4Ljg2OTNTNTAwLjIyNCA3MzUuMjg1MyA0OTMuNjEwNyA3MjkuMzU0N0wxMS42NDggMzAwLjA0MjdDOS43MjggMjk3LjkwOTMgOC4wMjEzIDI5NS41MiA2LjYxMzMgMjkyLjkxNzNMLTAuMDQyNyAyODUuNDA4Qy0wLjA4NTMgMjg0LjY0LTAuMTI4IDI4My43NDQtMC4xMjggMjgyLjg0OFMtMC4wODUzIDI4MS4wNTYtMC4wNDI3IDI4MC4xNkMtMC4yMTMzIDI3OS4wNTA3LTAuMjk4NyAyNzcuNjg1My0wLjI5ODcgMjc2LjI3NzNTLTAuMjEzMyAyNzMuNDYxMy0wLjA0MjcgMjcyLjA5NkwtMC4wNDI3IDI3Mi4yNjY3Vi0xMDIuMjE4N0MtMC4xMjgtMTAyLjk4NjctMC4xMjgtMTAzLjg4MjctMC4xMjgtMTA0Ljc3ODdTLTAuMDg1My0xMDYuNTcwNyAwLTEwNy40NjY3Qy0wLjE3MDctMTA4LjU3Ni0wLjI1Ni0xMDkuOTQxMy0wLjI1Ni0xMTEuMzkyUy0wLjE3MDctMTE0LjIwOCAwLTExNS41NzMzQzEuMjM3My0xMTguMjE4NyAyLjY4OC0xMjAuNjA4IDQuNDM3My0xMjIuNzg0TDQuMzk0Ny0xMjcuMDkzMyAxMC45NjUzLTEzMi4yMTMzSDQzLjg2MTNMNTEuMTU3My0xMjcuODE4N0g1NS41NTJMNTExLjk1NzMgMjc5LjYwNTMgOTYxLjc5Mi0xMjguNTQ0SDk2NS40NjEzTDk3My41MjUzLTEzMi45Mzg3SDEwMDQuOTcwN0wxMDEyLjI2NjctMTI3LjgxODdWLTEyMy40MjRDMTAxMy45MzA3LTEyMS4yOTA3IDEwMTUuMzgxMy0xMTguOTAxMyAxMDE2LjU3Ni0xMTYuMzQxMyAxMDE2LjgzMi0xMTQuOTMzMyAxMDE2LjkxNzMtMTEzLjUyNTMgMTAxNi45MTczLTExMi4xMTczUzEwMTYuODMyLTEwOS4zMDEzIDEwMTYuNjYxMy0xMDcuOTM2QzEwMTYuNzQ2Ny0xMDcuMzM4NyAxMDE2Ljc4OTMtMTA2LjQ0MjcgMTAxNi43ODkzLTEwNS41NDY3UzEwMTYuNzQ2Ny0xMDMuNzU0NyAxMDE2LjcwNC0xMDIuODU4N0wxMDE2LjcwNCAyNzEuNDk4N1oiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxMTgiIHVuaWNvZGU9IiYjeEUxMTg7IiBkPSJNNTEyIDgxMkMyMjkuMjQ4IDgxMiAwIDU4Mi43NTIgMCAzMDBTMjI5LjI0OC0yMTIgNTEyLTIxMkM3OTQuNzUyLTIxMiAxMDI0IDE3LjI0OCAxMDI0IDMwMFM3OTQuNzUyIDgxMiA1MTIgODEyWk03NjggMzAwQzc2OC4yOTg3IDI5OC4zNzg3IDc2OC40NjkzIDI5Ni41MDEzIDc2OC40NjkzIDI5NC41Mzg3Uzc2OC4yOTg3IDI5MC43NDEzIDc2Ny45NTczIDI4OC45MDY3TDc2OCAyODQuNjRDNzY4LjA4NTMgMjgzLjg3MiA3NjguMTI4IDI4Mi45NzYgNzY4LjEyOCAyODIuMDhTNzY4LjA4NTMgMjgwLjI4OCA3NjggMjc5LjM5Mkw1OTUuODQgODcuNTJDNTg5LjkwOTMgODAuMTgxMyA1ODAuOTQ5MyA3NS41NzMzIDU3MC44OCA3NS41NzMzIDU1My4yMTYgNzUuNTczMyA1MzguODggODkuOTA5MyA1MzguODggMTA3LjU3MzMgNTM4Ljg4IDExNi41MzMzIDU0Mi41NDkzIDEyNC41OTczIDU0OC40OCAxMzAuNEw2NjMuNjggMjY4SDI4OEMyNzAuMzM2IDI2OCAyNTYgMjgyLjMzNiAyNTYgMzAwUzI3MC4zMzYgMzMyIDI4OCAzMzJINjYzLjY4TDU0MC4xNiA0NjcuNjhDNTM0LjIyOTMgNDczLjQ4MjcgNTMwLjU2IDQ4MS41ODkzIDUzMC41NiA0OTAuNTA2NyA1MzAuNTYgNTA4LjE3MDcgNTQ0Ljg5NiA1MjIuNTA2NyA1NjIuNTYgNTIyLjUwNjcgNTcyLjYyOTMgNTIyLjUwNjcgNTgxLjU4OTMgNTE3Ljg1NiA1ODcuNDc3MyA1MTAuNjAyN0w3NTkuNjggMzE4LjU2Qzc1OS43NjUzIDMxNy43OTIgNzU5LjgwOCAzMTYuODk2IDc1OS44MDggMzE2Uzc1OS43NjUzIDMxNC4yMDggNzU5LjY4IDMxMy4zMTJMNzU5LjY4IDMwOC45NkM3NjMuMDA4IDMwNi41MjggNzY1Ljc4MTMgMzAzLjU0MTMgNzY3LjkxNDcgMzAwLjEyOEw3NjggMzAwWiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTExOSIgdW5pY29kZT0iJiN4RTExOTsiIGQ9Ik01MTIgODEyQzIyOS43NiA4MTIgMCA1ODIuMjQgMCAzMDBTMjI5Ljc2LTIxMiA1MTItMjEyIDEwMjQgMTcuNzYgMTAyNCAzMDAgNzk0LjI0IDgxMiA1MTIgODEyWk01MTItMTQ4QzI2NC45Ni0xNDggNjQgNTIuOTYgNjQgMzAwUzI2NC45NiA3NDggNTEyIDc0OEM3NTkuMDQgNzQ4IDk2MCA1NDcuMDQgOTYwIDMwMFM3NTkuMDQtMTQ4IDUxMi0xNDhaTTc2OCAyOTkuMzZDNzY4IDI5OS4zNiA3NjggMzAwIDc2OCAzMDBTNzY4IDMwMC42NCA3NjggMzAwLjY0Qzc2OCAzMDQuNDggNzY3LjM2IDMwOC4zMiA3NjYuMDggMzExLjUyIDc2NS40NCAzMTMuNDQgNzY0LjE2IDMxNC43MiA3NjMuNTIgMzE2IDc2Mi4yNCAzMTcuOTIgNzYxLjYgMzE5Ljg0IDc2MC4zMiAzMjEuMTJMNTg3LjUyIDUxMS4yQzU3NS4zNiA1MjQgNTU1LjUyIDUyNS4yOCA1NDIuMDggNTEzLjEyIDUyOS4yOCA1MDAuOTYgNTI4IDQ4MS4xMiA1NDAuMTYgNDY3LjY4TDY2My42OCAzMzEuMzZIMjg4QzI3MC4wOCAzMzIgMjU2IDMxNy45MiAyNTYgMzAwUzI3MC4wOCAyNjggMjg4IDI2OEg2NjMuNjhMNTQwLjE2IDEzMS42OEM1MjggMTE4Ljg4IDUyOS4yOCA5OC40IDU0Mi4wOCA4Ni4yNCA1NDguNDggODAuNDggNTU2LjE2IDc3LjkyIDU2My44NCA3Ny45MiA1NzIuOCA3Ny45MiA1ODEuMTIgODEuMTIgNTg3LjUyIDg4LjE2TDc1OS42OCAyNzcuNkM3NjAuOTYgMjc4Ljg4IDc2MS42IDI4MC44IDc2Mi44OCAyODIuNzIgNzYzLjUyIDI4NCA3NjQuOCAyODUuOTIgNzY1LjQ0IDI4Ny4yIDc2Ni43MiAyOTEuNjggNzY4IDI5NS41MiA3NjggMjk5LjM2WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTExQSIgdW5pY29kZT0iJiN4RTExQTsiIGQ9Ik0xMDEyLjkwNjcgMzE2LjIxMzNMNjUxLjk0NjcgNzEzLjg2NjcgNjQ1LjEyIDcxOC45ODY3IDYzOC4yOTMzIDcyMy4yNTMzSDYwNi43Mkw1OTcuMzMzMyA3MTguOTg2NyA1OTEuMzYgNzEzLjg2NjdDNTg4LjM3MzMgNzEwLjkyMjcgNTg1LjgxMzMgNzA3LjU1MiA1ODMuODA4IDcwMy44NEw1ODMuNjggNzAzLjYyNjdDNTgzLjQ2NjcgNzAyLjA5MDcgNTgzLjM4MTMgNzAwLjI5ODcgNTgzLjM4MTMgNjk4LjUwNjdTNTgzLjUwOTMgNjk0LjkyMjcgNTgzLjcyMjcgNjkzLjE3MzNDNTgzLjYzNzMgNjkyLjQ5MDcgNTgzLjU5NDcgNjkxLjQ2NjcgNTgzLjU5NDcgNjkwLjRTNTgzLjYzNzMgNjg4LjMwOTMgNTgzLjcyMjcgNjg3LjI4NTNMNTgzLjcyMjcgNDE1LjJIODUuMzc2QzM4LjIyOTMgNDE1LjIgMC4wNDI3IDM3Ny4wMTMzIDAuMDQyNyAzMjkuODY2N1YyNDQuNTMzM0MwLjA0MjcgMTk3LjM4NjcgMzguMjI5MyAxNTkuMiA4NS4zNzYgMTU5LjJINTc3Ljc0OTNWLTExMS4zMDY3QzU3Ny42NjQtMTEyLjMzMDcgNTc3LjYyMTMtMTEzLjUyNTMgNTc3LjYyMTMtMTE0LjcyUzU3Ny42NjQtMTE3LjEwOTMgNTc3Ljc0OTMtMTE4LjMwNEM1NzcuNTc4Ny0xMTkuNTQxMyA1NzcuNDkzMy0xMjEuMjA1MyA1NzcuNDkzMy0xMjIuODI2N1M1NzcuNTc4Ny0xMjYuMTEyIDU3Ny43NDkzLTEyNy43MzMzTDU3Ny43NDkzLTEyNy41MkM1NzkuNzEyLTEzMS4xMDQgNTgxLjk3MzMtMTM0LjE3NiA1ODQuNTc2LTEzNi45MDY3TDU4NC41NzYtMTM2LjkwNjdINTg4Ljg0MjdMNTk3LjM3Ni0xNDIuMDI2N0g2MjkuODAyN0w2MzYuNjI5My0xMzcuNzYgNjUxLjEzNi0xMzkuNDY2NyAxMDEyLjA5NiAyNTcuMzMzM0MxMDE4LjkyMjcgMjY0Ljg4NTMgMTAyMy4xMDQgMjc0LjkxMiAxMDIzLjEwNCAyODUuOTJTMTAxOC45MjI3IDMwNi45NTQ3IDEwMTIuMDk2IDMxNC41NDkzWiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTExQiIgdW5pY29kZT0iJiN4RTExQjsiIGQ9Ik02MDggMzMySDI4OFYyNjhINjA4TDUxMiAxNzIgNTYwIDEyNCA3MzYgMzAwIDU2MCA0NzYgNTEyIDQyOFoiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxMUMiIHVuaWNvZGU9IiYjeEUxMUM7IiBkPSJNNTEyIDgxMkMyMjkuMjQ4IDgxMiAwIDU4Mi43NTIgMCAzMDBTMjI5LjI0OC0yMTIgNTEyLTIxMkM3OTQuNzUyLTIxMiAxMDI0IDE3LjI0OCAxMDI0IDMwMFM3OTQuNzUyIDgxMiA1MTIgODEyWk03MjUuMTIgMzMwLjA4QzcxOS4zMTczIDMyNC4yMzQ3IDcxMS4yOTYgMzIwLjYwOCA3MDIuMzc4NyAzMjAuNjA4UzY4NS40NCAzMjQuMjM0NyA2NzkuNjggMzMwLjA4TDU0NCA0NTEuNjhWNzZDNTQ0IDU4LjMzNiA1MjkuNjY0IDQ0IDUxMiA0NFM0ODAgNTguMzM2IDQ4MCA3NlY0NTEuNjhMMzQ0LjMyIDMyOC4xNkMzMzguNTE3MyAzMjIuMjI5MyAzMzAuNDEwNyAzMTguNTYgMzIxLjQ5MzMgMzE4LjU2IDMwMy44MjkzIDMxOC41NiAyODkuNDkzMyAzMzIuODk2IDI4OS40OTMzIDM1MC41NiAyODkuNDkzMyAzNjAuNjI5MyAyOTQuMTQ0IDM2OS41ODkzIDMwMS4zOTczIDM3NS40NzczTDQ5My40NCA1NDcuNjhINTAzLjA0QzUwNS40NzIgNTUxLjAwOCA1MDguNDU4NyA1NTMuNzgxMyA1MTEuODcyIDU1NS45MTQ3TDUxMiA1NTZDNTEzLjYyMTMgNTU2LjI5ODcgNTE1LjQ5ODcgNTU2LjQ2OTMgNTE3LjQ2MTMgNTU2LjQ2OTNTNTIxLjI1ODcgNTU2LjI5ODcgNTIzLjA5MzMgNTU1Ljk1NzNMNTI3LjM2IDU1Nkg1MzIuNDhMNzI0LjQ4IDM4My44NEM3MzMuNTI1MyAzNzguMDggNzM5LjQ1NiAzNjguMDk2IDczOS40NTYgMzU2Ljc0NjcgNzM5LjQ1NiAzNDUuNjUzMyA3MzMuODI0IDMzNS44ODI3IDcyNS4yNDggMzMwLjE2NTNaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMTFEIiB1bmljb2RlPSImI3hFMTFEOyIgZD0iTTUxMiA4MTJDMjI5Ljc2IDgxMiAwIDU4Mi4yNCAwIDMwMFMyMjkuNzYtMjEyIDUxMi0yMTIgMTAyNCAxNy43NiAxMDI0IDMwMCA3OTQuMjQgODEyIDUxMiA4MTJaTTUxMi0xNDhDMjY0Ljk2LTE0OCA2NCA1Mi45NiA2NCAzMDBTMjY0Ljk2IDc0OCA1MTIgNzQ4Qzc1OS4wNCA3NDggOTYwIDU0Ny4wNCA5NjAgMzAwUzc1OS4wNC0xNDggNTEyLTE0OFpNNTMzLjc2IDU0Ny42OEM1MzEuODQgNTQ4Ljk2IDUyOS45MiA1NDkuNiA1MjguNjQgNTUwLjg4IDUyNi43MiA1NTEuNTIgNTI1LjQ0IDU1Mi44IDUyMy41MiA1NTMuNDQgNTIwLjMyIDU1NC43MiA1MTYuNDggNTU1LjM2IDUxMy4yOCA1NTYgNTEyLjY0IDU1NiA1MTIuNjQgNTU2IDUxMiA1NTYgNTEyIDU1NiA1MTEuMzYgNTU2IDUxMS4zNiA1NTYgNTA3LjUyIDU1NiA1MDMuNjggNTU1LjM2IDQ5OS44NCA1NTMuNDQgNDk4LjU2IDU1Mi44IDQ5Ny4yOCA1NTEuNTIgNDk1LjM2IDU1MC44OCA0OTQuMDggNTQ5LjYgNDkyLjE2IDU0OC45NiA0OTAuMjQgNTQ3LjY4TDMwMC44IDM3NS41MkMyODggMzYzLjM2IDI4Ni43MiAzNDMuNTIgMjk4Ljg4IDMzMC4wOCAzMTEuMDQgMzE3LjI4IDMzMC44OCAzMTYgMzQ0LjMyIDMyOC4xNkw0ODAgNDUxLjY4Vjc2QzQ4MCA1OC4wOCA0OTQuMDggNDQgNTEyIDQ0UzU0NCA1OC4wOCA1NDQgNzZWNDUxLjY4TDY4MC4zMiAzMjguMTZDNjg2LjcyIDMyMi40IDY5NC40IDMxOS44NCA3MDIuMDggMzE5Ljg0IDcxMS4wNCAzMTkuODQgNzE5LjM2IDMyMy42OCA3MjUuNzYgMzMwLjA4IDczNy45MiAzNDIuODggNzM2LjY0IDM2My4zNiA3MjMuODQgMzc1LjUyTDUzMy43NiA1NDcuNjhaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMTFFIiB1bmljb2RlPSImI3hFMTFFOyIgZD0iTTk2NC4yNjY3IDQwOS4yMjY3Qzk2NC40OCA0MTAuNzYyNyA5NjQuNTY1MyA0MTIuNTU0NyA5NjQuNTY1MyA0MTQuMzQ2N1M5NjQuNDM3MyA0MTcuOTMwNyA5NjQuMjI0IDQxOS42OEM5NjQuMzA5MyA0MjAuMzYyNyA5NjQuMzUyIDQyMS4zODY3IDk2NC4zNTIgNDIyLjQ1MzNTOTY0LjMwOTMgNDI0LjU0NCA5NjQuMjI0IDQyNS41NjhMOTU5Ljk1NzMgNDMyLjI2NjcgOTUxLjQyNCA0MzkuMDkzMyA1NTMuNzcwNyA4MDAuOTA2N0M1NDYuMjE4NyA4MDcuNzMzMyA1MzYuMTkyIDgxMS45MTQ3IDUyNS4xODQgODExLjkxNDdTNTA0LjE0OTMgODA3LjczMzMgNDk2LjU1NDcgODAwLjkwNjdMOTguMDkwNyA0MzkuOTg5MyA5Mi45NzA3IDQzMy4xNjI3QzkxLjQzNDcgNDMxLjIgOTAuMDI2NyA0MjguOTM4NyA4OC44MzIgNDI2LjU5MiA4OC42NjEzIDQyNS40NCA4OC42MTg3IDQyNC40MTYgODguNjE4NyA0MjMuMzQ5M1M4OC42NjEzIDQyMS4yNTg3IDg4Ljc0NjcgNDIwLjIzNDdDODguNTMzMyA0MTguODI2NyA4OC40NDggNDE3LjA3NzMgODguNDQ4IDQxNS4yNDI3Uzg4LjU3NiA0MTEuNjU4NyA4OC43ODkzIDQwOS45MDkzTDg4Ljc4OTMgNDEwLjEyMjdDODguNzA0IDQwOS4wOTg3IDg4LjY2MTMgNDA3LjkwNCA4OC42NjEzIDQwNi43MDkzUzg4LjcwNCA0MDQuMzIgODguODMyIDQwMy4xMjUzQzg4Ljc0NjcgNDAyLjQ0MjcgODguNjYxMyA0MDEuNDYxMyA4OC42NjEzIDQwMC40OCA4OC42NjEzIDM5NC44NDggOTAuMjgyNyAzODkuNjQyNyA5My4xNDEzIDM4NS4yNDhMOTMuMDU2IDM4MS4xMDkzSDk4LjE3NkMxMDEuMTIgMzc4LjEyMjcgMTA0LjQ5MDcgMzc1LjU2MjcgMTA4LjIwMjcgMzczLjU1NzNMMTA4LjQxNiAzNzMuNDI5M0gzOTYuODQyN1YtMTI2LjYyNEMzOTYuODQyNy0xNzMuNzcwNyA0MzUuMDI5My0yMTEuOTU3MyA0ODIuMTc2LTIxMS45NTczSDU2Ny41MDkzQzYxNC42NTYtMjExLjk1NzMgNjUyLjg0MjctMTczLjc3MDcgNjUyLjg0MjctMTI2LjYyNFYzNjUuNzQ5M0g5MzkuNTYyN0M5NDQuNDY5MyAzNjkuNDE4NyA5NDguNDggMzczLjk0MTMgOTUxLjM4MTMgMzc5LjE4OTNMOTUxLjUwOTMgMzc5LjQwMjdWMzgzLjY2OTNDOTU1LjYwNTMgMzg4LjQ5MDcgOTU4LjEyMjcgMzk0LjcyIDk1OC4zMzYgNDAxLjU0NjcgOTU4LjQyMTMgNDAyLjQ4NTMgOTU4LjQ2NCA0MDMuNTA5MyA5NTguNDY0IDQwNC41NzZTOTU4LjQyMTMgNDA2LjY2NjcgOTU4LjMzNiA0MDcuNjkwN1oiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxMUYiIHVuaWNvZGU9IiYjeEUxMUY7IiBkPSJNNTQ0IDM5NlY3Nkg0ODBWMzk2TDM4NCAzMDAgMzM2IDM0OCA1MTIgNTI0IDY4OCAzNDggNjQwIDMwMFoiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxMjAiIHVuaWNvZGU9IiYjeEUxMjA7IiBkPSJNODk2IDY4NEw4OTYgMzAwIDg5Ni04NCA2MDAuNjQgMTA4IDMyMCAzMDAgNjAwLjY0IDQ5MiA4OTYgNjg0Wk0xMjggNjg0SDE5MlYtODRIMTI4WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTEyMSIgdW5pY29kZT0iJiN4RTEyMTsiIGQ9Ik04MzIgNzQ3LjM2QzgyNC45NiA3NDcuMzYgODE3LjkyIDc0NS40NCA4MTIuMTYgNzQwLjMyTDMwMC4xNiAzMjQuOTZDMjg0LjE2IDMxMi4xNiAyODQuMTYgMjg3Ljg0IDMwMC4xNiAyNzUuMDRMODEyLjE2LTE0MC4zMkM4MTguNTYtMTQ1LjQ0IDgyNS42LTE0Ny4zNiA4MzItMTQ3LjM2IDg0OC42NC0xNDcuMzYgODY0LTEzNC41NiA4NjQtMTE1LjM2VjcxNS4zNkM4NjQgNzMzLjkyIDg0OC42NCA3NDcuMzYgODMyIDc0Ny4zNlpNODAwLTQ4LjE2TDM3MC41NiAzMDAgODAwIDY0OC4xNlYtNDguMTZaTTE2MCA3NDhDMTQyLjA4IDc0OCAxMjggNzMzLjkyIDEyOCA3MTZWLTExNkMxMjgtMTMzLjkyIDE0Mi4wOC0xNDggMTYwLTE0OFMxOTItMTMzLjkyIDE5Mi0xMTZWNzE2QzE5MiA3MzMuOTIgMTc3LjkyIDc0OCAxNjAgNzQ4WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTEyMiIgdW5pY29kZT0iJiN4RTEyMjsiIGQ9Ik01NDQgNTU2SDIzNy40NEwzMTEuMDQgNjI5LjZDMzIzLjg0IDY0Mi40IDMyMy44NCA2NjIuMjQgMzExLjA0IDY3NS4wNFMyNzguNCA2ODcuODQgMjY1LjYgNjc1LjA0TDE4Mi40IDU5MS44NEMxNDUuMjggNTU0LjcyIDE0NS4yOCA0OTMuMjggMTgyLjQgNDU2LjE2TDI2NC45NiAzNzMuNkMyNzEuMzYgMzY3LjIgMjc5LjY4IDM2NCAyODggMzY0UzMwNC42NCAzNjcuMiAzMTAuNCAzNzMuNkMzMjMuMiAzODYuNCAzMjMuMiA0MDYuMjQgMzEwLjQgNDE5LjA0TDIzNy40NCA0OTJINTQ0QzcwMi43MiA0OTIgODMyIDM3Ny40NCA4MzIgMjM2UzcxNy40NC0yMCA1NzYtMjBIMjg4QzI3MC4wOC0yMCAyNTYtMzQuMDggMjU2LTUyUzI3MC4wOC04NCAyODgtODRINTc2Qzc1Mi42NC04NCA4OTYgNTkuMzYgODk2IDIzNlM3MzcuOTIgNTU2IDU0NCA1NTZaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMTIzIiB1bmljb2RlPSImI3hFMTIzOyIgZD0iTTk5Mi0yMEg2NFY2NTJDNjQgNjY5LjkyIDQ5LjkyIDY4NCAzMiA2ODRTMCA2NjkuOTIgMCA2NTJWLTUyQzAtNjkuOTIgMTQuMDgtODQgMzItODRIOTkyQzEwMDkuOTItODQgMTAyNC02OS45MiAxMDI0LTUyUzEwMDkuOTItMjAgOTkyLTIwWk0yMDAuMzIgNzZIMjQ4LjMyQzI2Ni4yNCA3NiAyODAuMzIgOTAuMDggMjgwLjMyIDEwOFY0NjBDMjgwLjMyIDQ3Ny45MiAyNjYuMjQgNDkyIDI0OC4zMiA0OTJIMjAwLjMyQzE4Mi40IDQ5MiAxNjguMzIgNDc3LjkyIDE2OC4zMiA0NjBWMTA4QzE2OC4zMiA5MC4wOCAxODIuNCA3NiAyMDAuMzIgNzZaTTQyNC4zMiA3Nkg0NzIuMzJDNDkwLjI0IDc2IDUwNC4zMiA5MC4wOCA1MDQuMzIgMTA4VjY1MkM1MDQuMzIgNjY5LjkyIDQ5MC4yNCA2ODQgNDcyLjMyIDY4NEg0MjQuMzJDNDA2LjQgNjg0IDM5Mi4zMiA2NjkuOTIgMzkyLjMyIDY1MlYxMDhDMzkyLjMyIDkwLjA4IDQwNi40IDc2IDQyNC4zMiA3NlpNNjQ4LjMyIDc2SDY5Ni4zMkM3MTQuMjQgNzYgNzI4LjMyIDkwLjA4IDcyOC4zMiAxMDhWMzMyQzcyOC4zMiAzNDkuOTIgNzE0LjI0IDM2NCA2OTYuMzIgMzY0SDY0OC4zMkM2MzAuNCAzNjQgNjE2LjMyIDM0OS45MiA2MTYuMzIgMzMyVjEwOEM2MTYuMzIgOTAuMDggNjMwLjQgNzYgNjQ4LjMyIDc2Wk04NzIuMzIgNzZIOTIwLjMyQzkzOC4yNCA3NiA5NTIuMzIgOTAuMDggOTUyLjMyIDEwOFYyMDRDOTUyLjMyIDIyMS45MiA5MzguMjQgMjM2IDkyMC4zMiAyMzZIODcyLjMyQzg1NC40IDIzNiA4NDAuMzIgMjIxLjkyIDg0MC4zMiAyMDRWMTA4Qzg0MC4zMiA5MC4wOCA4NTQuNCA3NiA4NzIuMzIgNzZaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMTI0IiB1bmljb2RlPSImI3hFMTI0OyIgZD0iTTM4NCA1MjIuNzJDNDg3LjUwOTMgNTAzLjczMzMgNTY3Ljg5MzMgNDIzLjM0OTMgNTg2LjYyNCAzMjEuMzc2TDU5MiAyODRDNTkzLjY2NCAyMDAuMzczMyA2MjQuNTk3MyAxMjQuMjk4NyA2NzQuOTQ0IDY1LjI5MDcgNzA3LjY2OTMgMjcuNDQ1MyA3NTUuOTY4IDIuOTk3MyA4MTAuMDI2NyAxLjc2IDgxMi45MjggMS42MzIgODE2LjA4NTMgMS41NDY3IDgxOS4yNDI3IDEuNTQ2NyA4NjkuMDc3MyAxLjU0NjcgOTE0LjczMDcgMTkuNTA5MyA5NTAuMDU4NyA0OS4zMzMzIDk5Ny40NjEzIDkxLjcwMTMgMTAyNy4zNzA3IDE1My40NCAxMDI3LjM3MDcgMjIyLjEzMzMgMTAyNy4zNzA3IDIzNi4wODUzIDEwMjYuMTMzMyAyNDkuNjk2IDEwMjMuNzg2NyAyNjIuOTY1MyAxMDA4IDM3OC41OTIgOTI3LjQ4OCA0NzMuMzk3MyA4MjAuMDUzMyA1MDkuODc3MyA4MTQuMjA4IDU2OS44NjY3IDc4Ni41NiA2MjIuMDkwNyA3NDQuNTc2IDY1OC4xMDEzIDcwNy4yNDI3IDY5Mi41MzMzIDY1Ny41MzYgNzEzLjUyNTMgNjAyLjk2NTMgNzEzLjUyNTMgNTg3LjUyIDcxMy41MjUzIDU3Mi40NTg3IDcxMS44NjEzIDU1Ny45NTIgNzA4LjY2MTMgNTA2Ljk2NTMgNjk1LjUyIDQ2Mi45MzMzIDY2NS44MjQgNDMxLjc0NCA2MjUuNTg5MyA0MjYuNDEwNyA2MTkuNDQ1MyA0MjMuMzgxMyA2MTIuMDIxMyA0MjMuMzgxMyA2MDMuOTE0NyA0MjMuMzgxMyA1OTQuMjI5MyA0MjcuNjkwNyA1ODUuNTI1MyA0MzQuNTE3MyA1NzkuNjM3M0w0MzguNCA1NzkuNTk0N0M0MjIuMTg2NyA1ODMuNjQ4IDQwMy40OTg3IDU4Ni4yMDggMzg0LjI5ODcgNTg2LjYzNDcgMzc4LjE5NzMgNTg3LjAxODcgMzcxLjM3MDcgNTg3LjI3NDcgMzY0LjUwMTMgNTg3LjI3NDdTMzUwLjgwNTMgNTg3LjA2MTMgMzQ0LjA2NCA1ODYuNTkyTDM0NS4wMDI3IDU5Ny41MTQ3QzM0Ny4xMzYgNjIzLjMyOCAzNjIuMTk3MyA2NDUuMjE2IDM4My42NTg3IDY1Ni44MjEzIDM5Mi44MzIgNjYyLjgzNzMgMzk4LjU5MiA2NzIuNjkzMyAzOTguNTkyIDY4My45MTQ3IDM5OC41OTIgNzAxLjY2NCAzODQuMjEzMyA3MTYuMDQyNyAzNjYuNDY0IDcxNi4wNDI3IDM1OS45MzYgNzE2LjA0MjcgMzUzLjgzNDcgNzE0LjA4IDM0OC43NTczIDcxMC43MDkzIDMyNy40NjY3IDY5Ny4wNTYgMzEwLjU3MDcgNjc3Ljg5ODcgMjk5Ljk0NjcgNjU1LjI4NTMgMjg0LjY3MiA2NjEuNzI4IDI2Ny4wOTMzIDY2NS45OTQ3IDI0OC41MzMzIDY2NS45OTQ3IDIzOS44NzIgNjY1Ljk5NDcgMjMxLjQyNCA2NjUuMDU2IDIyMy4yNzQ3IDY2My4zMDY3IDIwOS4yMzczIDY2MC4xMDY3IDE5OC4zMTQ3IDY0Ny4wNTA3IDE5OC4zMTQ3IDYzMS40MzQ3IDE5OC4zMTQ3IDYxMy4zNDQgMjEyLjk5MiA1OTguNjY2NyAyMzEuMDgyNyA1OTguNjY2NyAyMzMuNTU3MyA1OTguNjY2NyAyMzUuOTg5MyA1OTguOTY1MyAyMzguMzM2IDU5OS40NzczIDI0MC40NjkzIDU5OS43NzYgMjQzLjE1NzMgNTk5Ljk4OTMgMjQ1Ljg4OCA1OTkuOTg5MyAyNjMuOTM2IDU5OS45ODkzIDI4MC4wNjQgNTkxLjU4NCAyOTAuNTE3MyA1NzguNDQyN0wyOTAuNjAyNyA1NzguMzE0N0MxNjguMzYyNyA1NTAuMTU0NyA5My40ODI3IDQzOC43OTQ3IDUwLjYwMjcgMzQxLjUxNDcgMTcuMzIyNyAyNjYuNjM0Ny0zMC4wMzczIDEyNS44MzQ3IDI2LjI4MjcgMjQuNzE0NyA1NS44OTMzLTM2LjM0MTMgMTE1LjI0MjctNzguODM3MyAxODUuMDAyNy04NC4wNDI3TDg4OS42NDI3LTg0LjA4NTNDOTA3LjMwNjctODQuMDg1MyA5MjEuNjQyNy02OS43NDkzIDkyMS42NDI3LTUyLjA4NTNTOTA3LjMwNjctMjAuMDg1MyA4ODkuNjQyNy0yMC4wODUzSDE4NS42NDI3QzEzOC43OTQ3LTE1LjE3ODcgOTkuODQgMTQuMzg5MyA4MS42NjQgNTUuMjY0IDM3LjE2MjcgMTM1LjQzNDcgODUuMTYyNyAyNjQuMDc0NyAxMDguMjAyNyAzMTUuOTE0NyAxNzQuMTIyNyA0NjMuMTE0NyAyNjUuMDAyNyA1MzMuNTE0NyAzODQuMDQyNyA1MjIuNjM0N1pNNDgwIDU4Mi44OEM1MDIuODI2NyA2MTMuODU2IDUzNS4yOTYgNjM2LjUxMiA1NzIuODg1MyA2NDYuNjI0IDU4Mi45NTQ3IDY0OC44IDU5My4xNTIgNjQ5Ljg2NjcgNjAzLjYwNTMgNjQ5Ljg2NjcgNjQxLjQ5MzMgNjQ5Ljg2NjcgNjc2LjA1MzMgNjM1LjYxNiA3MDIuMjA4IDYxMi4xOTIgNzMzLjk5NDcgNTgzLjM5MiA3NTMuOTYyNyA1NDEuNzkyIDc1My45NjI3IDQ5NS40OTg3IDc1My45NjI3IDQ5NC4yNjEzIDc1My45NjI3IDQ5My4wMjQgNzUzLjkyIDQ5MS43ODY3TDc1My45MiA0NTkuMzE3MyA3NzguODggNDU1LjQ3NzNDODc0LjE1NDcgNDMyLjE4MTMgOTQ2LjEzMzMgMzUzLjk3MzMgOTU5Ljg3MiAyNTcuMDc3MyA5NjEuNzkyIDI0Ni41ODEzIDk2Mi44MTYgMjM1Ljk1NzMgOTYyLjgxNiAyMjUuMDc3MyA5NjIuODE2IDE3Mi41NTQ3IDkzOS4yMjEzIDEyNS41Nzg3IDkwMi4wNTg3IDk0LjA5MDcgODgwLjU1NDcgNzcuNTM2IDg1My41NDY3IDY3LjcyMjcgODI0LjIzNDcgNjcuNzIyNyA4MjAuMDEwNyA2Ny43MjI3IDgxNS43ODY3IDY3LjkzNiA4MTEuNjQ4IDY4LjMyIDgxMi4xNiA2OC4yNzczIDgxMi4xNiA2OC4yNzczIDgxMi4xNiA2OC4yNzczIDc3Ni41NzYgNjguMjc3MyA3NDQuNjE4NyA4My44MDggNzIyLjY4OCAxMDguNDY5MyA2ODMuMzA2NyAxNTcuMjM3MyA2NTkuMjg1MyAyMTkuNjU4NyA2NTguNjAyNyAyODcuNjI2N0w2NTIuODQyNyAzMzAuMDM3M0M2MjkuODg4IDQ0MS43ODEzIDU1Mi41MzMzIDUzMS40MjQgNDUwLjI2MTMgNTcxLjE4OTMgNDQ5LjE1MiA1NzEuODI5MyA0NTAuNDc0NyA1NzEuNzQ0IDQ1MS43OTczIDU3MS43NDQgNDYyLjAzNzMgNTcxLjc0NCA0NzEuMjEwNyA1NzYuMjY2NyA0NzcuMzk3MyA1ODMuNDM0N1oiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxMjUiIHVuaWNvZGU9IiYjeEUxMjU7IiBkPSJNMzc1LjY4LTIxMkgxMDIuNEM0NS44NjY3LTIxMiAwLTE2Ni4xMzMzIDAtMTA5LjZWLTEwOS42IDE2My42OEMwIDIyMC4yMTMzIDQ1Ljg2NjcgMjY2LjA4IDEwMi40IDI2Ni4wOFYyNjYuMDhIMzc1LjY4QzQzMi4yMTMzIDI2Ni4wOCA0NzguMDggMjIwLjIxMzMgNDc4LjA4IDE2My42OFYxNjMuNjgtMTA5LjZDNDc4LjA4LTE2Ni4xMzMzIDQzMi4yMTMzLTIxMiAzNzUuNjgtMjEyVi0yMTJaTTM3NS42OCAzMzMuOTJIMTAyLjRDNDUuODY2NyAzMzMuOTIgMCAzNzkuNzg2NyAwIDQzNi4zMlY0MzYuMzIgNzA5LjZDMCA3NjYuMTMzMyA0NS44NjY3IDgxMiAxMDIuNCA4MTJWODEySDM3NS42OEM0MzIuMjEzMyA4MTIgNDc4LjA4IDc2Ni4xMzMzIDQ3OC4wOCA3MDkuNlY3MDkuNiA0MzYuMzJDNDc4LjA4IDM3OS43ODY3IDQzMi4yMTMzIDMzMy45MiAzNzUuNjggMzMzLjkyVjMzMy45MlpNOTIxLjYtMjEySDY0OC4zMkM1OTEuNzg2Ny0yMTIgNTQ1LjkyLTE2Ni4xMzMzIDU0NS45Mi0xMDkuNlYtMTA5LjYgMTYzLjY4QzU0NS45MiAyMjAuMjEzMyA1OTEuNzg2NyAyNjYuMDggNjQ4LjMyIDI2Ni4wOFYyNjYuMDhIOTIxLjZDOTc4LjEzMzMgMjY2LjA4IDEwMjQgMjIwLjIxMzMgMTAyNCAxNjMuNjhWMTYzLjY4LTEwOS42QzEwMjQtMTY2LjEzMzMgOTc4LjEzMzMtMjEyIDkyMS42LTIxMlYtMjEyWk05MjEuNiAzMzMuOTJINjQ4LjMyQzU5MS43ODY3IDMzMy45MiA1NDUuOTIgMzc5Ljc4NjcgNTQ1LjkyIDQzNi4zMlY0MzYuMzIgNzA5LjZDNTQ1LjkyIDc2Ni4xMzMzIDU5MS43ODY3IDgxMiA2NDguMzIgODEySDkyMS42Qzk3OC4xMzMzIDgxMiAxMDI0IDc2Ni4xMzMzIDEwMjQgNzA5LjZWNzA5LjYgNDM2LjMyQzEwMjQgMzc5Ljc4NjcgOTc4LjEzMzMgMzMzLjkyIDkyMS42IDMzMy45MlYzMzMuOTJaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMTI2IiB1bmljb2RlPSImI3hFMTI2OyIgZD0iTTIzOC4wOCA3ODBIMjcwLjA4QzI4Ny43NDQgNzgwIDMwMi4wOCA3NjUuNjY0IDMwMi4wOCA3NDhWNjIwQzMwMi4wOCA2MDIuMzM2IDI4Ny43NDQgNTg4IDI3MC4wOCA1ODhIMjM4LjA4QzIyMC40MTYgNTg4IDIwNi4wOCA2MDIuMzM2IDIwNi4wOCA2MjBWNzQ4QzIwNi4wOCA3NjUuNjY0IDIyMC40MTYgNzgwIDIzOC4wOCA3ODBaTTc1MiA3ODBINzg0QzgwMS42NjQgNzgwIDgxNiA3NjUuNjY0IDgxNiA3NDhWNjIwQzgxNiA2MDIuMzM2IDgwMS42NjQgNTg4IDc4NCA1ODhINzUyQzczNC4zMzYgNTg4IDcyMCA2MDIuMzM2IDcyMCA2MjBWNzQ4QzcyMCA3NjUuNjY0IDczNC4zMzYgNzgwIDc1MiA3ODBaTTk5MiA0NDRIMzJDMTQuMzM2IDQ0NCAwIDQyOS42NjQgMCA0MTJWLTEwMEMwLTE1My4wMzQ3IDQyLjk2NTMtMTk2IDk2LTE5Nkg5MjhDOTgxLjAzNDctMTk2IDEwMjQtMTUzLjAzNDcgMTAyNC0xMDBWNDEyQzEwMjQgNDI5LjY2NCAxMDA5LjY2NCA0NDQgOTkyIDQ0NFpNODAwLTRIMjI0QzIwNi4zMzYtNCAxOTIgMTAuMzM2IDE5MiAyOFMyMDYuMzM2IDYwIDIyNCA2MEg4MDBDODE3LjY2NCA2MCA4MzIgNDUuNjY0IDgzMiAyOFM4MTcuNjY0LTQgODAwLTRaTTgwMCAxODhIMzUyQzMzNC4zMzYgMTg4IDMyMCAyMDIuMzM2IDMyMCAyMjBTMzM0LjMzNiAyNTIgMzUyIDI1Mkg4MDBDODE3LjY2NCAyNTIgODMyIDIzNy42NjQgODMyIDIyMFM4MTcuNjY0IDE4OCA4MDAgMTg4Wk05MjggNzAwSDg0OFY2MjBDODQ4IDU4NC42NzIgODE5LjMyOCA1NTYgNzg0IDU1Nkg3NTJDNzE2LjY3MiA1NTYgNjg4IDU4NC42NzIgNjg4IDYyMFY3MDBIMzM0LjA4VjYyMEMzMzQuMDggNTg0LjY3MiAzMDUuNDA4IDU1NiAyNzAuMDggNTU2SDIzOC4wOEMyMDIuNzUyIDU1NiAxNzQuMDggNTg0LjY3MiAxNzQuMDggNjIwVjcwMEg5NkM0Mi45NjUzIDcwMCAwIDY1Ny4wMzQ3IDAgNjA0VjU0MEMwIDUyMi4zMzYgMTQuMzM2IDUwOCAzMiA1MDhIOTkyQzEwMDkuNjY0IDUwOCAxMDI0IDUyMi4zMzYgMTAyNCA1NDBWNjA0QzEwMjQgNjU3LjAzNDcgOTgxLjAzNDcgNzAwIDkyOCA3MDBaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMTI3IiB1bmljb2RlPSImI3hFMTI3OyIgZD0iTTkyOCA3MDBIODE2Vjc0OEM4MTYgNzY1LjY2NCA4MDEuNjY0IDc4MCA3ODQgNzgwSDc1MkM3MzQuMzM2IDc4MCA3MjAgNzY1LjY2NCA3MjAgNzQ4VjcwMEgzMDIuMDhWNzQ4QzMwMi4wOCA3NjUuNjY0IDI4Ny43NDQgNzgwIDI3MC4wOCA3ODBIMjM4LjA4QzIyMC40MTYgNzgwIDIwNi4wOCA3NjUuNjY0IDIwNi4wOCA3NDhWNzAwSDk2QzQyLjk2NTMgNzAwIDAgNjU3LjAzNDcgMCA2MDRWLTEwMEMwLTE1My4wMzQ3IDQyLjk2NTMtMTk2IDk2LTE5Nkg5MjhDOTgxLjAzNDctMTk2IDEwMjQtMTUzLjAzNDcgMTAyNC0xMDBWNjA0QzEwMjQgNjU3LjAzNDcgOTgxLjAzNDcgNzAwIDkyOCA3MDBaTTY0IDYwNEM2NCA2MjEuNjY0IDc4LjMzNiA2MzYgOTYgNjM2SDIwNi4wOFY2MjBDMjA2LjA4IDYwMi4zMzYgMjIwLjQxNiA1ODggMjM4LjA4IDU4OEgyNzAuMDhDMjg3Ljc0NCA1ODggMzAyLjA4IDYwMi4zMzYgMzAyLjA4IDYyMFY2MzZINzIwVjYyMEM3MjAgNjAyLjMzNiA3MzQuMzM2IDU4OCA3NTIgNTg4SDc4NEM4MDEuNjY0IDU4OCA4MTYgNjAyLjMzNiA4MTYgNjIwVjYzNkg5MjhDOTQ1LjY2NCA2MzYgOTYwIDYyMS42NjQgOTYwIDYwNFY1MDhINjRaTTkyOC0xMzJIOTZDNzguMzM2LTEzMiA2NC0xMTcuNjY0IDY0LTEwMFY0NDRIOTYwVi0xMDBDOTYwLTExNy42NjQgOTQ1LjY2NC0xMzIgOTI4LTEzMlpNODAwIDI1MkgzNTJDMzM0LjMzNiAyNTIgMzIwIDIzNy42NjQgMzIwIDIyMFMzMzQuMzM2IDE4OCAzNTIgMTg4SDgwMEM4MTcuNjY0IDE4OCA4MzIgMjAyLjMzNiA4MzIgMjIwUzgxNy42NjQgMjUyIDgwMCAyNTJaTTgwMCA2MEgyMjRDMjA2LjMzNiA2MCAxOTIgNDUuNjY0IDE5MiAyOFMyMDYuMzM2LTQgMjI0LTRIODAwQzgxNy42NjQtNCA4MzIgMTAuMzM2IDgzMiAyOFM4MTcuNjY0IDYwIDgwMCA2MFoiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxMjgiIHVuaWNvZGU9IiYjeEUxMjg7IiBkPSJNOTkxLjk1NzMgNzEuMDkzM0w3NTYuODY0IDMwNi4xODY3QzczOC4xNzYgMzI1LjE3MzMgNzEyLjcwNCAzMzcuNDE4NyA2ODQuMzczMyAzMzguOTEyIDY4My45MDQgMzM4LjkxMiA2ODMuNjkwNyAzMzguOTEyIDY4My40NzczIDMzOC45MTIgNjU1LjE4OTMgMzM4LjkxMiA2MjkuNTg5MyAzMjcuMjIxMyA2MTEuMzcwNyAzMDguMzYyN0w1ODYuNTgxMyAyODMuNTczMyA0OTMuNDQgMzcyLjM2MjcgNTE5LjYzNzMgMzk4LjU2QzUzOS4zNDkzIDQxOC4zMTQ3IDU1MS41NTIgNDQ1LjU3ODcgNTUxLjU1MiA0NzUuNzAxM1M1MzkuMzQ5MyA1MzMuMDg4IDUxOS42MzczIDU1Mi44NDI3TDI5MC4zODkzIDc3OS45MTQ3QzI3MC42MzQ3IDc5OS42MjY3IDI0My4zNzA3IDgxMS44MjkzIDIxMy4yNDggODExLjgyOTNTMTU1Ljg2MTMgNzk5LjYyNjcgMTM2LjEwNjcgNzc5LjkxNDdMMzIuMDQyNyA2NzUuODUwN0MxMi4zMzA3IDY1Ni4wOTYgMC4xMjggNjI4LjgzMiAwLjEyOCA1OTguNzA5M1MxMi4zMzA3IDU0MS4zMjI3IDMyLjA0MjcgNTIxLjU2OEwyNjEuMjkwNyAyOTIuMzJDMjgxLjA0NTMgMjcyLjYwOCAzMDguMzA5MyAyNjAuNDA1MyAzMzguNDMyIDI2MC40MDUzUzM5NS44MTg3IDI3Mi42MDggNDE1LjU3MzMgMjkyLjMyTDQzOS41OTQ3IDMxOC41MTczIDUyOC4zODQgMjMxLjkwNCA1MDMuNjM3MyAyMDcuMTU3M0M0ODQuOTA2NyAxODguNTU0NyA0NzMuMjU4NyAxNjIuODY5MyA0NzMuMDg4IDEzNC40MTA3IDQ3NC41ODEzIDEwNS43ODEzIDQ4Ni44MjY3IDgwLjI2NjcgNTA1LjgxMzMgNjEuNjIxM0w3NDAuOTA2Ny0xNzMuNDcyQzc2MC43ODkzLTE5My41MjUzIDc4OC4zMDkzLTIwNi4wMjY3IDgxOC43MzA3LTIwNi4yNCA4NDcuMjMyLTIwNS45ODQgODcyLjkxNzMtMTk0LjMzNiA4OTEuNTYyNy0xNzUuNjkwN0w5OTIuNzI1My03NC41MjhDMTAxMC4wNDgtNTUuNDk4NyAxMDIwLjY3Mi0zMC4wNjkzIDEwMjAuNjcyLTIuMTY1MyAxMDIwLjY3MiAyNi4xMjI3IDEwMDkuNzQ5MyA1MS44NTA3IDk5MS45MTQ3IDcxLjA5MzNaTTM2Ni44MDUzIDM0NC4wMzJDMzYwLjE0OTMgMzM3LjU0NjcgMzUxLjAxODcgMzMzLjU3ODcgMzQwLjk0OTMgMzMzLjU3ODdTMzIxLjc5MiAzMzcuNTg5MyAzMTUuMDkzMyAzNDQuMDc0N0w4My42NjkzIDU3My4zMjI3Qzc3LjAxMzMgNTc5LjkzNiA3Mi45MTczIDU4OS4wNjY3IDcyLjkxNzMgNTk5LjE3ODdTNzcuMDEzMyA2MTguNDIxMyA4My42NjkzIDYyNC45OTJMMTg3LjczMzMgNzI4LjMzMDdDMTk0LjM0NjcgNzM0Ljk4NjcgMjAzLjQ3NzMgNzM5LjA4MjcgMjEzLjU4OTMgNzM5LjA4MjdTMjMyLjgzMiA3MzQuOTg2NyAyMzkuNDAyNyA3MjguMzMwN0w0NjcuOTI1MyA0OTkuMDgyN0M0NzQuNTgxMyA0OTIuNDY5MyA0NzguNjc3MyA0ODMuMzM4NyA0NzguNjc3MyA0NzMuMjI2N1M0NzQuNTgxMyA0NTMuOTg0IDQ2Ny45MjUzIDQ0Ny40MTMzTDQzOS41NTIgNDIxLjk0MTMgNDA1LjMzMzMgNDU2LjE2QzM5OC43MiA0NjIuNzczMyAzODkuNTg5MyA0NjYuODY5MyAzNzkuNDc3MyA0NjYuODY5MyAzNTkuMjk2IDQ2Ni44NjkzIDM0Mi45NTQ3IDQ1MC41MjggMzQyLjk1NDcgNDMwLjM0NjcgMzQyLjk1NDcgNDIwLjI3NzMgMzQ3LjA1MDcgNDExLjEwNCAzNTMuNjY0IDQwNC40OTA3TDM5MC4wNTg3IDM3Mi40NDhaTTk0NS40MDgtMzAuMDY5M0w4NDQuMjQ1My0xMzEuMjMyQzgzNy44NDUzLTEzNy40MTg3IDgyOS4wOTg3LTE0MS4yMTYgODE5LjQ5ODctMTQxLjIxNlM4MDEuMTUyLTEzNy40MTg3IDc5NC43NTItMTMxLjIzMkw1NTcuNDgyNyAxMDYuNzYyN0M1NTAuODI2NyAxMTMuNTA0IDU0Ni42ODggMTIyLjcyIDU0Ni41NiAxMzIuOTYgNTQ2Ljc3MzMgMTQxLjE5NDcgNTUwLjA1ODcgMTQ4LjU3NiA1NTUuMzA2NyAxNTQuMTIyN0w1ODAuMDUzMyAxNzguODY5MyA2MTcuODk4NyAxNDEuMDI0QzYyNC41MTIgMTM0LjQxMDcgNjMzLjY0MjcgMTMwLjMxNDcgNjQzLjc1NDcgMTMwLjMxNDcgNjYzLjkzNiAxMzAuMzE0NyA2ODAuMjc3MyAxNDYuNjU2IDY4MC4yNzczIDE2Ni44MzczIDY4MC4yNzczIDE3Ni45MDY3IDY3Ni4xODEzIDE4Ni4wOCA2NjkuNTY4IDE5Mi42OTMzTDYzMS43MjI3IDIzMC41Mzg3IDY1Ny45MiAyNTYuNzM2QzY2My41NTIgMjYyLjE1NDcgNjcxLjE4OTMgMjY1LjQ4MjcgNjc5LjYzNzMgMjY1LjQ4MjcgNjc5LjkzNiAyNjUuNDgyNyA2ODAuMjM0NyAyNjUuNDgyNyA2ODAuNTMzMyAyNjUuNDgyN0w2ODAuNDkwNyAyNjUuNDgyN0M2OTAuNzMwNyAyNjUuMzU0NyA2OTkuOTQ2NyAyNjEuMjE2IDcwNi42ODggMjU0LjU2TDk0MS43Mzg3IDE5LjUwOTNDOTQ4LjEzODcgMTMuMDY2NyA5NTIuMTA2NyA0LjE5MiA5NTIuMTA2Ny01LjYyMTMgOTUyLjEwNjctMTUuMDUwNyA5NDguNDM3My0yMy42MjY3IDk0Mi40NjQtMzAuMDI2N1oiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxMjkiIHVuaWNvZGU9IiYjeEUxMjk7IiBkPSJNNzA0IDQ2MEw3NTIgNDEyIDQ0OCAxMDggMjcyIDI4NCAzMjAgMzMyIDQ0OCAyMDRaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMTJBIiB1bmljb2RlPSImI3hFMTJBOyIgZD0iTTUxMiA3NDhDMjY0IDc0OCA2NCA1NDggNjQgMzAwUzI2NC0xNDggNTEyLTE0OCA5NjAgNTIgOTYwIDMwMCA3NjAgNzQ4IDUxMiA3NDhaTTQ0OCAxMDhMMjcyIDI4NCAzMjAgMzMyIDQ0OCAyMDQgNzA0IDQ2MCA3NTIgNDEyIDQ0OCAxMDhaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMTJCIiB1bmljb2RlPSImI3hFMTJCOyIgZD0iTTUxMiA3NDhDNzYwIDc0OCA5NjAgNTQ4IDk2MCAzMDBTNzYwLTE0OCA1MTItMTQ4IDY0IDUyIDY0IDMwMCAyNjQgNzQ4IDUxMiA3NDhaTTUxMiA2ODRDMjk5LjIgNjg0IDEyOCA1MTIuOCAxMjggMzAwIDEyOCA4Ny4yIDI5OS4yLTg0IDUxMC40LTg1LjYgNjEyLjgtODUuNiA3MTAuNC00NS42IDc4NCAyOCA5MzQuNCAxNzguNCA5MzQuNCA0MjEuNiA3ODUuNiA1NzAuNCA3ODUuNiA1NzAuNCA3ODUuNiA1NzAuNCA3ODQgNTcyIDcxMiA2NDQgNjE0LjQgNjg0IDUxMiA2ODRaTTcwNCA0NjBMNzUyIDQxMiA0NDggMTA4IDI3MiAyODQgMzIwIDMzMiA0NDggMjA0WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTEyQyIgdW5pY29kZT0iJiN4RTEyQzsiIGQ9Ik01MTIgODEyQzQ5NC4wOCA4MTIgNDgwIDc5Ny45MiA0ODAgNzgwUzQ5NC4wOCA3NDggNTEyIDc0OEM3NTkuMDQgNzQ4IDk2MCA1NDcuMDQgOTYwIDMwMFM3NTkuMDQtMTQ4IDUxMi0xNDhDNDk0LjA4LTE0OCA0ODAtMTYyLjA4IDQ4MC0xODBTNDk0LjA4LTIxMiA1MTItMjEyQzc5NC4yNC0yMTIgMTAyNCAxNy43NiAxMDI0IDMwMFM3OTQuMjQgODEyIDUxMiA4MTJaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMTJEIiB1bmljb2RlPSImI3hFMTJEOyIgZD0iTTUxMiA4MTJDNDk0LjA4IDgxMiA0ODAgNzk3LjkyIDQ4MCA3ODBTNDk0LjA4IDc0OCA1MTIgNzQ4Qzc1OS4wNCA3NDggOTYwIDU0Ny4wNCA5NjAgMzAwIDk2MCAyODIuMDggOTc0LjA4IDI2OCA5OTIgMjY4UzEwMjQgMjgyLjA4IDEwMjQgMzAwQzEwMjQgNTgyLjI0IDc5NC4yNCA4MTIgNTEyIDgxMloiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxMkUiIHVuaWNvZGU9IiYjeEUxMkU7IiBkPSJNNTEyIDMwME02NCAzMDBBNDQ4IDQ0OCAwIDEgMSA5NjAgMzAwIDQ0OCA0NDggMCAxIDEgNjQgMzAwWiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTEyRiIgdW5pY29kZT0iJiN4RTEyRjsiIGQ9Ik01MTIgNjg0QTM4NCAzODQgMCAxIDAgMTI4IDMwMCAzODQgMzg0IDAgMCAwIDUxMiA2ODRNNTEyIDc0OEE0NDggNDQ4IDAgMSAxIDk2MCAzMDAgNDQ4IDQ0OCAwIDAgMSA1MTIgNzQ4WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTEzMCIgdW5pY29kZT0iJiN4RTEzMDsiIGQ9Ik0xMDI0IDIzNkMxMDI0LjA4NTMgMjM2Ljg1MzMgMTAyNC4xNzA3IDIzNy44NzczIDEwMjQuMTcwNyAyMzguODU4N1MxMDI0LjEyOCAyNDAuODY0IDEwMjQgMjQxLjg0NTNMMTAyNCAyNDYuODM3MyA4NTIuNDggNDU5Ljk1NzMgODQ4IDQ2My43OTczSDU3NkM1NDAuNjcyIDQ2My43OTczIDUxMiA0MzUuMTI1MyA1MTIgMzk5Ljc5NzNWLTE0MS42NDI3QzUxMi0xODAuNTEyIDU0My41MzA3LTIxMi4wNDI3IDU4Mi40LTIxMi4wNDI3SDk1NC4yNEM5OTIuNzY4LTIxMi4wNDI3IDEwMjQtMTgwLjgxMDcgMTAyNC0xNDIuMjgyN1YyMzUuOTU3M1pNNjQwIDUzNC44OEM2NzUuMzI4IDUzNC44OCA3MDQgNTYzLjU1MiA3MDQgNTk4Ljg4VjcxNkM3MDQgNzY5LjAzNDcgNjYxLjAzNDcgODEyIDYwOCA4MTJIOTZDNDIuOTY1MyA4MTIgMCA3NjkuMDM0NyAwIDcxNlYxMkMwLTQxLjAzNDcgNDIuOTY1My04NCA5Ni04NEgzODRDNDE5LjMyOC04NCA0NDgtNTUuMzI4IDQ0OC0yMFY0NTUuNTJDNDQ4IDQ1NS41MiA0NDggNDU1LjUyIDQ0OCA0NTUuNTIgNDQ4IDQ5OS4xMjUzIDQ4My4xNTczIDUzNC40OTYgNTI2LjY3NzMgNTM0Ljg4Wk00ODAgNjIwSDIyNEMyMDYuMzM2IDYyMCAxOTIgNjM0LjMzNiAxOTIgNjUyUzIwNi4zMzYgNjg0IDIyNCA2ODRINDgwQzQ5Ny42NjQgNjg0IDUxMiA2NjkuNjY0IDUxMiA2NTJTNDk3LjY2NCA2MjAgNDgwIDYyMFoiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxMzEiIHVuaWNvZGU9IiYjeEUxMzE7IiBkPSJNMTAyNCAyOTMuNkMxMDIzLjc0NCAyOTguNDIxMyAxMDIyLjA4IDMwMi44MTYgMTAxOS40NzczIDMwNi40ODUzTDEwMTkuNTIgMzA5LjYgODMyIDU0My44NCA4MjYuODggNTQ4LjMySDcwNFY3MjAuNDhDNzA0IDcyMC42NTA3IDcwNCA3MjAuOTA2NyA3MDQgNzIxLjEyIDcwNCA3NzEuMDgyNyA2NjMuNjggODExLjYxNiA2MTMuODAyNyA4MTJIOTAuMjRDNDAuMzIgODExLjY1ODcgMCA3NzEuMDgyNyAwIDcyMS4xMiAwIDcyMC45MDY3IDAgNzIwLjY1MDcgMCA3MjAuNDM3M1Y3LjUyQzAgNy4zNDkzIDAgNy4wOTMzIDAgNi44OCAwLTQzLjA4MjcgNDAuMzItODMuNjE2IDkwLjE5NzMtODRINDQ4Vi0xMzMuOTJDNDQ4LjM0MTMtMTc3LjE0MTMgNDgzLjQ1Ni0yMTIgNTI2LjcyLTIxMiA1MjYuNzItMjEyIDUyNi43Mi0yMTIgNTI2LjcyLTIxMkg5NDUuOTJDOTg5LjE0MTMtMjExLjY1ODcgMTAyNC0xNzYuNTQ0IDEwMjQtMTMzLjI4IDEwMjQtMTMzLjI4IDEwMjQtMTMzLjI4IDEwMjQtMTMzLjI4VjI4OS4xMkMxMDI0LjA0MjcgMjg5LjgwMjcgMTAyNC4wODUzIDI5MC41NzA3IDEwMjQuMDg1MyAyOTEuMzM4N1MxMDI0LjA0MjcgMjkyLjkxNzMgMTAyNCAyOTMuNjg1M1pNNDQzLjUyLTIwSDkwLjI0Qzc1LjY0OC0xOS42NTg3IDY0LTcuNzU0NyA2NCA2Ljg4IDY0IDcuMDkzMyA2NCA3LjM0OTMgNjQgNy41NjI3TDY0IDcyMC40OEM2NCA3MjAuNjkzMyA2NCA3MjAuOTA2NyA2NCA3MjEuMTIgNjQgNzM1Ljc1NDcgNzUuNjkwNyA3NDcuNjU4NyA5MC4xOTczIDc0OEw2MTMuNzYgNzQ4QzYyOC4zNTIgNzQ3LjY1ODcgNjQwIDczNS43NTQ3IDY0MCA3MjEuMTIgNjQwIDcyMC45MDY3IDY0MCA3MjAuNjUwNyA2NDAgNzIwLjQzNzNMNjQwIDU1Nkg1MjYuNzJDNDgzLjI0MjcgNTU2IDQ0OCA1MjAuNzU3MyA0NDggNDc3LjI4Vi0yMFpNOTQ1LjkyLTE0OEg1MjYuNzJDNTE4LjU3MDctMTQ4IDUxMi0xNDEuNDI5MyA1MTItMTMzLjI4VjQ3Ny4yOEM1MTIgNDg1LjQyOTMgNTE4LjU3MDcgNDkyIDUyNi43MiA0OTJINzkwLjRMOTYwIDI3OC4yNFYtMTMzLjI4Qzk2MC0xNDEuNDI5MyA5NTMuNDI5My0xNDggOTQ1LjI4LTE0OFpNNTEyIDY1MkM1MTIgNjY5LjY2NCA0OTcuNjY0IDY4NCA0ODAgNjg0SDIyNEMyMDYuMzM2IDY4NCAxOTIgNjY5LjY2NCAxOTIgNjUyUzIwNi4zMzYgNjIwIDIyNCA2MjBINDgwQzQ5Ny42NjQgNjIwIDUxMiA2MzQuMzM2IDUxMiA2NTJaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMTMyIiB1bmljb2RlPSImI3hFMTMyOyIgZD0iTTUxMiA3NDhDMjY0IDc0OCA2NCA1NDggNjQgMzAwUzI2NC0xNDggNTEyLTE0OCA5NjAgNTIgOTYwIDMwMCA3NjAgNzQ4IDUxMiA3NDhaTTYyNS42IDEzMkw0NDggMjY4VjU1Nkg1MTJWMzAwTDY2NCAxODMuMiA2MjUuNiAxMzJaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMTMzIiB1bmljb2RlPSImI3hFMTMzOyIgZD0iTTUxMiA2ODRDNzI0LjggNjg0IDg5NiA1MTIuOCA4OTYgMzAwUzcyNC44LTg0IDUxMi04NCAxMjggODcuMiAxMjggMzAwIDI5OS4yIDY4NCA1MTIgNjg0TTUxMiA3NDhDMjY0IDc0OCA2NCA1NDggNjQgMzAwUzI2NC0xNDggNTEyLTE0OCA5NjAgNTIgOTYwIDMwMCA3NjAgNzQ4IDUxMiA3NDhaTTUxMiAzMDBMNTEyIDU1NiA0NDggNTU2IDQ0OCAyNjggNjI1LjYgMTMyIDY2NCAxODMuMloiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxMzQiIHVuaWNvZGU9IiYjeEUxMzQ7IiBkPSJNNTEyIDc0OEMyNjQgNzQ4IDY0IDU0OCA2NCAzMDBTMjY0LTE0OCA1MTItMTQ4IDk2MCA1MiA5NjAgMzAwIDc2MCA3NDggNTEyIDc0OFpNNjkyLjggMTY0TDY0OCAxMTkuMiA1MTIgMjU1LjIgMzc2IDExOS4yIDMzMS4yIDE2NCA0NjcuMiAzMDAgMzMxLjIgNDM2IDM3NiA0ODAuOCA1MTIgMzQ0LjggNjQ4IDQ4MC44IDY5Mi44IDQzNiA1NTYuOCAzMDAgNjkyLjggMTY0WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTEzNSIgdW5pY29kZT0iJiN4RTEzNTsiIGQ9Ik01MTIgNjg0QzcyNC44IDY4NCA4OTYgNTEyLjggODk2IDMwMFM3MjQuOC04NCA1MTItODQgMTI4IDg3LjIgMTI4IDMwMCAyOTkuMiA2ODQgNTEyIDY4NE01MTIgNzQ4QzI2NCA3NDggNjQgNTQ4IDY0IDMwMFMyNjQtMTQ4IDUxMi0xNDggOTYwIDUyIDk2MCAzMDAgNzYwIDc0OCA1MTIgNzQ4Wk02NDggNDgwLjhMNjkyLjggNDM2IDU1Ni44IDMwMCA2OTIuOCAxNjQgNjQ4IDExOS4yIDUxMiAyNTUuMiAzNzYgMTE5LjIgMzMxLjIgMTY0IDQ2Ny4yIDMwMCAzMzEuMiA0MzYgMzc2IDQ4MC44IDUxMiAzNDQuOCA2NDggNDgwLjhaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMTM2IiB1bmljb2RlPSImI3hFMTM2OyIgZD0iTTY3OC40IDUxNC40TDUxMiAzNDQuOCAzNDUuNiA1MTQuNCAyOTcuNiA0NjYuNCA0NjcuMiAzMDAgMjk3LjYgMTMzLjYgMzQ1LjYgODUuNiA1MTIgMjU1LjIgNjc4LjQgODUuNiA3MjYuNCAxMzMuNiA1NTYuOCAzMDAgNzI2LjQgNDY2LjRaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMTM3IiB1bmljb2RlPSImI3hFMTM3OyIgZD0iTTY3MiA1ODhWNjUyQzY3MiA2ODcuMiA2NDMuMiA3MTYgNjA4IDcxNkg0MTZDMzgwLjggNzE2IDM1MiA2ODcuMiAzNTIgNjUyVjU4OEg5NlY1MjRIMjA4Vi01MkMyMDgtODcuMiAyMzYuOC0xMTYgMjcyLTExNkg3NTJDNzg3LjItMTE2IDgxNi04Ny4yIDgxNi01MlY1MjRIOTI4VjU4OEg2NzJaTTQxNiA2MzZDNDE2IDY0NS42IDQyMi40IDY1MiA0MzIgNjUySDU5MkM2MDEuNiA2NTIgNjA4IDY0NS42IDYwOCA2MzZWNTg4SDQxNlY2MzZaTTQ0OCA2MEgzODRWNDEySDQ0OFY2MFpNNjQwIDYwSDU3NlY0MTJINjQwVjYwWiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTEzOCIgdW5pY29kZT0iJiN4RTEzODsiIGQ9Ik0xMDExLjIgMzIyLjRMNzg3LjIgNTQ2LjRDNzc0LjQgNTU5LjIgNzU0LjU2IDU1OS4yIDc0MS43NiA1NDYuNFM3MjguOTYgNTEzLjc2IDc0MS43NiA1MDAuOTZMOTQzLjM2IDMwMCA3NDEuNzYgOTguNEM3MjguOTYgODUuNiA3MjguOTYgNjUuNzYgNzQxLjc2IDUyLjk2IDc0OC4xNiA0Ni41NiA3NTYuNDggNDMuMzYgNzY0LjE2IDQzLjM2Uzc4MC44IDQ2LjU2IDc4Ni41NiA1Mi45NkwxMDEwLjU2IDI3Ni45NkMxMDIzLjM2IDI4OS43NiAxMDIzLjM2IDMxMC4yNCAxMDExLjIgMzIyLjRaTTI4Mi4yNCA1NDYuNEMyNjkuNDQgNTU5LjIgMjQ5LjYgNTU5LjIgMjM2LjggNTQ2LjRMMTIuOCAzMjIuNEMwIDMwOS42IDAgMjg5Ljc2IDEyLjggMjc2Ljk2TDIzNi44IDUyLjk2QzI0My4yIDQ3LjIgMjUxLjUyIDQ0IDI1OS44NCA0NFMyNzYuNDggNDcuMiAyODIuMjQgNTMuNkMyOTUuMDQgNjYuNCAyOTUuMDQgODYuMjQgMjgyLjI0IDk5LjA0TDgwLjY0IDMwMCAyODIuMjQgNTAxLjZDMjk0LjQgNTEzLjc2IDI5NC40IDUzNC4yNCAyODIuMjQgNTQ2LjRaTTYxNi4zMiA2ODIuNzJDNTk5LjY4IDY4Ny44NCA1ODEuNzYgNjc3LjYgNTc3LjI4IDY2MC4zMkwzODUuMjgtNDMuNjhDMzgwLjgtNjAuOTYgMzkwLjQtNzguMjQgNDA3LjY4LTgyLjcyIDQxMC4yNC04My4zNiA0MTMuNDQtODQgNDE2LTg0IDQzMC4wOC04NCA0NDIuODgtNzQuNCA0NDYuNzItNjAuMzJMNjM4LjcyIDY0My42OEM2NDMuMiA2NjAuMzIgNjMzLjYgNjc4LjI0IDYxNi4zMiA2ODIuNzJaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMTM5IiB1bmljb2RlPSImI3hFMTM5OyIgZD0iTTUxMiAzMDBNNDE2IDMwMEE5NiA5NiAwIDEgMSA2MDggMzAwIDk2IDk2IDAgMSAxIDQxNiAzMDBaTTg2MC44IDI1My42Qzg2NS42IDI4NCA4NjUuNiAzMTYgODYwLjggMzQ2LjRMOTI4IDQwNEM5MzcuNiA0MTIgOTQyLjQgNDI2LjQgOTM3LjYgNDM5LjIgOTE4LjQgNDk4LjQgODg2LjQgNTU0LjQgODQ0LjggNjAwLjggODM4LjQgNjA3LjIgODMwLjQgNjEyIDgyMC44IDYxMiA4MTcuNiA2MTIgODEyLjggNjEyIDgwOS42IDYxMC40TDcyNi40IDU4MEM3MDIuNCA1OTkuMiA2NzMuNiA2MTUuMiA2NDQuOCA2MjYuNEw2MjguOCA3MTIuOEM2MjcuMiA3MjUuNiA2MTYgNzM1LjIgNjAzLjIgNzM4LjQgNTQyLjQgNzUxLjIgNDc4LjQgNzUxLjIgNDE3LjYgNzM4LjQgNDA0LjggNzM1LjIgMzk1LjIgNzI1LjYgMzkzLjYgNzEyLjhMMzc3LjYgNjI2LjRDMzQ4LjggNjE1LjIgMzIxLjYgNTk5LjIgMjk2IDU4MEwyMTIuOCA2MTAuNEMyMDkuNiA2MTIgMjA2LjQgNjEyIDIwMS42IDYxMiAxOTIgNjEyIDE4NCA2MDguOCAxNzcuNiA2MDAuOCAxMzYgNTU0LjQgMTA0IDUwMCA4NC44IDQzOS4yIDgwIDQyNi40IDg0LjggNDEyIDk0LjQgNDA0TDE2MS42IDM0Ni40QzE2MCAzMTYgMTYwIDI4NCAxNjMuMiAyNTMuNkw5NiAxOTZDODYuNCAxODggODEuNiAxNzMuNiA4Ni40IDE2MC44IDEwNS42IDEwMS42IDEzNy42IDQ1LjYgMTc5LjItMC44IDE4NS42LTcuMiAxOTMuNi0xMiAyMDMuMi0xMiAyMDYuNC0xMiAyMTEuMi0xMiAyMTQuNC0xMC40TDI5Ny42IDIwQzMyMS42IDAuOCAzNTAuNC0xNS4yIDM3OS4yLTI2LjRMMzk1LjItMTEyLjhDMzk2LjgtMTI1LjYgNDA4LTEzNS4yIDQyMC44LTEzOC40IDQ4MS42LTE1MS4yIDU0NS42LTE1MS4yIDYwNi40LTEzOC40IDYxOS4yLTEzNS4yIDYyOC44LTEyNS42IDYzMi0xMTIuOEw2NDgtMjYuNEM2NzYuOC0xNS4yIDcwNCAwLjggNzI5LjYgMjBMODEyLjgtMTAuNEM4MTYtMTIgODE5LjItMTIgODI0LTEyIDgzMy42LTEyIDg0MS42LTguOCA4NDgtMC44IDg4OS42IDQ1LjYgOTIxLjYgMTAwIDk0MC44IDE2MC44IDk0NCAxNzMuNiA5NDAuOCAxODggOTI5LjYgMTk2TDg2MC44IDI1My42Wk01MTIgMTQwQzQyNCAxNDAgMzUyIDIxMiAzNTIgMzAwUzQyNCA0NjAgNTEyIDQ2MCA2NzIgMzg4IDY3MiAzMDAgNjAwIDE0MCA1MTIgMTQwWiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTEzQSIgdW5pY29kZT0iJiN4RTEzQTsiIGQ9Ik01MTIgNjg0QzUzMS4yIDY4NCA1NTIgNjgyLjQgNTcxLjIgNjc5LjJMNTgyLjQgNjEzLjYgNTg4LjggNTc4LjQgNjIwLjggNTY1LjZDNjQ0LjggNTU2IDY2Ny4yIDU0My4yIDY4OCA1MjcuMkw3MTUuMiA1MDYuNCA3NDguOCA1MTkuMiA4MTEuMiA1NDEuNkM4MzYuOCA1MTEuMiA4NTYgNDc2IDg3MC40IDQzOS4yTDgxOS4yIDM5NiA3OTIgMzczLjYgNzk2LjggMzM4LjRDODAwIDMxMi44IDgwMCAyODcuMiA3OTYuOCAyNjEuNkw3OTIgMjI2LjQgODE5LjIgMjA0IDg3MC40IDE2MC44Qzg1NiAxMjQgODM2LjggODguOCA4MTEuMiA1OC40TDc0OC44IDgwLjggNzE1LjIgOTMuNiA2ODggNzIuOEM2NjcuMiA1Ni44IDY0NC44IDQ0IDYyMC44IDM0LjRMNTg4LjggMjEuNiA1ODIuNC0xMy42IDU3MS4yLTc5LjJDNTMxLjItODUuNiA0OTIuOC04NS42IDQ1Mi44LTc5LjJMNDQxLjYtMTMuNiA0MzUuMiAyMS42IDQwMy4yIDM0LjRDMzc5LjIgNDQgMzU2LjggNTYuOCAzMzYgNzIuOEwzMDguOCA5My42IDI3NS4yIDgwLjggMjEyLjggNTguNEMxODcuMiA4OC44IDE2OCAxMjQgMTUzLjYgMTYwLjhMMjA0LjggMjA0IDIzMiAyMjYuNCAyMjcuMiAyNjEuNkMyMjQgMjg3LjIgMjI0IDMxMi44IDIyNy4yIDMzOC40TDIzMiAzNzMuNiAyMDQuOCAzOTYgMTUzLjYgNDM3LjZDMTY4IDQ3NC40IDE4Ny4yIDUwOS42IDIxMi44IDU0MEwyNzUuMiA1MTcuNiAzMDguOCA1MDQuOCAzMzYgNTI1LjZDMzU2LjggNTQxLjYgMzc5LjIgNTU0LjQgNDAxLjYgNTY0TDQzMy42IDU3Ni44IDQ0MCA2MTIgNDUxLjIgNjc3LjZDNDcyIDY4Mi40IDQ5MS4yIDY4NCA1MTIgNjg0TTUxMiA3NDhDNDgwIDc0OCA0NDkuNiA3NDQuOCA0MTkuMiA3MzguNCA0MDYuNCA3MzUuMiAzOTYuOCA3MjUuNiAzOTMuNiA3MTIuOEwzNzcuNiA2MjYuNEMzNDguOCA2MTUuMiAzMjEuNiA1OTkuMiAyOTYgNTgwTDIxMi44IDYxMC40QzIwOS42IDYxMiAyMDYuNCA2MTIgMjAxLjYgNjEyIDE5MiA2MTIgMTg0IDYwOC44IDE3Ny42IDYwMC44IDEzNiA1NTQuNCAxMDQgNTAwIDg0LjggNDM5LjIgODAgNDI2LjQgODQuOCA0MTIgOTQuNCA0MDRMMTYxLjYgMzQ2LjRDMTYwIDMxNiAxNjAgMjg0IDE2My4yIDI1My42TDk2IDE5NkM4Ni40IDE4OCA4MS42IDE3My42IDg2LjQgMTYwLjggMTA1LjYgMTAxLjYgMTM3LjYgNDUuNiAxNzkuMi0wLjggMTg1LjYtNy4yIDE5My42LTEyIDIwMy4yLTEyIDIwNi40LTEyIDIxMS4yLTEyIDIxNC40LTEwLjRMMjk3LjYgMjBDMzIxLjYgMC44IDM1MC40LTE1LjIgMzc5LjItMjYuNEwzOTUuMi0xMTIuOEMzOTYuOC0xMjUuNiA0MDgtMTM1LjIgNDIwLjgtMTM4LjQgNDgxLjYtMTUxLjIgNTQ1LjYtMTUxLjIgNjA2LjQtMTM4LjQgNjE5LjItMTM1LjIgNjI4LjgtMTI1LjYgNjMyLTExMi44TDY0OC0yNi40QzY3Ni44LTE1LjIgNzA0IDAuOCA3MjkuNiAyMEw4MTIuOC0xMC40QzgxNi0xMiA4MTkuMi0xMiA4MjQtMTIgODMzLjYtMTIgODQxLjYtOC44IDg0OC0wLjggODg5LjYgNDUuNiA5MjEuNiAxMDAgOTQwLjggMTYwLjggOTQ0IDE3My42IDk0MC44IDE4OCA5MjkuNiAxOTZMODYyLjQgMjUzLjZDODY3LjIgMjg0IDg2Ny4yIDMxNiA4NjIuNCAzNDYuNEw5MjkuNiA0MDRDOTM5LjIgNDEyIDk0NCA0MjYuNCA5MzkuMiA0MzkuMiA5MjAgNDk4LjQgODg4IDU1NC40IDg0Ni40IDYwMC44IDg0MCA2MDcuMiA4MzIgNjEyIDgyMi40IDYxMiA4MTkuMiA2MTIgODE0LjQgNjEyIDgxMS4yIDYxMC40TDcyOCA1ODBDNzA0IDU5OS4yIDY3NS4yIDYxNS4yIDY0Ni40IDYyNi40TDYzMC40IDcxMi44QzYyOC44IDcyNS42IDYxNy42IDczNS4yIDYwNC44IDczOC40IDU3NC40IDc0NC44IDU0Mi40IDc0OCA1MTIgNzQ4Wk01MTIgMzk2QzU2NC44IDM5NiA2MDggMzUyLjggNjA4IDMwMFM1NjQuOCAyMDQgNTEyIDIwNCA0MTYgMjQ3LjIgNDE2IDMwMCA0NTkuMiAzOTYgNTEyIDM5Nk01MTIgNDYwQzQyNCA0NjAgMzUyIDM4OCAzNTIgMzAwUzQyNCAxNDAgNTEyIDE0MCA2NzIgMjEyIDY3MiAzMDAgNjAwIDQ2MCA1MTIgNDYwWiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTEzQiIgdW5pY29kZT0iJiN4RTEzQjsiIGQ9Ik01MTIgODEyQzIyOS4yNDggODEyIDAgNTgyLjc1MiAwIDMwMFMyMjkuMjQ4LTIxMiA1MTItMjEyQzc5NC43NTItMjEyIDEwMjQgMTcuMjQ4IDEwMjQgMzAwUzc5NC43NTIgODEyIDUxMiA4MTJaTTQxNiA0MjhIMzUyVjc2QzM1MiA1OC4zMzYgMzM3LjY2NCA0NCAzMjAgNDRTMjg4IDU4LjMzNiAyODggNzZWNDI4SDIyNEMyMDYuMzM2IDQyOCAxOTIgNDQyLjMzNiAxOTIgNDYwUzIwNi4zMzYgNDkyIDIyNCA0OTJINDE2QzQzMy42NjQgNDkyIDQ0OCA0NzcuNjY0IDQ0OCA0NjBTNDMzLjY2NCA0MjggNDE2IDQyOFpNODAwIDQyOEg3MzZWNzZDNzM2IDU4LjMzNiA3MjEuNjY0IDQ0IDcwNCA0NFM2NzIgNTguMzM2IDY3MiA3NlY0MjhINjA4QzU5MC4zMzYgNDI4IDU3NiA0NDIuMzM2IDU3NiA0NjBTNTkwLjMzNiA0OTIgNjA4IDQ5Mkg4MDBDODE3LjY2NCA0OTIgODMyIDQ3Ny42NjQgODMyIDQ2MFM4MTcuNjY0IDQyOCA4MDAgNDI4WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTEzQyIgdW5pY29kZT0iJiN4RTEzQzsiIGQ9Ik01MTIgODEyQzIyOS43NiA4MTIgMCA1ODIuMjQgMCAzMDBTMjI5Ljc2LTIxMiA1MTItMjEyIDEwMjQgMTcuNzYgMTAyNCAzMDAgNzk0LjI0IDgxMiA1MTIgODEyWk01MTItMTQ4QzI2NC45Ni0xNDggNjQgNTIuOTYgNjQgMzAwUzI2NC45NiA3NDggNTEyIDc0OEM3NTkuMDQgNzQ4IDk2MCA1NDcuMDQgOTYwIDMwMFM3NTkuMDQtMTQ4IDUxMi0xNDhaTTQxNiA0OTJIMjI0QzIwNi4wOCA0OTIgMTkyIDQ3Ny45MiAxOTIgNDYwUzIwNi4wOCA0MjggMjI0IDQyOEgyODhWNzZDMjg4IDU4LjA4IDMwMi4wOCA0NCAzMjAgNDRTMzUyIDU4LjA4IDM1MiA3NlY0MjhINDE2QzQzMy45MiA0MjggNDQ4IDQ0Mi4wOCA0NDggNDYwUzQzMy45MiA0OTIgNDE2IDQ5MlpNODAwIDQ5Mkg2MDhDNTkwLjA4IDQ5MiA1NzYgNDc3LjkyIDU3NiA0NjBTNTkwLjA4IDQyOCA2MDggNDI4SDY3MlY3NkM2NzIgNTguMDggNjg2LjA4IDQ0IDcwNCA0NFM3MzYgNTguMDggNzM2IDc2VjQyOEg4MDBDODE3LjkyIDQyOCA4MzIgNDQyLjA4IDgzMiA0NjBTODE3LjkyIDQ5MiA4MDAgNDkyWiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTEzRCIgdW5pY29kZT0iJiN4RTEzRDsiIGQ9Ik01MTIgNjUyQzIyOS4yNDggNjUyIDAgNDIyLjc1MiAwIDE0MCAwIDcyLjI0NTMgMTMuMTQxMyA3LjYwNTMgMzcuMDM0Ny01MS42MTZMMzUuNzk3My00OC4xNkMzNy4yMDUzLTUxLjEwNCAzOC45MTItNTMuNjIxMyA0MC45Ni01NS44ODI3TDQwLjkxNzMtNTUuODRINDUuMzk3M0w1MS4xNTczLTU5LjY4QzUyLjY5MzMtNTkuOTM2IDU0LjQ4NTMtNjAuMTA2NyA1Ni4yNzczLTYwLjEwNjdTNTkuODYxMy01OS45MzYgNjEuNTY4LTU5LjY4TDk1OS45NTczLTU5LjcyMjdDOTY1LjkzMDctNTkuNDY2NyA5NzEuNDM0Ny01Ny41ODkzIDk3Ni4wODUzLTU0LjUxNzNMOTc1Ljk1NzMtNTQuNjAyN0M5ODAuNzM2LTUxLjIzMiA5ODQuNDQ4LTQ2LjY2NjcgOTg2Ljc1Mi00MS4zNzZMOTg2LjgzNzMtNDEuMTYyN0MxMDA3Ljc4NjcgMTIuNTk3MyAxMDE5Ljk0NjcgNzQuODkwNyAxMDE5Ljk0NjcgMTM5Ljk1NzMgMTAxOS45NDY3IDQyMS4zMDEzIDc5My4wMDI3IDY0OS42NTMzIDUxMi4xNzA3IDY1MS45NTczWk03MDAuMTYgMzcyLjk2TDU2NS43NiAxMjRDNTcxLjgxODcgMTE0Ljc4NCA1NzUuNTczMyAxMDMuNTYyNyA1NzYgOTEuNDg4IDU3NiA1Ni4wMzIgNTQ3LjMyOCAyNy4zNiA1MTIgMjcuMzZTNDQ4IDU2LjAzMiA0NDggOTEuMzZDNDQ4IDEyNi42ODggNDc2LjY3MiAxNTUuMzYgNTEyIDE1NS4zNkw2NDUuNzYgNDAzLjA0QzY1MS4zMDY3IDQxMy4wNjY3IDY2MS44NDUzIDQxOS43NjUzIDY3My45MiA0MTkuNzY1MyA2OTEuNjI2NyA0MTkuNzY1MyA3MDYuMDA1MyA0MDUuMzg2NyA3MDYuMDA1MyAzODcuNjggNzA2LjAwNTMgMzgyLjA0OCA3MDQuNTU0NyAzNzYuNzU3MyA3MDEuOTk0NyAzNzIuMTQ5M1oiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxM0UiIHVuaWNvZGU9IiYjeEUxM0U7IiBkPSJNNzAwLjE2IDQ0NC42NEw1NjUuNzYgMTk2LjMyQzU3MS41MiAxODYuNzIgNTc2IDE3NS44NCA1NzYgMTY0LjMyIDU3NiAxMjkuMTIgNTQ3LjIgMTAwLjMyIDUxMiAxMDAuMzJTNDQ4IDEyOS4xMiA0NDggMTY0LjMyQzQ0OCAxOTguODggNDc1LjUyIDIyNy4wNCA1MTAuMDggMjI3LjY4TDY0My44NCA0NzUuMzZDNjUyLjE2IDQ5MC43MiA2NzIgNDk2LjQ4IDY4Ny4zNiA0ODguMTZTNzA4LjQ4IDQ2MC42NCA3MDAuMTYgNDQ0LjY0Wk01MTIgNzI0LjMyQzIyOS43NiA3MjQuMzIgMCA0OTQuNTYgMCAyMTIuMzIgMCAxNDcuNjggMTIuMTYgODQuMzIgMzUuODQgMjQuOCA0Mi4yNCA4LjE2IDYwLjggMC40OCA3Ny40NCA2Ljg4UzEwMS43NiAzMS44NCA5NS4zNiA0OC40OEM3NC4yNCA5OS42OCA2NCAxNTUuMzYgNjQgMjExLjY4IDY0IDQ1OC43MiAyNjQuOTYgNjU5LjY4IDUxMiA2NTkuNjhTOTYwIDQ1OC43MiA5NjAgMjExLjY4Qzk2MCAxNTQuNzIgOTQ5Ljc2IDk5LjY4IDkyOC42NCA0Ny4yIDkyMi4yNCAzMC41NiA5MjkuOTIgMTIgOTQ2LjU2IDUuNiA5NTAuNCA0LjMyIDk1NC4yNCAzLjA0IDk1OC4wOCAzLjA0IDk3MC44OCAzLjA0IDk4My4wNCAxMC43MiA5ODcuNTIgMjMuNTIgMTAxMS44NCA4NC4zMiAxMDI0IDE0Ny4wNCAxMDI0IDIxMS42OCAxMDI0IDQ5NC41NiA3OTQuMjQgNzI0LjMyIDUxMiA3MjQuMzJaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMTNGIiB1bmljb2RlPSImI3hFMTNGOyIgZD0iTTUxMiA3NDhDNTExLjkxNDcgNzQ4IDUxMS44MjkzIDc0OCA1MTEuNzg2NyA3NDggMjI5LjAzNDcgNzQ4LTAuMjEzMyA1MTguNzUyLTAuMjEzMyAyMzYtMC4yMTMzIDc4LjEzMzMgNzEuMjEwNy02My4wMDggMTgzLjUwOTMtMTU2Ljk2TDE4NC4zMi0xNTcuNkgxOTIuNjRDMTk0LjM4OTMtMTU3Ljk0MTMgMTk2LjM1Mi0xNTguMTEyIDE5OC40LTE1OC4xMTJTMjAyLjQxMDctMTU3Ljk0MTMgMjA0LjM3MzMtMTU3LjU1NzNMODM5LjA0LTE1Ny42IDg0NC44LTE1NC40SDg0OC42NEM5NTUuOTg5My01Ny45NzMzIDEwMjMuNDAyNyA4MS4wNzczIDEwMjQgMjM1Ljg3MiAxMDI0IDUxOC43NTIgNzk0Ljc1MiA3NDggNTEyIDc0OFpNNTEyLTRDNDc2LjY3Mi00IDQ0OCAyNC42NzIgNDQ4IDYwIDQ0OC4zODQgODMuMTY4IDQ2MS4wMTMzIDEwMy4zMDY3IDQ3OS43MDEzIDExNC4yMjkzTDQ4MCAzOTZDNDgwIDQxMy42NjQgNDk0LjMzNiA0MjggNTEyIDQyOFM1NDQgNDEzLjY2NCA1NDQgMzk2VjExNC40QzU2Mi45ODY3IDEwMy4zMDY3IDU3NS42MTYgODMuMTY4IDU3NiA2MC4wNDI3IDU3NiAyNC42MjkzIDU0Ny4zMjgtNCA1MTItNFpNODQwLjMyIDM2Ny44NEM4MzYuMDUzMyAzNjUuNDkzMyA4MzEuMDE4NyAzNjQuMDQyNyA4MjUuNiAzNjQgODI1LjQ3MiAzNjQgODI1LjM0NCAzNjQgODI1LjIxNiAzNjQgODEyLjkyOCAzNjQgODAyLjI2MTMgMzcwLjk1NDcgNzk2Ljg4NTMgMzgxLjEwOTMgNzQyLjY1NiA0ODUuNjQyNyA2MzUuNDM0NyA1NTUuNzAxMyA1MTEuODI5MyA1NTUuNzAxMyAzOTQuMTEyIDU1NS43MDEzIDI5MS4yODUzIDQ5Mi4xNzA3IDIzNS42OTA3IDM5Ny40OTMzIDIyOS4yMDUzIDM4Ni4yNzIgMjE4Ljg4IDM3OS44NzIgMjA3LjAxODcgMzc5Ljg3MiAxODkuMjY5MyAzNzkuODcyIDE3NC44OTA3IDM5NC4yNTA3IDE3NC44OTA3IDQxMiAxNzQuODkwNyA0MTcuODg4IDE3Ni40NjkzIDQyMy4zOTIgMTc5LjI0MjcgNDI4LjE3MDcgMjQ2Ljc4NCA1NDMuNjI2NyAzNzAuMzQ2NyA2MjAuMDg1MyA1MTEuNzQ0IDYyMC4wODUzIDY2MC4wNTMzIDYyMC4wODUzIDc4OC43MzYgNTM1Ljk4OTMgODUyLjY5MzMgNDEyLjg5NiA4NTUuOTM2IDQwNi40OTYgODU3LjI1ODcgNDAxLjQ2MTMgODU3LjI1ODcgMzk2LjEyOCA4NTcuMjU4NyAzODMuOTY4IDg1MC40NzQ3IDM3My4zODY3IDg0MC40NDggMzY3Ljk2OFoiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxNDAiIHVuaWNvZGU9IiYjeEUxNDA7IiBkPSJNNTc2IDEyNEM1NzYgODguOCA1NDcuMiA2MCA1MTIgNjBTNDQ4IDg4LjggNDQ4IDEyNEM0NDggMTQ3LjA0IDQ2MS40NCAxNjYuODggNDgwIDE3OC40VjQ2MEM0ODAgNDc3LjkyIDQ5NC4wOCA0OTIgNTEyIDQ5MlM1NDQgNDc3LjkyIDU0NCA0NjBWMTc4LjRDNTYyLjU2IDE2Ni44OCA1NzYgMTQ3LjA0IDU3NiAxMjRaTTUxMiA4MTJDMjI5Ljc2IDgxMiAwIDU4Mi4yNCAwIDMwMCAwIDE0Ni40IDY3Ljg0IDIuNCAxODYuODgtOTUuNTIgMTkyLjY0LTEwMC42NCAyMDAuMzItMTAyLjU2IDIwNy4zNi0xMDIuNTYgMjE2LjMyLTEwMi41NiAyMjUuOTItOTguNzIgMjMyLjMyLTkxLjA0IDI0My44NC03Ny42IDI0MS4yOC01Ny4xMiAyMjcuODQtNDYuMjQgMTIzLjUyIDM5LjUyIDY0IDE2NS42IDY0IDMwMCA2NCA1NDcuMDQgMjY0Ljk2IDc0OCA1MTIgNzQ4Uzk2MCA1NDcuMDQgOTYwIDMwMEM5NjAgMTY5LjQ0IDkwMy42OCA0NS45MiA4MDQuNDgtMzkuMiA3OTEuMDQtNTAuNzIgNzg5Ljc2LTcxLjIgODAxLjI4LTg0LjY0UzgzMy4yOC05OS4zNiA4NDYuNzItODcuODRDOTU5LjM2IDkuNDQgMTAyNCAxNTAuODggMTAyNCAzMDAgMTAyNCA1ODIuMjQgNzk0LjI0IDgxMiA1MTIgODEyWk04MjUuNiA0MjhDODMwLjcyIDQyOCA4MzUuODQgNDI5LjI4IDg0MC4zMiA0MzEuODQgODU2LjMyIDQ0MC4xNiA4NjIuMDggNDU5LjM2IDg1NC40IDQ3NC43MiA3ODcuODQgNjA0IDY1Ni42NCA2ODQgNTEyIDY4NCAzNzUuNjggNjg0IDI0Ny42OCA2MTAuNCAxNzkuMiA0OTIgMTcwLjI0IDQ3Ni42NCAxNzYgNDU3LjQ0IDE5MS4zNiA0NDguNDhTMjI1LjkyIDQ0NC42NCAyMzQuODggNDYwQzI5MS44NCA1NTguNTYgMzk4LjA4IDYyMCA1MTIgNjIwIDYzMi45NiA2MjAgNzQxLjc2IDU1My40NCA3OTYuOCA0NDUuOTIgODAyLjU2IDQzNC40IDgxNC4wOCA0MjggODI1LjYgNDI4WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTE0MSIgdW5pY29kZT0iJiN4RTE0MTsiIGQ9Ik0xNTQuMjQgNTk0LjRDMjQyLjM4OTMgNTcyLjgxMDcgMzQzLjU5NDcgNTYwLjM5NDcgNDQ3LjY1ODcgNTYwLjM5NDdTNjUyLjkyOCA1NzIuNzY4IDc0OS44NjY3IDU5Ni4xNDkzQzg0Mi44OCA2MTkuOTU3MyA4OTYgNjYwLjkxNzMgODk2IDY4My45NTczIDg5NiA3MjYuODM3MyA3MzcuOTIgODExLjk1NzMgNDQ4IDgxMS45NTczUzAgNzI4LjExNzMgMCA2ODMuOTU3M0MwIDY2MC45MTczIDUzLjEyIDYxOS45NTczIDE1NC4yNCA1OTQuMzU3M1pNNzQ5LjQ0IDMuNjhDNjYyLjYxMzMtMTguNzIgNTYyLjk0NC0zMS41NjI3IDQ2MC4yODgtMzEuNTYyNyA0NTUuOTc4Ny0zMS41NjI3IDQ1MS42NjkzLTMxLjUyIDQ0Ny4zNi0zMS40NzczIDQ0NC4zMzA3LTMxLjUyIDQ0MC4wMjEzLTMxLjU2MjcgNDM1LjY2OTMtMzEuNTYyNyAzMzMuMDEzMy0zMS41NjI3IDIzMy4zODY3LTE4LjcyIDEzOC4yODI3IDUuNTE0NyAzOS4wODI3LTI2Ljk5NzMgMC4wNDI3LTY2LjAzNzMgMC4wNDI3LTgzLjk1NzMgMC4wNDI3LTEyNi44MzczIDE1OC4xMjI3LTIxMS45NTczIDQ0OC4wNDI3LTIxMS45NTczUzg5Ni4wNDI3LTEyOC43NTczIDg5Ni4wNDI3LTgzLjk1NzNDODk2LjA0MjctNjYuMDM3MyA4NTcuMDAyNy0yNi45OTczIDc0OS40ODI3IDMuNzIyN1pNNzQ5LjQ0IDI2My41MkM2NTguOTg2NyAyNDEuNTg5MyA1NTUuMTM2IDIyOS4wMDI3IDQ0OC4yOTg3IDIyOS4wMDI3UzIzNy42NTMzIDI0MS41ODkzIDEzOC4xMTIgMjY1LjM1NDdDMzguOTk3MyAyMzIuOC0wLjA0MjcgMTkzLjEyLTAuMDQyNyAxNzItMC4wNDI3IDEyOS4xMiAxNTguMDM3MyA0NCA0NDcuOTU3MyA0NFM4OTUuOTU3MyAxMjcuMiA4OTUuOTU3MyAxNzJDODk1Ljk1NzMgMTkzLjEyIDg1Ni45MTczIDIzMi44IDc0OS4zOTczIDI2My41MlpNNzQ5LjQ0IDUyMS40NEg3MzcuOTJDNjUwLjkyMjcgNDk5LjIxMDcgNTUwLjk5NzMgNDg2LjQxMDcgNDQ4LjA4NTMgNDg2LjI0IDQ0NS4zOTczIDQ4Ni4yNCA0NDIuMzY4IDQ4Ni4xOTczIDQzOS4yOTYgNDg2LjE5NzMgMzM5LjU0MTMgNDg2LjE5NzMgMjQyLjUxNzMgNDk4LjEwMTMgMTQ5LjY3NDcgNTIwLjU4NjdMMTQ3LjE1NzMgNTE4Ljg4QzM4Ljk5NzMgNDkyLTAuMDQyNyA0NTEuMDQtMC4wNDI3IDQzMS44NC0wLjA0MjcgMzg4Ljk2IDE1OC4wMzczIDMwMy44NCA0NDcuOTU3MyAzMDMuODRTODk1Ljk1NzMgMzg3LjY4IDg5NS45NTczIDQzMS44NEM4OTUuOTU3MyA0NTEuMDQgODU2LjkxNzMgNDkyIDc0OS4zOTczIDUyMS40NFoiICBob3Jpei1hZHYteD0iODk2IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTE0MiIgdW5pY29kZT0iJiN4RTE0MjsiIGQ9Ik0xMDI2LjU2IDQxNi43Nzg3QzEwMjYuNTYgNDYxLjA2NjcgOTg5LjM1NDcgNDk4LjI3MiA5MTkuNDI0IDUyOC40MzczIDk4My41OTQ3IDU1Ni42ODI3IDEwMjYuNTYgNTkyLjYwOCAxMDI2LjU2IDYzOS40MTMzIDEwMjYuNTYgODY5LjA4OCAwIDg2OS4wODggMCA2MzkuNDEzMyAwIDU5My44NDUzIDQxLjY4NTMgNTU3LjkyIDEwNy4xMzYgNTI4LjQzNzMgMzcuMjA1MyA0OTguOTEyIDAgNDYxLjA2NjcgMCA0MTYuNzc4N1M0My42NDggMzMyLjcyNTMgMTExLjY1ODcgMzAxLjI4QzM4LjUyOCAyNzQuMzE0NyAwIDIzNy4xMDkzIDAgMTkwLjk0NFM0NC4yODggMTA4LjgxMDcgMTEzLjU3ODcgNzcuMzY1M0MzOS4xNjggNDQuNjQgMCA4LjcxNDcgMC0zNi44NTMzIDAtMTUxLjcxMiAyNTYuNjQtMjEyIDUxMy4yOC0yMTJTMTAyNi41Ni0xNTEuNjY5MyAxMDI2LjU2LTM2Ljg1MzNDMTAyNi41NiA4LjcxNDcgOTg3LjQzNDcgNDcuMiA5MTIuOTgxMyA3Ny4zNjUzIDk4Mi4yNzIgMTA4LjgxMDcgMTAyNi41NiAxNDMuNDU2IDEwMjYuNTYgMTkwLjk0NFM5ODguMDc0NyAyNzQuMzU3MyA5MTQuOTAxMyAzMDEuMjhDOTgyLjkxMiAzMzIuNzI1MyAxMDI2LjU2IDM2OS45MzA3IDEwMjYuNTYgNDE2Ljc3ODdaTTY0LjE3MDcgNjM5LjQxMzNDNjQuMTcwNyA2NzcuMjU4NyAyMjIuNjM0NyA3NTAuMzg5MyA1MTMuMjggNzUwLjM4OTNTOTYyLjM4OTMgNjc3LjI1ODcgOTYyLjM4OTMgNjM5LjQxMzNDOTYyLjM4OTMgNjE3LjYxMDcgOTA5LjE0MTMgNTg0LjI0NTMgODA3Ljc2NTMgNTU5LjIgNzE4LjI5MzMgNTM5Ljc4NjcgNjE1LjUwOTMgNTI4LjY1MDcgNTEwLjEyMjcgNTI4LjY1MDcgNDA2Ljk5NzMgNTI4LjY1MDcgMzA2LjM0NjcgNTM5LjMxNzMgMjA5LjIzNzMgNTU5LjU0MTMgMTE3LjM3NiA1ODQuMjAyNyA2NC4xMjggNjE3LjU2OCA2NC4xMjggNjM5LjM3MDdaTTk2Mi4zODkzLTM2Ljg1MzNDOTYyLjM4OTMtNzQuNjk4NyA4MDMuOTI1My0xNDcuODI5MyA1MTMuMjgtMTQ3LjgyOTNTNjQuMTcwNy03NC42OTg3IDY0LjE3MDctMzYuODUzM0M2NC4xNzA3LTIwLjE3MDcgMTAzLjI5NiAxNC40NzQ3IDIxMS4xMTQ3IDQxLjQ0IDI5OC4wMjY3IDIxLjgxMzMgMzk3LjgyNCAxMC41OTIgNTAwLjIyNCAxMC41OTIgNTA0LjgzMiAxMC41OTIgNTA5LjM5NzMgMTAuNjM0NyA1MTQuMDA1MyAxMC42NzczIDUxNy4xNjI3IDEwLjYzNDcgNTIxLjcyOCAxMC41OTIgNTI2LjI5MzMgMTAuNTkyIDYyOC43MzYgMTAuNTkyIDcyOC41NzYgMjEuODEzMyA4MjQuNTc2IDQzLjE0NjcgOTIzLjI2NCAxNC41MTczIDk2Mi4zODkzLTE5LjQ4OCA5NjIuMzg5My0zNi44MTA3Wk05NjIuMzg5MyAxOTAuOTQ0Qzk2Mi4zODkzIDE1My4wOTg3IDgwMy45MjUzIDc5Ljk2OCA1MTMuMjggNzkuOTY4UzY0LjE3MDcgMTUzLjA5ODcgNjQuMTcwNyAxOTAuOTQ0QzY0LjE3MDcgMjA3LjYyNjcgMTAzLjI5NiAyNDIuMjcyIDIxMS4xMTQ3IDI2OS4yMzczIDMwMS44NjY3IDI0OS45OTQ3IDQwNi4xNDQgMjM4Ljk0NCA1MTIuOTgxMyAyMzguOTQ0UzcyNC4wOTYgMjQ5Ljk5NDcgODI0LjcwNCAyNzAuOTQ0QzkyMy4yNjQgMjQyLjI3MiA5NjIuMzg5MyAyMDcuNjI2NyA5NjIuMzg5MyAxOTAuOTQ0Wk01MTMuMjggMzA1Ljc2QzIyMi42MzQ3IDMwNS43NiA2NC4xNzA3IDM3OC44OTA3IDY0LjE3MDcgNDE2LjczNiA2NC4xNzA3IDQzMy40MTg3IDEwMy4yOTYgNDY4LjA2NCAyMTEuMTE0NyA0OTUuMDI5M0gyMjIuMDM3M0MzMDkuNTg5MyA0NzUuNDg4IDQxMC4xMTIgNDY0LjI2NjcgNTEzLjMyMjcgNDY0LjIyNCA1MTQuNzczMyA0NjQuMjI0IDUxNi40OCA0NjQuMjI0IDUxOC4xODY3IDQ2NC4yMjQgNjE5LjM5MiA0NjQuMjI0IDcxOC4wOCA0NzQuOTc2IDgxMy4xNDEzIDQ5NS40MTMzTDgxNS40ODggNDkzLjc0OTNDOTIzLjI2NCA0NjguMTA2NyA5NjIuNDMyIDQzNC4xMDEzIDk2Mi40MzIgNDE2Ljc3ODcgOTYyLjQzMiAzNzkuNTczMyA4MDMuOTY4IDMwNS44MDI3IDUxMy4zMjI3IDMwNS44MDI3WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTE0MyIgdW5pY29kZT0iJiN4RTE0MzsiIGQ9Ik0wIDMyNC4zMlYxNzJDMCAxMjAuMTYgMTc0LjcyIDQ0IDQ0OCA0NFM4OTYgMTE4Ljg4IDg5NiAxNzJWMzI0LjMyQzc5OS4zNiAyNjMuNTIgNjIzLjM2IDIzMi4xNiA0NDggMjMyLjE2Uzk2LjY0IDI2My41MiAwIDMyNC4zMlpNMCA1NzcuNzZWNDMxLjg0QzAgMzgwIDE3NC43MiAzMDMuODQgNDQ4IDMwMy44NFM4OTYgMzc4LjcyIDg5NiA0MzEuODRWNTc3Ljc2Qzc5OS4zNiA1MTYuOTYgNjIzLjM2IDQ4NS42IDQ0OCA0ODUuNlM5Ni42NCA1MTYuOTYgMCA1NzcuNzZaTTQ0OCA1NTZDNzIxLjI4IDU1NiA4OTYgNjMwLjg4IDg5NiA2ODRTNzIxLjI4IDgxMiA0NDggODEyIDAgNzM3LjEyIDAgNjg0IDE3NC43MiA1NTYgNDQ4IDU1NlpNMCA2Ni40Vi04NEMwLTEzNS44NCAxNzQuNzItMjEyIDQ0OC0yMTJTODk2LTEzNy4xMiA4OTYtODRWNjYuNEM3OTkuMzYgNS42IDYyMy4zNi0yNS43NiA0NDgtMjUuNzZTOTYuNjQgNS42IDAgNjYuNFoiICBob3Jpei1hZHYteD0iODk2IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTE0NCIgdW5pY29kZT0iJiN4RTE0NDsiIGQ9Ik04ODkuODk4NyA2NzUuMzM4N0M4MDYuNDg1MyA4NTcuNTY4IDkxLjczMzMgODU3LjU2OCA4LjMyIDY3NS4zMzg3IDMuMiA2NjkuNzkyIDAgNjYyLjM2OCAwIDY1NC4xNzZWLTUxLjYxNkMwLjA0MjctNTkuODA4IDMuMi02Ny4yMzIgOC4zNjI3LTcyLjgyMTMgNTAuMDQ4LTE2NC41NTQ3IDI1MC4yNC0yMTIuMDQyNyA0NDkuMTA5My0yMTIuMDQyN1M4NDguMTcwNy0xNjQuNTU0NyA4ODkuODk4Ny03Mi44MjEzQzg5NS4wMTg3LTY3LjI3NDcgODk4LjIxODctNTkuODUwNyA4OTguMjE4Ny01MS42NTg3VjY1NC4xMzMzQzg5OC4xNzYgNjYyLjMyNTMgODk1LjAxODcgNjY5Ljc0OTMgODg5Ljg1NiA2NzUuMzM4N1pNODM0LjA5MDcgMTkwLjk0NEM4MzQuMDkwNyAxNDUuMzc2IDY4My45NDY3IDc5Ljk2OCA0NDkuMTA5MyA3OS45NjhTNjQuMTI4IDE0NC4xMzg3IDY0LjEyOCAxOTAuOTQ0VjMyMi40ODUzQzE2NS44ODggMjcwLjk4NjcgMjg1Ljk5NDcgMjQwLjgyMTMgNDEzLjE0MTMgMjQwLjgyMTMgNDI1Ljc3MDcgMjQwLjgyMTMgNDM4LjM1NzMgMjQxLjEyIDQ1MC44NTg3IDI0MS43MTczIDQ1OS44MTg3IDI0MS4xMiA0NzIuNDA1MyAyNDAuODIxMyA0ODUuMDM0NyAyNDAuODIxMyA2MTIuMTgxMyAyNDAuODIxMyA3MzIuMjg4IDI3MC45ODY3IDgzOC41NzA3IDMyNC41MzMzWk04MzQuMDkwNyA0MTYuNzc4N0M4MzQuMDkwNyAzNzEuMjEwNyA2ODMuOTQ2NyAzMDUuODAyNyA0NDkuMTA5MyAzMDUuODAyN1M2NC4xMjggMzcxLjg5MzMgNjQuMTI4IDQxNi43Nzg3VjU0NS4xMkMxNjUuODg4IDQ5My42MjEzIDI4NS45OTQ3IDQ2My40NTYgNDEzLjE0MTMgNDYzLjQ1NiA0MjUuNzcwNyA0NjMuNDU2IDQzOC4zNTczIDQ2My43NTQ3IDQ1MC44NTg3IDQ2NC4zNTIgNDU5LjgxODcgNDYzLjc1NDcgNDcyLjQwNTMgNDYzLjQ1NiA0ODUuMDM0NyA0NjMuNDU2IDYxMi4xODEzIDQ2My40NTYgNzMyLjI4OCA0OTMuNjIxMyA4MzguNTcwNyA1NDcuMTY4Wk00NDkuMTA5MyA3NTAuMzg5M0M2ODMuOTQ2NyA3NTAuMzg5MyA4MzQuMDkwNyA2ODYuMjE4NyA4MzQuMDkwNyA2MzkuNDEzM1M2ODMuOTQ2NyA1MjguNDM3MyA0NDkuMTA5MyA1MjguNDM3MyA2NC4xMjggNTkyLjYwOCA2NC4xMjggNjM5LjQxMzMgMjE0LjI3MiA3NTAuMzg5MyA0NDkuMTA5MyA3NTAuMzg5M1pNNDQ5LjEwOTMtMTQ3LjgyOTNDMjE0LjI3Mi0xNDcuODI5MyA2NC4xMjgtODMuNjU4NyA2NC4xMjgtMzYuODUzM1Y5Ni42MDhDMTY1LjkzMDcgNDUuMTA5MyAyODYuMDggMTQuOTQ0IDQxMy4yNjkzIDE0Ljk0NCA0MjUuODU2IDE0Ljk0NCA0MzguNCAxNS4yNDI3IDQ1MC44NTg3IDE1Ljg0IDQ1OS43NzYgMTUuMjQyNyA0NzIuMzIgMTQuOTQ0IDQ4NC45MDY3IDE0Ljk0NCA2MTIuMDk2IDE0Ljk0NCA3MzIuMjQ1MyA0NS4xMDkzIDgzOC41NzA3IDk4LjY1Nkw4MzQuMDQ4LTM2Ljg1MzNDODM0LjA0OC04My43MDEzIDY4My45MDQtMTQ3LjgyOTMgNDQ5LjA2NjctMTQ3LjgyOTNaIiAgaG9yaXotYWR2LXg9Ijg5NiIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxNDUiIHVuaWNvZGU9IiYjeEUxNDU7IiBkPSJNNjMuMzYgMjk5LjM2TDIzNC4yNCAxMzkuMzZWNDU4LjcyTDYzLjM2IDI5OS4zNlpNMzIgNjUySDk5MkMxMDA5LjY2NCA2NTIgMTAyNCA2NjYuMzM2IDEwMjQgNjg0UzEwMDkuNjY0IDcxNiA5OTIgNzE2SDMyQzE0LjMzNiA3MTYgMCA3MDEuNjY0IDAgNjg0UzE0LjMzNiA2NTIgMzIgNjUyWk0zMi0xMTcuMjhIOTkyQzEwMDkuNjY0LTExNy4yOCAxMDI0LTEwMi45NDQgMTAyNC04NS4yOFMxMDA5LjY2NC01My4yOCA5OTItNTMuMjhIMzJDMTQuMzM2LTUzLjI4IDAtNjcuNjE2IDAtODUuMjhTMTQuMzM2LTExNy4yOCAzMi0xMTcuMjhaTTQ3Ni44IDM5Ni42NEg5OTJDMTAwOS42NjQgMzk2LjY0IDEwMjQgNDEwLjk3NiAxMDI0IDQyOC42NFMxMDA5LjY2NCA0NjAuNjQgOTkyIDQ2MC42NEg0NzYuOEM0NTkuMTM2IDQ2MC42NCA0NDQuOCA0NDYuMzA0IDQ0NC44IDQyOC42NFM0NTkuMTM2IDM5Ni42NCA0NzYuOCAzOTYuNjRaTTQ3Ni44IDE0MEg5OTJDMTAwOS42NjQgMTQwIDEwMjQgMTU0LjMzNiAxMDI0IDE3MlMxMDA5LjY2NCAyMDQgOTkyIDIwNEg0NzYuOEM0NTkuMTM2IDIwNCA0NDQuOCAxODkuNjY0IDQ0NC44IDE3MlM0NTkuMTM2IDE0MCA0NzYuOCAxNDBaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMTQ2IiB1bmljb2RlPSImI3hFMTQ2OyIgZD0iTTkyOCA1ODhINjcyVjY1MkM2NzIgNjg3LjIgNjQzLjIgNzE2IDYwOCA3MTZINDE2QzM4MC44IDcxNiAzNTIgNjg3LjIgMzUyIDY1MlY1ODhIOTZWNTI0SDIwOFYtNTJDMjA4LTg3LjIgMjM2LjgtMTE2IDI3Mi0xMTZINzUyQzc4Ny4yLTExNiA4MTYtODcuMiA4MTYtNTJWNTI0SDkyOFY1ODhaTTQzMiA2NTJINTkyQzYwMS42IDY1MiA2MDggNjQ1LjYgNjA4IDYzNlY1ODhINDE2VjYzNkM0MTYgNjQ1LjYgNDIyLjQgNjUyIDQzMiA2NTJaTTczNi01MkgyODhDMjc4LjQtNTIgMjcyLTQ1LjYgMjcyLTM2VjUyNEg3NTJWLTM2Qzc1Mi00NS42IDc0NS42LTUyIDczNi01MlpNNTc2IDQxMkg2NDBWNjBINTc2Wk0zODQgNDEySDQ0OFY2MEgzODRaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMTQ3IiB1bmljb2RlPSImI3hFMTQ3OyIgZD0iTTgzMiAxOTcuNlY2NTguNEM4MzAuMjUwNyA3MDguMjc3MyA3ODkuNDE4NyA3NDguMDQyNyA3MzkuMjQyNyA3NDguMDQyNyA3MzguMDkwNyA3NDguMDQyNyA3MzYuOTM4NyA3NDguMDQyNyA3MzUuODI5MyA3NDhMOTYgNzQ4Qzk1LjAxODcgNzQ4LjA0MjcgOTMuOTA5MyA3NDguMDQyNyA5Mi43NTczIDc0OC4wNDI3IDQyLjYyNCA3NDguMDQyNyAxLjc0OTMgNzA4LjI3NzMgMCA2NTguNTI4TDAgMTk3LjU1NzNDMS43NDkzIDE0Ny42OCA0Mi41ODEzIDEwNy45MTQ3IDkyLjc1NzMgMTA3LjkxNDcgOTMuOTA5MyAxMDcuOTE0NyA5NS4wNjEzIDEwNy45MTQ3IDk2LjE3MDcgMTA3Ljk1NzNMMTI4IDEwNy45NTczVjExLjk1NzNDMTI4LjA4NTMtMS4yNjkzIDEzNi4xNDkzLTEyLjU3NiAxNDcuNjI2Ny0xNy4zOTczIDE0OS42NzQ3LTE3Ljg2NjcgMTUxLjc2NTMtMTguMDM3MyAxNTMuODk4Ny0xOC4wMzczUzE1OC4xNjUzLTE3LjgyNCAxNjAuMTcwNy0xNy40NEMxNjguNzQ2Ny0xNy4zNTQ3IDE3Ni42NC0xMy42ODUzIDE4Mi4zNTczLTcuODgyN0wzMDEuMzk3MyAxMDcuOTU3M0g3MzUuOTU3M0M3MzYuOTM4NyAxMDcuOTE0NyA3MzguMDQ4IDEwNy45MTQ3IDczOS4yIDEwNy45MTQ3IDc4OS4zMzMzIDEwNy45MTQ3IDgzMC4yMDggMTQ3LjY4IDgzMS45NTczIDE5Ny40MjkzWk05MjggNjIwQzkxMC4zMzYgNjIwIDg5NiA2MDUuNjY0IDg5NiA1ODhWMTQwQzg5NiA4Ni45NjUzIDg1My4wMzQ3IDQ0IDgwMCA0NEg0MTZDMzk4LjMzNiA0NCAzODQgMjkuNjY0IDM4NCAxMlMzOTguMzM2LTIwIDQxNi0yMEg3MjIuNTZMODQwLjk2LTEzOC40Qzg0Ni44MDUzLTE0NC40NTg3IDg1NC45NTQ3LTE0OC4yMTMzIDg2NC0xNDguMjEzMyA4ODEuNjY0LTE0OC4yMTMzIDg5Ni0xMzMuODc3MyA4OTYtMTE2LjIxMzMgODk2LTExNi4xMjggODk2LTExNi4wODUzIDg5Ni0xMTZWLTIwSDkyOEM5MjguOTgxMy0yMC4wNDI3IDkzMC4wOTA3LTIwLjA0MjcgOTMxLjI0MjctMjAuMDQyNyA5ODEuMzc2LTIwLjA0MjcgMTAyMi4yNTA3IDE5LjcyMjcgMTAyNCA2OS40NzJMMTAyNCA1MzAuNDQyN0MxMDIyLjI1MDcgNTgwLjMyIDk4MS40MTg3IDYyMC4wODUzIDkzMS4yNDI3IDYyMC4wODUzIDkzMC4wOTA3IDYyMC4wODUzIDkyOC45Mzg3IDYyMC4wODUzIDkyNy44MjkzIDYyMC4wNDI3WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTE0OCIgdW5pY29kZT0iJiN4RTE0ODsiIGQ9Ik04MzIgMTk3LjZWNjU4LjRDODMwLjI1MDcgNzA4LjI3NzMgNzg5LjQxODcgNzQ4LjA0MjcgNzM5LjI0MjcgNzQ4LjA0MjcgNzM4LjA5MDcgNzQ4LjA0MjcgNzM2LjkzODcgNzQ4LjA0MjcgNzM1LjgyOTMgNzQ4TDk2IDc0OEM5NS4wMTg3IDc0OC4wNDI3IDkzLjkwOTMgNzQ4LjA0MjcgOTIuNzU3MyA3NDguMDQyNyA0Mi42MjQgNzQ4LjA0MjcgMS43NDkzIDcwOC4yNzczIDAgNjU4LjUyOEwwIDE5Ny41NTczQzEuNzQ5MyAxNDcuNjggNDIuNTgxMyAxMDcuOTE0NyA5Mi43NTczIDEwNy45MTQ3IDkzLjkwOTMgMTA3LjkxNDcgOTUuMDYxMyAxMDcuOTE0NyA5Ni4xNzA3IDEwNy45NTczTDEyOCAxMDcuOTU3M1YxMS45NTczQzEyOC4wODUzLTEuMjY5MyAxMzYuMTQ5My0xMi41NzYgMTQ3LjYyNjctMTcuMzk3MyAxNDkuNjc0Ny0xNy44NjY3IDE1MS43NjUzLTE4LjAzNzMgMTUzLjg5ODctMTguMDM3M1MxNTguMTY1My0xNy44MjQgMTYwLjE3MDctMTcuNDRDMTY4Ljc0NjctMTcuMzU0NyAxNzYuNjQtMTMuNjg1MyAxODIuMzU3My03Ljg4MjdMMzAxLjM5NzMgMTA3Ljk1NzNINzM1Ljk1NzNDNzM2LjkzODcgMTA3LjkxNDcgNzM4LjA0OCAxMDcuOTE0NyA3MzkuMiAxMDcuOTE0NyA3ODkuMzMzMyAxMDcuOTE0NyA4MzAuMjA4IDE0Ny42OCA4MzEuOTU3MyAxOTcuNDI5M1pNMjg4IDE3MkMyNzkuMjEwNyAxNzEuODcyIDI3MS4zMTczIDE2OC4yMDI3IDI2NS42IDE2Mi40TDE5MiA4OS40NFYxNDBDMTkyIDE1Ny42NjQgMTc3LjY2NCAxNzIgMTYwIDE3Mkg5NkM5NS4zMTczIDE3MS45NTczIDk0LjU0OTMgMTcxLjkxNDcgOTMuNzM4NyAxNzEuOTE0NyA3OC42NzczIDE3MS45MTQ3IDY2LjIxODcgMTgyLjk2NTMgNjQgMTk3LjQyOTNMNjQgNjU4LjRDNjUuOTIgNjcyLjk5MiA3OC4yNTA3IDY4NC4xMjggOTMuMjI2NyA2ODQuMTI4IDk0LjIwOCA2ODQuMTI4IDk1LjE4OTMgNjg0LjA4NTMgOTYuMTI4IDY4NEw3MzYgNjg0QzczNi44NTMzIDY4NC4wODUzIDczNy43OTIgNjg0LjEyOCA3MzguNzczMyA2ODQuMTI4IDc1My43MDY3IDY4NC4xMjggNzY2LjA4IDY3Mi45OTIgNzY3Ljk1NzMgNjU4LjUyOEw3NjcuOTU3MyAxOTcuNkM3NjYuMDM3MyAxODMuMDA4IDc1My43MDY3IDE3MS44NzIgNzM4LjczMDcgMTcxLjg3MiA3MzcuNzQ5MyAxNzEuODcyIDczNi43NjggMTcxLjkxNDcgNzM1LjgyOTMgMTcyWk05MjggNjIwQzkxMC4zMzYgNjIwIDg5NiA2MDUuNjY0IDg5NiA1ODhTOTEwLjMzNiA1NTYgOTI4IDU1NkM5MjguODUzMyA1NTYuMDg1MyA5MjkuNzkyIDU1Ni4xMjggOTMwLjc3MzMgNTU2LjEyOCA5NDUuNzA2NyA1NTYuMTI4IDk1OC4wOCA1NDQuOTkyIDk1OS45NTczIDUzMC41MjhMOTU5Ljk1NzMgNjkuNkM5NTguMDM3MyA1NS4wMDggOTQ1LjcwNjcgNDMuODcyIDkzMC43MzA3IDQzLjg3MiA5MjkuNzQ5MyA0My44NzIgOTI4Ljc2OCA0My45MTQ3IDkyNy44MjkzIDQ0TDg2My45NTczIDQ0Qzg0Ni4yOTMzIDQ0IDgzMS45NTczIDI5LjY2NCA4MzEuOTU3MyAxMlYtMzguNTZMNzU4LjM1NzMgMzUuMDRDNzUyLjU5NzMgNDAuNTg2NyA3NDQuNzg5MyA0NCA3MzYuMTcwNyA0NCA3MzYuMDg1MyA0NCA3MzYuMDQyNyA0NCA3MzUuOTU3MyA0NEg0MTUuOTU3M0MzOTguMjkzMyA0NCAzODMuOTU3MyAyOS42NjQgMzgzLjk1NzMgMTJTMzk4LjI5MzMtMjAgNDE1Ljk1NzMtMjBINzIyLjUxNzNMODQwLjkxNzMtMTM4LjRDODQ2Ljc2MjctMTQ0LjQ1ODcgODU0LjkxMi0xNDguMjEzMyA4NjMuOTU3My0xNDguMjEzMyA4ODEuNjIxMy0xNDguMjEzMyA4OTUuOTU3My0xMzMuODc3MyA4OTUuOTU3My0xMTYuMjEzMyA4OTUuOTU3My0xMTYuMTI4IDg5NS45NTczLTExNi4wODUzIDg5NS45NTczLTExNlYtMjBIOTI3Ljk1NzNDOTI4LjkzODctMjAuMDQyNyA5MzAuMDQ4LTIwLjA0MjcgOTMxLjItMjAuMDQyNyA5ODEuMzMzMy0yMC4wNDI3IDEwMjIuMjA4IDE5LjcyMjcgMTAyMy45NTczIDY5LjQ3MkwxMDIzLjk1NzMgNTMwLjQ0MjdDMTAyMi4yMDggNTgwLjMyIDk4MS4zNzYgNjIwLjA4NTMgOTMxLjIgNjIwLjA4NTMgOTMwLjA0OCA2MjAuMDg1MyA5MjguODk2IDYyMC4wODUzIDkyNy43ODY3IDYyMC4wNDI3WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTE0OSIgdW5pY29kZT0iJiN4RTE0OTsiIGQ9Ik04MzIgMTk3LjZWNjU4LjRDODMwLjI1MDcgNzA4LjI3NzMgNzg5LjQxODcgNzQ4LjA0MjcgNzM5LjI0MjcgNzQ4LjA0MjcgNzM4LjA5MDcgNzQ4LjA0MjcgNzM2LjkzODcgNzQ4LjA0MjcgNzM1LjgyOTMgNzQ4TDk2IDc0OEM5NS4wMTg3IDc0OC4wNDI3IDkzLjkwOTMgNzQ4LjA0MjcgOTIuNzU3MyA3NDguMDQyNyA0Mi42MjQgNzQ4LjA0MjcgMS43NDkzIDcwOC4yNzczIDAgNjU4LjUyOEwwIDE5Ny41NTczQzEuNzQ5MyAxNDcuNjggNDIuNTgxMyAxMDcuOTE0NyA5Mi43NTczIDEwNy45MTQ3IDkzLjkwOTMgMTA3LjkxNDcgOTUuMDYxMyAxMDcuOTE0NyA5Ni4xNzA3IDEwNy45NTczTDEyOCAxMDcuOTU3M1YxMS45NTczQzEyOC4wODUzLTEuMjY5MyAxMzYuMTQ5My0xMi41NzYgMTQ3LjYyNjctMTcuMzk3MyAxNDkuNjc0Ny0xNy44NjY3IDE1MS43NjUzLTE4LjAzNzMgMTUzLjg5ODctMTguMDM3M1MxNTguMTY1My0xNy44MjQgMTYwLjE3MDctMTcuNDRDMTY4Ljc0NjctMTcuMzU0NyAxNzYuNjQtMTMuNjg1MyAxODIuMzU3My03Ljg4MjdMMzAxLjM5NzMgMTA3Ljk1NzNINzM1Ljk1NzNDNzM2LjkzODcgMTA3LjkxNDcgNzM4LjA0OCAxMDcuOTE0NyA3MzkuMiAxMDcuOTE0NyA3ODkuMzMzMyAxMDcuOTE0NyA4MzAuMjA4IDE0Ny42OCA4MzEuOTU3MyAxOTcuNDI5M1pNMjI0IDM2NEMxODguNjcyIDM2NCAxNjAgMzkyLjY3MiAxNjAgNDI4UzE4OC42NzIgNDkyIDIyNCA0OTJDMjU5LjMyOCA0OTIgMjg4IDQ2My4zMjggMjg4IDQyOFMyNTkuMzI4IDM2NCAyMjQgMzY0Wk00MTYgMzY0QzM4MC42NzIgMzY0IDM1MiAzOTIuNjcyIDM1MiA0MjhTMzgwLjY3MiA0OTIgNDE2IDQ5MkM0NTEuMzI4IDQ5MiA0ODAgNDYzLjMyOCA0ODAgNDI4UzQ1MS4zMjggMzY0IDQxNiAzNjRaTTYwOCAzNjRDNTcyLjY3MiAzNjQgNTQ0IDM5Mi42NzIgNTQ0IDQyOFM1NzIuNjcyIDQ5MiA2MDggNDkyQzY0My4zMjggNDkyIDY3MiA0NjMuMzI4IDY3MiA0MjhTNjQzLjMyOCAzNjQgNjA4IDM2NFpNOTI4IDYyMEM5MTAuMzM2IDYyMCA4OTYgNjA1LjY2NCA4OTYgNTg4VjE0MEM4OTYgODYuOTY1MyA4NTMuMDM0NyA0NCA4MDAgNDRINDE2QzM5OC4zMzYgNDQgMzg0IDI5LjY2NCAzODQgMTJTMzk4LjMzNi0yMCA0MTYtMjBINzIyLjU2TDg0MC45Ni0xMzguNEM4NDYuODA1My0xNDQuNDU4NyA4NTQuOTU0Ny0xNDguMjEzMyA4NjQtMTQ4LjIxMzMgODgxLjY2NC0xNDguMjEzMyA4OTYtMTMzLjg3NzMgODk2LTExNi4yMTMzIDg5Ni0xMTYuMTI4IDg5Ni0xMTYuMDg1MyA4OTYtMTE2Vi0yMEg5MjhDOTI4Ljk4MTMtMjAuMDQyNyA5MzAuMDkwNy0yMC4wNDI3IDkzMS4yNDI3LTIwLjA0MjcgOTgxLjM3Ni0yMC4wNDI3IDEwMjIuMjUwNyAxOS43MjI3IDEwMjQgNjkuNDcyTDEwMjQgNTMwLjQ0MjdDMTAyMi4yNTA3IDU4MC4zMiA5ODEuNDE4NyA2MjAuMDg1MyA5MzEuMjQyNyA2MjAuMDg1MyA5MzAuMDkwNyA2MjAuMDg1MyA5MjguOTM4NyA2MjAuMDg1MyA5MjcuODI5MyA2MjAuMDQyN1oiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxNEEiIHVuaWNvZGU9IiYjeEUxNEE7IiBkPSJNODMyIDE5Ny42VjY1OC40QzgzMC4yNTA3IDcwOC4yNzczIDc4OS40MTg3IDc0OC4wNDI3IDczOS4yNDI3IDc0OC4wNDI3IDczOC4wOTA3IDc0OC4wNDI3IDczNi45Mzg3IDc0OC4wNDI3IDczNS44MjkzIDc0OEw5NiA3NDhDOTUuMDE4NyA3NDguMDQyNyA5My45MDkzIDc0OC4wNDI3IDkyLjc1NzMgNzQ4LjA0MjcgNDIuNjI0IDc0OC4wNDI3IDEuNzQ5MyA3MDguMjc3MyAwIDY1OC41MjhMMCAxOTcuNTU3M0MxLjc0OTMgMTQ3LjY4IDQyLjU4MTMgMTA3LjkxNDcgOTIuNzU3MyAxMDcuOTE0NyA5My45MDkzIDEwNy45MTQ3IDk1LjA2MTMgMTA3LjkxNDcgOTYuMTcwNyAxMDcuOTU3M0wxMjggMTA3Ljk1NzNWMTEuOTU3M0MxMjguMDg1My0xLjI2OTMgMTM2LjE0OTMtMTIuNTc2IDE0Ny42MjY3LTE3LjM5NzMgMTQ5LjY3NDctMTcuODY2NyAxNTEuNzY1My0xOC4wMzczIDE1My44OTg3LTE4LjAzNzNTMTU4LjE2NTMtMTcuODI0IDE2MC4xNzA3LTE3LjQ0QzE2OC43NDY3LTE3LjM1NDcgMTc2LjY0LTEzLjY4NTMgMTgyLjM1NzMtNy44ODI3TDMwMS4zOTczIDEwNy45NTczSDczNS45NTczQzczNi45Mzg3IDEwNy45MTQ3IDczOC4wNDggMTA3LjkxNDcgNzM5LjIgMTA3LjkxNDcgNzg5LjMzMzMgMTA3LjkxNDcgODMwLjIwOCAxNDcuNjggODMxLjk1NzMgMTk3LjQyOTNaTTI4OCAxNzJDMjc5LjIxMDcgMTcxLjg3MiAyNzEuMzE3MyAxNjguMjAyNyAyNjUuNiAxNjIuNEwxOTIgODkuNDRWMTQwQzE5MiAxNTcuNjY0IDE3Ny42NjQgMTcyIDE2MCAxNzJIOTZDOTUuMzE3MyAxNzEuOTU3MyA5NC41NDkzIDE3MS45MTQ3IDkzLjczODcgMTcxLjkxNDcgNzguNjc3MyAxNzEuOTE0NyA2Ni4yMTg3IDE4Mi45NjUzIDY0IDE5Ny40MjkzTDY0IDY1OC40QzY1LjkyIDY3Mi45OTIgNzguMjUwNyA2ODQuMTI4IDkzLjIyNjcgNjg0LjEyOCA5NC4yMDggNjg0LjEyOCA5NS4xODkzIDY4NC4wODUzIDk2LjEyOCA2ODRMNzM2IDY4NEM3MzYuODUzMyA2ODQuMDg1MyA3MzcuNzkyIDY4NC4xMjggNzM4Ljc3MzMgNjg0LjEyOCA3NTMuNzA2NyA2ODQuMTI4IDc2Ni4wOCA2NzIuOTkyIDc2Ny45NTczIDY1OC41MjhMNzY3Ljk1NzMgMTk3LjZDNzY2LjAzNzMgMTgzLjAwOCA3NTMuNzA2NyAxNzEuODcyIDczOC43MzA3IDE3MS44NzIgNzM3Ljc0OTMgMTcxLjg3MiA3MzYuNzY4IDE3MS45MTQ3IDczNS44MjkzIDE3MlpNMTAyNCA1MzAuNFY2OS42QzEwMjIuMjUwNyAxOS43MjI3IDk4MS40MTg3LTIwLjA0MjcgOTMxLjI0MjctMjAuMDQyNyA5MzAuMDkwNy0yMC4wNDI3IDkyOC45Mzg3LTIwLjA0MjcgOTI3LjgyOTMtMjBMODk2LTIwVi0xMTZDODk1Ljc0NC0xMzMuNDkzMyA4ODEuNTM2LTE0Ny41MzA3IDg2NC0xNDcuNTMwNyA4NTUuMjUzMy0xNDcuNTMwNyA4NDcuMzYtMTQ0LjAzMiA4NDEuNi0xMzguMzU3M0w3MjIuNTYtMTkuOTU3M0g0MTZDMzk4LjMzNi0xOS45NTczIDM4NC01LjYyMTMgMzg0IDEyLjA0MjdTMzk4LjMzNiA0NC4wNDI3IDQxNiA0NC4wNDI3SDczNkM3NDQuNzg5MyA0My45MTQ3IDc1Mi42ODI3IDQwLjI0NTMgNzU4LjQgMzQuNDQyN0w4MzItMzguNTE3M1YxMi4wNDI3QzgzMiAyOS43MDY3IDg0Ni4zMzYgNDQuMDQyNyA4NjQgNDQuMDQyN0g5MjhDOTI4Ljg1MzMgNDMuOTU3MyA5MjkuNzkyIDQzLjkxNDcgOTMwLjc3MzMgNDMuOTE0NyA5NDUuNzA2NyA0My45MTQ3IDk1OC4wOCA1NS4wNTA3IDk1OS45NTczIDY5LjUxNDdMOTU5Ljk1NzMgNTMwLjQ0MjdDOTU4LjAzNzMgNTQ1LjAzNDcgOTQ1LjcwNjcgNTU2LjE3MDcgOTMwLjczMDcgNTU2LjE3MDcgOTI5Ljc0OTMgNTU2LjE3MDcgOTI4Ljc2OCA1NTYuMTI4IDkyNy44MjkzIDU1Ni4wNDI3IDkxMC4yOTMzIDU1Ni4wNDI3IDg5NS45NTczIDU3MC4zNzg3IDg5NS45NTczIDU4OC4wNDI3UzkxMC4yOTMzIDYyMC4wNDI3IDkyNy45NTczIDYyMC4wNDI3QzkyOC45Mzg3IDYyMC4wODUzIDkzMC4wNDggNjIwLjA4NTMgOTMxLjIgNjIwLjA4NTMgOTgxLjMzMzMgNjIwLjA4NTMgMTAyMi4yMDggNTgwLjMyIDEwMjMuOTU3MyA1MzAuNTcwN1pNMjg4IDQyOEMyODggMzkyLjY3MiAyNTkuMzI4IDM2NCAyMjQgMzY0UzE2MCAzOTIuNjcyIDE2MCA0MjhDMTYwIDQ2My4zMjggMTg4LjY3MiA0OTIgMjI0IDQ5MlMyODggNDYzLjMyOCAyODggNDI4Wk00ODAgNDI4QzQ4MCAzOTIuNjcyIDQ1MS4zMjggMzY0IDQxNiAzNjRTMzUyIDM5Mi42NzIgMzUyIDQyOEMzNTIgNDYzLjMyOCAzODAuNjcyIDQ5MiA0MTYgNDkyUzQ4MCA0NjMuMzI4IDQ4MCA0MjhaTTY3MiA0MjhDNjcyIDM5Mi42NzIgNjQzLjMyOCAzNjQgNjA4IDM2NFM1NDQgMzkyLjY3MiA1NDQgNDI4QzU0NCA0NjMuMzI4IDU3Mi42NzIgNDkyIDYwOCA0OTJTNjcyIDQ2My4zMjggNjcyIDQyOFoiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxNEIiIHVuaWNvZGU9IiYjeEUxNEI7IiBkPSJNNTEyIDgxMkMyMjkuMjQ4IDgxMiAwIDU4Mi43NTIgMCAzMDBTMjI5LjI0OC0yMTIgNTEyLTIxMkM3OTQuNzUyLTIxMiAxMDI0IDE3LjI0OCAxMDI0IDMwMFM3OTQuNzUyIDgxMiA1MTIgODEyWk0zMDQgNTA4QzMzMC40OTYgNTA4IDM1MiA0ODYuNDk2IDM1MiA0NjBTMzMwLjQ5NiA0MTIgMzA0IDQxMkMyNzcuNTA0IDQxMiAyNTYgNDMzLjUwNCAyNTYgNDYwUzI3Ny41MDQgNTA4IDMwNCA1MDhaTTc0MC40OCA0NEM3MzkuMDI5MyA0My43ODY3IDczNy4zNjUzIDQzLjYxNiA3MzUuNjU4NyA0My42MTYgNzE5LjY1ODcgNDMuNjE2IDcwNi4zODkzIDU1LjM0OTMgNzA0LjA0MjcgNzAuNjY2NyA2OTAuMzg5MyAxNjQuNzA0IDYxMC40NzQ3IDIzNS45NTczIDUxMy45MiAyMzUuOTU3MyA1MTMuMjM3MyAyMzUuOTU3MyA1MTIuNTk3MyAyMzUuOTU3MyA1MTEuOTE0NyAyMzUuOTU3MyA0MTYgMjMzLjM5NzMgMzM2Ljk4MTMgMTYzLjU5NDcgMzIwLjIxMzMgNzIuMDc0NyAzMTcuNDgyNyA1NS41MiAzMDQuMjk4NyA0My45NTczIDI4OC40MjY3IDQzLjk1NzMgMjg4LjI5ODcgNDMuOTU3MyAyODguMTI4IDQzLjk1NzMgMjg4IDQzLjk1NzNIMjgyLjkyMjdDMjY3LjM0OTMgNDYuMzA0IDI1NS41NzMzIDU5LjU3MzMgMjU1LjU3MzMgNzUuNjE2IDI1NS41NzMzIDc3LjUzNiAyNTUuNzQ0IDc5LjQxMzMgMjU2LjA4NTMgODEuMjQ4IDI3Ny41MDQgMjA1LjE1MiAzODMuNjU4NyAyOTguNTQ5MyA1MTEuOTE0NyAyOTkuOTE0NyA2NDEuMTUyIDI5OS44MjkzIDc0OC4xNiAyMDUuNDA4IDc2Ny44NzIgODEuODg4IDc2OC4yOTg3IDc4Ljk4NjcgNzY4LjQyNjcgNzcuMzIyNyA3NjguNDI2NyA3NS42NTg3IDc2OC40MjY3IDU5LjQ0NTMgNzU2LjM1MiA0Ni4wNDggNzQwLjczNiA0My45NTczWk03MjAgNDExLjM2QzY5My41MDQgNDExLjM2IDY3MiA0MzIuODY0IDY3MiA0NTkuMzZTNjkzLjUwNCA1MDcuMzYgNzIwIDUwNy4zNkM3NDYuMjgyNyA1MDcuMzYgNzY3LjYxNiA0ODYuMjQgNzY4IDQ2MC4wNDI3IDc2OCA0MzMuNTA0IDc0Ni40OTYgNDEyIDcyMCA0MTJaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMTRDIiB1bmljb2RlPSImI3hFMTRDOyIgZD0iTTI1NiA0NjBDMjU2IDQ4Ni4yNCAyNzcuNzYgNTA4IDMwNCA1MDhTMzUyIDQ4Ni4yNCAzNTIgNDYwQzM1MiA0MzMuNzYgMzMwLjI0IDQxMiAzMDQgNDEyUzI1NiA0MzMuNzYgMjU2IDQ2MFpNMTAyNCAzMDBDMTAyNCAxNy43NiA3OTQuMjQtMjEyIDUxMi0yMTJTMCAxNy43NiAwIDMwMCAyMjkuNzYgODEyIDUxMiA4MTIgMTAyNCA1ODIuMjQgMTAyNCAzMDBaTTk2MCAzMDBDOTYwIDU0Ny4wNCA3NTkuMDQgNzQ4IDUxMiA3NDhTNjQgNTQ3LjA0IDY0IDMwMEM2NCA1Mi45NiAyNjQuOTYtMTQ4IDUxMi0xNDhTOTYwIDUyLjk2IDk2MCAzMDBaTTcyMCA1MDhDNjkzLjc2IDUwOCA2NzIgNDg2LjI0IDY3MiA0NjBTNjkzLjc2IDQxMiA3MjAgNDEyIDc2OCA0MzMuNzYgNzY4IDQ2MEM3NjggNDg2LjI0IDc0Ni4yNCA1MDggNzIwIDUwOFpNNTEyIDMwMEMzODcuMiAzMDAgMjc3LjEyIDIwNS45MiAyNTYuNjQgODEuMTIgMjUzLjQ0IDYzLjg0IDI2NS42IDQ3LjIgMjgyLjg4IDQ0IDI4NC44IDQ0IDI4Ni4wOCA0NCAyODggNDQgMzAzLjM2IDQ0IDMxNi44IDU0Ljg4IDMxOS4zNiA3MC44OCAzMzQuNzIgMTYzLjY4IDQxOS4yIDIzNiA1MTIgMjM2IDYwOCAyMzYgNjkwLjU2IDE2NC45NiA3MDQuNjQgNzEuNTIgNzA3LjIgNTQuMjQgNzIzLjg0IDQyLjA4IDc0MS4xMiA0NC42NFM3NzAuNTYgNjMuMiA3NjggODEuMTJDNzQ4LjggMjA1LjkyIDYzOS4zNiAzMDAgNTEyIDMwMFoiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxNEQiIHVuaWNvZGU9IiYjeEUxNEQ7IiBkPSJNMTAwNi44OTA3IDQwMS4wNzczQzk2Ny43MjI3IDQyNy42NTg3IDkyMS44NTYgNDI4LjI1NiA4OTEuNTIgNDI0LjQ1ODcgODc2LjUwMTMgNDg3LjUyIDgxOS4zMjggNTIzLjIzMiA4MTYuNTEyIDUyNC45Mzg3TDc5NC45MjI3IDUzOC4xNjUzIDc3OS40NzczIDUxOC4wNjkzQzczMC43MDkzIDQ1NC41ODEzIDc0My41OTQ3IDM4NS40NjEzIDc2NC4yNDUzIDM0Mi45MjI3IDczOC41NiAzMjkuMzEyIDcxMi45MTczIDMyOC44NDI3IDcxMi43MDQgMzI4Ljg0MjdINjk1LjM4MTNWNDMzLjU4OTNINTc3LjI4VjYzNy44MzQ3SDQzNC42MDI3VjUzNS42OTA3SDIwMC43ODkzVjQzMy41NDY3SDgzLjg4MjdWMzI4LjhINy42MzczTDQuMDEwNyAzMDQuODY0QzMuMiAyOTkuNDQ1My0xNS4xMDQgMTcxLjA2MTMgNzAuMzU3MyA3MS42NDggMTMyLjg2NC0xLjA1NiAyMzIuNzg5My0zNy45MiAzNjcuMjc0Ny0zNy45MiA1NzUuMDYxMy0zNy45MiA3MDIuNzYyNyA1My42IDc3My4yNDggMTMwLjQgODI4LjI0NTMgMTkwLjMwNCA4NTcuNiAyNTAuMDggODcwLjE4NjcgMjgwLjIwMjcgMTAwMC4zNjI3IDI4Mi4zNzg3IDEwMTguMDI2NyAzNjguNzM2IDEwMTguNzUyIDM3Mi41NzZMMTAyMi4xMjI3IDM5MC42NjY3IDEwMDYuODkwNyA0MDEuMDM0N1pNNDc1LjYwNTMgNDM0LjAxNlY0OTQuNzczM0g1MzYuMzYyN1Y0MzQuMDE2SDQ3NS42MDUzWk0yNDEuNzkyIDMzMS44NzJWMzkyLjYyOTNIMzAyLjU0OTNWMzMxLjg3MkgyNDEuNzkyWk0zNTguNjk4NyAzMzEuODcyVjM5Mi42MjkzSDQxOS40NTZWMzMxLjg3MkgzNTguNjk4N1pNNDc1LjYwNTMgMzMxLjg3MlYzOTIuNjI5M0g1MzYuMzYyN1YzMzEuODcySDQ3NS42MDUzWk01OTMuNzA2NyAzOTIuNjI5M0g2NTQuNDY0VjMzMS44NzJINTkzLjcwNjdWMzkyLjYyOTNaTTQ3NS42MDUzIDU5Ni44NzQ3SDUzNi4zNjI3VjUzNi4xMTczSDQ3NS42MDUzVjU5Ni44NzQ3Wk0zNTguNjk4NyA0OTQuNzczM0g0MTkuNDU2VjQzNC4wMTZIMzU4LjY5ODdWNDk0Ljc3MzNaTTI0MS43OTIgNDk0Ljc3MzNIMzAyLjU0OTNWNDM0LjAxNkgyNDEuNzkyVjQ5NC43NzMzWk0xMjQuODg1MyAzOTIuNjI5M0gxODUuNjQyN1YzMzEuODcySDEyNC44ODUzVjM5Mi42MjkzWk0zNjcuMzE3MyAxOC40ODUzQzMwMy40NDUzIDE4LjQ4NTMgMjQ5LjAwMjcgMjcuNDQ1MyAyMDQuMzczMyA0NS4yMzczIDIzNy40ODI3IDUyLjE5MiAyNzUuMiA2NS4xNjI3IDMwOS4xNjI3IDg5LjA1NiAzMjEuODc3MyA5OC4wMTYgMzI0Ljk0OTMgMTE1LjU1MiAzMTUuOTg5MyAxMjguMjY2N1MyODkuNDkzMyAxNDQuMDUzMyAyNzYuNzM2IDEzNS4wOTMzQzIyMS41MjUzIDk2LjI2NjcgMTUwLjIyOTMgOTMuNTM2IDEyNi45MzMzIDkzLjgzNDcgMTIyLjE5NzMgOTguMzU3MyAxMTcuNzE3MyAxMDMuMDkzMyAxMTMuNDUwNyAxMDggNjQuMzg0IDE2NC43NDY3IDU3Ljg5ODcgMjM2LjA0MjcgNTguMjgyNyAyNzIuNTY1M0g3MTIuNzQ2N0M3MTUuMjIxMyAyNzIuNTY1MyA3NzMuODg4IDI3My4wMzQ3IDgyMC4zNTIgMzEzLjUyNTNMODIzLjg1MDcgMzE2LjU5NzNDODE4LjQ3NDcgMzAwLjg1MzMgNzE2Ljg0MjcgMTguNDg1MyAzNjcuMjc0NyAxOC40ODUzWk04NTIuMjY2NyAzMzYuODIxM0w4MzQuODU4NyAzMzcuNjMyIDgyNC4zNjI3IDM1MS41ODRDODIzLjkzNiAzNTIuMTgxMyA3ODYuODU4NyA0MDIuNjk4NyA4MDkuMzQ0IDQ1OC4xNjUzIDgyMy43MjI3IDQ0My4yMzIgODM5LjU5NDcgNDIwLjE5MiA4MzguNzg0IDM5MS42MDUzTDgzNy42MzIgMzUxLjcxMiA4NzUuNjA1MyAzNjRDODc2LjA3NDcgMzY0LjE3MDcgOTE1Ljk2OCAzNzYuMzMwNyA5NTIuNzA0IDM2NS4xMDkzIDkzOS42OTA3IDM1MC45NDQgOTExLjQ4OCAzMzMuOTYyNyA4NTIuMjY2NyAzMzYuODIxM1pNMzc5LjI2NCAyMjIuNDMyQzM1My45MiAyMjIuNDMyIDMzMy4zMTIgMjAxLjgyNCAzMzMuMzEyIDE3Ni40OFMzNTMuOTIgMTMwLjUyOCAzNzkuMjY0IDEzMC41MjhDNDA0LjYwOCAxMzAuNTI4IDQyNS4yMTYgMTUxLjEzNiA0MjUuMjE2IDE3Ni40OFM0MDQuNjA4IDIyMi40MzIgMzc5LjI2NCAyMjIuNDMyWk0zNzkuMjY0IDE2Ni4xMTJDMzczLjU0NjcgMTY2LjExMiAzNjguODk2IDE3MC43NjI3IDM2OC44OTYgMTc2LjQ4UzM3My41NDY3IDE4Ni44NDggMzc5LjI2NCAxODYuODQ4IDM4OS42MzIgMTgyLjE5NzMgMzg5LjYzMiAxNzYuNDhDMzg5LjYzMiAxNzAuNzYyNyAzODQuOTgxMyAxNjYuMTEyIDM3OS4yNjQgMTY2LjExMloiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxNEUiIHVuaWNvZGU9IiYjeEUxNEU7IiBkPSJNNTEyIDQ0QzUwNS42IDQ0IDQ5OC41NiA0Ni41NiA0OTMuNDQgNTIuMzJMMTM2Ljk2IDQzNi4zMkMxMjguNjQgNDQ1LjI4IDEyNi4wOCA0NTkuMzYgMTI5LjkyIDQ3MS41MlMxNDQgNDkyIDE1NS41MiA0OTJIODY4LjQ4Qzg4MCA0OTIgODg5LjYgNDgzLjY4IDg5NC4wOCA0NzEuNTJTODk1LjM2IDQ0NS4yOCA4ODcuMDQgNDM2LjMyTDUzMC41NiA1Mi4zMkM1MjUuNDQgNDYuNTYgNTE4LjQgNDQgNTEyIDQ0WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTE0RiIgdW5pY29kZT0iJiN4RTE0RjsiIGQ9Ik05OTIgMjA0Qzk3NC4zMzYgMjA0IDk2MCAxODkuNjY0IDk2MCAxNzJWLTg0Qzk2MC0xMDEuNjY0IDk0NS42NjQtMTE2IDkyOC0xMTZIOTZDNzguMzM2LTExNiA2NC0xMDEuNjY0IDY0LTg0VjE3MkM2NCAxODkuNjY0IDQ5LjY2NCAyMDQgMzIgMjA0UzAgMTg5LjY2NCAwIDE3MlYtODRDMC0xMzcuMDM0NyA0Mi45NjUzLTE4MCA5Ni0xODBIOTI4Qzk4MS4wMzQ3LTE4MCAxMDI0LTEzNy4wMzQ3IDEwMjQtODRWMTcyQzEwMjQgMTg5LjY2NCAxMDA5LjY2NCAyMDQgOTkyIDIwNFpNNDkyLjE2IDE5LjA0VjE5LjA0QzQ5Ny4xMDkzIDE1LjExNDcgNTAzLjQ2NjcgMTIuNzI1MyA1MTAuNDIxMyAxMi43MjUzUzUyMy42OTA3IDE1LjExNDcgNTI4LjcyNTMgMTkuMDgyN0w1MjguNjgyNyAxOS4wNCA2ODguNjgyNyAxNDcuMDRDNjk3LjM0NCAxNTIuODQyNyA3MDIuOTc2IDE2Mi42MTMzIDcwMi45NzYgMTczLjcwNjcgNzAyLjk3NiAxOTEuMzcwNyA2ODguNjQgMjA1LjcwNjcgNjcwLjk3NiAyMDUuNzA2NyA2NjIuNDQyNyAyMDUuNzA2NyA2NTQuNzIgMjAyLjM3ODcgNjQ5LjAwMjcgMTk2Ljk2TDU0NC4wNDI3IDExMC41NlY3NDhDNTQ0LjA0MjcgNzY1LjY2NCA1MjkuNzA2NyA3ODAgNTEyLjA0MjcgNzgwUzQ4MC4wNDI3IDc2NS42NjQgNDgwLjA0MjcgNzQ4VjEwOEwzNzEuODgyNyAxOTYuOTZDMzY2Ljg5MDcgMjAwLjMzMDcgMzYwLjc4OTMgMjAyLjI5MzMgMzU0LjE3NiAyMDIuMjkzMyAzMzYuNTEyIDIwMi4yOTMzIDMyMi4xNzYgMTg3Ljk1NzMgMzIyLjE3NiAxNzAuMjkzMyAzMjIuMTc2IDE2MS4xMiAzMjYuMDE2IDE1Mi44ODUzIDMzMi4yMDI3IDE0Ny4wNFoiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxNTAiIHVuaWNvZGU9IiYjeEUxNTA7IiBkPSJNNDgwIDE3MkM0NjIuNDY0IDE3Mi4yMTMzIDQ0OC4zNDEzIDE4Ni40NjQgNDQ4LjM0MTMgMjA0IDQ0OC4zNDEzIDIxMi4xMDY3IDQ1MS4zNzA3IDIxOS41MzA3IDQ1Ni4zMiAyMjUuMTYyN0w5NjguMjc3MyA4MDEuMTJDOTc0LjEyMjcgODA3LjE3ODcgOTgyLjI3MiA4MTAuOTMzMyA5OTEuMzYgODEwLjkzMzMgMTAwOS4wMjQgODEwLjkzMzMgMTAyMy4zNiA3OTYuNTk3MyAxMDIzLjM2IDc3OC45MzMzIDEwMjMuMzYgNzcxLjI5NiAxMDIwLjY3MiA3NjQuMjk4NyAxMDE2LjIzNDcgNzU4Ljc5NDdMNTA0LjI3NzMgMTgyLjgzNzNDNDk4LjM4OTMgMTc2LjEzODcgNDg5LjgxMzMgMTcxLjk1NzMgNDgwLjI1NiAxNzEuOTU3MyA0ODAuMTcwNyAxNzEuOTU3MyA0ODAuMDQyNyAxNzEuOTU3MyA0NzkuOTU3MyAxNzEuOTU3M1pNODY0LTIxMkgxNjBDNzEuNjM3My0yMTIgMC0xNDAuMzYyNyAwLTUyVjY1MkMwIDc0MC4zNjI3IDcxLjYzNzMgODEyIDE2MCA4MTJINjcyQzY4OS42NjQgODEyIDcwNCA3OTcuNjY0IDcwNCA3ODBTNjg5LjY2NCA3NDggNjcyIDc0OEgxNjBDMTA2Ljk2NTMgNzQ4IDY0IDcwNS4wMzQ3IDY0IDY1MlYtNTJDNjQtMTA1LjAzNDcgMTA2Ljk2NTMtMTQ4IDE2MC0xNDhIODY0QzkxNy4wMzQ3LTE0OCA5NjAtMTA1LjAzNDcgOTYwLTUyVjQ2MEM5NjAgNDc3LjY2NCA5NzQuMzM2IDQ5MiA5OTIgNDkyUzEwMjQgNDc3LjY2NCAxMDI0IDQ2MFYtNTJDMTAyNC0xNDAuMzYyNyA5NTIuMzYyNy0yMTIgODY0LTIxMloiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxNTEiIHVuaWNvZGU9IiYjeEUxNTE7IiBkPSJNMjg4IDE0MEg3MzZWNzZIMjg4Wk00MDAgMTg4TDMzNiAxODggMzM2IDI1MiA1NjAgNDc2IDYyNCA0MTJaTTU3Ni40NTk1IDQ5MS44MjlMNjA4LjEzNzQgNTIzLjUwNzkgNjcxLjQ5NTIgNDYwLjE1MjMgNjM5LjgxNzQgNDI4LjQ3MzNaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMTUyIiB1bmljb2RlPSImI3hFMTUyOyIgZD0iTTMyMCAzMDBDMzIwIDI2NC44IDI5MS4yIDIzNiAyNTYgMjM2UzE5MiAyNjQuOCAxOTIgMzAwQzE5MiAzMzUuMiAyMjAuOCAzNjQgMjU2IDM2NFMzMjAgMzM1LjIgMzIwIDMwMFpNNTEyIDM2NEM0NzYuOCAzNjQgNDQ4IDMzNS4yIDQ0OCAzMDBTNDc2LjggMjM2IDUxMiAyMzYgNTc2IDI2NC44IDU3NiAzMDBDNTc2IDMzNS4yIDU0Ny4yIDM2NCA1MTIgMzY0Wk03NjggMzY0QzczMi44IDM2NCA3MDQgMzM1LjIgNzA0IDMwMFM3MzIuOCAyMzYgNzY4IDIzNiA4MzIgMjY0LjggODMyIDMwMEM4MzIgMzM1LjIgODAzLjIgMzY0IDc2OCAzNjRaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMTUzIiB1bmljb2RlPSImI3hFMTUzOyIgZD0iTTk4MS41ODkzIDcwMi4zMDRINDIuNDUzM0MxOC44NTg3IDcwMS40OTMzIDAuMDQyNyA2ODIuMTY1MyAwLjA0MjcgNjU4LjQ0MjcgMC4wNDI3IDY1OC4xODY3IDAuMDQyNyA2NTcuOTMwNyAwLjA0MjcgNjU3LjYzMkwwLjA0MjcgNTQ1Ljc2IDQ5OS42MjY3IDIyNi44NjkzQzUwMy4wODI3IDIyNC40MzczIDUwNy4zOTIgMjIyLjk4NjcgNTEyLjA0MjcgMjIyLjk4NjdTNTIxLjAwMjcgMjI0LjQzNzMgNTI0LjU0NCAyMjYuOTEyTDEwMjQuMDQyNyA1NDUuNzZWNjU3LjY3NDdDMTAyNC4wNDI3IDY1Ny44ODggMTAyNC4wNDI3IDY1OC4xNDQgMTAyNC4wNDI3IDY1OC40NDI3IDEwMjQuMDQyNyA2ODIuMTY1MyAxMDA1LjIyNjcgNzAxLjQ5MzMgOTgxLjY3NDcgNzAyLjMwNFpNNTEyIDEzMy4yMTZDNDkwLjc5NDcgMTMzLjIxNiA0NzEuMDgyNyAxMzkuNDg4IDQ1NC41MjggMTUwLjI4MjdMMCA0NDEuMTQxM1YtNTcuNjc0N0MwLTU3Ljg4OCAwLTU4LjE0NCAwLTU4LjQ0MjcgMC04Mi4xNjUzIDE4LjgxNi0xMDEuNDkzMyA0Mi4zNjgtMTAyLjMwNEw5ODEuNTg5My0xMDIuMzA0QzEwMDUuMTg0LTEwMS40OTMzIDEwMjQtODIuMTY1MyAxMDI0LTU4LjQ0MjcgMTAyNC01OC4xODY3IDEwMjQtNTcuOTMwNyAxMDI0LTU3LjYzMkwxMDI0IDQ0MS4xODQgNTY5LjA0NTMgMTQ4LjYxODdDNTUzLjQyOTMgMTM4Ljk3NiA1MzQuNDg1MyAxMzMuMjE2IDUxNC4yMTg3IDEzMy4yMTYgNTEzLjQ1MDcgMTMzLjIxNiA1MTIuNjQgMTMzLjIxNiA1MTEuODcyIDEzMy4yNTg3WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTE1NCIgdW5pY29kZT0iJiN4RTE1NDsiIGQ9Ik05MTQuMzA0IDcwMi4zMDRIMTA5LjczODdDNDkuMTUyIDcwMi4zMDQgMC4wNDI3IDY1My4xOTQ3IDAuMDQyNyA1OTIuNjA4VjcuNDc3M0MwLjA0MjctNTMuMTA5MyA0OS4xNTItMTAyLjIxODcgMTA5LjczODctMTAyLjIxODdIOTE0LjMwNEM5NzQuODkwNy0xMDIuMjE4NyAxMDI0LTUzLjEwOTMgMTAyNCA3LjQ3NzNWNTkyLjYwOEMxMDI0IDY1My4xOTQ3IDk3NC44OTA3IDcwMi4zMDQgOTE0LjMwNCA3MDIuMzA0Wk0xMDkuNjk2IDYyOS4xMzA3SDkxNC4yNjEzQzkzNC40NDI3IDYyOS4xMzA3IDk1MC44MjY3IDYxMi43NDY3IDk1MC44MjY3IDU5Mi41NjUzVjUwMS4xMzA3TDUyMi45MjI3IDIzOS4yODUzQzUxOS45MzYgMjM3LjM2NTMgNTE2LjI2NjcgMjM2LjIxMzMgNTEyLjI5ODcgMjM2LjIxMzNTNTA0LjcwNCAyMzcuMzY1MyA1MDEuNjMyIDIzOS4zNzA3TDczLjA4OCA1MDEuMTczM1Y1OTIuNjA4QzczLjA4OCA2MTIuNzg5MyA4OS40NzIgNjI5LjE3MzMgMTA5LjY1MzMgNjI5LjE3MzNaTTkxNC4zMDQtMjkuMTMwN0gxMDkuNzM4N0M4OS41NTczLTI5LjEzMDcgNzMuMTczMy0xMi43NDY3IDczLjE3MzMgNy40MzQ3VjQxNS41ODRMNDYzLjAxODcgMTc3LjEyQzQ3Ni44ODUzIDE2OC41NDQgNDkzLjY5NiAxNjMuNTA5MyA1MTEuNjU4NyAxNjMuNTA5M1M1NDYuNDMyIDE2OC41ODY3IDU2MC42ODI3IDE3Ny4zNzZMOTUwLjg2OTMgNDE1LjU4NFY3LjQzNDdDOTUwLjg2OTMtMTIuNzQ2NyA5MzQuNDg1My0yOS4xMzA3IDkxNC4zMDQtMjkuMTMwN1oiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxNTUiIHVuaWNvZGU9IiYjeEUxNTU7IiBkPSJNOTYgMzMySDM4NEExMjggMTI4IDAgMCAxIDY0MCAzMzJIOTI4QTMyIDMyIDAgMCAxIDk2MCAzNjRMODMyIDcxNkEzMiAzMiAwIDAgMSA4MDAgNzQ4SDIyNEEzMiAzMiAwIDAgMSAxOTIgNzE2TDY0IDM2NEEzMiAzMiAwIDAgMSA5NiAzMzJaTTkyOCAyNjhINjkyLjhBMTkyIDE5MiAwIDAgMCAzMzEuMiAyNjhIOTZBMzIgMzIgMCAwIDEgNjQgMjM2VjEyQTMyIDMyIDAgMCAxIDk2LTIwSDkyOEEzMiAzMiAwIDAgMSA5NjAgMTJWMjM2QTMyIDMyIDAgMCAxIDkyOCAyNjhaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMTU2IiB1bmljb2RlPSImI3hFMTU2OyIgZD0iTTgzMiA3MTZBMzIgMzIgMCAwIDEgODAwIDc0OEgyMjRBMzIgMzIgMCAwIDEgMTkyIDcxNkw2NCAzMDBWMTJBMzIgMzIgMCAwIDEgOTYtMjBIOTI4QTMyIDMyIDAgMCAxIDk2MCAxMlYzMDBaTTI0OS4xMiA2ODRINzc0Ljg4TDg4My4yIDMzMkg2MDhBOTYgOTYgMCAwIDAgNDE2IDMzMkgxNDAuOFpNODk2IDQ0SDEyOFYyNjhIMzY1LjQ0QTE2MCAxNjAgMCAwIDEgNjU4LjU2IDI2OEg4OTZaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMTU3IiB1bmljb2RlPSImI3hFMTU3OyIgZD0iTTUxMi0xNDkuOTJDMjY0Ljk2LTE0OS45MiA2NCA1MS4wNCA2NCAyOTguMDggNjQgNDY5LjYgMTYwIDYyMy44NCAzMTMuNiA3MDAgMzI5LjYgNzA3LjY4IDM0OC44IDcwMS4yOCAzNTYuNDggNjg1LjI4IDM2NC44IDY2OS4yOCAzNTcuNzYgNjUwLjA4IDM0Mi40IDY0Mi40IDIwOS45MiA1NzcuMTIgMTI4IDQ0NS4yOCAxMjggMjk4LjA4IDEyOCA4Ni4yNCAzMDAuMTYtODUuOTIgNTEyLTg1LjkyUzg5NiA4Ni4yNCA4OTYgMjk4LjA4Qzg5NiA0NDUuOTIgODEyLjggNTc3Ljc2IDY3OS42OCA2NDIuNCA2NjMuNjggNjUwLjA4IDY1Ny4yOCA2NjkuMjggNjY0Ljk2IDY4NS4yOFM2OTEuODQgNzA3LjY4IDcwNy44NCA3MDBDODYzLjM2IDYyNC40OCA5NjAgNDcwLjI0IDk2MCAyOTguMDggOTYwIDUxLjA0IDc1OS4wNC0xNDkuOTIgNTEyLTE0OS45MlpNNTEyIDQyOEM0OTQuMDggNDI4IDQ4MCA0NDIuMDggNDgwIDQ2MFY3ODBDNDgwIDc5Ny45MiA0OTQuMDggODEyIDUxMiA4MTJTNTQ0IDc5Ny45MiA1NDQgNzgwVjQ2MEM1NDQgNDQyLjA4IDUyOS45MiA0MjggNTEyIDQyOFoiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxNTgiIHVuaWNvZGU9IiYjeEUxNTg7IiBkPSJNNTEyIDc0OEMyNjQgNzQ4IDY0IDU0OCA2NCAzMDBTMjY0LTE0OCA1MTItMTQ4IDk2MCA1MiA5NjAgMzAwIDc2MCA3NDggNTEyIDc0OFpNNTEyIDQ0QzQ4NC44IDQ0IDQ2NCA2NC44IDQ2NCA5MlM0ODQuOCAxNDAgNTEyIDE0MEM1MzkuMiAxNDAgNTYwIDExOS4yIDU2MCA5MlM1MzkuMiA0NCA1MTIgNDRaTTU2MCA1MDMuMkw1NDQgMjA0QzU0NCAxODYuNCA1MjkuNiAxNzIgNTEyIDE3MiA0OTQuNCAxNzIgNDgwIDE4Ni40IDQ4MCAyMDRMNDY0IDUwMy4yQzQ2NCA1MDQuOCA0NjQgNTA2LjQgNDY0IDUwOCA0NjQgNTM1LjIgNDg0LjggNTU2IDUxMiA1NTYgNTM5LjIgNTU2IDU2MCA1MzUuMiA1NjAgNTA4IDU2MCA1MDYuNCA1NjAgNTA0LjggNTYwIDUwMy4yWiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTE1OSIgdW5pY29kZT0iJiN4RTE1OTsiIGQ9Ik01MTIgNzQ4QzI2NCA3NDggNjQgNTQ4IDY0IDMwMFMyNjQtMTQ4IDUxMi0xNDggOTYwIDUyIDk2MCAzMDAgNzYwIDc0OCA1MTIgNzQ4Wk01MTItODRDMjk5LjItODQgMTI4IDg3LjIgMTI4IDMwMFMyOTkuMiA2ODQgNTEyIDY4NCA4OTYgNTEyLjggODk2IDMwMCA3MjQuOC04NCA1MTItODRaTTUxMiA5Mk00NjQgOTJBNDggNDggMCAxIDEgNTYwIDkyIDQ4IDQ4IDAgMSAxIDQ2NCA5MlpNNTEyIDU1NkM0ODQuOCA1NTYgNDY0IDUzNS4yIDQ2NCA1MDggNDY0IDUwNi40IDQ2NCA1MDQuOCA0NjQgNTAzLjJMNDgwIDIwNEM0ODAgMTg2LjQgNDk0LjQgMTcyIDUxMiAxNzIgNTI5LjYgMTcyIDU0NCAxODYuNCA1NDQgMjA0TDU2MCA1MDMuMkM1NjAgNTA0LjggNTYwIDUwNi40IDU2MCA1MDggNTYwIDUzNS4yIDUzOS4yIDU1NiA1MTIgNTU2WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTE1QSIgdW5pY29kZT0iJiN4RTE1QTsiIGQ9Ik05NDcuMiAzMS4yTDU5MiA2NjBDNTY2LjQgNzAzLjIgNTEyIDcxOS4yIDQ2Ny4yIDY5NS4yIDQ1Mi44IDY4Ny4yIDQ0MS42IDY3NC40IDQzMiA2NjBMNzYuOCAzMS4yQzYwLjggMi40IDYwLjgtMzIuOCA3Ni44LTYxLjYgOTIuOC05MC40IDEyMy4yLTEwOCAxNTUuMi0xMDYuNEg4NjguOEM5MDAuOC0xMDYuNCA5MzEuMi04OC44IDk0Ny4yLTYxLjYgOTYzLjItMzIuOCA5NjQuOCAyLjQgOTQ3LjIgMzEuMlpNNTEyIDQ0QzQ5Mi44IDQ0IDQ3NS4yIDYwIDQ3NS4yIDc5LjIgNDc1LjIgOTguNCA0OTEuMiAxMTYgNTEwLjQgMTE2IDUyOS42IDExNiA1NDcuMiAxMDAgNTQ3LjIgODAuOCA1NDcuMiA4MC44IDU0Ny4yIDgwLjggNTQ3LjIgODAuOCA1NDcuMiA2MCA1MzEuMiA0NCA1MTIgNDRMNTEyIDQ0Wk01NDcuMiAzODhMNTM2IDE2NEM1MzYgMTUxLjIgNTI0LjggMTQwIDUxMiAxNDBTNDg4IDE1MS4yIDQ4OCAxNjRMNDc2LjggMzg4QzQ3Ni44IDM4OS42IDQ3Ni44IDM5MS4yIDQ3Ni44IDM5MS4yIDQ3Ni44IDQxMC40IDQ5Mi44IDQyOCA1MTMuNiA0MjhTNTQ4LjggNDEyIDU0OC44IDM5MS4yTDU0OC44IDM5MS4yQzU0OC44IDM5MS4yIDU0OC44IDM4OS42IDU0Ny4yIDM4OFoiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxNUIiIHVuaWNvZGU9IiYjeEUxNUI7IiBkPSJNNTEyIDY0Mi40QzUyMS42IDY0Mi40IDUzMS4yIDYzNy42IDUzNiA2MjhMODkyLjgtMi40QzkwMC44LTE1LjIgODk2LTMyLjggODgzLjItNDAuOCA4NzguNC00Mi40IDg3NS4yLTQ0IDg3MC40LTQ0SDE1NS4yQzEzOS4yLTQ0IDEyOC0zMS4yIDEyOC0xNS4yIDEyOC0xMC40IDEyOS42LTUuNiAxMzEuMi0yLjRMNDg4IDYyOEM0OTIuOCA2MzcuNiA1MDIuNCA2NDIuNCA1MTIgNjQyLjRNNTEyIDcwNi40QzQ3OC40IDcwNi40IDQ0OCA2ODguOCA0MzIgNjYwTDc2LjggMzEuMkM2MC44IDIuNCA2MC44LTMyLjggNzYuOC02MS42IDkyLjgtOTAuNCAxMjMuMi0xMDggMTU1LjItMTA2LjRIODY4LjhDOTAwLjgtMTA2LjQgOTMxLjItODguOCA5NDcuMi02MS42IDk2My4yLTMyLjggOTYzLjIgMi40IDk0Ny4yIDMxLjJMNTkyIDY2MEM1NzYgNjg4LjggNTQ1LjYgNzA2LjQgNTEyIDcwNi40Wk01MTIgNzkuMk00NzYuOCA3OS4yQTM1LjIgMzUuMiAwIDEgMSA1NDcuMiA3OS4yIDM1LjIgMzUuMiAwIDEgMSA0NzYuOCA3OS4yWk00ODggMTY0QzQ4OCAxNTEuMiA0OTkuMiAxNDAgNTEyIDE0MFM1MzYgMTUxLjIgNTM2IDE2NEw1NDcuMiAzODhDNTQ3LjIgMzg5LjYgNTQ3LjIgMzkxLjIgNTQ3LjIgMzkxLjIgNTQ3LjIgNDEwLjQgNTMxLjIgNDI2LjQgNTEyIDQyNi40UzQ3Ni44IDQxMC40IDQ3Ni44IDM5MS4yTDQ3Ni44IDM5MS4yQzQ3Ni44IDM4OS42IDQ3Ni44IDM4OCA0NzYuOCAzODhMNDg4IDE2NFoiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxNUMiIHVuaWNvZGU9IiYjeEUxNUM7IiBkPSJNNTEyLTEyTTQ0MC0xMkE3MiA3MiAwIDEgMSA1ODQtMTIgNzIgNzIgMCAxIDEgNDQwLTEyWk01MTIgNjg0QTcwLjcyIDcwLjcyIDAgMCAxIDQ0MCA2MTJWNjA0TDQ2NCAxNTZBNDggNDggMCAwIDEgNTYwIDE1Nkw1ODQgNjA0VjYxMkE3MC43MiA3MC43MiAwIDAgMSA1MTIgNjg0WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTE1RCIgdW5pY29kZT0iJiN4RTE1RDsiIGQ9Ik04ODQuNDggNjEwLjRDODg5Ljg5ODcgNjIyLjIxODcgODkzLjA1NiA2MzYuMDQyNyA4OTMuMDU2IDY1MC41OTIgODkzLjA1NiA3MDUuMDM0NyA4NDguOTM4NyA3NDkuMTUyIDc5NC40OTYgNzQ5LjE1MlM2OTUuOTM2IDcwNS4wMzQ3IDY5NS45MzYgNjUwLjU5MkM2OTUuOTM2IDU5Ni4xNDkzIDc0MC4wNTMzIDU1Mi4wMzIgNzk0LjQ5NiA1NTIuMDMyIDgxMS41MiA1NTIuMDMyIDgyNy41MiA1NTYuMzQxMyA4NDEuNDcyIDU2My45MzZMODQwLjk2IDU2My42OEM4OTcuNjY0IDQ5Ni4xMzg3IDkzMi4wOTYgNDA4LjIwMjcgOTMyLjA5NiAzMTIuMjg4IDkzMi4wOTYgMjIzLjk2OCA5MDIuOTEyIDE0Mi40NzQ3IDg1My42NzQ3IDc2Ljg5Nkw4NTQuNCA3Ny45MkM4NTAuMzg5MyA3Mi42MjkzIDg0OCA2NS45NzMzIDg0OCA1OC43MiA4NDggNDEuMDU2IDg2Mi4zMzYgMjYuNzIgODgwIDI2LjcyIDg5MC40NTMzIDI2LjcyIDg5OS43MTIgMzEuNzEyIDkwNS41NTczIDM5LjQzNDdMOTA1LjYgMzkuNTJDOTYyLjI2MTMgMTE0LjU3MDcgOTk2LjM1MiAyMDkuNDE4NyA5OTYuMzUyIDMxMi4yMDI3IDk5Ni4zNTIgNDI2Ljg0OCA5NTMuOTg0IDUzMS41NTIgODg0LjAxMDcgNjExLjU1Mkw4ODQuNDggNjExLjA0Wk0yMjAuMTYgMzEyLjE2QzIxOS43NzYgMzUzLjMzMzMgMTkzLjQ5MzMgMzg4LjI3NzMgMTU2Ljg0MjcgNDAxLjU0NjdMMTU2LjE2IDQwMS43NkMxOTguMDE2IDU3Ni40MzczIDM1Mi44NTMzIDcwNC4yNjY3IDUzNy41NTczIDcwNC4yNjY3IDU2NC41MjI3IDcwNC4yNjY3IDU5MC44NDggNzAxLjUzNiA2MTYuMjc3MyA2OTYuMzczM0w2MTMuNzYgNjk2LjhDNjE1LjI5NiA2OTYuNTQ0IDYxNy4wODggNjk2LjM3MzMgNjE4LjkyMjcgNjk2LjM3MzMgNjM0LjU4MTMgNjk2LjM3MzMgNjQ3LjY4IDcwNy40MjQgNjUwLjgzNzMgNzIyLjE4NjdMNjUwLjg4IDcyMi40QzY1MS4yNjQgNzI0LjI3NzMgNjUxLjUyIDcyNi40NTMzIDY1MS41MiA3MjguNjcyIDY1MS41MiA3NDQuMjg4IDY0MC4yOTg3IDc1Ny4zMDEzIDYyNS40OTMzIDc2MC4xMTczTDYyNS4yOCA3NjAuMTZDNTk5LjYzNzMgNzY1LjI4IDU3MC4xOTczIDc2OC4xODEzIDU0MC4wMzIgNzY4LjE4MTMgMzIwLjA0MjcgNzY4LjE4MTMgMTM2LjQ0OCA2MTIuNTMzMyA5My4zMTIgNDA1LjM0NEw5Mi44IDQwMi40QzU1LjIxMDcgMzg4LjgzMiAyOC44IDM1My40MTg3IDI4LjggMzExLjkwNCAyOC44IDI1OC44NjkzIDcxLjc2NTMgMjE1LjkwNCAxMjQuOCAyMTUuOTA0UzIyMC44IDI1OC44NjkzIDIyMC44IDMxMS45MDRDMjIwLjggMzExLjk4OTMgMjIwLjggMzEyLjA3NDcgMjIwLjggMzEyLjIwMjdWMzEyLjIwMjdaTTczMi4xNiAyNC4xNkM2ODAuOTYgMjMuODYxMyA2MzkuMjMyLTE2LjUwMTMgNjM2LjgtNjcuMTQ2N0w2MzYuOC02Ny4zNkM2MDcuNDg4LTc1LjI1MzMgNTczLjg2NjctNzkuNzc2IDUzOS4xNzg3LTc5Ljc3NiAzODMuNjU4Ny03OS43NzYgMjQ5LjM4NjcgMTEuMTQ2NyAxODYuNjI0IDE0Mi43MzA3TDE4NS42IDE0NS4wNzczQzE4MC43Nzg3IDE1Ny4wNjY3IDE2OS4yNTg3IDE2NS4zODY3IDE1NS44MTg3IDE2NS4zODY3IDEzOC4xNTQ3IDE2NS4zODY3IDEyMy44MTg3IDE1MS4wNTA3IDEyMy44MTg3IDEzMy4zODY3IDEyMy44MTg3IDEyNy41ODQgMTI1LjM1NDcgMTIyLjEyMjcgMTI4LjA4NTMgMTE3LjQyOTNMMTI4IDExNy42QzIwMi4xMTItMzguMTc2IDM1OC4yMjkzLTE0My45NDY3IDUzOS4wNTA3LTE0My45NDY3IDU4MC4zOTQ3LTE0My45NDY3IDYyMC40NTg3LTEzOC40IDY1OC41Ni0xMjguMDMyTDY1NS4zNi0xMjguNzU3M0M2NzMuMDI0LTE1Mi41NjUzIDcwMS4wNTYtMTY3Ljc5NzMgNzMyLjYyOTMtMTY3Ljc5NzMgNzg1LjY2NC0xNjcuNzk3MyA4MjguNjI5My0xMjQuODMyIDgyOC42MjkzLTcxLjc5NzNTNzg1LjY2NCAyNC4yMDI3IDczMi42MjkzIDI0LjIwMjdDNzMyLjQ1ODcgMjQuMjAyNyA3MzIuMjg4IDI0LjIwMjcgNzMyLjExNzMgMjQuMjAyN0g3MzIuMTZaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMTVFIiB1bmljb2RlPSImI3hFMTVFOyIgZD0iTTY0MCAzMDBDNjQwIDIyOS4zMDEzIDU4Mi42OTg3IDE3MiA1MTIgMTcyUzM4NCAyMjkuMzAxMyAzODQgMzAwQzM4NCAzNzAuNjk4NyA0NDEuMzAxMyA0MjggNTEyIDQyOFM2NDAgMzcwLjY5ODcgNjQwIDMwMFpNNTEyIDY4NEMyMjkuNzYgNjg0IDAgNTExLjg0IDAgMzAwUzIyOS43Ni04NCA1MTItODQgMTAyNCA4OC4xNiAxMDI0IDMwMCA3OTQuMjQgNjg0IDUxMiA2ODRaTTUxMiAxMDhDNDA1Ljk3MzMgMTA4IDMyMCAxOTMuOTczMyAzMjAgMzAwUzQwNS45NzMzIDQ5MiA1MTIgNDkyQzYxOC4wMjY3IDQ5MiA3MDQgNDA2LjAyNjcgNzA0IDMwMFM2MTguMDI2NyAxMDggNTEyIDEwOFoiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxNUYiIHVuaWNvZGU9IiYjeEUxNUY7IiBkPSJNMTE2LjQ4IDY3Ni4zMkMxMTAuOTMzMyA2ODEuMDk4NyAxMDMuNjM3MyA2ODQgOTUuNzAxMyA2ODQgNzguMDM3MyA2ODQgNjMuNzAxMyA2NjkuNjY0IDYzLjcwMTMgNjUyIDYzLjcwMTMgNjQyLjI3MiA2OC4wMTA3IDYzMy41NjggNzQuODggNjI3LjcyMjdMOTA2LjkyMjctNzYuMzJDOTEyLjQ2OTMtODEuMDk4NyA5MTkuNzY1My04NCA5MjcuNzQ0LTg0IDk0NS40MDgtODQgOTU5Ljc0NC02OS42NjQgOTU5Ljc0NC01MiA5NTkuNzQ0LTQyLjI3MiA5NTUuNDM0Ny0zMy41NjggOTQ4LjU2NTMtMjcuNzIyN1pNNTEyIDQyOEw2NDAgMzE5LjJDNjMwLjM1NzMgMzgxLjE1MiA1NzcuMzY1MyA0MjggNTEzLjQ1MDcgNDI4IDUxMi45Mzg3IDQyOCA1MTIuNDI2NyA0MjggNTExLjkxNDcgNDI4Wk01MTIgNDkyQzYxNy45NDEzIDQ5MS45MTQ3IDcwMy44MjkzIDQwNS45ODQgNzAzLjgyOTMgMzAwIDcwMy44MjkzIDI4OC4wMTA3IDcwMi43MiAyNzYuMjc3MyA3MDAuNjI5MyAyNjQuODg1M0w5MjYuNzIgNzQuMDhDOTg1Ljg1NiAxMzEuNDI0IDEwMjIuODkwNyAyMTEuMjk2IDEwMjQgMjk5Ljc4NjcgMTAyNCA1MTEuODQgNzk0LjI0IDY4NCA1MTIgNjg0IDUxMS4yNzQ3IDY4NCA1MTAuNDIxMyA2ODQgNTA5LjU2OCA2ODQgNDIwLjg2NCA2ODQgMzM2LjM4NCA2NjYuMTIyNyAyNTkuNDEzMyA2MzMuNzgxM0w0NDggNDc5Ljg0QzQ2Ni45ODY3IDQ4Ny4xNzg3IDQ4OC45MTczIDQ5MS41NzMzIDUxMS44MjkzIDQ5MlpNNTEyIDE3MkwzODQgMjgwLjhDMzkzLjY0MjcgMjE4Ljg0OCA0NDYuNjM0NyAxNzIgNTEwLjU0OTMgMTcyIDUxMS4wNjEzIDE3MiA1MTEuNTczMyAxNzIgNTEyLjA4NTMgMTcyWk01MTIgMTA4QzQwNi4wNTg3IDEwOC4wODUzIDMyMC4xNzA3IDE5NC4wMTYgMzIwLjE3MDcgMzAwIDMyMC4xNzA3IDMxMS45ODkzIDMyMS4yOCAzMjMuNzIyNyAzMjMuMzcwNyAzMzUuMTE0N0w5Ny4yOCA1MjUuOTJDMzguMTQ0IDQ2OC41NzYgMS4xMDkzIDM4OC43MDQgMCAzMDAuMjEzMyAwIDg4LjE2IDIyOS43Ni04NCA1MTItODQgNTEyLjcyNTMtODQgNTEzLjU3ODctODQgNTE0LjQzMi04NCA2MDMuMTM2LTg0IDY4Ny42MTYtNjYuMTIyNyA3NjQuNTg2Ny0zMy43ODEzTDU3NiAxMjAuMTZDNTU3LjAxMzMgMTEyLjgyMTMgNTM1LjA4MjcgMTA4LjQyNjcgNTEyLjE3MDcgMTA4WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTE2MCIgdW5pY29kZT0iJiN4RTE2MDsiIGQ9Ik04NzguMDggMzEuODRDOTYzLjc1NDcgOTIuMDg1MyAxMDIwLjA3NDcgMTg5LjA2NjcgMTAyNCAyOTkuNDAyNyAxMDI0IDUxMS44NCA3OTQuMjQgNjg0IDUxMiA2ODQgNTEwLjM3ODcgNjg0IDUwOC40NTg3IDY4NC4wNDI3IDUwNi40OTYgNjg0LjA0MjcgMzk0LjQ5NiA2ODQuMDQyNyAyODkuNDA4IDY1NC42MDI3IDE5OC40ODUzIDYwMy4wNjEzTDExNi40OCA2NzYuMzYyN0MxMTAuOTMzMyA2ODEuMTQxMyAxMDMuNjM3MyA2ODQuMDQyNyA5NS43MDEzIDY4NC4wNDI3IDc4LjAzNzMgNjg0LjA0MjcgNjMuNzAxMyA2NjkuNzA2NyA2My43MDEzIDY1Mi4wNDI3IDYzLjcwMTMgNjQyLjMxNDcgNjguMDEwNyA2MzMuNjEwNyA3NC44OCA2MjcuNzY1M0wxNDUuMzIyNyA1NjguMjAyN0M1OS45MDQgNTA3LjgyOTMgMy44NCA0MTAuODQ4IDAuMDQyNyAzMDAuNTk3MyAwLjA0MjcgODguMjAyNyAyMjkuODAyNy04My45NTczIDUxMi4wNDI3LTgzLjk1NzMgNTEzLjY2NC04My45NTczIDUxNS41ODQtODQgNTE3LjU0NjctODQgNjI5LjU0NjctODQgNzM0LjYzNDctNTQuNTYgODI1LjU1NzMtMy4wMTg3TDkwNy41NjI3LTc2LjMyQzkxMy4xMDkzLTgxLjA5ODcgOTIwLjQwNTMtODQgOTI4LjM4NC04NCA5NDYuMDQ4LTg0IDk2MC4zODQtNjkuNjY0IDk2MC4zODQtNTIgOTYwLjM4NC00Mi4yNzIgOTU2LjA3NDctMzMuNTY4IDk0OS4yMDUzLTI3LjcyMjdaTTUxMiA2MjBDNzU5LjA0IDYyMCA5NjAgNDc2LjY0IDk2MCAzMDAgOTU1LjQ3NzMgMjA0Ljk4MTMgOTA0Ljc0NjcgMTIyLjcyIDgyOS45MDkzIDc0Ljc2MjdMNjc2LjQ4IDIwMi4wOEM2OTMuNTg5MyAyMzAuMDI2NyA3MDMuNzg2NyAyNjMuNzc2IDcwNCAyOTkuOTU3MyA3MDQgNDA2LjA2OTMgNjE4LjAyNjcgNDkyIDUxMiA0OTIgNDY0LjkzODcgNDkxLjUzMDcgNDIxLjk3MzMgNDc0LjE2NTMgMzg4Ljg2NCA0NDUuNzA2N0wyNTYgNTYxLjEyQzMzMC4wMjY3IDU5OC4yNCA0MTcuMzIyNyA2MjAgNTA5LjY5NiA2MjAgNTEwLjUwNjcgNjIwIDUxMS4zMTczIDYyMCA1MTIuMTI4IDYyMFpNMzk2LjggMzU1LjA0TDU4NS42IDE5NS42OEM1NjUuMjkwNyAxODEuNDcyIDU0MC4wMzIgMTcyLjk4MTMgNTEyLjgxMDcgMTcyLjk4MTMgNDQyLjExMiAxNzIuOTgxMyAzODQuODEwNyAyMzAuMjgyNyAzODQuODEwNyAzMDAuOTgxMyAzODQuODEwNyAzMjAuNjA4IDM4OS4yNDggMzM5LjIxMDcgMzk3LjA5ODcgMzU1LjgwOFpNNDM3Ljc2IDQwNC4zMkM0NTguMjgyNyA0MTguOTU0NyA0ODMuODgyNyA0MjcuNzAxMyA1MTEuNDg4IDQyNy43MDEzIDU4Mi4xODY3IDQyNy43MDEzIDYzOS40ODggMzcwLjQgNjM5LjQ4OCAyOTkuNzAxMyA2MzkuNDg4IDI3OS44MTg3IDYzNC45NjUzIDI2MS4wMDI3IDYyNi44NTg3IDI0NC4xOTJaTTUxMi0yMEMyNjQuOTYtMjAgNjQgMTIzLjM2IDY0IDMwMCA2OC41MjI3IDM5NS4wMTg3IDExOS4yNTMzIDQ3Ny4yOCAxOTQuMDkwNyA1MjUuMjM3M0wzNDcuNTIgMzk3LjkyQzMzMC40MTA3IDM2OS45NzMzIDMyMC4yMTMzIDMzNi4yMjQgMzIwIDMwMC4wNDI3IDMyMCAxOTMuOTMwNyA0MDUuOTczMyAxMDggNTEyIDEwOCA1NTkuMDYxMyAxMDguNDY5MyA2MDIuMDI2NyAxMjUuODM0NyA2MzUuMTM2IDE1NC4yOTMzTDc2OCAzOC44OEM2OTMuOTczMyAxLjc2IDYwNi42NzczLTIwIDUxNC4zMDQtMjAgNTEzLjQ5MzMtMjAgNTEyLjY4MjctMjAgNTExLjg3Mi0yMFoiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxNjEiIHVuaWNvZGU9IiYjeEUxNjE7IiBkPSJNNTEyLTg0QzIyOS43Ni04NCAwIDg4LjE2IDAgMzAwUzIyOS43NiA2ODQgNTEyIDY4NCAxMDI0IDUxMS44NCAxMDI0IDMwMCA3OTQuMjQtODQgNTEyLTg0Wk01MTIgNjIwQzI2NC45NiA2MjAgNjQgNDc2LjY0IDY0IDMwMFMyNjQuOTYtMjAgNTEyLTIwIDk2MCAxMjMuMzYgOTYwIDMwMCA3NTkuMDQgNjIwIDUxMiA2MjBaTTUxMiAxMDhDNDA1Ljk3MzMgMTA4IDMyMCAxOTMuOTczMyAzMjAgMzAwUzQwNS45NzMzIDQ5MiA1MTIgNDkyQzYxOC4wMjY3IDQ5MiA3MDQgNDA2LjAyNjcgNzA0IDMwMFM2MTguMDI2NyAxMDggNTEyIDEwOFpNNTEyIDQyOEM0NDEuMzAxMyA0MjggMzg0IDM3MC42OTg3IDM4NCAzMDBTNDQxLjMwMTMgMTcyIDUxMiAxNzJDNTgyLjY5ODcgMTcyIDY0MCAyMjkuMzAxMyA2NDAgMzAwUzU4Mi42OTg3IDQyOCA1MTIgNDI4WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTE2MiIgdW5pY29kZT0iJiN4RTE2MjsiIGQ9Ik05MTEuMzYgNDk2LjczNkM5MDkuMzU0NyA1MDEuMzAxMyA5MDYuNjY2NyA1MDUuMTg0IDkwMy4zMzg3IDUwOC40MjY3TDYxMC43NzMzIDgwMC45OTJDNjA0LjIwMjcgODA3LjU2MjcgNTk1LjIgODExLjc0NCA1ODUuMjE2IDgxMS45NTczTDIxMi44NjQgODExLjk1NzNDMjEyLjQzNzMgODExLjk1NzMgMjExLjkyNTMgODExLjk1NzMgMjExLjM3MDcgODExLjk1NzMgMTU1LjczMzMgODExLjk1NzMgMTEwLjU0OTMgNzY3LjI0MjcgMTA5LjY5NiA3MTEuODE4N0wxMDkuNjk2LTExMS44NjEzQzExMC41MDY3LTE2Ny4zNzA3IDE1NS43MzMzLTIxMi4wODUzIDIxMS4zNzA3LTIxMi4wODUzIDIxMS44ODI3LTIxMi4wODUzIDIxMi4zOTQ3LTIxMi4wODUzIDIxMi45MDY3LTIxMi4wODUzTDgxMS4xMzYtMjEyLjA4NTNDODExLjU2MjctMjEyLjA4NTMgODEyLjA3NDctMjEyLjA4NTMgODEyLjYyOTMtMjEyLjA4NTMgODY4LjI2NjctMjEyLjA4NTMgOTEzLjQ1MDctMTY3LjM3MDcgOTE0LjMwNC0xMTEuOTQ2N0w5MTQuMzA0IDQ4Mi43ODRDOTE0LjI2MTMgNDg3LjgxODcgOTEzLjE1MiA0OTIuNTk3MyA5MTEuMjc0NyA0OTYuOTA2N1pNNjU4LjMwNCAxNTMuNjk2SDU0OC42MDhWNDRDNTQ4LjYwOCAyMy44MTg3IDUzMi4yMjQgNy40MzQ3IDUxMi4wNDI3IDcuNDM0N1M0NzUuNDc3MyAyMy44MTg3IDQ3NS40NzczIDQ0VjE1My42OTZIMzY1Ljc4MTNDMzQ1LjYgMTUzLjY5NiAzMjkuMjE2IDE3MC4wOCAzMjkuMjE2IDE5MC4yNjEzUzM0NS42IDIyNi44MjY3IDM2NS43ODEzIDIyNi44MjY3SDQ3NS40NzczVjMzNi41MjI3QzQ3NS40NzczIDM1Ni43MDQgNDkxLjg2MTMgMzczLjA4OCA1MTIuMDQyNyAzNzMuMDg4UzU0OC42MDggMzU2LjcwNCA1NDguNjA4IDMzNi41MjI3VjIyNi44MjY3SDY1OC4zMDRDNjc4LjQ4NTMgMjI2LjgyNjcgNjk0Ljg2OTMgMjEwLjQ0MjcgNjk0Ljg2OTMgMTkwLjI2MTNTNjc4LjQ4NTMgMTUzLjY5NiA2NTguMzA0IDE1My42OTZaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMTYzIiB1bmljb2RlPSImI3hFMTYzOyIgZD0iTTg2NCA0NjYuNEM4NjQgNDY2LjQgODY0IDQ2Ni40IDg2NCA0NjYuNCA4NjQgNDcyLjggODU3LjYgNDc5LjIgODU3LjYgNDg1LjZMNjAxLjYgNzQxLjZDNTk1LjIgNzQxLjYgNTg4LjggNzQ4IDU4Mi40IDc0OCA1ODIuNCA3NDggNTgyLjQgNzQ4IDU3NiA3NDggNTc2IDc0OCA1NzYgNzQ4IDU3NiA3NDhIMjQ5LjZDMTk4LjQgNzQ4IDE2MCA3MDkuNiAxNjAgNjU4LjRWLTY0LjhDMTYwLTExNiAxOTguNC0xNTQuNCAyNDkuNi0xNTQuNEg3NzQuNEM4MjUuNi0xNTQuNCA4NjQtMTE2IDg2NC02NC44VjQ2Ni40Qzg2NCA0NjAgODY0IDQ2MCA4NjQgNDY2LjRaTTYwOCA2MzkuMkw3NTUuMiA0OTJINjA4VjYzOS4yWk03NzQuNC04NEgyNDkuNkMyMzYuOC04NCAyMjQtNzEuMiAyMjQtNTguNFY2NTguNEMyMjQgNjcxLjIgMjM2LjggNjg0IDI0OS42IDY4NEg1NDRWNDYwQzU0NCA0NDAuOCA1NTYuOCA0MjggNTc2IDQyOEg4MDBWLTU4LjRDODAwLTcxLjIgNzg3LjItODQgNzc0LjQtODRaTTY0MCAyMzZINTQ0VjMzMkM1NDQgMzUxLjIgNTMxLjIgMzY0IDUxMiAzNjRTNDgwIDM1MS4yIDQ4MCAzMzJWMjM2SDM4NEMzNjQuOCAyMzYgMzUyIDIyMy4yIDM1MiAyMDRTMzY0LjggMTcyIDM4NCAxNzJINDgwVjc2QzQ4MCA1Ni44IDQ5Mi44IDQ0IDUxMiA0NFM1NDQgNTYuOCA1NDQgNzZWMTcySDY0MEM2NTkuMiAxNzIgNjcyIDE4NC44IDY3MiAyMDRTNjU5LjIgMjM2IDY0MCAyMzZaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMTY0IiB1bmljb2RlPSImI3hFMTY0OyIgZD0iTTkxMS4zNiA0OTYuNzM2QzkwOS4zNTQ3IDUwMS4zMDEzIDkwNi42NjY3IDUwNS4xODQgOTAzLjMzODcgNTA4LjQyNjdMNjEwLjc3MzMgODAwLjk5MkM2MDQuMjAyNyA4MDcuNTYyNyA1OTUuMiA4MTEuNzQ0IDU4NS4yMTYgODExLjk1NzNMMjEyLjg2NCA4MTEuOTU3M0MyMTIuNDM3MyA4MTEuOTU3MyAyMTEuOTI1MyA4MTEuOTU3MyAyMTEuMzcwNyA4MTEuOTU3MyAxNTUuNzMzMyA4MTEuOTU3MyAxMTAuNTQ5MyA3NjcuMjQyNyAxMDkuNjk2IDcxMS44MTg3TDEwOS42OTYtMTExLjg2MTNDMTEwLjUwNjctMTY3LjM3MDcgMTU1LjczMzMtMjEyLjA4NTMgMjExLjM3MDctMjEyLjA4NTMgMjExLjg4MjctMjEyLjA4NTMgMjEyLjM5NDctMjEyLjA4NTMgMjEyLjkwNjctMjEyLjA4NTNMODExLjEzNi0yMTIuMDg1M0M4MTEuNTYyNy0yMTIuMDg1MyA4MTIuMDc0Ny0yMTIuMDg1MyA4MTIuNjI5My0yMTIuMDg1MyA4NjguMjY2Ny0yMTIuMDg1MyA5MTMuNDUwNy0xNjcuMzcwNyA5MTQuMzA0LTExMS45NDY3TDkxNC4zMDQgNDgyLjc4NEM5MTQuMjYxMyA0ODcuODE4NyA5MTMuMTUyIDQ5Mi41OTczIDkxMS4yNzQ3IDQ5Ni45MDY3WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTE2NSIgdW5pY29kZT0iJiN4RTE2NTsiIGQ9Ik04NjQgNDY2LjRDODY0IDQ2Ni40IDg2NCA0NjYuNCA4NjQgNDY2LjQgODY0IDQ3Mi44IDg1Ny42IDQ3OS4yIDg1Ny42IDQ4NS42TDYwMS42IDc0MS42QzU5NS4yIDc0MS42IDU4OC44IDc0OCA1ODIuNCA3NDggNTgyLjQgNzQ4IDU4Mi40IDc0OCA1NzYgNzQ4IDU3NiA3NDggNTc2IDc0OCA1NzYgNzQ4SDI0OS42QzE5OC40IDc0OCAxNjAgNzA5LjYgMTYwIDY1OC40Vi02NC44QzE2MC0xMTYgMTk4LjQtMTU0LjQgMjQ5LjYtMTU0LjRINzc0LjRDODI1LjYtMTU0LjQgODY0LTExNiA4NjQtNjQuOFY0NjYuNEM4NjQgNDYwIDg2NCA0NjAgODY0IDQ2Ni40Wk02MDggNjM5LjJMNzU1LjIgNDkySDYwOFY2MzkuMlpNNzc0LjQtODRIMjQ5LjZDMjM2LjgtODQgMjI0LTcxLjIgMjI0LTU4LjRWNjU4LjRDMjI0IDY3MS4yIDIzNi44IDY4NCAyNDkuNiA2ODRINTQ0VjQ2MEM1NDQgNDQwLjggNTU2LjggNDI4IDU3NiA0MjhIODAwVi01OC40QzgwMC03MS4yIDc4Ny4yLTg0IDc3NC40LTg0WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTE2NiIgdW5pY29kZT0iJiN4RTE2NjsiIGQ9Ik0yMDIuMjQgMzkwLjg4QzIwNC4wMzIgNDQ3LjExNDcgMjUwLjAyNjcgNDkyIDMwNi41MTczIDQ5MiAzMDYuOTg2NyA0OTIgMzA3LjQ1NiA0OTIgMzA3LjkyNTMgNDkyTDg3Ni4xNiA0OTJDODc2LjMzMDcgNDkyIDg3Ni41NDQgNDkyIDg3Ni43NTczIDQ5MiA4ODMuODQgNDkyIDg4OS41NTczIDQ5Ny43MTczIDg4OS41NTczIDUwNC44IDg4OS41NTczIDUwNi4xNjUzIDg4OS4zNDQgNTA3LjQ4OCA4ODguOTE3MyA1MDguNzI1MyA4NjcuNzEyIDU3My43NDkzIDgwNy41MDkzIDYyMCA3MzYuNTEyIDYyMCA3MzYuMzQxMyA2MjAgNzM2LjEyOCA2MjAgNzM1Ljk1NzMgNjIwSDQ0OFY2NTJDNDQ4IDcwNS4wMzQ3IDQwNS4wMzQ3IDc0OCAzNTIgNzQ4SDk2QzQyLjk2NTMgNzQ4IDAgNzA1LjAzNDcgMCA2NTJWMTJDMCAxMS4wMTg3LTAuMDQyNyA5LjkwOTMtMC4wNDI3IDguNzU3My0wLjA0MjctNjguMjk4NyA1NC40LTEzMi42NCAxMjYuOTMzMy0xNDcuODI5MyAxMjcuODI5My0xNDUuOTA5MyAxMjcuNzQ0LTE0My40MzQ3IDEyNy43NDQtMTQwLjk2UzEyNy44MjkzLTEzNi4wMTA3IDEyOC0xMzMuNTc4N1pNOTYwIDQyOEgzMDcuODRDMjg0Ljg4NTMgNDI4IDI2Ni4yNCA0MDkuMzU0NyAyNjYuMjQgMzg2LjRMMTkyLTEzNS4yQzE5MS41NzMzLTEzNy4xMiAxOTEuMzYtMTM5LjMzODcgMTkxLjM2LTE0MS42UzE5MS42MTYtMTQ2LjA4IDE5Mi4wNDI3LTE0OC4yMTMzTDg5Ni0xNDhDOTMxLjMyOC0xNDggOTYwLTExOS4zMjggOTYwLTg0TDEwMjQgMzY0QzEwMjQgMzk5LjMyOCA5OTUuMzI4IDQyOCA5NjAgNDI4WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTE2NyIgdW5pY29kZT0iJiN4RTE2NzsiIGQ9Ik05MjggNDkySDg5Mi44Qzg3Ny4zOTczIDU2NS41NTczIDgxMy4wNTYgNjIwIDczNi4wNDI3IDYyMCA3MzYuMDQyNyA2MjAgNzM2IDYyMCA3MzYgNjIwSDQ0OFY2NTJDNDQ4IDcwNS4wMzQ3IDQwNS4wMzQ3IDc0OCAzNTIgNzQ4SDk2QzQyLjk2NTMgNzQ4IDAgNzA1LjAzNDcgMCA2NTJWMTJDMC03Ni4zNjI3IDcxLjYzNzMtMTQ4IDE2MC0xNDhIODY0Qzg2NC4zODQtMTQ4IDg2NC44NTMzLTE0OCA4NjUuMzIyNy0xNDggOTE2LjUyMjctMTQ4IDk1OC4yMDgtMTA3LjM4MTMgOTYwLTU2LjY1MDdMMTAyNCAzOTZDMTAyNCA0NDkuMDM0NyA5ODEuMDM0NyA0OTIgOTI4IDQ5MlpNNjQgMTJWNjUyQzY0IDY2OS42NjQgNzguMzM2IDY4NCA5NiA2ODRIMzUyQzM2OS42NjQgNjg0IDM4NCA2NjkuNjY0IDM4NCA2NTJWNTg4QzM4NCA1NzAuMzM2IDM5OC4zMzYgNTU2IDQxNiA1NTZINzM2Qzc3Ny40MjkzIDU1NS44NzIgODEyLjcxNDcgNTI5LjUwNCA4MjYuMDI2NyA0OTIuNjgyN0wyODggNDkyQzI4Ny42MTYgNDkyIDI4Ny4xNDY3IDQ5MiAyODYuNjc3MyA0OTIgMjM1LjQ3NzMgNDkyIDE5My43OTIgNDUxLjM4MTMgMTkyIDQwMC42NTA3TDEyOC01MkMxMjguMTI4LTYxLjg1NiAxMjkuNzQ5My03MS4zMjggMTMyLjY1MDctODAuMjAyNyA5Mi42NzItNjcuMzYgNjQuMTcwNy0zMS4wNTA3IDY0IDExLjk1NzNaTTg5Ni01MkM4OTYtNjkuNjY0IDg4MS42NjQtODQgODY0LTg0SDIyNEMyMjMuOTE0Ny04NCAyMjMuNzg2Ny04NCAyMjMuNzAxMy04NCAyMDcuNjE2LTg0IDE5NC4zMDQtNzIuMTM4NyAxOTIuMDQyNy01Ni42NTA3TDI1Ni4wNDI3IDM5NkMyNTYuMDQyNyA0MTMuNjY0IDI3MC4zNzg3IDQyOCAyODguMDQyNyA0MjhIOTI4LjA0MjdDOTI4LjEyOCA0MjggOTI4LjI1NiA0MjggOTI4LjM0MTMgNDI4IDk0NC40MjY3IDQyOCA5NTcuNzM4NyA0MTYuMTM4NyA5NjAgNDAwLjY1MDdaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMTY4IiB1bmljb2RlPSImI3hFMTY4OyIgZD0iTTg2NCA2MjBINDQ4VjY1MkM0NDggNzA1LjAzNDcgNDA1LjAzNDcgNzQ4IDM1MiA3NDhIOTZDNDIuOTY1MyA3NDggMCA3MDUuMDM0NyAwIDY1MlYxMkMwLTc2LjM2MjcgNzEuNjM3My0xNDggMTYwLTE0OEg4NjRDOTUyLjM2MjctMTQ4IDEwMjQtNzYuMzYyNyAxMDI0IDEyVjQ2MEMxMDI0IDU0OC4zNjI3IDk1Mi4zNjI3IDYyMCA4NjQgNjIwWk02NDAgMTcySDU0NFY3NkM1NDQgNTguMzM2IDUyOS42NjQgNDQgNTEyIDQ0UzQ4MCA1OC4zMzYgNDgwIDc2VjE3MkgzODRDMzY2LjMzNiAxNzIgMzUyIDE4Ni4zMzYgMzUyIDIwNFMzNjYuMzM2IDIzNiAzODQgMjM2SDQ4MFYzMzJDNDgwIDM0OS42NjQgNDk0LjMzNiAzNjQgNTEyIDM2NFM1NDQgMzQ5LjY2NCA1NDQgMzMyVjIzNkg2NDBDNjU3LjY2NCAyMzYgNjcyIDIyMS42NjQgNjcyIDIwNFM2NTcuNjY0IDE3MiA2NDAgMTcyWiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTE2OSIgdW5pY29kZT0iJiN4RTE2OTsiIGQ9Ik04NjQgNjIwSDQ0OFY2NTJDNDQ4IDcwMy4yIDQwMy4yIDc0OCAzNTIgNzQ4SDk2QzQ0LjggNzQ4IDAgNzAzLjIgMCA2NTJWMTJDMC03Ny42IDcwLjQtMTQ4IDE2MC0xNDhIODY0Qzk1My42LTE0OCAxMDI0LTc3LjYgMTAyNCAxMlY0NjBDMTAyNCA1NDkuNiA5NTMuNiA2MjAgODY0IDYyMFpNOTYwIDEyQzk2MC0zOS4yIDkxNS4yLTg0IDg2NC04NEgxNjBDMTA4LjgtODQgNjQtMzkuMiA2NCAxMlY2NTJDNjQgNjcxLjIgNzYuOCA2ODQgOTYgNjg0SDM1MkMzNzEuMiA2ODQgMzg0IDY3MS4yIDM4NCA2NTJWNTg4QzM4NCA1NjguOCAzOTYuOCA1NTYgNDE2IDU1Nkg4NjRDOTE1LjIgNTU2IDk2MCA1MTEuMiA5NjAgNDYwVjEyWk02NDAgMjM2SDU0NFYzMzJDNTQ0IDM1MS4yIDUzMS4yIDM2NCA1MTIgMzY0UzQ4MCAzNTEuMiA0ODAgMzMyVjIzNkgzODRDMzY0LjggMjM2IDM1MiAyMjMuMiAzNTIgMjA0UzM2NC44IDE3MiAzODQgMTcySDQ4MFY3NkM0ODAgNTYuOCA0OTIuOCA0NCA1MTIgNDRTNTQ0IDU2LjggNTQ0IDc2VjE3Mkg2NDBDNjU5LjIgMTcyIDY3MiAxODQuOCA2NzIgMjA0UzY1OS4yIDIzNiA2NDAgMjM2WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTE2QSIgdW5pY29kZT0iJiN4RTE2QTsiIGQ9Ik04NjQgNjIwSDQ0OFY2NTJDNDQ4IDcwNS4wMzQ3IDQwNS4wMzQ3IDc0OCAzNTIgNzQ4SDk2QzQyLjk2NTMgNzQ4IDAgNzA1LjAzNDcgMCA2NTJWMTJDMC03Ni4zNjI3IDcxLjYzNzMtMTQ4IDE2MC0xNDhIODY0Qzk1Mi4zNjI3LTE0OCAxMDI0LTc2LjM2MjcgMTAyNCAxMlY0NjBDMTAyNCA1NDguMzYyNyA5NTIuMzYyNyA2MjAgODY0IDYyMFoiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxNkIiIHVuaWNvZGU9IiYjeEUxNkI7IiBkPSJNODY0LTE0OEgxNjBDNzEuNjM3My0xNDggMC03Ni4zNjI3IDAgMTJWNjUyQzAgNzA1LjAzNDcgNDIuOTY1MyA3NDggOTYgNzQ4SDM1MkM0MDUuMDM0NyA3NDggNDQ4IDcwNS4wMzQ3IDQ0OCA2NTJWNjIwSDg2NEM5NTIuMzYyNyA2MjAgMTAyNCA1NDguMzYyNyAxMDI0IDQ2MFYxMkMxMDI0LTc2LjM2MjcgOTUyLjM2MjctMTQ4IDg2NC0xNDhaTTk2IDY4NEM3OC4zMzYgNjg0IDY0IDY2OS42NjQgNjQgNjUyVjEyQzY0LTQxLjAzNDcgMTA2Ljk2NTMtODQgMTYwLTg0SDg2NEM5MTcuMDM0Ny04NCA5NjAtNDEuMDM0NyA5NjAgMTJWNDYwQzk2MCA1MTMuMDM0NyA5MTcuMDM0NyA1NTYgODY0IDU1Nkg0MTZDMzk4LjMzNiA1NTYgMzg0IDU3MC4zMzYgMzg0IDU4OFY2NTJDMzg0IDY2OS42NjQgMzY5LjY2NCA2ODQgMzUyIDY4NFoiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxNkMiIHVuaWNvZGU9IiYjeEUxNkM7IiBkPSJNMzUyIDgxMkgzMkMxNC4zMzYgODEyIDAgNzk3LjY2NCAwIDc4MFY0NjBDMCA0NDIuMzM2IDE0LjMzNiA0MjggMzIgNDI4UzY0IDQ0Mi4zMzYgNjQgNDYwVjc0OEgzNTJDMzY5LjY2NCA3NDggMzg0IDc2Mi4zMzYgMzg0IDc4MFMzNjkuNjY0IDgxMiAzNTIgODEyWk05OTIgODEySDY3MkM2NTQuMzM2IDgxMiA2NDAgNzk3LjY2NCA2NDAgNzgwUzY1NC4zMzYgNzQ4IDY3MiA3NDhIOTYwVjQ2MEM5NjAgNDQyLjMzNiA5NzQuMzM2IDQyOCA5OTIgNDI4UzEwMjQgNDQyLjMzNiAxMDI0IDQ2MFY3ODBDMTAyNCA3OTcuNjY0IDEwMDkuNjY0IDgxMiA5OTIgODEyWk0zNTItMTQ4SDY0VjE0MEM2NCAxNTcuNjY0IDQ5LjY2NCAxNzIgMzIgMTcyUzAgMTU3LjY2NCAwIDE0MFYtMTgwQzAtMTk3LjY2NCAxNC4zMzYtMjEyIDMyLTIxMkgzNTJDMzY5LjY2NC0yMTIgMzg0LTE5Ny42NjQgMzg0LTE4MFMzNjkuNjY0LTE0OCAzNTItMTQ4Wk05OTIgMTcyQzk3NC4zMzYgMTcyIDk2MCAxNTcuNjY0IDk2MCAxNDBWLTE0OEg2NzJDNjU0LjMzNi0xNDggNjQwLTE2Mi4zMzYgNjQwLTE4MFM2NTQuMzM2LTIxMiA2NzItMjEySDk5MkMxMDA5LjY2NC0yMTIgMTAyNC0xOTcuNjY0IDEwMjQtMTgwVjE0MEMxMDI0IDE1Ny42NjQgMTAwOS42NjQgMTcyIDk5MiAxNzJaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMTZEIiB1bmljb2RlPSImI3hFMTZEOyIgZD0iTTc0MS4xMiA3NDhDNjgxLjQyOTMgNzQ2LjUwNjcgNjI2LjY4OCA3MjYuMzI1MyA1ODIuMzE0NyA2OTMuMDg4IDU1NS4xMzYgNjczLjIwNTMgNTMxLjU4NCA2NDguOCA1MTIuNjQgNjIxLjAyNCA0OTIuNDE2IDY0OC44IDQ2OC44NjQgNjczLjIwNTMgNDQxLjc3MDcgNjkzLjA0NTMgMzk3LjI2OTMgNzI2LjMyNTMgMzQyLjU3MDcgNzQ2LjUwNjcgMjgzLjIyMTMgNzQ4IDI4Mi4xMTIgNzQ4IDI4MS4yMTYgNzQ4IDI4MC4yNzczIDc0OCAxMjYuODA1MyA3NDggMi4xMzMzIDYyNC42NTA3IDAgNDcxLjY5MDcgMi42MDI3IDM3OS4zNiAzMi4xNzA3IDI5NC41ODEzIDgwLjk4MTMgMjI0LjIyNCAxMjkuNTc4NyAxNTIuNjI5MyAxODYuMTk3MyA4OS41MjUzIDI1MC4xOTczIDM0LjgyNjcgMzI0LjM5NDctMzEuMzkyIDQwNS40NjEzLTkwLjQ0MjcgNDkyLjExNzMtMTQxLjAwMjcgNTAyLjkxMi0xNDYuODA1MyA1MDcuMzA2Ny0xNDggNTEyLTE0OEg1MTJDNTE2LjY5MzMtMTQ4IDUyMS4wODgtMTQ2LjgwNTMgNTI0LjkyOC0xNDQuNzE0NyA2MTguNTM4Ny05MC45NTQ3IDY5OS42MDUzLTMyLjUwMTMgNzc0LjA1ODcgMzMuMjQ4IDgzNy43NiA4Ny42NDggODk0LjM3ODcgMTUwLjc1MiA5NDEuODY2NyAyMjAuNTU0NyA5OTIuMTcwNyAyOTMuMjE2IDEwMjEuNzM4NyAzNzguNjc3MyAxMDIzLjk1NzMgNDcwLjk2NTMgMTAyMS44MjQgNjI0LjY5MzMgODk3LjE1MiA3NDggNzQzLjY4IDc0OCA3NDIuNzg0IDc0OCA3NDEuODQ1MyA3NDggNzQwLjk0OTMgNzQ4WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTE2RSIgdW5pY29kZT0iJiN4RTE2RTsiIGQ9Ik01MTItMTQ4QzUwNy41Mi0xNDggNTAzLjA0LTE0Ni43MiA0OTkuMi0xNDQuOCA0OTQuMDgtMTQyLjI0IDM3My43Ni03Ni4zMiAyNTEuNTIgMzEuODQgMTc5LjIgOTUuODQgMTIxLjYgMTYxLjEyIDgwIDIyNS43NiAyNi44OCAzMDguMzIgMCAzOTAuODggMCA0NzEuNTIgMCA2MjMuODQgMTI2LjcyIDc0OCAyODIuODggNzQ4IDMzNiA3NDggMzkxLjY4IDcyOC44IDQ0MC45NiA2OTMuNiA0NjkuNzYgNjczLjEyIDQ5NC4wOCA2NDguMTYgNTEyIDYyMS45MiA1MjkuOTIgNjQ4LjE2IDU1NC4yNCA2NzMuMTIgNTgzLjA0IDY5My42IDYzMi4zMiA3MjguOCA2ODggNzQ4IDc0MS4xMiA3NDggODk3LjI4IDc0OCAxMDI0IDYyMy44NCAxMDI0IDQ3MS41MiAxMDI0IDM5MS41MiA5OTcuMTIgMzA4Ljk2IDk0NCAyMjUuNzYgOTAyLjQgMTYxLjEyIDg0NC44IDk1Ljg0IDc3Mi40OCAzMS44NCA2NTAuMjQtNzUuNjggNTI5LjkyLTE0MS42IDUyNC44LTE0NC44IDUyMC45Ni0xNDYuNzIgNTE2LjQ4LTE0OCA1MTItMTQ4Vi0xNDhaTTI4OCA2ODRDMTY0LjQ4IDY4NCA2NCA1ODYuMDggNjQgNDY1LjEyIDY0IDMwOC45NiAxODguMTYgMTY2LjI0IDI5MS44NCA3NC43MiAzODQuNjQtNy4yIDQ3OC43Mi02NC44IDUxMi04NCA1NDUuMjgtNjQuOCA2MzkuMzYtNy4yIDczMi4xNiA3NC43MiA4MzUuODQgMTY2Ljg4IDk2MCAzMDguOTYgOTYwIDQ2NS4xMiA5NjAgNTg2LjA4IDg1OS41MiA2ODQgNzM2IDY4NCA2NDYuNCA2ODQgNTU5LjM2IDYxMS42OCA1MzYuOTYgNTQ3LjA0IDUzMy4xMiA1MzYuOCA1MjMuNTIgNTI5Ljc2IDUxMiA1MjkuNzZTNDkwLjg4IDUzNi44IDQ4Ny4wNCA1NDcuNjhDNDY0LjY0IDYxMS42OCAzNzcuNiA2ODQgMjg4IDY4NFoiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxNkYiIHVuaWNvZGU9IiYjeEUxNkY7IiBkPSJNODk2IDM2OC40OEM5NDguNDggNDA3LjUyIDk5MiA0NTQuMjQgMTAyMC4xNiA1MDggMTAyOC40OCA1MjMuMzYgMTAyMi4wOCA1NDMuMiAxMDA2LjcyIDU1MC44OCA5OTEuMzYgNTU5LjIgOTcxLjUyIDU1My40NCA5NjMuODQgNTM3LjQ0IDg5My40NCA0MDQuMzIgNzEyLjMyIDMxNC43MiA1MTIgMzE0LjcyUzEzMC41NiA0MDQuMzIgNjAuMTYgNTM3LjQ0QzUxLjg0IDU1My40NCAzMi42NCA1NTkuMiAxNy4yOCA1NTAuODggMS4yOCA1NDMuMi00LjQ4IDUyMy4zNiAzLjg0IDUwOCAzMiA0NTQuMjQgNzUuNTIgNDA2Ljg4IDEyOCAzNjguNDhMNy4wNCAyMTcuNDRDLTMuODQgMjAzLjM2LTEuOTIgMTgyLjg4IDEyLjE2IDE3MiAxNy45MiAxNjcuNTIgMjQuOTYgMTY0Ljk2IDMyIDE2NC45NiA0MS42IDE2NC45NiA1MC41NiAxNjguOCA1Ni45NiAxNzcuMTJMMTgyLjQgMzMzLjI4QzIzOC4wOCAzMDEuOTIgMzAyLjA4IDI3OC44OCAzNzEuMiAyNjUuNDRMMjkxLjIgOTAuNzJDMjgzLjUyIDc0LjcyIDI5MS4yIDU1LjUyIDMwNy4yIDQ4LjQ4IDMxMS42OCA0Ni41NiAzMTYuMTYgNDUuMjggMzIwLjY0IDQ1LjI4IDMzMi44IDQ1LjI4IDM0NC4zMiA1Mi4zMiAzNTAuMDggNjMuODRMNDM3LjEyIDI1NS4yQzQ2MS40NCAyNTIuNjQgNDg2LjQgMjUwLjcyIDUxMiAyNTAuNzIgNTMyLjQ4IDI1MC43MiA1NTIuMzIgMjUyLjY0IDU3Mi4xNiAyNTMuOTJMNjU5LjIgNjMuODRDNjY0LjMyIDUyLjMyIDY3NS44NCA0NS4yOCA2ODggNDUuMjggNjkyLjQ4IDQ1LjI4IDY5Ni45NiA0NS45MiA3MDEuNDQgNDguNDggNzE3LjQ0IDU1LjUyIDcyNC40OCA3NC43MiA3MTcuNDQgOTAuNzJMNjM4LjcyIDI2Mi44OEM3MTMuNiAyNzUuNjggNzgyLjA4IDMwMCA4NDEuNiAzMzMuOTJMOTY2LjQgMTc3Ljc2Qzk3Mi44IDE3MC4wOCA5ODEuNzYgMTY1LjYgOTkxLjM2IDE2NS42IDk5OC40IDE2NS42IDEwMDUuNDQgMTY4LjE2IDEwMTEuMiAxNzIuNjQgMTAyNS4yOCAxODMuNTIgMTAyNy4yIDIwNCAxMDE2LjMyIDIxNy40NEw4OTYgMzY4LjQ4WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTE3MCIgdW5pY29kZT0iJiN4RTE3MDsiIGQ9Ik05MzYgMzA0LjhMNTYwIDY5NS4yQzUzNC40IDcyMi40IDQ5MS4yIDcyMi40IDQ2NS42IDY5Ni44TDQ2NCA2OTUuMiA4OCAzMDQuOEM2Ny4yIDI4NCA2Ny4yIDI1MC40IDg5LjYgMjI5LjYgOTkuMiAyMjAgMTEyIDIxNS4yIDEyNC44IDIxNS4ySDIwMFYtNjhDMjAwLTEwMy4yIDIyNy4yLTEzMC40IDI2Mi40LTEzMC40TDI2Mi40LTEzMC40SDc2NC44QzgwMC0xMzAuNCA4MjguOC0xMDMuMiA4MjguOC02OFYyMTMuNkg5MDRDOTMyLjggMjE1LjIgOTU2LjggMjQwLjggOTU1LjIgMjY5LjYgOTUzLjYgMjgyLjQgOTQ1LjYgMjk1LjIgOTM2IDMwNC44Wk02MDYuNC02OS42SDQxNy42VjEyMi40QzQxNy42IDE1NC40IDQ0NC44IDE4MS42IDQ3Ni44IDE4MS42TDQ3Ni44IDE4MS42SDU0Ny4yQzU3OS4yIDE4MS42IDYwNi40IDE1NC40IDYwNi40IDEyMi40TDYwNi40IDEyMi40Vi02OS42WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTE3MSIgdW5pY29kZT0iJiN4RTE3MTsiIGQ9Ik05MzYgMzA0LjhMNTYwIDY5NS4yQzU0Ny4yIDcwOS42IDUyOS42IDcxNiA1MTIgNzE2IDQ5NC40IDcxNiA0NzguNCA3MDkuNiA0NjUuNiA2OTYuOEw0NjQgNjk1LjIgODggMzA0LjhDNjcuMiAyODQgNjcuMiAyNTAuNCA4OS42IDIyOS42IDk5LjIgMjIwIDExMiAyMTUuMiAxMjQuOCAyMTUuMkgyMDBWLTY4QzIwMC0xMDMuMiAyMjcuMi0xMzAuNCAyNjIuNC0xMzAuNEg3NjQuOEM4MDAtMTMwLjQgODI4LjgtMTAzLjIgODI4LjgtNjhWMjEzLjZIOTA0QzkzMi44IDIxNS4yIDk1Ni44IDI0MC44IDk1NS4yIDI2OS42IDk1My42IDI4Mi40IDk0NS42IDI5NS4yIDkzNiAzMDQuOFpNODI4LjggMjc3LjZINzY0LjhWMjEzLjYtNjYuNEw2MDYuNC02Ni40VjEyMi40QzYwNi40IDE1NC40IDU3OS4yIDE4MS42IDU0Ny4yIDE4MS42SDQ3Ni44QzQ0NC44IDE4MS42IDQxNy42IDE1NC40IDQxNy42IDEyMi40Vi02Ni40TDI2NC02Ni40VjIxNS4yIDI3OS4ySDIwMCAxNTJMNTA4LjggNjUwLjQgNTEwLjQgNjUyQzUxMC40IDY1MiA1MTAuNCA2NTIgNTEyIDY1MiA1MTMuNiA2NTIgNTEzLjYgNjUyIDUxMy42IDY1MC40TDg3My42IDI3Ny42SDgyOC44WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTE3MiIgdW5pY29kZT0iJiN4RTE3MjsiIGQ9Ik0zNTIgMzY0TTMwNCAzNjRBNDggNDggMCAxIDEgNDAwIDM2NCA0OCA0OCAwIDEgMSAzMDQgMzY0Wk05MjggNjUySDk2Qzc4LjQgNjUyIDY0IDYzNy42IDY0IDYyMFYtMjBDNjQtMzcuNiA3OC40LTUyIDk2LTUySDkyOEM5NDUuNi01MiA5NjAtMzcuNiA5NjAtMjBWNjIwQzk2MCA2MzcuNiA5NDUuNiA2NTIgOTI4IDY1MlpNNTc2IDQxMkg3MzZWMzQ4SDU3NlY0MTJaTTQ0OCAxNTZDNDQ4IDIwOC44IDQwNC44IDI1MiAzNTIgMjUyUzI1NiAyMDguOCAyNTYgMTU2SDE5MC40QzE5MC40IDIxMiAyMTkuMiAyNjMuMiAyNjUuNiAyOTIgMjMwLjQgMzMzLjYgMjMwLjQgMzk2IDI2NS42IDQzNy42IDMwNS42IDQ4NS42IDM3NiA0OTAuNCA0MjQgNDUwLjRTNDc2LjggMzM4LjQgNDM2LjggMjkyQzQ4My4yIDI2MS42IDUxMiAyMTAuNCA1MTIgMTU2SDQ0OFpNODMyIDIyMEg1NzZWMjg0SDgzMlYyMjBaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMTczIiB1bmljb2RlPSImI3hFMTczOyIgZD0iTTkyOCA2NTJIOTZDNzguNCA2NTIgNjQgNjM3LjYgNjQgNjIwVi0yMEM2NC0zNy42IDc4LjQtNTIgOTYtNTJIOTI4Qzk0NS42LTUyIDk2MC0zNy42IDk2MC0yMFY2MjBDOTYwIDYzNy42IDk0NS42IDY1MiA5MjggNjUyWk04OTYgMTJIMTI4VjU4OEg4OTZWMTJaTTU3NiAyODRIODMyVjIyMEg1NzZaTTU3NiA0MTJINzM2VjM0OEg1NzZaTTI1NiAxNTZMMjU2IDE1NkMyNTYgMjA4LjggMjk5LjIgMjUyIDM1MiAyNTJTNDQ4IDIwOC44IDQ0OCAxNTZINTEyQzUxMiAyMTAuNCA0ODMuMiAyNjEuNiA0MzYuOCAyOTIgNDc2LjggMzM4LjQgNDcyIDQxMC40IDQyNCA0NTAuNFMzMDUuNiA0ODUuNiAyNjUuNiA0MzcuNkMyMzAuNCAzOTYgMjMwLjQgMzMzLjYgMjY1LjYgMjkyIDIxOS4yIDI2My4yIDE5MC40IDIxMiAxOTAuNCAxNTZIMjU2Wk0zNTIgNDEyQzM3OS4yIDQxMiA0MDAgMzkxLjIgNDAwIDM2NFMzNzkuMiAzMTYgMzUyIDMxNiAzMDQgMzM2LjggMzA0IDM2NCAzMjQuOCA0MTIgMzUyIDQxMloiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxNzQiIHVuaWNvZGU9IiYjeEUxNzQ7IiBkPSJNODk2IDcxNkgxMjhDMTEwLjQgNzE2IDk2IDcwMS42IDk2IDY4NFYtODRDOTYtMTAxLjYgMTEwLjQtMTE2IDEyOC0xMTZIODk2QzkxMy42LTExNiA5MjgtMTAxLjYgOTI4LTg0VjY4NEM5MjggNzAxLjYgOTEzLjYgNzE2IDg5NiA3MTZaTTg2NCA2NTJWMjI0LjhMNjQ4IDQ0MC44IDQwNi40IDIwMC44IDI4OCAzMTkuMiAxNjAgMTkxLjJWNjUySDg2NFpNMzM2IDQ3Nk0yNDAgNDc2QTk2IDk2IDAgMSAxIDQzMiA0NzYgOTYgOTYgMCAxIDEgMjQwIDQ3NloiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxNzUiIHVuaWNvZGU9IiYjeEUxNzU7IiBkPSJNODk2IDcxNkgxMjhDMTEwLjQgNzE2IDk2IDcwMS42IDk2IDY4NFYtODRDOTYtMTAxLjYgMTEwLjQtMTE2IDEyOC0xMTZIODk2QzkxMy42LTExNiA5MjgtMTAxLjYgOTI4LTg0VjY4NEM5MjggNzAxLjYgOTEzLjYgNzE2IDg5NiA3MTZaTTg2NCA2NTJWMjI0LjhMNjQ4IDQ0MC44IDQwNi40IDIwMC44IDI4OCAzMTkuMiAxNjAgMTkxLjJWNjUySDg2NFpNMTYwLTUyVjEwMEwyODggMjI4IDQwNi40IDEwOS42IDY0OCAzNTEuMiA4NjQgMTM1LjJWLTUySDE2MFpNMzM2IDQ3Nk0yNDAgNDc2QTk2IDk2IDAgMSAxIDQzMiA0NzYgOTYgOTYgMCAxIDEgMjQwIDQ3NloiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxNzYiIHVuaWNvZGU9IiYjeEUxNzY7IiBkPSJNMjM0LjI0IDI5OS4zNkw2My4zNiAxMzkuMzZWNDU4LjcyTDIzNC4yNCAyOTkuMzZaTTMyIDY1Mkg5OTJDMTAwOS42NjQgNjUyIDEwMjQgNjY2LjMzNiAxMDI0IDY4NFMxMDA5LjY2NCA3MTYgOTkyIDcxNkgzMkMxNC4zMzYgNzE2IDAgNzAxLjY2NCAwIDY4NFMxNC4zMzYgNjUyIDMyIDY1MlpNMzItMTE3LjI4SDk5MkMxMDA5LjY2NC0xMTcuMjggMTAyNC0xMDIuOTQ0IDEwMjQtODUuMjhTMTAwOS42NjQtNTMuMjggOTkyLTUzLjI4SDMyQzE0LjMzNi01My4yOCAwLTY3LjYxNiAwLTg1LjI4UzE0LjMzNi0xMTcuMjggMzItMTE3LjI4Wk00NzYuOCAzOTYuNjRIOTkyQzEwMDkuNjY0IDM5Ni42NCAxMDI0IDQxMC45NzYgMTAyNCA0MjguNjRTMTAwOS42NjQgNDYwLjY0IDk5MiA0NjAuNjRINDc2LjhDNDU5LjEzNiA0NjAuNjQgNDQ0LjggNDQ2LjMwNCA0NDQuOCA0MjguNjRTNDU5LjEzNiAzOTYuNjQgNDc2LjggMzk2LjY0Wk00NzYuOCAxNDBIOTkyQzEwMDkuNjY0IDE0MCAxMDI0IDE1NC4zMzYgMTAyNCAxNzJTMTAwOS42NjQgMjA0IDk5MiAyMDRINDc2LjhDNDU5LjEzNiAyMDQgNDQ0LjggMTg5LjY2NCA0NDQuOCAxNzJTNDU5LjEzNiAxNDAgNDc2LjggMTQwWiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTE3NyIgdW5pY29kZT0iJiN4RTE3NzsiIGQ9Ik01MTIgNzQ4QzI2NCA3NDggNjQgNTQ4IDY0IDMwMFMyNjQtMTQ4IDUxMi0xNDggOTYwIDUyIDk2MCAzMDAgNzYwIDc0OCA1MTIgNzQ4Wk01NjAgNTU2QzU4Ny4yIDU1NiA2MDggNTM1LjIgNjA4IDUwOFM1ODcuMiA0NjAgNTYwIDQ2MCA1MTIgNDgwLjggNTEyIDUwOCA1MzIuOCA1NTYgNTYwIDU1NlpNNTk4LjQgODAuOEM1NzYgNTguNCA1NDguOCA0Mi40IDUxOC40IDM2IDQ5OS4yIDMxLjIgNDc4LjQgMzIuOCA0NjAuOCA0MC44IDQ0NC44IDUwLjQgNDM1LjIgNjQuOCA0MzIgODIuNCA0MjguOCA5OC40IDQ0MCAxNDYuNCA0NjIuNCAyMjMuMiA0NzMuNiAyNjYuNCA0ODMuMiAyOTguNCA0ODggMzE3LjYgNDkyLjggMzMyIDQ5NC40IDM0NC44IDQ5Mi44IDM1OS4yIDQ5MS4yIDM2Ny4yIDQ4NC44IDM3MC40IDQ3My42IDM2OC44IDQ1Ny42IDM2Mi40IDQ0My4yIDM1Mi44IDQzMy42IDM0MCA0MTkuMiAzMjIuNCAzOTMuNiAzNDQuOCA0MTcuNiAzNjcuMiA0MzguNCAzODggNDY1LjYgNDAyLjQgNDk0LjQgNDA4LjggNTEyIDQxMy42IDUzMi44IDQxMy42IDU0OC44IDQwNy4yIDU2MS42IDQwMC44IDU3MS4yIDM4OCA1NzQuNCAzNzMuNiA1NzkuMiAzNTQuNCA1NjEuNiAyNzcuNiA1MjEuNiAxNDEuNiA1MTYuOCAxMjguOCA1MTMuNiAxMTQuNCA1MTUuMiAxMDAgNTE4LjQgODcuMiA1MjYuNCA4MC44IDU0MC44IDg0IDU1Ni44IDg3LjIgNTcxLjIgOTYuOCA1ODAuOCAxMDkuNiA1OTUuMiAxMjQgNjI0IDEwNi40IDU5OC40IDgwLjhaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMTc4IiB1bmljb2RlPSImI3hFMTc4OyIgZD0iTTUxMiA3NDhDMjY0IDc0OCA2NCA1NDggNjQgMzAwUzI2NC0xNDggNTEyLTE0OCA5NjAgNTIgOTYwIDMwMCA3NjAgNzQ4IDUxMiA3NDhaTTUxMi04NEMyOTkuMi04NCAxMjggODcuMiAxMjggMzAwUzI5OS4yIDY4NCA1MTIgNjg0IDg5NiA1MTIuOCA4OTYgMzAwIDcyNC44LTg0IDUxMi04NFpNNDk0LjQgNDA4LjhDNDY1LjYgNDAyLjQgNDM4LjQgMzg4IDQxNy42IDM2Ny4yIDM5My42IDM0NC44IDQxOS4yIDMyMi40IDQzMy42IDM0MCA0NDMuMiAzNTIuOCA0NTcuNiAzNjIuNCA0NzMuNiAzNjguOCA0ODQuOCAzNzAuNCA0OTEuMiAzNjcuMiA0OTIuOCAzNTkuMiA0OTQuNCAzNDQuOCA0OTIuOCAzMzIgNDg4IDMxNy42IDQ4My4yIDI5OC40IDQ3My42IDI2Ni40IDQ2Mi40IDIyMy4yIDQ0MCAxNDYuNCA0MjguOCA5OC40IDQzMiA4Mi40IDQzNS4yIDY0LjggNDQ0LjggNTAuNCA0NjAuOCA0MC44IDQ3OC40IDMyLjggNDk5LjIgMzEuMiA1MTguNCAzNiA1NDguOCA0Mi40IDU3NiA1OC40IDU5OC40IDgwLjggNjI0IDEwNi40IDU5NS4yIDEyNCA1ODAuOCAxMDkuNiA1NzEuMiA5Ni44IDU1Ni44IDg3LjIgNTQwLjggODQgNTI2LjQgODAuOCA1MTguNCA4Ny4yIDUxNS4yIDEwMCA1MTMuNiAxMTQuNCA1MTYuOCAxMjguOCA1MjEuNiAxNDEuNiA1NjEuNiAyNzcuNiA1NzkuMiAzNTQuNCA1NzQuNCAzNzMuNiA1NzEuMiAzODggNTYxLjYgNDAwLjggNTQ4LjggNDA3LjIgNTMyLjggNDEzLjYgNTEyIDQxMy42IDQ5NC40IDQwOC44Wk01NjAgNTA4TTUxMiA1MDhBNDggNDggMCAxIDEgNjA4IDUwOCA0OCA0OCAwIDEgMSA1MTIgNTA4WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTE3OSIgdW5pY29kZT0iJiN4RTE3OTsiIGQ9Ik01MTIgNzQ4QzI2NCA3NDggNjQgNTQ4IDY0IDMwMFMyNjQtMTQ4IDUxMi0xNDggOTYwIDUyIDk2MCAzMDAgNzYwIDc0OCA1MTIgNzQ4Wk01MTItODRDMjk5LjItODQgMTI4IDg3LjIgMTI4IDMwMFMyOTkuMiA2ODQgNTEyIDY4NCA4OTYgNTEyLjggODk2IDMwMCA3MjQuOC04NCA1MTItODRaTTQ5NC40IDQwOC44QzQ2NS42IDQwMi40IDQzOC40IDM4OCA0MTcuNiAzNjcuMiAzOTMuNiAzNDQuOCA0MTkuMiAzMjIuNCA0MzMuNiAzNDAgNDQzLjIgMzUyLjggNDU3LjYgMzYyLjQgNDczLjYgMzY4LjggNDg0LjggMzcwLjQgNDkxLjIgMzY3LjIgNDkyLjggMzU5LjIgNDk0LjQgMzQ0LjggNDkyLjggMzMyIDQ4OCAzMTcuNiA0ODMuMiAyOTguNCA0NzMuNiAyNjYuNCA0NjIuNCAyMjMuMiA0NDAgMTQ2LjQgNDI4LjggOTguNCA0MzIgODIuNCA0MzUuMiA2NC44IDQ0NC44IDUwLjQgNDYwLjggNDAuOCA0NzguNCAzMi44IDQ5OS4yIDMxLjIgNTE4LjQgMzYgNTQ4LjggNDIuNCA1NzYgNTguNCA1OTguNCA4MC44IDYyNCAxMDYuNCA1OTUuMiAxMjQgNTgwLjggMTA5LjYgNTcxLjIgOTYuOCA1NTYuOCA4Ny4yIDU0MC44IDg0IDUyNi40IDgwLjggNTE4LjQgODcuMiA1MTUuMiAxMDAgNTEzLjYgMTE0LjQgNTE2LjggMTI4LjggNTIxLjYgMTQxLjYgNTYxLjYgMjc3LjYgNTc5LjIgMzU0LjQgNTc0LjQgMzczLjYgNTcxLjIgMzg4IDU2MS42IDQwMC44IDU0OC44IDQwNy4yIDUzMi44IDQxMy42IDUxMiA0MTMuNiA0OTQuNCA0MDguOFpNNTYwIDUwOE01MTIgNTA4QTQ4IDQ4IDAgMSAxIDYwOCA1MDggNDggNDggMCAxIDEgNTEyIDUwOFoiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxN0EiIHVuaWNvZGU9IiYjeEUxN0E7IiBkPSJNODc3LjQ0LTIwTDk1MS4wNCA1My42Qzk2My44NCA2Ni40IDk2My44NCA4Ni4yNCA5NTEuMDQgOTkuMDRTOTE4LjQgMTExLjg0IDkwNS42IDk5LjA0TDgzMiAyNS40NCA3NDkuNDQgMTA4IDgyMy4wNCAxODEuNkM4MzUuODQgMTk0LjQgODM1Ljg0IDIxNC4yNCA4MjMuMDQgMjI3LjA0Uzc5MC40IDIzOS44NCA3NzcuNiAyMjcuMDRMNzA0IDE1My40NCA1NzYgMjgxLjQ0QzYxNS42OCAzMzAuNzIgNjQwIDM5Mi4xNiA2NDAgNDYwIDY0MCA2MTguNzIgNTEwLjcyIDc0OCAzNTIgNzQ4UzY0IDYxOC43MiA2NCA0NjAgMTkzLjI4IDE3MiAzNTIgMTcyQzQxOS44NCAxNzIgNDgxLjI4IDE5Ni4zMiA1MzAuNTYgMjM2TDkwNC45Ni0xMzguNEM5MTEuMzYtMTQ0LjggOTE5LjY4LTE0OCA5MjcuMzYtMTQ4Uzk0NC0xNDQuOCA5NDkuNzYtMTM4LjRDOTYyLjU2LTEyNS42IDk2Mi41Ni0xMDUuNzYgOTQ5Ljc2LTkyLjk2TDg3Ny40NC0yMFpNMzUyIDIzNkMyMjguNDggMjM2IDEyOCAzMzYuNDggMTI4IDQ2MFMyMjguNDggNjg0IDM1MiA2ODQgNTc2IDU4My41MiA1NzYgNDYwIDQ3NS41MiAyMzYgMzUyIDIzNloiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxN0IiIHVuaWNvZGU9IiYjeEUxN0I7IiBkPSJNNjgwLjk2IDY4Mi4wOEM2NjYuODggNjg1LjkyIDY1MC44OCA2ODMuMzYgNjQwLjY0IDY3NS4wNEwyMDEuNiAzMTguNTZDMTg4LjggMzA4LjMyIDE4OC44IDI5MS42OCAyMDEuNiAyODEuNDRMNjQwLjY0LTc1LjA0QzY0Ny42OC04MC44IDY1Ny4yOC04NCA2NjcuNTItODQgNjcyLTg0IDY3Ni40OC04My4zNiA2ODAuOTYtODIuMDggNjk1LjA0LTc4LjI0IDcwNC02OCA3MDQtNTYuNDhWNjU2LjQ4QzcwNCA2NjggNjk1LjA0IDY3OC4yNCA2ODAuOTYgNjgyLjA4WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTE3QyIgdW5pY29kZT0iJiN4RTE3QzsiIGQ9Ik05OTItMjBINjRWMjc3LjZMMjQ1LjEyIDQ0Mi4wOEMyNTcuOTIgNDMzLjc2IDI3MiA0MjggMjg4IDQyOCAzMDIuNzIgNDI4IDMxNS41MiA0MzMuMTIgMzI3LjA0IDQzOS41Mkw1OTUuMiAxNzEuMzZDNTkzLjkyIDE2Ni4yNCA1OTIgMTYxLjEyIDU5MiAxNTYgNTkyIDExMS44NCA2MjcuODQgNzYgNjcyIDc2Uzc1MiAxMTEuODQgNzUyIDE1NkM3NTIgMTYxLjc2IDc1MC4wOCAxNjYuMjQgNzQ4LjggMTcxLjM2TDkxNS4yIDMzNy43NkM5MjQuMTYgMzM0LjU2IDkzMy43NiAzMzIgOTQ0IDMzMiA5ODguMTYgMzMyIDEwMjQgMzY3Ljg0IDEwMjQgNDEyUzk4OC4xNiA0OTIgOTQ0IDQ5MiA4NjQgNDU2LjE2IDg2NCA0MTJDODY0IDQwMS43NiA4NjYuNTYgMzkyLjE2IDg2OS43NiAzODMuMkw3MTEuMDQgMjI0LjQ4QzY5OS41MiAyMzAuODggNjg2LjcyIDIzNiA2NzIgMjM2UzY0NC40OCAyMzAuODggNjMyLjk2IDIyNC40OEwzNjQuOCA0OTIuNjRDMzY2LjA4IDQ5Ny43NiAzNjggNTAyLjg4IDM2OCA1MDggMzY4IDU1Mi4xNiAzMzIuMTYgNTg4IDI4OCA1ODhTMjA4IDU1Mi4xNiAyMDggNTA4QzIwOCA1MDQuMTYgMjA5LjkyIDUwMC4zMiAyMTAuNTYgNDk2LjQ4TDY0IDM2NFY2NTJDNjQgNjY5LjkyIDQ5LjkyIDY4NCAzMiA2ODRTMCA2NjkuOTIgMCA2NTJWLTUyQzAtNjkuOTIgMTQuMDgtODQgMzItODRIOTkyQzEwMDkuOTItODQgMTAyNC02OS45MiAxMDI0LTUyUzEwMDkuOTItMjAgOTkyLTIwWiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTE3RCIgdW5pY29kZT0iJiN4RTE3RDsiIGQ9Ik0zNTIgMTQwSDgwMFY3NkgzNTJaTTM1MiAzMzJIODAwVjI2OEgzNTJaTTM1MiA1MjRIODAwVjQ2MEgzNTJaTTIyNCAxNDBIMjg4Vjc2SDIyNFpNMjI0IDMzMkgyODhWMjY4SDIyNFpNMjI0IDUyNEgyODhWNDYwSDIyNFoiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxN0UiIHVuaWNvZGU9IiYjeEUxN0U7IiBkPSJNODY0IDM5Nkg3NTJWNDQ0QTI0MCAyNDAgMCAwIDEgMjcyIDQ0NFYzOTZIMTYwQTMwLjQgMzAuNCAwIDAgMSAxMjggMzY3Ljg0Vi01NS4zNkEzMC43MiAzMC43MiAwIDAgMSAxNjAtODRIODY0QTMwLjcyIDMwLjcyIDAgMCAxIDg5Ni01NS4zNlYzNjcuMzZBMzAuNzIgMzAuNzIgMCAwIDEgODY0IDM5NlpNMzM2IDQ0NEExNzYgMTc2IDAgMCAwIDY4OCA0NDRWMzk2SDMzNlpNNTUyIDE1MS4wNFY2OS4yOEE0MCA0MCAwIDAgMCA0NzIgNjkuMjhWMTUxLjA0QTgwIDgwIDAgMSAwIDU1MiAxNTEuMDRaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMTdGIiB1bmljb2RlPSImI3hFMTdGOyIgZD0iTTQ3MiAxMzUuMDRWNTJBNDAgNDAgMCAwIDEgNTUyIDUyVjEzNS4wNEE4MCA4MCAwIDEgMSA0NzIgMTM1LjA0Wk04NjQgMzk2SDc1MlY0NDRBMjQwIDI0MCAwIDAgMSAyNzIgNDQ0VjM5NkgxNjBBMzAuNCAzMC40IDAgMCAxIDEyOCAzNjcuODRWLTU1LjM2QTMwLjcyIDMwLjcyIDAgMCAxIDE2MC04NEg4NjRBMzAuNzIgMzAuNzIgMCAwIDEgODk2LTU1LjM2VjM2Ny4zNkEzMC43MiAzMC43MiAwIDAgMSA4NjQgMzk2Wk0zMzYgNDQ0QTE3NiAxNzYgMCAwIDAgNjg4IDQ0NFYzOTZIMzM2Wk04MzItMjBIMTkyVjMzMkg4MzJaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMTgwIiB1bmljb2RlPSImI3hFMTgwOyIgZD0iTTUxMiA3NDhDMjY0IDc0OCA2NCA1NDggNjQgMzAwUzI2NC0xNDggNTEyLTE0OCA5NjAgNTIgOTYwIDMwMCA3NjAgNzQ4IDUxMiA3NDhaTTczNiAyNjhIMjg4VjMzMkg3MzZWMjY4WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTE4MSIgdW5pY29kZT0iJiN4RTE4MTsiIGQ9Ik01MTIgNjg0QzcyNC44IDY4NCA4OTYgNTEyLjggODk2IDMwMFM3MjQuOC04NCA1MTItODQgMTI4IDg3LjIgMTI4IDMwMCAyOTkuMiA2ODQgNTEyIDY4NE01MTIgNzQ4QzI2NCA3NDggNjQgNTQ4IDY0IDMwMFMyNjQtMTQ4IDUxMi0xNDggOTYwIDUyIDk2MCAzMDAgNzYwIDc0OCA1MTIgNzQ4Wk0yODggMzMySDczNlYyNjhIMjg4WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTE4MiIgdW5pY29kZT0iJiN4RTE4MjsiIGQ9Ik04NjQgODEySDE2MEM3MS42MzczIDgxMiAwIDc0MC4zNjI3IDAgNjUyVi01MkMwLTE0MC4zNjI3IDcxLjYzNzMtMjEyIDE2MC0yMTJIODY0Qzk1Mi4zNjI3LTIxMiAxMDI0LTE0MC4zNjI3IDEwMjQtNTJWNjUyQzEwMjQgNzQwLjM2MjcgOTUyLjM2MjcgODEyIDg2NCA4MTJaTTczNiAyNjhIMjg4QzI3MC4zMzYgMjY4IDI1NiAyODIuMzM2IDI1NiAzMDBTMjcwLjMzNiAzMzIgMjg4IDMzMkg3MzZDNzUzLjY2NCAzMzIgNzY4IDMxNy42NjQgNzY4IDMwMFM3NTMuNjY0IDI2OCA3MzYgMjY4WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTE4MyIgdW5pY29kZT0iJiN4RTE4MzsiIGQ9Ik03MzYgMjY4SDI4OEMyNzAuMzM2IDI2OCAyNTYgMjgyLjMzNiAyNTYgMzAwUzI3MC4zMzYgMzMyIDI4OCAzMzJINzM2Qzc1My42NjQgMzMyIDc2OCAzMTcuNjY0IDc2OCAzMDBTNzUzLjY2NCAyNjggNzM2IDI2OFpNODY0LTIxMkgxNjBDNzEuNjM3My0yMTIgMC0xNDAuMzYyNyAwLTUyVjY1MkMwIDc0MC4zNjI3IDcxLjYzNzMgODEyIDE2MCA4MTJIODY0Qzk1Mi4zNjI3IDgxMiAxMDI0IDc0MC4zNjI3IDEwMjQgNjUyVi01MkMxMDI0LTE0MC4zNjI3IDk1Mi4zNjI3LTIxMiA4NjQtMjEyWk0xNjAgNzQ4QzEwNi45NjUzIDc0OCA2NCA3MDUuMDM0NyA2NCA2NTJWLTUyQzY0LTEwNS4wMzQ3IDEwNi45NjUzLTE0OCAxNjAtMTQ4SDg2NEM5MTcuMDM0Ny0xNDggOTYwLTEwNS4wMzQ3IDk2MC01MlY2NTJDOTYwIDcwNS4wMzQ3IDkxNy4wMzQ3IDc0OCA4NjQgNzQ4WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTE4NCIgdW5pY29kZT0iJiN4RTE4NDsiIGQ9Ik05MjIuODggMjY4SDEwMS4xMkM4MC42NCAyNjggNjQgMjgyLjA4IDY0IDMwMFM4MC42NCAzMzIgMTAxLjEyIDMzMkg5MjIuMjRDOTQzLjM2IDMzMiA5NjAgMzE3LjkyIDk2MCAzMDBTOTQzLjM2IDI2OCA5MjIuODggMjY4WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTE4NSIgdW5pY29kZT0iJiN4RTE4NTsiIGQ9Ik0zNTEuODM4Mi04My41ODgyVi04My41ODgyWk01NDMuNzUgODEySDE1OS45MjY1QzcxLjYwNDQgODEyIDAgNzQwLjM5NTYgMCA2NTIuMDczNVYtNTEuNjAyOUMwLTEzOS45MjUgNzEuNjA0NC0yMTEuNTI5NCAxNTkuOTI2NS0yMTEuNTI5NEg1NDMuNzVDNjMyLjA3MjEtMjExLjUyOTQgNzAzLjY3NjUtMTM5LjkyNSA3MDMuNjc2NS01MS42MDI5VjY1Mi4wNzM1QzcwMy42NzY1IDc0MC4zOTU2IDYzMi4wNzIxIDgxMiA1NDMuNzUgODEyWk0yODcuODY3NiA3NDguMDI5NEg0MTUuODA4OEM0MzMuNDY0NyA3NDguMDI5NCA0NDcuNzk0MSA3MzMuNyA0NDcuNzk0MSA3MTYuMDQ0MVM0MzMuNDY0NyA2ODQuMDU4OCA0MTUuODA4OCA2ODQuMDU4OEgyODcuODY3NkMyNzAuMjExOCA2ODQuMDU4OCAyNTUuODgyNCA2OTguMzg4MiAyNTUuODgyNCA3MTYuMDQ0MVMyNzAuMjExOCA3NDguMDI5NCAyODcuODY3NiA3NDguMDI5NFpNMzUxLjgzODItMTQ3LjU1ODhDMzE2LjUyNjUtMTQ3LjU1ODggMjg3Ljg2NzYtMTE4LjkgMjg3Ljg2NzYtODMuNTg4MlMzMTYuNTI2NS0xOS42MTc2IDM1MS44MzgyLTE5LjYxNzZDMzg3LjE1LTE5LjYxNzYgNDE1LjgwODgtNDguMjc2NSA0MTUuODA4OC04My41ODgyUzM4Ny4xNS0xNDcuNTU4OCAzNTEuODM4Mi0xNDcuNTU4OFpNNjA3LjcyMDYgNzYuMzM4MkM2MDcuNzIwNiA1OC42ODI0IDU5My4zOTEyIDQ0LjM1MjkgNTc1LjczNTMgNDQuMzUyOUgxMjcuOTQxMkMxMTAuMjg1MyA0NC4zNTI5IDk1Ljk1NTkgNTguNjgyNCA5NS45NTU5IDc2LjMzODJWNTg4LjEwMjlDOTUuOTU1OSA2MDUuNzU4OCAxMTAuMjg1MyA2MjAuMDg4MiAxMjcuOTQxMiA2MjAuMDg4Mkg1NzUuNzM1M0M1OTMuMzkxMiA2MjAuMDg4MiA2MDcuNzIwNiA2MDUuNzU4OCA2MDcuNzIwNiA1ODguMTAyOVoiICBob3Jpei1hZHYteD0iNzI1IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTE4NiIgdW5pY29kZT0iJiN4RTE4NjsiIGQ9Ik01NDMuNzUtMjExLjUyOTRIMTU5LjkyNjVDNzEuNjA0NC0yMTEuNTI5NCAwLTEzOS45MjUgMC01MS42MDI5VjY1Mi4wNzM1QzAgNzQwLjM5NTYgNzEuNjA0NCA4MTIgMTU5LjkyNjUgODEySDU0My43NUM2MzIuMDcyMSA4MTIgNzAzLjY3NjUgNzQwLjM5NTYgNzAzLjY3NjUgNjUyLjA3MzVWLTUxLjYwMjlDNzAzLjY3NjUtMTM5LjkyNSA2MzIuMDcyMS0yMTEuNTI5NCA1NDMuNzUtMjExLjUyOTRaTTE1OS45MjY1IDc0OC4wMjk0QzEwNi45MTYyIDc0OC4wMjk0IDYzLjk3MDYgNzA1LjA4MzggNjMuOTcwNiA2NTIuMDczNVYtNTEuNjAyOUM2My45NzA2LTEwNC42MTMyIDEwNi45MTYyLTE0Ny41NTg4IDE1OS45MjY1LTE0Ny41NTg4SDU0My43NUM1OTYuNzYwMy0xNDcuNTU4OCA2MzkuNzA1OS0xMDQuNjEzMiA2MzkuNzA1OS01MS42MDI5VjY1Mi4wNzM1QzYzOS43MDU5IDcwNS4wODM4IDU5Ni43NjAzIDc0OC4wMjk0IDU0My43NSA3NDguMDI5NFpNMzUxLjgzODItODMuNTg4MkMzMTYuNTI2NS04My41ODgyIDI4Ny44Njc2LTU0LjkyOTQgMjg3Ljg2NzYtMTkuNjE3NlMzMTYuNTI2NSA0NC4zNTI5IDM1MS44MzgyIDQ0LjM1MjlDMzg3LjE1IDQ0LjM1MjkgNDE1LjgwODggMTUuNjk0MSA0MTUuODA4OC0xOS42MTc2UzM4Ny4xNS04My41ODgyIDM1MS44MzgyLTgzLjU4ODJaTTQxNS44MDg4IDYyMC4wODgySDI4Ny44Njc2QzI3MC4yMTE4IDYyMC4wODgyIDI1NS44ODI0IDYzNC40MTc2IDI1NS44ODI0IDY1Mi4wNzM1UzI3MC4yMTE4IDY4NC4wNTg4IDI4Ny44Njc2IDY4NC4wNTg4SDQxNS44MDg4QzQzMy40NjQ3IDY4NC4wNTg4IDQ0Ny43OTQxIDY2OS43Mjk0IDQ0Ny43OTQxIDY1Mi4wNzM1UzQzMy40NjQ3IDYyMC4wODgyIDQxNS44MDg4IDYyMC4wODgyWiIgIGhvcml6LWFkdi14PSI3MjUiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMTg3IiB1bmljb2RlPSImI3hFMTg3OyIgZD0iTTkzMy4yMDUzIDEzMi4wNjRMOTA1LjIxNiAxMzcuNTI1M0M5MDAuMzk0NyAxNTEuMDkzMyA4OTQuNDIxMyAxNjIuNzg0IDg4Ny4xMjUzIDE3My41Nzg3TDg4Ny40NjY3IDE3My4wMjQgOTAxLjgwMjcgMTk1LjU1MkM5MDYuNDk2IDIwMC4xNiA5MDkuNDQgMjA2LjU2IDkwOS40NCAyMTMuNjQyN1M5MDYuNTM4NyAyMjcuMTI1MyA5MDEuODAyNyAyMzEuNzMzM0w5MDEuODAyNyAyMzEuNzMzMyA4ODcuNDY2NyAyNDkuNDgyN0M4ODMuMDcyIDI1My43NDkzIDg3Ny4wMTMzIDI1Ni4zOTQ3IDg3MC40IDI1Ni4zOTQ3Uzg1Ny43MjggMjUzLjc0OTMgODUzLjMzMzMgMjQ5LjQ4MjdMODUzLjMzMzMgMjQ5LjQ4MjcgODI4Ljc1NzMgMjMxLjczMzNDODE4Ljk4NjcgMjM3LjM2NTMgODA3LjYzNzMgMjQyLjIyOTMgNzk1Ljc3NiAyNDUuNzcwN0w3OTQuNjI0IDI0Ni4wNjkzIDc4OS4xNjI3IDI3MS4zMjhDNzg5LjI0OCAyNzIuMTM4NyA3ODkuMjkwNyAyNzMuMTIgNzg5LjI5MDcgMjc0LjA1ODcgNzg5LjI5MDcgMjg4LjE4MTMgNzc3Ljk4NCAyOTkuNzAxMyA3NjMuOTA0IDMwMEg3MzguNjAyN0M3MzguMzg5MyAzMDAgNzM4LjEzMzMgMzAwIDczNy44NzczIDMwMCA3MjQuNzc4NyAzMDAgNzE0LjA2OTMgMjg5Ljc2IDcxMy4zNDQgMjc2LjgzMkw3MTMuMzQ0IDI3Ni43NDY3IDcwNy44ODI3IDI0OC43NTczQzY5NC44NjkzIDI0NC45NiA2ODMuNTIgMjQwLjA1MzMgNjcyLjk4MTMgMjMzLjk5NDdMNjczLjc0OTMgMjM0LjQyMTMgNjUxLjkwNCAyNDguNzU3M0M2NDcuMzgxMyAyNTMuMzIyNyA2NDEuMTA5MyAyNTYuMjI0IDYzNC4xNTQ3IDI1Ni4yNjY3SDYzNC4xNTQ3QzYzNC4xMTIgMjU2LjI2NjcgNjM0LjAyNjcgMjU2LjI2NjcgNjMzLjk4NCAyNTYuMjY2NyA2MjYuODU4NyAyNTYuMjY2NyA2MjAuNDE2IDI1My40MDggNjE1LjcyMjcgMjQ4Ljc1NzNMNjE1LjcyMjcgMjQ4Ljc1NzMgNTk3LjI5MDcgMjMxLjY5MDdDNTkyLjcyNTMgMjI3LjE2OCA1ODkuODI0IDIyMC44OTYgNTg5Ljc4MTMgMjEzLjk0MTNWMjEzLjk0MTNDNTg5LjczODcgMjEzLjUxNDcgNTg5LjczODcgMjEzLjA0NTMgNTg5LjczODcgMjEyLjU3NiA1ODkuNzM4NyAyMDYuODU4NyA1OTEuODI5MyAyMDEuNTY4IDU5NS4yODUzIDE5Ny41NTczTDU5NS4yNDI3IDE5Ny42IDYxMS42MjY3IDE3My4wMjRDNjA1Ljg2NjcgMTYyLjgyNjcgNjAwLjk2IDE1MS4wNTA3IDU5Ny41NDY3IDEzOC42MzQ3TDU5Ny4yOTA3IDEzNy41MjUzIDU3MC42NjY3IDEzMi4wNjRDNTU2LjYyOTMgMTMxLjY4IDU0NS40MDggMTIwLjIwMjcgNTQ1LjQwOCAxMDYuMTIyNyA1NDUuNDA4IDEwNi4xMjI3IDU0NS40MDggMTA2LjEyMjcgNTQ1LjQwOCAxMDYuMTIyN1YxMDYuMTIyNyA4MC44NjRDNTQ1LjQwOCA4MC44MjEzIDU0NS40MDggODAuODIxMyA1NDUuNDA4IDgwLjc3ODcgNTQ1LjQwOCA2Ny41NTIgNTU1LjU2MjcgNTYuNzE0NyA1NjguNTMzMyA1NS42MDUzTDU2OC42MTg3IDU1LjYwNTMgNTk4LjY1NiA0OS40NjEzQzYwMi40NTMzIDM2LjQ0OCA2MDcuMzE3MyAyNS4wOTg3IDYxMy40MTg3IDE0LjU2TDYxMi45OTIgMTUuMzI4IDU5Ny4yOTA3LTguNTY1M0M1OTIuNzI1My0xMy4yMTYgNTg5Ljk1Mi0xOS42MTYgNTg5Ljk1Mi0yNi42NTZTNTkyLjc2OC00MC4wOTYgNTk3LjI5MDctNDQuNzQ2N0w1OTcuMjkwNy00NC43NDY3IDYxNS43MjI3LTYyLjQ5NkM2MjAuMTE3My02Ni43NjI3IDYyNi4xNzYtNjkuNDA4IDYzMi43ODkzLTY5LjQwOFM2NDUuNDYxMy02Ni43NjI3IDY0OS44NTYtNjIuNDk2TDY0OS44NTYtNjIuNDk2IDY3Ni40OC00NC43NDY3QzY4NS4yMjY3LTQ5LjQ4MjcgNjk1LjQyNC01My42NjQgNzA2LjA5MDctNTYuNzM2TDcwNy4yLTU3LjAzNDcgNzEzLjM0NC04NS43MDY3QzcxMy4zNDQtMTAwLjA0MjcgNzI0Ljk0OTMtMTExLjY0OCA3MzkuMjg1My0xMTEuNjQ4Vi0xMTEuNjQ4SDc2NS4yMjY3Qzc2NS40NC0xMTEuNjQ4IDc2NS42OTYtMTExLjY0OCA3NjUuOTUyLTExMS42NDggNzc5LjA1MDctMTExLjY0OCA3ODkuNzYtMTAxLjQwOCA3OTAuNDg1My04OC40OEw3OTAuNDg1My04OC4zOTQ3IDc5Ni42MjkzLTU2Ljk5MkM4MDguNDA1My01My42MjEzIDgxOC42MDI3LTQ5LjQ0IDgyOC4yMDI3LTQ0LjI3NzNMODI3LjM0OTMtNDQuNzA0IDg1MS45MjUzLTYxLjA4OEM4NTYuNTc2LTY1LjY1MzMgODYyLjk3Ni02OC40MjY3IDg3MC4wMTYtNjguNDI2N1M4ODMuNDU2LTY1LjYxMDcgODg4LjEwNjctNjEuMDg4TDg4OC4xMDY3LTYxLjA4OCA5MDYuNTM4Ny00My4zMzg3QzkxMC44NDgtMzguODE2IDkxMy40OTMzLTMyLjY3MiA5MTMuNDkzMy0yNS45MzA3UzkxMC44NDgtMTMuMDQ1MyA5MDYuNTM4Ny04LjUyMjdMOTA2LjUzODctOC41MjI3IDg4Ny40MjQgMTYuMDUzM0M4OTMuMDk4NyAyNS44MjQgODk3Ljk2MjcgMzcuMTczMyA5MDEuNDYxMyA0OS4wNzczTDkwMS43NiA1MC4xODY3IDkyOS4wNjY3IDU1LjY0OEM5NDMuNDAyNyA1NS42NDggOTU1LjAwOCA2Ny4yNTMzIDk1NS4wMDggODEuNTg5M1YxMDYuODQ4Qzk1NC42NjY3IDEyMC4yMDI3IDk0NC4zNDEzIDEzMS4wNCA5MzEuMiAxMzIuMTA2N0w5MzEuMTE0NyAxMzIuMTA2N1pNNzUwLjkzMzMgMzEuMDI5M0M3MTUuNDc3MyAzMS4wMjkzIDY4Ni43NjI3IDU5Ljc0NCA2ODYuNzYyNyA5NS4yUzcxNS40NzczIDE1OS4zNzA3IDc1MC45MzMzIDE1OS4zNzA3Qzc4Ni4zODkzIDE1OS4zNzA3IDgxNS4xMDQgMTMwLjY1NiA4MTUuMTA0IDk1LjJWOTUuMkM4MTUuMTA0IDU5Ljc0NCA3ODYuMzg5MyAzMS4wMjkzIDc1MC45MzMzIDMxLjAyOTNWMzEuMDI5M1pNNjU3LjQwOCAzMTQuMzM2QzY3NC45NDQgMzI3LjUyIDY5NC45NTQ3IDMzOC45OTczIDcxNi4zMzA3IDM0Ny43ODY3TDcxOC4xNjUzIDM0OC40NjkzIDU5Ny4zMzMzIDcwMC4wNDI3QzU5NS40OTg3IDcwNS41NDY3IDU5MC4zNzg3IDcwOS40MjkzIDU4NC4zNjI3IDcwOS40MjkzUzU3My4yMjY3IDcwNS41NDY3IDU3MS40MzQ3IDcwMC4xMjhMNTcxLjM5MiA3MDAuMDQyNyA0NDEuNjg1MyAxMDEuMzQ0IDI4OS40NTA3IDQ5Ni42MDhDMjg3LjYxNiA1MDIuMTEyIDI4Mi40OTYgNTA1Ljk5NDcgMjc2LjQ4IDUwNS45OTQ3UzI2NS4zNDQgNTAyLjExMiAyNjMuNTUyIDQ5Ni42OTMzTDI2My41MDkzIDQ5Ni42MDggMjA0LjggMzE0LjMzNkMyMDMuMDA4IDMwOC43NDY3IDE5Ny44ODggMzA0LjgyMTMgMTkxLjgyOTMgMzA0Ljc3ODdIMzQuMTMzM0MxNS4yNzQ3IDMwNC43Nzg3IDAgMjg5LjUwNCAwIDI3MC42NDUzUzE1LjI3NDcgMjM2LjUxMiAzNC4xMzMzIDIzNi41MTJWMjM2LjUxMkgyNDMuMDI5M0MyNDkuMDg4IDIzNi41NTQ3IDI1NC4yMDggMjQwLjQ4IDI1NS45NTczIDI0NS45ODRMMjU2IDI0Ni4wNjkzIDI4MS4yNTg3IDMyNS45NDEzIDQ0Mi4zNjgtOTYuNjI5M0M0NDQuMjAyNy0xMDIuMTMzMyA0NDkuMzIyNy0xMDYuMDE2IDQ1NS4zMzg3LTEwNi4wMTZTNDY2LjQ3NDctMTAyLjEzMzMgNDY4LjI2NjctOTYuNzE0N0w0NjguMzA5My05Ni42MjkzIDU5NS45NjggNDkwLjQ2NFpNMTAyNC00MS4zMzMzQzEwMjQtNDEuMzMzMyAxMDA4LjcyNTMtNDEuMzMzMyA5ODkuODY2Ny00MS4zMzMzUzk1NS43MzMzLTQxLjMzMzMgOTU1LjczMzMtNDEuMzMzM0M5NTUuNzMzMy00MS4zMzMzIDk3MS4wMDgtNDEuMzMzMyA5ODkuODY2Ny00MS4zMzMzUzEwMjQtNDEuMzMzMyAxMDI0LTQxLjMzMzNaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMTg4IiB1bmljb2RlPSImI3hFMTg4OyIgZD0iTTUwMi40ODUzLTEyMi43ODRDNTAwLjUyMjctMTI4LjY3MiA0OTUuMDE4Ny0xMzIuODUzMyA0ODguNTc2LTEzMi44NTMzUzQ3Ni42NzItMTI4LjY3MiA0NzQuNzA5My0xMjIuOTEyTDQ3NC42NjY3LTEyMi44MjY3IDMwMi4wMzczIDMyNy43MzMzIDI3NC4yNjEzIDI0Mi4xNDRDMjcyLjM0MTMgMjM2LjE3MDcgMjY2LjgzNzMgMjMxLjk0NjcgMjYwLjM1MiAyMzEuOTA0SDM2LjUyMjdDMTYuMzQxMyAyMzEuOTA0LTAuMDQyNyAyNDguMjg4LTAuMDQyNyAyNjguNDY5M1MxNi4zNDEzIDMwNS4wMzQ3IDM2LjUyMjcgMzA1LjAzNDdWMzA1LjAzNDdIMjA2LjkzMzNDMjEyLjgyMTMgMzA1LjY3NDcgMjE3LjY0MjcgMzA5LjcyOCAyMTkuMzQ5MyAzMTUuMTg5M0wyMTkuMzkyIDMxNS4yNzQ3IDI4MS41NTczIDUwOS44MzQ3QzI4My41MiA1MTUuNzIyNyAyODkuMDI0IDUxOS45MDQgMjk1LjQ2NjcgNTE5LjkwNFMzMDcuMzcwNyA1MTUuNzIyNyAzMDkuMzMzMyA1MDkuOTYyN0wzMDkuMzc2IDUwOS44NzczIDQ3MS43NjUzIDg0LjE5MiA2MTAuNzMwNyA3MjUuNjQyN0M2MTIuNjkzMyA3MzEuNTMwNyA2MTguMTk3MyA3MzUuNzEyIDYyNC42NCA3MzUuNzEyUzYzNi41NDQgNzMxLjUzMDcgNjM4LjUwNjcgNzI1Ljc3MDdMNjM4LjU0OTMgNzI1LjY4NTMgODA0LjU2NTMgMjU3LjU4OTNDODA2LjQ4NTMgMjUxLjYxNiA4MTEuOTg5MyAyNDcuMzkyIDgxOC40NzQ3IDI0Ny4zNDkzSDk4Ny40MzQ3QzEwMDcuNjE2IDI0Ny4zNDkzIDEwMjQgMjMwLjk2NTMgMTAyNCAyMTAuNzg0UzEwMDcuNjE2IDE3NC4yMTg3IDk4Ny40MzQ3IDE3NC4yMTg3VjE3NC4yMTg3SDc2My42MDUzQzc1Ny4xMiAxNzQuMjYxMyA3NTEuNjE2IDE3OC40ODUzIDc0OS43Mzg3IDE4NC4zNzMzTDc0OS42OTYgMTg0LjQ1ODcgNjM4LjUwNjcgNTA2LjI5MzNaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMTg5IiB1bmljb2RlPSImI3hFMTg5OyIgZD0iTTQ0OCA1NTZDNDQ4IDU5MS4yIDQ3Ni44IDYyMCA1MTIgNjIwUzU3NiA1OTEuMiA1NzYgNTU2QzU3NiA1MjAuOCA1NDcuMiA0OTIgNTEyIDQ5MlM0NDggNTIwLjggNDQ4IDU1NlpNNTEyIDM2NEM0NzYuOCAzNjQgNDQ4IDMzNS4yIDQ0OCAzMDBTNDc2LjggMjM2IDUxMiAyMzYgNTc2IDI2NC44IDU3NiAzMDBDNTc2IDMzNS4yIDU0Ny4yIDM2NCA1MTIgMzY0Wk01MTIgMTA4QzQ3Ni44IDEwOCA0NDggNzkuMiA0NDggNDRTNDc2LjgtMjAgNTEyLTIwIDU3NiA4LjggNTc2IDQ0QzU3NiA3OS4yIDU0Ny4yIDEwOCA1MTIgMTA4WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTE4QSIgdW5pY29kZT0iJiN4RTE4QTsiIGQ9Ik0xMDE4Ljg4IDMxNy4yOEMxMDE4Ljg4IDMxNy4yOCAxMDE4Ljg4IDMxNy4yOCAxMDE4Ljg4IDMxNy4yOFMxMDE4Ljg4IDMxNy4yOCAxMDE4Ljg4IDMxNy4yOFYzMTcuMjhDMTAxOC44OCAzMTcuMjggMTAxOC44OCAzMTcuMjggMTAxOC44OCAzMTcuMjhTMTAxOC44OCAzMTcuMjggMTAxOC44OCAzMTcuMjggMTAxOC44OCAzMTcuMjggMTAxOC44OCAzMTcuMjggMTAxOC44OCAzMTcuMjggMTAxOC44OCAzMTcuMjhDMTAxOC4yNCAzMTcuOTIgMTAxOC4yNCAzMTguNTYgMTAxOC4yNCAzMTguNTZTMTAxOC4yNCAzMTguNTYgMTAxOC4yNCAzMTguNTYgMTAxOC4yNCAzMTguNTYgMTAxOC4yNCAzMTguNTYgMTAxOC4yNCAzMTguNTYgMTAxOC4yNCAzMTguNTZWMzE4LjU2QzEwMTguMjQgMzE4LjU2IDEwMTguMjQgMzE4LjU2IDEwMTguMjQgMzE4LjU2UzEwMTguMjQgMzE4LjU2IDEwMTguMjQgMzE4LjU2IDEwMTguMjQgMzE4LjU2IDEwMTguMjQgMzE4LjU2VjMxOC41NiAzMTguNTZDMTAxOC4yNCAzMTguNTYgMTAxOC4yNCAzMTguNTYgMTAxOC4yNCAzMTguNTZTMTAxOC4yNCAzMTguNTYgMTAxOC4yNCAzMTguNTZDMTAxNy42IDMxOS4yIDEwMTYuOTYgMzIwLjQ4IDEwMTYuMzIgMzIxLjEyTDg1Ni4zMiA0OTcuMTJDODQ0LjE2IDUwOS45MiA4MjQuMzIgNTExLjIgODEwLjg4IDQ5OS4wNFM3OTYuOCA0NjcuMDQgODA4Ljk2IDQ1My42TDkyMC4zMiAzMzEuMzZINTQ0VjcwNy42OEw2NjYuMjQgNTk2LjMyQzY3OS42OCA1ODQuMTYgNjk5LjUyIDU4NS40NCA3MTEuNjggNTk4LjI0UzcyMi41NiA2MzEuNTIgNzA5Ljc2IDY0My42OEw1MzMuNzYgODAzLjY4QzUzMi40OCA4MDQuMzIgNTMxLjg0IDgwNC45NiA1MzEuMiA4MDUuNiA1MzEuMiA4MDUuNiA1MzEuMiA4MDUuNiA1MzEuMiA4MDUuNlM1MzEuMiA4MDUuNiA1MzEuMiA4MDUuNlY4MDUuNkM1MzEuMiA4MDUuNiA1MzEuMiA4MDUuNiA1MzEuMiA4MDUuNlM1MzEuMiA4MDUuNiA1MzEuMiA4MDUuNlY4MDUuNkM1MzEuMiA4MDUuNiA1MzEuMiA4MDUuNiA1MzEuMiA4MDUuNlM1MzEuMiA4MDUuNiA1MzEuMiA4MDUuNlY4MDUuNkM1MzEuMiA4MDUuNiA1MzEuMiA4MDUuNiA1MzEuMiA4MDUuNlM1MzAuNTYgODA2LjI0IDUyOS45MiA4MDYuMjRDNTI5LjkyIDgwNi4yNCA1MjkuOTIgODA2LjI0IDUyOS45MiA4MDYuMjRTNTI5LjkyIDgwNi4yNCA1MjkuOTIgODA2LjI0IDUyOS45MiA4MDYuMjQgNTI5LjkyIDgwNi4yNCA1MjkuOTIgODA2LjI0IDUyOS45MiA4MDYuMjQgNTI5LjkyIDgwNi4yNCA1MjkuOTIgODA2LjI0VjgwNi4yNEM1MjkuOTIgODA2LjI0IDUyOS45MiA4MDYuMjQgNTI5LjkyIDgwNi4yNFM1MjkuOTIgODA2LjI0IDUyOS45MiA4MDYuMjRDNTE5LjY4IDgxMi42NCA1MDUuNiA4MTIuNjQgNDk1LjM2IDgwNi4yNCA0OTUuMzYgODA2LjI0IDQ5NS4zNiA4MDYuMjQgNDk1LjM2IDgwNi4yNFM0OTUuMzYgODA2LjI0IDQ5NS4zNiA4MDYuMjRWODA2LjI0QzQ5NS4zNiA4MDYuMjQgNDk1LjM2IDgwNi4yNCA0OTUuMzYgODA2LjI0UzQ5NS4zNiA4MDYuMjQgNDk1LjM2IDgwNi4yNCA0OTUuMzYgODA2LjI0IDQ5NS4zNiA4MDYuMjQgNDk1LjM2IDgwNi4yNCA0OTUuMzYgODA2LjI0IDQ5NS4zNiA4MDYuMjQgNDk1LjM2IDgwNi4yNEM0OTQuNzIgODA2LjI0IDQ5NC43MiA4MDUuNiA0OTQuMDggODA1LjYgNDk0LjA4IDgwNS42IDQ5NC4wOCA4MDUuNiA0OTQuMDggODA1LjZWODA1LjZDNDk0LjA4IDgwNS42IDQ5NC4wOCA4MDUuNiA0OTQuMDggODA1LjZTNDk0LjA4IDgwNS42IDQ5NC4wOCA4MDUuNlY4MDUuNkM0OTQuMDggODA1LjYgNDk0LjA4IDgwNS42IDQ5NC4wOCA4MDUuNlM0OTQuMDggODA1LjYgNDk0LjA4IDgwNS42VjgwNS42QzQ5NC4wOCA4MDUuNiA0OTQuMDggODA1LjYgNDk0LjA4IDgwNS42UzQ5NC4wOCA4MDUuNiA0OTQuMDggODA1LjZDNDkyLjE2IDgwNC45NiA0OTEuNTIgODA0LjMyIDQ5MC4yNCA4MDMuNjhMMzE0LjI0IDY0My42OEMzMDEuNDQgNjMxLjUyIDMwMC4xNiA2MTEuNjggMzEyLjMyIDU5OC4yNFMzNDQuMzIgNTg0LjE2IDM1Ny43NiA1OTYuMzJMNDgwIDcwNy42OFYzMzMuMjhIMTA0LjMyTDIxNS42OCA0NTUuNTJDMjI3Ljg0IDQ2OC4zMiAyMjYuNTYgNDg4LjggMjEzLjc2IDUwMC45NlMxODAuNDggNTExLjg0IDE2OC4zMiA0OTkuMDRMOC4zMiAzMjMuMDRDMy4yIDMxNy4yOCAwIDMwOS42IDAgMzAxLjI4UzMuMiAyODUuMjggOC4zMiAyNzkuNTJMMTY4LjMyIDEwMy41MkMxODAuNDggOTAuMDggMjAwLjMyIDg5LjQ0IDIxMy43NiAxMDEuNiAyMjYuNTYgMTEzLjc2IDIyNy44NCAxMzMuNiAyMTUuNjggMTQ3LjA0TDEwNC4zMiAyNjkuMjhINDgwVi0xMDcuNjhMMzU3Ljc2IDMuNjhDMzQ0Ljk2IDE1LjIgMzI0LjQ4IDE0LjU2IDMxMi4zMiAxLjc2UzMwMS40NC0zMS41MiAzMTQuMjQtNDMuNjhMNDkwLjI0LTIwMy42OEM0OTYuNjQtMjA5LjQ0IDUwNC4zMi0yMTIgNTEyLTIxMlM1MjcuMzYtMjA5LjQ0IDUzMy43Ni0yMDMuNjhMNzA5Ljc2LTQzLjY4QzcyMy4yLTMxLjUyIDcyMy44NC0xMS42OCA3MTEuNjggMS43NlM2NzkuNjggMTUuODQgNjY2LjI0IDMuNjhMNTQ0LTEwNy42OFYyNjhIOTE5LjY4TDgwOC4zMiAxNDUuNzZDNzk2LjE2IDEzMi45NiA3OTcuNDQgMTEyLjQ4IDgxMC4yNCAxMDAuMzJTODQzLjUyIDg5LjQ0IDg1NS42OCAxMDIuMjRMMTAxNS42OCAyNzguMjRDMTAxNi4zMiAyNzguODggMTAxNi45NiAyNzkuNTIgMTAxNy42IDI4MC44IDEwMTcuNiAyODAuOCAxMDE3LjYgMjgwLjggMTAxNy42IDI4MC44UzEwMTcuNiAyODAuOCAxMDE3LjYgMjgwLjhWMjgwLjggMjgwLjhDMTAxNy42IDI4MC44IDEwMTcuNiAyODAuOCAxMDE3LjYgMjgwLjhTMTAxNy42IDI4MC44IDEwMTcuNiAyODAuOCAxMDE3LjYgMjgwLjggMTAxNy42IDI4MC44VjI4MC44QzEwMTcuNiAyODAuOCAxMDE3LjYgMjgwLjggMTAxNy42IDI4MC44UzEwMTcuNiAyODAuOCAxMDE3LjYgMjgwLjggMTAxNy42IDI4MC44IDEwMTcuNiAyODAuOCAxMDE4LjI0IDI4MS40NCAxMDE4LjI0IDI4Mi4wOEMxMDE4LjI0IDI4Mi4wOCAxMDE4LjI0IDI4Mi4wOCAxMDE4LjI0IDI4Mi4wOFMxMDE4LjI0IDI4Mi4wOCAxMDE4LjI0IDI4Mi4wOCAxMDE4LjI0IDI4Mi4wOCAxMDE4LjI0IDI4Mi4wOCAxMDE4LjI0IDI4Mi4wOCAxMDE4LjI0IDI4Mi4wOFYyODIuMDhDMTAxOC4yNCAyODIuMDggMTAxOC4yNCAyODIuMDggMTAxOC4yNCAyODIuMDhTMTAxOC4yNCAyODIuMDggMTAxOC4yNCAyODIuMDhDMTAyMi4wOCAyODcuODQgMTAyNCAyOTMuNiAxMDI0IDMwMFMxMDIyLjA4IDMxMi4xNiAxMDE4Ljg4IDMxNy4yOFoiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxOEIiIHVuaWNvZGU9IiYjeEUxOEI7IiBkPSJNMTI4IDY4NEwxMjggMzAwIDEyOC04NCA0MjMuMzYgMTA4IDcwNCAzMDAgNDIzLjM2IDQ5MiAxMjggNjg0Wk04MzIgNjg0SDg5NlYtODRIODMyWiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTE4QyIgdW5pY29kZT0iJiN4RTE4QzsiIGQ9Ik0xMjggNjg0Vi04NEw0MjMuMzYgMTA4IDcwNCAzMDAgNDIzLjM2IDQ5MlpNMzg3Ljg0IDE2MS4yOEwxOTIgMzMuOTJWNTY2LjA4TDM4Ny44NCA0MzguMDggNTkwLjcyIDMwMFpNODMyIDY4NEg4OTZWLTg0SDgzMloiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxOEQiIHVuaWNvZGU9IiYjeEUxOEQ7IiBkPSJNMjYyLjI5NzUgNDkyLjEyNUg1NjkuMzc3NUM1NzAuMzU4NSA0OTIuMDgyNCA1NzEuNTEgNDkyLjAzOTcgNTcyLjY2MTYgNDkyLjAzOTcgNjA4LjY1ODEgNDkyLjAzOTcgNjM4LjA0NCA1MjAuMzU5MyA2MzkuNzUgNTU1LjkyOTRMNjM5Ljc1IDY4NC4wNUM2MzguMDQ0IDcxOS43OTA3IDYwOC42NTgyIDc0OC4xMTAzIDU3Mi42NjE2IDc0OC4xMTAzIDU3MS41MSA3NDguMTEwMyA1NzAuMzU4NSA3NDguMDY3NyA1NjkuMjQ5NSA3NDguMDI1TDU2My4wMjI2IDc0OC4wMjVDNTYxLjMxNjcgNzgzLjc2NTcgNTMxLjkzMDggODEyLjA4NTMgNDk1LjkzNDIgODEyLjA4NTMgNDk0Ljc4MjcgODEyLjA4NTMgNDkzLjYzMTEgODEyLjA0MjcgNDkyLjUyMjIgODEyTDMzOS4xNTI4IDgxMkMzMzguMTcxOSA4MTIuMDQyNyAzMzcuMDIwMyA4MTIuMDg1MyAzMzUuODY4NyA4MTIuMDg1MyAyOTkuODcyMSA4MTIuMDg1MyAyNzAuNDg2MyA3ODMuNzY1NyAyNjguNzgwMyA3NDguMTk1NkwyNjIuMzgyOCA3NDguMDI1QzI2MS41NzI0IDc0OC4wNjc3IDI2MC42NzY4IDc0OC4wNjc3IDI1OS43Mzg1IDc0OC4wNjc3IDIyMy42MTM5IDc0OC4wNjc3IDE5NC4xMDAxIDcxOS44MzM0IDE5Mi4wNTI5IDY4NC4yMjA2TDE5Mi4wNTI5IDU1Ni4xQzE5NC4xMDAxIDUyMC4zMTY2IDIyMy42NTY2IDQ5Mi4wODI0IDI1OS43ODExIDQ5Mi4wODI0IDI2MC43MTk0IDQ5Mi4wODI0IDI2MS42NTc3IDQ5Mi4wODI0IDI2Mi41OTYgNDkyLjEyNVpNNzI5Ljk1NDcgNjg0LjA1SDcwMy43MjVWNDkyLjEyNUM3MDMuNzI1IDQ1Ni44MTA4IDY3NS4wNjQyIDQyOC4xNSA2MzkuNzUgNDI4LjE1SDE5MS45MjVDMTU2LjYxMDggNDI4LjE1IDEyNy45NSA0NTYuODEwOCAxMjcuOTUgNDkyLjEyNVY2ODQuMDVIMTAxLjcyMDJDMTAwLjk1MjYgNjg0LjA5MjcgMTAwLjAxNDIgNjg0LjA5MjcgOTkuMTE4NiA2ODQuMDkyNyA0NS40NjQ5IDY4NC4wOTI3IDEuNzQ4NiA2NDEuNDg1MyAwIDU4OC4yNTgxTDAtMTE1LjYzNzVDMS43NDg3LTE2OS4wMzUzIDQ1LjQ2NDktMjExLjY0MjcgOTkuMTE4Ni0yMTEuNjQyNyAxMDAuMDU2OS0yMTEuNjQyNyAxMDAuOTUyNi0yMTEuNjQyNyAxMDEuODQ4Mi0yMTEuNkw3MjkuOTU0OC0yMTEuNkM3MzAuNzIyNS0yMTEuNjQyNyA3MzEuNjYwOC0yMTEuNjQyNyA3MzIuNTU2NC0yMTEuNjQyNyA3ODYuMjEwMS0yMTEuNjQyNyA4MjkuOTI2NC0xNjkuMDM1MyA4MzEuNjc1LTExNS44MDgxTDgzMS42NzUgNTg4LjA4NzVDODI5LjkyNjMgNjQxLjQ4NTMgNzg2LjIxMDEgNjg0LjA5MjcgNzMyLjU1NjQgNjg0LjA5MjcgNzMxLjYxODEgNjg0LjA5MjcgNzMwLjcyMjUgNjg0LjA5MjcgNzI5LjgyNjggNjg0LjA1Wk02MDcuNzYyNS0xOS42NzVIMjIzLjkxMjVDMjA2LjI1NTQtMTkuNjc1IDE5MS45MjUtNS4zNDQ2IDE5MS45MjUgMTIuMzEyNVMyMDYuMjU1NCA0NC4zIDIyMy45MTI1IDQ0LjNINjA3Ljc2MjVDNjI1LjQxOTYgNDQuMyA2MzkuNzUgMjkuOTY5NiA2MzkuNzUgMTIuMzEyNVM2MjUuNDE5Ni0xOS42NzUgNjA3Ljc2MjUtMTkuNjc1Wk02MDcuNzYyNSAxMDguMjc1SDIyMy45MTI1QzIwNi4yNTU0IDEwOC4yNzUgMTkxLjkyNSAxMjIuNjA1NCAxOTEuOTI1IDE0MC4yNjI1UzIwNi4yNTU0IDE3Mi4yNSAyMjMuOTEyNSAxNzIuMjVINjA3Ljc2MjVDNjI1LjQxOTYgMTcyLjI1IDYzOS43NSAxNTcuOTE5NiA2MzkuNzUgMTQwLjI2MjVTNjI1LjQxOTYgMTA4LjI3NSA2MDcuNzYyNSAxMDguMjc1Wk02MDcuNzYyNSAyMzYuMjI1SDIyMy45MTI1QzIwNi4yNTU0IDIzNi4yMjUgMTkxLjkyNSAyNTAuNTU1NCAxOTEuOTI1IDI2OC4yMTI1UzIwNi4yNTU0IDMwMC4yIDIyMy45MTI1IDMwMC4ySDYwNy43NjI1QzYyNS40MTk2IDMwMC4yIDYzOS43NSAyODUuODY5NiA2MzkuNzUgMjY4LjIxMjVTNjI1LjQxOTYgMjM2LjIyNSA2MDcuNzYyNSAyMzYuMjI1WiIgIGhvcml6LWFkdi14PSI4NTMiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMThFIiB1bmljb2RlPSImI3hFMThFOyIgZD0iTTgyNi4yNCA2ODRINzM2QzczNiA3MTkuMiA3MDQuNjQgNzQ4IDY2NS42IDc0OEg2NTkuMkM2NTkuMiA3ODMuMiA2MjcuODQgODEyIDU4OC44IDgxMkg0MzUuMkMzOTYuMTYgODEyIDM2NC44IDc4My4yIDM2NC44IDc0OEgzNTguNEMzMTkuMzYgNzQ4IDI4OCA3MTkuMiAyODggNjg0SDE5Ny43NkMxNDEuNDQgNjg0IDk2IDY0MS4xMiA5NiA1ODhWLTExNkM5Ni0xNjkuMTIgMTQxLjQ0LTIxMiAxOTcuNzYtMjEySDgyNi4yNEM4ODIuNTYtMjEyIDkyOC0xNjkuMTIgOTI4LTExNlY1ODhDOTI4IDY0MS4xMiA4ODIuNTYgNjg0IDgyNi4yNCA2ODRaTTM1OC40IDY4NEgzOTYuOEM0MTQuNzIgNjg0IDQyOC44IDY5OC4wOCA0MjguOCA3MTZMNDI4LjE2IDc0NS40NEM0MjguOCA3NDYuMDggNDMwLjcyIDc0OCA0MzUuMiA3NDhINTg4LjhDNTkyLjY0IDc0OCA1OTUuMiA3NDYuNzIgNTk1LjIgNzQ3LjM2VjcxNkM1OTUuMiA2OTguMDggNjA5LjI4IDY4NCA2MjcuMiA2ODRINjY1LjZDNjY5LjQ0IDY4NCA2NzIgNjgyLjcyIDY3MiA2ODMuMzZWNjUyLjY0QzY3MiA2NTIuNjQgNjcyIDY1MiA2NzIgNjUyUzY3MiA2NTEuMzYgNjcyIDY1MS4zNkw2NzIuNjQgNTU4LjU2QzY3MiA1NTcuOTIgNjcwLjA4IDU1NiA2NjUuNiA1NTZIMzU4LjRDMzU1Ljg0IDU1NiAzNTMuMjggNTU2LjY0IDM1Mi42NCA1NTYuNjRTMzUyIDU1Ni42NCAzNTIgNTU2TDM1MS4zNiA2NTAuMDhDMzUxLjM2IDY1MC43MiAzNTIgNjUxLjM2IDM1MiA2NTJTMzUxLjM2IDY1My4yOCAzNTEuMzYgNjU0LjU2VjY4Mi4wOEMzNTIgNjgyLjA4IDM1My45MiA2ODQgMzU4LjQgNjg0Wk04NjQtMTE2Qzg2NC0xMzMuOTIgODQ3LjM2LTE0OCA4MjYuMjQtMTQ4SDE5Ny43NkMxNzYuNjQtMTQ4IDE2MC0xMzMuOTIgMTYwLTExNlY1ODhDMTYwIDYwNS45MiAxNzcuMjggNjIwIDE5Ny43NiA2MjBIMjg4VjU1NkMyODggNTIwLjggMzE5LjM2IDQ5MiAzNTguNCA0OTJINjY1LjZDNzA0LjY0IDQ5MiA3MzYgNTIwLjggNzM2IDU1NlY2MjBIODI2LjI0Qzg0Ny4zNiA2MjAgODY0IDYwNS45MiA4NjQgNTg4Vi0xMTZaTTcwNCAzMDBIMzIwQzMwMi4wOCAzMDAgMjg4IDI4NS45MiAyODggMjY4UzMwMi4wOCAyMzYgMzIwIDIzNkg3MDRDNzIxLjkyIDIzNiA3MzYgMjUwLjA4IDczNiAyNjhTNzIxLjkyIDMwMCA3MDQgMzAwWk03MDQgMTcySDMyMEMzMDIuMDggMTcyIDI4OCAxNTcuOTIgMjg4IDE0MFMzMDIuMDggMTA4IDMyMCAxMDhINzA0QzcyMS45MiAxMDggNzM2IDEyMi4wOCA3MzYgMTQwUzcyMS45MiAxNzIgNzA0IDE3MlpNNzA0IDQ0SDMyMEMzMDIuMDggNDQgMjg4IDI5LjkyIDI4OCAxMlMzMDIuMDgtMjAgMzIwLTIwSDcwNEM3MjEuOTItMjAgNzM2LTUuOTIgNzM2IDEyUzcyMS45MiA0NCA3MDQgNDRaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMThGIiB1bmljb2RlPSImI3hFMThGOyIgZD0iTTkwLjI0IDQyOEg4NzIuOTZDOTIxLjc3MDcgNDMxLjQxMzMgOTYwLjA0MjcgNDcxLjg2MTMgOTYwLjA0MjcgNTIxLjIyNjcgOTYwLjA0MjcgNTIyLjIwOCA5NjAuMDQyNyA1MjMuMTg5MyA5NjAgNTI0LjEyOEw5NjAgNTI0VjY1MkM5NjAuMDQyNyA2NTIuODEwNyA5NjAuMDQyNyA2NTMuNzkyIDk2MC4wNDI3IDY1NC43NzMzIDk2MC4wNDI3IDcwNC4xMzg3IDkyMS43NzA3IDc0NC41ODY3IDg3My4yNTg3IDc0OEw4NzIuOTYgNzQ4SDkwLjI0QzQwLjAyMTMgNzQ2LjI1MDctMC4wNDI3IDcwNS4xMi0wLjA0MjcgNjU0LjYwMjctMC4wNDI3IDY1My42NjQtMC4wNDI3IDY1Mi43NjggMCA2NTEuODcyTDAgNjUyVjUyNEMtMC4wNDI3IDUyMy4yMzItMC4wNDI3IDUyMi4yOTMzLTAuMDQyNyA1MjEuMzk3My0wLjA0MjcgNDcwLjkyMjcgNDAuMDIxMyA0MjkuNzQ5MyA5MC4wNjkzIDQyOEw5MC4yNCA0MjhaTTYwLjE2IDY1MkM2MC4xNiA2NTIuMjEzMyA2MC4xNiA2NTIuNDI2NyA2MC4xNiA2NTIuNjgyNyA2MC4xNiA2NjkuNTM2IDczLjQ3MiA2ODMuMzE3MyA5MC4xOTczIDY4NEw5MC4yNCA2ODRIODcyLjk2Qzg4OS43MjggNjgzLjMxNzMgOTAzLjA0IDY2OS41MzYgOTAzLjA0IDY1Mi42ODI3IDkwMy4wNCA2NTIuNDY5MyA5MDMuMDQgNjUyLjIxMzMgOTAzLjA0IDY1Mkw5MDMuMDQgNjUyLjA0MjdWNTI0LjA0MjdDOTAzLjA0IDUyMy44MjkzIDkwMy4wNCA1MjMuNjE2IDkwMy4wNCA1MjMuMzYgOTAzLjA0IDUwNi41MDY3IDg4OS43MjggNDkyLjcyNTMgODczLjAwMjcgNDkyLjA0MjdMODcyLjk2IDQ5Mi4wNDI3SDkwLjI0QzczLjQ3MiA0OTIuNzI1MyA2MC4xNiA1MDYuNTA2NyA2MC4xNiA1MjMuMzYgNjAuMTYgNTIzLjU3MzMgNjAuMTYgNTIzLjgyOTMgNjAuMTYgNTI0LjA0MjdMNjAuMTYgNTI0Wk01MzYuOTYtODRIODguOTZDNzIuMTkyLTgzLjMxNzMgNTguODgtNjkuNTM2IDU4Ljg4LTUyLjY4MjcgNTguODgtNTIuNDY5MyA1OC44OC01Mi4yMTMzIDU4Ljg4LTUyTDU4Ljg4LTUyLjA0MjdWMjY3Ljk1NzNDNTguODggMjY4LjEyOCA1OC44OCAyNjguMzg0IDU4Ljg4IDI2OC41OTczIDU4Ljg4IDI4NS45MiA3Mi45MTczIDI5OS45NTczIDkwLjI0IDI5OS45NTczIDkwLjI0IDI5OS45NTczIDkwLjI0IDI5OS45NTczIDkwLjI0IDI5OS45NTczSDYwMi4yNEM2MTMuMjQ4IDMyNC43NDY3IDYyNy45MjUzIDM0NS45NTIgNjQ1Ljc2IDM2My45NTczTDY0NS43NiAzNjMuOTU3M0g5MC4yNEM0MC4wMjEzIDM2Mi4yMDgtMC4wNDI3IDMyMS4wNzczLTAuMDQyNyAyNzAuNTYtMC4wNDI3IDI2OS42MjEzLTAuMDQyNyAyNjguNzI1MyAwIDI2Ny44MjkzTDAgMjY3Ljk1NzNWLTUyLjA0MjdDLTAuMDQyNy01Mi44MTA3LTAuMDQyNy01My43NDkzLTAuMDQyNy01NC42NDUzLTAuMDQyNy0xMDUuMTIgNDAuMDIxMy0xNDYuMjkzMyA5MC4wNjkzLTE0OC4wNDI3TDkwLjI0LTE0OC4wNDI3SDUwMS4xMkM1MTEuNjE2LTEyMy41NTIgNTIzLjYwNTMtMTAyLjUxNzMgNTM3LjY0MjctODMuMDYxM0w1MzYuOTYtODQuMDQyN1pNMzMwLjg4IDEwOEMzMzAuODggNzIuNjcyIDMwMy45NTczIDQ0IDI3MC43MiA0NFMyMTAuNTYgNzIuNjcyIDIxMC41NiAxMDhDMjEwLjU2IDE0My4zMjggMjM3LjQ4MjcgMTcyIDI3MC43MiAxNzJTMzMwLjg4IDE0My4zMjggMzMwLjg4IDEwOFpNNTQxLjQ0IDEwOEM1NDEuNDQgNzIuNjcyIDUxNC41MTczIDQ0IDQ4MS4yOCA0NFM0MjEuMTIgNzIuNjcyIDQyMS4xMiAxMDhDNDIxLjEyIDE0My4zMjggNDQ4LjA0MjcgMTcyIDQ4MS4yOCAxNzJTNTQxLjQ0IDE0My4zMjggNTQxLjQ0IDEwOFpNODY5LjEyIDk2LjQ4QzkxMi44NTMzIDEyNC4yMTMzIDk0MS40NCAxNzIuMzQxMyA5NDEuNDQgMjI3LjE2OCA5NDEuNDQgMjI3LjU1MiA5NDEuNDQgMjI3Ljk3ODcgOTQxLjQ0IDIyOC4zNjI3VjIyOC4zMkM5NDEuNDgyNyAyMjkuNjg1MyA5NDEuNTI1MyAyMzEuMjY0IDk0MS41MjUzIDIzMi44ODUzIDk0MS41MjUzIDMxMy4wOTg3IDg3Ny45MDkzIDM3OC40NjQgNzk4LjMzNiAzODEuMjhMNzk4LjA4IDM4MS4yOEM3MTguMjkzMyAzNzguNDY0IDY1NC42MzQ3IDMxMy4wOTg3IDY1NC42MzQ3IDIzMi44ODUzIDY1NC42MzQ3IDIzMS4yNjQgNjU0LjY3NzMgMjI5LjY4NTMgNjU0LjcyIDIyOC4xMDY3TDY1NC43MiAyMjguMzJDNjU0LjcyIDIyNy45Nzg3IDY1NC43MiAyMjcuNTk0NyA2NTQuNzIgMjI3LjE2OCA2NTQuNzIgMTcyLjM0MTMgNjgzLjMwNjcgMTI0LjIxMzMgNzI2LjQgOTYuODY0TDcyNy4wNCA5Ni40OEM2MzUuNzMzMyA2MS4zNjUzIDU3Mi4xMTczLTI1LjYzMiA1NzIuMTE3My0xMjcuNDc3MyA1NzIuMTE3My0xMjguODQyNyA1NzIuMTE3My0xMzAuMjA4IDU3Mi4xNi0xMzEuNTczM0w1NzIuMTYtMTMxLjM2QzU3Mi4xNi0xMzEuNTczMyA1NzIuMTYtMTMxLjc4NjcgNTcyLjE2LTEzMiA1NzIuMTYtMTQwLjYxODcgNTc4Ljk4NjctMTQ3LjY1ODcgNTg3LjUyLTE0OEw1ODcuNTYyNy0xNDhIMTAwOC4wNDI3QzEwMTYuNjE4Ny0xNDcuNjU4NyAxMDIzLjQwMjctMTQwLjYxODcgMTAyMy40MDI3LTEzMiAxMDIzLjQwMjctMTMxLjc4NjcgMTAyMy40MDI3LTEzMS41MzA3IDEwMjMuNDAyNy0xMzEuMzE3M0wxMDIzLjQwMjctMTMxLjM2QzEwMjMuNDQ1My0xMzAuMTIyNyAxMDIzLjQ0NTMtMTI4LjY3MiAxMDIzLjQ0NTMtMTI3LjI2NCAxMDIzLjQ0NTMtMjUuNjMyIDk2MC4xMjggNjEuMTUyIDg3MC43ODQgOTUuOTI1M0w4NjkuMTYyNyA5Ni40OFoiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxOTAiIHVuaWNvZGU9IiYjeEUxOTA7IiBkPSJNOTI4IDQyOEg5NkM0Mi45NjUzIDQyOCAwIDQ3MC45NjUzIDAgNTI0VjUyNCA2NTJDMCA3MDUuMDM0NyA0Mi45NjUzIDc0OCA5NiA3NDhWNzQ4SDkyOEM5ODEuMDM0NyA3NDggMTAyNCA3MDUuMDM0NyAxMDI0IDY1MlY2NTIgNTI0QzEwMjQgNDcwLjk2NTMgOTgxLjAzNDcgNDI4IDkyOCA0MjhWNDI4Wk05MjggMzY0SDk2QzQyLjk2NTMgMzY0IDAgMzIxLjAzNDcgMCAyNjhWMjY4LTUyQzAtMTA1LjAzNDcgNDIuOTY1My0xNDggOTYtMTQ4Vi0xNDhIOTI4Qzk4MS4wMzQ3LTE0OCAxMDI0LTEwNS4wMzQ3IDEwMjQtNTJWLTUyIDI2OEMxMDI0IDMyMS4wMzQ3IDk4MS4wMzQ3IDM2NCA5MjggMzY0VjM2NFpNMjg4IDQ0QzI1Mi42NzIgNDQgMjI0IDcyLjY3MiAyMjQgMTA4UzI1Mi42NzIgMTcyIDI4OCAxNzJDMzIzLjMyOCAxNzIgMzUyIDE0My4zMjggMzUyIDEwOFYxMDhDMzUyIDcyLjY3MiAzMjMuMzI4IDQ0IDI4OCA0NFY0NFpNNTEyIDQ0QzQ3Ni42NzIgNDQgNDQ4IDcyLjY3MiA0NDggMTA4UzQ3Ni42NzIgMTcyIDUxMiAxNzJDNTQ3LjMyOCAxNzIgNTc2IDE0My4zMjggNTc2IDEwOFYxMDhDNTc2IDcyLjY3MiA1NDcuMzI4IDQ0IDUxMiA0NFY0NFpNNzM2IDQ0QzcwMC42NzIgNDQgNjcyIDcyLjY3MiA2NzIgMTA4UzcwMC42NzIgMTcyIDczNiAxNzJDNzcxLjMyOCAxNzIgODAwIDE0My4zMjggODAwIDEwOFYxMDhDODAwIDcyLjY3MiA3NzEuMzI4IDQ0IDczNiA0NFY0NFoiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxOTEiIHVuaWNvZGU9IiYjeEUxOTE7IiBkPSJNOTYgNDI4SDkyOEM5ODEuMDM0NyA0MjggMTAyNCA0NzAuOTY1MyAxMDI0IDUyNFY1MjQgNjUyQzEwMjQgNzA1LjAzNDcgOTgxLjAzNDcgNzQ4IDkyOCA3NDhWNzQ4SDk2QzQyLjk2NTMgNzQ4IDAgNzA1LjAzNDcgMCA2NTJWNjUyIDUyNEMwIDQ3MC45NjUzIDQyLjk2NTMgNDI4IDk2IDQyOFY0MjhaTTY0IDY1MkM2NCA2NjkuNjY0IDc4LjMzNiA2ODQgOTYgNjg0VjY4NEg5MjhDOTQ1LjY2NCA2ODQgOTYwIDY2OS42NjQgOTYwIDY1MlY2NTIgNTI0Qzk2MCA1MDYuMzM2IDk0NS42NjQgNDkyIDkyOCA0OTJWNDkySDk2Qzc4LjMzNiA0OTIgNjQgNTA2LjMzNiA2NCA1MjRWNTI0Wk0zNTIgMTA0LjE2QzM1MiA2Ni42OTg3IDMyMy4zMjggMzYuMzIgMjg4IDM2LjMyUzIyNCA2Ni42OTg3IDIyNCAxMDQuMTZDMjI0IDE0MS42MjEzIDI1Mi42NzIgMTcyIDI4OCAxNzJTMzUyIDE0MS42MjEzIDM1MiAxMDQuMTZaTTU3NiAxMDQuMTZDNTc2IDY2LjY5ODcgNTQ3LjMyOCAzNi4zMiA1MTIgMzYuMzJTNDQ4IDY2LjY5ODcgNDQ4IDEwNC4xNkM0NDggMTQxLjYyMTMgNDc2LjY3MiAxNzIgNTEyIDE3MlM1NzYgMTQxLjYyMTMgNTc2IDEwNC4xNlpNODAwIDEwNC4xNkM4MDAgNjYuNjk4NyA3NzEuMzI4IDM2LjMyIDczNiAzNi4zMlM2NzIgNjYuNjk4NyA2NzIgMTA0LjE2QzY3MiAxNDEuNjIxMyA3MDAuNjcyIDE3MiA3MzYgMTcyUzgwMCAxNDEuNjIxMyA4MDAgMTA0LjE2Wk04OTYgMzAwQzkzMS4zMjggMzAwIDk2MCAyNzEuMzI4IDk2MCAyMzZWMjM2LTIwQzk2MC01NS4zMjggOTMxLjMyOC04NCA4OTYtODRWLTg0SDEyOEM5Mi42NzItODQgNjQtNTUuMzI4IDY0LTIwVi0yMCAyMzZDNjQgMjcxLjMyOCA5Mi42NzIgMzAwIDEyOCAzMDBWMzAwSDg5NlpNODk2IDM2NEgxMjhDNTcuMzAxMyAzNjQgMCAzMDYuNjk4NyAwIDIzNlYyMzYtMjBDMC05MC42OTg3IDU3LjMwMTMtMTQ4IDEyOC0xNDhWLTE0OEg4OTZDOTY2LjY5ODctMTQ4IDEwMjQtOTAuNjk4NyAxMDI0LTIwVi0yMCAyMzZDMTAyNCAzMDYuNjk4NyA5NjYuNjk4NyAzNjQgODk2IDM2NFYzNjRaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMTkyIiB1bmljb2RlPSImI3hFMTkyOyIgZD0iTTQ5Ny45MiA4MTJMMjMuNjggNjIwQzExLjUyIDYxMy43MjggMy4zMjggNjAxLjI2OTMgMy4zMjggNTg2Ljg5MDcgMy4zMjggNTc0LjA0OCA5LjgxMzMgNTYyLjc4NCAxOS43MTIgNTU2LjA4NTNMMTkuODQgNTU2IDQ5NC4wOCAzMDMuMkM0OTkuMiAzMDAuNDY5MyA1MDUuMjU4NyAyOTguODQ4IDUxMS42NTg3IDI5OC44NDhTNTI0LjE2IDMwMC40NjkzIDUyOS40NTA3IDMwMy4yODUzTDUyOS4yMzczIDMwMy4yIDEwMDQuMTE3MyA1NTZDMTAxNC4xNDQgNTYyLjc0MTMgMTAyMC42MjkzIDU3NC4wNDggMTAyMC42MjkzIDU4Ni44OTA3IDEwMjAuNjI5MyA2MDEuMjY5MyAxMDEyLjQzNzMgNjEzLjc3MDcgMTAwMC40OTA3IDYxOS45MTQ3TDEwMDAuMjc3MyA2MjAgNTI2LjAzNzMgODEyQzUyMS44NTYgODEzLjcwNjcgNTE3LjAzNDcgODE0LjczMDcgNTExLjk1NzMgODE0LjczMDdTNTAyLjA1ODcgODEzLjc0OTMgNDk3LjYyMTMgODExLjkxNDdMNDk3Ljg3NzMgODEyWk01MjQuOCA3NDAuOTZWNzQwLjk2Wk01MTIgODEyQzUwOS44NjY3IDgxMi40MjY3IDUwNy40MzQ3IDgxMi42ODI3IDUwNC45NiA4MTIuNjgyN1M1MDAuMDUzMyA4MTIuNDI2NyA0OTcuNjY0IDgxMkw0OTcuOTIgODEyLjA0MjcgMjMuNjggNjIwLjA0MjdDMTEuNTIgNjEzLjc3MDcgMy4zMjggNjAxLjMxMiAzLjMyOCA1ODYuOTMzMyAzLjMyOCA1NzQuMDkwNyA5LjgxMzMgNTYyLjgyNjcgMTkuNzEyIDU1Ni4xMjhMMTkuODQgNTU2LjA0MjcgNDk0LjA4IDMwMy4yNDI3QzQ5OS4yIDMwMC41MTIgNTA1LjI1ODcgMjk4Ljg5MDcgNTExLjY1ODcgMjk4Ljg5MDdTNTI0LjE2IDMwMC41MTIgNTI5LjQ1MDcgMzAzLjMyOEw1MjkuMjM3MyAzMDMuMjQyNyAxMDA0LjExNzMgNTU2LjA0MjdDMTAxNC4xNDQgNTYyLjc4NCAxMDIwLjYyOTMgNTc0LjA5MDcgMTAyMC42MjkzIDU4Ni45MzMzIDEwMjAuNjI5MyA2MDEuMzEyIDEwMTIuNDM3MyA2MTMuODEzMyAxMDAwLjQ5MDcgNjE5Ljk1NzNMMTAwMC4yNzczIDYyMC4wNDI3IDUyNi4wMzczIDgxMi4wNDI3QzUyMy45MDQgODEyLjQ2OTMgNTIxLjQ3MiA4MTIuNzI1MyA1MTguOTk3MyA4MTIuNzI1M1M1MTQuMDkwNyA4MTIuNDY5MyA1MTEuNzAxMyA4MTIuMDQyN0w1MTEuOTU3MyA4MTIuMDg1M1pNNTEyIDQ0QzQ5OS4zMjggNDQuMDQyNyA0ODcuNDI0IDQ3LjMyOCA0NzcuMDk4NyA1My4xMzA3TDQ3Ny40NCA1Mi45NiAxOS4yIDMwMy4yQzcuODUwNyAzMDkuNTU3MyAwLjI5ODcgMzIxLjUwNCAwLjI5ODcgMzM1LjIgMC4yOTg3IDM1NS4zODEzIDE2LjY0IDM3MS43MjI3IDM2LjgyMTMgMzcxLjcyMjcgNDMuMjY0IDM3MS43MjI3IDQ5LjMyMjcgMzcwLjA1ODcgNTQuNjEzMyAzNjcuMTE0N0w1NC40NDI3IDM2Ny4yIDUxMi4wNDI3IDExNS42OCA5NjkuNjQyNyAzNjcuODRDOTc0LjcyIDM3MC42OTg3IDk4MC43Nzg3IDM3Mi4zNjI3IDk4Ny4yNjQgMzcyLjM2MjcgMTAwNy40NDUzIDM3Mi4zNjI3IDEwMjMuNzg2NyAzNTYuMDIxMyAxMDIzLjc4NjcgMzM1Ljg0IDEwMjMuNzg2NyAzMjIuMTQ0IDEwMTYuMjM0NyAzMTAuMTk3MyAxMDA1LjA1NiAzMDMuOTI1M0wxMDA0Ljg4NTMgMzAzLjg0IDU0Ni42NDUzIDUxLjA0QzUzNy42IDQ2LjU2IDUyNi45MzMzIDQzLjkxNDcgNTE1LjYyNjcgNDMuOTE0NyA1MTQuMzg5MyA0My45MTQ3IDUxMy4xNTIgNDMuOTU3MyA1MTEuOTE0NyA0NEw1MTIuMDg1MyA0NFpNNTEyLTIxMkM0OTkuMzI4LTIxMS45NTczIDQ4Ny40MjQtMjA4LjY3MiA0NzcuMDk4Ny0yMDIuODY5M0w0NzcuNDQtMjAzLjA0IDE5LjIgNDkuMTJDNy44NTA3IDU1LjQ3NzMgMC4yOTg3IDY3LjQyNCAwLjI5ODcgODEuMTIgMC4yOTg3IDEwMS4zMDEzIDE2LjY0IDExNy42NDI3IDM2LjgyMTMgMTE3LjY0MjcgNDMuMjY0IDExNy42NDI3IDQ5LjMyMjcgMTE1Ljk3ODcgNTQuNjEzMyAxMTMuMDM0N0w1NC40NDI3IDExMy4xMiA1MTIuMDQyNy0xMzkuMDQgOTY5LjY0MjcgMTEzLjEyQzk3NC43MiAxMTUuOTc4NyA5ODAuNzc4NyAxMTcuNjQyNyA5ODcuMjY0IDExNy42NDI3IDEwMDcuNDQ1MyAxMTcuNjQyNyAxMDIzLjc4NjcgMTAxLjMwMTMgMTAyMy43ODY3IDgxLjEyIDEwMjMuNzg2NyA2Ny40MjQgMTAxNi4yMzQ3IDU1LjQ3NzMgMTAwNS4wNTYgNDkuMjA1M0wxMDA0Ljg4NTMgNDkuMTIgNTQ2LjY0NTMtMjAzLjA0QzUzNi42NjEzLTIwOC42MjkzIDUyNC43NTczLTIxMS45NTczIDUxMi4wODUzLTIxMkg1MTIuMDg1M1oiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxOTMiIHVuaWNvZGU9IiYjeEUxOTM7IiBkPSJNODY0IDYyMEgxNjBDNzEuNjM3MyA2MjAgMCA1NDguMzYyNyAwIDQ2MFYxNDBDMCA1MS42MzczIDcxLjYzNzMtMjAgMTYwLTIwSDg2NEM5NTIuMzYyNy0yMCAxMDI0IDUxLjYzNzMgMTAyNCAxNDBWNDYwQzEwMjQgNTQ4LjM2MjcgOTUyLjM2MjcgNjIwIDg2NCA2MjBaTTI1NiAyMzZDMjIwLjY3MiAyMzYgMTkyIDI2NC42NzIgMTkyIDMwMFMyMjAuNjcyIDM2NCAyNTYgMzY0QzI5MS4zMjggMzY0IDMyMCAzMzUuMzI4IDMyMCAzMDBTMjkxLjMyOCAyMzYgMjU2IDIzNlpNNTEyIDIzNkM0NzYuNjcyIDIzNiA0NDggMjY0LjY3MiA0NDggMzAwUzQ3Ni42NzIgMzY0IDUxMiAzNjRDNTQ3LjMyOCAzNjQgNTc2IDMzNS4zMjggNTc2IDMwMFM1NDcuMzI4IDIzNiA1MTIgMjM2Wk03NjggMjM2QzczMi42NzIgMjM2IDcwNCAyNjQuNjcyIDcwNCAzMDBTNzMyLjY3MiAzNjQgNzY4IDM2NEM4MDMuMzI4IDM2NCA4MzIgMzM1LjMyOCA4MzIgMzAwUzgwMy4zMjggMjM2IDc2OCAyMzZaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMTk0IiB1bmljb2RlPSImI3hFMTk0OyIgZD0iTTg2NC0yMEgxNjBDNzEuNjgtMjAgMCA1MS42OCAwIDE0MFY0NjBDMCA1NDguMzIgNzEuNjggNjIwIDE2MCA2MjBIODY0Qzk1Mi4zMiA2MjAgMTAyNCA1NDguMzIgMTAyNCA0NjBWMTQwQzEwMjQgNTEuNjggOTUyLjMyLTIwIDg2NC0yMFpNMTYwIDU1NkMxMDYuODggNTU2IDY0IDUxMy4xMiA2NCA0NjBWMTQwQzY0IDg2Ljg4IDEwNi44OCA0NCAxNjAgNDRIODY0QzkxNy4xMiA0NCA5NjAgODYuODggOTYwIDE0MFY0NjBDOTYwIDUxMy4xMiA5MTcuMTIgNTU2IDg2NCA1NTZIMTYwWk0yNTYgMzY0QzIyMC44IDM2NCAxOTIgMzM1LjIgMTkyIDMwMFMyMjAuOCAyMzYgMjU2IDIzNiAzMjAgMjY0LjggMzIwIDMwMCAyOTEuMiAzNjQgMjU2IDM2NFpNNTEyIDM2NEM0NzYuOCAzNjQgNDQ4IDMzNS4yIDQ0OCAzMDBTNDc2LjggMjM2IDUxMiAyMzYgNTc2IDI2NC44IDU3NiAzMDAgNTQ3LjIgMzY0IDUxMiAzNjRaTTc2OCAzNjRDNzMyLjggMzY0IDcwNCAzMzUuMiA3MDQgMzAwUzczMi44IDIzNiA3NjggMjM2IDgzMiAyNjQuOCA4MzIgMzAwIDgwMy4yIDM2NCA3NjggMzY0WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTE5NSIgdW5pY29kZT0iJiN4RTE5NTsiIGQ9Ik03NjggNjUyVi01MkM3NjgtNjkuOTIgNzUzLjkyLTg0IDczNi04NFM3MDQtNjkuOTIgNzA0LTUyVjY1MkM3MDQgNjY5LjkyIDcxOC4wOCA2ODQgNzM2IDY4NFM3NjggNjY5LjkyIDc2OCA2NTJaTTI4OCA2ODRDMjcwLjA4IDY4NCAyNTYgNjY5LjkyIDI1NiA2NTJWLTUyQzI1Ni02OS45MiAyNzAuMDgtODQgMjg4LTg0UzMyMC02OS45MiAzMjAtNTJWNjUyQzMyMCA2NjkuOTIgMzA1LjkyIDY4NCAyODggNjg0WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTE5NiIgdW5pY29kZT0iJiN4RTE5NjsiIGQ9Ik05NjAgMjUyVjYzNkM5NjAgNjUzLjYgOTQ1LjYgNjY4IDkyOCA2NjhIOTZDNzguNCA2NjggNjQgNjUzLjYgNjQgNjM2VjI1Mkg5NjBaTTY0IDE4OFY5MkM2NCA3NC40IDc4LjQgNjAgOTYgNjBINDE2Vi00SDM1MkMzMzQuNC00IDMyMC0xOC40IDMyMC0zNlMzMzQuNC02OCAzNTItNjhINjcyQzY4OS42LTY4IDcwNC01My42IDcwNC0zNlM2ODkuNi00IDY3Mi00SDYwOFY2MEg5MjhDOTQ1LjYgNjAgOTYwIDc0LjQgOTYwIDkyVjE4OEg2NFoiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxOTciIHVuaWNvZGU9IiYjeEUxOTc7IiBkPSJNOTI4IDY2OEg5NkM3OC40IDY2OCA2NCA2NTMuNiA2NCA2MzZWMjUyIDE4OCA5MkM2NCA3NC40IDc4LjQgNjAgOTYgNjBINDE2Vi00SDM1MkMzMzQuNC00IDMyMC0xOC40IDMyMC0zNlMzMzQuNC02OCAzNTItNjhINjcyQzY4OS42LTY4IDcwNC01My42IDcwNC0zNlM2ODkuNi00IDY3Mi00SDYwOFY2MEg5MjhDOTQ1LjYgNjAgOTYwIDc0LjQgOTYwIDkyVjE4OCAyNTIgNjM2Qzk2MCA2NTMuNiA5NDUuNiA2NjggOTI4IDY2OFpNODk2IDEyNEgxMjhWMTg4SDg5NlYxMjRaTTEyOCAyNTJWNjA0SDg5NlYyNTJIMTI4WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTE5OCIgdW5pY29kZT0iJiN4RTE5ODsiIGQ9Ik04NjQgMjM2SDQ4MEM0NjIuMzM2IDIzNiA0NDggMjUwLjMzNiA0NDggMjY4VjY1MkM0NDggNjUyIDQ0OCA2NTIuMDQyNyA0NDggNjUyLjA0MjcgNDQ4IDY2OS43MDY3IDQzMy42NjQgNjg0LjA0MjcgNDE2IDY4NC4wNDI3IDQxNS4zMTczIDY4NC4wNDI3IDQxNC42MzQ3IDY4NC4wNDI3IDQxMy45OTQ3IDY4NCAxODEuMzc2IDY2Ni4yMDgtMC43MjUzIDQ3Mi45NzA3LTAuNzI1MyAyMzcuMjM3My0wLjcyNTMgMTg3LjgyOTMgNy4yNTMzIDE0MC4yOTg3IDIyLjAxNiA5NS44ODI3IDY1LjYyMTMtMzkuNDEzMyAxNzIuNTQ0LTE0Ni4zMzYgMzA3Ljg4MjctMTg5Ljk4NCAzNTIuMjk4Ny0yMDQuNzA0IDM5OS44MjkzLTIxMi43MjUzIDQ0OS4xOTQ3LTIxMi43MjUzIDY4NC45MjgtMjEyLjcyNTMgODc4LjE2NTMtMzAuNjI0IDg5NS44NzIgMjAwLjU0NCA4OTYuMDQyNyAyMDIuODA1MyA4OTYuMDQyNyAyMDMuNjU4NyA4OTYuMDQyNyAyMDQuNTEyIDg5Ni4wNDI3IDIxMi45NiA4OTIuODQyNyAyMjAuNjQgODg3LjU5NDcgMjI2LjQgODgxLjc5MiAyMzIuMjg4IDg3My43MjggMjM2IDg2NC43NjggMjM2IDg2NC40NjkzIDIzNiA4NjQuMjEzMyAyMzYgODYzLjkxNDcgMjM2Wk01NzYgODEySDU0MS40NEM1MjQuODg1MyA4MTAuNjc3MyA1MTEuOTE0NyA3OTYuODk2IDUxMS45MTQ3IDc4MC4wODUzIDUxMS45MTQ3IDc3OS4zNiA1MTEuOTU3MyA3NzguNjc3MyA1MTIgNzc3Ljk1Mkw1MTIgMzMwLjAzNzNDNTEyIDMxMi4zNzMzIDUyNi4zMzYgMjk4LjAzNzMgNTQ0IDI5OC4wMzczSDk5MkM5OTIuMDQyNyAyOTguMDM3MyA5OTIuMDg1MyAyOTguMDM3MyA5OTIuMDg1MyAyOTguMDM3MyAxMDA4Ljg1MzMgMjk4LjAzNzMgMTAyMi42MzQ3IDMxMC45MjI3IDEwMjMuOTU3MyAzMjcuMzQ5MyAxMDIzLjk1NzMgMzM4Ljk5NzMgMTAyMy45NTczIDM1MC41MTczIDEwMjMuOTU3MyAzNjIuMDM3MyAxMDIzLjk1NzMgMzYyLjU5MiAxMDIzLjk1NzMgMzYzLjI3NDcgMTAyMy45NTczIDM2My45NTczIDEwMjMuOTU3MyA2MTEuMzgxMyA4MjMuMzgxMyA4MTEuOTU3MyA1NzUuOTU3MyA4MTEuOTU3MyA1NzUuOTU3MyA4MTEuOTU3MyA1NzUuOTU3MyA4MTEuOTU3MyA1NzUuOTU3MyA4MTEuOTU3M1oiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxOTkiIHVuaWNvZGU9IiYjeEUxOTk7IiBkPSJNNDQ4LjY0LTIxMkMyMDEuNi0yMTIgMC0xMC40IDAgMjM2LjY0IDAgNDY5LjYgMTgxLjc2IDY2Ni4wOCA0MTQuMDggNjg0IDQyMy4wNCA2ODQuNjQgNDMyIDY4MS40NCA0MzguNCA2NzUuNjhTNDQ4LjY0IDY2MC45NiA0NDguNjQgNjUyVjIzNi42NEg4NjRDODcyLjk2IDIzNi42NCA4ODEuMjggMjMyLjggODg3LjY4IDIyNi40IDg5My40NCAyMjAgODk2LjY0IDIxMS4wNCA4OTYgMjAyLjA4IDg3OC4wOC0zMC4yNCA2ODEuNi0yMTIgNDQ4LjY0LTIxMlpNMzg0LjY0IDYxNi4xNkMyMDIuMjQgNTg0LjggNjQgNDI0LjggNjQgMjM2LjY0IDY0IDI0LjggMjM2LjgtMTQ4IDQ0OC42NC0xNDggNjM2LjgtMTQ4IDc5Ni44LTkuNzYgODI3LjUyIDE3Mi42NEg0MTYuNjRDMzk4LjcyIDE3Mi42NCAzODQuNjQgMTg2LjcyIDM4NC42NCAyMDQuNjRWNjE2LjE2Wk05OTAuMDggMzAwSDU0NEM1MjYuMDggMzAwIDUxMiAzMTQuMDggNTEyIDMzMlY3NzguMDhDNTEyIDc5NC43MiA1MjQuOCA4MDguOCA1NDEuNDQgODEwLjA4IDU1Mi45NiA4MTEuMzYgNTY0LjQ4IDgxMiA1NzYgODEyIDgyMy4wNCA4MTIgMTAyNCA2MTEuMDQgMTAyNCAzNjQgMTAyNCAzNTIuNDggMTAyMy4zNiAzNDAuOTYgMTAyMi4wOCAzMjkuNDQgMTAyMC44IDMxMi44IDEwMDcuMzYgMzAwIDk5MC4wOCAzMDBaTTU3NiAzNjRIOTYwQzk2MCA1NzUuODQgNzg3Ljg0IDc0OCA1NzYgNzQ4VjM2NFoiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxOUEiIHVuaWNvZGU9IiYjeEUxOUE7IiBkPSJNMzkzLjYgNjg0SDY0OS42QzY4NC44IDY4NCA3MTMuNiA2NTUuMiA3MTMuNiA2MjBWNTU2QzcxMy42IDUyMC44IDY4NC44IDQ5MiA2NDkuNiA0OTJIMzkzLjZDMzU4LjQgNDkyIDMyOS42IDUyMC44IDMyOS42IDU1NlY2MjBDMzI5LjYgNjU1LjIgMzU4LjQgNjg0IDM5My42IDY4NFpNMzkzLjYgMzk2SDY0OS42QzY4NC44IDM5NiA3MTMuNiAzNjcuMiA3MTMuNiAzMzJWMjY4QzcxMy42IDIzMi44IDY4NC44IDIwNCA2NDkuNiAyMDRIMzkzLjZDMzU4LjQgMjA0IDMyOS42IDIzMi44IDMyOS42IDI2OFYzMzJDMzI5LjYgMzY3LjIgMzU4LjQgMzk2IDM5My42IDM5NlpNMzkzLjYgMTA4SDY0OS42QzY4NC44IDEwOCA3MTMuNiA3OS4yIDcxMy42IDQ0Vi0yMEM3MTMuNi01NS4yIDY4NC44LTg0IDY0OS42LTg0SDM5My42QzM1OC40LTg0IDMyOS42LTU1LjIgMzI5LjYtMjBWNDRDMzI5LjYgNzkuMiAzNTguNCAxMDggMzkzLjYgMTA4Wk0yODAgMjhIMTkyQzEyMS42IDI4IDY0IDg1LjYgNjQgMTU2UzEyMS42IDI4NCAxOTIgMjg0SDI4MFYyMjBIMTkyQzE1Ni44IDIyMCAxMjggMTkxLjIgMTI4IDE1NlMxNTYuOCA5MiAxOTIgOTJIMjgwVjI4Wk04MzIgMzE2SDc0NFYzODBIODMyQzg2Ny4yIDM4MCA4OTYgNDA4LjggODk2IDQ0NFM4NjcuMiA1MDggODMyIDUwOEg3NDRWNTcySDgzMkM5MDIuNCA1NzIgOTYwIDUxNC40IDk2MCA0NDRTOTAyLjQgMzE2IDgzMiAzMTZaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMTlCIiB1bmljb2RlPSImI3hFMTlCOyIgZD0iTTY0OS42IDYyMFY1NTZIMzkzLjZWNjIwSDY0OS42TTY0OS42IDY4NEgzOTMuNkMzNTguNCA2ODQgMzI5LjYgNjU1LjIgMzI5LjYgNjIwVjU1NkMzMjkuNiA1MjAuOCAzNTguNCA0OTIgMzkzLjYgNDkySDY0OS42QzY4NC44IDQ5MiA3MTMuNiA1MjAuOCA3MTMuNiA1NTZWNjIwQzcxMy42IDY1NS4yIDY4NC44IDY4NCA2NDkuNiA2ODRMNjQ5LjYgNjg0Wk02NDkuNiAzMzJWMjY4SDM5My42VjMzMkg2NDkuNk02NDkuNiAzOTZIMzkzLjZDMzU4LjQgMzk2IDMyOS42IDM2Ny4yIDMyOS42IDMzMlYyNjhDMzI5LjYgMjMyLjggMzU4LjQgMjA0IDM5My42IDIwNEg2NDkuNkM2ODQuOCAyMDQgNzEzLjYgMjMyLjggNzEzLjYgMjY4VjMzMkM3MTMuNiAzNjcuMiA2ODQuOCAzOTYgNjQ5LjYgMzk2TDY0OS42IDM5NlpNNjQ5LjYgNDRWLTIwSDM5My42VjQ0SDY0OS42TTY0OS42IDEwOEgzOTMuNkMzNTguNCAxMDggMzI5LjYgNzkuMiAzMjkuNiA0NFYtMjBDMzI5LjYtNTUuMiAzNTguNC04NCAzOTMuNi04NEg2NDkuNkM2ODQuOC04NCA3MTMuNi01NS4yIDcxMy42LTIwVjQ0QzcxMy42IDc5LjIgNjg0LjggMTA4IDY0OS42IDEwOEw2NDkuNiAxMDhaTTI4MCAyOEgxOTJDMTIxLjYgMjggNjQgODUuNiA2NCAxNTZTMTIxLjYgMjg0IDE5MiAyODRIMjgwVjIyMEgxOTJDMTU2LjggMjIwIDEyOCAxOTEuMiAxMjggMTU2UzE1Ni44IDkyIDE5MiA5MkgyODBWMjhaTTgzMiAzMTZINzQ0VjM4MEg4MzJDODY3LjIgMzgwIDg5NiA0MDguOCA4OTYgNDQ0Uzg2Ny4yIDUwOCA4MzIgNTA4SDc0NFY1NzJIODMyQzkwMi40IDU3MiA5NjAgNTE0LjQgOTYwIDQ0NFM5MDIuNCAzMTYgODMyIDMxNloiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxOUMiIHVuaWNvZGU9IiYjeEUxOUM7IiBkPSJNNTEyIDc0OEMyNjQgNzQ4IDY0IDU0OCA2NCAzMDBTMjY0LTE0OCA1MTItMTQ4IDk2MCA1MiA5NjAgMzAwIDc2MCA3NDggNTEyIDc0OFpNNjY4LjggMjg3LjJMNDU0LjQgMTA4QzQ0Ni40IDEwMS42IDQzNi44IDEwMy4yIDQzMC40IDEwOS42IDQyNy4yIDExMi44IDQyNy4yIDExNiA0MjcuMiAxMjAuOFY0NzcuNkM0MjcuMiA0ODcuMiA0MzUuMiA0OTUuMiA0NDQuOCA0OTUuMiA0NDkuNiA0OTUuMiA0NTIuOCA0OTMuNiA0NTYgNDkyTDY3MC40IDMxMi44QzY3OC40IDMwNi40IDY3OC40IDI5NS4yIDY3MiAyODguOCA2NzAuNCAyODcuMiA2NjguOCAyODcuMiA2NjguOCAyODcuMloiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxOUQiIHVuaWNvZGU9IiYjeEUxOUQ7IiBkPSJNODI3Ljk4OTMgMzI5LjI2OTNMMjQyLjg1ODcgODAzLjk3ODdDMjM2LjYyOTMgODA5LjM5NzMgMjI4LjQzNzMgODEyLjcyNTMgMjE5LjQ3NzMgODEyLjc2OCAxOTkuMjUzMyA4MTIuNzY4IDE4Mi45MTIgNzk2LjM4NCAxODIuOTEyIDc3Ni4yMDI3Vi0xNzQuNjY2N0MxODIuOTEyLTE5NC44NDggMTk5LjI5Ni0yMTEuMjMyIDIxOS40NzczLTIxMS4yMzIgMjE5LjQ3NzMtMjExLjIzMiAyMTkuNTItMjExLjIzMiAyMTkuNTItMjExLjIzMiAyMjguMTM4Ny0yMTEuMjMyIDIzNi4wMzItMjA4LjIwMjcgMjQyLjIxODctMjAzLjEyNTNMODI3LjMwNjcgMjcxLjU0MTNDODM2LjE4MTMgMjc4LjI4MjcgODQxLjgxMzMgMjg4LjgyMTMgODQxLjgxMzMgMzAwLjcyNTMgODQxLjgxMzMgMzEyLjI4OCA4MzYuNDggMzIyLjU3MDcgODI4LjExNzMgMzI5LjI2OTNaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMTlFIiB1bmljb2RlPSImI3hFMTlFOyIgZD0iTTUxMiA2ODRDNzI0LjggNjg0IDg5NiA1MTIuOCA4OTYgMzAwUzcyNC44LTg0IDUxMi04NCAxMjggODcuMiAxMjggMzAwIDI5OS4yIDY4NCA1MTIgNjg0TTUxMiA3NDhDMjY0IDc0OCA2NCA1NDggNjQgMzAwUzI2NC0xNDggNTEyLTE0OCA5NjAgNTIgOTYwIDMwMCA3NjAgNzQ4IDUxMiA3NDhaTTQyNS42IDQ3Ny42VjEyMC44QzQyNS42IDExMS4yIDQzMy42IDEwMy4yIDQ0My4yIDEwMy4yIDQ0OCAxMDMuMiA0NTEuMiAxMDQuOCA0NTQuNCAxMDYuNEw2NjguOCAyODUuNkM2NzYuOCAyOTIgNjc2LjggMzAzLjIgNjcwLjQgMzA5LjYgNjcwLjQgMzA5LjYgNjY4LjggMzExLjIgNjY4LjggMzExLjJMNDU0LjQgNDkyQzQ0Ni40IDQ5OC40IDQzNi44IDQ5Ni44IDQzMC40IDQ5MC40IDQyNy4yIDQ4Ny4yIDQyNS42IDQ4Mi40IDQyNS42IDQ3Ny42WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTE5RiIgdW5pY29kZT0iJiN4RTE5RjsiIGQ9Ik03ODguNDggMzI0Ljk2TDI3Ni40OCA3NDAuMzJDMjcwLjA4IDc0NC44IDI2My4wNCA3NDcuMzYgMjU2IDc0Ny4zNiAyMzkuMzYgNzQ3LjM2IDIyNCA3MzQuNTYgMjI0IDcxNS4zNlYtMTE0LjcyQzIyNC0xMzMuOTIgMjM5LjM2LTE0Ni43MiAyNTYtMTQ2LjcyIDI2My4wNC0xNDYuNzIgMjcwLjA4LTE0NC44IDI3NS44NC0xMzkuNjhMNzg3Ljg0IDI3NS42OEM4MDMuODQgMjg3Ljg0IDgwMy44NCAzMTIuMTYgNzg4LjQ4IDMyNC45NlpNMjg4LTQ4LjE2VjY0OC4xNkw3MTcuNDQgMzAwIDI4OC00OC4xNloiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxQTAiIHVuaWNvZGU9IiYjeEUxQTA7IiBkPSJNNTEyIDgxMkMyMjkuNzYgODEyIDAgNTgyLjI0IDAgMzAwUzIyOS43Ni0yMTIgNTEyLTIxMiAxMDI0IDE3Ljc2IDEwMjQgMzAwIDc5NC4yNCA4MTIgNTEyIDgxMlpNNTEyLTE0OEMyNjQuOTYtMTQ4IDY0IDUyLjk2IDY0IDMwMFMyNjQuOTYgNzQ4IDUxMiA3NDhDNzU5LjA0IDc0OCA5NjAgNTQ3LjA0IDk2MCAzMDBTNzU5LjA0LTE0OCA1MTItMTQ4Wk00MzUuMiA1MzQuMjRDNDI4LjggNTM4LjcyIDQyMS43NiA1NDEuMjggNDE1LjM2IDU0MS4yOCAzOTguNzIgNTQxLjI4IDM4My4zNiA1MjguNDggMzgzLjM2IDUwOS4yOFY5MC43MkMzODMuMzYgNzEuNTIgMzk4LjcyIDU4LjcyIDQxNS4zNiA1OC43MiA0MjIuNCA1OC43MiA0MjkuNDQgNjAuNjQgNDM1LjIgNjUuNzZMNjkzLjEyIDI3NS4wNEM3MDkuMTIgMjg3Ljg0IDcwOS4xMiAzMTIuMTYgNjkzLjEyIDMyNC45Nkw0MzUuMiA1MzQuMjRaTTQ0Ni43MiAxNTcuOTJWNDQyLjA4TDYyMi4wOCAzMDAgNDQ2LjcyIDE1Ny45MloiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxQTEiIHVuaWNvZGU9IiYjeEUxQTE7IiBkPSJNNTEyIDc0OEMyNjQgNzQ4IDY0IDU0OCA2NCAzMDBTMjY0LTE0OCA1MTItMTQ4IDk2MCA1MiA5NjAgMzAwIDc2MCA3NDggNTEyIDc0OFpNNzM2IDI2OEg1NDRWNzZINDgwVjI2OEgyODhWMzMySDQ4MFY1MjRINTQ0VjMzMkg3MzZWMjY4WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTFBMiIgdW5pY29kZT0iJiN4RTFBMjsiIGQ9Ik01MTIgNjg0QzcyNC44IDY4NCA4OTYgNTEyLjggODk2IDMwMFM3MjQuOC04NCA1MTItODQgMTI4IDg3LjIgMTI4IDMwMCAyOTkuMiA2ODQgNTEyIDY4NE01MTIgNzQ4QzI2NCA3NDggNjQgNTQ4IDY0IDMwMFMyNjQtMTQ4IDUxMi0xNDggOTYwIDUyIDk2MCAzMDAgNzYwIDc0OCA1MTIgNzQ4Wk03MzYgMzMyTDU0NCAzMzIgNTQ0IDUyNCA0ODAgNTI0IDQ4MCAzMzIgMjg4IDMzMiAyODggMjY4IDQ4MCAyNjggNDgwIDc2IDU0NCA3NiA1NDQgMjY4IDczNiAyNjhaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMUEzIiB1bmljb2RlPSImI3hFMUEzOyIgZD0iTTg2NCA2ODRIMTYwQTMyIDMyIDAgMCAxIDEyOCA2NTJWLTUyQTMyIDMyIDAgMCAxIDE2MC04NEg4NjRBMzIgMzIgMCAwIDEgODk2LTUyVjY1MkEzMiAzMiAwIDAgMSA4NjQgNjg0Wk03MDQgMjY4SDU0NFYxMDhINDgwVjI2OEgzMjBWMzMySDQ4MFY0OTJINTQ0VjMzMkg3MDRaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMUE0IiB1bmljb2RlPSImI3hFMUE0OyIgZD0iTTg2NCA2ODRIMTYwQTMyIDMyIDAgMCAxIDEyOCA2NTJWLTUyQTMyIDMyIDAgMCAxIDE2MC04NEg4NjRBMzIgMzIgMCAwIDEgODk2LTUyVjY1MkEzMiAzMiAwIDAgMSA4NjQgNjg0Wk0xOTItMjBWNjIwSDgzMlYtMjBaTTU0NCA0OTJMNDgwIDQ5MiA0ODAgMzMyIDMyMCAzMzIgMzIwIDI2OCA0ODAgMjY4IDQ4MCAxMDggNTQ0IDEwOCA1NDQgMjY4IDcwNCAyNjggNzA0IDMzMiA1NDQgMzMyIDU0NCA0OTIgNTQ0IDQ5MloiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxQTUiIHVuaWNvZGU9IiYjeEUxQTU7IiBkPSJNNzM2IDMzMkw1NDQgMzMyIDU0NCA1MjQgNDgwIDUyNCA0ODAgMzMyIDI4OCAzMzIgMjg4IDI2OCA0ODAgMjY4IDQ4MCA3NiA1NDQgNzYgNTQ0IDI2OCA3MzYgMjY4WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTFBNiIgdW5pY29kZT0iJiN4RTFBNjsiIGQ9Ik04MTIuOCAzNDkuOTJDODA0LjM1MiAzNjUuNjY0IDc4OC4wMTA3IDM3Ni4xNiA3NjkuMjM3MyAzNzYuMTYgNzY4LjgxMDcgMzc2LjE2IDc2OC4zODQgMzc2LjE2IDc2Ny45NTczIDM3Ni4xNkw3NjguMDQyNyAzNzYuMTZINDM0LjYwMjdDNDA5LjE3MzMgMzc2LjE2IDM4OC41MjI3IDM1NS41MDkzIDM4OC41MjI3IDMzMC4wOFM0MDkuMTczMyAyODQgNDM0LjYwMjcgMjg0SDY5MC42MDI3QzcxOS40NDUzIDMyMS4zMzMzIDc2Mi45MjI3IDM0Ni4xNjUzIDgxMi4yODggMzQ5Ljg3NzNMODEyLjg0MjcgMzQ5LjkyWk00MzQuNTYgMTkzLjEyQzQwOS4xMzA3IDE5My4xMiAzODguNDggMTcyLjQ2OTMgMzg4LjQ4IDE0Ny4wNFM0MDkuMTMwNyAxMDAuOTYgNDM0LjU2IDEwMC45Nkg2NzguNEM2NjUuNTE0NyAxMjQuMDQyNyA2NTcuOTIgMTUxLjYwNTMgNjU3LjkyIDE4MC45MTczIDY1Ny45MiAxODAuOTE3MyA2NTcuOTIgMTgwLjkxNzMgNjU3LjkyIDE4MC45NlYxODAuOTZRNjU3LjkyIDE4Ny4zNiA2NTcuOTIgMTkzLjc2Wk0zMDQgMzMwLjA4QzMwNCAzMDIuODU4NyAyODAuNDkwNyAyODAuOCAyNTEuNTIgMjgwLjhTMTk5LjA0IDMwMi44NTg3IDE5OS4wNCAzMzAuMDhDMTk5LjA0IDM1Ny4zMDEzIDIyMi41NDkzIDM3OS4zNiAyNTEuNTIgMzc5LjM2UzMwNCAzNTcuMzAxMyAzMDQgMzMwLjA4Wk02NC0xNS41MlY0NzQuMDhDNjQuNjgyNyA1MDAuNDA1MyA4Ni4xODY3IDUyMS40ODI3IDExMi42NCA1MjEuNDgyNyAxMTMuMzIyNyA1MjEuNDgyNyAxMTQuMDA1MyA1MjEuNDgyNyAxMTQuNjg4IDUyMS40NEwxMTQuNjAyNyA1MjEuNDRIODgyLjYwMjdDODgzLjIgNTIxLjQ4MjcgODgzLjg0IDUyMS40ODI3IDg4NC41MjI3IDUyMS40ODI3IDkxMC45MzMzIDUyMS40ODI3IDkzMi40MzczIDUwMC40MDUzIDkzMy4xNjI3IDQ3NC4xNjUzTDkzMy4xNjI3IDQ3NC4wOFYzMTQuNzJDOTY1LjA3NzMgMjkwLjUyOCA5ODguMDMyIDI1NS45MjUzIDk5Ni45NDkzIDIxNi4wMzJMOTk3LjE2MjcgMjE0Ljg4VjUzNC44OEM5OTcuMTYyNyA1MzQuOTIyNyA5OTcuMTYyNyA1MzUuMDA4IDk5Ny4xNjI3IDUzNS4wOTMzIDk5Ny4xNjI3IDU3MC40MjEzIDk2OC40OTA3IDU5OS4wOTMzIDkzMy4xNjI3IDU5OS4wOTMzIDkzMS4zNzA3IDU5OS4wOTMzIDkyOS41Nzg3IDU5OS4wMDggOTI3LjgyOTMgNTk4Ljg4TDkyOC4wNDI3IDU5OC44OEg1MzYuMzYyN0M1MzUuNDY2NyA1OTguODM3MyA1MzQuNDQyNyA1OTguNzk0NyA1MzMuMzc2IDU5OC43OTQ3IDUyMS4wODggNTk4Ljc5NDcgNTA5LjgyNCA2MDMuMTg5MyA1MDEuMDc3MyA2MTAuNDg1M0w1MDEuMTYyNyA2MTAuNFM0ODQuNTIyNyA2MzYuNjQgNDU1LjA4MjcgNjgxLjQ0QzQ0Mi44OCA3MDMuMzcwNyA0MTkuODQgNzE3Ljk2MjcgMzkzLjM4NjcgNzE3Ljk2MjcgMzkyLjU3NiA3MTcuOTYyNyAzOTEuNzY1MyA3MTcuOTYyNyAzOTAuOTk3MyA3MTcuOTJMMzkxLjEyNTMgNzE3LjkySDg1LjIwNTNDODMuMTE0NyA3MTguMTMzMyA4MC42NCA3MTguMjE4NyA3OC4xNjUzIDcxOC4yMTg3IDM1LjAyOTMgNzE4LjIxODcgMC4wODUzIDY4My4yNzQ3IDAuMDg1MyA2NDAuMTM4NyAwLjA4NTMgNjM5Ljc5NzMgMC4wODUzIDYzOS40NTYgMC4wODUzIDYzOS4xMTQ3TDAuMDg1MyA2MzkuMTU3M1YtNDYuMjgyN0MwLjA4NTMtMTMwLjc2MjcgNjcuOTI1My0xMjAuNTIyNyA2Ny45MjUzLTEyMC41MjI3SDU3OS45MjUzQzU4OC44ODUzLTk4LjUwNjcgNTk5LjYzNzMtNzkuNTYyNyA2MTIuNDM3My02Mi4xOTczTDYxMS45MjUzLTYyLjkyMjdIMTEyLjA4NTNDODUuOTMwNy02Mi41ODEzIDY0LjgxMDctNDEuNjc0NyA2NC4wODUzLTE1LjY0OEw2NC4wODUzLTE1LjU2MjdaTTMwNCAxNDcuNjhDMzA0IDEyMC40NTg3IDI4MC40OTA3IDk4LjQgMjUxLjUyIDk4LjRTMTk5LjA0IDEyMC40NTg3IDE5OS4wNCAxNDcuNjhDMTk5LjA0IDE3NC45MDEzIDIyMi41NDkzIDE5Ni45NiAyNTEuNTIgMTk2Ljk2UzMwNCAxNzQuOTAxMyAzMDQgMTQ3LjY4Wk04OTEuNTIgNzYuNjRDOTI4Ljg1MzMgOTguMTg2NyA5NTMuNiAxMzcuOTA5MyA5NTMuNiAxODMuNDM0NyA5NTMuNiAyNTEuMzE3MyA4OTguNjAyNyAzMDYuMzE0NyA4MzAuNzIgMzA2LjMxNDdTNzA3Ljg0IDI1MS4zMTczIDcwNy44NCAxODMuNDM0N0M3MDcuODQgMTM3Ljk1MiA3MzIuNTg2NyA5OC4xODY3IDc2OS4zMjI3IDc2Ljk4MTNMNzY5LjkyIDc2LjY4MjdDNjkzLjcxNzMgNTAuMDU4NyA2NDAtMjEuMTk0NyA2NDAtMTA0Ljk5MiA2NDAtMTA1LjQ2MTMgNjQwLTEwNS45MzA3IDY0MC0xMDYuNFYtMTA2LjMxNDdDNjQwLTExMy43Mzg3IDY0Ni4wMTYtMTE5Ljc1NDcgNjUzLjQ0LTExOS43NTQ3Vi0xMTkuNzU0N0gxMDEzLjc2QzEwMjEuMTg0LTExOS43NTQ3IDEwMjcuMi0xMTMuNzM4NyAxMDI3LjItMTA2LjMxNDdWLTEwNi4zMTQ3QzEwMjYuOTQ0LTIwLjU5NzMgOTcwLjU4MTMgNTEuOTM2IDg5Mi44ODUzIDc2LjM0MTNMODkxLjUyIDc2LjcyNTNaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMUE3IiB1bmljb2RlPSImI3hFMUE3OyIgZD0iTTg0Ny4zOTc3IDM0OC45NjkxQzg0OS42NTc1IDM1OC44NjA3IDg1MC45MzY1IDM3MC4yMDIgODUwLjkzNjUgMzgxLjg0MTcgODUwLjkzNjUgNDE3Ljg2OTUgODM4LjUyOTQgNDUxLjA0MDUgODE3LjcyMjggNDc3LjIxOTMgODE0LjY1MyA1NjcuODY0MiA3NzYuNjY0IDY0OS4zNDIzIDcxNi45MzA1IDcwOS4wNzU4IDY1NC45Nzk4IDc3Mi4wNDk3IDU2OS4xMTAyIDgxMS4yNzUyIDQ3NC4wMzExIDgxMi4wNDI2IDQ3Mi41Mzg4IDgxMi4wNDI2IDQ3MC45NjEzIDgxMi4wODUzIDQ2OS40MjY0IDgxMi4wODUzIDI4Mi4wODIyIDgxMi4wODUzIDEzMC4xNjg4IDY2MC4zODUxIDEyOS44Mjc3IDQ3My4xMjYyIDExNC45NDc2IDQ1OS4wNTYyIDEwNS40ODI0IDQzOS40MDA4IDEwNC44ODU1IDQxNy41NzEgOTYuOTEyNSA0MDMuODg0NyA5Mi4yMjI1IDM4Ny41OTc2IDkyLjIyMjUgMzcwLjIwMiA5Mi4yMjI1IDM2Ni43OTExIDkyLjM5MyAzNjMuNDIyOCA5Mi43MzQxIDM2MC4xMzk4IDkyLjM5MyAzNTcuNTgxNiA5Mi4yMjI1IDM1NC4xMjgxIDkyLjIyMjUgMzUwLjYzMTlTOTIuMzkzIDM0My42ODIyIDkyLjczNDEgMzQwLjI3MTNDMzcuMDUxIDI3Ni43NDMxLTM1LjIxNzYgMTYwLjM0NTggMTIuNzQ4MyAzMy4wNzYzIDE4Ljc2IDE3LjAwMjQgMzMuNDY5NSA1LjUzMzIgNTAuOTkzMSA0LjI5NjcgNzcuNDI3NiA2LjY4NDQgMTAwLjE1MjggMjAuMTE0OCAxMTQuOTA1IDM5Ljg1NTUgMTIyLjc5MjcgMjUuNDAxNyAxMzAuNDY3MyAxMy4wNzk4IDEzOC44MjQgMS4zMTIyIDEyNy44NjY1LTQuNjE0MyAxMTguOTk4MS0xMi42Mjk5IDExMS40MDg4LTIxLjcxMTUgMTAwLjc5MjQtMzIuNzExNiA5NC4wOTg1LTQ3LjI1MDYgOTMuMzMxLTYzLjMyNDUgODkuMDY3NC03Mi4yNzgyIDg2LjQ2NjUtODIuNTUzNSA4Ni4yOTYtOTMuNDY4NSA4Ni4yNTM0LTk0LjU3NyA4Ni4yMTA3LTk1Ljc3MDggODYuMjEwNy05Ni45NjQ2IDg2LjIxMDctMTIyLjI0OCA5Ni43ODQ1LTE0NS4xMDExIDExMy43NTM4LTE2MS4zMDI5IDE1My4xNDk4LTE5Mi40Mjc1IDIwMy41MDM0LTIxMS4yMzAxIDI1OC4yNDg1LTIxMS4yMzAxIDI1OC43MTc1LTIxMS4yMzAxIDI1OS4xODY1LTIxMS4yMzAxIDI1OS42OTgxLTIxMS4yMzAxSDI4Ny43NTI4QzI5MC4zNTM2LTIxMS4zMTU0IDI5My40MjM1LTIxMS4zNTggMjk2LjQ5MzMtMjExLjM1OCAzNTUuNzE1Mi0yMTEuMzU4IDQxMC4yODk3LTE5MS41NzQ3IDQ1NC4wMzQ2LTE1OC4zMTg0TDQ4MS41MzUxLTE1OC43ODc0QzUyNi4wOTAxLTE5MS44MzA1IDU4Mi4xNTY5LTIxMS42NTY1IDY0Mi44Mjg1LTIxMS42NTY1IDY1My42MTU1LTIxMS42NTY1IDY2NC4yMzE5LTIxMS4wMTY5IDY3NC42Nzc4LTIwOS44MjMxIDcyNy4yNDg1LTIwOS4zNTQxIDc3Ni42NjQtMTkwLjY3OTQgODE1Ljg4OTUtMTU5LjY4MjcgODMyLjM4OTctMTQzLjgyMiA4NDIuOTYzNS0xMjEuMDExNSA4NDIuOTYzNS05NS42ODU1IDg0Mi45NjM1LTk0LjQ5MTcgODQyLjkyMDktOTMuMjU1MyA4NDIuODc4My05Mi4wNjE1IDg0Mi43MDc3LTgxLjI3NDUgODQwLjEwNjktNzAuOTU2NSA4MzUuNjcyNy02MS43NDcgODM0Ljk0NzktNDYuMTg0NyA4MjguMjk2Ni0zMS45MDE1IDgxNy45MzYtMjEuMjQyNSA4MDguOTgyNC0xMC4zNzAyIDc5OC40MDg1LTEuMjQ2IDc4Ni41MTMgNS45MTY5IDc5NC44Njk3IDE3LjQyODcgODAzLjUyNDkgMjkuOTIxMiA4MTEuMzI3NCA0My4wNTMyIDgyNS43ODExIDI0LjI1MDUgODQ3LjQ0MDQgMTAuMTgwNSA4NzIuNTEwNSA2Ljg5NzVMODcyLjkzNjkgNi44NTQ5Qzg5MC45Mjk1IDYuOTgyOCA5MDYuMzYzOCAxNy44OTc3IDkxMy4xMDA0IDMzLjQxNzQgOTcwLjE0NzggMTYxLjYyNDkgODkzLjQwMjQgMjg4Ljg5NDUgODQ3LjM1NTEgMzQ5LjAxMTdaIiAgaG9yaXotYWR2LXg9IjkzOCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxQTgiIHVuaWNvZGU9IiYjeEUxQTg7IiBkPSJNMjg3Ljc5NTUtMjExLjI3MjdIMjU5LjY1NTVDMjA1LjgwNTctMjEwLjY3NTggMTU2LjM5MDItMTkyLjAwMTEgMTE3LjE2NDctMTYxLjAwNDUgMTAwLjY2NDUtMTQ1LjE0MzcgOTAuMDkwNi0xMjIuMzMzMyA5MC4wOTA2LTk3LjAwNzMgOTAuMDkwNi05NS44MTM1IDkwLjEzMzMtOTQuNTc3IDkwLjE3NTktOTMuMzgzMiA5MC4zNDY1LTgyLjU5NjIgOTIuOTQ3My03Mi4yNzgyIDk3LjM4MTUtNjMuMDY4NyA5Ny4yMTA5LTYzLjM2NzIgOTcuMjEwOS02My4yMzkzIDk3LjIxMDktNjMuMDY4NyA5Ny4yMTA5LTQ2LjE0MjEgMTAzLjc3NjktMzAuNzUwNCAxMTQuNTIxMy0xOS4zMjM4IDEyMi4yMzg1LTEwLjA3MTcgMTMxLjEwNjgtMi4wMTM1IDE0MC45MTMyIDQuNjgwNSAxMzMuNzA3NiAxNS42ODA2IDEyNi4wNzU3IDI4LjA0NTIgMTE5LjIxMTMgNDAuODM2MSAxMDMuMzkzMiAyMi43MTU2IDgwLjYyNTQgOS4yODUyIDU0LjcwMjUgNi44OTc1IDM2LjcwOTkgOC4xMzQgMjIuMDAwNCAxOS42MDMyIDE2LjA3MzkgMzUuMzM2LTMxLjMzNzcgMTYzLjU0MzUgNDAuMjkxNCAyNzguMDIyMiA5NS45MzE4IDM0My4yNTU4IDk1LjYzMzQgMzQ2LjI0MDQgOTUuNDYyOCAzNDkuNjkzOSA5NS40NjI4IDM1My4xNDc1Uzk1LjYzMzQgMzYwLjA5NzIgOTUuOTc0NSAzNjMuNTA4MUM5NS42MzM0IDM2NS45ODEgOTUuNDYyOCAzNjkuMzQ5MyA5NS40NjI4IDM3Mi43MTc1IDk1LjQ2MjggMzkwLjExMzIgMTAwLjE1MjggNDA2LjQwMDMgMTA4LjMzOSA0MjAuNDI3NiAxMDguNzIyNyA0NDEuOTU5IDExOC4xNDU0IDQ2MS42MTQ0IDEzMi45ODI4IDQ3NS41OTkxIDEzNC44MTYyIDY2MS43OTIxIDI4Ni4xNzUzIDgxMi4wNDI2IDQ3Mi42MjQxIDgxMi4wNDI2IDQ3My4wOTMxIDgxMi4wNDI2IDQ3My41MTk1IDgxMi4wNDI2IDQ3My45ODg1IDgxMi4wNDI2IDU2OS42MjE4IDgxMC44OTE1IDY1NS43NDczIDc3MC45NDEyIDcxNy40ODQ3IDcwNy4yNDI1IDc3Ny4zNDYyIDY0Ny40NjYzIDgxNS4zMzUyIDU2NS45NDU1IDgxOC42MTgyIDQ3NS41OTkxIDgzOS4xNjg5IDQ0OS4xMjE5IDg1MS42MTg3IDQxNS45NTA4IDg1MS42MTg3IDM3OS45MjMxIDg1MS42MTg3IDM2OC4yODM0IDg1MC4zMzk2IDM1Ni45NDIxIDg0Ny44NjY3IDM0Ni4wMjcyIDg5NC43NjY3IDI4Ni45MzMyIDk3MC44NzI2IDE1OS42NjM2IDkxMi4wMzQ1IDMxLjExNSA5MDUuMTcgMTUuMjk2OSA4ODkuNzM1NiA0LjM4MiA4NzEuNzQzMSA0LjI1NDFIODcxLjc0MzFDODQ2LjM3NDUgOC41MTc3IDgyNS4xNDE1IDIzLjQ0MDUgODEyLjQ3ODUgNDQuMTYxNyA4MDQuNzYxNCAyOS44MzU5IDc5Ny4zIDE3LjQ3MTQgNzg5LjE1NjUgNS42NjExIDgwMi4zMzExLTAuNjkxNyA4MTIuOTA0OS05Ljg1ODUgODIxLjY4OC0yMC41MTc2IDgzMi4xNzY1LTMxLjM4OTkgODM4LjgyNzgtNDUuNjczMSA4MzkuNzY1OC02MS40OTEyIDg0NC4wMjk1LTcwLjQ0NDggODQ2LjYzMDMtODAuNzYyOCA4NDYuODAwOC05MS42Nzc3IDg0Ni44NDM1LTkyLjc4NjMgODQ2Ljg4NjEtOTMuOTgwMSA4NDYuODg2MS05NS4xNzM5IDg0Ni44ODYxLTEyMC40NTczIDgzNi4zMTIzLTE0My4zMTA0IDgxOS4zNDMtMTU5LjUxMjIgNzgwLjU4NjUtMTkwLjE2NzcgNzMxLjE3MS0yMDguODQyNSA2NzcuNDQ5Mi0yMDkuNDM5NCA2NjguMTU0NS0yMTAuNTQ3OSA2NTcuNTM4LTIxMS4xNDQ4IDY0Ni43NTEtMjExLjE0NDggNTg2LjAzNjgtMjExLjE0NDggNTMwLjAxMjYtMTkxLjMxODkgNDg0LjY5MDItMTU3LjcyMTVMNDU0LjA3NzMtMTU4LjIzMzFDNDEwLjg0NC0xOTEuNDQ2OCAzNTUuOTI4NC0yMTEuNDQzMyAyOTYuMzY1NC0yMTEuNDQzMyAyOTMuMzM4Mi0yMTEuNDQzMyAyOTAuMzUzNi0yMTEuNDAwNiAyODcuMzY5MS0yMTEuMjcyN1pNMTcxLjM5ODItNTUuMjIzNkwxODguMDI2NC02NS40NTY0IDE1Mi44NTE0LTkzLjU5NjRDMTUzLjYxODgtMTAxLjE0MyAxNTYuMzkwMi0xMDcuOTIyMiAxNjAuNjExMi0xMTMuNTA3NSAxODkuMjIwMi0xMzQuNDg0NiAyMjUuMjA1My0xNDcuMTQ3NiAyNjQuMTMyMy0xNDcuMzE4MiAyNzIuOTE1NC0xNDguNjM5OSAyODIuOTc3NS0xNDkuNDA3NCAyOTMuMjEwMy0xNDkuNDA3NCAzNDEuODE1Ny0xNDkuNDA3NCAzODYuNDEzNC0xMzIuMTgyMyA0MjEuMjA0Ni0xMDMuNTMwNkw0MzAuNDU2Ny05NC44MzI4SDQ1MC4yODI2QzQ1Ni4yMDkxLTk1LjI1OTIgNDYzLjExNjItOTUuNTE1IDQ3MC4xMDg1LTk1LjUxNVM0ODQuMDA4LTk1LjI1OTIgNDkwLjg3MjUtOTQuNzkwMkw1MDQuMDA0NS05NC44MzI4IDUxNC4yMzcyLTEwNC40MjZDNTQ4LjQ3NDItMTMyLjkwNzEgNTkyLjk0MzktMTUwLjIxNzUgNjQxLjQyMTUtMTUwLjIxNzUgNjUyLjA4MDUtMTUwLjIxNzUgNjYyLjUyNjUtMTQ5LjM2NDcgNjcyLjcxNjUtMTQ3Ljc4NzIgNjcyLjExOTYtMTQ3Ljk1NzcgNjcyLjcxNjUtMTQ3Ljk1NzcgNjczLjMxMzUtMTQ3Ljk1NzcgNzExLjg1NjctMTQ3Ljk1NzcgNzQ3LjQ1ODEtMTM1LjQ2NTMgNzc2LjMyMjktMTE0LjM2MDMgNzc5LjY5MTItMTEwLjE4MTkgNzgyLjAzNjItMTA0LjI1NTUgNzgyLjAzNjItOTcuNzc0NyA3ODIuMDM2Mi05Ni4wNjkzIDc4MS44NjU2LTk0LjQwNjUgNzgxLjU2NzItOTIuNzg2M0w3NDYuNDM0OC02NC44MTY4IDc2My4wNjMtNTUuODYzMkM3NTMuODUzNS00OC44NzA4IDc0Mi45Mzg2LTQzLjU0MTMgNzMxLjA0MzEtNDAuNjQyTDY3OS45MjIxLTI3LjcyMzIgNzE0LjQ1NzUgMTEuMjg5MUM3NDEuNjE2OSA0MS42ODg4IDc2Mi4yMTAzIDc4LjYxMTkgNzczLjQ2NjMgMTE5LjM3MjNMNzk2LjMxOTQgMjA1LjcxMDkgODMzLjQxMyAxMjcuMDQ2OEM4NDEuNTEzOSAxMDkuMjI0OCA4NTEuMTA3MSA5My44NzU3IDg2Mi40OTEgNzkuOTc2MyA4OTAuMzMyNSAxNzkuNDg5NSA4MTkuMzQzIDI3OS44OTgyIDc4Ni4wODY2IDMyMC4xODk1TDc3My45MzUzIDMzNC4yNTk1IDc4MC4zMzA3IDM1MS41MjczQzc4My4xODc0IDM1OS44NDE0IDc4NC44MDc1IDM2OS40MzQ1IDc4NC44MDc1IDM3OS40MTE1IDc4NC44MDc1IDQwMi40MzUxIDc3Ni4wNjcxIDQyMy40MTIyIDc2MS42OTg2IDQzOS4xODc2TDc1Mi44MzAzIDQ0OC42OTU1VjQ2MS40ODY1Qzc1Mi41MzE4IDYxNi45Mzg2IDYyOC44MDExIDc0My4zOTgxIDQ3NC40MTQ4IDc0OC4wMDI4IDQ3My4xNzg0IDc0OC4wMDI4IDQ3Mi4yNDA0IDc0OC4wNDU1IDQ3MS4yNTk3IDc0OC4wNDU1IDMxNy41OTgzIDc0OC4wNDU1IDE5My4wNTc1IDYyMy41MDQ2IDE5My4wNTc1IDQ2OS44NDMyIDE5My4wNTc1IDQ2Ni40NzQ5IDE5My4xMDAxIDQ2My4xMDY2IDE5My4yMjggNDU5LjczODRMMTkzLjIyOCA0NDEuMDIxIDE3Ny4yMzk0IDQyOC4yMzAxQzE3Mi4wMzc3IDQyNS4zMzA4IDE2OC41ODQyIDQxOS45MTYgMTY4LjU4NDIgNDEzLjY0ODUgMTY4LjU4NDIgNDEyLjQ1NDYgMTY4LjcxMjEgNDExLjM0NjEgMTY4LjkyNTMgNDEwLjIzNzVMMTcyLjc2MjUgMzg1LjQyMzIgMTU3LjQxMzUgMzc4LjM4ODJDMTU3LjA3MjQgMzc1Ljg3MjYgMTU2Ljg1OTIgMzczLjAxNiAxNTYuODU5MiAzNzAuMDc0MVMxNTcuMDcyNCAzNjQuMjc1NSAxNTcuNDU2MSAzNjEuNDE4OUMxNTcuOTI1MSAzNTUuMTUxNCAxNTkuNTQ1MyAzNDkuMDk3IDE2Mi4wMTgyIDM0My41MTE2TDE2OS41NjQ4IDMyNS4zMDU5IDE1Ni4xMzQ0IDMxMC41OTY0QzEwMS42NDUxIDI1OS43NzM4IDY3LjcwNjUgMTg3LjU5MDUgNjcuNzA2NSAxMDcuNDM0MSA2Ny43MDY1IDk3LjQ1NzIgNjguMjE4MiA4Ny41NjU1IDY5LjI4NDEgNzcuODQ0NSA4MC41NDAxIDkxLjM2MDIgOTAuNTE3IDEwNS4yMTcgOTguNzAzMiAxMjAuMTgyNEwxMzYuMzUxMSAxODUuMjAyOCAxNTguMDk1NiAxMTIuOTM0MkMxNzAuMjg5NiA3Mi41MTQ5IDE5MC4yODYxIDM3LjYzODQgMjE2LjUwNzUgOC40MzI1TDI0OS41NTA2LTI4LjQwNTQgMjAxLjU4NDctNDMuMTE0OUMxOTAuMjAwOC00NS4yNDY3IDE4MC4wOTYtNDkuNDY3NyAxNzEuMjI3Ni01NS40MzY4Wk0xNTEuNTcyMyAzNzcuMTA5MVYzNzcuMTA5MVoiICBob3Jpei1hZHYteD0iOTM4IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTFBOSIgdW5pY29kZT0iJiN4RTFBOTsiIGQ9Ik01MTIgODEyQzIyOS4yNDggODEyIDAgNTgyLjc1MiAwIDMwMFMyMjkuMjQ4LTIxMiA1MTItMjEyQzc5NC43NTItMjEyIDEwMjQgMTcuMjQ4IDEwMjQgMzAwUzc5NC43NTIgODEyIDUxMiA4MTJaTTUxMi0yMEM0OTQuMzM2LTIwIDQ4MC01LjY2NCA0ODAgMTJTNDk0LjMzNiA0NCA1MTIgNDRDNTI5LjY2NCA0NCA1NDQgMjkuNjY0IDU0NCAxMlM1MjkuNjY0LTIwIDUxMi0yMFpNNjQwIDI3Ni45NkM2MzEuNDI0IDI3MC4wOTA3IDYyMS43ODEzIDI2My45NDY3IDYxMS40OTg3IDI1OC44MjY3IDU3MS42OTA3IDI0MS4yNDggNTQ1LjA2NjcgMjAzLjAxODcgNTQ1LjA2NjcgMTU4LjYwMjcgNTQ1LjA2NjcgMTUyLjI0NTMgNTQ1LjYyMTMgMTQ2LjA1ODcgNTQ2LjY0NTMgMTQwIDU0Ni41NiAxMjIuOTc2IDUzMi4yMjQgMTA4LjY0IDUxNC41NiAxMDguNjRTNDgyLjU2IDEyMi45NzYgNDgyLjU2IDE0MC42NEM0ODEuODc3MyAxNDYuMjcyIDQ4MS40OTMzIDE1Mi44NDI3IDQ4MS40OTMzIDE1OS40OTg3IDQ4MS40OTMzIDIyNy42OCA1MjEuNTU3MyAyODYuNDc0NyA1NzkuNDEzMyAzMTMuNjUzMyA1ODcuNjA1MyAzMTcuNTM2IDU5My42NjQgMzIxLjE2MjcgNTk5LjQyNCAzMjUuMjU4NyA2MjcuMzI4IDM0OS41MzYgNjQ1LjA3NzMgMzg1LjU0NjcgNjQ1LjA3NzMgNDI1LjY5NiA2NDUuMDc3MyA0OTkuMjEwNyA1ODUuNDcyIDU1OC44MTYgNTExLjk1NzMgNTU4LjgxNiA0MzkuMjUzMyA1NTguODE2IDM4MC4xNiA1MDAuNTMzMyAzNzguODggNDI4LjE3MDcgMzc3LjYgNDEwLjg5MDcgMzY0LjAzMiAzOTcuMzIyNyAzNDcuMDA4IDM5Ni4wNDI3IDMyOS4yMTYgMzk2LjA0MjcgMzE0Ljg4IDQxMC4zNzg3IDMxNC44OCA0MjguMDQyNyAzMTUuNTIgNTM2LjQxNiA0MDMuNTQxMyA2MjQuMDEwNyA1MTIgNjI0LjAxMDcgNjIwLjg4NTMgNjI0LjAxMDcgNzA5LjEyIDUzNS43NzYgNzA5LjEyIDQyNi44OTA3IDcwOS4xMiAzNjYuOTg2NyA2ODIuNDEwNyAzMTMuMzU0NyA2NDAuMjU2IDI3Ny4yMTZaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMUFBIiB1bmljb2RlPSImI3hFMUFBOyIgZD0iTTUxMiA2ODRDNzI0LjggNjg0IDg5NiA1MTIuOCA4OTYgMzAwUzcyNC44LTg0IDUxMi04NCAxMjggODcuMiAxMjggMzAwIDI5OS4yIDY4NCA1MTIgNjg0TTUxMiA3NDhDMjY0IDc0OCA2NCA1NDggNjQgMzAwUzI2NC0xNDggNTEyLTE0OCA5NjAgNTIgOTYwIDMwMCA3NjAgNzQ4IDUxMiA3NDhaTTUwMC44IDEzOC40TTQ1Mi44IDEzOC40QTQ4IDQ4IDAgMSAxIDU0OC44IDEzOC40IDQ4IDQ4IDAgMSAxIDQ1Mi44IDEzOC40Wk01MTMuNiA1MDkuNkM1OTMuNiA1MDkuNiA2NDYuNCA0NjQuOCA2NDYuNCAzOTkuMiA2NDYuNCAzNTcuNiA2MjUuNiAzMjcuMiA1ODUuNiAzMDMuMiA1NDUuNiAyNzkuMiA1MzcuNiAyNjggNTM3LjYgMjQwLjhWMjI2LjRINDY0VjI0Mi40QzQ2MC44IDI4Ny4yIDQ3NS4yIDMxMi44IDUxNS4yIDMzNS4yIDU1MiAzNTcuNiA1NjMuMiAzNzAuNCA1NjMuMiAzOTZTNTQyLjQgNDQwLjggNTEwLjQgNDQwLjhDNDgxLjYgNDQyLjQgNDU3LjYgNDIxLjYgNDU0LjQgMzkyLjggNDU0LjQgMzkxLjIgNDU0LjQgMzkxLjIgNDU0LjQgMzg5LjZIMzc3LjZDMzc3LjYgNDYwIDQyNy4yIDUwOS42IDUxMy42IDUwOS42WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTFBQiIgdW5pY29kZT0iJiN4RTFBQjsiIGQ9Ik04MzIgNDkyQzgzMiAzOTguNTYgNzkxLjY4IDMxMC4yNCA3MjAuNjQgMjQ5LjQ0IDcwOC40OCAyMzkuMiA2OTMuNzYgMjMwLjI0IDY3Ny43NiAyMjAuNjQgNjE4LjI0IDE4NS40NCA1NDQgMTQxLjI4IDU0NC0yMCA1NDQtMzcuOTIgNTI5LjkyLTUyIDUxMi01MlM0ODAtMzcuOTIgNDgwLTIwQzQ4MCAxNzcuNzYgNTgzLjY4IDIzOS4yIDY0NS4xMiAyNzUuNjggNjU4LjU2IDI4My4zNiA2NzAuMDggMjkwLjQgNjc5LjA0IDI5OC4wOCA3MzUuMzYgMzQ2LjcyIDc2OCA0MTcuMTIgNzY4IDQ5MiA3NjggNjMzLjQ0IDY1My40NCA3NDggNTEyIDc0OCAzNzEuODQgNzQ4IDI1Ny4yOCA2MzQuMDggMjU2IDQ5NC41NiAyNTYgNDc3LjI4IDI0MS4yOCA0NjIuNTYgMjI0IDQ2Mi41NiAyMjQgNDYyLjU2IDIyNCA0NjIuNTYgMjI0IDQ2Mi41NiAyMDYuMDggNDYyLjU2IDE5MiA0NzcuMjggMTkyIDQ5NS4yIDE5My4yOCA2NjkuOTIgMzM3LjI4IDgxMiA1MTIgODEyIDY4OC42NCA4MTIgODMyIDY2OC42NCA4MzIgNDkyWk01MTItMTQ4QzQ5NC4wOC0xNDggNDgwLTE2Mi4wOCA0ODAtMTgwUzQ5NC4wOC0yMTIgNTEyLTIxMiA1NDQtMTk3LjkyIDU0NC0xODBDNTQ0LTE2Mi4wOCA1MjkuOTItMTQ4IDUxMi0xNDhaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMUFDIiB1bmljb2RlPSImI3hFMUFDOyIgZD0iTTg2OC44IDQ0Mi40Qzg4Ni40IDM5Ny42IDg5NiAzNDggODk2IDMwMCA4OTYgODcuMiA3MjMuMi04NCA1MTItODQgNDIwLjgtODQgMzMyLjgtNTIgMjY0IDcuMkgzNDAuOFY3MS4ySDE2MFYtMTA4SDIyNFYtNDIuNEM0MTIuOC0yMDAuOCA2OTYtMTc2LjggODU0LjQgMTIgOTYzLjIgMTQxLjYgOTg4LjggMzE5LjIgOTIzLjIgNDc0LjRMODY4LjggNDQyLjRaTTE1NS4yIDE1Ny42QzEzNy42IDIwMi40IDEyOCAyNTIgMTI4IDMwMCAxMjggNTEyLjggMzAwLjggNjg0IDUxMiA2ODQgNjAzLjIgNjg0IDY5MS4yIDY1MiA3NjAgNTkyLjhINjgzLjJWNTI4LjhIODY0VjcwOEg4MDBWNjQyLjRDNjExLjIgODAyLjQgMzI4IDc3Ni44IDE2OS42IDU4OCA2MC44IDQ1OC40IDM1LjIgMjgwLjggMTAwLjggMTI1LjZMMTU1LjIgMTU3LjZaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMUFEIiB1bmljb2RlPSImI3hFMUFEOyIgZD0iTTgyMi40IDMxOC41NkwzODMuMzYgNjc1LjA0QzM3My4xMiA2ODMuMzYgMzU3LjEyIDY4NS45MiAzNDMuMDQgNjgyLjA4UzMyMCA2NjggMzIwIDY1Ni40OFYtNTYuNDhDMzIwLTY4IDMyOC45Ni03Ny42IDM0My4wNC04Mi4wOCAzNDcuNTItODMuMzYgMzUyLTg0IDM1Ni40OC04NCAzNjYuNzItODQgMzc2LjMyLTgwLjggMzgzLjM2LTc1LjA0TDgyMi40IDI4MS40NEM4MzUuMiAyOTEuNjggODM1LjIgMzA4LjMyIDgyMi40IDMxOC41NloiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxQUUiIHVuaWNvZGU9IiYjeEUxQUU7IiBkPSJNNDgwIDU5Ni44SDQ4MEM1MjggNjE2Ljk2IDUxMC43MiA2NDIuMjQgNDkyLjggNjU3LjI4QTMzMi45NiAzMzIuOTYgMCAwIDEgMzUxLjg0IDcxMy4xMkgzNTAuMDhBNDQ4IDQ0OCAwIDAgMSA2NCAzMDBWMzAwQzY0IDI5My40NCA2NCAyODUuNzYgNjQgMjc3LjkyUzY0IDI2MS45MiA2NCAyNTQuNzJWMjU1Ljg0QTY5My4yOCA2OTMuMjggMCAwIDAgNDcyIDU5NS41Mkw0NzYuOTYgNTk2LjhaTTk2MCAzMDBBNDQ4IDQ0OCAwIDAgMSA5MTYuMzIgNDkyTDkxNy40NCA0ODkuMjhBMjU3Ljc2IDI1Ny43NiAwIDAgMSA3NTguODggNTYwLjk2SDc1Ny45MkM3MTMuNzYgNTU3LjEyIDc1Ny45MiA0ODQuOCA3NTcuOTIgNDg0LjhINzU3LjkyQTcwMC4xNiA3MDAuMTYgMCAwIDAgODI5LjYgMzQ4TDgzMS4yIDM0My4yQTY5My42IDY5My42IDAgMCAwIDg4MCA4My41MkM4ODAgNzAuNCA4ODAgNTcuNiA4NzkuMDQgNDQuOFY0Ni41NkE0NDIuNzIgNDQyLjcyIDAgMCAxIDk2MCAzMDBaTTU2NC4xNiA2NzYuMzJINTY0LjE2TDU4OS45MiA2NjAuMzJBMzU5Ljg0IDM1OS44NCAwIDAgMSA3MTEuNjggNjIwTDcxMy43NiA2MjAgNzUyLjggNjE1LjA0QTM0My4yIDM0My4yIDAgMCAwIDg3My4yOCA1NjQuMzJMODcyLjE2IDU2NC4zMkE0NDQuNDggNDQ0LjQ4IDAgMCAxIDM5Ny4xMiA3MzJMNDAwLjE2IDczMkE0NDggNDQ4IDAgMCAwIDU2NC42NCA2NzYuMzJMNTYyLjU2IDY3Ny40NFpNNTM1LjY4IDUzNi4zMkE3MDYuNCA3MDYuNCAwIDAgMSA4MCAxOTQuNTZMNzguMDggMTkxLjA0QTQ0OCA0NDggMCAwIDEgODQxLjYtMy4wNEw4NDEuNi0zLjA0Qzg0MS42IDUuOTIgODQxLjYgMTYuNDggODQxLjYgMjcuMDRBNzI0LjE2IDcyNC4xNiAwIDAgMSA2NjUuNiA1MDEuNkw2NjYuNCA1MDAuOEExNDQgMTQ0IDAgMCAxIDU2NS43NiA1NDEuNiAxNDkuMjggMTQ5LjI4IDAgMCAxIDUzMy43NiA1MzguMDhINTM0LjcyWiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTFBRiIgdW5pY29kZT0iJiN4RTFBRjsiIGQ9Ik03NjggODEySDI1NlY0MjhINzY4Wk02NzIgNTU2QzY3MiA1MzguMzM2IDY1Ny42NjQgNTI0IDY0MCA1MjRTNjA4IDUzOC4zMzYgNjA4IDU1NlY2MjBDNjA4IDYzNy42NjQgNjIyLjMzNiA2NTIgNjQwIDY1MlM2NzIgNjM3LjY2NCA2NzIgNjIwWk04NjQgODEySDgzMlYzOTZDODMyIDM3OC4zMzYgODE3LjY2NCAzNjQgODAwIDM2NEgyMjRDMjA2LjMzNiAzNjQgMTkyIDM3OC4zMzYgMTkyIDM5NlY4MTJIMTYwQzcxLjYzNzMgODEyIDAgNzQwLjM2MjcgMCA2NTJWLTUyQzAtMTQwLjM2MjcgNzEuNjM3My0yMTIgMTYwLTIxMkg4NjRDOTUyLjM2MjctMjEyIDEwMjQtMTQwLjM2MjcgMTAyNC01MlY2NTJDMTAyNCA3NDAuMzYyNyA5NTIuMzYyNyA4MTIgODY0IDgxMloiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxQjAiIHVuaWNvZGU9IiYjeEUxQjA7IiBkPSJNODY0IDgxMkgxNjBDNzEuNjM3MyA4MTIgMCA3NDAuMzYyNyAwIDY1MlYtNTJDMC0xNDAuMzYyNyA3MS42MzczLTIxMiAxNjAtMjEySDg2NEM5NTIuMzYyNy0yMTIgMTAyNC0xNDAuMzYyNyAxMDI0LTUyVjY1MkMxMDI0IDc0MC4zNjI3IDk1Mi4zNjI3IDgxMiA4NjQgODEyWk03NjggNzQ4VjQyOEgyNTZWNzQ4Wk05NjAtNTJDOTYwLTEwNS4wMzQ3IDkxNy4wMzQ3LTE0OCA4NjQtMTQ4SDE2MEMxMDYuOTY1My0xNDggNjQtMTA1LjAzNDcgNjQtNTJWNjUyQzY0IDcwNS4wMzQ3IDEwNi45NjUzIDc0OCAxNjAgNzQ4SDE5MlYzOTZDMTkyIDM3OC4zMzYgMjA2LjMzNiAzNjQgMjI0IDM2NEg4MDBDODE3LjY2NCAzNjQgODMyIDM3OC4zMzYgODMyIDM5NlY3NDhIODY0QzkxNy4wMzQ3IDc0OCA5NjAgNzA1LjAzNDcgOTYwIDY1MlpNNjQwIDUyNEM2NTcuNjY0IDUyNCA2NzIgNTM4LjMzNiA2NzIgNTU2VjYyMEM2NzIgNjM3LjY2NCA2NTcuNjY0IDY1MiA2NDAgNjUyUzYwOCA2MzcuNjY0IDYwOCA2MjBWNTU2QzYwOCA1MzguMzM2IDYyMi4zMzYgNTI0IDY0MCA1MjRaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMUIxIiB1bmljb2RlPSImI3hFMUIxOyIgZD0iTTgwMS4yNjA1IDQ4OS4wNjU4VjQ5Mi4yNjMyQzc5OS45ODE2IDQ5OC4wMTg0IDc5Ny4yOTU4IDUwMy4wMDYzIDc5My41ODY4IDUwNi45NzExTDc5My41ODY4IDUwNi45NzExIDQ5Ny41MTA1IDgwMi40MDc5QzQ5My42NzM3IDgwNi44NDE2IDQ4OC42ODU4IDgxMC4xNjY4IDQ4My4wMTU4IDgxMS45NTc0TDQ4Mi44MDI2IDgxMkg5OS4xMTg0Qzk4LjczNDcgODEyIDk4LjI2NTggODEyIDk3LjgzOTUgODEyIDQ0LjQ2NDcgODEyIDEuMTA4NCA3NjkuMjgzMiAwIDcxNi4xNjQyTDAgNzE2LjA3ODlWLTExNS4yMzY4QzEuMDY1OC0xNjguNDQxMSA0NC40NjQ3LTIxMS4xNTc5IDk3LjgzOTUtMjExLjE1NzkgOTguMzA4NC0yMTEuMTU3OSA5OC43MzQ3LTIxMS4xNTc5IDk5LjIwMzctMjExLjE1NzlMOTkuMTE4NC0yMTEuMTU3OUg3MDIuNzgxNkM3MDMuMTY1My0yMTEuMTU3OSA3MDMuNjM0Mi0yMTEuMTU3OSA3MDQuMDYwNS0yMTEuMTU3OSA3NTcuNDM1My0yMTEuMTU3OSA4MDAuNzkxNi0xNjguNDQxMSA4MDEuOS0xMTUuMzIyMUw4MDEuOS0xMTUuMjM2OFY0ODQuNTg5NUM4MDEuNzcyMSA0ODYuMjUyMSA4MDEuNTU4OSA0ODcuNzg2OCA4MDEuMjE3OSA0ODkuMjc4OUw4MDEuMjYwNSA0ODkuMDY1OFpNNTA2LjQ2MzIgNzAyLjY1TDY5Mi41NSA1MTYuNTYzMkg1MDYuNDYzMlpNNzAyLjc4MTYtMTQ3LjIxMDVIOTkuMTE4NEM5OC43MzQ3LTE0Ny4yMTA1IDk4LjI2NTgtMTQ3LjI1MzIgOTcuNzk2OC0xNDcuMjUzMiA3OS43NjM3LTE0Ny4yNTMyIDY0Ljk3MDUtMTMzLjE0MjEgNjMuOTQ3NC0xMTUuMzY0N0w2My45NDc0LTExNS4yNzk1VjcxNi4wMzYzQzY0Ljk3MDUgNzMzLjk0MTYgNzkuNzIxMSA3NDguMDUyNiA5Ny43OTY4IDc0OC4wNTI2IDk4LjI2NTggNzQ4LjA1MjYgOTguNzM0NyA3NDguMDUyNiA5OS4yMDM3IDc0OC4wMUw5OS4xMTg0IDc0OC4wMUg0NDIuNTE1OFY0ODQuNTQ2OEM0NDIuNTE1OCA0NjYuODk3NCA0NTYuODQgNDUyLjU3MzIgNDc0LjQ4OTUgNDUyLjU3MzJWNDUyLjU3MzJINzM3Ljk1MjZWLTExNS4yNzk1QzczNi45Mjk1LTEzMy4xODQ3IDcyMi4xNzg5LTE0Ny4yOTU4IDcwNC4xMDMyLTE0Ny4yOTU4IDcwMy42MzQyLTE0Ny4yOTU4IDcwMy4xNjUzLTE0Ny4yOTU4IDcwMi42OTYzLTE0Ny4yNTMyTDcwMi43ODE2LTE0Ny4yNTMyWk01NDIuOTEzMiAyODEuMjM2OEM1MzcuMzI4NCAyODYuMDk2OCA1MjkuOTk1OCAyODkuMDgxMSA1MjEuOTM4NCAyODkuMDgxMSA1MDQuMjg4OSAyODkuMDgxMSA0ODkuOTY0NyAyNzQuNzU2OCA0ODkuOTY0NyAyNTcuMTA3NCA0ODkuOTY0NyAyNDkuMjIwNSA0OTIuODIxMSAyNDIuMDE1OCA0OTcuNTUzMiAyMzYuNDMxMUw0OTcuNTEwNSAyMzYuNDczNyA1ODAuNjQyMSAxNTMuMzQyMSA0OTcuNTEwNSA3MC4yMTA1QzQ5MS43MTI2IDY0LjQxMjYgNDg4LjA4ODkgNTYuMzU1MyA0ODguMDg4OSA0Ny40ODc5IDQ4OC4wODg5IDI5Ljc1MzIgNTAyLjQ1NTggMTUuMzg2MyA1MjAuMTkwNSAxNS4zODYzIDUyOS4wNTc5IDE1LjM4NjMgNTM3LjA3MjYgMTguOTY3NCA1NDIuODcwNSAyNC44MDc5TDY0OC4zODM3IDEzMC4zMjExQzY1NC4yMjQyIDEzNi4xMTg5IDY1Ny44NDc5IDE0NC4xMzM3IDY1Ny44NDc5IDE1My4wMDExUzY1NC4yMjQyIDE2OS45MjU4IDY0OC4zODM3IDE3NS42ODExTDY0OC4zODM3IDE3NS42ODExWk0zMDQuMzg5NSAyODEuMjM2OEMyOTguNTkxNiAyODcuMDc3NCAyOTAuNTc2OCAyOTAuNzAxMSAyODEuNjY2OCAyOTAuNzAxMVMyNjQuNzQyMSAyODcuMDc3NCAyNTguOTg2OCAyODEuMjM2OEwyNTguOTg2OCAyODEuMjM2OCAxNTMuNDczNyAxNzIuNTI2M0MxNDcuNjMzMiAxNjYuNzI4NCAxNDQuMDA5NSAxNTguNzEzNyAxNDQuMDA5NSAxNDkuODQ2M1MxNDcuNjMzMiAxMzIuOTIxNiAxNTMuNDczNyAxMjcuMTY2M0wyNTguOTg2OCAyMS42NTMyQzI2NC43ODQ3IDE1Ljg1NTMgMjcyLjg0MjEgMTIuMjMxNiAyODEuNzA5NSAxMi4yMzE2IDI5OS40NDQyIDEyLjIzMTYgMzEzLjgxMTEgMjYuNTk4NCAzMTMuODExMSA0NC4zMzMyIDMxMy44MTExIDUzLjIwMDUgMzEwLjIzIDYxLjIxNTMgMzA0LjM4OTUgNjcuMDEzMkwyMjEuMjU3OSAxNTAuMTQ0NyAzMDQuMzg5NSAyMzYuNDczN0MzMTAuMDU5NSAyNDIuMjI4OSAzMTMuNTEyNiAyNTAuMTU4NCAzMTMuNTEyNiAyNTguODU1M1MzMTAuMDE2OCAyNzUuNDgxNiAzMDQuMzQ2OCAyODEuMjM2OEwzMDQuMzQ2OCAyODEuMjM2OFpNNDU0LjY2NTggMzQ5LjY2MDVDNDUyLjE5MzIgMzUwLjM0MjYgNDQ5LjM3OTUgMzUwLjcyNjMgNDQ2LjQ4MDUgMzUwLjcyNjMgNDMxLjg1NzkgMzUwLjcyNjMgNDE5LjUzNzQgMzQwLjkyMTEgNDE1LjcwMDUgMzI3LjQ5MjFMNDE1LjY1NzkgMzI3LjI3ODkgMzI0Ljg1MjYtNC42MDc5QzMyNC4xNzA1LTcuMDgwNSAzMjMuNzg2OC05Ljg5NDIgMzIzLjc4NjgtMTIuNzkzMiAzMjMuNzg2OC0yNy40MTU4IDMzMy41OTIxLTM5LjczNjMgMzQ3LjAyMTEtNDMuNTczMkwzNDcuMjM0Mi00My42MTU4SDM1NS41NDc0QzM3MC4zNDA1LTQzLjQ0NTMgMzgyLjcwMzctMzMuMjU2MyAzODYuMTk5NS0xOS41Mjg5TDM4Ni4yNDIxLTE5LjMxNTggNDc3LjA0NzQgMzEwLjY1MjZDNDc3LjcyOTUgMzEzLjEyNTMgNDc4LjExMzIgMzE1LjkzODkgNDc4LjExMzIgMzE4LjgzNzkgNDc4LjExMzIgMzMzLjQ2MDUgNDY4LjMwNzkgMzQ1Ljc4MTEgNDU0Ljg3ODkgMzQ5LjYxNzlMNDU0LjY2NTggMzQ5LjY2MDVaIiAgaG9yaXotYWR2LXg9IjgxMCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxQjIiIHVuaWNvZGU9IiYjeEUxQjI7IiBkPSJNNDkzLjcyOTEgMjM2LjQwOTFDNDg3LjkzMDUgMjQyLjIwNzYgNDc5Ljg3MjMgMjQ1LjgzMTcgNDcxLjAwMzkgMjQ1LjgzMTcgNDUzLjI2NzIgMjQ1LjgzMTcgNDM4Ljg5ODcgMjMxLjQ2MzMgNDM4Ljg5ODcgMjEzLjcyNjUgNDM4Ljg5ODcgMjA0Ljg1ODIgNDQyLjQ4MDIgMTk2Ljg0MjUgNDQ4LjMyMTQgMTkxLjAwMTRMNTIwLjU5IDExOC43MzI3IDQ0OC4zMjE0IDQ0LjU0NTVDNDQyLjUyMjggMzguNzQ2OSA0MzguODk4NyAzMC42ODg2IDQzOC44OTg3IDIxLjg2MjkgNDM4Ljg5ODcgNC4xMjYyIDQ1My4yNjcyLTEwLjI0MjMgNDcxLjAwMzktMTAuMjQyMyA0NzkuODcyMy0xMC4yNDIzIDQ4Ny44ODc5LTYuNjYwOCA0OTMuNzI5MS0wLjgxOTZWLTAuODE5Nkw1OTAuMzAwNSA5Ny4wMzA4QzU5Ni4xNDE2IDEwMi44Mjk0IDU5OS43NjU3IDExMC44NDUgNTk5Ljc2NTcgMTE5Ljc1NlM1OTYuMTQxNiAxMzYuNjgyNiA1OTAuMzAwNSAxNDIuNDM4NUw1OTAuMzAwNSAxNDIuNDM4NVpNMjc5LjQ4MTQgMjM2LjQwOTFDMjczLjY4MjggMjQyLjI1MDMgMjY1LjY2NzIgMjQ1Ljg3NDQgMjU2Ljc5ODggMjQ1Ljg3NDRTMjM5Ljg3MjIgMjQyLjI1MDMgMjM0LjExNjMgMjM2LjQwOTFMMjM0LjExNjMgMjM2LjQwOTEgMTM5LjQ2MzUgMTQyLjM5NTlDMTMzLjYyMjQgMTM2LjU5NzQgMTI5Ljk5ODMgMTI4LjU4MTcgMTI5Ljk5ODMgMTE5LjY3MDdTMTMzLjYyMjQgMTAyLjc0NDEgMTM5LjQ2MzUgOTYuOTg4MkwyMzQuNzU1OCAxLjY5NTlDMjM5LjU3MzctMS4zMzEzIDI0NS40MTQ5LTMuMTY0NiAyNTEuNjgyNS0zLjE2NDYgMjY5LjMzMzktMy4xNjQ2IDI4My42NTk3IDExLjE2MTIgMjgzLjY1OTcgMjguODEyNiAyODMuNjU5NyAzNC41Njg1IDI4Mi4xMjQ4IDQwLjAyNiAyNzkuNDM4NyA0NC42NzM0TDI3OS41MjQgNDQuNTAyOCAyMDYuNjE1OCAxMTkuMzI5NiAyNzkuNTI0IDE5Mi4yMzc4QzI4NC45ODE1IDE5Ny45NTExIDI4OC4zNDk3IDIwNS43NTM1IDI4OC4zNDk3IDIxNC4zMjM1UzI4NC45ODE1IDIzMC42NTMyIDI3OS41MjQgMjM2LjQwOTFMMjc5LjUyNCAyMzYuNDA5MVpNNDEzLjE0NjQgMzAwLjM2MzZDNDEwLjY3MzUgMzAxLjA0NTggNDA3Ljg1OTUgMzAxLjQyOTUgNDA0Ljk2MDIgMzAxLjQyOTUgMzkwLjMzNTkgMzAxLjQyOTUgMzc4LjAxNCAyOTEuNjIzMiAzNzQuMTc2NyAyNzguMTkyN0wzNzQuMTM0MSAyNzcuOTc5NSAyOTIuMjcyMy0xOS40MDkxQzI5MS41OTAxLTIxLjg4MiAyOTEuMjA2NC0yNC42OTYgMjkxLjIwNjQtMjcuNTk1MyAyOTEuMjA2NC00Mi4yMTk1IDMwMS4wMTI3LTU0LjU0MTUgMzE0LjQ0MzItNTguMzc4N0wzMTQuNjU2NC01OC40MjE0SDMyMi45NzA1QzMzNy41OTQ3LTU4LjMzNjEgMzQ5LjkxNjYtNDguNDQ0NSAzNTMuNjI2LTM0Ljk3MTRMMzUzLjY2ODYtMzQuNzU4MiA0MzUuNTMwNSAyNjAuNzExOEM0MzYuMjk3OSAyNjMuMzU1MyA0MzYuNzY2OSAyNjYuMzgyNSA0MzYuNzY2OSAyNjkuNDk0OSA0MzYuNzY2OSAyODQuMTYxOCA0MjYuODc1MyAyOTYuNTY5IDQxMy4zNTk1IDMwMC4zMjFMNDEzLjE0NjQgMzAwLjM2MzZaTTkyNC4xNDMyIDUxOC40NDg2VjUyMi4yODU5QzkyMi44NjQxIDUyOC4wNDE4IDkyMC4xNzggNTMzLjAzMDMgOTE2LjQ2ODYgNTM2Ljk5NTVMOTE2LjQ2ODYgNTM2Ljk5NTUgNjQ5Ljc3ODIgODAyLjQwNjhDNjQ2LjExMTUgODA2LjcxMzEgNjQxLjMzNjIgODEwLjAzODcgNjM1LjkyMTQgODExLjkxNDdMNjM1LjcwODIgODEySDI4OS4wNzQ1QzI4OC42OTA4IDgxMiAyODguMjIxOCA4MTIgMjg3Ljc5NTUgODEyIDIzOC4wODE1IDgxMiAxOTcuNzA0OCA3NzIuMDQ5NyAxOTYuOTggNzIyLjUwNjNMMTk2Ljk4IDcyMi40MjFWNzE2LjAyNTVIOTIuMDk0NUM5MS43MTA4IDcxNi4wMjU1IDkxLjI0MTggNzE2LjAyNTUgOTAuODE1NSA3MTYuMDI1NSA0MS4xMDE1IDcxNi4wMjU1IDAuNzI0OCA2NzYuMDc1MyAwIDYyNi41MzE4TDAgNjI2LjQ0NjVWLTEyMS44MjE2QzAuNzI0OC0xNzEuNDA3NyA0MS4xMDE1LTIxMS4zNTggOTAuODE1NS0yMTEuMzU4IDkxLjI4NDUtMjExLjM1OCA5MS43MTA4LTIxMS4zNTggOTIuMTc5OC0yMTEuMzU4TDkyLjA5NDUtMjExLjM1OEg2MzUuNzA4MkM2MzYuMDkxOS0yMTEuMzU4IDYzNi41NjA5LTIxMS4zNTggNjM2Ljk4NzMtMjExLjM1OCA2ODYuNzAxMy0yMTEuMzU4IDcyNy4wNzc5LTE3MS40MDc3IDcyNy44MDI3LTEyMS44NjQzTDcyNy44MDI3LTEyMS43NzlWLTExNS4zODM1SDgzMi4wNDg2QzgzMi40MzI0LTExNS4zODM1IDgzMi45MDE0LTExNS4zODM1IDgzMy4zMjc3LTExNS4zODM1IDg4My4wNDE3LTExNS4zODM1IDkyMy40MTg0LTc1LjQzMzMgOTI0LjE0MzItMjUuODg5OEw5MjQuMTQzMi0yNS44MDQ1VjUxNC42MTE0QzkyNC4xODU4IDUxNS4xNjU2IDkyNC4xODU4IDUxNS44NDc4IDkyNC4xODU4IDUxNi41M1M5MjQuMTQzMiA1MTcuODk0NCA5MjQuMTAwNSA1MTguNTMzOUw5MjQuMTAwNSA1MTguNDQ4NlpNNDYyLjM5MTQgNjA2LjcwNTlMNjE5LjA4IDQ1MC4wMTczSDQ2Mi4zOTE0Wk02NTguNzMxOCA3MDMuMjc3M0w4MTYuMDYgNTQ1Ljk0OTFINjU0LjI1NVpNMjYwLjkzNDUgNzIyLjQ2MzZDMjYxLjk1NzggNzM2Ljc4OTUgMjczLjg1MzQgNzQ4LjA0NTUgMjg4LjM0OTcgNzQ4LjA0NTUgMjg4LjYwNTUgNzQ4LjA0NTUgMjg4Ljg2MTQgNzQ4LjA0NTUgMjg5LjA3NDUgNzQ4LjA0NTVMMjg5LjAzMTkgNzQ4LjA0NTVINTk0LjczNDZWNTY2LjQxNDVMNDUyLjc1NTUgNzA2LjQ3NUM0NDguNzQ3NyA3MTAuMTQxNyA0NDMuNzU5MyA3MTIuODI3OCA0MzguMjU5MiA3MTQuMTA2OUw0MzguMDQ2IDcxNC4xNDk1SDI2MC44OTE5Wk02MzUuNzA4Mi0xNDcuMzE4Mkg5Mi4wOTQ1QzkxLjg4MTQtMTQ3LjMxODIgOTEuNjI1NS0xNDcuMzE4MiA5MS4zNjk3LTE0Ny4zMTgyIDc2Ljg3MzQtMTQ3LjMxODIgNjQuOTc3OC0xMzYuMDYyMiA2My45NTQ1LTEyMS44MjE2TDYzLjk1NDUtMTIxLjczNjRWNjI2LjUzMThDNjQuOTc3OCA2NDAuODU3NiA3Ni44NzM0IDY1Mi4xMTM2IDkxLjM2OTcgNjUyLjExMzYgOTEuNjI1NSA2NTIuMTEzNiA5MS44ODE0IDY1Mi4xMTM2IDkyLjA5NDUgNjUyLjExMzZMOTIuMDUxOSA2NTIuMTEzNkgzOTguMzk0MlY0MTguNjc5NUMzOTguMzk0MiA0MDEuMDI4MSA0MTIuNzIgMzg2LjcwMjMgNDMwLjM3MTUgMzg2LjcwMjNWMzg2LjcwMjNINjYzLjgwNTVWLTEyMS4wOTY4QzY2My4xMjM0LTEzNS43MjExIDY1MS4wNTczLTE0Ny4zMTgyIDYzNi4zNDc3LTE0Ny4zMTgyIDYzNi4wOTE5LTE0Ny4zMTgyIDYzNS44Nzg3LTE0Ny4zMTgyIDYzNS42NjU1LTE0Ny4zMTgyTDYzNS43MDgyLTE0Ny4zMTgyWk04MzIuNjg4Mi01MS4zODY0SDcyNy44MDI3VjQxOC42Nzk1QzcyNy44NDU0IDQxOS4yMzM4IDcyNy44NDU0IDQxOS45MTYgNzI3Ljg0NTQgNDIwLjU5ODJTNzI3LjgwMjcgNDIxLjk2MjUgNzI3Ljc2MDEgNDIyLjYwMjFMNzI3Ljc2MDEgNDIyLjUxNjhWNDI4LjI3MjdDNzI1LjYyODMgNDMzLjQzMTcgNzIyLjM0NTMgNDM3LjczOCA3MTguMjA5NSA0NDEuMDIxTDcxOC4xMjQzIDQ0MS4wNjM2IDY3Ni41NTM4IDQ4Mi42MzQxSDg2MC4xMDM0Vi0yNS44MDQ1Qzg1OS4wODAxLTQwLjEzMDQgODQ3LjE4NDUtNTEuMzg2NCA4MzIuNjg4Mi01MS4zODY0IDgzMi42NDU1LTUxLjM4NjQgODMyLjY0NTUtNTEuMzg2NCA4MzIuNjAyOS01MS4zODY0SDgzMi42MDI5WiIgIGhvcml6LWFkdi14PSI5MzgiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMUIzIiB1bmljb2RlPSImI3hFMUIzOyIgZD0iTTg4MS45Mi0yLjA4TDc1My45MiAxMjUuOTIgNzUwLjg4IDEyOC40OEEzNTIgMzUyIDAgMSAxIDY4NS42IDU4LjcyTDY4NS42IDU4LjcyIDgxMy42LTY5LjI4QTQ4IDQ4IDAgMSAxIDg4MS40NC0xLjQ0Wk00NjQgNDRBMjg4IDI4OCAwIDEgMCA3NTIgMzMyIDI4OCAyODggMCAwIDAgNDY0IDQ0WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTFCNCIgdW5pY29kZT0iJiN4RTFCNDsiIGQ9Ik03NjggMzI4LjE2Qzc3NC4xODY3IDM0MC44MzIgNzc3LjgxMzMgMzU1LjcyMjcgNzc3LjgxMzMgMzcxLjQ2NjcgNzc3LjgxMzMgMzk5LjMyOCA3NjYuNDY0IDQyNC41NDQgNzQ4LjE2IDQ0Mi43MiA3MTYuMDc0NyA0NjcuNjM3MyA2NzUuMjg1MyA0ODIuNjU2IDYzMC45NTQ3IDQ4Mi42NTYgNTk2LjQzNzMgNDgyLjY1NiA1NjQuMDEwNyA0NzMuNTI1MyA1MzYuMDIxMyA0NTcuNTY4TDUzNi45NiA0NTguMDhDNTM5LjEzNiA0NjYuNTI4IDU0MC4zNzMzIDQ3Ni4yNTYgNTQwLjM3MzMgNDg2LjI0IDU0MC4zNzMzIDUyMi40NjQgNTIzLjkwNCA1NTQuODQ4IDQ5OC4wOTA3IDU3Ni4zNTIgNDc1Ljc3NiA1ODcuNjU4NyA0NDkuNjY0IDU5NC4xODY3IDQyMi4wNTg3IDU5NC4xODY3UzM2OC4zNDEzIDU4Ny42NTg3IDM0NS4yMTYgNTc2LjA1MzNDLTM1LjI0MjcgMzYwLjIwMjctMC4wNDI3IDE0MS4zMjI3LTAuMDQyNyAxMzcuNDgyNy0wLjA0MjctMy4zMTczIDIwNC4xMTczLTEzMS4zMTczIDQyOC43NTczLTEzMS4zMTczIDQzNy44ODgtMTMxLjg3MiA0NDguNTEyLTEzMi4yMTMzIDQ1OS4yNjQtMTMyLjIxMzMgNjEwLjA0OC0xMzIuMjEzMyA3NDYuMDI2Ny02OC43NjggODQxLjk4NCAzMi45MDY3IDg3NC40OTYgNjkuMzAxMyA4OTQuMjA4IDExNy4yMTYgODk0LjIwOCAxNjkuNzM4NyA4OTQuMjA4IDE4Mi43NTIgODkzLjAxMzMgMTk1LjUwOTMgODkwLjY2NjcgMjA3Ljg4MjcgODcxLjA4MjcgMjY0LjQxNiA4MjYuMDY5MyAzMDkuMDAyNyA3NjkuMzIyNyAzMjcuODE4N1pNODMyIDM4MEM4MzYuMjY2NyAzNzguMTIyNyA4NDEuMjE2IDM3Ny4wMTMzIDg0Ni40MjEzIDM3Ny4wMTMzIDg2MS4zOTczIDM3Ny4wMTMzIDg3NC4yODI3IDM4Ni4wNTg3IDg3OS44NzIgMzk4Ljk0NCA4ODguMTA2NyA0MTUuNTQxMyA4OTIuODQyNyA0MzQuNzg0IDg5Mi44NDI3IDQ1NS4xNzg3IDg5Mi44NDI3IDUyNS44NzczIDgzNS41NDEzIDU4My4xNzg3IDc2NC44NDI3IDU4My4xNzg3IDc0NC4zMiA1ODMuMTc4NyA3MjQuOTA2NyA1NzguMzU3MyA3MDcuNzEyIDU2OS43Mzg3IDY5Ni4xNDkzIDU2NC4wNjQgNjg3Ljc4NjcgNTUxLjYwNTMgNjg3Ljc4NjcgNTM3LjIyNjcgNjg3Ljc4NjcgNTE3LjA4OCA3MDQuMTI4IDUwMC43NDY3IDcyNC4yNjY3IDUwMC43NDY3IDcyOC43MDQgNTAwLjc0NjcgNzMyLjkyOCA1MDEuNTE0NyA3MzYuODUzMyA1MDIuOTY1MyA3NDMuMjUzMyA1MDUuODI0IDc1MS4wMTg3IDUwNy41NzMzIDc1OS4yMTA3IDUwNy41NzMzIDc5MC42NTYgNTA3LjU3MzMgODE2LjE3MDcgNDgyLjA1ODcgODE2LjE3MDcgNDUwLjYxMzMgODE2LjE3MDcgNDQyLjQ2NCA4MTQuNDY0IDQzNC42OTg3IDgxMS4zNDkzIDQyNy42NTg3IDgwOS43MjggNDIzLjkwNCA4MDguNzA0IDQxOS4wODI3IDgwOC43MDQgNDE0LjA0OCA4MDguNzA0IDM5OC42NDUzIDgxOC4yNjEzIDM4NS41MDQgODMxLjc0NCAzODAuMTI4Wk03NTkuMDQgNzE2QzczNi4yMTMzIDcxNS44MjkzIDcxNC4xOTczIDcxMi44IDY5My4yMDUzIDcwNy4yNTMzIDY4MC43ODkzIDcwMi40NzQ3IDY3MC44MDUzIDY4OS4wNzczIDY3MC44MDUzIDY3My4yOTA3IDY3MC44MDUzIDY1My4xNTIgNjg3LjE0NjcgNjM2LjgxMDcgNzA3LjI4NTMgNjM2LjgxMDcgNzA5LjI5MDcgNjM2LjgxMDcgNzExLjI1MzMgNjM2Ljk4MTMgNzEzLjE3MzMgNjM3LjI4IDcyNy4xMjUzIDY0MC45OTIgNzQzLjM4MTMgNjQzLjEyNTMgNzYwLjEwNjcgNjQzLjEyNTMgODY2LjEzMzMgNjQzLjEyNTMgOTUyLjEwNjcgNTU3LjE1MiA5NTIuMTA2NyA0NTEuMTI1MyA5NTIuMTA2NyA0MjcuMTg5MyA5NDcuNzEyIDQwNC4yNzczIDkzOS43MzMzIDM4My4xMTQ3IDkzOC43OTQ3IDM4MC43MjUzIDkzNy45ODQgMzc2LjQ1ODcgOTM3Ljk4NCAzNzEuOTc4NyA5MzcuOTg0IDM1Ni4zMiA5NDcuODQgMzQyLjk2NTMgOTYxLjY2NCAzMzcuODAyNyA5NjUuNjMyIDMzNi4zNTIgOTY5Ljg5ODcgMzM1LjU0MTMgOTc0LjM3ODcgMzM1LjU0MTMgOTkwLjAzNzMgMzM1LjU0MTMgMTAwMy4zOTIgMzQ1LjM5NzMgMTAwOC41NTQ3IDM1OS4yMjEzIDEwMTguNzUyIDM4Ni40ODUzIDEwMjQuNjQgNDE3Ljc2IDEwMjQuNjQgNDUwLjM1NzMgMTAyNC42NCA1OTcuMTczMyA5MDUuODEzMyA3MTYuMjEzMyA3NTkuMDgyNyA3MTYuNTk3M1oiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxQjUiIHVuaWNvZGU9IiYjeEUxQjU7IiBkPSJNNDI5LjQ0LTEzMS4zNkMyMDUuNDQtMTMxLjM2IDAuNjQtMy4zNiAwLjY0IDEzNy40NCAwIDE0MS4yOC0zNS4yIDM2MC4xNiAzNDYuMjQgNTc2LjQ4IDM2OC4zODQgNTg3LjYxNiAzOTQuNDUzMyA1OTQuMTQ0IDQyMi4xMDEzIDU5NC4xNDRTNDc1LjgxODcgNTg3LjYxNiA0OTguOTQ0IDU3Ni4wMTA3QzUyMy4xMzYgNTU0Ljg0OCA1MzkuMDA4IDUyMi45NzYgNTM5LjAwOCA0ODcuMzkyIDUzOS4wMDggNDc4LjYwMjcgNTM4LjAyNjcgNDcwLjAyNjcgNTM2LjE5MiA0NjEuNzQ5M0w1MzYuMzIgNDYyLjUxNzNDNTYzLjM3MDcgNDc3Ljk2MjcgNTk1Ljc1NDcgNDg3LjA5MzMgNjMwLjMxNDcgNDg3LjA5MzMgNjc0LjY0NTMgNDg3LjA5MzMgNzE1LjQ3NzMgNDcyLjA3NDcgNzQ3Ljk0NjcgNDQ2LjgxNiA3NjYuOTc2IDQyOC43NjggNzc5LjA5MzMgNDAyLjc4NCA3NzkuMDkzMyAzNzQuMDI2NyA3NzkuMDkzMyAzNTcuMjU4NyA3NzQuOTk3MyAzNDEuNDcyIDc2Ny43NDQgMzI3LjU2MjcgODI2LjYyNCAzMDkuMjU4NyA4NzIuMTA2NyAyNjQuNTg2NyA4OTEuNzc2IDIwNy44ODI3IDg5NC4yOTMzIDE5NS40NjY3IDg5NS41MzA3IDE4Mi43MDkzIDg5NS41MzA3IDE2OS42NTMzIDg5NS41MzA3IDExNy4xMzA3IDg3NS44MTg3IDY5LjIxNiA4NDMuMzkyIDMyLjg2NCA3NDcuMzkyLTY4Ljg1MzMgNjExLjQxMzMtMTMyLjM0MTMgNDYwLjU4NjctMTMyLjM0MTMgNDQ5LjY2NC0xMzIuMzQxMyA0MzguNzg0LTEzMiA0MjcuOTg5My0xMzEuMzZaTTQyOS40NCA1MjkuMTJDNDA4LjMyIDUyOC40OCAzODguMzk0NyA1MjQuMDQyNyAzNzAuMDQ4IDUxNi41MzMzIDM5LjY4IDMyOC44IDY0IDE0NS4xMiA2NCAxNDMuMiA2NCA0NS4yOCAyMjcuMi02Ny4zNiA0MjguOC02Ny4zNiA0MzcuNzYtNjcuOTU3MyA0NDguMjEzMy02OC4zNDEzIDQ1OC43NTItNjguMzQxMyA1ODkuNjk2LTY4LjM0MTMgNzA3LjkyNTMtMTQuMDI2NyA3OTIuMTkyIDczLjI2OTMgODE3LjYyMTMgOTkuMjUzMyA4MzMuMjM3MyAxMzQuNjI0IDgzMy4yMzczIDE3My43MDY3IDgzMy4yMzczIDE4MC4zMiA4MzIuNzY4IDE4Ni44NDggODMxLjkxNDcgMTkzLjIwNTMgODEyLjIwMjcgMjM3LjE5NDcgNzcxLjE1NzMgMjY5LjMyMjcgNzIyLjAwNTMgMjc2LjIzNDdMNjg1LjQ0IDI4My4zNiA3MDQgMzM3LjEyQzcyNS4xMiAzNzguMDggNzEwLjQgMzkyLjE2IDcwNCAzOTcuMjggNjgzLjY5MDcgNDEwLjY3NzMgNjU4LjgxNiA0MTguNjU2IDYzMi4wNjQgNDE4LjY1NiA2MDcuOTE0NyA0MTguNjU2IDU4NS4yNTg3IDQxMi4xNzA3IDU2NS43NiA0MDAuODIxMyA1NDkuNzYgMzkyLjIwMjcgNTAyLjQgMzY3LjI0MjcgNDc2LjggMzk0LjEyMjdTNDY1LjI4IDQ1MS43MjI3IDQ3Ni44IDQ3MC45MjI3IDQ3Ni44IDUxMS44ODI3IDQ2NCA1MjEuNDgyN0M0NTYuNTMzMyA1MjYuNDc0NyA0NDcuMzYgNTI5LjQ2MTMgNDM3LjQ2MTMgNTI5LjQ2MTMgNDM1LjU0MTMgNTI5LjQ2MTMgNDMzLjYyMTMgNTI5LjMzMzMgNDMxLjc0NCA1MjkuMTJaTTgzMiAzODBDODM2LjI2NjcgMzc4LjEyMjcgODQxLjIxNiAzNzcuMDEzMyA4NDYuNDIxMyAzNzcuMDEzMyA4NjEuMzk3MyAzNzcuMDEzMyA4NzQuMjgyNyAzODYuMDU4NyA4NzkuODcyIDM5OC45NDQgODg4LjEwNjcgNDE1LjU0MTMgODkyLjg0MjcgNDM0Ljc4NCA4OTIuODQyNyA0NTUuMTc4NyA4OTIuODQyNyA1MjUuODc3MyA4MzUuNTQxMyA1ODMuMTc4NyA3NjQuODQyNyA1ODMuMTc4NyA3NDQuMzIgNTgzLjE3ODcgNzI0LjkwNjcgNTc4LjM1NzMgNzA3LjcxMiA1NjkuNzM4NyA2OTYuMTQ5MyA1NjQuMDY0IDY4Ny43ODY3IDU1MS42MDUzIDY4Ny43ODY3IDUzNy4yMjY3IDY4Ny43ODY3IDUxNy4wODggNzA0LjEyOCA1MDAuNzQ2NyA3MjQuMjY2NyA1MDAuNzQ2NyA3MjguNzA0IDUwMC43NDY3IDczMi45MjggNTAxLjUxNDcgNzM2Ljg1MzMgNTAyLjk2NTMgNzQzLjI1MzMgNTA1LjgyNCA3NTEuMDE4NyA1MDcuNTczMyA3NTkuMjEwNyA1MDcuNTczMyA3OTAuNjU2IDUwNy41NzMzIDgxNi4xNzA3IDQ4Mi4wNTg3IDgxNi4xNzA3IDQ1MC42MTMzIDgxNi4xNzA3IDQ0Mi40NjQgODE0LjQ2NCA0MzQuNjk4NyA4MTEuMzQ5MyA0MjcuNjU4NyA4MDkuNiA0MjMuNzc2IDgwOC41MzMzIDQxOC43ODQgODA4LjUzMzMgNDEzLjU3ODcgODA4LjUzMzMgMzk4LjYwMjcgODE3LjU3ODcgMzg1LjcxNzMgODMwLjQ2NCAzODAuMTI4Wk03NTkuMDQgNzE2QzczNi4yMTMzIDcxNS44MjkzIDcxNC4xOTczIDcxMi44IDY5My4yMDUzIDcwNy4yNTMzIDY4MC43ODkzIDcwMi40NzQ3IDY3MC44MDUzIDY4OS4wNzczIDY3MC44MDUzIDY3My4yOTA3IDY3MC44MDUzIDY1My4xNTIgNjg3LjE0NjcgNjM2LjgxMDcgNzA3LjI4NTMgNjM2LjgxMDcgNzA5LjI5MDcgNjM2LjgxMDcgNzExLjI1MzMgNjM2Ljk4MTMgNzEzLjE3MzMgNjM3LjI4IDcyNy4xMjUzIDY0MC45OTIgNzQzLjM4MTMgNjQzLjEyNTMgNzYwLjEwNjcgNjQzLjEyNTMgODY2LjEzMzMgNjQzLjEyNTMgOTUyLjEwNjcgNTU3LjE1MiA5NTIuMTA2NyA0NTEuMTI1MyA5NTIuMTA2NyA0MjcuMTg5MyA5NDcuNzEyIDQwNC4yNzczIDkzOS43MzMzIDM4My4xMTQ3IDkzOC43OTQ3IDM4MC43MjUzIDkzNy45ODQgMzc2LjQ1ODcgOTM3Ljk4NCAzNzEuOTc4NyA5MzcuOTg0IDM1Ni4zMiA5NDcuODQgMzQyLjk2NTMgOTYxLjY2NCAzMzcuODAyNyA5NjUuNjMyIDMzNi4zNTIgOTY5Ljg5ODcgMzM1LjU0MTMgOTc0LjM3ODcgMzM1LjU0MTMgOTkwLjAzNzMgMzM1LjU0MTMgMTAwMy4zOTIgMzQ1LjM5NzMgMTAwOC41NTQ3IDM1OS4yMjEzIDEwMTguNzUyIDM4Ni40ODUzIDEwMjQuNjQgNDE3Ljc2IDEwMjQuNjQgNDUwLjM1NzMgMTAyNC42NCA1OTcuMTczMyA5MDUuODEzMyA3MTYuMjEzMyA3NTkuMDgyNyA3MTYuNTk3M1oiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxQjYiIHVuaWNvZGU9IiYjeEUxQjY7IiBkPSJNOTYwIDE0MEg5MTJWMjY4QzkxMiAzMDMuMzI4IDg4My4zMjggMzMyIDg0OCAzMzJINTQ0VjQ2MEg1OTJDNjI3LjMyOCA0NjAgNjU2IDQ4OC42NzIgNjU2IDUyNFY2ODRDNjU2IDcxOS4zMjggNjI3LjMyOCA3NDggNTkyIDc0OEg0MzJDMzk2LjY3MiA3NDggMzY4IDcxOS4zMjggMzY4IDY4NFY1MjRDMzY4IDQ4OC42NzIgMzk2LjY3MiA0NjAgNDMyIDQ2MEg0ODBWMzMySDE3NkMxNDAuNjcyIDMzMiAxMTIgMzAzLjMyOCAxMTIgMjY4VjE0MEg2NEMyOC42NzIgMTQwIDAgMTExLjMyOCAwIDc2Vi04NEMwLTExOS4zMjggMjguNjcyLTE0OCA2NC0xNDhIMjI0QzI1OS4zMjgtMTQ4IDI4OC0xMTkuMzI4IDI4OC04NFY3NkMyODggMTExLjMyOCAyNTkuMzI4IDE0MCAyMjQgMTQwSDE3NlYyNjhINDgwVjE0MEg0MzJDMzk2LjY3MiAxNDAgMzY4IDExMS4zMjggMzY4IDc2Vi04NEMzNjgtMTE5LjMyOCAzOTYuNjcyLTE0OCA0MzItMTQ4SDU5MkM2MjcuMzI4LTE0OCA2NTYtMTE5LjMyOCA2NTYtODRWNzZDNjU2IDExMS4zMjggNjI3LjMyOCAxNDAgNTkyIDE0MEg1NDRWMjY4SDg0OFYxNDBIODAwQzc2NC42NzIgMTQwIDczNiAxMTEuMzI4IDczNiA3NlYtODRDNzM2LTExOS4zMjggNzY0LjY3Mi0xNDggODAwLTE0OEg5NjBDOTk1LjMyOC0xNDggMTAyNC0xMTkuMzI4IDEwMjQtODRWNzZDMTAyNCAxMTEuMzI4IDk5NS4zMjggMTQwIDk2MCAxNDBaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMUI3IiB1bmljb2RlPSImI3hFMUI3OyIgZD0iTTk2MCAxNDBIOTEyVjI2OEM5MTIgMzAzLjMyOCA4ODMuMzI4IDMzMiA4NDggMzMySDU0NFY0NjBINTkyQzYyNy4zMjggNDYwIDY1NiA0ODguNjcyIDY1NiA1MjRWNjg0QzY1NiA3MTkuMzI4IDYyNy4zMjggNzQ4IDU5MiA3NDhINDMyQzM5Ni42NzIgNzQ4IDM2OCA3MTkuMzI4IDM2OCA2ODRWNTI0QzM2OCA0ODguNjcyIDM5Ni42NzIgNDYwIDQzMiA0NjBINDgwVjMzMkgxNzZDMTQwLjY3MiAzMzIgMTEyIDMwMy4zMjggMTEyIDI2OFYxNDBINjRDMjguNjcyIDE0MCAwIDExMS4zMjggMCA3NlYtODRDMC0xMTkuMzI4IDI4LjY3Mi0xNDggNjQtMTQ4SDIyNEMyNTkuMzI4LTE0OCAyODgtMTE5LjMyOCAyODgtODRWNzZDMjg4IDExMS4zMjggMjU5LjMyOCAxNDAgMjI0IDE0MEgxNzZWMjY4SDQ4MFYxNDBINDMyQzM5Ni42NzIgMTQwIDM2OCAxMTEuMzI4IDM2OCA3NlYtODRDMzY4LTExOS4zMjggMzk2LjY3Mi0xNDggNDMyLTE0OEg1OTJDNjI3LjMyOC0xNDggNjU2LTExOS4zMjggNjU2LTg0Vjc2QzY1NiAxMTEuMzI4IDYyNy4zMjggMTQwIDU5MiAxNDBINTQ0VjI2OEg4NDhWMTQwSDgwMEM3NjQuNjcyIDE0MCA3MzYgMTExLjMyOCA3MzYgNzZWLTg0QzczNi0xMTkuMzI4IDc2NC42NzItMTQ4IDgwMC0xNDhIOTYwQzk5NS4zMjgtMTQ4IDEwMjQtMTE5LjMyOCAxMDI0LTg0Vjc2QzEwMjQgMTExLjMyOCA5OTUuMzI4IDE0MCA5NjAgMTQwWk00MzIgNTI0VjY4NEg1OTJWNTI0Wk0yMjQtODRINjRWNzZIMjI0Wk01OTIgNzZWLTg0SDQzMlY3NlpNOTYwLTg0SDgwMFY3Nkg5NjBaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMUI4IiB1bmljb2RlPSImI3hFMUI4OyIgZD0iTTUxMiA4MTJDMjI5LjI0OCA4MTIgMCA1ODIuNzUyIDAgMzAwUzIyOS4yNDgtMjEyIDUxMi0yMTJDNzk0Ljc1Mi0yMTIgMTAyNCAxNy4yNDggMTAyNCAzMDBTNzk0Ljc1MiA4MTIgNTEyIDgxMlpNMzA0IDUwOEMzMzAuNDk2IDUwOCAzNTIgNDg2LjQ5NiAzNTIgNDYwUzMzMC40OTYgNDEyIDMwNCA0MTJDMjc3LjUwNCA0MTIgMjU2IDQzMy41MDQgMjU2IDQ2MFMyNzcuNTA0IDUwOCAzMDQgNTA4Wk01MTIgNDRDMzgzLjYxNiA0NS40MDggMjc3LjQxODcgMTM4LjgwNTMgMjU2LjIxMzMgMjYxLjMwMTMgMjU1Ljc0NCAyNjQuNDE2IDI1NS41NzMzIDI2Ni4xNjUzIDI1NS41NzMzIDI2OCAyNTUuNTczMyAyODUuODc3MyAyNzAuMDggMzAwLjQyNjcgMjg4IDMwMC40MjY3IDMwNC4wODUzIDMwMC40MjY3IDMxNy40NCAyODguNjkzMyAzMTkuOTU3MyAyNzMuMzMzMyAzMzYuOTM4NyAxODAuMzYyNyA0MTUuOTU3MyAxMTAuNjAyNyA1MTEuNzAxMyAxMDguMDQyNyA1MTIuNTU0NyAxMDguMDQyNyA1MTMuMjM3MyAxMDguMDQyNyA1MTMuOTYyNyAxMDguMDQyNyA2MTAuMzA0IDEwOC4wNDI3IDY5MC4wNDggMTc4Ljk5NzMgNzAzLjg3MiAyNzEuNDk4NyA3MDYuNDMyIDI4OC4zNTIgNzE5Ljk1NzMgMzAwLjM0MTMgNzM2LjI5ODcgMzAwLjM0MTMgNzM3Ljc5MiAzMDAuMzQxMyA3MzkuMjQyNyAzMDAuMjU2IDc0MC42NTA3IDMwMC4wNDI3IDc1Ni4wMTA3IDI5Ny42NTMzIDc2Ny43NDQgMjg0LjQyNjcgNzY3Ljc0NCAyNjguNDI2NyA3NjcuNzQ0IDI2Ni43MiA3NjcuNjE2IDI2NS4wNTYgNzY3LjM2IDI2My4zOTIgNzQ3LjUyIDEzOC43NjI3IDY0MC44NTMzIDQ0LjQ2OTMgNTEyLjA4NTMgNDQuMDQyN1pNNzIwIDQxMkM2OTMuNTA0IDQxMiA2NzIgNDMzLjUwNCA2NzIgNDYwUzY5My41MDQgNTA4IDcyMCA1MDhDNzQ2LjQ5NiA1MDggNzY4IDQ4Ni40OTYgNzY4IDQ2MFM3NDYuNDk2IDQxMiA3MjAgNDEyWiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTFCOSIgdW5pY29kZT0iJiN4RTFCOTsiIGQ9Ik0yNTYgNDYwQzI1NiA0ODYuMjQgMjc3Ljc2IDUwOCAzMDQgNTA4UzM1MiA0ODYuMjQgMzUyIDQ2MEMzNTIgNDMzLjc2IDMzMC4yNCA0MTIgMzA0IDQxMlMyNTYgNDMzLjc2IDI1NiA0NjBaTTEwMjQgMzAwQzEwMjQgMTcuNzYgNzk0LjI0LTIxMiA1MTItMjEyUzAgMTcuNzYgMCAzMDAgMjI5Ljc2IDgxMiA1MTIgODEyIDEwMjQgNTgyLjI0IDEwMjQgMzAwWk05NjAgMzAwQzk2MCA1NDcuMDQgNzU5LjA0IDc0OCA1MTIgNzQ4UzY0IDU0Ny4wNCA2NCAzMDBDNjQgNTIuOTYgMjY0Ljk2LTE0OCA1MTItMTQ4Uzk2MCA1Mi45NiA5NjAgMzAwWk03MjAgNTA4QzY5My43NiA1MDggNjcyIDQ4Ni4yNCA2NzIgNDYwUzY5My43NiA0MTIgNzIwIDQxMiA3NjggNDMzLjc2IDc2OCA0NjBDNzY4IDQ4Ni4yNCA3NDYuMjQgNTA4IDcyMCA1MDhaTTc0MC40OCAyOTkuMzZDNzIzLjIgMzAxLjkyIDcwNi41NiAyODkuNzYgNzA0IDI3Mi40OCA2OTAuNTYgMTc5LjA0IDYwOCAxMDggNTEyIDEwOCA0MTkuMiAxMDggMzM0LjcyIDE4MC4zMiAzMTkuMzYgMjczLjEyIDMxNi44IDI5MC40IDMwMC4xNiAzMDIuNTYgMjgyLjg4IDI5OS4zNiAyNjUuNiAyOTYuOCAyNTMuNDQgMjgwLjE2IDI1Ni42NCAyNjIuODggMjc3LjEyIDEzOC4wOCAzODcuMiA0NCA1MTIgNDQgNjM5LjM2IDQ0IDc0OC44IDEzOC4wOCA3NjcuMzYgMjYzLjUyIDc3MC41NiAyODAuOCA3NTguNCAyOTYuOCA3NDAuNDggMjk5LjM2WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTFCQSIgdW5pY29kZT0iJiN4RTFCQTsiIGQ9Ik0zMzYgNDI1LjkyTDMzNi04NCA0MzItODQgNDMyIDY4NCAxNjAgNDI4IDMzNiA0MjUuOTJaTTY4OCAxNzMuOTJMNjg4IDY4NCA1OTIgNjg0IDU5Mi04NCA4NjQgMTcyIDY4OCAxNzMuOTJaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMUJCIiB1bmljb2RlPSImI3hFMUJCOyIgZD0iTTEwMjAuOCA0MjhDMTAxMy4zMzMzIDQ1MS44NTA3IDk5Mi45Mzg3IDQ2OS40NzIgOTY4LjAyMTMgNDcyLjc1NzNMNjkzLjEyIDUxNi4zMiA1NzIuMTYgNzczLjZDNTYyLjk4NjcgNzk4LjM4OTMgNTM5LjUyIDgxNS43NTQ3IDUxMiA4MTUuNzU0N1M0NjEuMDEzMyA3OTguMzg5MyA0NTEuOTY4IDc3NC4wMjY3TDMyOC45NiA1MTQuNCA1Ni4zMiA0NzIuOEMyMi44NjkzIDQ3MC40OTYtMy4zNzA3IDQ0Mi43NjI3LTMuMzcwNyA0MDguOTI4LTMuMzcwNyAzODkuNDI5MyA1LjMzMzMgMzcxLjkzNiAxOS4xMTQ3IDM2MC4yMDI3TDIxOC44OCAxNTIuNzU3MyAxNzIuMTYtMTM0LjYwMjdDMTcwLjgzNzMtMTM5LjQ2NjcgMTcwLjA2OTMtMTQ1LjA1NiAxNzAuMDY5My0xNTAuODE2IDE3MC4wNjkzLTE4Ni4xNDQgMTk4Ljc0MTMtMjE0LjgxNiAyMzQuMDY5My0yMTQuODE2IDI0Ny41MDkzLTIxNC44MTYgMjYwLjAxMDctMjEwLjY3NzMgMjcwLjI5MzMtMjAzLjU5NDdMNTEyLTY5Ljk2MjcgNzUyLjY0LTIwMy4wODI3Qzc2Mi43MDkzLTIxMC4wMzczIDc3NS4yMTA3LTIxNC4xNzYgNzg4LjY1MDctMjE0LjE3NiA4MjMuOTc4Ny0yMTQuMTc2IDg1Mi42NTA3LTE4NS41MDQgODUyLjY1MDctMTUwLjE3NiA4NTIuNjUwNy0xNDQuNDE2IDg1MS44ODI3LTEzOC44MjY3IDg1MC40NzQ3LTEzMy41MzZMODA0LjQ4IDE1NS45NTczIDEwMDQuMTYgMzYwLjc1NzNDMTAxNi41MzMzIDM3Mi40NDggMTAyNC4yMTMzIDM4OC45NiAxMDI0LjIxMzMgNDA3LjMwNjcgMTAyNC4yMTMzIDQxNC42ODggMTAyMi45NzYgNDIxLjgxMzMgMTAyMC42MjkzIDQyOC40MjY3WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTFCQyIgdW5pY29kZT0iJiN4RTFCQzsiIGQ9Ik03ODUuOTItMjEyQzc4NS43OTItMjEyIDc4NS42MjEzLTIxMiA3ODUuNDkzMy0yMTIgNzczLjg4OC0yMTIgNzYzLjAwOC0yMDguOTI4IDc1My42MjEzLTIwMy41MDkzTDUxMi02OS45MiAyNjguOC0yMDMuMDRDMjU4LjczMDctMjA5Ljk5NDcgMjQ2LjIyOTMtMjE0LjEzMzMgMjMyLjc4OTMtMjE0LjEzMzMgMTk3LjQ2MTMtMjE0LjEzMzMgMTY4Ljc4OTMtMTg1LjQ2MTMgMTY4Ljc4OTMtMTUwLjEzMzMgMTY4Ljc4OTMtMTQ0LjM3MzMgMTY5LjU1NzMtMTM4Ljc4NCAxNzAuOTY1My0xMzMuNDkzM0wyMTcuNiAxNTMuMzk3MyAxOS4yIDM2MC4xMTczQzUuMzMzMyAzNzEuOTM2LTMuMzcwNyAzODkuMzg2Ny0zLjM3MDcgNDA4Ljg4NTMtMy4zNzA3IDQ0Mi43MiAyMi44NjkzIDQ3MC40MTA3IDU2LjEwNjcgNDcyLjcxNDdMMzI4Ljk2IDUxNC4zMTQ3IDQ1MS44NCA3NzMuNTE0N0M0NjEuMDEzMyA3OTguMzA0IDQ4NC40OCA4MTUuNjY5MyA1MTIgODE1LjY2OTNTNTYyLjk4NjcgNzk4LjMwNCA1NzIuMDMyIDc3My45NDEzTDY5My4xMiA1MTcuNTE0NyA5NjcuNjggNDczLjk5NDdDMTAwMS4wODggNDcxLjYwNTMgMTAyNy4yODUzIDQ0My45NTczIDEwMjcuMjg1MyA0MTAuMTY1MyAxMDI3LjI4NTMgMzkxLjAwOCAxMDE4Ljg4IDM3My44MTMzIDEwMDUuNTI1MyAzNjIuMDhMODA1Ljc2IDE1Ny4yMzczIDg1MS44NC0xMzIuNjgyN0M4NTIuNzM2LTEzNi43MzYgODUzLjI5MDctMTQxLjM4NjcgODUzLjI5MDctMTQ2LjEyMjcgODUzLjI5MDctMTgxLjQ1MDcgODI0LjYxODctMjEwLjEyMjcgNzg5LjI5MDctMjEwLjEyMjcgNzg4Ljc3ODctMjEwLjEyMjcgNzg4LjI2NjctMjEwLjEyMjcgNzg3Ljc5NzMtMjEwLjEyMjdaTTUxMi01LjkyQzUxMi4xMjgtNS45MiA1MTIuMjk4Ny01LjkyIDUxMi40MjY3LTUuOTIgNTI0LjAzMi01LjkyIDUzNC45MTItOC45OTIgNTQ0LjI5ODctMTQuNDEwN0w3ODQuNjQtMTQ4IDc0MS43NiAxNDIuNTZDNzQxLjA3NzMgMTQ2LjAxNiA3NDAuNzM2IDE0OS45ODQgNzQwLjczNiAxNTQuMDM3MyA3NDAuNzM2IDE3MS44MjkzIDc0Ny45ODkzIDE4Ny45MTQ3IDc1OS42OCAxOTkuNTJMOTYwIDQwNC45NiA2ODQuOCA0NTEuMDRDNjYyLjMxNDcgNDU0LjE5NzMgNjQzLjg0IDQ2OC42NjEzIDYzNS4wNTA3IDQ4OC4zNzMzTDUxMiA3NDggMzg5LjEyIDQ4OC44QzM4MC4xNiA0NjguNjYxMyAzNjEuNjg1MyA0NTQuMTk3MyAzMzkuNTQxMyA0NTEuMDgyN0w2NCA0MDkuNDQgMjYyLjQgMjAwLjE2QzI3NC4wOTA3IDE4OC41NTQ3IDI4MS4zNDQgMTcyLjQ2OTMgMjgxLjM0NCAxNTQuNjc3MyAyODEuMzQ0IDE1MC42MjQgMjgwLjk2IDE0Ni42NTYgMjgwLjIzNDcgMTQyLjc3MzNMMjM1LjQ3NzMtMTQ4LjA0MjcgNDc5Ljk1NzMtMjAuMDQyN0M0ODguNzQ2Ny0xMi43NDY3IDQ5OS42MjY3LTcuNzEyIDUxMS42MTYtNi4wMDUzWiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTFCRCIgdW5pY29kZT0iJiN4RTFCRDsiIGQ9Ik04MDAgNjIwSDIyNEMyMDYuMDggNjIwIDE5MiA2MDUuOTIgMTkyIDU4OFYxMkMxOTItNS45MiAyMDYuMDgtMjAgMjI0LTIwSDgwMEM4MTcuOTItMjAgODMyLTUuOTIgODMyIDEyVjU4OEM4MzIgNjA1LjkyIDgxNy45MiA2MjAgODAwIDYyMFoiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxQkUiIHVuaWNvZGU9IiYjeEUxQkU7IiBkPSJNODAwIDYyMEgyMjRDMjA2LjA4IDYyMCAxOTIgNjA1LjkyIDE5MiA1ODhWMTJDMTkyLTUuOTIgMjA2LjA4LTIwIDIyNC0yMEg4MDBDODE3LjkyLTIwIDgzMi01LjkyIDgzMiAxMlY1ODhDODMyIDYwNS45MiA4MTcuOTIgNjIwIDgwMCA2MjBaTTc2OCA0NEgyNTZWNTU2SDc2OFY0NFoiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxQkYiIHVuaWNvZGU9IiYjeEUxQkY7IiBkPSJNNDMyLjY0IDIzNkg1ODkuNDRMNTEwLjA4IDQ5Ni40OCA0MzIuNjQgMjM2Wk01MTIgODEyQzIyOS4yNDggODEyIDAgNTgyLjc1MiAwIDMwMFMyMjkuMjQ4LTIxMiA1MTItMjEyQzc5NC43NTItMjEyIDEwMjQgMTcuMjQ4IDEwMjQgMzAwUzc5NC43NTIgODEyIDUxMiA4MTJaTTY4MS42IDQ0SDY3MkM2NzEuOTU3MyA0NCA2NzEuODcyIDQ0IDY3MS43ODY3IDQ0IDY1Ny41MzYgNDQgNjQ1LjQ2MTMgNTMuMzAxMyA2NDEuMzIyNyA2Ni4xODY3TDYwOS4yOCAxNzJINDE3LjI4TDM4NCA2Ni40QzM3OS44NjEzIDUyLjQwNTMgMzY3LjEwNCA0Mi4zNzg3IDM1MiA0Mi4zNzg3IDMzMy42MTA3IDQyLjM3ODcgMzE4LjY3NzMgNTcuMzEyIDMxOC42NzczIDc1LjcwMTMgMzE4LjY3NzMgNzkuMDI5MyAzMTkuMTQ2NyA4Mi4xODY3IDMyMC4wNDI3IDg1LjIxNkw0NTMuMTIgNTE1LjA0QzQ2Mi45MzMzIDUzOC41OTIgNDg1Ljc2IDU1NC44NDggNTEyLjM4NCA1NTQuODQ4IDUzNy4zMDEzIDU1NC44NDggNTU4Ljg0OCA1NDAuNjQgNTY5LjQyOTMgNTE5Ljg2MTNMNzA0IDg1LjU1NzNDNzA1LjE1MiA4Mi40IDcwNS43OTIgNzguNzczMyA3MDUuNzkyIDc0Ljk3NiA3MDUuNzkyIDYwLjA4NTMgNjk1LjU5NDcgNDcuNTQxMyA2ODEuODEzMyA0NFoiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxQzAiIHVuaWNvZGU9IiYjeEUxQzA7IiBkPSJNNTEyIDgxMkMyMjkuNzYgODEyIDAgNTgyLjI0IDAgMzAwUzIyOS43Ni0yMTIgNTEyLTIxMiAxMDI0IDE3Ljc2IDEwMjQgMzAwIDc5NC4yNCA4MTIgNTEyIDgxMlpNNTEyLTE0OEMyNjQuOTYtMTQ4IDY0IDUyLjk2IDY0IDMwMFMyNjQuOTYgNzQ4IDUxMiA3NDhDNzU5LjA0IDc0OCA5NjAgNTQ3LjA0IDk2MCAzMDBTNzU5LjA0LTE0OCA1MTItMTQ4Wk01NjkuNiA1MTkuNTJDNTQ3Ljg0IDU2NC4zMiA0NzguMDggNTY4LjggNDUzLjEyIDUxNS4wNEwzMjEuMjggODUuNkMzMTYuMTYgNjguOTYgMzI1Ljc2IDUxLjA0IDM0Mi40IDQ1LjI4IDM1OS42OCA0MC4xNiAzNzYuOTYgNDkuNzYgMzgyLjA4IDY2LjRMNDEzLjQ0IDE3MkM0MTQuNzIgMTcyLjY0IDQxNS4zNiAxNzIgNDE2IDE3Mkg2MDhDNjA4LjY0IDE3MiA2MDguNjQgMTcyIDYwOS4yOCAxNzJMNjQxLjkyIDY2LjRDNjQ1Ljc2IDUyLjk2IDY1OC41NiA0NCA2NzIgNDQgNjc1LjIgNDQgNjc4LjQgNDQuNjQgNjgxLjYgNDUuMjggNjk4LjI0IDUwLjQgNzA3Ljg0IDY4LjMyIDcwMi43MiA4NS42TDU2OS42IDUxOS41MlpNNDMyLjY0IDIzNkw1MDkuNDQgNDk2LjQ4IDU4OS40NCAyMzZINDMyLjY0WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTFDMSIgdW5pY29kZT0iJiN4RTFDMTsiIGQ9Ik01MTIgODEyQzIyOS4yNDggODEyIDAgNTgyLjc1MiAwIDMwMFMyMjkuMjQ4LTIxMiA1MTItMjEyQzc5NC43NTItMjEyIDEwMjQgMTcuMjQ4IDEwMjQgMzAwUzc5NC43NTIgODEyIDUxMiA4MTJaTTcyMi41NiAxMDhDNzIyLjU2IDk5LjE2OCA3MTUuMzkyIDkyIDcwNi41NiA5Mkg2NzQuNTZDNjY1LjcyOCA5MiA2NTguNTYgOTkuMTY4IDY1OC41NiAxMDhWMTQ2LjRDNjIwLjc1NzMgMTA2Ljg5MDcgNTY3LjU5NDcgODIuMzU3MyA1MDguNjcyIDgyLjM1NzMgNTA2LjkyMjcgODIuMzU3MyA1MDUuMTczMyA4Mi40IDUwMy40MjQgODIuNDQyNyAzODMuNjU4NyA4NS4zNDQgMjg3LjQ0NTMgMTgzLjM0OTMgMjg3LjQ0NTMgMzAzLjc5NzMgMjg3LjQ0NTMgMzA5LjIxNiAyODcuNjU4NyAzMTQuNTkyIDI4OC4wNDI3IDMxOS45MjUzIDI4Ny43MDEzIDMyMy40MjQgMjg3LjU3MzMgMzI4LjMzMDcgMjg3LjU3MzMgMzMzLjI4IDI4Ny41NzMzIDQ1Ni4yODggMzg3LjI4NTMgNTU2IDUxMC4yOTMzIDU1NiA1MTAuODkwNyA1NTYgNTExLjQ4OCA1NTYgNTEyLjEyOCA1NTYgNTE2Ljc3ODcgNTU2LjQyNjcgNTIyLjMyNTMgNTU2LjY0IDUyNy45MTQ3IDU1Ni42NCA2MTEuMjQyNyA1NTYuNjQgNjgyLjE5NzMgNTAzLjUyIDcwOC43MzYgNDI5LjMyMjcgNzEwLjA1ODcgNDI2LjAzNzMgNzEwLjU3MDcgNDIzLjc3NiA3MTAuNTcwNyA0MjEuMzg2NyA3MTAuNTcwNyA0MTMuNDA4IDcwNC43MjUzIDQwNi43OTQ3IDY5Ny4wODggNDA1LjZMNjYzLjcyMjcgNDAwLjQ4QzY2Mi45MTIgNDAwLjMwOTMgNjYxLjk3MzMgNDAwLjIyNCA2NjAuOTkyIDQwMC4yMjQgNjU0LjI1MDcgNDAwLjIyNCA2NDguNTMzMyA0MDQuNTc2IDY0Ni40NDI3IDQxMC41OTIgNjMwLjM1NzMgNDY0LjMwOTMgNTgxLjQ2MTMgNTAyLjc1MiA1MjMuNTYyNyA1MDIuNzUyIDUxOS41MDkzIDUwMi43NTIgNTE1LjQ1NiA1MDIuNTgxMyA1MTEuNDg4IDUwMi4xOTczIDQyMy4xMjUzIDQ5OC44MjY3IDM1Mi4zNDEzIDQyNS45OTQ3IDM1Mi4zNDEzIDMzNi42MDggMzUyLjM0MTMgMzMwLjQ2NCAzNTIuNjgyNyAzMjQuNDQ4IDM1My4zMjI3IDMxOC40NzQ3IDM1My4yMzczIDIxMy42IDQxNy4yMzczIDEzMy42IDUwNS41NTczIDEzMy42IDU3NC43NjI3IDEzNC4xNTQ3IDYzMy41NTczIDE3OC4wMTYgNjU2LjIxMzMgMjM5LjM3MDdMNjU2LjU5NzMgMjg0SDUxNy4wNzczQzUwOC4yNDUzIDI4NCA1MDEuMDc3MyAyOTEuMTY4IDUwMS4wNzczIDMwMFYzMjMuNjhDNTAxLjA3NzMgMzMyLjUxMiA1MDguMjQ1MyAzMzkuNjggNTE3LjA3NzMgMzM5LjY4SDcwOS4wNzczQzcxNy45MDkzIDMzOS42OCA3MjUuMDc3MyAzMzIuNTEyIDcyNS4wNzczIDMyMy42OFoiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxQzIiIHVuaWNvZGU9IiYjeEUxQzI7IiBkPSJNNTEyIDgxMkMyMjkuNzYgODEyIDAgNTgyLjI0IDAgMzAwUzIyOS43Ni0yMTIgNTEyLTIxMiAxMDI0IDE3Ljc2IDEwMjQgMzAwIDc5NC4yNCA4MTIgNTEyIDgxMlpNNTEyLTE0OEMyNjQuOTYtMTQ4IDY0IDUyLjk2IDY0IDMwMFMyNjQuOTYgNzQ4IDUxMiA3NDhDNzU5LjA0IDc0OCA5NjAgNTQ3LjA0IDk2MCAzMDBTNzU5LjA0LTE0OCA1MTItMTQ4Wk03MjIuNTYgMzIzLjY4VjEwNS40NEM3MjIuNTYgOTYuNDggNzE1LjUyIDg5LjQ0IDcwNi41NiA4OS40NEg2NzQuNTZDNjY1LjYgODkuNDQgNjU4LjU2IDk2LjQ4IDY1OC41NiAxMDUuNDRWMTQzLjg0QzYyMC4xNiAxMDIuMjQgNTY1LjEyIDc4LjU2IDUwMy42OCA3OC41NiAzOTYuOCA3OC41NiAyODggMTYxLjEyIDI4OCAzMTkuODQgMjg4IDQ2MC42NCAzODEuNDQgNTU4LjU2IDUxNC41NiA1NTguNTYgNjQwLjY0IDU1OC41NiA2ODYuMDggNDkwLjA4IDcxMS42OCA0MzEuMiA3MTMuNiA0MjYuNzIgNzEzLjYgNDIxLjYgNzExLjA0IDQxNy4xMlM3MDQgNDA5LjQ0IDY5OS41MiA0MDguMTZMNjY2LjI0IDQwMy4wNEM2NTguNTYgNDAxLjc2IDY1MS41MiA0MDYuMjQgNjQ4Ljk2IDQxMy4yOCA2MjYuNTYgNDcyLjE2IDU4MS43NiA1MDIuMjQgNTE0LjU2IDUwMi4yNCA0MTkuODQgNTAyLjI0IDM1My4yOCA0MjYuNzIgMzUzLjI4IDMxOS4yIDM1My4yOCAyMTMuNiA0MTkuMiAxMzMuNiA1MDUuNiAxMzMuNiA1NzIuMTYgMTMzLjYgNjI4LjQ4IDE3My4yOCA2NTYuNjQgMjQwLjQ4VjI4NEg1MTcuMTJDNTA4LjE2IDI4NCA1MDEuMTIgMjkxLjY4IDUwMS4xMiAzMDBWMzIzLjY4QzUwMS4xMiAzMzIuNjQgNTA4LjE2IDMzOS42OCA1MTcuMTIgMzM5LjY4SDcwNi41NkM3MTQuODggMzM5LjY4IDcyMi41NiAzMzIuNjQgNzIyLjU2IDMyMy42OFoiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxQzMiIHVuaWNvZGU9IiYjeEUxQzM7IiBkPSJNNTEyIDgxMkMyMjkuMjQ4IDgxMiAwIDU4Mi43NTIgMCAzMDBTMjI5LjI0OC0yMTIgNTEyLTIxMkM3OTQuNzUyLTIxMiAxMDI0IDE3LjI0OCAxMDI0IDMwMFM3OTQuNzUyIDgxMiA1MTIgODEyWk03MDQgNDRWNDRDNjg2LjMzNiA0NCA2NzIgNTguMzM2IDY3MiA3Nkw2NjguOCA0ODUuNiA1NDAuOCAxOTEuODRWMTg3LjM2QzUzOS42NDggMTg1LjQ0IDUzOC4zNjggMTgzLjczMzMgNTM2Ljk2IDE4Mi4yNCA1MzQuOTU0NyAxODAuMjc3MyA1MzIuNjA4IDE3OC41NzA3IDUzMC4wOTA3IDE3Ny4yMDUzTDUyOS45MiAxNzcuMTJINDk5Ljg0TDQ5My40NCAxODEuNkM0OTIuMDMyIDE4My4wOTMzIDQ5MC43NTIgMTg0LjggNDg5LjY4NTMgMTg2LjU5Mkw0ODkuNiAxOTEuMiAzNjEuNiA0ODMuMDQgMzUyIDc2QzM1MiA1OC4zMzYgMzM3LjY2NCA0NCAzMjAgNDRWNDRDMzAyLjMzNiA0NCAyODggNTguMzM2IDI4OCA3NkwyOTQuNCA1MTguODhDMzA1LjEwOTMgNTQwLjA4NTMgMzI2Ljc0MTMgNTU0LjMzNiAzNTEuNzAxMyA1NTQuMzM2UzM5OC4yNTA3IDU0MC4wODUzIDQwOC44MzIgNTE5LjI2NEw1MTIuMDQyNyAyODQgNjE0LjQ0MjcgNTE4LjI0QzYyNS4wNjY3IDUzOS43ODY3IDY0Ni44MjY3IDU1NC4zMzYgNjcyLjA0MjcgNTU0LjMzNlM3MTkuMDE4NyA1MzkuNzg2NyA3MjkuNDcyIDUxOC42MjRMNzI5LjY0MjcgNTA0LjggNzMzLjQ4MjcgNzUuMzZDNzMzLjE4NCA1OC44MDUzIDcyMC4zODQgNDUuMzY1MyA3MDQuMTcwNyA0NFoiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxQzQiIHVuaWNvZGU9IiYjeEUxQzQ7IiBkPSJNNTEyIDgxMkMyMjkuNzYgODEyIDAgNTgyLjI0IDAgMzAwUzIyOS43Ni0yMTIgNTEyLTIxMiAxMDI0IDE3Ljc2IDEwMjQgMzAwIDc5NC4yNCA4MTIgNTEyIDgxMlpNNTEyLTE0OEMyNjQuOTYtMTQ4IDY0IDUyLjk2IDY0IDMwMFMyNjQuOTYgNzQ4IDUxMiA3NDhDNzU5LjA0IDc0OCA5NjAgNTQ3LjA0IDk2MCAzMDBTNzU5LjA0LTE0OCA1MTItMTQ4Wk03MzIuMTYgNTA2LjA4TDczNiA3Ni42NEM3MzYgNTguNzIgNzIxLjkyIDQ0LjY0IDcwNCA0NC42NCA3MDQgNDQuNjQgNzA0IDQ0LjY0IDcwNCA0NC42NCA2ODYuNzIgNDQuNjQgNjcyIDU4LjcyIDY3MiA3Ni42NEw2NjguOCA0ODYuMjQgNTQxLjQ0IDE5MS4yQzU0MC44IDE4OS4yOCA1MzkuNTIgMTg4LjY0IDUzOC4yNCAxODYuNzJTNTM2LjMyIDE4Mi44OCA1MzQuNCAxODEuNkM1MzIuNDggMTc5LjY4IDUyOS45MiAxNzcuNzYgNTI3LjM2IDE3Ni40OCA1MjYuNzIgMTc1Ljg0IDUyNi4wOCAxNzUuMiA1MjQuOCAxNzQuNTYgNTI0LjggMTc0LjU2IDUyNC44IDE3NC41NiA1MjQuMTYgMTc0LjU2IDUyMS42IDE3My4yOCA1MTkuMDQgMTczLjI4IDUxNS44NCAxNzIuNjQgNTE0LjU2IDE3Mi42NCA1MTMuMjggMTcyIDUxMiAxNzJTNTA5LjQ0IDE3Mi42NCA1MDguMTYgMTcyLjY0QzUwNC45NiAxNzMuMjggNTAyLjQgMTczLjI4IDQ5OS44NCAxNzQuNTYgNDk5Ljg0IDE3NC41NiA0OTkuODQgMTc0LjU2IDQ5OS4yIDE3NC41NiA0OTcuOTIgMTc1LjIgNDk3LjI4IDE3Ni40OCA0OTYgMTc3LjEyIDQ5My40NCAxNzguNCA0OTEuNTIgMTc5LjY4IDQ4OS42IDE4MS42IDQ4Ny42OCAxODIuODggNDg3LjA0IDE4NC44IDQ4NS43NiAxODYuNzJTNDgzLjIgMTg5LjI4IDQ4Mi41NiAxOTEuMkwzNTUuMiA0ODMuMDQgMzUyIDc2QzM1MiA1OC4wOCAzMzcuMjggNDQgMzIwIDQ0IDMyMCA0NCAzMjAgNDQgMzIwIDQ0IDMwMi4wOCA0NCAyODggNTguNzIgMjg4IDc2TDI5NC40IDUxOC44OEMzMTYuMTYgNTY0LjMyIDM4Ny44NCA1NjQuMzIgNDA4Ljk2IDUxOC44OEw1MTIgMjg0IDYxNC40IDUxOC4yNEM2MzYuOCA1NjUuNiA3MDcuODQgNTY0LjMyIDcyOS42IDUxOS41Mkw3MzIuMTYgNTA2LjA4WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTFDNSIgdW5pY29kZT0iJiN4RTFDNTsiIGQ9Ik01MjggNDkySDQzMlYyNzUuNjhINTI4QzUzMC42NDUzIDI3NS40NjY3IDUzMy43MTczIDI3NS4zMzg3IDUzNi44MzIgMjc1LjMzODcgNTk4Ljk5NzMgMjc1LjMzODcgNjUwLjA2OTMgMzIyLjc0MTMgNjU1Ljk1NzMgMzgzLjMyOCA2NTAuMDY5MyA0NDQuOTM4NyA1OTguOTk3MyA0OTIuMjk4NyA1MzYuODMyIDQ5Mi4yOTg3IDUzMy43MTczIDQ5Mi4yOTg3IDUzMC42NDUzIDQ5Mi4xNzA3IDUyNy41NzMzIDQ5MS45NTczWk01MTIgODEyQzIyOS4yNDggODEyIDAgNTgyLjc1MiAwIDMwMFMyMjkuMjQ4LTIxMiA1MTItMjEyQzc5NC43NTItMjEyIDEwMjQgMTcuMjQ4IDEwMjQgMzAwUzc5NC43NTIgODEyIDUxMiA4MTJaTTUyOCAyMTEuNjhINDMyVjc2QzQzMiA1OC4zMzYgNDE3LjY2NCA0NCA0MDAgNDRTMzY4IDU4LjMzNiAzNjggNzZWNTI0QzM2OCA1NDEuNjY0IDM4Mi4zMzYgNTU2IDQwMCA1NTZINTI4QzUzMC43NzMzIDU1Ni4xNzA3IDUzNC4wMTYgNTU2LjI1NiA1MzcuMjU4NyA1NTYuMjU2IDYzNC42MjQgNTU2LjI1NiA3MTQuMTk3MyA0ODAuMjY2NyA3MTkuOTU3MyAzODQuMzUyIDcxNC4xOTczIDI4Ny40NTYgNjM0LjU4MTMgMjExLjQ2NjcgNTM3LjI1ODcgMjExLjQ2NjcgNTM0LjAxNiAyMTEuNDY2NyA1MzAuNzczMyAyMTEuNTUyIDUyNy41MzA3IDIxMS43MjI3WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTFDNiIgdW5pY29kZT0iJiN4RTFDNjsiIGQ9Ik01MTIgODEyQzIyOS43NiA4MTIgMCA1ODIuMjQgMCAzMDBTMjI5Ljc2LTIxMiA1MTItMjEyIDEwMjQgMTcuNzYgMTAyNCAzMDAgNzk0LjI0IDgxMiA1MTIgODEyWk01MTItMTQ4QzI2NC45Ni0xNDggNjQgNTIuOTYgNjQgMzAwUzI2NC45NiA3NDggNTEyIDc0OEM3NTkuMDQgNzQ4IDk2MCA1NDcuMDQgOTYwIDMwMFM3NTkuMDQtMTQ4IDUxMi0xNDhaTTUyOCA1NTZINDAwQzM4Mi4wOCA1NTYgMzY4IDU0MS45MiAzNjggNTI0Vjc2QzM2OCA1OC4wOCAzODIuMDggNDQgNDAwIDQ0UzQzMiA1OC4wOCA0MzIgNzZWMjExLjY4SDUyOEM2MzMuNiAyMTEuNjggNzIwIDI4OS4xMiA3MjAgMzgzLjg0UzYzMy42IDU1NiA1MjggNTU2Wk01MjggMjc1LjY4SDQzMlY0OTJINTI4QzU5OC40IDQ5MiA2NTYgNDQzLjM2IDY1NiAzODMuODRTNTk4LjQgMjc1LjY4IDUyOCAyNzUuNjhaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMUM4IiB1bmljb2RlPSImI3hFMUM4OyIgZD0iTTM4NCA3ODBWNDYwQzM4NCA0NDIuMDggMzY5LjkyIDQyOCAzNTIgNDI4SDMyQzE0LjA4IDQyOCAwIDQ0Mi4wOCAwIDQ2MFMxNC4wOCA0OTIgMzIgNDkySDMyMFY3ODBDMzIwIDc5Ny45MiAzMzQuMDggODEyIDM1MiA4MTJTMzg0IDc5Ny45MiAzODQgNzgwWk02NzIgNDI4SDk5MkMxMDA5LjkyIDQyOCAxMDI0IDQ0Mi4wOCAxMDI0IDQ2MFMxMDA5LjkyIDQ5MiA5OTIgNDkySDcwNFY3ODBDNzA0IDc5Ny45MiA2ODkuOTIgODEyIDY3MiA4MTJTNjQwIDc5Ny45MiA2NDAgNzgwVjQ2MEM2NDAgNDQyLjA4IDY1NC4wOCA0MjggNjcyIDQyOFpNMzUyIDE3MkgzMkMxNC4wOCAxNzIgMCAxNTcuOTIgMCAxNDBTMTQuMDggMTA4IDMyIDEwOEgzMjBWLTE4MEMzMjAtMTk3LjkyIDMzNC4wOC0yMTIgMzUyLTIxMlMzODQtMTk3LjkyIDM4NC0xODBWMTQwQzM4NCAxNTcuOTIgMzY5LjkyIDE3MiAzNTIgMTcyWk05OTIgMTcySDY3MkM2NTQuMDggMTcyIDY0MCAxNTcuOTIgNjQwIDE0MFYtMTgwQzY0MC0xOTcuOTIgNjU0LjA4LTIxMiA2NzItMjEyUzcwNC0xOTcuOTIgNzA0LTE4MFYxMDhIOTkyQzEwMDkuOTIgMTA4IDEwMjQgMTIyLjA4IDEwMjQgMTQwUzEwMDkuOTIgMTcyIDk5MiAxNzJaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMUM3IiB1bmljb2RlPSImI3hFMUM3OyIgZD0iTTg2NCAzOTZIMzQ1Ljc2VjQ0NEExNzYgMTc2IDAgMCAwIDY4MS43NiA1MTguNzIgMzIgMzIgMCAxIDEgNzM5LjY4IDU0Ni4wOCAyNDAgMjQwIDAgMCAxIDI4MS43NiA0NDRWMzk2SDE2MEEzMC40IDMwLjQgMCAwIDEgMTI4IDM2Ny44NFYtNTUuMzZBMzAuNzIgMzAuNzIgMCAwIDEgMTYwLTg0SDg2NEEzMC43MiAzMC43MiAwIDAgMSA4OTYtNTUuMzZWMzY3LjM2QTMwLjcyIDMwLjcyIDAgMCAxIDg2NCAzOTZaTTU1MiAxNTEuMDRWNjkuMjhBNDAgNDAgMCAwIDAgNDcyIDY5LjI4VjE1MS4wNEE4MCA4MCAwIDEgMCA1NTIgMTUxLjA0WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTFDOSIgdW5pY29kZT0iJiN4RTFDOTsiIGQ9Ik00NzIgMTM1LjA0VjUyQTQwIDQwIDAgMCAxIDU1MiA1MlYxMzUuMDRBODAgODAgMCAxIDEgNDcyIDEzNS4wNFpNODY0IDM5NkgzNDUuNzZWNDQ0QTE3NiAxNzYgMCAwIDAgNjgxLjc2IDUxOC43MiAzMiAzMiAwIDEgMSA3MzkuNjggNTQ2LjA4IDI0MCAyNDAgMCAwIDEgMjgxLjc2IDQ0NFYzOTZIMTYwQTMwLjQgMzAuNCAwIDAgMSAxMjggMzY3Ljg0Vi01NS4zNkEzMC43MiAzMC43MiAwIDAgMSAxNjAtODRIODY0QTMwLjcyIDMwLjcyIDAgMCAxIDg5Ni01NS4zNlYzNjcuMzZBMzAuNzIgMzAuNzIgMCAwIDEgODY0IDM5NlpNODMyLTIwSDE5MlYzMzJIODMyWiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTFDQSIgdW5pY29kZT0iJiN4RTFDQTsiIGQ9Ik04OTYgMTQwLjY0Qzg5NiAxNDMuMiA4OTUuMzYgMTQ1LjEyIDg5NC43MiAxNDcuNjggODk0LjA4IDE0OS42IDg5NC4wOCAxNTEuNTIgODkzLjQ0IDE1Mi44Uzg5Mi4xNiAxNTUuMzYgODkxLjUyIDE1NkM4OTAuMjQgMTU4LjU2IDg4OC45NiAxNjAuNDggODg3LjA0IDE2Mi40IDg4Ny4wNCAxNjIuNCA4ODcuMDQgMTYyLjQgODg3LjA0IDE2My4wNEw1MzAuNTYgNTQ3LjA0QzUyMC4zMiA1NTguNTYgNTAzLjY4IDU1OC41NiA0OTMuNDQgNTQ3LjA0TDEzNi45NiAxNjMuMDRDMTM2Ljk2IDE2My4wNCAxMzYuOTYgMTYyLjQgMTM2Ljk2IDE2Mi40IDEzNS4wNCAxNjAuNDggMTM0LjQgMTU4LjU2IDEzMy4xMiAxNTYgMTMyLjQ4IDE1NC43MiAxMzEuMiAxNTMuNDQgMTMwLjU2IDE1Mi4xNlMxMjkuOTIgMTQ4Ljk2IDEyOS4yOCAxNDcuMDRDMTI4LjY0IDE0NS43NiAxMjggMTQzLjIgMTI4IDE0MC42NCAxMjggMTQwLjY0IDEyOCAxNDAgMTI4IDE0MCAxMjggMTM4LjA4IDEyOC42NCAxMzYuOCAxMjguNjQgMTM1LjUyIDEyOC42NCAxMzIuOTYgMTI5LjI4IDEzMS4wNCAxMjkuOTIgMTI4LjQ4UzEzMS44NCAxMjQgMTMzLjEyIDEyMi4wOEMxMzMuNzYgMTIwLjggMTM0LjQgMTE5LjUyIDEzNS4wNCAxMTguMjQgMTM1LjA0IDExOC4yNCAxMzUuMDQgMTE4LjI0IDEzNS42OCAxMTcuNiAxMzYuOTYgMTE1LjY4IDEzOC44OCAxMTQuNCAxNDAuOCAxMTMuMTIgMTQyLjA4IDExMi40OCAxNDMuMzYgMTExLjIgMTQ0LjY0IDExMC41NlMxNDcuMiAxMDkuOTIgMTQ4LjQ4IDEwOS4yOEMxNTAuNCAxMDkuMjggMTUyLjMyIDEwOCAxNTQuODggMTA4IDE1NC44OCAxMDggMTU1LjUyIDEwOCAxNTUuNTIgMTA4SDg2OC40OEM4NzIuMzIgMTA4IDg3Ni4xNiAxMDguNjQgODc5LjM2IDExMC41NiA4ODAgMTEwLjU2IDg4MCAxMTEuMiA4ODAuNjQgMTExLjIgODgzLjg0IDExMy4xMiA4ODYuNCAxMTUuMDQgODg4Ljk2IDExNy42IDg4OC45NiAxMTcuNiA4ODguOTYgMTE3LjYgODg5LjYgMTE3LjYgODkwLjI0IDExOC44OCA4OTAuODggMTIwLjE2IDg5MS41MiAxMjEuNDQgODkyLjggMTIzLjM2IDg5NC4wOCAxMjUuMjggODk0LjcyIDEyNy44NCA4OTUuMzYgMTI5Ljc2IDg5NS4zNiAxMzIuMzIgODk2IDEzNC44OCA4OTYgMTM2LjggODk2LjY0IDEzOC4wOCA4OTYuNjQgMTM5LjM2IDg5NiAxNDAgODk2IDE0MC42NCA4OTYgMTQwLjY0WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTFDQiIgdW5pY29kZT0iJiN4RTFDQjsiIGQ9Ik05OTIgMjA0Qzk3NC4zMzYgMjA0IDk2MCAxODkuNjY0IDk2MCAxNzJWLTg0Qzk2MC0xMDEuNjY0IDk0NS42NjQtMTE2IDkyOC0xMTZIOTZDNzguMzM2LTExNiA2NC0xMDEuNjY0IDY0LTg0VjE3MkM2NCAxODkuNjY0IDQ5LjY2NCAyMDQgMzIgMjA0UzAgMTg5LjY2NCAwIDE3MlYtODRDMC0xMzcuMDM0NyA0Mi45NjUzLTE4MCA5Ni0xODBIOTI4Qzk4MS4wMzQ3LTE4MCAxMDI0LTEzNy4wMzQ3IDEwMjQtODRWMTcyQzEwMjQgMTg5LjY2NCAxMDA5LjY2NCAyMDQgOTkyIDIwNFpNMzcxLjg0IDU5NS4wNEw0ODAgNjgxLjQ0VjQxLjQ0QzQ4MCAyMy43NzYgNDk0LjMzNiA5LjQ0IDUxMiA5LjQ0UzU0NCAyMy43NzYgNTQ0IDQxLjQ0VjY4MS40NEw2NTIuMTYgNTk1LjA0QzY1Ny42MjEzIDU5MC42MDI3IDY2NC42NjEzIDU4Ny45MTQ3IDY3Mi4yOTg3IDU4Ny45MTQ3IDY5MC4wMDUzIDU4Ny45MTQ3IDcwNC4zODQgNjAyLjI5MzMgNzA0LjM4NCA2MjAgNzA0LjM4NCA2MzAuMDY5MyA2OTkuNzc2IDYzOS4wMjkzIDY5Mi41MjI3IDY0NC45MTczTDUzMi40OCA3NzIuOTZDNTI3LjUzMDcgNzc2Ljg4NTMgNTIxLjE3MzMgNzc5LjI3NDcgNTE0LjIxODcgNzc5LjI3NDdTNTAwLjk0OTMgNzc2Ljg4NTMgNDk1LjkxNDcgNzcyLjkxNzNMNDk1Ljk1NzMgNzcyLjk2IDMzNS45NTczIDY0NC45NkMzMjguNjYxMyA2MzkuMDI5MyAzMjQuMDUzMyA2MzAuMDY5MyAzMjQuMDUzMyA2MjAgMzI0LjA1MzMgNjAyLjI5MzMgMzM4LjQzMiA1ODcuOTE0NyAzNTYuMTM4NyA1ODcuOTE0NyAzNjMuODE4NyA1ODcuOTE0NyAzNzAuODU4NyA1OTAuNjAyNyAzNzYuMzYyNyA1OTUuMDgyN1oiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxQ0MiIHVuaWNvZGU9IiYjeEUxQ0M7IiBkPSJNNTEyIDc0OEMyNjQgNzQ4IDY0IDU0OCA2NCAzMDBTMjY0LTE0OCA1MTItMTQ4IDk2MCA1MiA5NjAgMzAwIDc2MCA3NDggNTEyIDc0OFpNNTEyIDY4NEM3MjQuOCA2ODQgODk2IDUxMi44IDg5NiAzMDAgODk2IDIzMS4yIDg3Ni44IDE2NCA4NDEuNiAxMDQuOCA2NTYgMjgwLjggMzY2LjQgMjgwLjggMTgwLjggMTA0LjggNzIgMjg3LjIgMTMyLjggNTIyLjQgMzE1LjIgNjMxLjIgMzc2IDY2NC44IDQ0My4yIDY4NCA1MTIgNjg0Wk01MTIgNjIwQzQxOS4yIDYyMCAzNDQgNTQ0LjggMzQ0IDQ1MlM0MTkuMiAyODQgNTEyIDI4NCA2ODAgMzU5LjIgNjgwIDQ1MiA2MDQuOCA2MjAgNTEyIDYyMFoiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxQ0QiIHVuaWNvZGU9IiYjeEUxQ0Q7IiBkPSJNNTEyIDc0OEMyNjQgNzQ4IDY0IDU0OCA2NCAzMDBTMjY0LTE0OCA1MTItMTQ4IDk2MCA1MiA5NjAgMzAwIDc2MCA3NDggNTEyIDc0OFpNNTEyIDY4NEM3MjQuOCA2ODQgODk2IDUxMi44IDg5NiAzMDAgODk2IDIyOCA4NzYuOCAxNjAuOCA4NDEuNiAxMDMuMiA2NzIgMjY2LjQgNDAwIDI4MC44IDIxMS4yIDEyOC44IDIwMS42IDEyMC44IDE5MiAxMTEuMiAxODIuNCAxMDMuMiAxNDcuMiAxNjAuOCAxMjggMjI4IDEyOCAzMDAgMTI4IDUxMi44IDI5OS4yIDY4NCA1MTIgNjg0Wk01MTItODRDMzk1LjItODQgMjg5LjYtMzEuMiAyMTkuMiA1MC40IDIyOC44IDYwIDI0MCA2OS42IDI1MS4yIDc5LjIgNDE3LjYgMjEzLjYgNjU2IDE5Ny42IDgwNC44IDUwLjQgNzM0LjQtMzEuMiA2MjguOC04NCA1MTItODRaTTUxMiA1NTZDNTY5LjYgNTU2IDYxNiA1MDkuNiA2MTYgNDUyUzU2OS42IDM0OCA1MTIgMzQ4IDQwOCAzOTQuNCA0MDggNDUyIDQ1NC40IDU1NiA1MTIgNTU2TTUxMiA2MjBDNDE5LjIgNjIwIDM0NCA1NDQuOCAzNDQgNDUyUzQxOS4yIDI4NCA1MTIgMjg0IDY4MCAzNTkuMiA2ODAgNDUyIDYwNC44IDYyMCA1MTIgNjIwWiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTFDRSIgdW5pY29kZT0iJiN4RTFDRTsiIGQ9Ik0xMDI0IDEwMi43MDkzQzEwMTMuMTYyNyAyMTYuMDc0NyA5MTguNCAzMDQuMDUzMyA4MDMuMDcyIDMwNC4wNTMzIDc5Ny4yMjY3IDMwNC4wNTMzIDc5MS40MjQgMzAzLjg0IDc4NS42NjQgMzAzLjM3MDcgNzgwLjYyOTMgMzAzLjk2OCA3NzMuODg4IDMwNC4yNjY3IDc2Ny4wNjEzIDMwNC4yNjY3IDY1MS42OTA3IDMwNC4yNjY3IDU1Ni44ODUzIDIxNi4yMDI3IDU0Ni4xNzYgMTAzLjYwNTMgNTU2Ljk3MDctMTAuNjU2IDY1MS43MzMzLTk4LjYzNDcgNzY3LjAxODctOTguNjM0NyA3NzIuODY0LTk4LjYzNDcgNzc4LjY2NjctOTguNDIxMyA3ODQuNDI2Ny05Ny45NTIgNzgzLjc0NC05Ny45OTQ3IDc4My43ODY3LTk3Ljk5NDcgNzgzLjg3Mi05Ny45OTQ3IDgwMi4xMzMzLTk3Ljk5NDcgODIwLjAxMDctOTYuMjQ1MyA4MzcuMzMzMy05Mi45MTczTDg1OC4xMTItODkuMTIgODc4LjU5Mi05OS4zNiA5MzMuMjA1My0xMjcuMzQ5M0g5MzkuMzQ5M0M5NDYuODU4Ny0xMjcuMzA2NyA5NTIuOTYtMTIxLjIwNTMgOTUyLjk2LTExMy42OTYgOTUyLjk2LTExMi4yNDUzIDk1Mi43NDY3LTExMC44MzczIDk1Mi4zMi0xMDkuNTE0N0w5NDcuNTg0LTk1LjI2NCA5MzQuNjEzMy01NS42NjkzIDk2My45NjgtMjYuMzE0N0M5OTkuMjk2IDUuOTQxMyAxMDIxLjk1MiA1MS40NjY3IDEwMjQuMDQyNyAxMDIuMzY4Wk03MDcuOTI1MyAxMzYuODQyN0M2OTEuMjQyNyAxMzcuMjI2NyA2NzcuODg4IDE1MC44MzczIDY3Ny44ODggMTY3LjU2MjcgNjc3Ljg4OCAxODQuNTQ0IDY5MS42MjY3IDE5OC4yODI3IDcwOC42MDggMTk4LjI4MjdTNzM5LjMyOCAxODQuNTQ0IDczOS4zMjggMTY3LjU2MjdDNzM5LjMyOCAxNjcuNTYyNyA3MzkuMzI4IDE2Ny41NjI3IDczOS4zMjggMTY3LjU2MjcgNzM5LjMyOCAxNTAuNTgxMyA3MjUuNTg5MyAxMzYuODQyNyA3MDguNjA4IDEzNi44NDI3IDcwOC4zNTIgMTM2Ljg0MjcgNzA4LjEzODcgMTM2Ljg0MjcgNzA3Ljg4MjcgMTM2Ljg0MjdaTTg2NC4yNTYgMTM2Ljg0MjdDODQ3LjU3MzMgMTM3LjIyNjcgODM0LjIxODcgMTUwLjgzNzMgODM0LjIxODcgMTY3LjU2MjcgODM0LjIxODcgMTg0LjU0NCA4NDcuOTU3MyAxOTguMjgyNyA4NjQuOTM4NyAxOTguMjgyN1M4OTUuNjU4NyAxODQuNTQ0IDg5NS42NTg3IDE2Ny41NjI3Qzg5NS42NTg3IDE2Ny41NjI3IDg5NS42NTg3IDE2Ny41NjI3IDg5NS42NTg3IDE2Ny41NjI3IDg5NS42NTg3IDE1MC41ODEzIDg4MS45MiAxMzYuODQyNyA4NjQuOTM4NyAxMzYuODQyNyA4NjQuNjgyNyAxMzYuODQyNyA4NjQuNDY5MyAxMzYuODQyNyA4NjQuMjEzMyAxMzYuODQyN1pNNzg2LjQzMiAzNzEuNjhDODI3Ljg2MTMgMzcxLjU1MiA4NjcuNDk4NyAzNjQuMDQyNyA5MDQuMTQ5MyAzNTAuNDMyTDkwMS44MDI3IDM1MS4yQzkwOS44MjQgMzYzLjU3MzMgOTE0LjU2IDM3OC42NzczIDkxNC41NiAzOTQuODkwNyA5MTQuNTYgMzk5LjcxMiA5MTQuMTMzMyA0MDQuNDQ4IDkxMy4zMjI3IDQwOS4wMTMzIDg3Ny4yMjY3IDYwMy4xMDQgNjg2Ljc2MjcgNzQzLjczMzMgNDU5LjQzNDcgNzQzLjczMzMgMjA0LjggNzQzLjczMzMgMCA1NjUuNTU3MyAwIDM0Ni40MjEzIDEuMzY1MyAyMzEuNjkwNyA1My45MzA3IDEyOS41NDY3IDEzNS44OTMzIDYxLjU3ODdMMTE4LjEwMTMgMi4zNTczQzExNS43NTQ3LTQuODk2IDExNC40MzItMTMuMjU4NyAxMTQuNDMyLTIxLjg3NzMgMTE0LjQzMi02Ny4xMDQgMTUxLjEyNTMtMTAzLjc5NzMgMTk2LjM1Mi0xMDMuNzk3MyAyMDkuNjIxMy0xMDMuNzk3MyAyMjIuMTY1My0xMDAuNjQgMjMzLjI1ODctOTUuMDUwN0wzNDEuMzMzMy0zOC42MDI3QzM3Ni4zNjI3LTQ2LjgzNzMgNDE2LjU1NDctNTEuNTczMyA0NTcuODU2LTUxLjU3MzMgNDU3Ljk0MTMtNTEuNTczMyA0NTguMDI2Ny01MS41NzMzIDQ1OC4xMTItNTEuNTczM0g0ODguMTQ5M0M1MDIuMTQ0LTUwLjc2MjcgNTE0Ljk4NjctNDYuNTgxMyA1MjYuMDM3My0zOS43NTQ3IDQ5Ni4yNTYtMC41ODY3IDQ3OC40MjEzIDQ4Ljk0OTMgNDc3LjkwOTMgMTAyLjU4MTMgNDg4LjU3NiAyNTMuNzkyIDYxMy44MDI3IDM3Mi4zNjI3IDc2Ni42NzczIDM3Mi4zNjI3IDc3My42MzIgMzcyLjM2MjcgNzgwLjU0NCAzNzIuMTA2NyA3ODcuMzcwNyAzNzEuNjM3M1pNNTkwLjUwNjcgNDkxLjgyOTNDNjE3Ljg5ODcgNDkwLjcyIDYzOS42NTg3IDQ2OC4yMzQ3IDYzOS42NTg3IDQ0MC42NzIgNjM5LjY1ODcgNDEyLjM4NCA2MTYuNzQ2NyAzODkuNDcyIDU4OC40NTg3IDM4OS40NzJTNTM3LjMwMTMgNDEyLjM4NCA1MzcuMjU4NyA0NDAuNjI5M0M1MzcuNjQyNyA0NjkuMDAyNyA1NjAuNzI1MyA0OTEuODI5MyA1ODkuMTQxMyA0OTEuODI5MyA1ODkuNjEwNyA0OTEuODI5MyA1OTAuMTIyNyA0OTEuODI5MyA1OTAuNTkyIDQ5MS44MjkzWk0zMjcuNjggMzg4Ljc0NjdDMzAwLjI4OCAzODkuODU2IDI3OC41MjggNDEyLjM0MTMgMjc4LjUyOCA0MzkuOTA0IDI3OC41MjggNDY4LjE5MiAzMDEuNDQgNDkxLjEwNCAzMjkuNzI4IDQ5MS4xMDRTMzgwLjg4NTMgNDY4LjE5MiAzODAuOTI4IDQzOS45NDY3QzM4MC4xNiA0MTEuNDg4IDM1Ni45NDkzIDM4OC43NDY3IDMyOC4zNjI3IDM4OC43NDY3IDMyOC4xMDY3IDM4OC43NDY3IDMyNy44NTA3IDM4OC43NDY3IDMyNy42MzczIDM4OC43NDY3WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTFDRiIgdW5pY29kZT0iJiN4RTFDRjsiIGQ9Ik02MDMuNTIgNDYzLjJDNjAzLjUyIDQzNi43MDQgNTgxLjE2MjcgNDE1LjIgNTUzLjYgNDE1LjJTNTAzLjY4IDQzNi43MDQgNTAzLjY4IDQ2My4yQzUwMy42OCA0ODkuNjk2IDUyNi4wMzczIDUxMS4yIDU1My42IDUxMS4yUzYwMy41MiA0ODkuNjk2IDYwMy41MiA0NjMuMlpNMzU3LjEyIDQ2My4yQzM1Ny4xMiA0MzYuNzA0IDMzNC43NjI3IDQxNS4yIDMwNy4yIDQxNS4yUzI1Ny4yOCA0MzYuNzA0IDI1Ny4yOCA0NjMuMkMyNTcuMjggNDg5LjY5NiAyNzkuNjM3MyA1MTEuMiAzMDcuMiA1MTEuMlMzNTcuMTIgNDg5LjY5NiAzNTcuMTIgNDYzLjJaTTY5My4xMiAyMDcuODRDNjkzLjEyIDE5MS45MjUzIDY3OS45MzYgMTc5LjA0IDY2My42OCAxNzkuMDRTNjM0LjI0IDE5MS45MjUzIDYzNC4yNCAyMDcuODRDNjM0LjI0IDIyMy43NTQ3IDY0Ny40MjQgMjM2LjY0IDY2My42OCAyMzYuNjRTNjkzLjEyIDIyMy43NTQ3IDY5My4xMiAyMDcuODRaTTk1MS42OC0yMEM5OTUuNDU2IDIyLjQxMDcgMTAyMi45NzYgODEuNDE4NyAxMDI0IDE0Ni44NjkzIDEwMTkuMzkyIDI1Ni41NjUzIDk0Ni42NDUzIDM0Ny45MTQ3IDg0Ny4yNzQ3IDM4MC4xNzA3IDg1Mi45NDkzIDM5Mi4yODggODU3LjQyOTMgNDA2LjQ1MzMgODU3LjQyOTMgNDIxLjY0MjcgODU3LjQyOTMgNDI2LjE2NTMgODU3LjA0NTMgNDMwLjYwMjcgODU2LjI3NzMgNDM0Ljg2OTMgODIyLjQ0MjcgNjE2LjE2IDY0My44ODI3IDc0OCA0MzAuNzYyNyA3NDggMTkyLjA0MjcgNzQ4IDAuMDQyNyA1ODAuOTYgMC4wNDI3IDM3NS41MiAxLjMyMjcgMjY3Ljk1NzMgNTAuNjAyNyAxNzIuMjEzMyAxMjcuNDQ1MyAxMDguNDY5M0wxMTAuNzYyNyA1Mi45NkMxMDguNTg2NyA0Ni4xNzYgMTA3LjMwNjcgMzguMzI1MyAxMDcuMzA2NyAzMC4yMTg3IDEwNy4zMDY3LTEyLjE5MiAxNDEuNjk2LTQ2LjU4MTMgMTg0LjEwNjctNDYuNTgxMyAxOTYuNTY1My00Ni41ODEzIDIwOC4yOTg3LTQzLjYzNzMgMjE4LjcwOTMtMzguMzQ2N0wzMjAuMDQyNyAxNC41NkMzNTIuODUzMyA2LjgzNzMgMzkwLjU3MDcgMi40IDQyOS4yNjkzIDIuNCA0MjkuMzU0NyAyLjQgNDI5LjQ0IDIuNCA0MjkuNDgyNyAyLjRINDU3LjY0MjdDNDcwLjc0MTMgMy4xNjggNDgyLjc3MzMgNy4wOTMzIDQ5My4xODQgMTMuNDUwNyA1NDcuNDEzMy02MC4xMDY3IDYzMy44NTYtMTA3LjA4MjcgNzMxLjI2NC0xMDcuMDgyNyA3MzIuOTI4LTEwNy4wODI3IDczNC42MzQ3LTEwNy4wODI3IDczNi4yOTg3LTEwNy4wNCA3NTcuMzc2LTEwNi45NTQ3IDc3OC4xNTQ3LTEwNC44NjQgNzk4LjI5MzMtMTAwLjkzODdMODQ3LjQwMjctMTI3LjUyQzg1Ny4zNDQtMTMyLjU1NDcgODY5LjEyLTEzNS41NDEzIDg4MS41Nzg3LTEzNS41NDEzIDkyMy45ODkzLTEzNS41NDEzIDk1OC4zNzg3LTEwMS4xNTIgOTU4LjM3ODctNTguNzQxMyA5NTguMzc4Ny01MC42MzQ3IDk1Ny4wOTg3LTQyLjc4NCA5NTQuNzk0Ny0zNS40NDUzWk00MzAuNzIgNTkuMzZDNDMwLjU0OTMgNTkuMzYgNDMwLjMzNiA1OS4zNiA0MzAuMTIyNyA1OS4zNiAzODkuMjkwNyA1OS4zNiAzNDkuODI0IDY1LjIwNTMgMzEyLjUzMzMgNzYuMDg1M0wzMDkuMDc3MyA3NS4zNiAxNzcuODc3MyA4LjE2IDIxMy4wNzczIDEyMS40NEgyMDkuODc3M0MxMjMuNzc2IDE3My40OTMzIDY2LjQ3NDcgMjY1LjYxMDcgNjMuOTU3MyAzNzEuMzM4NyA2My45NTczIDU0My44NCAyMjkuNzE3MyA2ODQgNDMwLjY3NzMgNjg0IDQzNi4zOTQ3IDY4NC4zNDEzIDQ0My4wOTMzIDY4NC41MTIgNDQ5LjgzNDcgNjg0LjUxMiA2MTMuMTYyNyA2ODQuNTEyIDc1MC40MjEzIDU3My4xMDkzIDc4OS44NDUzIDQyMi4xMTJMNzc1LjA0IDQxOS42OEM1OTIgNDE5LjY4IDQ0OCAzMDcuNjggNDQ4IDEzNC4yNCA0NDguNTEyIDEwNy41MzA3IDQ1My4xNjI3IDgyLjA1ODcgNDYxLjMxMiA1OC4yNTA3Wk04NzIuOTYtMC44Vi0wLjhMODk0LjcyLTY4LjY0IDgxMy40NC0yNy42OEg4MDkuNkM3ODguNDgtMzMuNzgxMyA3NjQuMjAyNy0zNy4yOCA3MzkuMTE0Ny0zNy4yOCA3MzguOTQ0LTM3LjI4IDczOC43MzA3LTM3LjI4IDczOC41Ni0zNy4yOCA3MzIuNjcyLTM3Ljg3NzMgNzI1LjgwMjctMzguMjE4NyA3MTguODQ4LTM4LjIxODcgNjExLjc1NDctMzguMjE4NyA1MjMuNTYyNyA0Mi43MiA1MTIuMTI4IDE0Ni43NDEzIDUyMi40OTYgMjUzLjcwNjcgNjExLjIgMzM1Ljg4MjcgNzE5LjEwNCAzMzUuODgyNyA3MjUuMDc3MyAzMzUuODgyNyA3MzAuOTY1MyAzMzUuNjI2NyA3MzYuODEwNyAzMzUuMTU3MyA3NDEuMTIgMzM1LjY2OTMgNzQ3LjAwOCAzMzUuODgyNyA3NTIuOTgxMyAzMzUuODgyNyA4NjAuODg1MyAzMzUuODgyNyA5NDkuNTg5MyAyNTMuNzA2NyA5NTkuOTU3MyAxNDguNTMzMyA5NTguMjUwNyA4NC43MDQgOTI0LjE2IDMwLjA5MDcgODczLjc3MDctMC4zNzMzWk04MzkuNjggMjA3Ljg0QzgzOS42OCAxOTEuOTI1MyA4MjYuNDk2IDE3OS4wNCA4MTAuMjQgMTc5LjA0Uzc4MC44IDE5MS45MjUzIDc4MC44IDIwNy44NEM3ODAuOCAyMjMuNzU0NyA3OTMuOTg0IDIzNi42NCA4MTAuMjQgMjM2LjY0UzgzOS42OCAyMjMuNzU0NyA4MzkuNjggMjA3Ljg0WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTFEMCIgdW5pY29kZT0iJiN4RTFEMDsiIGQ9Ik05MjUuOTIgNzZIOTI4TDkwNi44OCA4MC4xNkExMTYuOCAxMTYuOCAwIDAgMSA4OTUuNjggMTA3LjUyTDg5NS42OCAxMDcuNTIgOTA2LjI0IDEyNEExOS4zNiAxOS4zNiAwIDAgMSA5MTIgMTM3Ljc2IDE4LjcyIDE4LjcyIDAgMCAxIDkwNi4yNCAxNTEuMzZMODkyLjggMTY0LjhBMTcuOTIgMTcuOTIgMCAwIDEgODc5Ljg0IDE3MC4wOCAxOS4wNCAxOS4wNCAwIDAgMSA4NjYuODggMTY0LjhMODQ4LjggMTUyLjQ4QTEyNS45MiAxMjUuOTIgMCAwIDEgODIzLjg0IDE2My4wNEw4MjMuMDQgMTYzLjA0IDgxOC44OCAxODIuMDhBMTkuODQgMTkuODQgMCAwIDEgODAwIDIwMS4xMkg3ODAuMTZBMTguNzIgMTguNzIgMCAwIDEgNzYxLjQ0IDE4My41Mkg3NjEuNDRMNzU3LjQ0IDE2Mi4yNEExMjQuOCAxMjQuOCAwIDAgMSA3MzAuODggMTUxLjJINzMwLjg4TDcxNC44OCAxNjIuMDhBMTguODggMTguODggMCAwIDEgNzAxLjQ0IDE2Ny44NEg3MDEuNDRBMjAgMjAgMCAwIDEgNjg3LjUyIDE2Mi4wOEw2NzMuNiAxNDguNjRBMTkuMDQgMTkuMDQgMCAwIDEgNjY4IDEzNS4yVjEzNC4yNEExNi44IDE2LjggMCAwIDEgNjcyLjE2IDEyMi44OEg2NzIuMTZMNjg0LjY0IDEwNC4zMkExMTguODggMTE4Ljg4IDAgMCAxIDY3My45MiA3OC4yNFY3OC4yNEw2NTMuNzYgNzQuMDhBMTkuNjggMTkuNjggMCAwIDEgNjM0LjA4IDU0LjRWMzUuMzZINjM0LjA4QTE5LjA0IDE5LjA0IDAgMCAxIDY1MS42OCAxNi4zMkg2NTEuNjhMNjc0LjQgMTEuNjhBMTE2IDExNiAwIDAgMSA2ODUuNi0xNC43Mkw2ODUuNi0xNC43MiA2NzMuNzYtMzIuOEExOS41MiAxOS41MiAwIDAgMSA2NzMuNzYtNjAuMTZMNjg3LjY4LTczLjZBMTguNTYgMTguNTYgMCAwIDEgNzEzLjYtNzMuNkw3MzMuNzYtNjAuMTZBMTE5LjA0IDExOS4wNCAwIDAgMSA3NTYuMTYtNjkuMjhINzU2Ljk2TDc2MS42LTkxLjA0QTE5LjY4IDE5LjY4IDAgMCAxIDc4MS4yOC0xMTAuNTZIODAxLjQ0QTE4LjQgMTguNCAwIDAgMSA4MjAtOTMuMTJIODIwTDgyNC42NC02OS4yOEExMjUuMTIgMTI1LjEyIDAgMCAxIDg0OC42NC01OS42OEw4NDguNjQtNTkuNjggODY3LjItNzJBMTkuNTIgMTkuNTIgMCAwIDEgODk0LjU2LTcyTDkwOC42NC01OC41NkExOS4wNCAxOS4wNCAwIDAgMSA5MTMuOTItNDUuNDQgMTkuODQgMTkuODQgMCAwIDEgOTA4LjY0LTMyLjE2TDg5NC4wOC0xMS41MkExMTcuNDQgMTE3LjQ0IDAgMCAxIDkwMy41MiAxMlYxMy42TDkyNC4xNiAxNy42QTE5LjY4IDE5LjY4IDAgMCAxIDk0NCAzNy4yOFY1Ni40OEExOS42OCAxOS42OCAwIDAgMSA5MjUuOTIgNzZaTTc4OS40NC0wLjQ4QTQ4IDQ4IDAgMSAwIDgzNy40NCA0Ny41MiA0OCA0OCAwIDAgMCA3ODkuNDQtMC45NlpNNDA4IDIwNEg2MTZBNDAgNDAgMCAwIDEgNjU2IDI0NFYyNjhIODgwVjIyMEg5NDRWNTA4QTMyIDMyIDAgMCAxIDkxMiA1NDBINzA0VjY1MkEzMiAzMiAwIDAgMSA2NzIgNjg0SDM1MkEzMiAzMiAwIDAgMSAzMjAgNjUyVjU0MEgxMTJBMzIgMzIgMCAwIDEgODAgNTA4Vi00QTMyIDMyIDAgMCAxIDExMi0zNkg1NzZWMjhIMTQ0VjI2OEgzNjhWMjQ0QTQwIDQwIDAgMCAxIDQwOCAyMDRaTTU5MiAyNjhINDMyVjMzMkg1OTJaTTM4NCA2MjBINjQwVjU0MEgzODRaTTE0NCAzMzJWNDc2SDg4MFYzMzJINjU2VjM1NkE0MCA0MCAwIDAgMSA2MTYgMzk2SDQwOEE0MCA0MCAwIDAgMSAzNjggMzU2VjMzMloiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxRDEiIHVuaWNvZGU9IiYjeEUxRDE7IiBkPSJNODYwLjggNjg0SDE2My4yQTMyIDMyIDAgMCAxIDEzNS44NCA2MzJMNDMxLjA0IDI5NiA0MzIgMjk2Vi04NEw1OTItMS4yOFYyOTUuMkw1OTIuOTYgMjk1LjIgODg4LjE2IDYzMS4yQTMyIDMyIDAgMCAxIDg2MC44IDY4NFoiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxRDIiIHVuaWNvZGU9IiYjeEUxRDI7IiBkPSJNNTEyIDc0OEMyNjQgNzQ4IDY0IDU0OCA2NCAzMDBTMjY0LTE0OCA1MTItMTQ4IDk2MCA1MiA5NjAgMzAwIDc2MCA3NDggNTEyIDc0OFpNNDI4LjggNjEuNkgxNjBDMTYwIDE0MCAzMjAgMjEyIDM2MS42IDIxOC40IDM3NC40IDIyMCAzNzQuNCAyNTguNCAzNzQuNCAyNTguNFMzMzYgMjk4LjQgMzI2LjQgMzUxLjJDMzA0IDM1MS4yIDI4OS42IDQwNy4yIDMxMiA0MjYuNCAzMTAuNCA0NDcuMiAyODMuMiA1ODkuNiA0MjcuMiA1ODkuNiA1NzEuMiA1ODkuNiA1NDIuNCA0NDcuMiA1NDIuNCA0MjYuNCA1NjQuOCA0MDcuMiA1NTAuNCAzNTEuMiA1MjggMzUxLjIgNTIwIDI5OC40IDQ4MCAyNTguNCA0ODAgMjU4LjRTNDgwIDIyMS42IDQ5Mi44IDIxOC40QzUzNiAyMTIgNjk0LjQgMTQwIDY5NC40IDYxLjZINDI4LjhaTTc2OCA4MC44Qzc1MC40IDE1Mi44IDYwOCAyMTYuOCA1NjggMjIzLjIgNTYxLjYgMjI0LjggNTU4LjQgMjMxLjIgNTU2LjggMjM5LjIgNTU1LjIgMjQ4LjggNTU2LjggMjYxLjYgNTU2LjggMjYxLjZTNTU4LjQgMjY2LjQgNTU4LjQgMjY4QzU2OS42IDI4MC44IDU5My42IDMxMi44IDYwMCAzNTQuNCA2MjIuNCAzNTQuNCA2MzYuOCA0MTAuNCA2MTQuNCA0MjkuNiA2MTQuNCA0NDUuNiA2MzIgNTM1LjIgNTcyLjggNTczLjYgNTg0IDU3Ni44IDU5NS4yIDU3Ni44IDYwOS42IDU3Ni44IDc0NS42IDU3Ni44IDcxOC40IDQ0Mi40IDcxNi44IDQyMy4yIDczNy42IDQwNCA3MjQuOCAzNTEuMiA3MDQgMzUxLjIgNjk2IDMwMS42IDY1OS4yIDI2NC44IDY1OS4yIDI2NC44UzY1OS4yIDIyOS42IDY3MiAyMjhDNzEyIDIyMS42IDg2Mi40IDE1NC40IDg2Mi40IDc5LjJINzY4WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTFEMyIgdW5pY29kZT0iJiN4RTFEMzsiIGQ9Ik05NjAgMzAwQzk2MCA3NC40IDc5Mi0xMTYgNTY4LTE0NC44IDM0NC0xNzMuNiAxMzQuNC0yOS42IDc4LjQgMTg5LjZTMTM5LjIgNjM0LjQgMzQ4LjggNzE2QzQ1Mi44IDc1Ny42IDU2OS42IDc1Ny42IDY3NS4yIDcxNiA4NDYuNCA2NDguOCA5NjAgNDg0IDk2MCAzMDBNMzM5LjIgMzk0LjRDMzM3LjYgMzI0IDM3NC40IDI1OC40IDQzMy42IDIyMS42IDQ4MCAxOTQuNCA1MzkuMiAxOTQuNCA1ODUuNiAyMjAgNjQ4IDI1Ni44IDY4NC44IDMyMi40IDY4My4yIDM5NC40IDY5MS4yIDQ2MCA2NTkuMiA1MjQgNjAzLjIgNTYwLjggNTQ3LjIgNTk2IDQ3NS4yIDU5NiA0MTkuMiA1NjAuOFMzMzIuOCA0NjAgMzM5LjIgMzk0LjRNNTEzLjYtMTE3LjZDNjQwLTExNy42IDc1OC40LTYxLjYgODM4LjQgMzYgODI4LjggMTA5LjYgNzU2LjggMTczLjYgNjU0LjQgMjA1LjYgNTcyLjggMTMwLjQgNDQ4IDEzMiAzNjggMjA4LjggMjY4LjggMTgwIDE5NS4yIDEyMi40IDE3Ny42IDUzLjYgMjU2LTU1LjIgMzgwLjgtMTE3LjYgNTEzLjYtMTE3LjYiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxRDQiIHVuaWNvZGU9IiYjeEUxRDQ7IiBkPSJNODY0IDY4NEgyODhDMjcwLjQgNjg0IDI1NiA2NjkuNiAyNTYgNjUyVjU1NkgxNjBDMTQyLjQgNTU2IDEyOCA1NDEuNiAxMjggNTI0Vi01MkMxMjgtNjkuNiAxNDIuNC04NCAxNjAtODRINzM2Qzc1My42LTg0IDc2OC02OS42IDc2OC01MlY0NEg4NjRDODgxLjYgNDQgODk2IDU4LjQgODk2IDc2VjY1MkM4OTYgNjY5LjYgODgxLjYgNjg0IDg2NCA2ODRaTTcwNCAxMDhWNDQtMjBIMTkyVjQ5MkgyNTYgMzIwIDcwNFYxMDhaTTgzMiAxMDhINzY4VjUyNEM3NjggNTQxLjYgNzUzLjYgNTU2IDczNiA1NTZIMzIwVjYyMEg4MzJWMTA4Wk0yNzUuMiAzOTIuOEg2MTEuMlYzMjguOEgyNzUuMlpNMjcyIDI2OEg2MDhWMjA0SDI3MlpNMjcyIDE0MEg2MDhWNzZIMjcyWiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTFENiIgdW5pY29kZT0iJiN4RTFENjsiIGQ9Ik04MzcuMjggMzMyQTU4LjcyIDU4LjcyIDAgMCAxIDg5NiAzOTAuNzJWNjI1LjI4QTU4LjcyIDU4LjcyIDAgMCAxIDgzNy4yOCA2ODRINjAyLjcyQTU4LjcyIDU4LjcyIDAgMCAxIDU0NCA2MjUuMjhWMzkwLjcyQTU4LjcyIDU4LjcyIDAgMCAxIDYwMi43MiAzMzJaTTYwOCA2MjBIODMyVjM5Nkg2MDhaTTQyMS4yOCA2ODRIMTg2LjcyQTU4LjcyIDU4LjcyIDAgMCAxIDEyOCA2MjUuMjhWMzkwLjcyQTU4LjcyIDU4LjcyIDAgMCAxIDE4Ni43MiAzMzJINDIxLjI4QTU4LjcyIDU4LjcyIDAgMCAxIDQ4MCAzOTAuNzJWNjI1LjI4QTU4LjcyIDU4LjcyIDAgMCAxIDQyMS4yOCA2ODRaTTQxNiAzOTZIMTkyVjYyMEg0MTZaTTQyMS4yOCAyNjhIMTg2LjcyQTU4LjcyIDU4LjcyIDAgMCAxIDEyOCAyMDkuMjhWLTI1LjI4QTU4LjcyIDU4LjcyIDAgMCAxIDE4Ni43Mi04NEg0MjEuMjhBNTguNzIgNTguNzIgMCAwIDEgNDgwLTI1LjI4VjIwOS4yOEE1OC43MiA1OC43MiAwIDAgMSA0MjEuMjggMjY4Wk00MTYtMjBIMTkyVjIwNEg0MTZaTTkwNC4zMiAyMDUuNDRMNzIzLjIgMTAuMjQgNTk4LjU2IDExOC44OCA1NTMuNDQgNzMuNiA3MjUuMjgtODIuMjQgOTUxLjY4IDE2Mi4yNCA5MDQuMzIgMjA1LjQ0WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTFENSIgdW5pY29kZT0iJiN4RTFENTsiIGQ9Ik03MDQgNDYwSDkyOFY2ODRIODY0VjU3Ni44QTQ0OCA0NDggMCAxIDEgOTI1LjYgMTI3LjM2TDg2Ni40IDE1MkEzODQgMzg0IDAgMSAwIDgyMy44NCA1MjRINzA0WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTFENyIgdW5pY29kZT0iJiN4RTFENzsiIGQ9Ik05MDIuNTYgNjQ1LjQ0TDg1Ny40NCA2OTAuNTYgNTEyIDM0NS4yOCAxNjYuNTYgNjkwLjU2IDEyMS40NCA2NDUuNDQgNDY2LjcyIDMwMCAxMjEuNDQtNDUuNDQgMTY2LjU2LTkwLjU2IDUxMiAyNTQuNzIgODU3LjQ0LTkwLjU2IDkwMi41Ni00NS40NCA1NTcuMjggMzAwIDkwMi41NiA2NDUuNDRaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMUQ4IiB1bmljb2RlPSImI3hFMUQ4OyIgZD0iTTUxMiAxNjkuMjhMMTY2LjU2IDUxNC41NiAxMjEuNDQgNDY5LjQ0IDUxMiA3OC43MiA5MDIuNTYgNDY5LjQ0IDg1Ny40NCA1MTQuNTYgNTEyIDE2OS4yOFoiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxREIiIHVuaWNvZGU9IiYjeEUxREI7IiBkPSJNNTA2LjcyIDYwNS40NEw3NzIuOTYgMzMyLjggMTI4IDMzMi44IDEyOCAyNjcuMiA3NzIuOTYgMjY3LjIgNTA2LjcyLTUuNDQgNTUyLjE2LTUyIDg5NiAzMDAgNTUyLjE2IDY1MiA1MDYuNzIgNjA1LjQ0WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTFEOSIgdW5pY29kZT0iJiN4RTFEOTsiIGQ9Ik01MTcuMjggNjA1LjQ0TDI1MS4wNCAzMzIuOCA4OTYgMzMyLjggODk2IDI2Ny4yIDI1MS4wNCAyNjcuMiA1MTcuMjgtNS40NCA0NzEuODQtNTIgMTI4IDMwMCA0NzEuODQgNjUyIDUxNy4yOCA2MDUuNDRaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMURDIiB1bmljb2RlPSImI3hFMURDOyIgZD0iTTgxNy40NCAzMDUuOTJMNTQ0LjggMzkuNjggNTQ0LjggNjg0LjY0IDQ3OS4yIDY4NC42NCA0NzkuMiAzOS42OCAyMDYuNTYgMzA1LjkyIDE2MCAyNjAuNDggNTEyLTgzLjM2IDg2NCAyNjAuNDggODE3LjQ0IDMwNS45MloiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxREEiIHVuaWNvZGU9IiYjeEUxREE7IiBkPSJNODE3LjQ0IDI5NC43Mkw1NDQuOCA1NjAuOTYgNTQ0LjgtODQgNDc5LjItODQgNDc5LjIgNTYwLjk2IDIwNi41NiAyOTQuNzIgMTYwIDM0MC4xNiA1MTIgNjg0IDg2NCAzNDAuMTYgODE3LjQ0IDI5NC43MloiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxRTEiIHVuaWNvZGU9IiYjeEUxRTE7IiBkPSJNNzQ0LjY0IDMwMEw0NjIuNzIgMjIuNCA1NTQuNTYtNjggOTI4IDMwMCA1NTQuNTYgNjY4IDQ2Mi43MiA1NzcuNiA3NDQuNjQgMzAwWk0xODcuNjggNjY4TDk2IDU3Ny42IDM3Ny43NiAzMDAgOTYgMjIuNCAxODcuNjgtNjggNTYxLjI4IDMwMCAxODcuNjggNjY4WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTFERSIgdW5pY29kZT0iJiN4RTFERTsiIGQ9Ik01MTIgNjcuMzZMNzg5LjYgMzQ5LjI4IDg4MCAyNTcuNDQgNTEyLTExNiAxNDQgMjU3LjQ0IDIzNC40IDM0OS4yOCA1MTIgNjcuMzZaTTE0NCA2MjQuMzJMMjM0LjQgNzE2IDUxMiA0MzQuMjQgNzg5LjYgNzE2IDg4MCA2MjQuMzIgNTEyIDI1MC43MiAxNDQgNjI0LjMyWiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTFERiIgdW5pY29kZT0iJiN4RTFERjsiIGQ9Ik01MTIgNTMyLjY0TDc4OS42IDI1MC43MiA4ODAgMzQyLjU2IDUxMiA3MTYgMTQ0IDM0Mi41NiAyMzQuNCAyNTAuNzIgNTEyIDUzMi42NFpNMTQ0LTI0LjMyTDIzNC40LTExNiA1MTIgMTY1LjkyIDc4OS42LTExNiA4ODAtMjQuMzIgNTEyIDM0OS4yOCAxNDQtMjQuMzJaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMUREIiB1bmljb2RlPSImI3hFMUREOyIgZD0iTTI3OS4zNiAzMDBMNTYxLjI4IDIyLjQgNDY5LjQ0LTY4IDk2IDMwMCA0NjkuNDQgNjY4IDU2MS4yOCA1NzcuNiAyNzkuMzYgMzAwWk04MzYuMzIgNjY4TDkyOCA1NzcuNiA2NDYuMDggMzAwIDkyOCAyMi40IDgzNi4zMi02OCA0NjIuNzIgMzAwIDgzNi4zMiA2NjhaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMUUwIiB1bmljb2RlPSImI3hFMUUwOyIgZD0iTTI1NiAzMDBMNjc2LTExNiA3NjgtMjQuOTYgNDQwIDMwMCA3NjggNjI0Ljk2IDY3NiA3MTYgMjU2IDMwMFoiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxRTIiIHVuaWNvZGU9IiYjeEUxRTI7IiBkPSJNNzY4IDMwMEwzNDgtMTE2IDI1Ni0yNC45NiA1ODQgMzAwIDI1NiA2MjQuOTYgMzQ4IDcxNiA3NjggMzAwWiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTFFNCIgdW5pY29kZT0iJiN4RTFFNDsiIGQ9Ik01MTIgNTU3LjQ0TDk2IDEzNy40NCAxODcuMDQgNDUuNDQgNTEyIDM3My40NCA4MzYuOTYgNDUuNDQgOTI4IDEzNy40NCA1MTIgNTU3LjQ0WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTFFMyIgdW5pY29kZT0iJiN4RTFFMzsiIGQ9Ik01MTIgNDkuNDRMOTguNzIgNDYyLjcyIDE4OS4yOCA1NTMuMjggNTEyIDIzMC41NiA4MzQuNzIgNTUzLjI4IDkyNS4yOCA0NjIuNzIgNTEyIDQ5LjQ0WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTFFRCIgdW5pY29kZT0iJiN4RTFFRDsiIGQ9Ik04MjcuMiA1ODhMMzg3LjIgMTQ2LjQgMTk1LjIgMzQwIDEyOCAyNzIuOCAzMjAgODAuOCAzMjAgODAuOCAzODguOCAxMiA4OTYgNTE5LjJaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMUVDIiB1bmljb2RlPSImI3hFMUVDOyIgZD0iTTgzMiA1NTIuOEw3NjQuOCA2MjAgNTEyIDM2Ny4yIDI1OS4yIDYyMCAxOTIgNTUyLjggNDQ0LjggMzAwIDE5MiA0Ny4yIDI1OS4yLTIwIDUxMiAyMzIuOCA3NjQuOC0yMCA4MzIgNDcuMiA1NzkuMiAzMDBaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMUVFIiB1bmljb2RlPSImI3hFMUVFOyIgZD0iTTYwOS42IDYxMC40TDIwMy4yIDIwMi40IDIwMy4yIDEwMS42IDMwNCAxMDEuNiA3MTIgNTA4Wk0xMjggMTJIODk2Vi04NEgxMjhaTTY4My42NzE4IDY4My45NTgzTDc4NS40OTM0IDU4Mi4xMzMyIDc0MC4yMzc3IDUzNi44NzkxIDYzOC40MTYxIDYzOC43MDQzWiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTFFQiIgdW5pY29kZT0iJiN4RTFFQjsiIGQ9Ik0xMjggNjIwSDIyNFY1MjRIMTI4Wk0zMjAgNjIwSDg5NlY1MjRIMzIwWk0xMjggMzQ4SDIyNFYyNTJIMTI4Wk0zMjAgMzQ4SDg5NlYyNTJIMzIwWk0xMjggNzZIMjI0Vi0yMEgxMjhaTTMyMCA3Nkg4OTZWLTIwSDMyMFoiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxRUYiIHVuaWNvZGU9IiYjeEUxRUY7IiBkPSJNODk2IDM2NEw1NzYgMzY0IDU3NiA2ODQgNDQ4IDY4NCA0NDggMzY0IDEyOCAzNjQgMTI4IDIzNiA0NDggMjM2IDQ0OC04NCA1NzYtODQgNTc2IDIzNiA4OTYgMjM2WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTFGMCIgdW5pY29kZT0iJiN4RTFGMDsiIGQ9Ik01MTIgMTA4TDk2IDU1NiAxODcuMDQgNTU2IDUxMiA1NTYgODM2Ljk2IDU1NiA5MjggNTU2IDUxMiAxMDhaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMUYxIiB1bmljb2RlPSImI3hFMUYxOyIgZD0iTTUxMiA1NTZMOTYgMTA4IDE4Ny4wNCAxMDggNTEyIDEwOCA4MzYuOTYgMTA4IDkyOCAxMDggNTEyIDU1NloiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxRjIiIHVuaWNvZGU9IiYjeEUxRjI7IiBkPSJNNjk2Ljk2IDc0OEExMTIgMTEyIDAgMSAwIDU4NS45MiA2MzYgMTEyIDExMiAwIDAgMCA2OTYuOTYgNzQ4Wk0zMjcuMDQgNzQ4QTExMiAxMTIgMCAxIDAgMjE2IDYzNiAxMTIgMTEyIDAgMCAwIDMyNy4wNCA3NDhaTTY5Ni45NiA0MTJBMTEyIDExMiAwIDEgMCA1ODUuOTIgMzAwIDExMiAxMTIgMCAwIDAgNjk2Ljk2IDQxMlpNMzI3LjA0IDQxMkExMTIgMTEyIDAgMSAwIDIxNiAzMDAgMTEyIDExMiAwIDAgMCAzMjcuMDQgNDEyWk02OTYuOTYgNzZBMTEyIDExMiAwIDEgMCA1ODUuOTItMzYgMTEyIDExMiAwIDAgMCA2OTYuOTYgNzZaTTMyNy4wNCA3NkExMTIgMTEyIDAgMSAwIDIxNi0zNiAxMTIgMTEyIDAgMCAwIDMyNy4wNCA3NloiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxRjMiIHVuaWNvZGU9IiYjeEUxRjM7IiBkPSJNMjA1LjkyIDUxNS41Mkw0NzIuNjQgNDI4QTE2IDE2IDAgMCAwIDQ4NCA0MTJWOS40NEExNiAxNiAwIDAgMCA0NjEuOTItNi41NkwxOTQuNTYgOTcuNkExNi45NiAxNi45NiAwIDAgMCAxODQgMTEzLjZMMTg0LjggNDk5Ljg0QTE2IDE2IDAgMCAwIDIwNS45MiA1MTUuNTJaTTUyOCA2MjEuMTJMNzMwLjQgNTYwQTcuNTIgNy41MiAwIDAgMCA3MzAuNCA1NDUuOTJMNTI4IDQ4MC4zMkE1My43NiA1My43NiAwIDAgMCA0OTQuNzIgNDgwLjMyTDI5My45MiA1NDYuNzJBNy41MiA3LjUyIDAgMCAwIDI5My45MiA1NjAuOEw0OTcuMTIgNjIxLjI4QTU3LjI4IDU3LjI4IDAgMCAwIDUyOCA2MjEuMTJaTTg3MC4wOCA1NzcuNDRMNTIyLjg4IDY4Mi40QTMwLjg4IDMwLjg4IDAgMCAxIDUxMi44IDY4NCAzNS41MiAzNS41MiAwIDAgMSA1MDIuNzIgNjgyLjcyTDE3My42IDU4NC4zMkEyOC45NiAyOC45NiAwIDAgMSAxNjAuOTYgNTgwLjY0TDE1NC44OCA1NzguODhBMzYuOCAzNi44IDAgMCAxIDEyOC45NiA1NDMuMzZMMTI4IDg3LjUyQTM2Ljk2IDM2Ljk2IDAgMCAxIDE1MS4yIDUyLjk2TDQ5OC40LTgxLjZBMzQuNTYgMzQuNTYgMCAwIDEgNTIzLjY4LTgxLjZMODcxLjg0IDUxLjY4QTM2LjggMzYuOCAwIDAgMSA4OTYgODYuMDhMODk2IDU0MS45MkEzNi44IDM2LjggMCAwIDEgODcwLjI0IDU3Ny40NFoiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxRjQiIHVuaWNvZGU9IiYjeEUxRjQ7IiBkPSJNMjcwLjg4IDQ4NC40OEg4NTZWNTM0Ljg4QTUxLjg0IDUxLjg0IDAgMCAxIDgwNCA1ODYuMjRINDkyVjYzMi42NEE1MS44NCA1MS44NCAwIDAgMSA0NDAgNjg0SDE4MEE1MS44NCA1MS44NCAwIDAgMSAxMjggNjMyLjY0VjMxLjM2TDIxOC44OCA0MzMuMjhBNTEuNjggNTEuNjggMCAwIDAgMjcwLjg4IDQ4NC40OFpNODY4Ljk2IDMxLjM2QTUxLjY4IDUxLjY4IDAgMCAwIDgxNi45Ni0yMEgxNjcuMDRMMjU3LjkyIDM5NC43MkE1MS41MiA1MS41MiAwIDAgMCAzMDkuOTIgNDQ1LjkySDkwOEE1MS41MiA1MS41MiAwIDAgMCA5NjAgMzk0LjcyWiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTFGNSIgdW5pY29kZT0iJiN4RTFGNTsiIGQ9Ik00OTYgNTk2TDQxOS42OCA1MTkuNjggNTcyLjMyIDM2Ni44OEg2NFYyNjUuMTJINTcyLjE2TDQxOS42OCAxMTIuMzIgNDk2IDM2IDc3NS41MiAzMTZaTTg1OC40IDU5NlYzNkg5NjBWNTk2WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTFGNiIgdW5pY29kZT0iJiN4RTFGNjsiIGQ9Ik01MjggNTgwTDYwNC4zMiA1MDMuNjggNDUxLjY4IDM1MC44OEg5NjBWMjQ5LjEySDQ1MS44NEw2MDQuMzIgOTYuMzIgNTI4IDIwIDI0OC40OCAzMDBaTTE2NS42IDU4MFYyMEg2NFY1ODBaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMUY3IiB1bmljb2RlPSImI3hFMUY3OyIgZD0iTTEyOCAzNjRIODk2VjIzNkgxMjhWMzY0WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTFGOCIgdW5pY29kZT0iJiN4RTFGODsiIGQ9Ik01MTIgNTg4SDYwOFY1MjRINTEyVjU4OFpNNDE2IDUyNEg1MTJWNDYwSDQxNlY1MjRaTTUxMiA0NjBINjA4VjM5Nkg1MTJWNDYwWk00MTYgMTcySDYwOFYzMzJINTEyVjM5Nkg0MTZWMTcyWk00NjQgMjg0SDU2MFYyMjBINDY0VjI4NFpNOTYgNzE2Vi0xMTZIOTI4VjcxNkg5NlpNODY0LTUySDE2MFY2NTJINDE2VjU4OEg1MTJWNjUySDg2NFYtNTJaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMUZBIiB1bmljb2RlPSImI3hFMUZBOyIgZD0iTTg5NyAzODkuMUM4NjguNiA0MTcuNSA4MzMuNyA0MzYuOSA3OTUuNyA0NDYuMSA3ODUuNiA1MDQgNzU4LjEgNTU3LjMgNzE1LjcgNTk5LjcgNjYxLjMgNjU0IDU4OC45IDY4NCA1MTIgNjg0UzM2Mi43IDY1NCAzMDguNCA1OTkuNkMyNjYgNTU3LjIgMjM4LjUgNTAzLjkgMjI4LjQgNDQ2IDE5MC4zIDQzNi44IDE1NS40IDQxNy40IDEyNy4xIDM4OSA4Ni41IDM0OC40IDY0LjEgMjk0LjQgNjQuMSAyMzdWMjI3QzY0LjEgMTY5LjYgODYuNSAxMTUuNiAxMjcuMSA3NVMyMjEuNyAxMiAyNzkuMSAxMkgzMjAuMVY3NkgyNzkuMUMxOTUuOCA3NiAxMjguMSAxNDMuNyAxMjguMSAyMjdWMjM3QzEyOC4xIDMyMC4zIDE5NS44IDM4OCAyNzkuMSAzODhIMjg4LjNDMjg4LjIgMzkwLjYgMjg4LjEgMzkzLjMgMjg4LjEgMzk1LjlMMjg4LjEgMzk1LjkgMjg4LjEgMzk1LjlDMjg4LjEgMzk3LjYgMjg4LjEgMzk5LjIgMjg4LjIgNDAwLjggMjg4LjIgNDAxLjIgMjg4LjIgNDAxLjYgMjg4LjIgNDAyLjEgMjg4LjIgNDAzLjcgMjg4LjMgNDA1LjMgMjg4LjQgNDA2LjggMjg4LjQgNDA3LjIgMjg4LjQgNDA3LjUgMjg4LjUgNDA3LjkgMjg4LjYgNDA5LjEgMjg4LjYgNDEwLjQgMjg4LjcgNDExLjYgMjg4LjcgNDEyLjIgMjg4LjggNDEyLjggMjg4LjggNDEzLjQgMjg4LjkgNDE0LjggMjg5IDQxNi4xIDI4OS4xIDQxNy41IDI4OS4yIDQxOC4zIDI4OS4zIDQxOS4xIDI4OS40IDQyMCAyODkuNSA0MjAuNiAyODkuNSA0MjEuMiAyODkuNiA0MjEuOSAyOTAuOCA0MzIuMiAyOTIuNyA0NDIuMyAyOTUuMiA0NTIuMUwyOTUuMiA0NTIuMUMzMDUgNDkwLjUgMzI1IDUyNS43IDM1My44IDU1NC40IDM5NS45IDU5Ni43IDQ1Mi4yIDYyMCA1MTIgNjIwUzYyOC4xIDU5Ni43IDY3MC40IDU1NC40QzY5OS4xIDUyNS43IDcxOS4xIDQ5MC41IDcyOSA0NTIuMUw3MjkgNDUyLjFDNzMxLjUgNDQyLjMgNzMzLjQgNDMyLjIgNzM0LjYgNDIxLjkgNzM0LjcgNDIxLjMgNzM0LjcgNDIwLjcgNzM0LjggNDIwIDczNC45IDQxOS4yIDczNSA0MTguNCA3MzUuMSA0MTcuNSA3MzUuMiA0MTYuMSA3MzUuMyA0MTQuOCA3MzUuNCA0MTMuNCA3MzUuNCA0MTIuOCA3MzUuNSA0MTIuMiA3MzUuNSA0MTEuNiA3MzUuNiA0MTAuNCA3MzUuNyA0MDkuMSA3MzUuNyA0MDcuOSA3MzUuNyA0MDcuNSA3MzUuNyA0MDcuMiA3MzUuOCA0MDYuOCA3MzUuOSA0MDUuMiA3MzUuOSA0MDMuNiA3MzYgNDAyLjEgNzM2IDQwMS43IDczNiA0MDEuMyA3MzYgNDAwLjggNzM2IDM5OS4yIDczNi4xIDM5Ny41IDczNi4xIDM5NS45TDczNi4xIDM5NS45IDczNi4xIDM5NS45QzczNi4xIDM5My4yIDczNiAzOTAuNiA3MzUuOSAzODhINzQ1LjFDODI4LjQgMzg4IDg5Ni4xIDMyMC4zIDg5Ni4xIDIzN1YyMjdDODk2LjEgMTQzLjcgODI4LjQgNzYgNzQ1LjEgNzZINzA0LjFWMTJINzQ1LjFDODAyLjUgMTIgODU2LjUgMzQuNCA4OTcuMSA3NVM5NjAuMSAxNjkuNiA5NjAuMSAyMjdWMjM3Qzk2MCAyOTQuNSA5MzcuNiAzNDguNSA4OTcgMzg5LjFaTTM3Ni4yIDIwOS4xTDQyMS41IDE2My45IDQ4MCAyMjIuNCA0ODAtODQgNTQ0LTg0IDU0NCAyMjIuNCA2MDIuNSAxNjMuOSA2NDcuOCAyMDkuMSA1MTIgMzQ0LjlaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMUY5IiB1bmljb2RlPSImI3hFMUY5OyIgZD0iTTcwNCA3NDhMNzA0IDc0OEgxMjhWLTE0OEg4OTZWNTU2TDg5NiA1NTYgNzA0IDc0OFpNNzA0IDY1Ny41TDgwNS41IDU1Nkg3MDRWNjU3LjVaTTgzMi04NEgxOTJWNjg0SDY0MFY0OTJIODMyVi04NFpNMjg4IDQ5Mkg1NDRWNDI4SDI4OFY0OTJaTTI4OCAzNjRINzM2VjMwMEgyODhWMzY0Wk0yODggMjM2SDczNlYxNzJIMjg4VjIzNlpNMjg4IDEwOEg3MzZWNDRIMjg4VjEwOFoiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxRkUiIHVuaWNvZGU9IiYjeEUxRkU7IiBkPSJNMTI4IDQyOEwxOTIgNDI4IDE5MiA2MjAgMzg0IDYyMCAzODQgNjg0IDEyOCA2ODQgMTI4IDQyOFpNNjQwIDY4NEw2NDAgNjIwIDgzMiA2MjAgODMyIDQyOCA4OTYgNDI4IDg5NiA2ODQgNjQwIDY4NFpNMTkyIDE3MkwxMjggMTcyIDEyOC04NCAzODQtODQgMzg0LTIwIDE5Mi0yMCAxOTIgMTcyWk04MzItMjBMNjQwLTIwIDY0MC04NCA4OTYtODQgODk2IDE3MiA4MzIgMTcyIDgzMi0yMFoiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxRkIiIHVuaWNvZGU9IiYjeEUxRkI7IiBkPSJNMTkyIDMwMEEzMjAgMzIwIDAgMSAxIDI2OC45NiA1MDhIMzUyVjQ0NEgxNjBWNjM2SDIyNFY1NTMuOTJBMzg0IDM4NCAwIDEgMCAxMjggMzAwWiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTFGQyIgdW5pY29kZT0iJiN4RTFGQzsiIGQ9Ik04MzIgMzAwQTMyMCAzMjAgMCAxIDAgNzU1LjA0IDUwOEg2NzJWNDQ0SDg2NFY2MzZIODAwVjU1My45MkEzODQgMzg0IDAgMSAxIDg5NiAzMDBaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMUZEIiB1bmljb2RlPSImI3hFMUZEOyIgZD0iTTg4NS43Ni0yOC42NEw3MzYuOCAxMjAuNDhBMzQ0LjE2IDM0NC4xNiAwIDEgMSA2OTEuNTIgNzUuMkw4NDAuNjQtNzMuNzZBMzIgMzIgMCAxIDEgODg1Ljc2LTI4LjY0Wk00NzIgNjBBMjgwIDI4MCAwIDEgMCA3NTIgMzQwIDI4MC4zMiAyODAuMzIgMCAwIDAgNDcyIDYwWk01NzYgMzY0SDQ5NlY0NDRBMzIgMzIgMCAwIDEgNDMyIDQ0NFYzNjRIMzUyQTMyIDMyIDAgMCAxIDM1MiAzMDBINDMyVjIyMEEzMiAzMiAwIDAgMSA0OTYgMjIwVjMwMEg1NzZBMzIgMzIgMCAwIDEgNTc2IDM2NFoiICBob3Jpei1hZHYteD0iMTAyNCIgdmVydC1hZHYteT0iMTAyNCIgIC8+CgogICAgICAKICAgICAgPGdseXBoIGdseXBoLW5hbWU9InVuaUUxRkYiIHVuaWNvZGU9IiYjeEUxRkY7IiBkPSJNODg2LjU2LTI5LjI4TDczNy40NCAxMTkuODRBMzQ0LjY0IDM0NC42NCAwIDEgMSA2OTIuMTYgNzQuNTZMODQxLjI4LTc0LjU2QTMyIDMyIDAgMCAxIDg2NC04NCAzMiAzMiAwIDAgMSA4ODYuNTYtMjkuMjhaTTQ3Mi4zMiA2MEEyODAuMzIgMjgwLjMyIDAgMSAwIDc1MiAzMzkuNjggMjgwLjY0IDI4MC42NCAwIDAgMCA0NzIuMzIgNjBaTTU3NiAzNjRIMzUyQTMyIDMyIDAgMCAxIDM1MiAzMDBINTc2QTMyIDMyIDAgMCAxIDU3NiAzNjRaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMjAwIiB1bmljb2RlPSImI3hFMjAwOyIgZD0iTTM4NC04NEwzMjAtODQgMzIwIDEwOCAxMjggMTA4IDEyOCAxNzIgMzg0IDE3MiAzODQtODRaTTg5NiAxNzJMODk2IDEwOCA3MDQgMTA4IDcwNC04NCA2NDAtODQgNjQwIDE3MiA4OTYgMTcyWk0zMjAgNjg0TDM4NCA2ODQgMzg0IDQyOCAxMjggNDI4IDEyOCA0OTIgMzIwIDQ5MiAzMjAgNjg0Wk03MDQgNDkyTDg5NiA0OTIgODk2IDQyOCA2NDAgNDI4IDY0MCA2ODQgNzA0IDY4NCA3MDQgNDkyWiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTIwMyIgdW5pY29kZT0iJiN4RTIwMzsiIGQ9Ik04NjQgNjM2SDE2MEE5NiA5NiAwIDAgMSA2NCA1NDBWNjBBOTYgOTYgMCAwIDEgMTYwLTM2SDg2NEE5NiA5NiAwIDAgMSA5NjAgNjBWNTQwQTk2IDk2IDAgMCAxIDg2NCA2MzZaTTEyOCA1NDBBMzIgMzIgMCAwIDAgMTYwIDU3Mkg4NjRBMzIgMzIgMCAwIDAgODk2IDU0MFYxMjRMNzUyIDIzOC43MkE1Ny43NiA1Ny43NiAwIDAgMSA2OTUuNjggMjM4LjcyTDU5MiAxNDAgMzU2LjggMzcyLjE2QTQ2LjcyIDQ2LjcyIDAgMCAxIDI4Ni4wOCAzNjkuNkwxMjggMTU2Wk03NTIgNDEyQTk2IDk2IDAgMCAwIDY1NiAzMTYgOTYgOTYgMCAwIDAgNTYwIDQxMiA5NiA5NiAwIDAgMCA3NTIgNDEyWiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTIwNCIgdW5pY29kZT0iJiN4RTIwNDsiIGQ9Ik03NTIgMzAwQTE3NiAxNzYgMCAxIDEgOTI4IDEyNCAxNzYgMTc2IDAgMCAxIDc1MiAzMDBaTTc1MiAwLjhBMzAuODggMzAuODggMCAxIDAgNzgyLjg4IDMxLjY4IDMwLjcyIDMwLjcyIDAgMCAwIDc1MiAwLjhaTTc2OC45NiA5My4xMkExNy4xMiAxNy4xMiAwIDAgMCA3MzUuMDQgOTMuMTJTNzIxLjI4IDIxMS44NCA3MjEuMjggMjE2LjMyQTMwLjg4IDMwLjg4IDAgMSAwIDc4Mi44OCAyMTYuMzJDNzgyLjg4IDIxMS44NCA3NjguOTYgOTMuMTIgNzY4Ljk2IDkzLjEyWk04MDAgNjM2SDQ4MEw0MzUuNjggNTQ2LjU2IDQxMi4zMiA0NTcuMTIgMzQyLjA4IDM3MS41MiAzNzIuOTYgNDU3LjEyIDMyNi4wOCA1NDYuNTYgMzM2IDU3MkgzMzZWNTcyLjk2TDM1OS41MiA2MzZIMTYwQTk2IDk2IDAgMCAxIDY0IDU0MFY2MEE5NiA5NiAwIDAgMSAxNjAtMzZINTczLjQ0QTIzOC44OCAyMzguODggMCAwIDAgNTEyIDEyNCAyNDMuMiAyNDMuMiAwIDAgMCA1MjAuMTYgMTg1LjQ0TDM1Ni44IDI5Mi4xNkE0Ni43MiA0Ni43MiAwIDAgMSAyODYuMDggMjg5LjZMMTI4IDE1NlY1NDBBMzIgMzIgMCAwIDAgMTYwIDU3MkgyNzguNEwyNzIgNTI4LjY0IDM0Mi4wOCA0NTcuMTIgMzI3LjM2IDMzMiA0MzUuNjggNDM5LjM2IDUzMC40IDU3Mkg4MDBBMzIgMzIgMCAwIDAgODMyIDU0MFYzNTAuMDhBMjQxLjkyIDI0MS45MiAwIDAgMCA4OTYgMzE2VjU0MEE5NiA5NiAwIDAgMSA4MDAgNjM2Wk03MjAgNDEyQTgwIDgwIDAgMCAwIDY0MCAzMzIgODAgODAgMCAwIDAgNTYwIDQxMiA4MCA4MCAwIDAgMCA3MjAgNDEyWiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTIwNSIgdW5pY29kZT0iJiN4RTIwNTsiIGQ9Ik04OTYgNjM2SDEyOEE2NCA2NCAwIDAgMSA2NCA1NzJWMjhBNjQgNjQgMCAwIDEgMTI4LTM2SDg5NkE2NCA2NCAwIDAgMSA5NjAgMjhWNTcyQTY0IDY0IDAgMCAxIDg5NiA2MzZaTTg5NiAyOEgxMjhWNTcySDg5NlpNMzI3Ljg0IDE2Mi43MkgzODAuNDhWNDM4LjcySDMzNy43NkE5Ny4xMiA5Ny4xMiAwIDAgMCAzMDQgMzk0LjcyIDE1MC41NiAxNTAuNTYgMCAwIDAgMjU5LjIgMzY5LjEyVjMyMS4xMkExODIuNTYgMTgyLjU2IDAgMCAxIDMyNy4zNiAzNjEuMTJaTTQ4MC42NCAzNjEuNzZINTMzLjI4VjMwOS4xMkg0ODAuNjRWMzYxLjc2Wk00ODAuNjQgMjE1LjM2SDUzMy4yOFYxNjIuNzJINDgwLjY0VjIxNS4zNlpNNjY5LjI4IDE2Mi43Mkg3MjEuOTJWNDM4LjcySDY3OS4yQTk3LjEyIDk3LjEyIDAgMCAwIDY0NS45MiAzOTQuNzIgMTUwLjU2IDE1MC41NiAwIDAgMCA2MDEuMTIgMzY5LjEyVjMyMS4xMkExODIuNTYgMTgyLjU2IDAgMCAxIDY2OS4yOCAzNjEuMTJaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMjA2IiB1bmljb2RlPSImI3hFMjA2OyIgZD0iTTgyNS42IDIuNEM4MjUuNi0xMC40IDgxNi0yMCA4MDMuMi0yMEgyNDkuNkMyMzYuOC0yMCAyMjcuMi0xMC40IDIyNy4yIDIuNFYzMjguOEw5NiAyMDAuOEgxNjMuMlYtMjBDMTYzLjItNTUuMiAxOTItODQgMjI3LjItODRIODI1LjZDODYwLjgtODQgODg5LjYtNTUuMiA4ODkuNi0yMFYyNjEuNkw4MjUuNiAyMDAuOFYyLjRaTTIyNy4yIDU5Ny42QzIyNy4yIDYxMC40IDIzNi44IDYyMCAyNDkuNiA2MjBIODA5LjZDODIyLjQgNjIwIDgzMiA2MTAuNCA4MzIgNTk3LjZWMzAwTDk2My4yIDQzNy42SDg4OS42VjYyMEM4ODkuNiA2NTUuMiA4NjAuOCA2ODQgODI1LjYgNjg0SDIyNy4yQzE5MiA2ODQgMTYzLjIgNjU1LjIgMTYzLjIgNjIwVjM2Ny4yTDIyNy4yIDQzMS4yVjU5Ny42Wk01NTYuOCAxMDhWMjMyLjhINjQzLjJWMjA3LjJINzAwLjhWNDI0LjhINTU2LjhWNDkySDQ5OS4yVjQyNC44SDM1MlYyMDRINDA5LjZWMjMyLjhINDk2VjEwOEg1NTYuOFpNNjQzLjIgMjg3LjJINTU2LjhWMzcwLjRINjQzLjJWMjg3LjJaTTQ5NiAyODcuMkg0MDkuNlYzNzAuNEg0OTZWMjg3LjJaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCiAgICAgIDxnbHlwaCBnbHlwaC1uYW1lPSJ1bmlFMjA3IiB1bmljb2RlPSImI3hFMjA3OyIgZD0iTTQ2NCAzODYuNFY0NDcuMkgzMDAuOFYxNTZINDcwLjRWMjE2LjhIMzY4VjI3Ny42SDQ1Ny42VjMzMkgzNjhWMzg2LjRINDY0Wk0yMjcuMiAzMjguOFYtMC44QzIyNy4yLTEzLjYgMjM2LjgtMjMuMiAyNDkuNi0yMy4yTDI0OS42LTIzLjJIODAzLjJDODE2LTIzLjIgODI1LjYtMTMuNiA4MjUuNi0wLjhMODI1LjYtMC44VjIwMC44TDg4OS42IDI2MS42Vi0yMEM4ODkuNi01NS4yIDg2MC44LTg0IDgyNS42LTg0TDgyNS42LTg0SDIyNy4yQzE5Mi04NCAxNjMuMi01NS4yIDE2My4yLTIwTDE2My4yLTIwVjIwMC44SDk2TDIyNy4yIDMyOC44Wk03NTguNCA0NDRWMTUyLjhINjkxLjJMNTc2IDM0MS42IDU3Mi44IDM0NC44VjE0OS42SDUwOC44VjQ0MC44SDU4Mi40TDY5NC40IDI2MS42IDY5Ny42IDI1OC40VjQ0Ny4ySDc1OC40Wk04MjUuNiA2ODRDODYwLjggNjg0IDg4OS42IDY1NS4yIDg4OS42IDYyMEw4ODkuNiA2MjBWNDM3LjZIOTYzLjJMODI4LjggMzAwVjU5Ny42QzgyOC44IDYxMC40IDgxOS4yIDYyMCA4MDYuNCA2MjBMODA2LjQgNjIwSDI0OS42QzIzNi44IDYyMCAyMjcuMiA2MTAuNCAyMjcuMiA1OTcuNkwyMjcuMiA1OTcuNlY0MzEuMkwxNjMuMiAzNjcuMlY2MjBDMTYzLjIgNjU1LjIgMTkyIDY4NCAyMjcuMiA2ODRMMjI3LjIgNjg0SDgyNS42WiIgIGhvcml6LWFkdi14PSIxMDI0IiB2ZXJ0LWFkdi15PSIxMDI0IiAgLz4KCiAgICAgIAogICAgICA8Z2x5cGggZ2x5cGgtbmFtZT0idW5pRTIwOCIgdW5pY29kZT0iJiN4RTIwODsiIGQ9Ik04MjUuNiAyLjRDODI1LjYtMTAuNCA4MTYtMjAgODAzLjItMjBIMjQ5LjZDMjM2LjgtMjAgMjI3LjItMTAuNCAyMjcuMiAyLjRWMzI4LjhMOTYgMjAwLjhIMTYzLjJWLTIwQzE2My4yLTU1LjIgMTkyLTg0IDIyNy4yLTg0SDgyNS42Qzg2MC44LTg0IDg4OS42LTU1LjIgODg5LjYtMjBWMjYxLjZMODI1LjYgMjAwLjhWMi40Wk0yMjcuMiA1OTcuNkMyMjcuMiA2MTAuNCAyMzYuOCA2MjAgMjQ5LjYgNjIwSDgwOS42QzgyMi40IDYyMCA4MzIgNjEwLjQgODMyIDU5Ny42VjMwMEw5NjMuMiA0MzcuNkg4ODkuNlY2MjBDODg5LjYgNjU1LjIgODYwLjggNjg0IDgyNS42IDY4NEgyMjcuMkMxOTIgNjg0IDE2My4yIDY1NS4yIDE2My4yIDYyMFYzNjcuMkwyMjcuMiA0MzEuMlY1OTcuNlpNNTg4LjggNzZDNTkyIDkyIDU5MiAxMTEuMiA1OTUuMiAxMjcuMiA2MTEuMiAxMjAuOCA3MzIuOCAyMjYuNCA2MzMuNiAyNjhMNjMzLjYgMjY4QzYxNC40IDIzNiA1ODUuNiAyMDAuOCA1NDQgMTY4LjggNTUwLjQgMTU5LjIgNTUzLjYgMTQ5LjYgNTYwIDE0MCA1MzcuNiAxMjQgNTE4LjQgMTExLjIgNTE1LjIgMTA4IDUxNS4yIDEwOCA1MDUuNiAxMTcuNiA0OTYgMTQwIDQ4My4yIDEzMy42IDQ3MC40IDEyNy4yIDQ1NC40IDEyNCAzNzcuNiA5OC40IDM1MiAyMjMuMiAzNjEuNiAyNDguOCAzNzEuMiAyNjggNDAwIDMwNi40IDQ2NCAzMjIuNCA0NjQgMzM1LjIgNDY3LjIgMzQ0LjggNDcwLjQgMzU3LjYgNDMyIDM1Ny42IDM5MC40IDM2MC44IDM0OC44IDM3Ni44IDM1OC40IDM5Mi44IDM2NC44IDQwOC44IDM3MS4yIDQyMS42IDM3MS4yIDQyMS42IDQwNi40IDQwNS42IDQ4My4yIDQxMiA0ODkuNiA0MzcuNiA1MDIuNCA0NjMuMiA1MTIgNDg1LjZMNTU2LjggNDY2LjRDNTU2LjggNDY2LjQgNTQ3LjIgNDUwLjQgNTQwLjggNDIxLjYgNTY2LjQgNDI4IDU5NS4yIDQzNC40IDYyMC44IDQ0NCA2MzMuNiA0MTguNCA2NTIuOCA0MDUuNiA2NTIuOCA0MDUuNlM1OTguNCAzNzYuOCA1MjQuOCAzNjRDNTIxLjYgMzUxLjIgNTIxLjYgMzQxLjYgNTE4LjQgMzI4LjggNTQ0IDMyOC44IDU2OS42IDMyOC44IDYwMS42IDMyNS42IDYxNC40IDMzOC40IDYxMS4yIDM1Ny42IDYxMS4yIDM1Ny42TDY1OS4yIDM1MS4yQzY1OS4yIDM1MS4yIDY1NiAzMzguNCA2NDYuNCAzMTYgNjYyLjQgMzA5LjYgNzA0IDI5MC40IDcxMC40IDIzNiA3MjkuNiAxNzUuMiA2NDkuNiA2OS42IDU4OC44IDc2TDU4OC44IDc2IDU4OC44IDc2Wk00MDYuNCAyMjYuNEM0MDYuNCAyMTMuNiA0MTYgMTY4LjggNDMyIDE2OC44UzQ3MC40IDE4MS42IDQ3MC40IDE4MS42IDQ2MC44IDIyOS42IDQ2MC44IDI2NC44QzQzMiAyNTguNCA0MDYuNCAyMzkuMiA0MDYuNCAyMjYuNEw0MDYuNCAyMjYuNFpNNTcyLjggMjc0LjRDNTY2LjQgMjc3LjYgNTE1LjIgMjc0LjQgNTE1LjIgMjc0LjQgNTA4LjggMjYxLjYgNTIxLjYgMjE2LjggNTIxLjYgMjE2LjhTNTgyLjQgMjcxLjIgNTcyLjggMjc0LjRaIiAgaG9yaXotYWR2LXg9IjEwMjQiIHZlcnQtYWR2LXk9IjEwMjQiICAvPgoKICAgICAgCgogIDwvZm9udD4KICA8L2RlZnM+Cjwvc3ZnPg==');
        /***/ }),

      /***/ './node_modules/bk-magic-vue/lib/ui/iconfont.css':
      /*! *******************************************************!*\
  !*** ./node_modules/bk-magic-vue/lib/ui/iconfont.css ***!
  \*******************************************************/
      /***/ ((module, __unused_webpack_exports, __webpack_require__) => {
        // style-loader: Adds some css to the DOM by adding a <style> tag

        // load the styles
        let content = __webpack_require__(/*! !!../../../css-loader/dist/cjs.js??clonedRuleSet-4[0].rules[0].use[1]!./iconfont.css */ './node_modules/css-loader/dist/cjs.js??clonedRuleSet-4[0].rules[0].use[1]!./node_modules/bk-magic-vue/lib/ui/iconfont.css');
        if (content.__esModule) content = content.default;
        if (typeof content === 'string') content = [[module.id, content, '']];
        if (content.locals) module.exports = content.locals;
        // add the styles to the DOM
        const add = (__webpack_require__(/*! !../../../vue-style-loader/lib/addStylesClient.js */ './node_modules/vue-style-loader/lib/addStylesClient.js').default);
        const update = add('1a9ea452', content, false, {});
        // Hot Module Replacement
        if (false) {}
        /***/ }),

      /***/ './node_modules/bk-magic-vue/lib/ui/popover.css':
      /*! ******************************************************!*\
  !*** ./node_modules/bk-magic-vue/lib/ui/popover.css ***!
  \******************************************************/
      /***/ ((module, __unused_webpack_exports, __webpack_require__) => {
        // style-loader: Adds some css to the DOM by adding a <style> tag

        // load the styles
        let content = __webpack_require__(/*! !!../../../css-loader/dist/cjs.js??clonedRuleSet-4[0].rules[0].use[1]!./popover.css */ './node_modules/css-loader/dist/cjs.js??clonedRuleSet-4[0].rules[0].use[1]!./node_modules/bk-magic-vue/lib/ui/popover.css');
        if (content.__esModule) content = content.default;
        if (typeof content === 'string') content = [[module.id, content, '']];
        if (content.locals) module.exports = content.locals;
        // add the styles to the DOM
        const add = (__webpack_require__(/*! !../../../vue-style-loader/lib/addStylesClient.js */ './node_modules/vue-style-loader/lib/addStylesClient.js').default);
        const update = add('6c84eb5b', content, false, {});
        // Hot Module Replacement
        if (false) {}
        /***/ }),

      /***/ './node_modules/bk-magic-vue/lib/ui/search-select-menu.css':
      /*! *****************************************************************!*\
  !*** ./node_modules/bk-magic-vue/lib/ui/search-select-menu.css ***!
  \*****************************************************************/
      /***/ ((module, __unused_webpack_exports, __webpack_require__) => {
        // style-loader: Adds some css to the DOM by adding a <style> tag

        // load the styles
        let content = __webpack_require__(/*! !!../../../css-loader/dist/cjs.js??clonedRuleSet-4[0].rules[0].use[1]!./search-select-menu.css */ './node_modules/css-loader/dist/cjs.js??clonedRuleSet-4[0].rules[0].use[1]!./node_modules/bk-magic-vue/lib/ui/search-select-menu.css');
        if (content.__esModule) content = content.default;
        if (typeof content === 'string') content = [[module.id, content, '']];
        if (content.locals) module.exports = content.locals;
        // add the styles to the DOM
        const add = (__webpack_require__(/*! !../../../vue-style-loader/lib/addStylesClient.js */ './node_modules/vue-style-loader/lib/addStylesClient.js').default);
        const update = add('0f15ab5d', content, false, {});
        // Hot Module Replacement
        if (false) {}
        /***/ }),

      /***/ './node_modules/bk-magic-vue/lib/ui/search-select.css':
      /*! ************************************************************!*\
  !*** ./node_modules/bk-magic-vue/lib/ui/search-select.css ***!
  \************************************************************/
      /***/ ((module, __unused_webpack_exports, __webpack_require__) => {
        // style-loader: Adds some css to the DOM by adding a <style> tag

        // load the styles
        let content = __webpack_require__(/*! !!../../../css-loader/dist/cjs.js??clonedRuleSet-4[0].rules[0].use[1]!./search-select.css */ './node_modules/css-loader/dist/cjs.js??clonedRuleSet-4[0].rules[0].use[1]!./node_modules/bk-magic-vue/lib/ui/search-select.css');
        if (content.__esModule) content = content.default;
        if (typeof content === 'string') content = [[module.id, content, '']];
        if (content.locals) module.exports = content.locals;
        // add the styles to the DOM
        const add = (__webpack_require__(/*! !../../../vue-style-loader/lib/addStylesClient.js */ './node_modules/vue-style-loader/lib/addStylesClient.js').default);
        const update = add('49c265ca', content, false, {});
        // Hot Module Replacement
        if (false) {}
        /***/ }),

      /***/ './node_modules/vue-style-loader/lib/addStylesClient.js':
      /*! **************************************************************!*\
  !*** ./node_modules/vue-style-loader/lib/addStylesClient.js ***!
  \**************************************************************/
      /***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {
        'use strict';
        __webpack_require__.r(__webpack_exports__);
        /* harmony export */ __webpack_require__.d(__webpack_exports__, {
          /* harmony export */   default: () => (/* binding */ addStylesClient)
          /* harmony export */ });
        /* harmony import */ const _listToStyles__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! ./listToStyles */ './node_modules/vue-style-loader/lib/listToStyles.js');
        /*
  MIT License http://www.opensource.org/licenses/mit-license.php
  Author Tobias Koppers @sokra
  Modified by Evan You @yyx990803
*/


        const hasDocument = typeof document !== 'undefined';

        if (typeof DEBUG !== 'undefined' && DEBUG) {
          if (!hasDocument) {
            throw new Error('vue-style-loader cannot be used in a non-browser environment. '
    + 'Use { target: \'node\' } in your Webpack config to indicate a server-rendering environment.');
          }
        }

        /*
type StyleObject = {
  id: number;
  parts: Array<StyleObjectPart>
}

type StyleObjectPart = {
  css: string;
  media: string;
  sourceMap: ?string
}
*/

        const stylesInDom = {/*
  [id: number]: {
    id: number,
    refs: number,
    parts: Array<(obj?: StyleObjectPart) => void>
  }
*/};

        const head = hasDocument && (document.head || document.getElementsByTagName('head')[0]);
        let singletonElement = null;
        let singletonCounter = 0;
        let isProduction = false;
        const noop = function () {};
        let options = null;
        const ssrIdKey = 'data-vue-ssr-id';

        // Force single-tag solution on IE6-9, which has a hard limit on the # of <style>
        // tags it will allow on a page
        const isOldIE = typeof navigator !== 'undefined' && /msie [6-9]\b/.test(navigator.userAgent.toLowerCase());

        function addStylesClient(parentId, list, _isProduction, _options) {
          isProduction = _isProduction;

          options = _options || {};

          let styles = (0, _listToStyles__WEBPACK_IMPORTED_MODULE_0__.default)(parentId, list);
          addStylesToDom(styles);

          return function update(newList) {
            const mayRemove = [];
            for (var i = 0; i < styles.length; i++) {
              const item = styles[i];
              var domStyle = stylesInDom[item.id];
              domStyle.refs--;
              mayRemove.push(domStyle);
            }
            if (newList) {
              styles = (0, _listToStyles__WEBPACK_IMPORTED_MODULE_0__.default)(parentId, newList);
              addStylesToDom(styles);
            } else {
              styles = [];
            }
            for (var i = 0; i < mayRemove.length; i++) {
              var domStyle = mayRemove[i];
              if (domStyle.refs === 0) {
                for (let j = 0; j < domStyle.parts.length; j++) {
                  domStyle.parts[j]();
                }
                delete stylesInDom[domStyle.id];
              }
            }
          };
        }

        function addStylesToDom(styles /* Array<StyleObject> */) {
          for (let i = 0; i < styles.length; i++) {
            const item = styles[i];
            const domStyle = stylesInDom[item.id];
            if (domStyle) {
              domStyle.refs++;
              for (var j = 0; j < domStyle.parts.length; j++) {
                domStyle.parts[j](item.parts[j]);
              }
              for (; j < item.parts.length; j++) {
                domStyle.parts.push(addStyle(item.parts[j]));
              }
              if (domStyle.parts.length > item.parts.length) {
                domStyle.parts.length = item.parts.length;
              }
            } else {
              const parts = [];
              for (var j = 0; j < item.parts.length; j++) {
                parts.push(addStyle(item.parts[j]));
              }
              stylesInDom[item.id] = { id: item.id, refs: 1, parts };
            }
          }
        }

        function createStyleElement() {
          const styleElement = document.createElement('style');
          styleElement.type = 'text/css';
          head.appendChild(styleElement);
          return styleElement;
        }

        function addStyle(obj /* StyleObjectPart */) {
          let update; let remove;
          let styleElement = document.querySelector(`style[${ssrIdKey}~="${obj.id}"]`);

          if (styleElement) {
            if (isProduction) {
              // has SSR styles and in production mode.
              // simply do nothing.
              return noop;
            }
            // has SSR styles but in dev mode.
            // for some reason Chrome can't handle source map in server-rendered
            // style tags - source maps in <style> only works if the style tag is
            // created and inserted dynamically. So we remove the server rendered
            // styles and inject new ones.
            styleElement.parentNode.removeChild(styleElement);
          }

          if (isOldIE) {
            // use singleton mode for IE9.
            const styleIndex = singletonCounter++;
            styleElement = singletonElement || (singletonElement = createStyleElement());
            update = applyToSingletonTag.bind(null, styleElement, styleIndex, false);
            remove = applyToSingletonTag.bind(null, styleElement, styleIndex, true);
          } else {
            // use multi-style-tag mode in all other cases
            styleElement = createStyleElement();
            update = applyToTag.bind(null, styleElement);
            remove = function () {
              styleElement.parentNode.removeChild(styleElement);
            };
          }

          update(obj);

          return function updateStyle(newObj /* StyleObjectPart */) {
            if (newObj) {
              if (newObj.css === obj.css
          && newObj.media === obj.media
          && newObj.sourceMap === obj.sourceMap) {
                return;
              }
              update(obj = newObj);
            } else {
              remove();
            }
          };
        }

        const replaceText = (function () {
          const textStore = [];

          return function (index, replacement) {
            textStore[index] = replacement;
            return textStore.filter(Boolean).join('\n');
          };
        }());

        function applyToSingletonTag(styleElement, index, remove, obj) {
          const css = remove ? '' : obj.css;

          if (styleElement.styleSheet) {
            styleElement.styleSheet.cssText = replaceText(index, css);
          } else {
            const cssNode = document.createTextNode(css);
            const { childNodes } = styleElement;
            if (childNodes[index]) styleElement.removeChild(childNodes[index]);
            if (childNodes.length) {
              styleElement.insertBefore(cssNode, childNodes[index]);
            } else {
              styleElement.appendChild(cssNode);
            }
          }
        }

        function applyToTag(styleElement, obj) {
          let { css } = obj;
          const { media } = obj;
          const { sourceMap } = obj;

          if (media) {
            styleElement.setAttribute('media', media);
          }
          if (options.ssrId) {
            styleElement.setAttribute(ssrIdKey, obj.id);
          }

          if (sourceMap) {
            // https://developer.chrome.com/devtools/docs/javascript-debugging
            // this makes source maps inside style tags work properly in Chrome
            css += `\n/*# sourceURL=${sourceMap.sources[0]} */`;
            // http://stackoverflow.com/a/26603875
            css += `\n/*# sourceMappingURL=data:application/json;base64,${btoa(unescape(encodeURIComponent(JSON.stringify(sourceMap))))} */`;
          }

          if (styleElement.styleSheet) {
            styleElement.styleSheet.cssText = css;
          } else {
            while (styleElement.firstChild) {
              styleElement.removeChild(styleElement.firstChild);
            }
            styleElement.appendChild(document.createTextNode(css));
          }
        }
        /***/ }),

      /***/ './node_modules/vue-style-loader/lib/listToStyles.js':
      /*! ***********************************************************!*\
  !*** ./node_modules/vue-style-loader/lib/listToStyles.js ***!
  \***********************************************************/
      /***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {
        'use strict';
        __webpack_require__.r(__webpack_exports__);
        /* harmony export */ __webpack_require__.d(__webpack_exports__, {
          /* harmony export */   default: () => (/* binding */ listToStyles)
          /* harmony export */ });
        /**
 * Translates the list format produced by css-loader into something
 * easier to manipulate.
 */
        function listToStyles(parentId, list) {
          const styles = [];
          const newStyles = {};
          for (let i = 0; i < list.length; i++) {
            const item = list[i];
            const id = item[0];
            const css = item[1];
            const media = item[2];
            const sourceMap = item[3];
            const part = {
              id: `${parentId}:${i}`,
              css,
              media,
              sourceMap
            };
            if (!newStyles[id]) {
              styles.push(newStyles[id] = { id, parts: [part] });
            } else {
              newStyles[id].parts.push(part);
            }
          }
          return styles;
        }
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
        /******/ 			id: moduleId,
        /******/ 			// no module.loaded needed
        /******/ 			exports: {}
        /******/ 		};
      /******/
      /******/ 		// Execute the module function
      /******/ 		__webpack_modules__[moduleId].call(module.exports, module, module.exports, __webpack_require__);
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
    /******/ 	/* webpack/runtime/publicPath */
    /******/ 	(() => {
      /******/ 		__webpack_require__.p = '/';
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
      /* harmony import */ const bk_magic_vue_lib_search_select_js__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! bk-magic-vue/lib/search-select.js */ './node_modules/bk-magic-vue/lib/search-select.js');
      /* harmony import */ const bk_magic_vue_lib_search_select_js__WEBPACK_IMPORTED_MODULE_0___default = /* #__PURE__*/__webpack_require__.n(bk_magic_vue_lib_search_select_js__WEBPACK_IMPORTED_MODULE_0__);
      /* harmony import */ const bk_magic_vue_lib_ui_search_select_css__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! bk-magic-vue/lib/ui/search-select.css */ './node_modules/bk-magic-vue/lib/ui/search-select.css');
      /* harmony import */ const bk_magic_vue_lib_ui_search_select_css__WEBPACK_IMPORTED_MODULE_1___default = /* #__PURE__*/__webpack_require__.n(bk_magic_vue_lib_ui_search_select_css__WEBPACK_IMPORTED_MODULE_1__);
      /* harmony import */ const bk_magic_vue_lib_ui_popover_css__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! bk-magic-vue/lib/ui/popover.css */ './node_modules/bk-magic-vue/lib/ui/popover.css');
      /* harmony import */ const bk_magic_vue_lib_ui_popover_css__WEBPACK_IMPORTED_MODULE_2___default = /* #__PURE__*/__webpack_require__.n(bk_magic_vue_lib_ui_popover_css__WEBPACK_IMPORTED_MODULE_2__);
      /* harmony import */ const bk_magic_vue_lib_ui_search_select_menu_css__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(/*! bk-magic-vue/lib/ui/search-select-menu.css */ './node_modules/bk-magic-vue/lib/ui/search-select-menu.css');
      /* harmony import */ const bk_magic_vue_lib_ui_search_select_menu_css__WEBPACK_IMPORTED_MODULE_3___default = /* #__PURE__*/__webpack_require__.n(bk_magic_vue_lib_ui_search_select_menu_css__WEBPACK_IMPORTED_MODULE_3__);
      /* harmony import */ const bk_magic_vue_lib_ui_iconfont_css__WEBPACK_IMPORTED_MODULE_4__ = __webpack_require__(/*! bk-magic-vue/lib/ui/iconfont.css */ './node_modules/bk-magic-vue/lib/ui/iconfont.css');
      /* harmony import */ const bk_magic_vue_lib_ui_iconfont_css__WEBPACK_IMPORTED_MODULE_4___default = /* #__PURE__*/__webpack_require__.n(bk_magic_vue_lib_ui_iconfont_css__WEBPACK_IMPORTED_MODULE_4__);
      /* harmony import */ const vue__WEBPACK_IMPORTED_MODULE_5__ = __webpack_require__(/*! vue */ './node_modules/vue/dist/vue.runtime.esm.js');
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
        Vue2: vue__WEBPACK_IMPORTED_MODULE_5__.default,
        BkSearchSelect: (bk_magic_vue_lib_search_select_js__WEBPACK_IMPORTED_MODULE_0___default())
      });
    })();

    /******/ 	return __webpack_exports__;
    /******/ })()));
// # sourceMappingURL=index.js.map
