package checker

import (
	"bufio"
	"errors"
	"fmt"
	"log/slog"
	"os"
	"os/exec"
	"strings"
)

// pt-table-checksum 退出码相关常量。
//
// 背景: pt-table-checksum 的 exit code 语义非常混乱, 不能只看官方文档。
//
//  1. 正常路径: main() return $exit_status, 脚本末尾 exit main(@ARGV)
//     此时 exit code 是一个位掩码(bitmask), 由下面几个 flag 按位 OR 组成:
//     ERROR=1, ALREADY_RUNNING=2, CAUGHT_SIGNAL=4, NO_SLAVES_FOUND=8,
//     TABLE_DIFF=16, SKIP_CHUNK=32, SKIP_TABLE=64
//     多个 flag 可以同时存在, 例如 exit 17 = 16+1 表示既有 diff 又有表级 error。
//
//  2. 异常路径: 源码里大量 die, 或 OptionParser 参数错误时 exit 1
//     die 未捕获 → 进程直接 exit 255, 不是 bitmask
//     如果对 255 做 collectFlags, 会把 1/2/4/8/16/32/64 全部误命中
//
//  3. stderr 大量是 warn, 不是 fatal
//     skip chunk、找不到 slave、表级 eval 捕获异常等都会 warn 到 stderr,
//     但进程仍可能正常跑完并输出 summary。因此「有 stderr 就 fail」会误杀。
const (
	// ptExitFatal: Perl die / 未捕获异常的标准退出码, 表示进程级失败。
	ptExitFatal = 255

	// ptExitAlreadyRunning: pid 文件冲突, 本次 checksum 根本没跑起来。
	ptExitAlreadyRunning = 2

	// ptExitCaughtSignal: 收到 SIGINT/SIGTERM 等, 结果被中断。
	ptExitCaughtSignal = 4

	// ptExitKnownFlagsMask: main() 正常返回时, 所有合法 flag 的按位或 = 1+2+4+8+16+32+64。
	// 若 exit code 超出这个掩码(且不是 0/255), 很可能是 die/系统 errno 污染, 不能当 bitmask 解读。
	ptExitKnownFlagsMask = 127
)

// ptStderrIgnoredSubstrings: stderr 里已知无害、不应参与 fatal 判定的文本。
//
// 例如 oversized 表被表级 eval 捕获后, pt 会 warn 并置 ERROR(1) flag,
// 工具仍会继续跑其他表。这类信息留给 summaries / replicate 表判断, 不当进程 fatal。
var ptStderrIgnoredSubstrings = []string{
	"There is no good index and the table is oversized",
}

// HandlePtChecksumResult 专门处理 pt-table-checksum 命令执行后的原始输出。
//
// 设计目的: 替代 run_command.go 354 行之后那套不完整/有 bug 的判断逻辑。
// 调用方在 command.Run() 之后, 把 stdout、stderr、err 原样传入即可。
//
// 参数:
//   - stdout: pt-table-checksum 标准输出, 含 TS 开头的 summary 表格
//   - stderr: pt-table-checksum 标准错误, 大量 warn 和部分 die 信息
//   - cmdErr:  command.Run() 的返回值
//     · exit 0 时为 nil
//     · exit 非 0 时为 *exec.ExitError (这在 Go 里是「正常收到退出码」, 不是 panic)
//     · perl 找不到、被 kill 等则为其他 error
//
// 三个返回值的分工(与 run() 保持一致, 方便 runGeneral/runDemand 直接对接):
//
//  1. output (*Output)
//     只要 stdout 能解析出 summary, 就会填充并返回(即使后面判定为 fatal 也会带上),
//     方便日志和排障。字段含义:
//     · Summaries: 每张表的 checksum 统计(errors/diffs/skipped 等)
//     · PtExitFlags: pt 报告的退出状态位, 供 demand 模式上报
//     · PtStderr: 原始 stderr 全文
//
//  2. err (error) — Go 侧/解析侧错误, 不是 pt 的业务结论
//     · cmdErr 不是 *exec.ExitError (例如 perl 不存在)
//     · stdout summary 解析失败
//     出现时应直接 return, 不算 checksum 跑完。
//
//  3. pterr (error) — pt 进程级 fatal, 本次 checksum 不可信
//     · exit 255 (die/崩溃)
//     · exit & 2 (ALREADY_RUNNING, pid 冲突)
//     · exit & 4 (CAUGHT_SIGNAL, 被信号打断)
//     · exit code 超出已知 bitmask 且 stderr 有有效内容 (疑似 die 污染)
//     出现时 runGeneral/runDemand 应直接失败, 不要只看 summaries 是否非空。
//
// 哪些 flag 故意 NOT 当 fatal (只写入 output.PtExitFlags, pterr=nil):
//
//	| Flag            | 值  | 处理方式 | 原因 |
//	|-----------------|-----|----------|------|
//	| ERROR           | 1   | 非 fatal | 某张表 checksum 过程出错, pt 会 warn 后继续跑下一张表 |
//	| NO_SLAVES_FOUND | 8   | 非 fatal | 找不到 slave 时 warn; general 模式 recursion-method=none 通常不会出现 |
//	| TABLE_DIFF      | 16  | 非 fatal | demand 模式的核心产出, 表示发现主从不一致 |
//	| SKIP_CHUNK      | 32  | 非 fatal | chunk 被 skip(超时/lock wait 等), general 靠 --resume 续跑 |
//	| SKIP_TABLE      | 64  | 非 fatal | 整表被 skip, summaries[].skipped 和 replicate 表可反映 |
//
// 上层真正该看的 ground truth (比 exit flag 更可靠):
//
//	· general: summaries 是否非空 (EmptySummaryError 重试逻辑)
//	· demand:  replicate 表 this_crc/master_crc 对比 + summaries[].skipped
//
// 接入示例 (替换 run() 354 行之后的逻辑):
//
//	err = command.Run()
//	return HandlePtChecksumResult(stdout.String(), stderr.String(), err)
func HandlePtChecksumResult(stdout, stderr string, cmdErr error) (output *Output, err error, pterr error) {
	// cmdErr 分两类:
	//   · *exec.ExitError → pt 进程正常退出(包括 exit 非 0), 继续往下解析
	//   · 其他 error      → Go 执行层面的意外失败, 直接返回
	var exitErr *exec.ExitError
	if cmdErr != nil {
		if !errors.As(cmdErr, &exitErr) {
			slog.Error("run pt-table-checksum got unexpected error", slog.String("error", cmdErr.Error()))
			return nil, cmdErr, nil
		}
	}

	exitCode := 0
	if exitErr != nil {
		exitCode = exitErr.ExitCode()
		slog.Info("run pt-table-checksum finished", slog.Int("exit_code", exitCode), slog.String("pt err", exitErr.String()))
	} else {
		slog.Info("run pt-table-checksum finished without exit error")
	}

	// 先解析 stdout summary。即使 exit 255, 崩溃前也可能已经打印了部分 summary。
	summaries, err := summary(stdout)
	if err != nil {
		slog.Error(
			"trans pt-table-checksum stdout to summary",
			slog.String("error", err.Error()),
			slog.String("pt stdout", stdout),
		)
		return nil, err, nil
	}
	slog.Info("checksum summary", slog.String("summary", stdout))

	stderrLines := filterPtStderrLines(stderr)
	ptFlags := collectPtExitFlags(exitCode, exitErr)

	output = &Output{
		PtStderr:    stderr,
		Summaries:   summaries,
		PtExitFlags: ptFlags,
	}

	// 判定是否为进程级 fatal。注意: 不在这里因为「有 stderr」就 fail。
	if fatal, reason := isPtFatalExit(exitCode, stderrLines); fatal {
		pterr = newPtChecksumError(output, reason, stderrLines)
		slog.Error(
			"run pt-table-checksum fatal exit",
			slog.String("reason", reason),
			slog.Int("exit_code", exitCode),
			slog.String("stderr", strings.Join(stderrLines, "\n")),
		)
		// 与旧 run() 行为一致: fatal 时把 output JSON 打到 os.Stderr 便于排障
		_, _ = fmt.Fprintf(os.Stderr, output.String())
		return output, nil, pterr
	}

	// 非 fatal: exit 可能是 0, 也可能是 1/8/16/32/64 或其组合。
	// 例如 exit 16 表示发现 diff, exit 32 表示有 chunk 被 skip, 这些都是预期内的业务状态。
	return output, nil, nil
}

// collectPtExitFlags 把 exit code 翻译成 output.PtExitFlags。
//
// 特殊处理 exit 255: 不能用 collectFlags, 否则 255 & 127 != 0 会把所有 flag 都打勾。
// 对 255 只标记一个 FATAL; 对 0 返回 nil; 其余走 collectFlags 按 bitmask 解析。
func collectPtExitFlags(exitCode int, exitErr *exec.ExitError) []PtExitFlag {
	if exitCode == ptExitFatal {
		return []PtExitFlag{{
			Flag:     "FATAL",
			Meaning:  "The tool died or crashed",
			BitValue: ptExitFatal,
		}}
	}
	if exitErr == nil || exitCode == 0 {
		return nil
	}
	return collectFlags(exitErr)
}

// isPtFatalExit 判断本次 pt 执行是否应在 Go 层直接失败 (返回 pterr)。
//
// 判定顺序:
//  1. exit 255        → die/崩溃, 必须 fail
//  2. exit & 2        → pid 冲突, 必须 fail (不依赖 stderr, 修复旧逻辑 stderr 为空时漏报的问题)
//  3. exit & 4        → 被信号打断, 必须 fail
//  4. exit 超出 127 且 stderr 有内容 → 不是 main() 的合法 bitmask, 疑似 die/errno, fail
//
// 不在此 fail 的情况 (举例):
//
//	· exit 1 (ERROR): 某表出错但工具跑完了
//	· exit 16 (TABLE_DIFF): demand 模式正常发现不一致
//	· exit 32 (SKIP_CHUNK): 有 chunk 被 skip, general 模式靠 resume 续跑
func isPtFatalExit(exitCode int, stderrLines []string) (fatal bool, reason string) {
	if exitCode == ptExitFatal {
		return true, "pt-table-checksum exited with 255 (fatal die/crash)"
	}
	if exitCode&ptExitAlreadyRunning != 0 {
		return true, "pt-table-checksum already running (ALREADY_RUNNING)"
	}
	if exitCode&ptExitCaughtSignal != 0 {
		return true, "pt-table-checksum caught signal (CAUGHT_SIGNAL)"
	}
	// exitCode & ^127 != 0 表示出现了 128 及以上未知高位, 不是 pt 文档定义的 flag
	if exitCode != 0 && exitCode&^ptExitKnownFlagsMask != 0 && len(stderrLines) > 0 {
		return true, fmt.Sprintf("pt-table-checksum exit code %d outside known flag mask", exitCode)
	}
	return false, ""
}

// filterPtStderrLines 从 stderr 提取有效行, 过滤空行和已知无害 warn。
//
// 注意: 此函数的输出仅用于 fatal 判定的辅助条件(第 4 条: 未知 exit code),
// 不会因为 stderr 非空就把整次执行判为 fatal。
func filterPtStderrLines(stderr string) []string {
	if stderr == "" {
		return nil
	}

	lines := make([]string, 0)
	scanner := bufio.NewScanner(strings.NewReader(stderr))
	scanner.Split(bufio.ScanLines)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" || isIgnoredPtStderrLine(line) {
			continue
		}
		lines = append(lines, line)
	}
	return lines
}

// isIgnoredPtStderrLine 判断 stderr 某行是否属于已知无害 warn, 不参与 fatal 辅助判定。
func isIgnoredPtStderrLine(line string) bool {
	for _, ignored := range ptStderrIgnoredSubstrings {
		if strings.Contains(line, ignored) {
			return true
		}
	}
	return false
}

// newPtChecksumError 构造 pterr, 把 fatal 原因、output JSON、stderr 有效行拼在一起方便排障。
func newPtChecksumError(output *Output, reason string, stderrLines []string) error {
	if len(stderrLines) > 0 {
		return fmt.Errorf("%s: %s; detail: %s", reason, output.String(), strings.Join(stderrLines, "\n"))
	}
	return fmt.Errorf("%s: %s", reason, output.String())
}
