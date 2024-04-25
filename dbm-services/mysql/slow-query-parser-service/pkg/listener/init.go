package listener

import (
	"errors"
	"fmt"
	"slow-query-parser-service/pkg/parser"

	"github.com/antlr4-go/antlr/v4"
)

type SqlListener struct {
	*parser.BaseMySqlParserListener
	tokens      antlr.TokenStream
	rewriter    *antlr.TokenStreamRewriter
	errListener *ErrorListener
	Cmd         string
	Databases   []string
	Tables      []string
	Functions   []string
}

func NewSqlListener(rawSql string) *SqlListener {
	errListener := &ErrorListener{}

	input := antlr.NewInputStream(rawSql)
	lexer := parser.NewMySqlLexer(input)
	lexer.RemoveErrorListeners()
	lexer.AddErrorListener(errListener)

	stream := antlr.NewCommonTokenStream(lexer, antlr.TokenDefaultChannel)

	p := parser.NewMySqlParser(stream)
	p.RemoveErrorListeners()
	p.AddErrorListener(errListener)

	l := &SqlListener{
		tokens:      stream,
		rewriter:    antlr.NewTokenStreamRewriter(stream),
		errListener: errListener,
	}

	antlr.ParseTreeWalkerDefault.Walk(l, p.Root())

	return l
}

func (r *SqlListener) RawSql() string {
	return r.tokens.GetAllText()
}

func (r *SqlListener) ReplacedSql() string {
	return r.rewriter.GetTextDefault()
}

func (r *SqlListener) Err() error {
	if len(r.errListener.Errors) > 0 {
		return errors.Join(r.errListener.Errors...)
	}
	return nil
}

//func (r *SqlListener) Report() {
//	input := antlr.NewInputStream(rawSql)
//	lexer := parser.NewMySqlLexer(input)
//	stream := antlr.NewCommonTokenStream(lexer, 0)
//	p := parser.NewMySqlParser(stream)
//
//}

type ErrorListener struct {
	*antlr.DefaultErrorListener
	Errors []error
}

func (r *ErrorListener) SyntaxError(recognizer antlr.Recognizer, offendingSymbol interface{}, line, column int, msg string, e antlr.RecognitionException) {
	r.Errors = append(
		r.Errors,
		fmt.Errorf("syntax error in line %d column %d: %s", line, column, msg))
}
