package main

import (
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/grant/import_grants_file/internal/listener"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/grant/import_grants_file/internal/parsing"
	"fmt"

	"github.com/antlr4-go/antlr/v4"
)

func main() {
	sql := "GRANT SELECT, SHOW VIEW ON `%`.`abc` TO 'bkbase_read'@'%';"
	in := antlr.NewInputStream(sql)
	lexer := parsing.NewMariaDBLexer(in)
	stream := antlr.NewCommonTokenStream(lexer, 0)
	p := parsing.NewMariaDBParser(stream)
	p.RemoveErrorListeners()
	p.AddErrorListener(antlr.NewDiagnosticErrorListener(true))

	tree := p.Root()

	l := listener.NewPrivListener(stream)
	antlr.ParseTreeWalkerDefault.Walk(l, tree)

	fmt.Printf("%s\n", l)
}
