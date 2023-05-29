package util_test

import (
	"bk-dbconfig/pkg/util"
	"fmt"
	"testing"
)

type I interface{}

type A struct {
	Greeting string
	Message  string
	Pi       float64
}

type B struct {
	Struct    A
	Ptr       *A
	Answer    int
	Map       map[string]string
	StructMap map[string]interface{}
	Slice     []string
}

func create() I {
	// The type C is actually hidden, but reflection allows us to look inside it
	type C struct {
		String string
	}

	return B{
		Struct: A{
			Greeting: " Hello!\n",
			Message:  " translate this\n",
			Pi:       3.14,
		},
		Ptr: &A{
			Greeting: " What's up?\n",
			Message:  " point here\n",
			Pi:       3.14,
		},
		Map: map[string]string{
			"Test": " translate this as well\n",
		},
		StructMap: map[string]interface{}{
			"C": C{
				String: " deep\n",
			},
		},
		Slice: []string{
			" and one more\n",
		},
		Answer: 42,
	}
}

func TestTrimSpace(t *testing.T) {
	// Some example test cases so you can mess around and see if it's working
	// To check if it's correct look at the output, no automated checking here

	// Test the simple cases
	{
		fmt.Println("Test with nil pointer to struct:")
		var original *B
		translated := util.TrimSpace(original)
		fmt.Println("original:  ", original)
		fmt.Println("translated:", translated)
		fmt.Println()
	}
	{
		fmt.Println("Test with nil pointer to interface:")
		var original *I
		translated := util.TrimSpace(original)
		fmt.Println("original:  ", original)
		fmt.Println("translated:", translated)
		fmt.Println()
	}
	{
		fmt.Println("Test with struct that has no elements:")
		type E struct {
		}
		var original E
		translated := util.TrimSpace(original)
		fmt.Println("original:  ", original)
		fmt.Println("translated:", translated)
		fmt.Println()
	}
	{
		fmt.Println("Test with empty struct:")
		var original B
		translated := util.TrimSpace(original)
		fmt.Println("original:  ", original, "->", original.Ptr)
		fmt.Println("translated:", translated, "->", translated.(B).Ptr)
		fmt.Println()
	}

	// Imagine we have no influence on the value returned by create()
	created := create()
	{
		// Assume we know that `created` is of type B
		fmt.Println("Translating a struct:")
		original := created.(B)
		translated := util.TrimSpace(original)
		fmt.Println("original:  ", original, "->", original.Ptr)
		fmt.Println("translated:", translated, "->", translated.(B).Ptr)
		fmt.Println()
	}
	{
		// Assume we don't know created's type
		fmt.Println("Translating a struct wrapped in an interface:")
		original := created
		translated := util.TrimSpace(original)
		fmt.Println("original:  ", original, "->", original.(B).Ptr)
		fmt.Println("translated:", translated, "->", translated.(B).Ptr)
		fmt.Println()
	}
	{
		// Assume we don't know B's type and want to pass a pointer
		fmt.Println("Translating a pointer to a struct wrapped in an interface:")
		original := &created
		translated := util.TrimSpace(original)
		fmt.Println("original:  ", (*original), "->", (*original).(B).Ptr)
		fmt.Println("translated:", (*translated.(*I)), "->", (*translated.(*I)).(B).Ptr)
		fmt.Println()
	}
	{
		// Assume we have a struct that contains an interface of an unknown type
		fmt.Println("Translating a struct containing a pointer to a struct wrapped in an interface:")
		type D struct {
			Payload *I
		}
		original := D{
			Payload: &created,
		}
		translated := util.TrimSpace(original)
		fmt.Println("original:  ", original, "->", (*original.Payload), "->", (*original.Payload).(B).Ptr)
		fmt.Println("translated:", translated, "->", (*translated.(D).Payload), "->", (*(translated.(D).Payload)).(B).Ptr)
		fmt.Println()
	}
}
