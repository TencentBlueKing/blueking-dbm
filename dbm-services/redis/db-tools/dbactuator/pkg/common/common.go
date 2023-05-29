// Package common 一些公共类定义
package common

// MySet 通过泛型自定义集合类型
type MySet[T int | string] map[T]struct{}

// Has 判断集合中是否有该元素
func (s MySet[T]) Has(key T) bool {
	_, ok := s[key]
	return ok
}

// Add 向集合中添加元素
func (s MySet[T]) Add(key T) {
	s[key] = struct{}{}
}

// Delete 从集合中删除元素
func (s MySet[T]) Delete(key T) {
	delete(s, key)
}

// ToStringSlice 返回对应的数组类型(不保证原始顺序)
func (s MySet[T]) ToStringSlice() (ret []T) {
	ret = make([]T, 0, len(s))
	for k := range s {
		ret = append(ret, k)
	}
	return ret
}

// UniqueSlice 去重,保证原始顺序
func UniqueSlice[T int | string](l01 []T) (ret []T) {
	var tmp MySet[T] = make(MySet[T])
	for _, ele := range l01 {
		if !tmp.Has(ele) {
			ret = append(ret, ele)
			tmp.Add(ele)
		}
	}
	return ret
}
