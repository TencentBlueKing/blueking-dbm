//go:build windows
// +build windows

package osutil

// 这里只是为了能在 windows 编译成功，不一定可以使用

// FindFirstMountPoint find first mountpoint in prefer order
func FindFirstMountPoint(paths ...string) (string, error) {
	return "/data", nil
}

// FindFirstMountPointProxy TODO
func FindFirstMountPointProxy(paths ...string) (string, error) {
	return "/data", nil
}
