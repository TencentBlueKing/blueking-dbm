package proxyuserlist

import (
	"bufio"
	"os"
	"strings"
)

func (c *Checker) compareMemAndFile(usersFromMem, usersFromFile []string) (onlyInMem, onlyInFile []string) {
	/*
		这种比较两个 slice, 并抽取各自独有的 element 的算法会更快, 理论上是 O(2(m+n))
		如果用传统的以一个 slice 做循环, 查找另一个 slice, 理论上是 O(mlog(n))

		BenchmarkMapIter-6              1000000000               0.001124 ns/op        0 B/op          0 allocs/op
		BenchmarkMapIter-6              1000000000               0.001228 ns/op        0 B/op          0 allocs/op
		BenchmarkMapIter-6              1000000000               0.001189 ns/op        0 B/op          0 allocs/op
		BenchmarkMapIter-6              1000000000               0.002286 ns/op        0 B/op          0 allocs/op
		BenchmarkMapIter-6              1000000000               0.001106 ns/op        0 B/op          0 allocs/op
		BenchmarkNormalIter-6           1000000000               0.1990 ns/op          0 B/op          0 allocs/op
		BenchmarkNormalIter-6           1000000000               0.1922 ns/op          0 B/op          0 allocs/op
		BenchmarkNormalIter-6           1000000000               0.1985 ns/op          0 B/op          0 allocs/op
		BenchmarkNormalIter-6           1000000000               0.1944 ns/op          0 B/op          0 allocs/op
		BenchmarkNormalIter-6           1000000000               0.1928 ns/op          0 B/op          0 allocs/op

		测试性能差别还是蛮大的
	*/
	stage := make(map[string]int)
	for _, u := range usersFromFile {
		stage[u] = 1
	}
	for _, u := range usersFromMem {
		if _, ok := stage[u]; !ok {
			stage[u] = 0
		}
		stage[u] -= 1
	}

	for k, v := range stage {
		if v == 1 {
			onlyInFile = append(onlyInFile, k)
		}
		if v == -1 {
			onlyInMem = append(onlyInMem, k)
		}
	}

	return
}

func isInUserFile(user string, f *os.File) bool {
	s := bufio.NewScanner(f)
	s.Split(bufio.ScanLines)

	for s.Scan() {
		if strings.TrimSpace(s.Text()) == strings.TrimSpace(user) {
			return true
		}
	}
	return false
}
