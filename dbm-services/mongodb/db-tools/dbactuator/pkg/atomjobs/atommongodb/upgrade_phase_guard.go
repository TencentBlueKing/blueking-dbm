package atommongodb

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strconv"
	"strings"

	"dbm-services/mongodb/db-tools/dbactuator/pkg/consts"
)

// 滚动升级两阶段守卫：
// 每个 hop 内先升 secondary、最后升 primary，使整个 hop 只发生一次 stepDown。
// 由于一个成员的升级要跨越 shield/stop/backup/replace/start/unblock/check 多个原子步骤，
// 且过程中 mongod 会被停掉、节点角色/版本会发生变化（primary 经自身 stop+stepDown 后变为 secondary），
// 因此不能在每个步骤各自实时判定角色。
// 解决方式：在第一个步骤（shield_dbmon，此时 mongod 仍在线）一次性判定并把"是否跳过"持久化到决策文件，
// 后续所有步骤（含以 root 运行的 replace_package）只读取该决策文件，保证整段升级动作语义一致。

const (
	// UpgradePhaseSecondary 升 secondary 阶段：运行期为 PRIMARY 的节点跳过。
	UpgradePhaseSecondary = "secondary"
	// UpgradePhasePrimary 升 primary 阶段：已是目标版本的节点跳过（基于版本而非角色判定，避免阶段间选主导致未升级节点被误跳过）；
	// 仍为旧版本的节点（正常即旧 primary）真正执行，其 stop 触发整 hop 唯一一次 stepDown。
	UpgradePhasePrimary = "primary"
)

type upgradePhaseDecision struct {
	Phase       string `json:"phase"`
	DestVersion string `json:"destVersion"`
	Skip        bool   `json:"skip"`
}

// upgradePhaseDecisionFile 决策文件路径，落在实例数据目录下（mysql 属主可写、root 可读）。
func upgradePhaseDecisionFile(port int) string {
	return filepath.Join(consts.GetMongoDataDir(), "mongodata", strconv.Itoa(port), ".dbm_upgrade_phase.json")
}

// writeUpgradePhaseDecision 在 mongod 在线时持久化本成员在本阶段的跳过决策，供后续步骤读取。
// 采用 write-to-temp + rename 模式：rename(2) 在同文件系统上是原子的，
// 进程被 kill 时读侧永远只会看到旧文件、新文件或文件不存在，不会读到半截/空 JSON。
// 这是必要前提——upgradePhaseShouldSkip 在 unmarshal 失败时 fail-open（按"执行"处理），
// 若读到坏文件会让本该跳过的 PRIMARY 重新走 stop+stepDown，违反"每 hop 仅一次 stepDown"。
func writeUpgradePhaseDecision(port int, phase, destVersion string, skip bool) error {
	d := upgradePhaseDecision{Phase: phase, DestVersion: destVersion, Skip: skip}
	b, err := json.Marshal(&d)
	if err != nil {
		return err
	}
	path := upgradePhaseDecisionFile(port)
	tmp := path + ".tmp"
	if err := os.WriteFile(tmp, b, 0644); err != nil {
		return err
	}
	return os.Rename(tmp, path)
}

// upgradePhaseShouldSkip 读取已持久化的阶段决策；缺失或与当前 (phase,destVersion) 不匹配时返回 false（兜底为执行，不误跳过升级）。
func upgradePhaseShouldSkip(port int, phase, destVersion string) (bool, error) {
	if strings.TrimSpace(phase) == "" {
		return false, nil
	}
	b, err := os.ReadFile(upgradePhaseDecisionFile(port))
	if err != nil {
		if os.IsNotExist(err) {
			return false, nil
		}
		return false, err
	}
	var d upgradePhaseDecision
	if err := json.Unmarshal(b, &d); err != nil {
		return false, nil
	}
	if d.Phase != phase || d.DestVersion != destVersion {
		return false, nil
	}
	return d.Skip, nil
}
