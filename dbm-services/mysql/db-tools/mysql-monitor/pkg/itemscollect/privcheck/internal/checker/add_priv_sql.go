package checker

import (
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/itemscollect/privcheck/internal/listener"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/itemscollect/privcheck/internal/parsing"

	"github.com/antlr4-go/antlr/v4"
)

func (c *Analyzer) AddPrivSQLString(sql string) {
	in := antlr.NewInputStream(sql)
	lexer := parsing.NewMySqlLexer(in)
	stream := antlr.NewCommonTokenStream(lexer, 0)
	p := parsing.NewMySqlParser(stream)
	tree := p.Root()
	l := listener.NewPrivListener(stream)
	antlr.ParseTreeWalkerDefault.Walk(l, tree)

	c.addUserSummary(l)
}

func (c *Analyzer) addUserSummary(l *listener.PrivListener) {
	if !l.IsGrantPriv && !l.IsCreateUser {
		return
	}

	if _, ok := c.userPrivSummaries[l.Username]; !ok {
		c.userPrivSummaries[l.Username] = &userPrivSummary{
			Username: l.Username,
		}
	}

	if l.IsCreateUser {
		return
	}

	c.addHostSummary(l, c.userPrivSummaries[l.Username])
}

func (c *Analyzer) addHostSummary(l *listener.PrivListener, userSummary *userPrivSummary) {
	if userSummary.HostPrivSummaries == nil {
		userSummary.HostPrivSummaries = make(map[string]*hostPrivSummary)
	}

	if _, ok := userSummary.HostPrivSummaries[l.Host]; !ok {
		userSummary.HostPrivSummaries[l.Host] = &hostPrivSummary{
			Host:     l.Host,
			Password: l.Password,
		}
	}

	c.addDBSummary(l, userSummary.HostPrivSummaries[l.Host])
}

func (c *Analyzer) addDBSummary(l *listener.PrivListener, hostSummary *hostPrivSummary) {
	if hostSummary.DBPrivSummaries == nil {
		hostSummary.DBPrivSummaries = make(map[string]*dbPrivSummary)
	}

	if _, ok := hostSummary.DBPrivSummaries[l.DBName]; !ok {
		hostSummary.DBPrivSummaries[l.DBName] = &dbPrivSummary{
			DBName:          l.DBName,
			WithGrantOption: l.WithGrantOption,
		}
	}

	c.addTableSummary(l, hostSummary.DBPrivSummaries[l.DBName])
}

func (c *Analyzer) addTableSummary(l *listener.PrivListener, dbSummary *dbPrivSummary) {
	if dbSummary.TablePrivSummaries == nil {
		dbSummary.TablePrivSummaries = make(map[string]*tablePrivSummary)
	}

	if _, ok := dbSummary.TablePrivSummaries[l.TableName]; !ok {
		dbSummary.TablePrivSummaries[l.TableName] = &tablePrivSummary{
			TableName:  l.TableName,
			Privileges: l.Privileges,
		}
	}
}
