package syntax_test

import (
	"fmt"
	"testing"

	"github.com/antonmedv/expr"
)

func TestRule(t *testing.T) {
	t.Log("start testing...")
	type CCC struct {
		Val  interface{}
		Item interface{}
	}
	e := CCC{
		Item: true,
	}
	pgm, err := expr.Compile(" Item ", expr.Env(CCC{}), expr.AsBool())
	if err != nil {
		t.Fatal(err)
	}
	output, err := expr.Run(pgm, e)
	if err != nil {
		panic(err)
	}
	fmt.Println(output)
}
