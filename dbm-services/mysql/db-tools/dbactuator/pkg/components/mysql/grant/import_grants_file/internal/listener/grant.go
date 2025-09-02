package listener

import (
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/grant/import_grants_file/internal/parsing"
	"strings"

	"github.com/antlr4-go/antlr/v4"
)

// EnterGrantStatement
/*
	grant 语句分成三类
	1. 普通授权
	2. 代理
	3. 角色
*/
func (c *PrivListener) EnterGrantStatement(ctx *parsing.GrantStatementContext) {
	c.StatementType = PrivStatementGrant

	if pl := ctx.PrivilegeLevel(); pl != nil {
		c.GrantType = GrantStatementTypeNormal

		//// 这东西长度可能不止是 2
		//// 比如其实是错误拼写的 `db.%.*`
		//// 但是为了忠实还原, 得搞回去
		//spl := strings.Split(pl.GetText(), ".")
		//c.DBName = strings.Trim(strings.Join(spl[:len(spl)-1], "."), "'`")
		//c.TableName = strings.Trim(spl[len(spl)-1], "'`")

		if po := ctx.GetPrivilegeObject(); po != nil {
			c.PrivObject = strings.TrimSpace(po.GetText())
		}

		c.WithGrantOption = withGrantOptionPattern.MatchString(c.RawSQL)

		if ctx.GetTlsNone() != nil {
			c.TlsNone = new(bool)
		}

		if ctx.AS() != nil && ctx.ROLE() != nil && ctx.RoleOption() != nil {
			roIter := antlr.Interval{}
			roIter.Start = ctx.AS().GetSourceInterval().Start
			roIter.Stop = ctx.RoleOption().GetSourceInterval().Stop
			c.RoleOption = strings.TrimSpace(c.tokenStream.GetTextFromInterval(roIter))
		}

		var pvs []string
		for _, pc := range ctx.AllPrivelegeClause() {
			pvs = append(pvs, c.tokenStream.GetTextFromInterval(pc.GetSourceInterval()))
		}
		c.Privileges = strings.Join(pvs, ", ")
	} else {
		c.GrantType = GrantStatementTypeRole
		if ad := ctx.ADMIN(); ad != nil {
			c.WithAdminOption = true
		}

		tokenTOInterval := ctx.TO().GetSourceInterval()
		for _, ele := range ctx.AllUserName() {
			thisInterval := ele.GetSourceInterval()
			if thisInterval.Stop < tokenTOInterval.Start {
				c.FromUserOrIds = append(c.FromUserOrIds, ele.GetText())
			} else if thisInterval.Start > tokenTOInterval.Stop {
				c.ToUserOrIds = append(c.ToUserOrIds, ele.GetText())
			}
		}
	}
}

func (c *PrivListener) EnterGrantProxy(ctx *parsing.GrantProxyContext) {
	c.StatementType = PrivStatementGrant
	c.GrantType = GrantStatementTypeProxy
	c.FromUsername = ctx.GetFromFirst().GetText()
	c.ToUsernames = []string{ctx.GetToFirst().GetText()}
	for _, ele := range ctx.GetToOther() {
		c.ToUsernames = append(c.ToUsernames, ele.GetText())
	}

	c.WithGrantOption = ctx.WITH() != nil
}
