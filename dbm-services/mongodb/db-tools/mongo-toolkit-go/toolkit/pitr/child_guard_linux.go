//go:build linux

package pitr

import (
	"os/exec"
	"syscall"
)

// setChildDeathSignal 让 cmd 启动的子进程在本进程异常退出时被 kernel SIGKILL。
//
// 背景：mongo-toolkit-go 通过 exec.Command 起 mongodump 后用 cmd.Wait() 等待其退出。
// 在 mongo-toolkit-go 正常结束的路径下，mongodump 一定先于父进程退出。
// 但若 mongo-toolkit-go 被 panic / SIGKILL / OOM 等异常终止，mongodump 会被
// reparent 到 init 继续运行：此时父进程持有的 port 维度 flock 已随 fd 关闭被释放，
// 下一轮 dbmon cron tick 可成功 TryLock 并再起一份 mongodump，
// 导致同一个 mongod 上出现两份并发的 mongodump。
//
// 通过 Pdeathsig=SIGKILL，由 kernel 在父进程退出（不论原因）时强杀子进程，
// 从根上阻断孤儿 mongodump，配合现有 flock 即可保证 port 维度的真正互斥。
//
// 注意（Go runtime 陷阱）：Pdeathsig 的内核语义是父 *线程* 退出时触发，
// 而非父 *进程* 退出。Go 程序中如果调用 cmd.Start() 的 OS 线程被 runtime
// 销毁，子进程会被误杀。本包当前的使用方式（runCmdList 在同一 goroutine 内
// 串行 Start + Wait）不会触发该问题；若后续把 Wait 移到独立 goroutine，
// 或改用 errgroup 等会跨 goroutine/线程的写法，请在持有子进程的 goroutine
// 中显式调用 runtime.LockOSThread()。
func setChildDeathSignal(cmd *exec.Cmd) {
	cmd.SysProcAttr = &syscall.SysProcAttr{Pdeathsig: syscall.SIGKILL}
}
