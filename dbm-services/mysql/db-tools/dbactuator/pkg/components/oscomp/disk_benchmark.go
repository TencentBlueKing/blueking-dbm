//go:build linux

/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package oscomp

import (
	"context"
	"fmt"
	"io"
	"math/rand"
	"os"
	"path/filepath"
	"runtime"
	"runtime/debug"
	"strconv"
	"strings"
	"sync"
	"sync/atomic"
	"syscall"
	"time"
	"unsafe"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
)

// 设计要点:
// 1. 仅支持文件模式 (target 必须是普通文件路径), 入口拒绝 /dev/ 开头的路径
//    本文件通篇不出现 isBlockDevice / blockDeviceSize 之类的块设备判断分支
// 2. 跑测前做:
//    - target 入参纯字符串校验 (不以 /dev/ 开头, 是绝对路径, 父目录存在)
//    - DB 进程黑名单扫描 (命中即拒)
//    - statfs 可用空间预检 (size + 1G 余量)
// 3. defer 注册清理 hook, 保证无论成功/失败/panic 都会清理 actuator 自己创建的测试文件
//    用户预先存在的 target 文件不删, 避免误删数据

const (
	alignSize   = 4096
	blockSize4K = 4 * 1024
	blockSize1M = 1024 * 1024
	defaultSize = "4G"
	minRuntime  = 1
	maxRuntime  = 600
	freeMargin  = int64(1024 * 1024 * 1024) // 1G 自由空间余量
	rampSeconds = 0                         // 不做 ramp_time, 用 runtime 抹平
)

// allowedTargetPrefixes target 必须落在这些目录下, 否则拒绝。
// 这是防御深度: 即便 flow 层校验失效 (或者别的非 flow 调用方手搓 payload),
// actuator 也会再挡一道, 避免误把测试文件指向 /etc/passwd / /usr/bin/* 这类系统关键文件。
//
// 选这三个前缀的原因:
//   - /data/    : DBM 体系下所有数据盘的常规挂载点
//   - /tmp/     : 通用临时目录
//   - /var/tmp/ : 通用临时目录 (持久化版本)
//
// 不走 "黑名单系统目录" 路线, 因为黑名单天生不可能枚举完整 (/etc /usr /bin
// /sbin /lib /lib64 /boot /root /var/lib/mysql ... 还有数据库实例自定义路径),
// 任何一处遗漏都是新事故。
var allowedTargetPrefixes = []string{
	"/data/",
	"/tmp/",
	"/var/tmp/",
}

// DiskBenchmarkParams payload extend, 来自 flow 入参
type DiskBenchmarkParams struct {
	// Target 测试目标文件绝对路径 (必填); 拒绝以 /dev/ 开头
	Target string `json:"target" validate:"required"`
	// Size 测试文件大小, 形如 4G/512M/1024K, target 不存在时按此创建
	Size string `json:"size,omitempty"`
	// Runtime 每个 phase 持续时长, 秒, 默认 30
	Runtime int `json:"runtime,omitempty"`
	// Jobs 随机 IO phase 的并发 worker 数, 默认 64
	Jobs int `json:"jobs,omitempty"`
	// ThroughputJobs 顺序 IO phase 的并发 worker 数, 默认 16
	ThroughputJobs int `json:"throughput_jobs,omitempty"`
}

// PhaseResult 单个 phase 的原始指标
type PhaseResult struct {
	Name      string  `json:"name"`
	Desc      string  `json:"desc"`
	Duration  float64 `json:"duration_sec"`
	Ops       int64   `json:"ops"`
	Bytes     int64   `json:"bytes"`
	IOPS      float64 `json:"iops"`
	BWMBps    float64 `json:"bw_mbps"`
	MeanLatMs float64 `json:"mean_lat_ms"`
}

// DiskBenchmarkResp actuator 输出, 字段名严格对齐 BaselineDisk 模型
type DiskBenchmarkResp struct {
	PerformanceIOPS               int64                  `json:"performance_iops"`
	PerformanceThroughputMBps     int64                  `json:"performance_throughput_mbps"`
	SequentialWriteThroughputMBps int64                  `json:"sequential_write_throughput_mbps"`
	RandomReadIOPS                int64                  `json:"random_read_iops"`
	WriteLatencyMs                float64                `json:"write_latency_ms"`
	Phases                        []*PhaseResult         `json:"phases"`
	Environment                   map[string]interface{} `json:"environment"`
}

// DiskBenchmarkComp main component
type DiskBenchmarkComp struct {
	Params DiskBenchmarkParams `json:"extend"`

	// internal state, 不导出
	fileSize        int64
	createdTestFile bool
	results         []*PhaseResult
}

// Example for --helper / --example
func (c *DiskBenchmarkComp) Example() interface{} {
	return DiskBenchmarkComp{
		Params: DiskBenchmarkParams{
			Target:         "/data/baseline_bench/fio_test.bin",
			Size:           "8G",
			Runtime:        30,
			Jobs:           64,
			ThroughputJobs: 16,
		},
	}
}

// Start 入口, 由 subcmd Steps 调用
func (c *DiskBenchmarkComp) Start() (err error) {
	if err = c.applyDefaults(); err != nil {
		return err
	}
	if err = c.validateParams(); err != nil {
		return err
	}
	if err = c.checkDBProcesses(); err != nil {
		return err
	}
	if err = c.prepareTarget(); err != nil {
		return err
	}

	// 关键: prepare 成功后立刻 defer 清理, 保证后续无论怎么退出都会清
	defer c.cleanupTarget()
	defer func() {
		if r := recover(); r != nil {
			err = fmt.Errorf("panic: %v\n%s", r, debug.Stack())
		}
	}()

	if err = c.runPhases(); err != nil {
		return err
	}
	return c.outputCtx()
}

// applyDefaults 填充默认值
func (c *DiskBenchmarkComp) applyDefaults() error {
	if c.Params.Size == "" {
		c.Params.Size = defaultSize
	}
	if c.Params.Runtime == 0 {
		c.Params.Runtime = 30
	}
	if c.Params.Jobs == 0 {
		c.Params.Jobs = 64
	}
	if c.Params.ThroughputJobs == 0 {
		c.Params.ThroughputJobs = 16
	}
	if c.Params.Runtime < minRuntime || c.Params.Runtime > maxRuntime {
		return fmt.Errorf("runtime 必须在 [%d, %d] 范围内, got %d", minRuntime, maxRuntime, c.Params.Runtime)
	}
	if c.Params.Jobs <= 0 || c.Params.Jobs > 4096 {
		return fmt.Errorf("jobs 必须在 (0, 4096] 范围内, got %d", c.Params.Jobs)
	}
	if c.Params.ThroughputJobs <= 0 || c.Params.ThroughputJobs > 256 {
		return fmt.Errorf("throughput_jobs 必须在 (0, 256] 范围内, got %d", c.Params.ThroughputJobs)
	}
	return nil
}

// validateParams 入口处的硬性参数校验
//
// 校验链 (任一失败立刻拒):
//  1. 非空 + 绝对路径 + 不以 /dev/ 开头
//  2. filepath.Clean 规范化路径, 防 ../ 注入
//  3. 路径白名单: 必须以 /data/ /tmp/ /var/tmp/ 之一开头 (字符串前缀)
//  4. 渐进式 EvalSymlinks 防 symlink 绕过 (resolveRealPath):
//     - 沿目标路径向上找第一个真实存在的祖先目录, 对它做 EvalSymlinks
//     - 把后续相对路径拼回去, 得到 target 的真实位置
//     - 真实位置仍必须落在白名单内
//
// 父目录可以不存在 — 由后续 prepareTarget 自动 MkdirAll 创建 (在白名单内是安全的)
func (c *DiskBenchmarkComp) validateParams() error {
	target := c.Params.Target
	if target == "" {
		return fmt.Errorf("target 不能为空")
	}
	if !filepath.IsAbs(target) {
		return fmt.Errorf("target 必须是绝对路径, got %q", target)
	}
	if strings.HasPrefix(target, "/dev/") {
		return fmt.Errorf("拒绝执行: target 不允许指向 /dev/ 设备节点, got %q. 本工具只支持文件模式压测", target)
	}

	// 规范化路径, 防止 /data/../etc/passwd 这类 ../ 注入
	cleanTarget := filepath.Clean(target)
	if !pathHasAllowedPrefix(cleanTarget) {
		return fmt.Errorf(
			"拒绝执行: target 必须落在白名单目录 %v 下, got %q. "+
				"本工具仅允许在数据盘/临时目录上做压测, 避免误覆盖系统关键文件",
			allowedTargetPrefixes, target,
		)
	}

	// 解析 target 的真实位置 (跟随 symlink), 父目录可以不存在 — 算法会沿路径
	// 向上找到第一个存在的祖先, 对它 EvalSymlinks, 再拼回相对部分
	realTarget, err := resolveRealPath(cleanTarget)
	if err != nil {
		return fmt.Errorf("解析 target 真实路径失败: %s: %w", cleanTarget, err)
	}
	if !pathHasAllowedPrefix(realTarget) {
		return fmt.Errorf(
			"拒绝执行: target 真实路径 %q 不在白名单 %v 下 (检测到 symlink 绕过)",
			realTarget, allowedTargetPrefixes,
		)
	}
	c.Params.Target = realTarget
	return nil
}

// pathHasAllowedPrefix 判断绝对路径是否落在 allowedTargetPrefixes 任一目录下
func pathHasAllowedPrefix(absPath string) bool {
	for _, p := range allowedTargetPrefixes {
		if strings.HasPrefix(absPath, p) {
			return true
		}
	}
	return false
}

// resolveRealPath 解析路径的真实位置, 即便部分末端不存在也能工作
//
// 算法: 沿 path 向上找到第一个真实存在的祖先, 对它 filepath.EvalSymlinks
// (一定能成功因为存在), 然后把 path 相对该祖先的剩余段拼回去, 得到 path 最终
// 在文件系统上的真实位置。
//
// 例:
//   - path=/data/baseline_bench/fio.bin, /data 存在但 /data/baseline_bench 不存在
//     → 第一个存在的祖先是 /data → EvalSymlinks(/data) = /data → realTarget = /data/baseline_bench/fio.bin
//   - path=/data/baseline_bench/fio.bin, /data 是 symlink 指向 /etc
//     → 第一个存在的祖先是 /data → EvalSymlinks(/data) = /etc → realTarget = /etc/baseline_bench/fio.bin
//     → 后续白名单检查会拒
func resolveRealPath(path string) (string, error) {
	p := filepath.Clean(path)
	cur := p
	for cur != "/" && cur != "." {
		if _, err := os.Stat(cur); err == nil {
			real, err := filepath.EvalSymlinks(cur)
			if err != nil {
				return "", err
			}
			rest := strings.TrimPrefix(p, cur)
			return filepath.Join(real, rest), nil
		} else if !os.IsNotExist(err) {
			return "", err
		}
		cur = filepath.Dir(cur)
	}
	// 一直到 / 都找不到 (理论上 / 一定存在, 这里只是防御)
	return p, nil
}

// checkDBProcesses actuator 内层防御: 主机有 DB 进程在跑就拒
func (c *DiskBenchmarkComp) checkDBProcesses() error {
	hits, err := ScanDBProcesses()
	if err != nil {
		return fmt.Errorf("scan db processes: %w", err)
	}
	if len(hits) > 0 {
		return FormatHitsError(hits)
	}
	logger.Info("DB process check passed: 主机上没有检测到任何 DB 进程")
	return nil
}

// prepareTarget statfs 空间预检 + 强制排他创建测试文件
//
// 安全策略 (用户确认): target 必须不存在, 由 actuator 排他创建。
// 不再支持 "已存在文件复用/扩容" 分支, 避免一旦 target 误指向系统关键文件
// (/etc/passwd, /usr/bin/*, 数据库实例 ibdata1 等) 就直接 truncate 毁掉。
// 副作用: 每次跑都要写 size 字节; 不能复用预生成的大文件。可以接受。
func (c *DiskBenchmarkComp) prepareTarget() error {
	sz, err := parseSize(c.Params.Size)
	if err != nil {
		return fmt.Errorf("parse size %q: %w", c.Params.Size, err)
	}
	c.fileSize = sz

	parent := filepath.Dir(c.Params.Target)
	// 父目录不存在则自动 MkdirAll 创建。validateParams 已确认 target 真实位置
	// 在白名单内, 所以 mkdir 在白名单目录下是安全的, 不会创建到 /etc/ /usr/ 之类
	if _, err := os.Stat(parent); err != nil {
		if !os.IsNotExist(err) {
			return fmt.Errorf("stat %s: %w", parent, err)
		}
		logger.Info("父目录不存在, 自动创建: %s", parent)
		if err := os.MkdirAll(parent, 0o755); err != nil {
			return fmt.Errorf("创建父目录失败: %s: %w", parent, err)
		}
	}
	var stat syscall.Statfs_t
	if err := syscall.Statfs(parent, &stat); err != nil {
		return fmt.Errorf("statfs %s: %w", parent, err)
	}
	avail := int64(stat.Bavail) * int64(stat.Bsize)
	required := sz + freeMargin
	if avail < required {
		return fmt.Errorf(
			"目录 %s 可用空间不足: avail=%.2fG, 需要 %.2fG (size=%s + 1G 余量)",
			parent, float64(avail)/float64(blockSize1M)/1024.0,
			float64(required)/float64(blockSize1M)/1024.0, c.Params.Size,
		)
	}

	// target 必须不存在: stat 报 NotExist 才放行, 任何其它情况 (含 stat 报错或文件存在) 都拒
	if _, err := os.Stat(c.Params.Target); err == nil {
		return fmt.Errorf(
			"拒绝执行: target 已存在 (%s). actuator 只支持新建测试文件, "+
				"避免误覆盖现有数据。请清理旧文件或换个不存在的路径再试",
			c.Params.Target,
		)
	} else if !os.IsNotExist(err) {
		return fmt.Errorf("stat %s: %w", c.Params.Target, err)
	}

	// O_CREATE|O_EXCL 排他创建: 即使有 race 别人在 stat 后抢先创建, EXCL 也会让 OpenFile 失败
	logger.Info("创建测试文件: %s (size=%s, %d bytes)", c.Params.Target, c.Params.Size, sz)
	f, err := os.OpenFile(c.Params.Target, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0644)
	if err != nil {
		return fmt.Errorf("排他创建 %s 失败 (可能是文件刚被别人抢先创建): %w", c.Params.Target, err)
	}
	c.createdTestFile = true // 创建成功即归我们清, 即便后续 truncate 失败
	defer f.Close()
	if err := f.Truncate(sz); err != nil {
		return fmt.Errorf("truncate %s: %w", c.Params.Target, err)
	}
	return nil
}

// cleanupTarget defer 调用, 仅清 actuator 自己创建的东西
// 清理失败不当致命错误, 仅打 log 让 SRE 排查
func (c *DiskBenchmarkComp) cleanupTarget() {
	if !c.createdTestFile {
		return
	}
	if err := os.Remove(c.Params.Target); err != nil {
		logger.Warn("清理测试文件失败 (非致命): %s: %v", c.Params.Target, err)
		return
	}
	logger.Info("已清理测试文件: %s", c.Params.Target)
}

// runPhases 顺序跑 5 个 phase, 任一失败立即返回
func (c *DiskBenchmarkComp) runPhases() error {
	dur := time.Duration(c.Params.Runtime) * time.Second

	type phaseFn func(context.Context) (*PhaseResult, error)
	phases := []struct {
		name string
		fn   phaseFn
	}{
		{"sequential_write", func(ctx context.Context) (*PhaseResult, error) { return c.phaseSeqWrite(ctx) }},
		{"random_read", func(ctx context.Context) (*PhaseResult, error) { return c.phaseRandRead(ctx) }},
		{"write_latency", func(ctx context.Context) (*PhaseResult, error) { return c.phaseWriteLatency(ctx) }},
		{"mixed_iops", func(ctx context.Context) (*PhaseResult, error) {
			return c.phaseMixed(ctx, "mixed_iops",
				fmt.Sprintf("综合 IOPS (4K 70R/30W, %d 并发, O_DIRECT)", c.Params.Jobs),
				c.Params.Jobs, blockSize4K, 0.7, false)
		}},
		{"mixed_throughput", func(ctx context.Context) (*PhaseResult, error) {
			return c.phaseMixed(ctx, "mixed_throughput",
				fmt.Sprintf("综合吞吐 (1M 50R/50W, %d 并发, O_DIRECT)", c.Params.ThroughputJobs),
				c.Params.ThroughputJobs, blockSize1M, 0.5, true)
		}},
	}

	c.results = make([]*PhaseResult, 0, len(phases))
	for _, p := range phases {
		logger.Info("[RUN ] %s 持续 %ds...", p.name, c.Params.Runtime)
		ctx, cancel := context.WithTimeout(context.Background(), dur)
		res, err := p.fn(ctx)
		cancel()
		if err != nil {
			return fmt.Errorf("phase %s failed: %w", p.name, err)
		}
		c.results = append(c.results, res)
		logger.Info("[OK   ] %s ops=%d iops=%.2f bw=%.2f MB/s lat=%.3f ms",
			res.Name, res.Ops, res.IOPS, res.BWMBps, res.MeanLatMs)
	}
	return nil
}

// outputCtx 把结果按 BaselineDisk 字段输出, 走 components.WrapperOutput
func (c *DiskBenchmarkComp) outputCtx() error {
	resp := DiskBenchmarkResp{
		Phases:      c.results,
		Environment: collectEnvironment(),
	}
	for _, r := range c.results {
		switch r.Name {
		case "sequential_write":
			resp.SequentialWriteThroughputMBps = int64(r.BWMBps + 0.5)
		case "random_read":
			resp.RandomReadIOPS = int64(r.IOPS + 0.5)
		case "write_latency":
			resp.WriteLatencyMs = roundN(r.MeanLatMs, 3)
		case "mixed_iops":
			resp.PerformanceIOPS = int64(r.IOPS + 0.5)
		case "mixed_throughput":
			resp.PerformanceThroughputMBps = int64(r.BWMBps + 0.5)
		}
	}
	return components.PrintOutputCtx(resp)
}

// ===================== 5 个 phase 实现 =====================

func (c *DiskBenchmarkComp) phaseSeqWrite(ctx context.Context) (*PhaseResult, error) {
	f, err := os.OpenFile(c.Params.Target, os.O_WRONLY|syscall.O_DIRECT, 0644)
	if err != nil {
		return nil, fmt.Errorf("open: %w", err)
	}
	defer f.Close()

	bs := blockSize1M
	buf := alignedBuffer(bs)
	r := rand.New(rand.NewSource(time.Now().UnixNano()))
	_, _ = r.Read(buf)

	var ops, bytes int64
	var off int64
	start := time.Now()
	for ctx.Err() == nil {
		n, werr := f.WriteAt(buf, off)
		if werr != nil {
			return nil, fmt.Errorf("write: %w", werr)
		}
		ops++
		bytes += int64(n)
		off += int64(n)
		if off+int64(bs) > c.fileSize {
			off = 0
		}
	}
	elapsed := time.Since(start).Seconds()
	return &PhaseResult{
		Name:     "sequential_write",
		Desc:     "顺序写吞吐 (1M, 单线程, O_DIRECT)",
		Duration: elapsed,
		Ops:      ops,
		Bytes:    bytes,
		IOPS:     float64(ops) / elapsed,
		BWMBps:   float64(bytes) / elapsed / float64(blockSize1M),
	}, nil
}

func (c *DiskBenchmarkComp) phaseRandRead(ctx context.Context) (*PhaseResult, error) {
	bs := blockSize4K
	jobs := c.Params.Jobs
	var totalOps, totalBytes int64
	var wg sync.WaitGroup
	errCh := make(chan error, jobs)
	start := time.Now()

	for i := 0; i < jobs; i++ {
		wg.Add(1)
		go func(id int) {
			defer wg.Done()
			f, err := os.OpenFile(c.Params.Target, os.O_RDONLY|syscall.O_DIRECT, 0644)
			if err != nil {
				errCh <- err
				return
			}
			defer f.Close()
			buf := alignedBuffer(bs)
			r := rand.New(rand.NewSource(time.Now().UnixNano() + int64(id)))
			for ctx.Err() == nil {
				off := randomAlignedOffset(r, c.fileSize, bs)
				n, rerr := f.ReadAt(buf, off)
				if rerr != nil && rerr != io.EOF {
					errCh <- rerr
					return
				}
				atomic.AddInt64(&totalOps, 1)
				atomic.AddInt64(&totalBytes, int64(n))
			}
		}(i)
	}
	wg.Wait()
	close(errCh)
	for e := range errCh {
		if e != nil {
			return nil, e
		}
	}
	elapsed := time.Since(start).Seconds()
	return &PhaseResult{
		Name:     "random_read",
		Desc:     fmt.Sprintf("随机读 IOPS (4K, %d 并发, O_DIRECT)", jobs),
		Duration: elapsed,
		Ops:      totalOps,
		Bytes:    totalBytes,
		IOPS:     float64(totalOps) / elapsed,
		BWMBps:   float64(totalBytes) / elapsed / float64(blockSize1M),
	}, nil
}

func (c *DiskBenchmarkComp) phaseWriteLatency(ctx context.Context) (*PhaseResult, error) {
	f, err := os.OpenFile(c.Params.Target, os.O_WRONLY|syscall.O_DIRECT|syscall.O_SYNC, 0644)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	bs := blockSize4K
	buf := alignedBuffer(bs)
	r := rand.New(rand.NewSource(time.Now().UnixNano()))
	_, _ = r.Read(buf)

	var ops, bytes, latNs int64
	start := time.Now()
	for ctx.Err() == nil {
		off := randomAlignedOffset(r, c.fileSize, bs)
		t0 := time.Now()
		n, werr := f.WriteAt(buf, off)
		if werr != nil {
			return nil, werr
		}
		latNs += time.Since(t0).Nanoseconds()
		ops++
		bytes += int64(n)
	}
	elapsed := time.Since(start).Seconds()
	mean := 0.0
	if ops > 0 {
		mean = float64(latNs) / float64(ops) / 1e6 // ns -> ms
	}
	return &PhaseResult{
		Name:      "write_latency",
		Desc:      "写延迟 (4K 单线程, O_DIRECT|O_SYNC)",
		Duration:  elapsed,
		Ops:       ops,
		Bytes:     bytes,
		IOPS:      float64(ops) / elapsed,
		BWMBps:    float64(bytes) / elapsed / float64(blockSize1M),
		MeanLatMs: mean,
	}, nil
}

func (c *DiskBenchmarkComp) phaseMixed(
	ctx context.Context, name, desc string,
	jobs, blockSz int, readRatio float64, sequential bool,
) (*PhaseResult, error) {
	var ops, bytes int64
	var wg sync.WaitGroup
	errCh := make(chan error, jobs)
	start := time.Now()

	// sequential 模式: 把整个文件按 worker 数等分, 每个 worker 在自己的 chunk 内顺序循环
	// 避免之前 "seqOff = id * blockSz 然后 += blockSz" 的 bug —— 那种写法下 worker 0
	// 跑到第 N 轮时正好和 worker 1 的第 N-1 轮在同一 offset 上互相覆盖, 性能数字会因
	// IO 调度抢锁而失真
	chunkBlocks := int64(0)
	if sequential {
		chunkBlocks = c.fileSize / int64(jobs) / int64(blockSz)
		if chunkBlocks <= 0 {
			// 文件太小不够等分, 退化到所有 worker 共享整个文件 (测量退化, 不崩)
			chunkBlocks = c.fileSize / int64(blockSz)
			if chunkBlocks <= 0 {
				chunkBlocks = 1
			}
		}
	}

	for i := 0; i < jobs; i++ {
		wg.Add(1)
		go func(id int) {
			defer wg.Done()
			f, err := os.OpenFile(c.Params.Target, os.O_RDWR|syscall.O_DIRECT, 0644)
			if err != nil {
				errCh <- err
				return
			}
			defer f.Close()
			buf := alignedBuffer(blockSz)
			r := rand.New(rand.NewSource(time.Now().UnixNano() + int64(id)))
			_, _ = r.Read(buf)

			// 每个 worker 自己 chunk 的 [start, end), 仅 sequential 模式用
			chunkStart := chunkBlocks * int64(blockSz) * int64(id)
			chunkEnd := chunkStart + chunkBlocks*int64(blockSz)
			if chunkEnd > c.fileSize {
				chunkEnd = c.fileSize
			}
			seqOff := chunkStart

			for ctx.Err() == nil {
				var off int64
				if sequential {
					off = seqOff
					seqOff += int64(blockSz)
					if seqOff+int64(blockSz) > chunkEnd {
						seqOff = chunkStart // 回到自己 chunk 起点循环
					}
				} else {
					off = randomAlignedOffset(r, c.fileSize, blockSz)
				}
				var n int
				var ioErr error
				if r.Float64() < readRatio {
					n, ioErr = f.ReadAt(buf, off)
					if ioErr == io.EOF {
						ioErr = nil
					}
				} else {
					n, ioErr = f.WriteAt(buf, off)
				}
				if ioErr != nil {
					errCh <- ioErr
					return
				}
				atomic.AddInt64(&ops, 1)
				atomic.AddInt64(&bytes, int64(n))
			}
		}(i)
	}
	wg.Wait()
	close(errCh)
	for e := range errCh {
		if e != nil {
			return nil, e
		}
	}
	elapsed := time.Since(start).Seconds()
	return &PhaseResult{
		Name:     name,
		Desc:     desc,
		Duration: elapsed,
		Ops:      ops,
		Bytes:    bytes,
		IOPS:     float64(ops) / elapsed,
		BWMBps:   float64(bytes) / elapsed / float64(blockSize1M),
	}, nil
}

// ===================== 辅助 =====================

// alignedBuffer 4K 对齐 buffer (O_DIRECT 必需)
func alignedBuffer(size int) []byte {
	buf := make([]byte, size+alignSize)
	ptr := uintptr(unsafe.Pointer(&buf[0]))
	offset := int((uintptr(alignSize) - ptr%uintptr(alignSize)) % uintptr(alignSize))
	return buf[offset : offset+size]
}

// parseSize 解析 4G/512M/1024K/12345
func parseSize(s string) (int64, error) {
	s = strings.TrimSpace(strings.ToUpper(s))
	if s == "" {
		return 0, fmt.Errorf("empty size")
	}
	mul := int64(1)
	switch s[len(s)-1] {
	case 'K':
		mul = 1024
		s = s[:len(s)-1]
	case 'M':
		mul = 1024 * 1024
		s = s[:len(s)-1]
	case 'G':
		mul = 1024 * 1024 * 1024
		s = s[:len(s)-1]
	case 'T':
		mul = 1024 * 1024 * 1024 * 1024
		s = s[:len(s)-1]
	}
	v, err := strconv.ParseInt(strings.TrimSpace(s), 10, 64)
	if err != nil {
		return 0, err
	}
	if v <= 0 {
		return 0, fmt.Errorf("size 必须 > 0")
	}
	return v * mul, nil
}

func randomAlignedOffset(r *rand.Rand, fileSz int64, blockSz int) int64 {
	maxBlocks := fileSz / int64(blockSz)
	if maxBlocks <= 0 {
		return 0
	}
	return r.Int63n(maxBlocks) * int64(blockSz)
}

func roundN(v float64, digits int) float64 {
	mul := 1.0
	for i := 0; i < digits; i++ {
		mul *= 10
	}
	return float64(int64(v*mul+0.5)) / mul
}

// collectEnvironment 仅采集 cpu_model + go_version + num_cpu 这种安全只读信息
// 不再读 /sys/block/* 因为 target 是文件, 没有直接对应的设备节点
func collectEnvironment() map[string]interface{} {
	env := map[string]interface{}{
		"go_version": runtime.Version(),
		"num_cpu":    runtime.NumCPU(),
	}
	if data, err := os.ReadFile("/proc/cpuinfo"); err == nil {
		for _, line := range strings.Split(string(data), "\n") {
			if strings.HasPrefix(line, "model name") {
				if parts := strings.SplitN(line, ":", 2); len(parts) == 2 {
					env["cpu_model"] = strings.TrimSpace(parts[1])
				}
				break
			}
		}
	}
	return env
}
