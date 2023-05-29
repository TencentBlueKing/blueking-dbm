package util

import (
	"sync"
)

// Set TODO
type Set struct {
	m map[interface{}]bool
	sync.RWMutex
}

// NewSet TODO
func NewSet() *Set {
	return &Set{
		m: map[interface{}]bool{},
	}
}

// AddList TODO
func (s *Set) AddList(items []interface{}) {
	s.Lock()
	defer s.Unlock()
	for _, item := range items {
		s.m[item] = true
	}
}

// Add TODO
func (s *Set) Add(item interface{}) {
	s.Lock()
	defer s.Unlock()
	s.m[item] = true
}

// Remove TODO
func (s *Set) Remove(item interface{}) {
	s.Lock()
	defer s.Unlock()
	delete(s.m, item)
}

// Has TODO
func (s *Set) Has(item interface{}) bool {
	s.RLock()
	defer s.RUnlock()
	_, ok := s.m[item]
	return ok
}

// Len 用于排序
func (s *Set) Len() int {
	return len(s.List())
}

// Clear TODO
func (s *Set) Clear() {
	s.Lock()
	defer s.Unlock()
	s.m = map[interface{}]bool{}
}

// IsEmpty TODO
func (s *Set) IsEmpty() bool {
	if s.Len() == 0 {
		return true
	}
	return false
}

// List TODO
func (s *Set) List() []interface{} {
	s.RLock()
	defer s.RUnlock()
	list := []interface{}{}
	for item := range s.m {
		list = append(list, item)
	}
	return list
}

/*
func (s *Set) SortList() []int {
    s.RLock()
    defer s.RUnlock()
    list := []int{}
    for item := range s.m {
        list = append(list, item)
    }
    sort.Ints(list)
    return list
}

func main() {
    s := New()
    s.Add("1.1.1.1")
    s.Add("2.2.2.2")
    fmt.Println("无序的切片", s.List())
    fmt.Println("length:", len(s.List()))
}
*/
