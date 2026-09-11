package atomoracle

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"sort"
	"strings"

	"dbm-services/oracle/db-tools/dbactuator/pkg/consts"
	"dbm-services/oracle/db-tools/dbactuator/pkg/util/osutil"
)

// DirPlan 目录/软链接操作分组结构化清单（作为中间数据，用于生成 shell 脚本）
type DirPlan struct {
	// Symlinks 需要处理的软链接（含目标目录、软链接下的用户子目录）
	Symlinks []SymlinkPlan `json:"symlinks"`
	// PlainDirs 需要直接 mkdir 的普通目录（已 EvalSymlinks 转为真实路径，去重后）
	PlainDirs []string `json:"plain_dirs"`
	// ChownTopDirs 需要 chown -R 的顶层目录（去重后，保持首次出现顺序）
	ChownTopDirs []string `json:"chown_top_dirs"`
	// User chown 使用的属主
	User string `json:"user"`
	// Group chown 使用的属组
	Group string `json:"group"`
}

// SymlinkPlan 单条软链接的操作计划
type SymlinkPlan struct {
	// Link 软链接节点绝对路径
	Link string `json:"link"`
	// RealPath 软链接目标绝对路径
	RealPath string `json:"real_path"`
	// SubDirs 软链接下的用户子目录（真实路径形式，如 /data2/rman/backup）
	SubDirs []string `json:"sub_dirs,omitempty"`
	// SkipLn 幂等标记：true 表示 Link 已存在且指向一致，无需 ln -s
	SkipLn bool `json:"skip_ln"`
}

// allowedTopDirRegexp 允许作为顶层目录的白名单正则
// 匹配根下第一级目录（如 /data、/data1、/oradata、/u01、/u、/rman、/arch、/backup、/log、/dump）
var allowedTopDirRegexp = regexp.MustCompile(`^/(data\d*|oradata\d*|u\d*|rman|arch|backup|log|dump)$`)

// PrepareDirs 主入口
// 1. 根据 Params.LinkPlans / Params.PlainDirs 构建分组清单 DirPlan
// 2. 由 DirPlan 生成 shell 脚本，写到临时文件
// 3. 执行 shell 脚本
// 脚本文件在执行完成/失败后均保留，路径记入 e.DirScriptPath 便于排查
func (e *InstallOracle) PrepareDirs() error {
	plan, err := e.buildDirPlan()
	if err != nil {
		return err
	}
	e.DirPlan = plan

	script := renderDirScript(plan)
	scriptPath, err := writeScriptToTempFile(script)
	if err != nil {
		return fmt.Errorf("write prepare-dirs script fail: %s", err)
	}
	e.DirScriptPath = scriptPath
	e.Runtime.Logger.Info("prepare-dirs script written to: %s", scriptPath)

	if err := runShellScript(scriptPath); err != nil {
		e.Runtime.Logger.Error("execute prepare-dirs script fail, script kept at %s, error:%s",
			scriptPath, err)
		return fmt.Errorf("execute prepare-dirs script fail: %s", err)
	}
	e.Runtime.Logger.Info("prepare-dirs script executed successfully")
	return nil
}

// buildDirPlan 汇总生成分组清单
func (e *InstallOracle) buildDirPlan() (*DirPlan, error) {
	plan := &DirPlan{
		Symlinks:     make([]SymlinkPlan, 0),
		PlainDirs:    make([]string, 0),
		ChownTopDirs: make([]string, 0),
		User:         consts.OracleAccount,
		Group:        consts.OracleGroup,
	}
	if err := e.fillSymlinkPlans(plan); err != nil {
		return nil, err
	}
	if err := e.fillPlainDirs(plan); err != nil {
		return nil, err
	}
	return plan, nil
}

// fillSymlinkPlans 处理 LinkPlans，产出 SymlinkPlan 列表
// 规则：
//  1. 稳定顺序：userPath 字典序遍历；每个 userPath 内的 links 按 Link 深度从浅到深
//  2. 跨 userPath 的 Link 去重；同一 Link 若指向不同 RealPath 直接报错
//  3. 幂等：Link 已是指向一致的软链接则 SkipLn=true；指向不一致或非软链接直接报错
//  4. userPath 深于 Link 时补建真实子目录（挂到该 Link 的 SubDirs）
//  5. 顶层目录白名单校验（Link/RealPath/SubDirs）
func (e *InstallOracle) fillSymlinkPlans(plan *DirPlan) error {
	userPaths := make([]string, 0, len(e.Params.LinkPlans))
	for k := range e.Params.LinkPlans {
		userPaths = append(userPaths, k)
	}
	sort.Strings(userPaths)

	// Link -> 在 plan.Symlinks 中的下标（用于跨 userPath 去重 + 追加 SubDirs）
	linkIdx := make(map[string]int)

	for _, userPath := range userPaths {
		links := e.Params.LinkPlans[userPath]
		if len(links) == 0 {
			continue
		}
		sortedLinks := make([]SymbolicLinkInfo, len(links))
		copy(sortedLinks, links)
		sort.SliceStable(sortedLinks, func(i, j int) bool {
			return strings.Count(sortedLinks[i].Link, "/") < strings.Count(sortedLinks[j].Link, "/")
		})

		for _, info := range sortedLinks {
			if info.Link == "" || info.RealPath == "" {
				return fmt.Errorf("invalid link plan under userPath=%s, link=%q, real_path=%q",
					userPath, info.Link, info.RealPath)
			}
			if idx, ok := linkIdx[info.Link]; ok {
				if plan.Symlinks[idx].RealPath != info.RealPath {
					return fmt.Errorf("conflict link plan: %s -> %s vs %s",
						info.Link, plan.Symlinks[idx].RealPath, info.RealPath)
				}
				continue
			}
			if err := checkTopDirAllowed(info.Link); err != nil {
				return err
			}
			if err := checkTopDirAllowed(info.RealPath); err != nil {
				return err
			}
			needSymlink, err := checkSymlinkState(info.Link, info.RealPath)
			if err != nil {
				return err
			}
			plan.Symlinks = append(plan.Symlinks, SymlinkPlan{
				Link:     info.Link,
				RealPath: info.RealPath,
				SkipLn:   !needSymlink,
			})
			linkIdx[info.Link] = len(plan.Symlinks) - 1
		}

		// userPath 深于最深一层 Link 时，补建真实子目录
		deepest := sortedLinks[len(sortedLinks)-1]
		cleanUser := filepath.Clean(userPath)
		cleanLink := filepath.Clean(deepest.Link)
		if cleanUser == cleanLink {
			continue
		}
		rel, err := filepath.Rel(cleanLink, cleanUser)
		if err != nil || strings.HasPrefix(rel, "..") {
			return fmt.Errorf("userPath %s is not under link %s", userPath, deepest.Link)
		}
		realSub := filepath.Join(deepest.RealPath, rel)
		if err := checkTopDirAllowed(realSub); err != nil {
			return err
		}
		idx := linkIdx[deepest.Link]
		// SubDirs 内部再做一次去重
		if !containsString(plan.Symlinks[idx].SubDirs, realSub) {
			plan.Symlinks[idx].SubDirs = append(plan.Symlinks[idx].SubDirs, realSub)
		}
	}
	return nil
}

// fillPlainDirs 处理 PlainDirs：EvalSymlinks -> 顶层校验 -> 收集去重 -> 顶层 chown
func (e *InstallOracle) fillPlainDirs(plan *DirPlan) error {
	seenDir := make(map[string]struct{})
	seenTop := make(map[string]struct{})

	for _, p := range e.Params.PlainDirs {
		if p == "" {
			continue
		}
		abs, err := filepath.Abs(p)
		if err != nil {
			return fmt.Errorf("resolve absolute path fail, path:%s, error:%s", p, err)
		}
		realPath := abs
		if resolved, err := filepath.EvalSymlinks(abs); err == nil {
			realPath = resolved
		} else if !os.IsNotExist(err) {
			return fmt.Errorf("eval symlinks fail, path:%s, error:%s", abs, err)
		}
		top, err := firstLevelDir(realPath)
		if err != nil {
			return err
		}
		if err := checkTopDirAllowed(top); err != nil {
			return err
		}
		if _, ok := seenDir[realPath]; !ok {
			seenDir[realPath] = struct{}{}
			plan.PlainDirs = append(plan.PlainDirs, realPath)
		}
		if _, ok := seenTop[top]; !ok {
			seenTop[top] = struct{}{}
			if top != "/u" && !osutil.IsDataDirOk(top) {
				return fmt.Errorf("top directory %s does not meet data dir requirement "+
					"(must be a mount point with >150GB available), from path %s", top, p)
			}

			plan.ChownTopDirs = append(plan.ChownTopDirs, top)
		}
	}
	return nil
}

// renderDirScript 根据 DirPlan 生成一份 shell 脚本内容
// 结构：
//
//	#!/bin/bash
//	set -euo pipefail
//	# ===== Symbolic Links =====
//	mkdir -p <RealPath>；chown -R <user>:<group> <RealPath>
//	ln -s <RealPath> <Link>（SkipLn=true 则跳过）
//	chown -h <user>:<group> <Link>
//	mkdir/chown SubDirs
//	# ===== Plain Dirs =====
//	mkdir -p <plainDir>
//	# ===== Chown top dirs =====
//	chown -R <user>:<group> <topDir>
func renderDirScript(plan *DirPlan) string {
	var b strings.Builder
	b.WriteString("#!/bin/bash\n")
	b.WriteString("set -euo pipefail\n")
	b.WriteString("# Auto-generated by install_oracle atom job. DO NOT edit manually.\n\n")

	if len(plan.Symlinks) > 0 {
		b.WriteString("# ===== Symbolic Links =====\n")
		for _, sp := range plan.Symlinks {
			b.WriteString(fmt.Sprintf("# link: %s -> %s\n", sp.Link, sp.RealPath))
			b.WriteString(fmt.Sprintf("mkdir -p -m %s %s\n", consts.DirModeStr, shellQuote(sp.RealPath)))
			b.WriteString(fmt.Sprintf("chown -R %s:%s %s\n",
				plan.User, plan.Group, shellQuote(sp.RealPath)))
			if sp.SkipLn {
				b.WriteString(fmt.Sprintf("# symlink %s already points to %s, skip ln -s\n",
					sp.Link, sp.RealPath))
			} else {
				b.WriteString(fmt.Sprintf("ln -s %s %s\n",
					shellQuote(sp.RealPath), shellQuote(sp.Link)))
			}
			b.WriteString(fmt.Sprintf("chown -h %s:%s %s\n",
				plan.User, plan.Group, shellQuote(sp.Link)))
			for _, sub := range sp.SubDirs {
				b.WriteString(fmt.Sprintf("mkdir -p -m %s %s\n", consts.DirModeStr, shellQuote(sub)))
				b.WriteString(fmt.Sprintf("chown -R %s:%s %s\n",
					plan.User, plan.Group, shellQuote(sub)))
			}
			b.WriteString("\n")
		}
	}

	if len(plan.PlainDirs) > 0 {
		b.WriteString("# ===== Plain Dirs =====\n")
		for _, d := range plan.PlainDirs {
			b.WriteString(fmt.Sprintf("mkdir -p -m %s %s\n", consts.DirModeStr, shellQuote(d)))
		}
		b.WriteString("\n")
	}

	if len(plan.ChownTopDirs) > 0 {
		b.WriteString("# ===== Chown top dirs =====\n")
		for _, top := range plan.ChownTopDirs {
			b.WriteString(fmt.Sprintf("chown -R %s:%s %s\n",
				plan.User, plan.Group, shellQuote(top)))
		}
	}
	return b.String()
}

// writeScriptToTempFile 把脚本写到临时文件，返回文件绝对路径。文件权限 0700。
func writeScriptToTempFile(content string) (string, error) {
	f, err := os.CreateTemp("", "install_oracle_prepare_dirs_*.sh")
	if err != nil {
		return "", err
	}
	path := f.Name()
	if _, err := f.WriteString(content); err != nil {
		_ = f.Close()
		return path, err
	}
	if err := f.Close(); err != nil {
		return path, err
	}
	if err := os.Chmod(path, 0700); err != nil {
		return path, err
	}
	return path, nil
}

// runShellScript 用 /bin/bash 执行脚本，stdout/stderr 合并输出到日志（通过 stderr）
// 执行失败保留脚本文件
func runShellScript(scriptPath string) error {
	cmd := exec.Command("/bin/bash", scriptPath)
	out, err := cmd.CombinedOutput()
	if len(out) > 0 {
		// 打印到进程 stderr 便于外层日志采集
		fmt.Fprintf(os.Stderr, "[prepare-dirs script output]\n%s\n", string(out))
	}
	if err != nil {
		return fmt.Errorf("bash %s exit with error: %s, output: %s",
			scriptPath, err, string(out))
	}
	return nil
}

// checkSymlinkState 检查 Link 当前状态，决定是否需要 ln -s
// 返回值：needSymlink（true=需要 ln -s；false=已存在且指向一致，幂等跳过）
// 错误：Link 存在但不是软链接；Link 是软链接但指向的目标与期望不一致
func checkSymlinkState(link, expected string) (needSymlink bool, err error) {
	info, statErr := os.Lstat(link)
	if statErr != nil {
		if os.IsNotExist(statErr) {
			return true, nil
		}
		return false, fmt.Errorf("lstat fail, link:%s, error:%s", link, statErr)
	}
	if info.Mode()&os.ModeSymlink == 0 {
		return false, fmt.Errorf("path %s exists but is not a symlink", link)
	}
	cur, readErr := os.Readlink(link)
	if readErr != nil {
		return false, fmt.Errorf("readlink fail, link:%s, error:%s", link, readErr)
	}
	curAbs := cur
	if !filepath.IsAbs(cur) {
		curAbs = filepath.Clean(filepath.Join(filepath.Dir(link), cur))
	}
	if curAbs != filepath.Clean(expected) {
		return false, fmt.Errorf("symlink %s points to %s, expected %s", link, curAbs, expected)
	}
	return false, nil
}

// checkTopDirAllowed 用允许白名单正则校验路径的顶层目录
func checkTopDirAllowed(path string) error {
	top, err := firstLevelDir(path)
	if err != nil {
		return err
	}
	if !allowedTopDirRegexp.MatchString(top) {
		return fmt.Errorf("top directory %s is not allowed (from path %s)", top, path)
	}
	return nil
}

// firstLevelDir 提取路径的根下第一级目录（例：/data1/oradata/xxx -> /data1）
func firstLevelDir(path string) (string, error) {
	if path == "" {
		return "", fmt.Errorf("empty path")
	}
	clean := filepath.Clean(path)
	if !filepath.IsAbs(clean) {
		return "", fmt.Errorf("path %s is not absolute", path)
	}
	if clean == "/" {
		return "", fmt.Errorf("path %s is root, not allowed", path)
	}
	rest := clean[1:]
	idx := strings.IndexByte(rest, '/')
	if idx < 0 {
		return clean, nil
	}
	return "/" + rest[:idx], nil
}

// shellQuote 对路径做 shell 单引号转义，防注入/空格问题
func shellQuote(s string) string {
	// 用单引号包裹，内部的 ' 用 '\'' 逃逸
	return "'" + strings.ReplaceAll(s, "'", `'\''`) + "'"
}

// containsString 简易的 []string 包含判断
func containsString(list []string, target string) bool {
	for _, s := range list {
		if s == target {
			return true
		}
	}
	return false
}
