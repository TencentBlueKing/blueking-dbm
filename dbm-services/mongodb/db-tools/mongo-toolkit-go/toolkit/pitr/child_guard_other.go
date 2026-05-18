//go:build !linux

package pitr

import "os/exec"

// setChildDeathSignal 在非 Linux 平台上是空操作；生产环境只在 Linux 上跑。
// 该 stub 仅保证 mongo-toolkit-go 在开发机（macOS）上仍能编译。
func setChildDeathSignal(cmd *exec.Cmd) {}
