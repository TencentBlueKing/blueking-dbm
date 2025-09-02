package listener

import (
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/grant/import_grants_file/internal/parsing"
	"strings"

	"github.com/antlr4-go/antlr/v4"
)

func (c *PrivListener) EnterCreateUserMysqlV56(ctx *parsing.CreateUserMysqlV56Context) {
	c.StatementType = PrivStatementCreate
}

func (c *PrivListener) EnterCreateUserMysqlV80(ctx *parsing.CreateUserMysqlV80Context) {
	c.StatementType = PrivStatementCreate

	optIter := antlr.Interval{
		Start: 99999999999, Stop: 0,
	}
	for _, ele := range ctx.AllUserPasswordOption() {
		iter := ele.GetSourceInterval()
		if iter.Start < optIter.Start {
			optIter.Start = iter.Start
		}
		if iter.Stop > optIter.Stop {
			optIter.Stop = iter.Stop
		}
	}

	for _, ele := range ctx.AllUserLockOption() {
		iter := ele.GetSourceInterval()
		if iter.Start < optIter.Start {
			optIter.Start = iter.Start
		}
		if iter.Stop > optIter.Stop {
			optIter.Stop = iter.Stop
		}
	}

	c.PasswordLockOption = strings.TrimSpace(c.tokenStream.GetTextFromInterval(optIter))

	if ctx.GetTlsNone() != nil {
		c.TlsNone = new(bool)
	}
}
