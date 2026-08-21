/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package sqlserver

import (
	"fmt"
	"regexp"
	"strings"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/components"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util/crypto"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util/sqlserver"
)

// rmtPwdMaskRe matches the value of @rmtpassword in sp_addlinkedsrvlogin, whether
// it is written as N'...' or '...'. The literal may contain escaped single quotes
// (”); we consume characters lazily up to a closing quote that is NOT followed
// by another quote. Case-insensitive to be safe.
var rmtPwdMaskRe = regexp.MustCompile(`(?i)(@rmtpassword\s*=\s*N?)'((?:[^']|'')*)'`)

// maskPasswordInSQL scrubs the password literal in sp_addlinkedsrvlogin statements
// so that logs / error messages never leak the plaintext password.
// Any '@rmtpassword=N”...”' or '@rmtpassword=”...”' is rewritten to
// '@rmtpassword=N”********”'.
// Safe to call on arbitrary strings (SQL text, wrapped error messages, etc.).
func maskPasswordInSQL(s string) string {
	if s == "" {
		return s
	}
	return rmtPwdMaskRe.ReplaceAllString(s, `${1}'********'`)
}

// CloneLinkserversComp 克隆linkserver
type CloneLinkserversComp struct {
	GeneralParam *components.GeneralParam
	Params       *CloneLinkserversParam
	cloneRunTimeCtx
}

// LinkserverSecret carries a per-linkedserver remote credential.
// EncryptedPwd is expected to be base64(nonce||ciphertext) produced by
// AES-256-GCM with key = SHA256(target-host + "|" + salt). See pkg/util/crypto.
type LinkserverSecret struct {
	Name         string `json:"name" validate:"required"`          // linked-server name on source, exact match
	RemoteUser   string `json:"remote_user" validate:"required"`   // remote login name to authenticate as
	EncryptedPwd string `json:"encrypted_pwd" validate:"required"` // base64(nonce||AES-256-GCM ciphertext)
}

// CloneLinkserversParam 参数
type CloneLinkserversParam struct {
	Host       string `json:"host" validate:"required,ip" `          // 本地hostip (also used as AES key derivation source)
	Port       int    `json:"port"  validate:"required,gt=0"`        // 需要操作的实例端口
	SourceHost string `json:"source_host" validate:"required,ip" `   // 权限源的ip
	SourcePort int    `json:"source_port"  validate:"required,gt=0"` // 权限源的port

	// LinkserverSecrets: encrypted remote-credentials, one entry per linked-server
	// that uses a fixed remote login (i.e. useself=false on source). Linked servers
	// that use "self credential" (useself=true) do NOT need an entry here.
	LinkserverSecrets []LinkserverSecret `json:"linkserver_secrets"`
}

// LinkserverInfo 骨架SQL: 一个linkserver一行
type LinkserverInfo struct {
	Name      string `db:"name"`
	CreateSQL string `db:"linkserver_sql"`
}

// LinkserverMeta 认证元信息: 一个linkserver一行
type LinkserverMeta struct {
	Name       string `db:"name"`
	UseSelf    bool   `db:"useself"`
	RemoteUser string `db:"remote_user"`
}

// Init 初始化
func (c *CloneLinkserversComp) Init() error {
	var LWork *sqlserver.DbWorker
	var SWork *sqlserver.DbWorker
	var err error
	if LWork, err = sqlserver.NewDbWorker(
		c.GeneralParam.RuntimeAccountParam.SAUser,
		c.GeneralParam.RuntimeAccountParam.SAPwd,
		c.Params.Host,
		c.Params.Port,
	); err != nil {
		logger.Error("connenct by [%s:%d] failed,err:%s",
			c.Params.Host, c.Params.Port, err.Error())
		return err
	}
	if SWork, err = sqlserver.NewDbWorker(
		c.GeneralParam.RuntimeAccountParam.SAUser,
		c.GeneralParam.RuntimeAccountParam.SAPwd,
		c.Params.SourceHost,
		c.Params.SourcePort,
	); err != nil {
		logger.Error("connenct by [%s:%d] failed,err:%s",
			c.Params.SourceHost, c.Params.SourcePort, err.Error())
		return err
	}
	c.LocalDB = LWork
	c.SourceDB = SWork
	return nil
}

// buildLoginStmt assembles the sp_addlinkedsrvlogin statement for one linked server.
//
// Rule:
//   - useself=true   → clone the "trusted delegation" style: @useself='True', no user/pwd
//   - useself=false  → must find a matching LinkserverSecret; decrypt and emit fixed credential
//     If no matching secret is provided, we REFUSE to fall back to useself='True'
//     (that would silently break RPC to the source's remote target — see risk-2).
func (c *CloneLinkserversComp) buildLoginStmt(meta LinkserverMeta) (string, error) {
	esc := escapeSQLLiteral(meta.Name)

	if meta.UseSelf {
		return fmt.Sprintf(
			"EXEC master.dbo.sp_addlinkedsrvlogin @rmtsrvname=N'%s',@useself=N'True',@locallogin=NULL,@rmtuser=NULL,@rmtpassword=NULL",
			esc,
		), nil
	}

	// useself=false → look up encrypted secret by linkserver name
	var found *LinkserverSecret
	for i := range c.Params.LinkserverSecrets {
		if c.Params.LinkserverSecrets[i].Name == meta.Name {
			found = &c.Params.LinkserverSecrets[i]
			break
		}
	}
	if found == nil {
		return "", fmt.Errorf(
			"linkserver [%s] uses fixed remote credential (remote_user=%s) on source, "+
				"but no encrypted secret was provided in LinkserverSecrets; refuse to clone as useself=True to avoid silently breaking downstream RPC",
			meta.Name, meta.RemoteUser,
		)
	}

	// Sanity check: remote_user in secret should match source's remote_user.
	// We warn but do not hard-fail — DBM ticket layer is the source of truth for what
	// the target should look like (user may intentionally re-map the remote login).
	if found.RemoteUser != meta.RemoteUser {
		logger.Warn("linkserver [%s] remote_user on source is [%s] but secret specifies [%s]; using the one from secret",
			meta.Name, meta.RemoteUser, found.RemoteUser)
	}

	plainPwd, err := crypto.DecryptLinkserverSecret(c.Params.Host, found.EncryptedPwd)
	if err != nil {
		return "", fmt.Errorf("decrypt password for linkserver [%s] failed: %w", meta.Name, err)
	}

	// Defensive sanity checks on the decrypted plaintext before it enters the T-SQL literal.
	// sp_addlinkedsrvlogin @rmtpassword is nvarchar(128); we also reject NUL because
	// SQL Server truncates nvarchar at NUL which would silently corrupt the credential.
	// NOTE: this is defense-in-depth only — the plaintext originates from DBM's
	// AES-256-GCM ciphertext (key derived from target host + salt), so an attacker
	// crafting a malicious payload here already implies key compromise.
	if strings.ContainsRune(plainPwd, 0x00) {
		return "", fmt.Errorf("decrypted password for linkserver [%s] contains NUL byte; refuse to build login stmt", meta.Name)
	}
	if len(plainPwd) > 128 {
		return "", fmt.Errorf("decrypted password for linkserver [%s] length=%d exceeds sp_addlinkedsrvlogin limit(128)", meta.Name, len(plainPwd))
	}

	return fmt.Sprintf(
		"EXEC master.dbo.sp_addlinkedsrvlogin @rmtsrvname=N'%s',@useself=N'False',@locallogin=NULL,@rmtuser=N'%s',@rmtpassword=N'%s'",
		esc,
		escapeSQLLiteral(found.RemoteUser),
		escapeSQLLiteral(plainPwd),
	), nil
}

// CloneLinkservers 克隆linkservers
//
// Flow (single-entry):
//  1. Query GET_LINKSERVERS_META  from source → per-LS auth meta (useself / remote_user)
//  2. Query GET_LINKSERVERS_INFO  from source → per-LS skeleton clone SQL (no login stmt)
//     2.5 TOCTOU guard: verify meta and skeleton name-sets match; fail-fast on divergence
//     (caller retries — the inconsistency window is milliseconds wide).
//  3. For each LS: assemble the correct sp_addlinkedsrvlogin stmt (decrypting the
//     password if useself=false) and append to the skeleton, then Exec on target.
//
// Semantics: "aggressive overwrite" — this component is designed for INTRA-CLUSTER
// node synchronization (primary/secondary, multi-replica), so the target's linked
// servers are FULLY overwritten by the source. Any per-user login mapping that a
// DBA may have added manually on the target will be dropped (by @droplogins='droplogins'
// in the skeleton SQL) and only the source's default mapping is rebuilt.
// This is BY DESIGN, not a bug — see the comment on GET_LINKSERVERS_INFO for details.
func (c *CloneLinkserversComp) CloneLinkservers() error {
	// 1) meta
	var metas []LinkserverMeta
	if err := c.SourceDB.Queryx(&metas, cst.GET_LINKSERVERS_META); err != nil {
		logger.Error("get linkserver meta failed: %s", err.Error())
		return err
	}
	if len(metas) == 0 {
		logger.Warn("[%s:%d] linkserver is not set here, skip", c.Params.SourceHost, c.Params.SourcePort)
		return nil
	}
	metaByName := make(map[string]LinkserverMeta, len(metas))
	for _, m := range metas {
		metaByName[m.Name] = m
	}

	// 2) skeleton per LS
	var skeletons []LinkserverInfo
	if err := c.SourceDB.Queryx(&skeletons, cst.GET_LINKSERVERS_INFO); err != nil {
		logger.Error("get linkserver skeleton sql failed: %s", err.Error())
		return err
	}

	// 2.5) TOCTOU guard: meta and skeleton are two independent snapshots of
	// source's sys.servers. If a linked server is added/dropped on source
	// between the two Queryx calls, the two name-sets may diverge:
	//   - name in skeleton but not in meta → already handled below (`no meta`, fail-fast)
	//   - name in meta but not in skeleton → would be SILENTLY skipped, breaking
	//     the "aggressive overwrite / intra-cluster fully-consistent" contract.
	// We compute the symmetric difference and fail-fast on any divergence;
	// callers should simply retry — the window is milliseconds wide.
	skeletonByName := make(map[string]struct{}, len(skeletons))
	for _, sk := range skeletons {
		skeletonByName[sk.Name] = struct{}{}
	}
	var missInSkeleton, missInMeta []string
	for name := range metaByName {
		if _, ok := skeletonByName[name]; !ok {
			missInSkeleton = append(missInSkeleton, name)
		}
	}
	for name := range skeletonByName {
		if _, ok := metaByName[name]; !ok {
			missInMeta = append(missInMeta, name)
		}
	}
	if len(missInSkeleton) > 0 || len(missInMeta) > 0 {
		return fmt.Errorf(
			"linkserver snapshot inconsistency between meta and skeleton queries on source [%s:%d] "+
				"(likely concurrent add/drop on source); missing_in_skeleton=%v, missing_in_meta=%v; please retry",
			c.Params.SourceHost, c.Params.SourcePort, missInSkeleton, missInMeta,
		)
	}

	// 3) per-LS: assemble + exec
	for _, sk := range skeletons {
		meta, ok := metaByName[sk.Name]
		if !ok {
			// should never happen — meta and skeleton come from the same sys.servers snapshot
			logger.Error("no meta found for linkserver [%s], abort", sk.Name)
			return fmt.Errorf("no meta for linkserver [%s]", sk.Name)
		}

		loginStmt, err := c.buildLoginStmt(meta)
		if err != nil {
			// Fail-fast: refuse to clone this LS. Do not proceed silently.
			logger.Error("build login stmt for [%s] failed: %s", sk.Name, err.Error())
			return err
		}

		// Inject the login stmt right before the closing 'END' of the skeleton block.
		// The skeleton ends with:
		//   ...sp_serveroption... 'remote proc transaction promotion' ...
		//   END
		// so we simply append: login stmt is idempotent w.r.t sp_addlinkedserver order.
		fullSQL := sk.CreateSQL + "\r\n" + loginStmt

		if _, err := c.LocalDB.Exec(fullSQL); err != nil {
			// IMPORTANT: the underlying ExecMore wraps the full SQL text into the
			// error message (fmt.Errorf("exec %s failed,err:%w", sqlStr, err)),
			// which for linked-server cloning contains sp_addlinkedsrvlogin with
			// the plaintext @rmtpassword. Scrub it before logging so credentials
			// never leak into log files.
			logger.Error("exec create linkserver [%s] on target [%s:%d] failed: %s",
				sk.Name, c.Params.Host, c.Params.Port, maskPasswordInSQL(err.Error()))
			return fmt.Errorf("%s", maskPasswordInSQL(err.Error()))
		}
		logger.Info("linkserver [%s] cloned (useself=%v)", sk.Name, meta.UseSelf)
	}
	return nil
}

// escapeSQLLiteral escapes a T-SQL single-quoted string literal.
//
// Why string-concat instead of parameterized sp_executesql?
//   - sp_addlinkedsrvlogin is a system stored proc invoked via EXEC; its @rmtpassword
//     parameter cannot be bound as a Go database/sql driver parameter because we do
//     not call it as the top-level statement — it is appended to a larger skeleton
//     script (GET_LINKSERVERS_INFO) that already contains BEGIN...IF EXISTS...
//     sp_addlinkedserver...sp_serveroption...END and is executed as a single batch.
//   - Rewriting the whole batch as nested sp_executesql with a full parameter list
//     is possible but disproportionately invasive for the current threat model:
//     the password plaintext comes from a DBM-side AES-256-GCM ciphertext (key
//     derived from target host + salt), so the only path to a crafted payload
//     here is prior key compromise, at which point SQL injection is not the
//     leading risk. Callers additionally validate NUL / length in buildLoginStmt.
func escapeSQLLiteral(s string) string {
	return strings.ReplaceAll(s, "'", "''")
}
