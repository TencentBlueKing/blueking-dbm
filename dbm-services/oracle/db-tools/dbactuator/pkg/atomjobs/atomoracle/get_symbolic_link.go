package atomoracle

import (
	"dbm-services/oracle/db-tools/dbactuator/pkg/atomjobs"
	"dbm-services/oracle/db-tools/dbactuator/pkg/consts"
	"dbm-services/oracle/db-tools/dbactuator/pkg/jobruntime"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"slices"

	"github.com/go-playground/validator/v10"
)

// GetSymbolicLinkParams 执行脚本初始化参数
type GetSymbolicLinkParams struct {
	Pathes []string `json:"pathes" validate:"required"`
}

// GetSymbolicLink 执行脚本原子任务   oracle用户执行
type GetSymbolicLink struct {
	BaseJob
	Params                    *GetSymbolicLinkParams
	GetSymbolicLinkRunTimeCtx `json:"-"`
}

// SymbolicLinkInfo 单个软链接节点的解析信息
type SymbolicLinkInfo struct {
	// Link 软链接节点本身（绝对路径）
	Link string `json:"link"`
	// RealPath EvalSymlinks 结果，递归解析后最终的真实绝对路径
	RealPath string `json:"real_path"`
}

// GetSymbolicLinkRunTimeCtx 运行时上下文
type GetSymbolicLinkRunTimeCtx struct {
	TmpPathes []string `json:"tmp_pathes"`
	// LinkPlans 软链接配置：key 为输入路径，value 为该路径逐级向上检测到的软链接节点列表
	// 每个节点包含软链接自身路径（Link）和真实目标路径（RealPath）
	LinkPlans map[string][]SymbolicLinkInfo `json:"link_plans"`
	// PlainDirs 普通目录列表：路径逐级向上均不含软链接（或仅命中白名单），可直接 mkdir 处理
	PlainDirs []string `json:"plain_dirs"`
}

// NewGetSymbolicLink new
func NewGetSymbolicLink() jobruntime.JobRunner {
	return &GetSymbolicLink{}
}

// Init 初始化
func (e *GetSymbolicLink) Init(runtime *jobruntime.JobGenericRuntime) error {
	e.Runtime = runtime
	err := json.Unmarshal([]byte(e.Runtime.PayloadDecoded), &e.Params)
	if err != nil {
		e.Runtime.Logger.Error(
			"get parameters of GetConfig fail by json.Unmarshal, error:%s", err)
		return fmt.Errorf("get parameters of GetConfig fail by json.Unmarshal, error:%s", err)
	}
	if err = e.checkParams(); err != nil {
		return err
	}
	e.Runtime.Logger.Info("init successfully")
	return nil
}

// checkParams 校验参数
func (e *GetSymbolicLink) checkParams() error {
	// 校验配置参数
	e.Runtime.Logger.Info("start to validate parameters")
	validate := validator.New()
	e.Runtime.Logger.Info("start to validate parameters of GetSymbolicLink")
	if err := validate.Struct(e.Params); err != nil {
		e.Runtime.Logger.Error("validate parameters of GetSymbolicLink fail, error:%s", err)
		return fmt.Errorf("validate parameters of GetSymbolicLink fail, error:%s", err)
	}
	e.Runtime.Logger.Info("validate parameters successfully")
	return nil
}

// Name 名字
func (e *GetSymbolicLink) Name() string {
	return "get-symbolic-link"
}

// Run 执行函数
func (e *GetSymbolicLink) Run() error {
	if err := e.ContainSymbolicLink(); err != nil {
		return err
	}
	if err := e.ResolveSymbolicLinks(); err != nil {
		return err
	}
	if err := e.OutputCtx(); err != nil {
		return err
	}
	return nil
}

// symbolicLinkWhitelist 软链接白名单，命中该白名单的软链接节点会被跳过
var symbolicLinkWhitelist = map[string]struct{}{
	"/u": {},
}

// defaultCheckPaths 默认必须检查的路径（Oracle 备份/归档常见目录），会被追加到用户传入的 Pathes 之后
var defaultCheckPaths = []string{consts.RmanPath, consts.ArchPath}

// ContainSymbolicLink 检查路径是否包含软链接
// 对入参 Pathes 中的每条路径逐级向上（自身及所有父目录）用 os.Lstat 检测，
// 一旦发现某一层是软链接就记录到该输入路径名下（同一条输入路径内部会去重）。
// 命中 symbolicLinkWhitelist 的软链接节点会被跳过，不计入结果。
// 结果写入：
//   - e.TmpPathes：本次待检查的路径清单（用户传入 + defaultCheckPaths）
//   - e.LinkPlans：map[输入路径] -> 该路径命中的软链接节点列表
//   - e.PlainDirs：本次检查中，路径逐级向上均不含软链接（或仅命中白名单）的路径列表
func (e *GetSymbolicLink) ContainSymbolicLink() error {
	e.TmpPathes = append(e.TmpPathes, e.Params.Pathes...)
	// 追加默认检查路径：仅在用户输入的 Pathes 中不存在时才追加，避免重复
	for _, dft := range defaultCheckPaths {
		if !slices.Contains(e.Params.Pathes, dft) {
			e.TmpPathes = append(e.TmpPathes, dft)
		}
	}
	e.LinkPlans = make(map[string][]SymbolicLinkInfo)
	e.PlainDirs = make([]string, 0, len(e.TmpPathes))
	total := 0
	for _, path := range e.TmpPathes {
		// 规整为绝对路径，避免相对路径导致漏检
		abs, err := filepath.Abs(path)
		if err != nil {
			e.Runtime.Logger.Error("resolve absolute path fail, path:%s, error:%s", path, err)
			return fmt.Errorf("resolve absolute path fail, path:%s, error:%s", path, err)
		}
		// 单条输入路径内部去重，避免同一节点重复出现（正常情况下不会，防御性处理）
		seen := make(map[string]struct{})
		// hasLink 标记当前 path 逐级向上是否命中过软链接（白名单不计）
		hasLink := false
		// 从当前路径逐级向上，直到根目录
		for cur := filepath.Clean(abs); ; cur = filepath.Dir(cur) {
			info, err := os.Lstat(cur)
			if err != nil {
				// 不存在的节点跳过，不视为错误
				if !os.IsNotExist(err) {
					e.Runtime.Logger.Error("lstat fail, path:%s, error:%s", cur, err)
					return fmt.Errorf("lstat fail, path:%s, error:%s", cur, err)
				}
			} else if info.Mode()&os.ModeSymlink != 0 {
				// 命中白名单的软链接节点跳过，不计入结果
				if _, inWhitelist := symbolicLinkWhitelist[cur]; inWhitelist {
					e.Runtime.Logger.Info("skip whitelisted symbolic link, path:%s, link:%s", path, cur)
				} else if _, ok := seen[cur]; !ok {
					seen[cur] = struct{}{}
					e.LinkPlans[path] = append(e.LinkPlans[path], SymbolicLinkInfo{Link: cur})
					hasLink = true
					total++
				}
			}
			// 到达根目录后跳出
			if cur == filepath.Dir(cur) {
				break
			}
		}
		// 无软链接且非追加的默认路径时，才计入 PlainDirs
		if !hasLink && !slices.Contains(defaultCheckPaths, path) {
			e.PlainDirs = append(e.PlainDirs, path)
		}
	}
	e.Runtime.Logger.Info("check symbolic link done, found %d symbolic link(s) across %d path(s), %d path(s) without symbolic link",
		total, len(e.LinkPlans), len(e.PlainDirs))
	return nil
}

// ResolveSymbolicLinks 解析 ContainSymbolicLink 收集到的软链接节点，
// 用 filepath.EvalSymlinks 递归解析所有层软链接，为每个节点补齐 RealPath 字段。
func (e *GetSymbolicLink) ResolveSymbolicLinks() error {
	for path, links := range e.LinkPlans {
		for i, item := range links {
			// 递归解析所有层软链接，得到最终真实绝对路径
			realPath, err := filepath.EvalSymlinks(item.Link)
			if err != nil {
				e.Runtime.Logger.Error("eval symlinks fail, link:%s, error:%s", item.Link, err)
				return fmt.Errorf("eval symlinks fail, link:%s, error:%s", item.Link, err)
			}
			links[i].RealPath = realPath
			e.Runtime.Logger.Info("resolve symbolic link, path:%s, link:%s -> real:%s",
				path, item.Link, realPath)
		}
		e.LinkPlans[path] = links
	}
	return nil
}

func (e *GetSymbolicLink) OutputCtx() error {
	err := atomjobs.PrintOutputCtx(atomjobs.ToPrettyJson(e.GetSymbolicLinkRunTimeCtx))
	if err != nil {
		return err
	}
	return nil
}
